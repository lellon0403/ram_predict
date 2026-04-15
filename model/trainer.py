"""
Samsung DDR5 16GB RAM 가격 예측 모델 학습 스크립트
선형 예측 알고리즘 (Log-return Linear Regression)

핵심 아이디어:
  - 가격 수준(level)이 아니라 전일 대비 변화율(log-return)을 예측
  - r_t = ln(price_t) - ln(price_{t-1})
  - 스케일 불변 → 저가(48K)와 고가(320K) 구간 모두 균일하게 학습
  - 예측 시 마지막 실제 가격에 누적 수익률을 적용하여 원화 환산

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
from sklearn.preprocessing import PolynomialFeatures, StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.metrics import mean_absolute_error

WINDOW_SIZE  = 30
POLY_DEGREE  = 2
DATA_PATH    = os.path.join(os.path.dirname(__file__), '..', 'data', 'ram_prices.csv')
MODEL_DIR    = os.path.join(os.path.dirname(__file__), '..', 'saved_model')
MODEL_PATH   = os.path.join(MODEL_DIR, 'model.joblib')
META_PATH    = os.path.join(MODEL_DIR, 'scaler.json')


def make_dataset(returns: np.ndarray, window: int):
    X, y = [], []
    for i in range(len(returns) - window):
        X.append(returns[i: i + window])
        y.append(returns[i + window])
    return np.array(X, dtype=np.float64), np.array(y, dtype=np.float64)


def train():
    print("=" * 60)
    print("Samsung DDR5 16GB 가격 예측 모델 학습 시작")
    print(f"알고리즘: Log-return + Polynomial(degree={POLY_DEGREE}) + Ridge")
    print("=" * 60)

    df = pd.read_csv(DATA_PATH)
    df['date'] = pd.to_datetime(df['date'])
    df = df.sort_values('date').reset_index(drop=True)
    prices = df['price'].values.astype(np.float64)

    print(f"데이터 기간: {df['date'].min().date()} ~ {df['date'].max().date()}")
    print(f"총 {len(prices)}일, 가격 범위: {prices.min():,.0f} ~ {prices.max():,.0f} 원")

    # 로그 수익률: r_t = ln(p_t) - ln(p_{t-1})
    log_returns = np.diff(np.log(prices))          # 길이 N-1

    # 정규화 파라미터 (로그 수익률의 mean/std)
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

    model = Pipeline([
        ('poly',  PolynomialFeatures(degree=POLY_DEGREE, include_bias=True)),
        ('scl',   StandardScaler()),
        ('ridge', Ridge(alpha=0.5)),
    ])
    model.fit(X_train, y_train)

    # 검증 MAE (원화 환산)
    # 검증 구간의 실제 가격 추출 (window+split 번째 이후)
    val_start_idx = split + WINDOW_SIZE + 1   # +1 은 returns 의 오프셋
    actual_prices = prices[val_start_idx: val_start_idx + len(y_val)]

    y_pred_sc  = model.predict(X_val)
    pred_log_r = y_pred_sc * ret_std + ret_mean
    true_log_r = y_val     * ret_std + ret_mean

    # 이전 실제가격에 예측 수익률 적용
    prev_prices = prices[val_start_idx - 1: val_start_idx - 1 + len(y_val)]
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
