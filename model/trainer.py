"""
Samsung DDR5 16GB RAM 가격 예측 모델 학습 스크립트
선형 예측 알고리즘 (Linear Regression + Polynomial Features)

NOTE: TensorFlow 는 Python 3.14를 아직 지원하지 않습니다.
      scikit-learn 으로 동일한 슬라이딩 윈도우 선형 회귀를 구현합니다.
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
WINDOW_SIZE  = 30          # 최근 30일 → 다음날 예측
POLY_DEGREE  = 2           # 다항 특성 차수 (선형=1, 2차=2)
DATA_PATH    = os.path.join(os.path.dirname(__file__), '..', 'data', 'ram_prices.csv')
MODEL_DIR    = os.path.join(os.path.dirname(__file__), '..', 'saved_model')
MODEL_PATH   = os.path.join(MODEL_DIR, 'model.joblib')
SCALER_PATH  = os.path.join(MODEL_DIR, 'scaler.json')


# ── 슬라이딩 윈도우 데이터셋 ──────────────────────────────────────────────────
def make_dataset(prices: np.ndarray, window: int):
    X, y = [], []
    for i in range(len(prices) - window):
        X.append(prices[i: i + window])
        y.append(prices[i + window])
    return np.array(X, dtype=np.float64), np.array(y, dtype=np.float64)


# ── 학습 ──────────────────────────────────────────────────────────────────────
def train():
    print("=" * 60)
    print("Samsung DDR5 16GB 가격 예측 모델 학습 시작")
    print(f"알고리즘: Polynomial(degree={POLY_DEGREE}) + Ridge Regression")
    print("=" * 60)

    # 데이터 로드
    df = pd.read_csv(DATA_PATH)
    df['date'] = pd.to_datetime(df['date'])
    df = df.sort_values('date').reset_index(drop=True)
    prices = df['price'].values.astype(np.float64)

    print(f"데이터 기간: {df['date'].min().date()} ~ {df['date'].max().date()}")
    print(f"총 {len(prices)}일 데이터 로드 완료")

    # 정규화 파라미터 저장
    scaler_params = {'min': float(prices.min()), 'max': float(prices.max())}
    prices_sc = (prices - scaler_params['min']) / (scaler_params['max'] - scaler_params['min'])

    # 데이터셋 생성
    X, y = make_dataset(prices_sc, WINDOW_SIZE)

    # Train / Validation 분리 (80/20)
    split = int(len(X) * 0.8)
    X_train, X_val = X[:split], X[split:]
    y_train, y_val = y[:split], y[split:]
    print(f"학습 샘플: {len(X_train)}, 검증 샘플: {len(X_val)}")

    # Pipeline: 다항 특성 → Ridge 회귀
    model = Pipeline([
        ('poly',  PolynomialFeatures(degree=POLY_DEGREE, include_bias=True)),
        ('scl',   StandardScaler()),
        ('ridge', Ridge(alpha=1.0)),
    ])
    model.fit(X_train, y_train)

    # 검증
    y_pred_sc = model.predict(X_val)
    y_pred    = y_pred_sc * (scaler_params['max'] - scaler_params['min']) + scaler_params['min']
    y_true    = y_val    * (scaler_params['max'] - scaler_params['min']) + scaler_params['min']
    mae       = mean_absolute_error(y_true, y_pred)

    # 저장
    os.makedirs(MODEL_DIR, exist_ok=True)
    joblib.dump(model, MODEL_PATH)
    with open(SCALER_PATH, 'w') as f:
        json.dump(scaler_params, f)

    print("\n" + "=" * 60)
    print("학습 완료!")
    print(f"검증 MAE: ±{mae:,.0f} 원")
    print(f"모델 저장 위치: {MODEL_PATH}")
    print("=" * 60)

    return model, scaler_params


if __name__ == '__main__':
    train()
