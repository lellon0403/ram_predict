import { useState, useEffect } from 'react'
import axios from 'axios'
import PriceChart from './components/PriceChart'
import PredictionCards from './components/PredictionCards'
import Recommendation from './components/Recommendation'
import ComparisonChart from './components/ComparisonChart'
import './App.css'

export default function App() {
  // ── n8n 연결 상태 ────────────────────────────────────────────────
  const [n8nUrl, setN8nUrl]       = useState('http://localhost:5678/webhook/ram-predict')
  const [connStatus, setConnStatus] = useState('idle')   // idle | testing | connected | error
  const [connError, setConnError]   = useState('')
  const [data, setData]             = useState(null)

  // ── 비교 데이터 (예측 vs 실제) ──────────────────────────────────
  const [compData, setCompData]         = useState(null)
  const [showComparison, setShowComparison] = useState(false)

  useEffect(() => {
    axios.get('/api/comparison')
      .then(res => { if (res.data?.success) setCompData(res.data.data) })
      .catch(() => {})
  }, [])

  // ── 가격 입력 ────────────────────────────────────────────────────
  const [inputRaw, setInputRaw]   = useState('')
  const [targetPrice, setTarget]  = useState(null)
  const [submitted, setSubmitted] = useState(false)

  // ── n8n 연결 테스트 ──────────────────────────────────────────────
  const testConnection = async () => {
    if (!n8nUrl.trim()) return
    setConnStatus('testing')
    setConnError('')
    setData(null)
    setSubmitted(false)
    setTarget(null)
    setInputRaw('')

    try {
      const res = await axios.post(n8nUrl.trim())
      // n8n → Flask 응답 구조 처리
      const payload = res.data?.data ?? res.data
      if (payload?.history && payload?.predictions) {
        setData(payload)
        setConnStatus('connected')
      } else if (res.data?.success && res.data?.data?.history) {
        setData(res.data.data)
        setConnStatus('connected')
      } else {
        throw new Error('응답 데이터 형식이 올바르지 않습니다. n8n 워크플로우를 확인하세요.')
      }
    } catch (e) {
      setConnStatus('error')
      setConnError(e.response
        ? `HTTP ${e.response.status} — ${e.response.statusText}`
        : e.message)
    }
  }

  const currentPrice = data?.history?.at(-1)?.price ?? null

  // ── 가격 입력 핸들러 ─────────────────────────────────────────────
  const handleInput = (e) => {
    setInputRaw(e.target.value.replace(/[^0-9]/g, ''))
    setSubmitted(false)
  }
  const handleKeyDown = (e) => { if (e.key === 'Enter') handleSubmit() }
  const handleSubmit  = () => { if (!inputRaw) return; setTarget(Number(inputRaw)); setSubmitted(true) }
  const clearInput    = () => { setInputRaw(''); setTarget(null); setSubmitted(false) }
  const handleQuick   = (val) => { setInputRaw(String(val)); setSubmitted(false) }

  const quickButtons = currentPrice ? [
    { label: '현재가', value: currentPrice },
    { label: '-5%',   value: Math.round(currentPrice * 0.95) },
    { label: '-10%',  value: Math.round(currentPrice * 0.90) },
    { label: '-20%',  value: Math.round(currentPrice * 0.80) },
  ] : []

  const showResults = submitted && !!targetPrice && !!data

  // ── 연결 상태 표시 설정 ──────────────────────────────────────────
  const statusConfig = {
    idle:      { dot: 'dot-idle',    text: '미연결',    desc: 'n8n 웹훅 URL을 입력하고 연결 테스트를 눌러주세요.' },
    testing:   { dot: 'dot-testing', text: '연결 중…',  desc: 'n8n 서버에 요청을 보내는 중입니다.' },
    connected: { dot: 'dot-ok',      text: '연결됨',    desc: `데이터 수신 완료 — 삼성 DDR5 16GB ${data ? `${data.history.length}일` : ''} 시세 로드됨` },
    error:     { dot: 'dot-err',     text: '연결 실패', desc: connError },
  }
  const sc = statusConfig[connStatus]

  return (
    <div className="app-bg">
      {/* ── 헤더 ───────────────────────────────────────────────────── */}
      <header className="header">
        <div className="header-inner">
          <div className="header-logo">
            <div className="logo-chip">💾</div>
            <div>
              <div className="logo-title">RAM Price Predictor</div>
              <div className="logo-sub">삼성 DDR5 16GB · AI 선형 예측 모델</div>
            </div>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            {compData && (
              <button
                onClick={() => setShowComparison(true)}
                style={{
                  display: 'flex', alignItems: 'center', gap: 6,
                  padding: '7px 14px', borderRadius: 8, border: '1.5px solid #2563eb',
                  background: '#eff6ff', color: '#2563eb',
                  fontSize: 13, fontWeight: 700, cursor: 'pointer',
                  whiteSpace: 'nowrap',
                }}
              >
                🎯 예측 정확도
              </button>
            )}
            {currentPrice && (
              <div className="current-badge">
                <span className="current-label">오늘 시세</span>
                <span className="current-price">₩{currentPrice.toLocaleString()}</span>
              </div>
            )}
          </div>
        </div>
      </header>

      <main className="main">

        {/* ── SECTION 1: n8n 연결 ───────────────────────────────── */}
        <section className="card">
          <div className="section-header">
            <h2 className="section-title">
              <span className="title-icon">🔗</span> n8n 연결 설정
            </h2>
            <div className={`status-pill ${sc.dot}`}>
              <span className="status-dot" />
              {sc.text}
            </div>
          </div>

          <p className="section-desc">
            n8n 웹훅 URL을 입력하세요.
            워크플로우 파일은 <code>n8n/workflow.json</code>을 n8n에서 임포트하면 자동 생성됩니다.
          </p>

          <div className="conn-row">
            <input
              className="url-input"
              type="text"
              placeholder="http://localhost:5678/webhook/ram-predict"
              value={n8nUrl}
              onChange={(e) => { setN8nUrl(e.target.value); setConnStatus('idle') }}
              onKeyDown={(e) => e.key === 'Enter' && testConnection()}
              spellCheck={false}
            />
            <button
              className={`conn-btn ${connStatus === 'testing' ? 'testing' : ''}`}
              onClick={testConnection}
              disabled={connStatus === 'testing'}
            >
              {connStatus === 'testing' ? '연결 중…' : '연결 테스트'}
            </button>
          </div>

          {/* 상태창 */}
          <div className={`status-box status-${connStatus}`}>
            <span className="status-icon">
              {connStatus === 'idle'      && '⚪'}
              {connStatus === 'testing'   && <span className="spin-sm">⟳</span>}
              {connStatus === 'connected' && '✅'}
              {connStatus === 'error'     && '❌'}
            </span>
            <div>
              <div className="status-main">{sc.text}</div>
              <div className="status-sub">{sc.desc}</div>
            </div>
          </div>
        </section>

        {/* ── SECTION 2: 가격 입력 (연결 후에만) ───────────────── */}
        {connStatus === 'connected' && (
          <>
            <section className="card">
              {!showResults && (
                <div className="hero-area">
                  <div className="hero-icon">🛒</div>
                  <h1 className="hero-title">지금 RAM 살 때가 맞을까요?</h1>
                  <p className="hero-desc">
                    구매 희망 가격을 입력하면 AI 선형 예측 모델이 1주일·1개월·3개월 후 가격을 예측하고<br />
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
                  <input
                    className="price-input"
                    type="text"
                    inputMode="numeric"
                    placeholder="300000"
                    value={inputRaw}
                    onChange={handleInput}
                    onKeyDown={handleKeyDown}
                    autoFocus
                  />
                  {inputRaw && (
                    <span className="input-formatted">
                      ({Number(inputRaw).toLocaleString()} 원)
                    </span>
                  )}
                </div>
                {inputRaw && !showResults && (
                  <button className="clear-btn" onClick={clearInput}>✕</button>
                )}
                <button
                  className={`submit-btn ${!inputRaw ? 'disabled' : ''}`}
                  onClick={handleSubmit}
                  disabled={!inputRaw}
                >
                  예측하기
                </button>
              </div>

              <div className="quick-btns">
                {quickButtons.map((b) => (
                  <button
                    key={b.label}
                    className={`quick-btn ${inputRaw === String(b.value) ? 'active' : ''}`}
                    onClick={() => handleQuick(b.value)}
                  >
                    <span className="quick-label">{b.label}</span>
                    <span className="quick-price">₩{b.value.toLocaleString()}</span>
                  </button>
                ))}
              </div>

              {!showResults && (
                <p className="input-hint">
                  숫자를 입력하거나 퀵 버튼 선택 후 <strong>예측하기</strong>를 누르세요
                </p>
              )}
              {showResults && (
                <p className="input-hint blue">
                  가격을 수정하면 결과가 초기화됩니다 — 수정 후 예측하기를 다시 눌러주세요
                </p>
              )}
            </section>

            {/* ── SECTION 3: 결과 ───────────────────────────────── */}
            {showResults && (
              <div className="results-area">
                <section className="card">
                  <h2 className="section-title"><span className="title-icon">🤖</span> AI 구매 추천</h2>
                  <Recommendation
                    targetPrice={targetPrice}
                    currentPrice={currentPrice}
                    forecast={data.forecast}
                  />
                </section>

                <section className="card">
                  <h2 className="section-title"><span className="title-icon">📊</span> 기간별 예측 가격</h2>
                  <PredictionCards
                    predictions={data.predictions}
                    currentPrice={currentPrice}
                    targetPrice={targetPrice}
                  />
                </section>

                <section className="card">
                  <div className="chart-header">
                    <h2 className="section-title" style={{ margin: 0 }}>
                      <span className="title-icon">📈</span> 가격 추이 &amp; 예측 차트
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
          </>
        )}

      </main>

      {/* ── 예측 정확도 모달 ───────────────────────────────────────── */}
      {showComparison && compData && (
        <div
          onClick={() => setShowComparison(false)}
          style={{
            position: 'fixed', inset: 0, zIndex: 1000,
            background: 'rgba(15,23,42,0.55)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            padding: '20px',
          }}
        >
          <div
            onClick={e => e.stopPropagation()}
            style={{
              background: '#fff', borderRadius: 16,
              width: '100%', maxWidth: 760,
              maxHeight: '88vh', overflowY: 'auto',
              boxShadow: '0 24px 64px rgba(0,0,0,0.2)',
              padding: '28px 32px',
            }}
          >
            {/* 모달 헤더 */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 20 }}>
              <div>
                <h2 style={{ margin: 0, fontSize: 20, fontWeight: 800, color: '#0f172a' }}>
                  🎯 예측 정확도 검증
                </h2>
                <p style={{ margin: '6px 0 0', fontSize: 13, color: '#64748b' }}>
                  모델 학습 마감(2026-04-14) 이후 13일 실제 시세와 비교
                </p>
              </div>
              <button
                onClick={() => setShowComparison(false)}
                style={{
                  border: 'none', background: '#f1f5f9', borderRadius: 8,
                  width: 32, height: 32, fontSize: 18, cursor: 'pointer',
                  color: '#475569', display: 'flex', alignItems: 'center', justifyContent: 'center',
                }}
              >✕</button>
            </div>

            {/* 설명 */}
            <p style={{ margin: '0 0 20px', fontSize: 14, color: '#475569', lineHeight: 1.7,
                        background: '#f8fafc', borderRadius: 8, padding: '12px 16px' }}>
              2026-04-14까지의 180일 데이터로 학습한 단일 변수 선형 회귀 모델이
              이후 <strong>13일(4/15~4/27)</strong>을 예측한 값과 실제 다나와 시세를 비교한 결과입니다.
            </p>

            <ComparisonChart records={compData.records} summary={compData.summary} />

            {/* 날짜별 상세 테이블 */}
            <div style={{ marginTop: 24 }}>
              <h3 style={{ fontSize: 14, fontWeight: 700, color: '#1e40af', marginBottom: 10 }}>
                📋 날짜별 상세 비교
              </h3>
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
                <thead>
                  <tr style={{ background: '#1e40af', color: '#fff' }}>
                    {['날짜', '예측가', '실제가', '오차', '오차율'].map(h => (
                      <th key={h} style={{ padding: '8px 12px', textAlign: 'center', fontWeight: 700 }}>{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {compData.records.map((r, i) => (
                    <tr key={r.date} style={{ background: i % 2 === 0 ? '#fff' : '#f8fafc' }}>
                      <td style={{ padding: '7px 12px', textAlign: 'center', fontWeight: 600, color: '#374151' }}>{r.date}</td>
                      <td style={{ padding: '7px 12px', textAlign: 'right', color: '#f97316', fontWeight: 600 }}>₩{r.predicted?.toLocaleString()}</td>
                      <td style={{ padding: '7px 12px', textAlign: 'right', color: '#2563eb', fontWeight: 600 }}>₩{r.actual?.toLocaleString()}</td>
                      <td style={{ padding: '7px 12px', textAlign: 'right', color: r.error < 0 ? '#dc2626' : '#16a34a', fontWeight: 600 }}>
                        {r.error != null ? `${r.error > 0 ? '+' : ''}${r.error?.toLocaleString()}` : '-'}
                      </td>
                      <td style={{ padding: '7px 12px', textAlign: 'center', color: r.error_pct < 0 ? '#dc2626' : '#16a34a', fontWeight: 700 }}>
                        {r.error_pct != null ? `${r.error_pct > 0 ? '+' : ''}${r.error_pct}%` : '-'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
