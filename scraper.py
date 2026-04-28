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
    'Referer': 'https://danawa.com',
    'Host':    'prod.danawa.com',
}


def fetch_price_history(pcode: str) -> list[dict]:
    """다나와 가격 히스토리 API 호출"""
    timestamp = int(time.time() * 1000)
    url = (
        f'https://prod.danawa.com/info/ajax/getProductPriceList.ajax.php'
        f'?productCode={pcode}&period=6&_={timestamp}'
    )

    resp = requests.get(url, headers=HEADERS, timeout=15)
    resp.raise_for_status()
    data = resp.json()

    records = []

    # 응답 구조: 월별 키로 구성된 dict
    for month_key, month_data in data.items():
        if not isinstance(month_data, dict):
            continue
        price_list = month_data.get('result', [])
        for item in price_list:
            full_date = item.get('Fulldate') or item.get('fullDate') or ''
            price     = item.get('minPrice') or item.get('price') or 0

            if not full_date or not price:
                continue

            # YY-MM-DD → YYYY-MM-DD 변환
            if len(full_date) == 8:   # YY-MM-DD
                full_date = '20' + full_date

            try:
                dt = datetime.strptime(full_date, '%Y-%m-%d')
            except ValueError:
                continue

            # 수집 기간 필터 (2025-10-17 ~ 2026-04-14)
            if START_DATE <= dt <= END_DATE:
                records.append({
                    'date':  full_date,
                    'price': int(str(price).replace(',', '')),
                })

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

    try:
        records = fetch_price_history(pcode)
    except Exception as e:
        print(f'  오류: {e}')
        return

    if not records:
        print('  해당 기간 데이터가 없습니다.')
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
