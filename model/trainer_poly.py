"""
Samsung DDR5 16GB RAM 가격 예측 모델 - 다항 회귀 학습 스크립트
알고리즘: TensorFlow Keras 2차 다항 회귀 (Polynomial Regression)

입력 구조:
  X = [x_sc, x_sc²]  → 정규화된 날짜 인덱스와 그 제곱
  y = 해당 날의 가격 (정규화)
  모델: Dense(1, linear) → H(x) = W₁*x_sc + W₂*x_sc² + b
"""

import os
import json
import warnings
import numpy as np
import pandas as pd

warnings.filterwarnings('ignore')

import tensorflow as tf
from tensorflow import keras

EPOCHS     = 2000
BATCH_SIZE = 32
LR         = 1e-3

DATA_PATH  = os.path.join(os.path.dirname(__file__), '..', 'data', 'train', 'ram_prices.csv')
MODEL_DIR  = os.path.join(os.path.dirname(__file__), '..', 'saved_model', 'ram', 'polynomial')
MODEL_PATH = os.path.join(MODEL_DIR, 'model.keras')
META_PATH  = os.path.join(MODEL_DIR, 'scaler.json')


def build_model() -> keras.Model:
    model = keras.Sequential([
        keras.layers.Input(shape=(2,)),      # 입력: [x_sc, x_sc²]
        keras.layers.Dense(
            units=1,
            activation='linear',
            name='poly_output'
        ),
    ], name='ram_poly_predictor')

    model.compile(
        optimizer=keras.optimizers.Adam(learning_rate=LR),
        loss='mse',
        metrics=['mae'],
    )
    return model


def train():
    print("=" * 60)
    print("Samsung DDR5 16GB 가격 예측 모델 학습 시작 (다항 회귀)")
    print(f"TensorFlow 버전: {tf.__version__}")
    print("알고리즘: TensorFlow Keras 2차 다항 회귀")
    print("=" * 60)

    df = pd.read_csv(DATA_PATH)
    df['date'] = pd.to_datetime(df['date'])
    df = df.sort_values('date').reset_index(drop=True)
    prices = df['price'].values.astype(np.float32)

    print(f"데이터 기간: {df['date'].min().date()} ~ {df['date'].max().date()}")
    print(f"총 {len(prices)}일, 가격 범위: {prices.min():,.0f} ~ {prices.max():,.0f} 원")

    # X 생성 및 정규화
    x_data = np.arange(len(prices), dtype=np.float32)
    y_data = prices.copy()

    x_mean = float(x_data.mean())
    x_std  = float(x_data.std())
    y_mean = float(y_data.mean())
    y_std  = float(y_data.std())

    x_sc = (x_data - x_mean) / x_std     # 정규화된 x
    X    = np.stack([x_sc, x_sc ** 2], axis=1)   # [x_sc, x_sc²]
    y_sc = (y_data - y_mean) / y_std

    # Train / Validation 분리
    split   = int(len(X) * 0.8)
    X_train = X[:split]
    X_val   = X[split:]
    y_train = y_sc[:split]
    y_val   = y_sc[split:]

    print(f"학습 샘플: {len(X_train)}, 검증 샘플: {len(X_val)}")

    model = build_model()
    model.summary()

    callbacks = [
        keras.callbacks.EarlyStopping(
            monitor='val_loss',
            patience=100,
            restore_best_weights=True,
            verbose=1
        ),
        keras.callbacks.ReduceLROnPlateau(
            monitor='val_loss',
            factor=0.5,
            patience=50,
            min_lr=1e-6,
            verbose=1
        ),
    ]

    history = model.fit(
        X_train, y_train,
        validation_data=(X_val, y_val),
        epochs=EPOCHS,
        batch_size=BATCH_SIZE,
        callbacks=callbacks,
        verbose=1,
    )

    best_epoch  = int(np.argmin(history.history['val_loss']))
    val_mae_sc  = history.history['val_mae'][best_epoch]
    val_mae_krw = val_mae_sc * y_std

    meta = {
        'x_mean':     x_mean,
        'x_std':      x_std,
        'y_mean':     y_mean,
        'y_std':      y_std,
        'n_days':     int(len(prices)),
        'last_price': float(prices[-1]),
        'model_type': 'polynomial',
    }

    os.makedirs(MODEL_DIR, exist_ok=True)
    model.save(MODEL_PATH)
    with open(META_PATH, 'w') as f:
        json.dump(meta, f)

    print("\n" + "=" * 60)
    print("학습 완료! (다항 회귀)")
    print(f"최적 에포크: {best_epoch + 1} / {EPOCHS}")
    print(f"검증 MAE (원화): ±{abs(val_mae_krw):,.0f} 원")
    print(f"모델 저장: {MODEL_PATH}")
    print("=" * 60)

    return model, meta


if __name__ == '__main__':
    train()
