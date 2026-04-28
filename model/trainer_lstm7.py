"""
Samsung DDR5 16GB RAM 가격 예측 모델 - LSTM-7 학습 스크립트

슬라이딩 윈도우 방식:
  입력: 최근 WINDOW_SIZE 일치 가격 시퀀스
  출력: 다음 날 가격
  모델: LSTM(64) → LSTM(32) → Dense(1)
"""

import os
import json
import warnings
import numpy as np
import pandas as pd

warnings.filterwarnings('ignore')

import tensorflow as tf
from tensorflow import keras

EPOCHS      = 200
BATCH_SIZE  = 16
LR          = 1e-3
WINDOW_SIZE = 7     # 과거 30일을 보고 다음날 예측

DATA_PATH  = os.path.join(os.path.dirname(__file__), '..', 'data', 'train', 'ram_prices.csv')
MODEL_DIR  = os.path.join(os.path.dirname(__file__), '..', 'saved_model/lstm7')
MODEL_PATH = os.path.join(MODEL_DIR, 'model.keras')
META_PATH  = os.path.join(MODEL_DIR, 'scaler.json')


def make_sequences(prices_sc: np.ndarray, window: int):
    """슬라이딩 윈도우로 (X, y) 시퀀스 생성"""
    X, y = [], []
    for i in range(len(prices_sc) - window):
        X.append(prices_sc[i: i + window])
        y.append(prices_sc[i + window])
    return np.array(X, dtype=np.float32), np.array(y, dtype=np.float32)


def build_model(window: int) -> keras.Model:
    model = keras.Sequential([
        keras.layers.Input(shape=(window, 1)),
        keras.layers.LSTM(64, return_sequences=True),
        keras.layers.LSTM(32),
        keras.layers.Dense(1),
    ], name='ram_lstm7_predictor')

    model.compile(
        optimizer=keras.optimizers.Adam(learning_rate=LR),
        loss='mse',
        metrics=['mae'],
    )
    return model


def train():
    print("=" * 60)
    print("Samsung DDR5 16GB 가격 예측 모델 학습 시작 (LSTM)")
    print(f"TensorFlow 버전: {tf.__version__}")
    print(f"윈도우 크기: {WINDOW_SIZE}일")
    print("=" * 60)

    df = pd.read_csv(DATA_PATH)
    df['date'] = pd.to_datetime(df['date'])
    df = df.sort_values('date').reset_index(drop=True)
    prices = df['price'].values.astype(np.float32)

    print(f"데이터 기간: {df['date'].min().date()} ~ {df['date'].max().date()}")
    print(f"총 {len(prices)}일, 가격 범위: {prices.min():,.0f} ~ {prices.max():,.0f} 원")

    # 정규화 (가격만)
    y_mean = float(prices.mean())
    y_std  = float(prices.std())
    prices_sc = (prices - y_mean) / y_std

    # 슬라이딩 윈도우 시퀀스 생성
    X, y = make_sequences(prices_sc, WINDOW_SIZE)
    X = X.reshape(-1, WINDOW_SIZE, 1)   # LSTM 입력: (samples, timesteps, features)

    # Train / Val 분리 (시간 순서 유지)
    split   = int(len(X) * 0.8)
    X_train = X[:split];  X_val = X[split:]
    y_train = y[:split];  y_val = y[split:]

    print(f"학습 샘플: {len(X_train)}, 검증 샘플: {len(X_val)}")

    model = build_model(WINDOW_SIZE)
    model.summary()

    callbacks = [
        keras.callbacks.EarlyStopping(
            monitor='val_loss',
            patience=20,
            restore_best_weights=True,
            verbose=1
        ),
        keras.callbacks.ReduceLROnPlateau(
            monitor='val_loss',
            factor=0.5,
            patience=10,
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
        'y_mean':      y_mean,
        'y_std':       y_std,
        'n_days':      int(len(prices)),
        'last_price':  float(prices[-1]),
        'window_size': WINDOW_SIZE,
        'model_type':  'lstm',
        # 예측에 필요한 마지막 30일 가격 저장
        'last_window': prices[-WINDOW_SIZE:].tolist(),
    }

    os.makedirs(MODEL_DIR, exist_ok=True)
    model.save(MODEL_PATH)
    with open(META_PATH, 'w') as f:
        json.dump(meta, f)

    print("\n" + "=" * 60)
    print("학습 완료! (LSTM)")
    print(f"최적 에포크: {best_epoch + 1} / {EPOCHS}")
    print(f"검증 MAE (원화): ±{abs(val_mae_krw):,.0f} 원")
    print(f"모델 저장: {MODEL_PATH}")
    print("=" * 60)

    return model, meta


if __name__ == '__main__':
    train()
