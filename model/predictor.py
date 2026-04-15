"""
학습된 모델을 로드하여 1주일 / 1개월 / 3개월 뒤 가격 예측
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


# ── 싱글톤 캐시 ───────────────────────────────────────────────────────────────
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


# ── 예측 ──────────────────────────────────────────────────────────────────────
def _predict_n_days(model, scaler, last_window_sc: np.ndarray, n: int) -> list:
    """
    슬라이딩 윈도우로 n일 뒤까지 순차 예측
    last_window_sc: 정규화된 최근 WINDOW_SIZE 일 가격
    반환: 원화 가격 리스트 (길이 n)
    """
    window = last_window_sc.copy()
    results = []
    mn, mx = scaler['min'], scaler['max']

    for _ in range(n):
        x = window[-WINDOW_SIZE:].reshape(1, -1)
        pred_sc = float(model.predict(x)[0])
        pred_sc = max(0.0, min(1.0, pred_sc))          # 범위 클리핑
        pred_price = pred_sc * (mx - mn) + mn
        results.append(pred_price)
        window = np.append(window, pred_sc)

    return results


# ── 공개 API ───────────────────────────────────────────────────────────────────
def get_predictions() -> dict:
    """
    반환 구조:
    {
      "history":  [{"date": "YYYY-MM-DD", "price": 82000}, ...],
      "forecast": [{"date": "YYYY-MM-DD", "price": 47200}, ...],   # 90일 일별
      "predictions": {
          "1week":   {"date": "YYYY-MM-DD", "price": 47200},
          "1month":  {"date": "YYYY-MM-DD", "price": 45800},
          "3months": {"date": "YYYY-MM-DD", "price": 43100},
      }
    }
    """
    model, scaler = _load_artifacts()

    df = pd.read_csv(DATA_PATH)
    df['date'] = pd.to_datetime(df['date'])
    df = df.sort_values('date').reset_index(drop=True)

    prices    = df['price'].values.astype(np.float64)
    mn, mx    = scaler['min'], scaler['max']
    prices_sc = (prices - mn) / (mx - mn)

    last_window = prices_sc[-WINDOW_SIZE:]
    last_date   = df['date'].iloc[-1].date()

    # 90일 예측
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
