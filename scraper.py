"""
다나와 부품별 최저가 히스토리 스크래퍼

사용법:
  python scraper.py --part cpu
  python scraper.py --part gpu
  python scraper.py --part mb
  python scraper.py --part ssd
  python scraper.py --all
"""

import requests
from bs4 import BeautifulSoup
import pandas as pd
import re
import time
import argparse
from datetime import datetime, timedelta
from pathlib import Path

# ── 데이터 수집 기준일 (RAM 과 동일하게 고정) ──────────────────────────────
END_DATE   = datetime(2026, 4, 14)
START_DATE = END_DATE - timedelta(days=180)   # 2025-10-17

# ── 다나와 제품 코드 ────────────────────────────────────────────────────────
PRODUCTS = {
    'ram': {
        'name':  '삼성 DDR5-5600 16GB',
        'pcode': '',           # RAM 은 기존 CSV 사용
        'csv':   'data/ram_prices.csv',
    },
    'cpu': {
        'name':  'AMD 라이젠5 9600X (그래니트 릿지) 멀티팩',
        'pcode': '62794079',
        'csv':   'data/cpu_prices.csv',
    },
    'gpu': {
        'name':  'MSI 지포스 RTX 5070 게이밍 트리오 OC 화이트 D7 12GB',
        'pcode': '78102347',
        'csv':   'data/gpu_prices.csv',
    },
    'mb': {
        'name':  'MSI MAG B650M 박격포 WIFI',
        'pcode': '17971187',
        'csv':   'data/mb_prices.csv',
    },
    'ssd': {
        'name':  'SK하이닉스 Platinum P41 M.2 NVMe 1TB',
        'pcode': '17001050',
        'csv':   'data/ssd_prices.csv',
    },
}

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                  'AppleWebKit/537.36 (KHTML, like Gecko) '
                  'Chrome/124.0.0.0 Safari/537.36',
    'Referer': 'https://prod.danawa.com/',
    'Accept-Language': 'ko-KR,ko;q=0.9',
}


def fetch_price_history(pcode: str) -> list[dict]:
    """다나와 가격 히스토리 AJAX 엔드포인트 호출"""
    url = 'https://prod.danawa.com/info/dprice/ajax/getProductPriceHistoryList.ajax.php'
    data = {
        'pcode':     pcode,
        'startDate': START_DATE.strftime('%Y-%m-%d'),
        'endDate':   END_DATE.strftime('%Y-%m-%d'),
        'page':      1,
    }

    resp = requests.post(url, data=data, headers=HEADERS, timeout=15)
    resp.raise_for_status()

    result = resp.json()
    records = []

    for item in result.get('priceHistoryList', result.get('list', [])):
        date  = item.get('date') or item.get('priceDate') or ''
        price = item.get('minPrice') or item.get('price') or 0
        if date and price:
            # 날짜 포맷 통일 (YYYYMMDD or YYYY-MM-DD)
            if len(date) == 8:
                date = f'{date[:4]}-{date[4:6]}-{date[6:]}'
            records.append({'date': date, 'price': int(str(price).replace(',', ''))})

    return sorted(records, key=lambda x: x['date'])


def fetch_price_from_page(pcode: str) -> list[dict]:
    """페이지 HTML 에서 가격 히스토리 JSON 추출 (폴백)"""
    url = f'https://prod.danawa.com/info/?pcode={pcode}'
    resp = requests.get(url, headers=HEADERS, timeout=15)
    soup = BeautifulSoup(resp.text, 'html.parser')

    records = []

    # script 태그에서 가격 히스토리 JSON 탐색
    for script in soup.find_all('script'):
        text = script.string or ''
        # 날짜+가격 배열 패턴 탐색
        match = re.search(r'\[(\s*\{["\']date["\'].*?\}[\s,]*)+\]', text, re.DOTALL)
        if match:
            try:
                import json
                data = json.loads(match.group(0))
                for item in data:
                    date  = item.get('date', '')
                    price = item.get('price') or item.get('minPrice') or 0
                    if date and price:
                        records.append({'date': date, 'price': int(price)})
            except Exception:
                pass

    return sorted(records, key=lambda x: x['date'])


def save_csv(records: list[dict], csv_path: str):
    """기존 CSV 와 병합 후 저장 (중복 날짜 제거)"""
    path = Path(csv_path)
    df_new = pd.DataFrame(records)

    if path.exists():
        df_old = pd.read_csv(path)
        df = pd.concat([df_old, df_new]).drop_duplicates('date').sort_values('date')
        print(f'  기존 {len(df_old)}행 + 신규 {len(df_new)}행 → 병합 후 {len(df)}행')
    else:
        df = df_new
        print(f'  신규 CSV 생성: {len(df)}행')

    df.to_csv(path, index=False)
    print(f'  저장 완료: {path}')


def scrape(part_key: str):
    info  = PRODUCTS[part_key]
    pcode = info['pcode']

    if not pcode:
        print(f'\n[{part_key.upper()}] pcode 가 비어 있어 건너뜁니다.')
        return

    print(f'\n[{part_key.upper()}] {info["name"]} 수집 중...')
    print(f'  기간: {START_DATE.strftime("%Y-%m-%d")} ~ {END_DATE.strftime("%Y-%m-%d")}')

    records = []

    # 1차: AJAX 엔드포인트 시도
    try:
        records = fetch_price_history(pcode)
    except Exception as e:
        print(f'  AJAX 실패 ({e}) → 페이지 파싱 시도...')

    # 2차: 페이지 HTML 파싱 폴백
    if not records:
        try:
            records = fetch_price_from_page(pcode)
        except Exception as e:
            print(f'  페이지 파싱도 실패: {e}')

    if not records:
        print('  데이터를 가져오지 못했습니다.')
        print('  → 다나와 제품 페이지에서 "가격추이" 탭 → 개발자도구(F12) → Network 탭에서')
        print('    실제 API 주소를 확인한 후 fetch_price_history() 의 url 을 수정해 주세요.')
        return

    print(f'  {records[0]["date"]} ~ {records[-1]["date"]}  총 {len(records)}일')
    save_csv(records, info['csv'])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--part', choices=list(PRODUCTS.keys()),
                        help='수집할 부품 (ram/cpu/gpu/mb/ssd)')
    parser.add_argument('--all', action='store_true', help='전체 부품 수집')
    args = parser.parse_args()

    if args.all:
        for key in PRODUCTS:
            scrape(key)
            time.sleep(1)
    elif args.part:
        scrape(args.part)
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
