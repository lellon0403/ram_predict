"""
학습된 모델로 1주일 / 1개월 / 3개월 뒤 가격 예측 (로그 스케일 버전)
"""

import os
import json
import numpy as np
import pandas as pd
import joblib
from datetime import date, timedelta

MODEL_DIR   = os.path.join(os.path.dirname(__file__), '..', 'saved_model')
DATA_PATH   = os.path.join(os.path.dirname(__file__), '..', 'data', 'ram_prices.csv')
MODEL_PATH  = os.path.join(MODEL_DIR, 'model.joblib')
SCALER_PATH = os.path.join(MODEL_DIR, 'scaler.json')
WINDOW_SIZE = 30

_model  = None
_scaler = None


def _load_artifacts():
    global _model, _scaler
    if _model is None:
        if not os.path.exists(MODEL_PATH):
            raise FileNotFoundError(
                f"모델 파일이 없습니다: {MODEL_PATH}\n"
                "먼저 POST /retrain 또는 `python model/trainer.py` 를 실행하세요."
            )
        _model = joblib.load(MODEL_PATH)
        with open(SCALER_PATH) as f:
            _scaler = json.load(f)
    return _model, _scaler


def _predict_n_days(model, scaler, last_window_sc: np.ndarray, n: int) -> list:
    """로그 스케일 슬라이딩 윈도우로 n일 예측, 원화로 변환하여 반환"""
    window = last_window_sc.copy()
    results = []
    log_min = scaler['log_min']
    log_max = scaler['log_max']
    rng     = log_max - log_min

    for _ in range(n):
        x = window[-WINDOW_SIZE:].reshape(1, -1)
        pred_sc = float(model.predict(x)[0])
        pred_sc = max(0.0, min(1.2, pred_sc))       # 범위 클리핑 (약간의 여유)
        pred_log   = pred_sc * rng + log_min
        pred_price = float(np.exp(pred_log))
        results.append(pred_price)
        window = np.append(window, pred_sc)

    return results


def get_predictions() -> dict:
    """
    반환 구조:
    {
      "history":  [{"date": "YYYY-MM-DD", "price": 82000}, ...],
      "forecast": [{"date": "YYYY-MM-DD", "price": 325000}, ...],  # 90일 일별
      "predictions": {
          "1week":   {"date": "YYYY-MM-DD", "price": 325000},
          "1month":  {"date": "YYYY-MM-DD", "price": 335000},
          "3months": {"date": "YYYY-MM-DD", "price": 350000},
      }
    }
    """
    model, scaler = _load_artifacts()

    df = pd.read_csv(DATA_PATH)
    df['date'] = pd.to_datetime(df['date'])
    df = df.sort_values('date').reset_index(drop=True)

    prices  = df['price'].values.astype(np.float64)
    log_min = scaler['log_min']
    log_max = scaler['log_max']
    rng     = log_max - log_min

    log_prices = np.log(prices)
    prices_sc  = (log_prices - log_min) / rng

    last_window = prices_sc[-WINDOW_SIZE:]
    last_date   = df['date'].iloc[-1].date()

    forecast_prices = _predict_n_days(model, scaler, last_window, 90)
    forecast_dates  = [last_date + timedelta(days=i + 1) for i in range(90)]

    forecast = [
        {"date": d.isoformat(), "price": round(p)}
        for d, p in zip(forecast_dates, forecast_prices)
    ]

    def pick(days):
        return {
            "date":  forecast_dates[days - 1].isoformat(),
            "price": round(forecast_prices[days - 1]),
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
