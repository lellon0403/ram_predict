"""
Samsung DDR5 16GB RAM 가격 예측 모델 학습 스크립트
선형(Linear) 레이어 기반 TensorFlow 모델
"""

import os
import numpy as np
import pandas as pd
import tensorflow as tf
import json

# ── 설정 ──────────────────────────────────────────────────────────────────────
WINDOW_SIZE = 30          # 입력 윈도우: 최근 30일 가격을 보고 다음날 예측
DATA_PATH   = os.path.join(os.path.dirname(__file__), '..', 'data', 'ram_prices.csv')
MODEL_DIR   = os.path.join(os.path.dirname(__file__), '..', 'saved_model')
SCALER_PATH = os.path.join(MODEL_DIR, 'scaler.json')
EPOCHS      = 300
BATCH_SIZE  = 16
LR          = 1e-3


# ── 정규화 유틸 ───────────────────────────────────────────────────────────────
def fit_scaler(values):
    """Min-Max 스케일러 파라미터 반환"""
    return {'min': float(np.min(values)), 'max': float(np.max(values))}


def scale(values, scaler):
    return (values - scaler['min']) / (scaler['max'] - scaler['min'] + 1e-9)


def unscale(values, scaler):
    return values * (scaler['max'] - scaler['min'] + 1e-9) + scaler['min']


# ── 슬라이딩 윈도우 데이터셋 생성 ──────────────────────────────────────────────
def make_dataset(prices_scaled, window):
    X, y = [], []
    for i in range(len(prices_scaled) - window):
        X.append(prices_scaled[i: i + window])
        y.append(prices_scaled[i + window])
    return np.array(X, dtype=np.float32), np.array(y, dtype=np.float32)


# ── 선형 예측 모델 정의 ────────────────────────────────────────────────────────
def build_model(window_size):
    """
    선형 예측 알고리즘:
    Dense(64, relu) → Dense(32, relu) → Dense(1, linear)
    최종 출력층이 linear activation → 선형 회귀 특성 유지
    """
    model = tf.keras.Sequential([
        tf.keras.layers.Input(shape=(window_size,)),
        tf.keras.layers.Dense(64, activation='relu',
                              kernel_regularizer=tf.keras.regularizers.l2(1e-4)),
        tf.keras.layers.Dense(32, activation='relu',
                              kernel_regularizer=tf.keras.regularizers.l2(1e-4)),
        tf.keras.layers.Dense(1, activation='linear'),
    ], name='ram_linear_predictor')

    model.compile(
        optimizer=tf.keras.optimizers.Adam(learning_rate=LR),
        loss='mse',
        metrics=['mae'],
    )
    return model


# ── 학습 실행 ─────────────────────────────────────────────────────────────────
def train():
    print("=" * 60)
    print("Samsung DDR5 16GB 가격 예측 모델 학습 시작")
    print(f"TensorFlow 버전: {tf.__version__}")
    print("=" * 60)

    # 데이터 로드
    df = pd.read_csv(DATA_PATH)
    df['date'] = pd.to_datetime(df['date'])
    df = df.sort_values('date').reset_index(drop=True)
    prices = df['price'].values.astype(np.float32)

    print(f"데이터 기간: {df['date'].min().date()} ~ {df['date'].max().date()}")
    print(f"총 {len(prices)}일 데이터 로드 완료")

    # 정규화
    scaler = fit_scaler(prices)
    prices_scaled = scale(prices, scaler)

    # 데이터셋
    X, y = make_dataset(prices_scaled, WINDOW_SIZE)

    # Train / Validation 분리 (80/20)
    split = int(len(X) * 0.8)
    X_train, X_val = X[:split], X[split:]
    y_train, y_val = y[:split], y[split:]

    print(f"학습 샘플: {len(X_train)}, 검증 샘플: {len(X_val)}")

    # 모델 빌드
    model = build_model(WINDOW_SIZE)
    model.summary()

    # 콜백
    callbacks = [
        tf.keras.callbacks.EarlyStopping(
            monitor='val_loss', patience=30, restore_best_weights=True, verbose=1
        ),
        tf.keras.callbacks.ReduceLROnPlateau(
            monitor='val_loss', factor=0.5, patience=15, min_lr=1e-6, verbose=1
        ),
    ]

    # 학습
    history = model.fit(
        X_train, y_train,
        validation_data=(X_val, y_val),
        epochs=EPOCHS,
        batch_size=BATCH_SIZE,
        callbacks=callbacks,
        verbose=1,
    )

    # 저장
    os.makedirs(MODEL_DIR, exist_ok=True)
    model.save(os.path.join(MODEL_DIR, 'model.keras'))

    with open(SCALER_PATH, 'w') as f:
        json.dump(scaler, f)

    # 최종 검증 손실 출력
    val_loss = history.history['val_loss']
    val_mae  = history.history['val_mae']
    best_epoch = int(np.argmin(val_loss))
    best_mae_krw = unscale(np.array(val_mae[best_epoch]), scaler) - scaler['min']

    print("\n" + "=" * 60)
    print(f"학습 완료! 최적 에포크: {best_epoch + 1}")
    print(f"검증 MAE (원화 환산): ±{best_mae_krw:,.0f} 원")
    print(f"모델 저장 위치: {MODEL_DIR}")
    print("=" * 60)

    return model, scaler


if __name__ == '__main__':
    train()
