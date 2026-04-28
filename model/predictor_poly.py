"""
Samsung DDR5 16GB RAM 가격 예측 모델 - 다항 회귀 추론 스크립트
입력: [x_sc, x_sc²] / 출력: 예측 가격 (원화)
"""

import os
import json
import warnings
import numpy as np
import pandas as pd
import tensorflow as tf

warnings.filterwarnings('ignore')

from datetime import date, timedelta

MODEL_DIR  = os.path.join(os.path.dirname(__file__), '..', 'saved_model', 'ram', 'polynomial')
DATA_PATH  = os.path.join(os.path.dirname(__file__), '..', 'data', 'train', 'ram_prices.csv')
MODEL_PATH = os.path.join(MODEL_DIR, 'model.keras')
META_PATH  = os.path.join(MODEL_DIR, 'scaler.json')

_model = None
_meta  = None


def _load_artifacts():
    global _model, _meta
    if _model is None:
        if not os.path.exists(MODEL_PATH):
            raise FileNotFoundError(
                f"다항 회귀 모델 없음: {MODEL_PATH}\n"
                "먼저 `python model/trainer_poly.py` 실행"
            )
        _model = tf.keras.models.load_model(MODEL_PATH)
        with open(META_PATH) as f:
            _meta = json.load(f)
    return _model, _meta


def get_predictions() -> dict:
    model, meta = _load_artifacts()

    x_mean = meta['x_mean']
    x_std  = meta['x_std']
    y_mean = meta['y_mean']
    y_std  = meta['y_std']
    n_days = meta['n_days']

    df = pd.read_csv(DATA_PATH)
    df['date'] = pd.to_datetime(df['date'])
    df = df.sort_values('date').reset_index(drop=True)
    last_date = df['date'].iloc[-1].date()

    # 미래 90일 인덱스 → 다항 피처 [x_sc, x_sc²]
    future_idx    = np.arange(n_days, n_days + 90, dtype=np.float32)
    future_idx_sc = (future_idx - x_mean) / x_std
    X_future      = np.stack([future_idx_sc, future_idx_sc ** 2], axis=1)

    pred_sc     = model.predict(X_future, verbose=0).flatten()
    pred_prices = pred_sc * y_std + y_mean

    forecast_dates = [last_date + timedelta(days=i + 1) for i in range(90)]

    forecast = [
        {"date": d.isoformat(), "price": max(1000, round(float(p)))}
        for d, p in zip(forecast_dates, pred_prices)
    ]

    def pick(days):
        return {
            "date":  forecast_dates[days - 1].isoformat(),
            "price": max(1000, round(float(pred_prices[days - 1]))),
        }

    return {
        "history": [
            {"date": row['date'].date().isoformat(), "price": int(row['price'])}
            for _, row in df.iterrows()
        ],
        "forecast":    forecast,
        "predictions": {
            "1week":   pick(7),
            "1month":  pick(30),
            "3months": pick(90),
        },
    }
