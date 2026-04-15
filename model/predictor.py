"""
학습된 Log-return 모델로 1주일 / 1개월 / 3개월 뒤 가격 예측
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
META_PATH   = os.path.join(MODEL_DIR, 'scaler.json')
WINDOW_SIZE = 30

_model = None
_meta  = None


def _load_artifacts():
    global _model, _meta
    if _model is None:
        if not os.path.exists(MODEL_PATH):
            raise FileNotFoundError(
                f"모델 없음: {MODEL_PATH}\n"
                "먼저 POST /retrain 또는 `python model/trainer.py` 실행"
            )
        _model = joblib.load(MODEL_PATH)
        with open(META_PATH) as f:
            _meta = json.load(f)
    return _model, _meta


def _predict_n_days(model, meta, last_returns_sc: np.ndarray, last_price: float, n: int):
    """
    슬라이딩 윈도우로 n일 예측
    last_returns_sc : 정규화된 최근 WINDOW_SIZE 개 로그 수익률
    last_price      : 마지막 실제 가격 (원화)
    반환             : 예측 원화 가격 리스트 (길이 n)
    """
    window   = last_returns_sc.copy()
    price    = last_price
    results  = []
    ret_mean = meta['ret_mean']
    ret_std  = meta['ret_std']

    for _ in range(n):
        # 입력 클리핑: polynomial 특성이 overflow 나지 않도록 ±3 sigma 이내로 제한
        x_raw   = np.clip(window[-WINDOW_SIZE:], -3.0, 3.0).reshape(1, -1)
        r_sc    = float(model.predict(x_raw)[0])
        r_sc    = np.clip(r_sc, -3.0, 3.0)          # 출력도 클리핑
        # 역정규화 → 실제 로그 수익률
        log_ret = r_sc * ret_std + ret_mean
        # 하루 ±20% 이상 변동 차단
        log_ret = max(-0.20, min(0.20, log_ret))
        price   = price * np.exp(log_ret)
        results.append(price)
        window = np.append(window, r_sc)

    return results


def get_predictions() -> dict:
    """
    반환 구조:
    {
      "history":  [{"date": "YYYY-MM-DD", "price": 82000}, ...],
      "forecast": [{"date": "YYYY-MM-DD", "price": 325000}, ...],
      "predictions": {
          "1week":   {"date": "YYYY-MM-DD", "price": ...},
          "1month":  {"date": "YYYY-MM-DD", "price": ...},
          "3months": {"date": "YYYY-MM-DD", "price": ...},
      }
    }
    """
    model, meta = _load_artifacts()

    df = pd.read_csv(DATA_PATH)
    df['date'] = pd.to_datetime(df['date'])
    df = df.sort_values('date').reset_index(drop=True)

    prices = df['price'].values.astype(np.float64)

    # 로그 수익률 + 정규화
    log_returns = np.diff(np.log(prices))
    ret_mean    = meta['ret_mean']
    ret_std     = meta['ret_std']
    returns_sc  = (log_returns - ret_mean) / (ret_std + 1e-9)

    last_window = returns_sc[-WINDOW_SIZE:]
    last_price  = float(prices[-1])
    last_date   = df['date'].iloc[-1].date()

    forecast_prices = _predict_n_days(model, meta, last_window, last_price, 90)
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
