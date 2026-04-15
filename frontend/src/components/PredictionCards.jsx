const LABELS = { '1week': '1주일 뒤', '1month': '1개월 뒤', '3months': '3개월 뒤' }
const ICONS  = { '1week': '📅', '1month': '🗓️', '3months': '🔭' }

export default function PredictionCards({ predictions, currentPrice, targetPrice }) {
  if (!predictions) return null

  return (
    <div style={{ display: 'flex', gap: 14, flexWrap: 'wrap' }}>
      {Object.entries(predictions).map(([key, val]) => {
        const diff    = currentPrice ? val.price - currentPrice : null
        const diffPct = currentPrice ? ((val.price - currentPrice) / currentPrice * 100) : null
        const vsTarget = targetPrice ? val.price - targetPrice : null
        const rising   = diff !== null && diff > 0

        return (
          <div key={key} style={{
            flex: '1 1 200px',
            background: '#f8faff',
            borderRadius: 12,
            padding: '18px 20px',
            border: `1.5px solid ${rising ? '#fca5a5' : '#86efac'}`,
            boxShadow: '0 2px 8px rgba(37,99,235,0.06)',
          }}>
            <div style={{ fontSize: 20, marginBottom: 5 }}>{ICONS[key]}</div>
            <div style={{ color: '#64748b', fontSize: 12.5, marginBottom: 4 }}>
              {LABELS[key]} ({val.date})
            </div>
            <div style={{ color: '#1e40af', fontSize: 24, fontWeight: 800, letterSpacing: -0.5 }}>
              ₩{val.price.toLocaleString()}
            </div>

            {diff !== null && (
              <div style={{ marginTop: 7, fontSize: 13, color: rising ? '#dc2626' : '#16a34a', fontWeight: 600 }}>
                현재 대비 {rising ? '▲' : '▼'} ₩{Math.abs(diff).toLocaleString()}
                <span style={{ marginLeft: 4, fontWeight: 400, opacity: 0.8 }}>
                  ({diffPct > 0 ? '+' : ''}{diffPct.toFixed(1)}%)
                </span>
              </div>
            )}

            {vsTarget !== null && (
              <div style={{
                marginTop: 5, fontSize: 12,
                color: vsTarget <= 0 ? '#15803d' : '#64748b',
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
