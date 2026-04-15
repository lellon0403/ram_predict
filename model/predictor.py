"""
학습된 모델을 로드하여 1주일 / 1개월 / 3개월 뒤 가격 예측
"""

import os
import json
import numpy as np
import pandas as pd
import tensorflow as tf
from datetime import date, timedelta

MODEL_DIR   = os.path.join(os.path.dirname(__file__), '..', 'saved_model')
DATA_PATH   = os.path.join(os.path.dirname(__file__), '..', 'data', 'ram_prices.csv')
WINDOW_SIZE = 30


# ── 스케일러 ───────────────────────────────────────────────────────────────────
def _scale(values, scaler):
    return (values - scaler['min']) / (scaler['max'] - scaler['min'] + 1e-9)


def _unscale(values, scaler):
    return values * (scaler['max'] - scaler['min'] + 1e-9) + scaler['min']


# ── 모델 로더 (싱글톤) ─────────────────────────────────────────────────────────
_model  = None
_scaler = None


def _load_artifacts():
    global _model, _scaler
    if _model is None:
        model_path  = os.path.join(MODEL_DIR, 'model.keras')
        scaler_path = os.path.join(MODEL_DIR, 'scaler.json')

        if not os.path.exists(model_path):
            raise FileNotFoundError(
                f"모델 파일이 없습니다: {model_path}\n"
                "먼저 `python model/trainer.py` 를 실행하세요."
            )

        _model = tf.keras.models.load_model(model_path)

        with open(scaler_path) as f:
            _scaler = json.load(f)

    return _model, _scaler


# ── 핵심 예측 함수 ─────────────────────────────────────────────────────────────
def _predict_n_days(model, scaler, last_window: np.ndarray, n: int) -> list[float]:
    """
    last_window: 정규화된 최근 WINDOW_SIZE 일 가격 배열
    n          : 예측할 날 수
    반환       : n 일간 예측 가격(원화) 리스트
    """
    window = last_window.copy().astype(np.float32)
    results = []

    for _ in range(n):
        x = window[-WINDOW_SIZE:].reshape(1, WINDOW_SIZE)
        pred_scaled = float(model.predict(x, verbose=0)[0][0])
        pred_price  = float(_unscale(np.array([pred_scaled]), scaler)[0])
        results.append(pred_price)
        window = np.append(window, pred_scaled)

    return results


# ── 공개 API ───────────────────────────────────────────────────────────────────
def get_predictions() -> dict:
    """
    반환 구조:
    {
      "history":     [{"date": "YYYY-MM-DD", "price": 82000}, ...],
      "forecast":    [{"date": "YYYY-MM-DD", "price": 47200}, ...],  # 90일치 일별
      "predictions": {
          "1week":   {"date": "YYYY-MM-DD", "price": 47200},
          "1month":  {"date": "YYYY-MM-DD", "price": 45800},
          "3months": {"date": "YYYY-MM-DD", "price": 43100},
      }
    }
    """
    model, scaler = _load_artifacts()

    # 히스토리 로드
    df = pd.read_csv(DATA_PATH)
    df['date'] = pd.to_datetime(df['date'])
    df = df.sort_values('date').reset_index(drop=True)

    prices      = df['price'].values.astype(np.float32)
    prices_sc   = _scale(prices, scaler)
    last_window = prices_sc[-WINDOW_SIZE:]
    last_date   = df['date'].iloc[-1].date()

    # 90일(3개월) 예측
    forecast_prices = _predict_n_days(model, scaler, last_window, 90)

    # 날짜 생성
    forecast_dates = [last_date + timedelta(days=i + 1) for i in range(90)]

    # 일별 예측 리스트
    forecast = [
        {"date": d.isoformat(), "price": round(p)}
        for d, p in zip(forecast_dates, forecast_prices)
    ]

    # 포인트 예측
    def pick(days):
        return {
            "date":  forecast_dates[days - 1].isoformat(),
            "price": round(forecast_prices[days - 1]),
        }

    return {
        "history":  [
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
