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


def parse_date(raw: str) -> datetime | None:
    """YY-MM-DD 또는 YY-MM → datetime 변환"""
    raw = '20' + raw  # 26-04-14 → 2026-04-14
    for fmt in ('%Y-%m-%d', '%Y-%m'):
        try:
            return datetime.strptime(raw, fmt)
        except ValueError:
            pass
    return None


def fetch_raw(pcode: str) -> dict:
    """다나와 가격 히스토리 전체 API 호출"""
    timestamp = int(time.time() * 1000)
    url = (
        f'https://prod.danawa.com/info/ajax/getProductPriceList.ajax.php'
        f'?productCode={pcode}&period=1&_={timestamp}'
    )
    resp = requests.get(url, headers=HEADERS, timeout=15)
    resp.raise_for_status()
    return resp.json()


def fetch_price_history(pcode: str) -> list[dict]:
    """주간(3개월) + 월간(12개월) 데이터 합산 후 일별 보간"""
    data = fetch_raw(pcode)

    # 주간 데이터 (key="3"): Fulldate = YY-MM-DD
    weekly = []
    for item in data.get('3', {}).get('result', []):
        dt = parse_date(item.get('Fulldate', ''))
        price = item.get('minPrice', 0)
        if dt and price:
            weekly.append((dt, int(price)))

    # 월간 데이터 (key="12"): date = YY-MM → 해당 월 1일로 처리
    monthly = []
    for item in data.get('12', {}).get('result', []):
        dt = parse_date(item.get('date', ''))
        price = item.get('minPrice', 0)
        if dt and price:
            monthly.append((dt, int(price)))

    # 월간 + 주간 합산 → 중복 제거 (주간 우선)
    combined = {dt: price for dt, price in monthly}
    for dt, price in weekly:
        combined[dt] = price  # 주간이 더 정확하므로 덮어씀

    anchor_points = sorted(combined.items())
    if not anchor_points:
        return []

    # 앵커 포인트 사이를 일별 선형 보간
    records = []
    for i in range(len(anchor_points) - 1):
        dt_start, p_start = anchor_points[i]
        dt_end,   p_end   = anchor_points[i + 1]
        days = (dt_end - dt_start).days

        for d in range(days):
            dt = dt_start + timedelta(days=d)
            if START_DATE <= dt <= END_DATE:
                price = int(p_start + (p_end - p_start) * d / days)
                records.append({'date': dt.strftime('%Y-%m-%d'), 'price': price})

    # 마지막 앵커 포인트 추가
    last_dt, last_price = anchor_points[-1]
    if START_DATE <= last_dt <= END_DATE:
        records.append({'date': last_dt.strftime('%Y-%m-%d'), 'price': last_price})

    # 중복 제거 및 정렬
    seen = set()
    unique = []
    for r in sorted(records, key=lambda x: x['date']):
        if r['date'] not in seen:
            seen.add(r['date'])
            unique.append(r)

    return unique


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
