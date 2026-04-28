"""
예측값 vs 실제값 비교 스크립트 (단일 변수 선형 회귀 버전)
- 학습 데이터 마지막 날(2026-04-14) 이후 13일(4/15~4/27) 예측
- ram_prices_actual_apr2026.csv 의 실제값과 비교
- comparison_result.csv 로 저장
"""

import os
import json
import warnings
import numpy as np
import pandas as pd
import tensorflow as tf

warnings.filterwarnings('ignore')

from datetime import date, timedelta

BASE_DIR    = os.path.dirname(__file__)
DATA_PATH   = os.path.join(BASE_DIR, 'data', 'train', 'ram_prices.csv')
ACTUAL_PATH = os.path.join(BASE_DIR, 'data', 'actual', 'ram_prices_actual_apr2026.csv')
MODEL_PATH  = os.path.join(BASE_DIR, 'saved_model', 'model.keras')
META_PATH   = os.path.join(BASE_DIR, 'saved_model', 'scaler.json')
OUTPUT_PATH = os.path.join(BASE_DIR, 'comparison_result.csv')


def main():
    print("TensorFlow 모델 로딩 중...")
    model = tf.keras.models.load_model(MODEL_PATH)
    with open(META_PATH) as f:
        meta = json.load(f)

    x_mean = meta['x_mean']
    x_std  = meta['x_std']
    y_mean = meta['y_mean']
    y_std  = meta['y_std']
    n_days = meta['n_days']

    df = pd.read_csv(DATA_PATH)
    df['date'] = pd.to_datetime(df['date']).dt.date
    df = df.sort_values('date').reset_index(drop=True)
    last_date = df['date'].iloc[-1]

    # 미래 13일 인덱스 예측
    N_DAYS = 13
    future_idx    = np.arange(n_days, n_days + N_DAYS, dtype=np.float32)
    future_idx_sc = (future_idx - x_mean) / x_std
    pred_sc       = model.predict(future_idx_sc.reshape(-1, 1), verbose=0).flatten()
    pred_prices   = pred_sc * y_std + y_mean
    pred_dates    = [last_date + timedelta(days=i + 1) for i in range(N_DAYS)]

    actual_df  = pd.read_csv(ACTUAL_PATH)
    actual_df['date'] = pd.to_datetime(actual_df['date']).dt.date
    actual_map = dict(zip(actual_df['date'], actual_df['price']))

    rows = []
    for d, p in zip(pred_dates, pred_prices):
        p = max(1000, round(float(p)))
        actual      = actual_map.get(d)
        error       = (actual - p) if actual else None
        error_pct   = round(error / actual * 100, 2) if actual else None
        abs_err_pct = round(abs(error) / actual * 100, 2) if actual else None
        rows.append({
            'date':          d.isoformat(),
            'predicted':     p,
            'actual':        actual,
            'error':         round(error) if error is not None else None,
            'error_pct':     error_pct,
            'abs_error_pct': abs_err_pct,
        })

    result = pd.DataFrame(rows)
    result.to_csv(OUTPUT_PATH, index=False, encoding='utf-8-sig')

    compared = result.dropna(subset=['actual'])
    mae  = compared['error'].abs().mean()
    mape = compared['abs_error_pct'].mean()

    print("=" * 60)
    print("Samsung DDR5 16GB  예측값 vs 실제값 비교")
    print(f"기준일: {last_date}  |  비교 기간: {pred_dates[0]} ~ {pred_dates[-1]}")
    print("=" * 60)
    print(f"{'날짜':^12} {'예측(원)':>10} {'실제(원)':>10} {'오차(원)':>10} {'오차율':>8}")
    print("-" * 60)
    for _, r in result.iterrows():
        if r['actual'] is not None:
            print(f"{r['date']:^12} {int(r['predicted']):>10,} {int(r['actual']):>10,} "
                  f"{int(r['error']):>+10,} {r['error_pct']:>+7.2f}%")
    print("=" * 60)
    print(f"MAE  (평균절대오차):   {mae:,.0f} 원")
    print(f"MAPE (평균절대오차율): {mape:.2f} %")
    print(f"\n결과 저장: {OUTPUT_PATH}")


if __name__ == '__main__':
    main()
