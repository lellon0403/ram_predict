"""
Samsung DDR5 16GB RAM 가격 예측 모델 학습 스크립트
선형 예측 알고리즘 (Linear Regression + Polynomial Features)

스케일링: 로그 변환(log-price) 사용
  - 가격이 47,000원 → 320,000원으로 약 7배 폭등한 비선형 데이터에서도
    log 스케일에서는 변화율이 균일해져 선형 회귀가 안정적으로 동작함

NOTE: TensorFlow 는 Python 3.14를 아직 지원하지 않으므로 scikit-learn 사용.
      Python 3.12 환경이 준비되면 tensorflow_trainer.py 로 전환하세요.
"""

import os
import json
import numpy as np
import pandas as pd
import joblib
from sklearn.linear_model import Ridge
from sklearn.preprocessing import PolynomialFeatures, StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.metrics import mean_absolute_error

# ── 설정 ──────────────────────────────────────────────────────────────────────
WINDOW_SIZE  = 30
POLY_DEGREE  = 2
DATA_PATH    = os.path.join(os.path.dirname(__file__), '..', 'data', 'ram_prices.csv')
MODEL_DIR    = os.path.join(os.path.dirname(__file__), '..', 'saved_model')
MODEL_PATH   = os.path.join(MODEL_DIR, 'model.joblib')
SCALER_PATH  = os.path.join(MODEL_DIR, 'scaler.json')


def make_dataset(log_prices: np.ndarray, window: int):
    X, y = [], []
    for i in range(len(log_prices) - window):
        X.append(log_prices[i: i + window])
        y.append(log_prices[i + window])
    return np.array(X, dtype=np.float64), np.array(y, dtype=np.float64)


def train():
    print("=" * 60)
    print("Samsung DDR5 16GB 가격 예측 모델 학습 시작")
    print(f"알고리즘: Log-scale + Polynomial(degree={POLY_DEGREE}) + Ridge Regression")
    print("=" * 60)

    df = pd.read_csv(DATA_PATH)
    df['date'] = pd.to_datetime(df['date'])
    df = df.sort_values('date').reset_index(drop=True)
    prices = df['price'].values.astype(np.float64)

    print(f"데이터 기간: {df['date'].min().date()} ~ {df['date'].max().date()}")
    print(f"총 {len(prices)}일 데이터, 가격 범위: {prices.min():,.0f} ~ {prices.max():,.0f} 원")

    # 로그 변환 후 MinMax 정규화
    log_prices = np.log(prices)
    scaler_params = {
        'log_min': float(log_prices.min()),
        'log_max': float(log_prices.max()),
    }
    rng = scaler_params['log_max'] - scaler_params['log_min']
    prices_sc = (log_prices - scaler_params['log_min']) / rng

    X, y = make_dataset(prices_sc, WINDOW_SIZE)

    split = int(len(X) * 0.8)
    X_train, X_val = X[:split], X[split:]
    y_train, y_val = y[:split], y[split:]
    print(f"학습 샘플: {len(X_train)}, 검증 샘플: {len(X_val)}")

    model = Pipeline([
        ('poly',  PolynomialFeatures(degree=POLY_DEGREE, include_bias=True)),
        ('scl',   StandardScaler()),
        ('ridge', Ridge(alpha=1.0)),
    ])
    model.fit(X_train, y_train)

    # 검증 (원화 기준 MAE 계산)
    y_pred_sc = model.predict(X_val)
    y_pred = np.exp(y_pred_sc * rng + scaler_params['log_min'])
    y_true = np.exp(y_val    * rng + scaler_params['log_min'])
    mae    = mean_absolute_error(y_true, y_pred)

    os.makedirs(MODEL_DIR, exist_ok=True)
    joblib.dump(model, MODEL_PATH)
    with open(SCALER_PATH, 'w') as f:
        json.dump(scaler_params, f)

    print("\n" + "=" * 60)
    print("학습 완료!")
    print(f"검증 MAE: ±{mae:,.0f} 원")
    print(f"모델 저장: {MODEL_PATH}")
    print("=" * 60)

    return model, scaler_params


if __name__ == '__main__':
    train()
