// 순서를 명시적으로 고정 (Object.entries 알파벳 정렬 방지)
const ORDER  = ['1week', '1month', '3months']
const LABELS = { '1week': '1주일 뒤', '1month': '1개월 뒤', '3months': '3개월 뒤' }
const ICONS  = { '1week': '📅', '1month': '🗓️', '3months': '🔭' }

export default function PredictionCards({ predictions, currentPrice, targetPrice }) {
  if (!predictions) return null

  // 목표가 이하인 첫 번째 구간 찾기 (구매 추천 강조용)
  const firstBuyPeriod = targetPrice
    ? ORDER.find((key) => predictions[key]?.price <= targetPrice)
    : null

  return (
    <div style={{ display: 'flex', gap: 14, flexWrap: 'wrap' }}>
      {ORDER.map((key) => {
        const val = predictions[key]
        if (!val) return null

        const diff     = currentPrice ? val.price - currentPrice : null
        const diffPct  = currentPrice ? ((val.price - currentPrice) / currentPrice * 100) : null
        const vsTarget = targetPrice ? val.price - targetPrice : null
        const rising   = diff !== null && diff > 0
        const isBuyRec = targetPrice && val.price <= targetPrice  // 목표가 이하 → 구매 추천

        return (
          <div key={key} style={{
            flex: '1 1 200px',
            background: isBuyRec ? '#f0fdf4' : '#f8faff',
            borderRadius: 12,
            padding: '18px 20px',
            border: isBuyRec
              ? '2px solid #16a34a'
              : `1.5px solid ${rising ? '#fca5a5' : '#bfdbfe'}`,
            boxShadow: isBuyRec
              ? '0 4px 14px rgba(22,163,74,0.15)'
              : '0 2px 8px rgba(37,99,235,0.06)',
            position: 'relative',
            transition: 'all .2s',
          }}>
            {/* 구매 추천 배지 */}
            {isBuyRec && (
              <div style={{
                position: 'absolute',
                top: -1,
                right: 12,
                background: '#16a34a',
                color: '#fff',
                fontSize: 11,
                fontWeight: 700,
                padding: '3px 10px',
                borderRadius: '0 0 8px 8px',
                letterSpacing: 0.3,
              }}>
                ✅ 구매 추천
              </div>
            )}

            {/* 첫 번째 구매 추천 구간 강조 */}
            {isBuyRec && key === firstBuyPeriod && (
              <div style={{
                marginBottom: 8,
                background: '#dcfce7',
                border: '1px solid #86efac',
                borderRadius: 6,
                padding: '5px 10px',
                fontSize: 12,
                color: '#14532d',
                fontWeight: 600,
              }}>
                🏆 이 시기가 구매 최적 타이밍입니다!
              </div>
            )}

            <div style={{ fontSize: 20, marginBottom: 5 }}>{ICONS[key]}</div>
            <div style={{ color: '#64748b', fontSize: 12.5, marginBottom: 4 }}>
              {LABELS[key]} ({val.date})
            </div>
            <div style={{
              color: isBuyRec ? '#15803d' : '#1e40af',
              fontSize: 24,
              fontWeight: 800,
              letterSpacing: -0.5,
            }}>
              ₩{val.price.toLocaleString()}
            </div>

            {/* 현재가 대비 */}
            {diff !== null && (
              <div style={{
                marginTop: 7, fontSize: 13,
                color: rising ? '#dc2626' : '#16a34a',
                fontWeight: 600,
              }}>
                현재 대비 {rising ? '▲' : '▼'} ₩{Math.abs(diff).toLocaleString()}
                <span style={{ marginLeft: 4, fontWeight: 400, opacity: 0.8 }}>
                  ({diffPct > 0 ? '+' : ''}{diffPct.toFixed(1)}%)
                </span>
              </div>
            )}

            {/* 목표가 대비 */}
            {vsTarget !== null && (
              <div style={{
                marginTop: 5,
                fontSize: 12,
                color: vsTarget <= 0 ? '#15803d' : '#64748b',
                fontWeight: vsTarget <= 0 ? 700 : 400,
              }}>
                {vsTarget <= 0
                  ? `🎯 목표가보다 ₩${Math.abs(vsTarget).toLocaleString()} 저렴`
                  : `목표가까지 ₩${vsTarget.toLocaleString()} 남음`}
              </div>
            )}
          </div>
        )
      })}
    </div>
  )
}
