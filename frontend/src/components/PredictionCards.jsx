const LABELS = { '1week': '1주일 뒤', '1month': '1개월 뒤', '3months': '3개월 뒤' }
const ICONS  = { '1week': '📅', '1month': '🗓️', '3months': '🔭' }

export default function PredictionCards({ predictions, currentPrice, targetPrice }) {
  if (!predictions) return null

  return (
    <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap' }}>
      {Object.entries(predictions).map(([key, val]) => {
        const diff = currentPrice ? val.price - currentPrice : null
        const diffPct = currentPrice ? ((val.price - currentPrice) / currentPrice * 100) : null
        const vsTarget = targetPrice ? val.price - targetPrice : null
        const rising = diff !== null && diff > 0

        return (
          <div key={key} style={{
            flex: '1 1 200px',
            background: '#1e293b',
            borderRadius: 14,
            padding: '20px 22px',
            border: `1px solid ${rising ? '#f9731644' : '#3b82f644'}`,
            transition: 'transform .15s',
          }}>
            <div style={{ fontSize: 22, marginBottom: 6 }}>{ICONS[key]}</div>
            <div style={{ color: '#94a3b8', fontSize: 13, marginBottom: 4 }}>
              {LABELS[key]} ({val.date})
            </div>
            <div style={{ color: '#f1f5f9', fontSize: 26, fontWeight: 700, letterSpacing: -0.5 }}>
              ₩{val.price.toLocaleString()}
            </div>

            {/* 현재가 대비 */}
            {diff !== null && (
              <div style={{ marginTop: 8, fontSize: 13, color: rising ? '#f87171' : '#4ade80' }}>
                현재 대비 {rising ? '▲' : '▼'} ₩{Math.abs(diff).toLocaleString()}
                <span style={{ marginLeft: 4, opacity: 0.75 }}>({diffPct > 0 ? '+' : ''}{diffPct.toFixed(1)}%)</span>
              </div>
            )}

            {/* 목표가 대비 */}
            {vsTarget !== null && (
              <div style={{
                marginTop: 6, fontSize: 12,
                color: vsTarget <= 0 ? '#4ade80' : '#94a3b8',
                fontWeight: vsTarget <= 0 ? 700 : 400,
              }}>
                {vsTarget <= 0
                  ? `✅ 목표가보다 ₩${Math.abs(vsTarget).toLocaleString()} 저렴`
                  : `목표가까지 ₩${vsTarget.toLocaleString()} 남음`}
              </div>
            )}
          </div>
        )
      })}
    </div>
  )
}
