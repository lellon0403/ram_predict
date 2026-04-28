"""
Samsung DDR5 16GB RAM 가격 예측 모델 - 학습 스크립트
알고리즘: TensorFlow Keras 단일 변수 선형 회귀 (Linear Regression)

단일 변수 구조:
  입력(X): 날짜 순서 (일수 인덱스, 정규화)
  출력(y): 해당 날의 가격 (정규화)
  모델:    Dense(1, activation='linear') → H(x) = W*x + b
"""

import os
import json
import warnings
import numpy as np
import pandas as pd

warnings.filterwarnings('ignore')

import tensorflow as tf
from tensorflow import keras


#######
# 전역 설정값 (하이퍼파라미터)
#######
EPOCHS     = 2000      # 최대 학습 반복 횟수
BATCH_SIZE = 32        # 배치 크기
LR         = 1e-3      # 학습률 (Adam optimizer)

DATA_PATH  = os.path.join(os.path.dirname(__file__), '..', 'data', 'train', 'ram_prices.csv')
MODEL_DIR  = os.path.join(os.path.dirname(__file__), '..', 'saved_model', 'linear')
MODEL_PATH = os.path.join(MODEL_DIR, 'model.keras')
META_PATH  = os.path.join(MODEL_DIR, 'scaler.json')


#######
# TensorFlow Keras 단일 변수 선형 회귀 모델 정의
# H(x) = W * x + b
# Dense(1, activation='linear') = 선형 회귀와 수학적으로 동일
#######
def build_model() -> keras.Model:
    model = keras.Sequential([
        keras.layers.Input(shape=(1,)),          # 입력: 날짜 인덱스 1개
        keras.layers.Dense(
            units=1,
            activation='linear',                 # 선형 활성화 = 활성화 함수 없음
            name='linear_output'
        ),
    ], name='ram_linear_predictor')

    model.compile(
        optimizer=keras.optimizers.Adam(learning_rate=LR),
        loss='mse',        # 평균제곱오차 손실함수
        metrics=['mae'],   # 평균절대오차 모니터링
    )
    return model


#######
# 메인 학습 함수
#######
def train():
    print("=" * 60)
    print("Samsung DDR5 16GB 가격 예측 모델 학습 시작")
    print(f"TensorFlow 버전: {tf.__version__}")
    print("알고리즘: TensorFlow Keras 단일 변수 선형 회귀")
    print("=" * 60)

    #######
    # 1단계: CSV 데이터 로드 및 정렬
    #######
    df = pd.read_csv(DATA_PATH)
    df['date'] = pd.to_datetime(df['date'])
    df = df.sort_values('date').reset_index(drop=True)
    prices = df['price'].values.astype(np.float32)

    print(f"데이터 기간: {df['date'].min().date()} ~ {df['date'].max().date()}")
    print(f"총 {len(prices)}일, 가격 범위: {prices.min():,.0f} ~ {prices.max():,.0f} 원")

    #######
    # 2단계: 단일 변수 X 생성 (날짜 인덱스)
    # X = [0, 1, 2, ..., N-1]  → 각 행의 날짜 순서
    # y = 해당 날의 가격
    #######
    x_data = np.arange(len(prices), dtype=np.float32)   # 0, 1, 2, ..., 729
    y_data = prices.copy()

    #######
    # 3단계: 정규화 (Z-score)
    # 입력과 출력 모두 평균=0, 표준편차=1 로 변환
    # → 학습 안정성 확보
    #######
    x_mean = float(x_data.mean())
    x_std  = float(x_data.std())
    y_mean = float(y_data.mean())
    y_std  = float(y_data.std())

    x_sc = (x_data - x_mean) / x_std
    y_sc = (y_data - y_mean) / y_std

    #######
    # 4단계: Train / Validation 분리 (80% / 20%)
    # 시계열이므로 시간 순서 유지 — 앞 80% 학습, 뒤 20% 검증
    #######
    split   = int(len(x_sc) * 0.8)
    X_train = x_sc[:split].reshape(-1, 1)
    X_val   = x_sc[split:].reshape(-1, 1)
    y_train = y_sc[:split]
    y_val   = y_sc[split:]

    print(f"학습 샘플: {len(X_train)}, 검증 샘플: {len(X_val)}")

    #######
    # 5단계: 모델 생성 및 구조 출력
    #######
    model = build_model()
    model.summary()

    #######
    # 6단계: 조기 종료 콜백 설정
    #######
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

    #######
    # 7단계: 모델 학습
    #######
    history = model.fit(
        X_train, y_train,
        validation_data=(X_val, y_val),
        epochs=EPOCHS,
        batch_size=BATCH_SIZE,
        callbacks=callbacks,
        verbose=1,
    )

    #######
    # 8단계: 검증 MAE 원화 환산
    #######
    best_epoch = int(np.argmin(history.history['val_loss']))
    val_mae_sc = history.history['val_mae'][best_epoch]
    val_mae_krw = val_mae_sc * y_std   # 정규화 역변환 → 원화

    #######
    # 9단계: 정규화 파라미터 및 메타데이터 저장
    #######
    meta = {
        'x_mean':     x_mean,
        'x_std':      x_std,
        'y_mean':     y_mean,
        'y_std':      y_std,
        'n_days':     int(len(prices)),      # 학습에 사용된 총 일수
        'last_price': float(prices[-1]),
    }

    os.makedirs(MODEL_DIR, exist_ok=True)
    model.save(MODEL_PATH)
    with open(META_PATH, 'w') as f:
        json.dump(meta, f)

    print("\n" + "=" * 60)
    print("학습 완료!")
    print(f"최적 에포크: {best_epoch + 1} / {EPOCHS}")
    print(f"검증 MAE (원화): ±{abs(val_mae_krw):,.0f} 원")
    print(f"모델 저장: {MODEL_PATH}")
    print("=" * 60)

    return model, meta


if __name__ == '__main__':
    train()
