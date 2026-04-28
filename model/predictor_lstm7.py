"""
Samsung DDR5 16GB RAM 가격 예측 모델 - LSTM 추론 스크립트

롤링 예측 방식:
  마지막 30일 실제 가격 → 내일 예측
  → 예측값을 윈도우에 추가 → 모레 예측
  → 반복하여 90일 예측
"""

import os
import json
import warnings
import numpy as np
import pandas as pd
import tensorflow as tf

warnings.filterwarnings('ignore')

from datetime import date, timedelta

MODEL_DIR  = os.path.join(os.path.dirname(__file__), '..', 'saved_model/lstm7')
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
                f"LSTM 모델 없음: {MODEL_PATH}\n"
                "먼저 `python model/trainer_lstm7.py` 실행"
            )
        _model = tf.keras.models.load_model(MODEL_PATH)
        with open(META_PATH) as f:
            _meta = json.load(f)
    return _model, _meta


def get_predictions() -> dict:
    model, meta = _load_artifacts()

    y_mean      = meta['y_mean']
    y_std       = meta['y_std']
    window_size = meta['window_size']
    last_window = np.array(meta['last_window'], dtype=np.float32)

    df = pd.read_csv(DATA_PATH)
    df['date'] = pd.to_datetime(df['date'])
    df = df.sort_values('date').reset_index(drop=True)
    last_date = df['date'].iloc[-1].date()

    # 롤링 예측: 마지막 window_size 일 → 90일 예측
    window_sc    = (last_window - y_mean) / y_std
    pred_prices  = []

    for _ in range(90):
        x_input  = window_sc[-window_size:].reshape(1, window_size, 1)
        pred_sc  = model.predict(x_input, verbose=0)[0][0]
        pred_krw = pred_sc * y_std + y_mean
        pred_prices.append(max(1000, round(float(pred_krw))))
        window_sc = np.append(window_sc, pred_sc)

    forecast_dates = [last_date + timedelta(days=i + 1) for i in range(90)]

    forecast = [
        {"date": d.isoformat(), "price": p}
        for d, p in zip(forecast_dates, pred_prices)
    ]

    def pick(days):
        return {
            "date":  forecast_dates[days - 1].isoformat(),
            "price": pred_prices[days - 1],
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
