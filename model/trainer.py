"""
Samsung DDR5 16GB RAM 가격 예측 모델 학습 스크립트
알고리즘: 선형 예측 모델 (Linear Regression)

구조:
  1. 가격을 로그 수익률로 변환  r_t = ln(p_t) - ln(p_{t-1})
  2. 최근 30일 수익률 → 다음날 수익률 예측  (슬라이딩 윈도우)
  3. 모델: StandardScaler + Ridge(alpha=0.5)
       - PolynomialFeatures 없음 → 입력과 출력이 선형 관계 유지
       - Ridge = 정규화(L2) 선형 회귀 → 과적합 방지

NOTE: Python 3.14는 TensorFlow 미지원 → scikit-learn 사용
"""

import os
import json
import warnings
import numpy as np
warnings.filterwarnings('ignore', category=RuntimeWarning)
import pandas as pd
import joblib
from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.metrics import mean_absolute_error

WINDOW_SIZE = 30
DATA_PATH   = os.path.join(os.path.dirname(__file__), '..', 'data', 'ram_prices.csv')
MODEL_DIR   = os.path.join(os.path.dirname(__file__), '..', 'saved_model')
MODEL_PATH  = os.path.join(MODEL_DIR, 'model.joblib')
META_PATH   = os.path.join(MODEL_DIR, 'scaler.json')


def make_dataset(returns: np.ndarray, window: int):
    X, y = [], []
    for i in range(len(returns) - window):
        X.append(returns[i: i + window])
        y.append(returns[i + window])
    return np.array(X, dtype=np.float64), np.array(y, dtype=np.float64)


def train():
    print("=" * 60)
    print("Samsung DDR5 16GB 가격 예측 모델 학습 시작")
    print("알고리즘: 선형 예측 모델 (Log-return + StandardScaler + Ridge)")
    print("=" * 60)

    df = pd.read_csv(DATA_PATH)
    df['date'] = pd.to_datetime(df['date'])
    df = df.sort_values('date').reset_index(drop=True)
    prices = df['price'].values.astype(np.float64)

    print(f"데이터 기간: {df['date'].min().date()} ~ {df['date'].max().date()}")
    print(f"총 {len(prices)}일, 가격 범위: {prices.min():,.0f} ~ {prices.max():,.0f} 원")

    # 로그 수익률: r_t = ln(p_t) - ln(p_{t-1})
    log_returns = np.diff(np.log(prices))

    ret_mean = float(log_returns.mean())
    ret_std  = float(log_returns.std())
    returns_sc = (log_returns - ret_mean) / (ret_std + 1e-9)

    meta = {
        'ret_mean':   ret_mean,
        'ret_std':    ret_std,
        'last_price': float(prices[-1]),
    }

    X, y = make_dataset(returns_sc, WINDOW_SIZE)

    split = int(len(X) * 0.8)
    X_train, X_val = X[:split], X[split:]
    y_train, y_val = y[:split], y[split:]
    print(f"학습 샘플: {len(X_train)}, 검증 샘플: {len(X_val)}")

    # 선형 모델: StandardScaler → Ridge (PolynomialFeatures 없음)
    model = Pipeline([
        ('scl',   StandardScaler()),
        ('ridge', Ridge(alpha=0.5)),
    ])
    model.fit(X_train, y_train)

    # 검증 MAE (원화 환산)
    val_start_idx = split + WINDOW_SIZE + 1
    actual_prices = prices[val_start_idx: val_start_idx + len(y_val)]
    prev_prices   = prices[val_start_idx - 1: val_start_idx - 1 + len(y_val)]

    y_pred_sc   = model.predict(X_val)
    pred_log_r  = y_pred_sc * ret_std + ret_mean
    pred_prices = prev_prices * np.exp(pred_log_r)
    mae = mean_absolute_error(actual_prices, pred_prices)

    os.makedirs(MODEL_DIR, exist_ok=True)
    joblib.dump(model, MODEL_PATH)
    with open(META_PATH, 'w') as f:
        json.dump(meta, f)

    print("\n" + "=" * 60)
    print("학습 완료!")
    print(f"검증 MAE: ±{mae:,.0f} 원")
    print(f"모델 저장: {MODEL_PATH}")
    print("=" * 60)

    return model, meta


if __name__ == '__main__':
    train()
