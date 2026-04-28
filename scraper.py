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
import pandas as pd
import json
import time
import argparse
from datetime import datetime, timedelta
from pathlib import Path

# ── 다나와 제품 코드 설정 ─────────────────────────────────────────
# 다나와 제품 URL: https://prod.danawa.com/info/?pcode=XXXXXXX
# 아래 pcode 는 각 제품 페이지 URL에서 확인 후 채워주세요
PRODUCTS = {
    'ram': {
        'name':  '삼성 DDR5-5600 16GB',
        'pcode': '',          # ← 다나와 URL의 pcode 값
        'csv':   'data/ram_prices.csv',
    },
    'cpu': {
        'name':  'AMD Ryzen 5 9600X',
        'pcode': '',          # ← 다나와 URL의 pcode 값
        'csv':   'data/cpu_prices.csv',
    },
    'gpu': {
        'name':  'RTX 4070 Super',
        'pcode': '',          # ← 다나와 URL의 pcode 값
        'csv':   'data/gpu_prices.csv',
    },
    'mb': {
        'name':  'MSI MAG B650 WIFI',
        'pcode': '',          # ← 다나와 URL의 pcode 값
        'csv':   'data/mb_prices.csv',
    },
    'ssd': {
        'name':  'SK Hynix P44 Pro 1TB',
        'pcode': '',          # ← 다나와 URL의 pcode 값
        'csv':   'data/ssd_prices.csv',
    },
}

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                  'AppleWebKit/537.36 (KHTML, like Gecko) '
                  'Chrome/124.0.0.0 Safari/537.36',
    'Referer': 'https://prod.danawa.com/',
}


def fetch_price_history(pcode: str, days: int = 180) -> list[dict]:
    """다나와 가격 히스토리 API 호출"""
    end   = datetime.today()
    start = end - timedelta(days=days)

    url = 'https://pricehistory.danawa.com/api/pricehistory/list'
    params = {
        'productCode': pcode,
        'startDate':   start.strftime('%Y%m%d'),
        'endDate':     end.strftime('%Y%m%d'),
        'marketType':  'A',   # A = 전체
    }

    resp = requests.get(url, params=params, headers=HEADERS, timeout=15)
    resp.raise_for_status()
    data = resp.json()

    records = []
    for item in data.get('priceHistoryList', []):
        date  = item.get('date', '')
        price = item.get('minPrice', 0)
        if date and price:
            records.append({
                'date':  f'{date[:4]}-{date[4:6]}-{date[6:]}',
                'price': int(price),
            })

    return sorted(records, key=lambda x: x['date'])


def save_csv(records: list[dict], csv_path: str, part_name: str):
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
    info = PRODUCTS[part_key]
    pcode = info['pcode']

    if not pcode:
        print(f'\n[{part_key.upper()}] pcode 가 비어 있습니다.')
        print(f'  다나와에서 "{info["name"]}" 검색 후')
        print(f'  제품 페이지 URL의 pcode=XXXXXXX 값을 scraper.py PRODUCTS[\'{part_key}\'][\'pcode\'] 에 입력하세요.')
        return

    print(f'\n[{part_key.upper()}] {info["name"]} 수집 중...')
    try:
        records = fetch_price_history(pcode)
        if not records:
            print('  데이터 없음 — pcode 를 확인하세요.')
            return
        print(f'  {records[0]["date"]} ~ {records[-1]["date"]}  총 {len(records)}일')
        save_csv(records, info['csv'], info['name'])
    except Exception as e:
        print(f'  오류: {e}')


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
