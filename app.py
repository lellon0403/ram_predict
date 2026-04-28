"""
RAM 가격 예측 Flask 서버
React / n8n 에서 POST 요청으로 예측 결과를 수신

Endpoints
─────────
POST /predict           전체 예측 결과 (history + forecast + point predictions)
GET  /history           저장된 히스토리 데이터만 반환
POST /retrain           모델 재학습 트리거 (백그라운드)
GET  /health            서버 상태 확인
"""

import os
import threading

from flask import Flask, jsonify, request
from flask_cors import CORS

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})   # React / n8n 연동 위해 전체 허용


# ── 헬퍼: 모델 존재 여부 확인 ──────────────────────────────────────────────────
def _model_trained() -> bool:
    model_path = os.path.join(
        os.path.dirname(__file__), 'saved_model', 'ram', 'linear', 'model.keras'
    )
    return os.path.exists(model_path)


# ── 라우트 ─────────────────────────────────────────────────────────────────────

@app.route('/health', methods=['GET'])
def health():
    """서버 및 모델 상태 확인"""
    return jsonify({
        "status":        "ok",
        "model_trained": _model_trained(),
        "message":       "RAM 가격 예측 서버가 정상 동작 중입니다." if _model_trained()
                         else "모델이 없습니다. POST /retrain 으로 학습을 시작하세요.",
    })


@app.route('/predict', methods=['POST'])
def predict():
    """
    예측 결과 반환

    Request Body (선택, 현재는 무시 – 추후 파라미터 추가 가능)
    ────────────────────────────────────────────────────────────
    {}

    Response
    ────────
    {
      "success": true,
      "data": {
        "history":  [{"date": "YYYY-MM-DD", "price": 82000}, ...],
        "forecast": [{"date": "YYYY-MM-DD", "price": 47200}, ...],   // 90일 일별
        "predictions": {
          "1week":   {"date": "YYYY-MM-DD", "price": 47200},
          "1month":  {"date": "YYYY-MM-DD", "price": 45800},
          "3months": {"date": "YYYY-MM-DD", "price": 43100}
        }
      }
    }
    """
    if not _model_trained():
        return jsonify({
            "success": False,
            "error": "모델이 학습되지 않았습니다. POST /retrain 을 먼저 실행하세요.",
        }), 503

    try:
        from model.predictor import get_predictions
        result = get_predictions()
        return jsonify({"success": True, "data": result})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/history', methods=['GET'])
def history():
    """저장된 히스토리 데이터 반환 (모델 불필요)"""
    import pandas as pd

    data_path = os.path.join(os.path.dirname(__file__), 'data', 'train', 'ram_prices.csv')
    df = pd.read_csv(data_path)
    df['date'] = pd.to_datetime(df['date'])
    df = df.sort_values('date')

    records = [
        {"date": row['date'].date().isoformat(), "price": int(row['price'])}
        for _, row in df.iterrows()
    ]
    return jsonify({"success": True, "data": records})


@app.route('/retrain', methods=['POST'])
def retrain():
    """
    모델 재학습 – 백그라운드 스레드에서 실행
    즉시 202 반환, 학습은 비동기로 진행
    """
    def _run():
        from model.trainer import train
        train()

    thread = threading.Thread(target=_run, daemon=True)
    thread.start()

    return jsonify({
        "success": True,
        "message": "학습이 백그라운드에서 시작되었습니다. 완료 후 /predict 를 호출하세요.",
    }), 202


@app.route('/comparison', methods=['GET'])
def comparison():
    """예측값 vs 실제값 비교 데이터 반환 (comparison_result.csv)"""
    import pandas as pd

    path = os.path.join(os.path.dirname(__file__), 'comparison_result.csv')
    if not os.path.exists(path):
        return jsonify({"success": False, "error": "comparison_result.csv 가 없습니다. python comparison.py 를 먼저 실행하세요."}), 404

    df = pd.read_csv(path)
    records = df.to_dict('records')
    mae  = round(df['error'].abs().mean())
    mape = round(df['abs_error_pct'].mean(), 2)

    return jsonify({
        "success": True,
        "data": {
            "records": records,
            "summary": {"mae": mae, "mape": mape, "days": len(df)},
        },
    })


# ── 진입점 ─────────────────────────────────────────────────────────────────────
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_DEBUG', 'false').lower() == 'true'
    print(f"Flask 서버 시작: http://localhost:{port}")
    print(f"모델 학습 여부: {_model_trained()}")
    if not _model_trained():
        print("  → POST http://localhost:{port}/retrain  으로 먼저 학습하세요.")
    app.run(host='0.0.0.0', port=port, debug=debug)
