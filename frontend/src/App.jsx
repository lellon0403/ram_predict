import { useState, useEffect } from 'react'
import axios from 'axios'
import PriceChart from './components/PriceChart'
import PredictionCards from './components/PredictionCards'
import Recommendation from './components/Recommendation'
import './App.css'

export default function App() {
  const [data, setData]          = useState(null)
  const [loading, setLoading]    = useState(true)
  const [error, setError]        = useState(null)
  const [inputRaw, setInputRaw]  = useState('')   // 숫자 문자열 (콤마 없음)
  const [targetPrice, setTarget] = useState(null) // Number or null

  useEffect(() => {
    axios.post('/api/predict')
      .then((res) => {
        if (res.data.success) setData(res.data.data)
        else setError(res.data.error)
      })
      .catch((e) => {
        setError(e.message + ' — Flask 서버(localhost:5000)가 실행 중인지 확인하세요.')
      })
      .finally(() => setLoading(false))
  }, [])

  const currentPrice = data?.history?.at(-1)?.price ?? null

  // 입력: 숫자만 허용, 콤마 없이 저장
  const handleInput = (e) => {
    const raw = e.target.value.replace(/[^0-9]/g, '')
    setInputRaw(raw)
    setTarget(raw ? Number(raw) : null)
  }

  const clearInput = () => { setInputRaw(''); setTarget(null) }

  const quickButtons = currentPrice
    ? [
        { label: '현재가',  value: currentPrice },
        { label: '-5%',   value: Math.round(currentPrice * 0.95) },
        { label: '-10%',  value: Math.round(currentPrice * 0.90) },
        { label: '-20%',  value: Math.round(currentPrice * 0.80) },
      ]
    : []

  const showResults = !!targetPrice && !!data

  return (
    <div className="app-bg">
      {/* ── 헤더 ─────────────────────────────────────────────────── */}
      <header className="header">
        <div className="header-inner">
          <div className="header-logo">
            <span className="logo-icon">💾</span>
            <div>
              <div className="logo-title">RAM Price Predictor</div>
              <div className="logo-sub">삼성 DDR5 16GB · AI 가격 예측</div>
            </div>
          </div>
          {currentPrice && (
            <div className="current-badge">
              <span className="current-label">오늘 시세</span>
              <span className="current-price">₩{currentPrice.toLocaleString()}</span>
            </div>
          )}
        </div>
      </header>

      <main className="main">
        {/* ── 로딩 ───────────────────────────────────────────────── */}
        {loading && (
          <div className="state-box">
            <div className="spinner" />
            <p>AI 예측 데이터를 불러오는 중...</p>
          </div>
        )}

        {/* ── 에러 ───────────────────────────────────────────────── */}
        {error && !loading && (
          <div className="error-box">
            <div style={{ fontSize: 40, marginBottom: 8 }}>⚠️</div>
            <strong>데이터 로드 실패</strong>
            <p style={{ fontSize: 13, marginTop: 6, opacity: .8 }}>{error}</p>
          </div>
        )}

        {/* ── 가격 입력 카드 ──────────────────────────────────────── */}
        {data && !loading && (
          <section className="card input-card">
            {/* 히어로 텍스트 (결과 없을 때만) */}
            {!showResults && (
              <div className="hero-area">
                <div className="hero-icon">💾</div>
                <h1 className="hero-title">지금 RAM 살 때가 맞을까요?</h1>
                <p className="hero-desc">
                  구매 희망 가격을 입력하면 AI가 1주일·1개월·3개월 후 가격을 예측하고<br />
                  지금 구매해야 할지 알려드립니다.
                </p>
              </div>
            )}

            <div className="input-label">
              {showResults ? '🎯 구매 희망 가격' : '구매 희망 가격을 입력하세요'}
            </div>

            <div className="input-row">
              <div className="input-wrap">
                <span className="input-prefix">₩</span>
                {/* value를 raw 숫자로 유지 → 커서 깨짐 없음 */}
                <input
                  className="price-input"
                  type="text"
                  inputMode="numeric"
                  placeholder="300000"
                  value={inputRaw}
                  onChange={handleInput}
                  autoFocus={!showResults}
                />
                {/* 포맷 표시는 입력 옆 별도 span */}
                {inputRaw && (
                  <span className="input-formatted">
                    ({Number(inputRaw).toLocaleString()} 원)
                  </span>
                )}
              </div>
              {inputRaw && (
                <button className="clear-btn" onClick={clearInput}>✕</button>
              )}
            </div>

            {/* 퀵 버튼 */}
            <div className="quick-btns">
              {quickButtons.map((b) => (
                <button
                  key={b.label}
                  className={`quick-btn ${targetPrice === b.value ? 'active' : ''}`}
                  onClick={() => { setInputRaw(String(b.value)); setTarget(b.value) }}
                >
                  <span className="quick-label">{b.label}</span>
                  <span className="quick-price">₩{b.value.toLocaleString()}</span>
                </button>
              ))}
            </div>

            {/* 안내 메시지 (입력 전) */}
            {!showResults && (
              <p className="input-hint">
                ↑ 숫자를 입력하거나 아래 버튼으로 빠르게 선택하세요
              </p>
            )}
          </section>
        )}

        {/* ── 결과 섹션: 가격 입력 후에만 표시 ──────────────────── */}
        {showResults && (
          <div className="results-area">
            {/* AI 구매 추천 */}
            <section className="card">
              <h2 className="section-title"><span>🤖</span> AI 구매 추천</h2>
              <Recommendation
                targetPrice={targetPrice}
                currentPrice={currentPrice}
                predictions={data.predictions}
              />
            </section>

            {/* 기간별 예측 카드 */}
            <section className="card">
              <h2 className="section-title"><span>📊</span> 기간별 예측 가격</h2>
              <PredictionCards
                predictions={data.predictions}
                currentPrice={currentPrice}
                targetPrice={targetPrice}
              />
            </section>

            {/* 차트 */}
            <section className="card">
              <div className="chart-header">
                <h2 className="section-title" style={{ margin: 0 }}>
                  <span>📈</span> 가격 추이 &amp; 예측 차트
                </h2>
                <span className="chart-note">최근 90일 실제 + 90일 예측</span>
              </div>
              <div style={{ marginTop: 20 }}>
                <PriceChart
                  history={data.history}
                  forecast={data.forecast}
                  predictions={data.predictions}
                  targetPrice={targetPrice}
                />
              </div>
              <div className="chart-legend-row">
                <span className="legend-item blue">● 실제 가격</span>
                <span className="legend-item orange">- - 예측 가격</span>
                <span className="legend-item green">— 목표 가격</span>
              </div>
            </section>

            <footer className="footer-note">
              데이터 출처: 다나와·네이버 가격 기반 실제 시세 / 예측은 참고용이며 실제 가격과 다를 수 있습니다
            </footer>
          </div>
        )}
      </main>
    </div>
  )
}
