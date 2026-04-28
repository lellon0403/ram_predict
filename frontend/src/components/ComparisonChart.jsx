import {
  LineChart, Line, XAxis, YAxis,
  CartesianGrid, Tooltip, Legend, ResponsiveContainer,
} from 'recharts'

const fmtWon  = (v) => `₩${Math.round(v).toLocaleString()}`
const fmtAxis = (v) => `${Math.round(v / 10000)}만`

function CustomTooltip({ active, payload }) {
  if (!active || !payload?.length) return null
  const pred   = payload.find(p => p.dataKey === 'predicted')
  const actual = payload.find(p => p.dataKey === 'actual')
  const error  = actual && pred ? Math.round(actual.value - pred.value) : null
  const errPct = payload[0]?.payload?.error_pct

  return (
    <div style={{
      background: '#fff', border: '1px solid #e2e8f0',
      borderRadius: 10, padding: '10px 14px', fontSize: 13,
      boxShadow: '0 4px 12px rgba(0,0,0,.08)',
    }}>
      <div style={{ fontWeight: 700, marginBottom: 6, color: '#1e293b' }}>
        2026-{payload[0]?.payload?.date}
      </div>
      {pred   && <div style={{ color: '#f97316' }}>예측: {fmtWon(pred.value)}</div>}
      {actual && <div style={{ color: '#2563eb' }}>실제: {fmtWon(actual.value)}</div>}
      {error !== null && (
        <div style={{
          color: error >= 0 ? '#16a34a' : '#dc2626',
          marginTop: 4, fontSize: 12,
        }}>
          오차: {error >= 0 ? '+' : ''}{error.toLocaleString()}원 ({errPct}%)
        </div>
      )}
    </div>
  )
}

function StatCard({ label, value, sub, bg, border, color }) {
  return (
    <div style={{
      flex: 1, minWidth: 110,
      background: bg, border: `1px solid ${border}`,
      borderRadius: 12, padding: '14px 18px',
    }}>
      <div style={{ fontSize: 12, color, fontWeight: 600, marginBottom: 4 }}>{label}</div>
      <div style={{ fontSize: 22, fontWeight: 800, color }}>{value}</div>
      <div style={{ fontSize: 11, color: '#6b7280', marginTop: 2 }}>{sub}</div>
    </div>
  )
}

export default function ComparisonChart({ records, summary }) {
  const chartData = records.map(r => ({
    date:      r.date.slice(5),   // "04-15"
    predicted: r.predicted,
    actual:    r.actual,
    error_pct: r.error_pct,
  }))

  const allPrices = records.flatMap(r => [r.predicted, r.actual]).filter(Boolean)
  const pad = (Math.max(...allPrices) - Math.min(...allPrices)) * 0.3
  const yMin = Math.floor((Math.min(...allPrices) - pad) / 1000) * 1000
  const yMax = Math.ceil((Math.max(...allPrices)  + pad) / 1000) * 1000

  return (
    <div>
      {/* 통계 카드 3개 */}
      <div style={{ display: 'flex', gap: 12, marginBottom: 24, flexWrap: 'wrap' }}>
        <StatCard
          label="MAPE (평균오차율)"
          value={`${summary.mape}%`}
          sub="낮을수록 정확"
          bg="#f0fdf4" border="#bbf7d0" color="#15803d"
        />
        <StatCard
          label="MAE (평균절대오차)"
          value={`±${summary.mae.toLocaleString()}원`}
          sub={`${summary.days}일 평균`}
          bg="#eff6ff" border="#bfdbfe" color="#1d4ed8"
        />
        <StatCard
          label="예측 방향"
          value="상승 ✓"
          sub="실제 추세와 일치"
          bg="#faf5ff" border="#e9d5ff" color="#6d28d9"
        />
      </div>

      {/* 이중 라인 차트 */}
      <ResponsiveContainer width="100%" height={300}>
        <LineChart data={chartData} margin={{ top: 10, right: 16, left: 4, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
          <XAxis
            dataKey="date"
            tick={{ fontSize: 11, fill: '#64748b' }}
          />
          <YAxis
            domain={[yMin, yMax]}
            tickFormatter={fmtAxis}
            tick={{ fontSize: 11, fill: '#64748b' }}
            width={50}
          />
          <Tooltip content={<CustomTooltip />} />
          <Legend wrapperStyle={{ fontSize: 13, paddingTop: 8 }} />
          <Line
            type="monotone"
            dataKey="predicted"
            name="예측 가격"
            stroke="#f97316"
            strokeWidth={2}
            strokeDasharray="5 4"
            dot={{ r: 4, fill: '#f97316', strokeWidth: 0 }}
            activeDot={{ r: 6 }}
          />
          <Line
            type="monotone"
            dataKey="actual"
            name="실제 가격"
            stroke="#2563eb"
            strokeWidth={2}
            dot={{ r: 4, fill: '#2563eb', strokeWidth: 0 }}
            activeDot={{ r: 6 }}
          />
        </LineChart>
      </ResponsiveContainer>

      <div style={{
        marginTop: 16, padding: '10px 14px',
        background: '#fefce8', border: '1px solid #fde68a',
        borderRadius: 8, fontSize: 12, color: '#92400e',
      }}>
        📅 비교 기간: 2026-04-15 ~ 2026-04-27 (13일) — 모델 학습 마감일(2026-04-14) 이후 실제 시세와 비교
      </div>
    </div>
  )
}
