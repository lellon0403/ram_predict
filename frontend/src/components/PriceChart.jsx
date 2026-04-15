import {
  ComposedChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ReferenceLine,
  ResponsiveContainer,
  ReferenceDot,
} from 'recharts'

const CustomTooltip = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null
  return (
    <div style={{
      background: '#fff', border: '1.5px solid #bfdbfe',
      borderRadius: 10, padding: '10px 14px', color: '#1e293b', fontSize: 13,
      boxShadow: '0 4px 12px rgba(37,99,235,0.12)',
    }}>
      <p style={{ margin: '0 0 6px', color: '#64748b', fontWeight: 600 }}>{label}</p>
      {payload.map((p) => (
        <p key={p.name} style={{ margin: '2px 0', color: p.color }}>
          {p.name}: <strong>₩{Number(p.value).toLocaleString()}</strong>
        </p>
      ))}
    </div>
  )
}

export default function PriceChart({ history, forecast, predictions, targetPrice }) {
  // 최근 90일 히스토리 + 90일 예측 병합
  const recentHistory = history.slice(-90)

  const chartData = [
    ...recentHistory.map((d) => ({ date: d.date.slice(5), actual: d.price, forecast: null })),
    ...forecast.map((d) => ({ date: d.date.slice(5), actual: null, forecast: d.price })),
  ]

  // 예측 마커용 dots
  const dots = predictions
    ? [
        { date: predictions['1week'].date.slice(5),   price: predictions['1week'].price,   label: '1주일' },
        { date: predictions['1month'].date.slice(5),  price: predictions['1month'].price,  label: '1개월' },
      ]
    : []

  const allPrices = chartData.flatMap((d) => [d.actual, d.forecast, targetPrice].filter(Boolean))
  const minY = Math.floor(Math.min(...allPrices) * 0.92 / 1000) * 1000
  const maxY = Math.ceil(Math.max(...allPrices)  * 1.05 / 1000) * 1000

  return (
    <div style={{ width: '100%', height: 380 }}>
      <ResponsiveContainer>
        <ComposedChart data={chartData} margin={{ top: 10, right: 20, left: 10, bottom: 0 }}>
          <defs>
            <linearGradient id="actualGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%"  stopColor="#3b82f6" stopOpacity={0.25} />
              <stop offset="95%" stopColor="#3b82f6" stopOpacity={0.02} />
            </linearGradient>
            <linearGradient id="forecastGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%"  stopColor="#f97316" stopOpacity={0.2} />
              <stop offset="95%" stopColor="#f97316" stopOpacity={0.02} />
            </linearGradient>
          </defs>

          <CartesianGrid stroke="#1e293b" strokeDasharray="3 3" />
          <XAxis
            dataKey="date"
            tick={{ fill: '#64748b', fontSize: 11 }}
            tickLine={false}
            interval={14}
          />
          <YAxis
            tickFormatter={(v) => `${(v / 10000).toFixed(0)}만`}
            tick={{ fill: '#64748b', fontSize: 11 }}
            tickLine={false}
            domain={[minY, maxY]}
            width={52}
          />
          <Tooltip content={<CustomTooltip />} />
          <Legend
            wrapperStyle={{ paddingTop: 12, fontSize: 13, color: '#94a3b8' }}
            formatter={(val) => <span style={{ color: '#94a3b8' }}>{val}</span>}
          />

          {/* 히스토리 */}
          <Area
            type="monotone"
            dataKey="actual"
            name="실제 가격"
            stroke="#3b82f6"
            strokeWidth={2}
            fill="url(#actualGrad)"
            dot={false}
            connectNulls={false}
          />

          {/* 예측 */}
          <Area
            type="monotone"
            dataKey="forecast"
            name="예측 가격"
            stroke="#f97316"
            strokeWidth={2}
            strokeDasharray="6 3"
            fill="url(#forecastGrad)"
            dot={false}
            connectNulls={false}
          />

          {/* 목표 가격 기준선 */}
          {targetPrice && (
            <ReferenceLine
              y={targetPrice}
              stroke="#22c55e"
              strokeWidth={2}
              strokeDasharray="8 4"
              label={{ value: `목표 ₩${targetPrice.toLocaleString()}`, fill: '#22c55e', fontSize: 12, position: 'insideTopRight' }}
            />
          )}

          {/* 예측 마커 */}
          {dots.map((d) => (
            <ReferenceDot
              key={d.label}
              x={d.date}
              y={d.price}
              r={5}
              fill="#f97316"
              stroke="#fff"
              strokeWidth={2}
              label={{ value: d.label, fill: '#f97316', fontSize: 11, position: 'top' }}
            />
          ))}
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  )
}
