"""
Samsung DDR5 16GB RAM 가격 예측 모델 - 학습 스크립트
알고리즘: TensorFlow Keras 선형 예측 모델 (Linear Regression)

선형 예측 구조:
  입력(X): 최근 30일치 로그 수익률 벡터
  출력(y): 다음 날 로그 수익률 스칼라
  모델:    Dense(1, activation='linear') → 선형 회귀와 동일한 구조

로그 수익률 사용 이유:
  가격이 47,000원 → 320,000원으로 폭등한 비정상적 범위를 다루기 위해
  r_t = ln(p_t) - ln(p_{t-1}) 변환으로 스케일 불변성 확보
"""

#######
# 필요한 라이브러리 임포트
#######
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
WINDOW_SIZE = 30        # 슬라이딩 윈도우 크기: 최근 30일 데이터로 다음 날 예측
EPOCHS      = 200       # 최대 학습 반복 횟수
BATCH_SIZE  = 16        # 한 번에 학습하는 샘플 수
LR          = 1e-3      # 학습률 (Adam optimizer)

DATA_PATH  = os.path.join(os.path.dirname(__file__), '..', 'data', 'ram_prices.csv')
MODEL_DIR  = os.path.join(os.path.dirname(__file__), '..', 'saved_model')
MODEL_PATH = os.path.join(MODEL_DIR, 'model.keras')
META_PATH  = os.path.join(MODEL_DIR, 'scaler.json')


#######
# 슬라이딩 윈도우 데이터셋 생성 함수
# 연속된 시계열 데이터를 (입력 윈도우, 정답) 쌍으로 변환
#######
def make_dataset(returns: np.ndarray, window: int):
    """
    returns : 정규화된 로그 수익률 배열 (길이 N)
    window  : 입력 윈도우 크기
    반환    : X shape=(N-window, window), y shape=(N-window,)
    """
    X, y = [], []
    for i in range(len(returns) - window):
        X.append(returns[i : i + window])   # 최근 window 일이 입력
        y.append(returns[i + window])        # 그 다음 날이 정답
    return np.array(X, dtype=np.float32), np.array(y, dtype=np.float32)


#######
# TensorFlow Keras 선형 예측 모델 정의
# Dense(1, activation='linear') = 선형 회귀와 수학적으로 동일
# y = W·x + b  (가중치 행렬 W, 편향 b)
#######
def build_model(window_size: int) -> keras.Model:
    """
    선형 예측 모델: 입력 차원 window_size → 출력 스칼라 1
    activation='linear' 이므로 비선형 변환 없음 → 순수 선형 회귀
    """
    model = keras.Sequential([
        keras.layers.Input(shape=(window_size,)),
        keras.layers.Dense(
            units=1,
            activation='linear',   # 선형 활성화 = 활성화 함수 없음
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
# 데이터 로드 → 전처리 → 모델 학습 → 저장
#######
def train():
    print("=" * 60)
    print("Samsung DDR5 16GB 가격 예측 모델 학습 시작")
    print(f"TensorFlow 버전: {tf.__version__}")
    print("알고리즘: TensorFlow Keras 선형 예측 모델")
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
    # 2단계: 로그 수익률 변환 및 정규화
    # r_t = ln(p_t) - ln(p_{t-1})  → 전일 대비 변화율
    # 표준화: (r - mean) / std  → 평균 0, 표준편차 1
    #######
    log_returns = np.diff(np.log(prices)).astype(np.float32)   # 길이 N-1

    ret_mean = float(log_returns.mean())
    ret_std  = float(log_returns.std())
    returns_sc = (log_returns - ret_mean) / (ret_std + 1e-9)   # 표준화

    # 정규화 파라미터 저장 (예측 시 역변환에 사용)
    meta = {
        'ret_mean':   ret_mean,
        'ret_std':    ret_std,
        'last_price': float(prices[-1]),
    }

    #######
    # 3단계: 슬라이딩 윈도우로 학습 데이터셋 생성
    #######
    X, y = make_dataset(returns_sc, WINDOW_SIZE)

    # 훈련 80% / 검증 20% 분리
    split   = int(len(X) * 0.8)
    X_train, X_val = X[:split], X[split:]
    y_train, y_val = y[:split], y[split:]
    print(f"학습 샘플: {len(X_train)}, 검증 샘플: {len(X_val)}")

    #######
    # 4단계: 모델 생성 및 구조 출력
    #######
    model = build_model(WINDOW_SIZE)
    model.summary()

    #######
    # 5단계: 조기 종료 콜백 설정
    # 검증 손실이 30 에포크 동안 개선되지 않으면 학습 중단
    #######
    callbacks = [
        keras.callbacks.EarlyStopping(
            monitor='val_loss',
            patience=30,
            restore_best_weights=True,
            verbose=1
        ),
        keras.callbacks.ReduceLROnPlateau(
            monitor='val_loss',
            factor=0.5,
            patience=15,
            min_lr=1e-6,
            verbose=1
        ),
    ]

    #######
    # 6단계: 모델 학습
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
    # 7단계: 검증 MAE 원화 환산 및 출력
    #######
    best_epoch  = int(np.argmin(history.history['val_loss']))
    val_mae_sc  = history.history['val_mae'][best_epoch]
    # 정규화된 MAE → 실제 로그 수익률 MAE → 가격 변화 MAE (근사)
    val_mae_krw = float(np.exp(val_mae_sc * ret_std) * meta['last_price'] - meta['last_price'])

    #######
    # 8단계: 모델 및 메타데이터 저장
    #######
    os.makedirs(MODEL_DIR, exist_ok=True)
    model.save(MODEL_PATH)                   # .keras 포맷으로 저장
    with open(META_PATH, 'w') as f:
        json.dump(meta, f)

    print("\n" + "=" * 60)
    print("학습 완료!")
    print(f"최적 에포크: {best_epoch + 1} / {EPOCHS}")
    print(f"검증 MAE (원화 근사): ±{abs(val_mae_krw):,.0f} 원")
    print(f"모델 저장: {MODEL_PATH}")
    print("=" * 60)

    return model, meta


#######
# 스크립트 직접 실행 시 학습 시작
#######
if __name__ == '__main__':
    train()
