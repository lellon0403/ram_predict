"""
Samsung DDR5 16GB RAM 가격 예측 모델 - 추론 스크립트
알고리즘: TensorFlow Keras 선형 예측 모델 (학습된 모델 로드 후 자동 회귀 예측)

예측 흐름:
  1. 저장된 model.keras 로드
  2. 최근 30일 로그 수익률 → 다음 날 예측 → 윈도우 슬라이딩 반복
  3. 90일 예측 완성 후 1주일/1개월/3개월 지점 추출
"""

#######
# 필요한 라이브러리 임포트
#######
import os
import json
import warnings
import numpy as np
import pandas as pd
import tensorflow as tf

warnings.filterwarnings('ignore')

from datetime import date, timedelta


#######
# 경로 설정 (trainer.py 와 동일한 구조)
#######
MODEL_DIR   = os.path.join(os.path.dirname(__file__), '..', 'saved_model')
DATA_PATH   = os.path.join(os.path.dirname(__file__), '..', 'data', 'ram_prices.csv')
MODEL_PATH  = os.path.join(MODEL_DIR, 'model.keras')   # TensorFlow .keras 포맷
META_PATH   = os.path.join(MODEL_DIR, 'scaler.json')   # 정규화 파라미터
WINDOW_SIZE = 30                                         # 슬라이딩 윈도우 크기 (trainer.py 와 동일)


#######
# 전역 캐시: 모델과 메타데이터를 한 번만 로드하도록 유지
# Flask 서버에서 요청마다 로드하지 않아 응답 속도 향상
#######
_model = None
_meta  = None


#######
# 모델 및 메타데이터 로드 함수
# 최초 호출 시에만 디스크에서 로드, 이후 캐시 반환
#######
def _load_artifacts():
    """
    TensorFlow .keras 모델과 scaler.json 메타데이터를 로드
    반환: (keras.Model, dict)
    """
    global _model, _meta
    if _model is None:
        if not os.path.exists(MODEL_PATH):
            raise FileNotFoundError(
                f"모델 없음: {MODEL_PATH}\n"
                "먼저 POST /retrain 또는 `python model/trainer.py` 실행"
            )
        # TensorFlow Keras 모델 로드 (.keras 포맷)
        _model = tf.keras.models.load_model(MODEL_PATH)
        with open(META_PATH) as f:
            _meta = json.load(f)
    return _model, _meta


#######
# 자동 회귀 예측 함수
# 슬라이딩 윈도우로 n일 연속 예측 수행
# 매 스텝: 예측 결과를 윈도우 끝에 추가하고 앞을 제거
#######
def _predict_n_days(model, meta, last_returns_sc: np.ndarray, last_price: float, n: int):
    """
    model          : 로드된 TensorFlow Keras 모델
    meta           : {'ret_mean': float, 'ret_std': float, 'last_price': float}
    last_returns_sc: 정규화된 최근 WINDOW_SIZE 개 로그 수익률 (길이 30)
    last_price     : 마지막 실제 가격 (원화)
    n              : 예측할 일수
    반환            : 예측 원화 가격 리스트 (길이 n)
    """
    window   = last_returns_sc.copy()
    price    = last_price
    results  = []
    ret_mean = meta['ret_mean']
    ret_std  = meta['ret_std']

    for _ in range(n):
        #######
        # 입력 클리핑: ±3σ 이내로 제한 (이상값 방지)
        # 자동 회귀 누적 오차가 극단값으로 발산하지 않도록 차단
        #######
        x_input = np.clip(window[-WINDOW_SIZE:], -3.0, 3.0).reshape(1, -1).astype(np.float32)

        #######
        # TensorFlow Keras 모델로 다음 날 정규화 로그 수익률 예측
        # model.predict() 반환: shape (1, 1) → float 추출
        #######
        r_sc = float(model.predict(x_input, verbose=0)[0][0])
        r_sc = np.clip(r_sc, -3.0, 3.0)   # 출력도 클리핑

        #######
        # 역정규화: 정규화된 수익률 → 실제 로그 수익률
        # r_real = r_sc * std + mean
        #######
        log_ret = r_sc * ret_std + ret_mean

        #######
        # 하루 최대 ±20% 변동 차단
        # 선형 모델의 드리프트로 인한 비현실적 예측 방지
        #######
        log_ret = max(-0.20, min(0.20, log_ret))

        #######
        # 가격 업데이트: p_t = p_{t-1} * exp(r_t)
        #######
        price = price * np.exp(log_ret)
        results.append(price)

        # 윈도우 슬라이딩: 새 예측값 추가, 가장 오래된 값 제거
        window = np.append(window[1:], r_sc)

    return results


#######
# 메인 예측 함수
# Flask /predict 엔드포인트에서 호출
# CSV 로드 → 로그 수익률 정규화 → 90일 자동 회귀 예측 → 결과 딕셔너리 반환
#######
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

    #######
    # 2단계: 가격 데이터 CSV 로드 및 정렬
    #######
    df = pd.read_csv(DATA_PATH)
    df['date'] = pd.to_datetime(df['date'])
    df = df.sort_values('date').reset_index(drop=True)
    prices = df['price'].values.astype(np.float64)

    #######
    # 3단계: 로그 수익률 변환 및 정규화 (trainer.py 와 동일한 파라미터 적용)
    #######
    log_returns = np.diff(np.log(prices))
    ret_mean    = meta['ret_mean']
    ret_std     = meta['ret_std']
    returns_sc  = (log_returns - ret_mean) / (ret_std + 1e-9)

    #######
    # 4단계: 마지막 30일 윈도우로 90일 예측 실행
    #######
    last_window = returns_sc[-WINDOW_SIZE:]
    last_price  = float(prices[-1])
    last_date   = df['date'].iloc[-1].date()

    forecast_prices = _predict_n_days(model, meta, last_window, last_price, 90)
    forecast_dates  = [last_date + timedelta(days=i + 1) for i in range(90)]

    #######
    # 5단계: 예측 결과를 날짜별 딕셔너리 리스트로 변환
    #######
    forecast = [
        {"date": d.isoformat(), "price": round(p)}
        for d, p in zip(forecast_dates, forecast_prices)
    ]

    #######
    # 6단계: 1주일(7일)/1개월(30일)/3개월(90일) 지점 추출
    #######
    def pick(days):
        return {
            "date":  forecast_dates[days - 1].isoformat(),
            "price": round(forecast_prices[days - 1]),
        }

    #######
    # 7단계: 전체 히스토리 + 예측 결과 반환
    #######
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
