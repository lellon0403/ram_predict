"""
Samsung DDR5 16GB RAM 가격 예측 모델 - 추론 스크립트
알고리즘: TensorFlow Keras 단일 변수 선형 회귀

예측 흐름:
  1. 저장된 model.keras 로드
  2. 미래 날짜 인덱스 X 생성 → 정규화
  3. 모델 예측 → 역정규화 → 원화 가격 반환
  4. 90일 예측 완성 후 1주일/1개월/3개월 지점 추출
"""

import os
import json
import warnings
import numpy as np
import pandas as pd
import tensorflow as tf

warnings.filterwarnings('ignore')

from datetime import date, timedelta


#######
# 경로 설정
#######
MODEL_DIR   = os.path.join(os.path.dirname(__file__), '..', 'saved_model', 'linear')
DATA_PATH   = os.path.join(os.path.dirname(__file__), '..', 'data', 'train', 'ram_prices.csv')
MODEL_PATH  = os.path.join(MODEL_DIR, 'model.keras')
META_PATH   = os.path.join(MODEL_DIR, 'scaler.json')

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
        _model = tf.keras.models.load_model(MODEL_PATH)
        with open(META_PATH) as f:
            _meta = json.load(f)
    return _model, _meta


def get_predictions() -> dict:
    """
    반환 구조:
    {
      "history":  [{"date": "YYYY-MM-DD", "price": 82000}, ...],
      "forecast": [{"date": "YYYY-MM-DD", "price": 325000}, ...],   // 90일 일별
      "predictions": {
          "1week":   {"date": "YYYY-MM-DD", "price": ...},
          "1month":  {"date": "YYYY-MM-DD", "price": ...},
          "3months": {"date": "YYYY-MM-DD", "price": ...},
      }
    }
    """
    #######
    # 1단계: 모델 및 메타데이터 로드
    #######
    model, meta = _load_artifacts()

    x_mean = meta['x_mean']
    x_std  = meta['x_std']
    y_mean = meta['y_mean']
    y_std  = meta['y_std']
    n_days = meta['n_days']   # 학습 데이터 총 일수 (0 ~ n_days-1)

    #######
    # 2단계: 가격 데이터 CSV 로드
    #######
    df = pd.read_csv(DATA_PATH)
    df['date'] = pd.to_datetime(df['date'])
    df = df.sort_values('date').reset_index(drop=True)
    last_date = df['date'].iloc[-1].date()

    #######
    # 3단계: 미래 90일 인덱스 생성 및 정규화
    # 학습 마지막 인덱스 = n_days - 1
    # 예측 인덱스 = n_days, n_days+1, ..., n_days+89
    #######
    future_idx = np.arange(n_days, n_days + 90, dtype=np.float32)
    future_idx_sc = (future_idx - x_mean) / x_std

    #######
    # 4단계: 모델 예측 → 역정규화 → 원화 가격
    #######
    pred_sc     = model.predict(future_idx_sc.reshape(-1, 1), verbose=0).flatten()
    pred_prices = pred_sc * y_std + y_mean   # 역정규화

    forecast_dates = [last_date + timedelta(days=i + 1) for i in range(90)]

    #######
    # 5단계: 예측 결과 딕셔너리 구성
    #######
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
