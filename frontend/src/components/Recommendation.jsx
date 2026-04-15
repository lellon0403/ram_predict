const fmtW = (n) => `₩${Number(Math.round(n)).toLocaleString()}`

/**
 * forecast 배열에서 기간(days) 내 목표가 이하인 날 중 최저가 날 반환
 * 없으면 null
 */
function findBestDay(forecast, targetPrice, fromDay, toDay) {
  const window = forecast.slice(fromDay, toDay)
  const below  = window.filter((d) => d.price <= targetPrice)
  if (!below.length) return null
  // 목표가 이하 중 가장 저렴한 날
  return below.reduce((a, b) => (a.price < b.price ? a : b))
}

/**
 * 기간(days) 내 최저가 날 반환 (목표가 관계없이)
 */
function findMinDay(forecast, fromDay, toDay) {
  const window = forecast.slice(fromDay, toDay)
  if (!window.length) return null
  return window.reduce((a, b) => (a.price < b.price ? a : b))
}

function calcRecommendation(targetPrice, currentPrice, forecast) {
  if (!forecast?.length) return null

  // 기간별 최적 매수일 탐색
  const bestIn1w  = findBestDay(forecast, targetPrice, 0, 7)    // 1주일 내
  const bestIn1m  = findBestDay(forecast, targetPrice, 0, 30)   // 1개월 내
  const bestIn3m  = findBestDay(forecast, targetPrice, 0, 90)   // 3개월 내

  // 기간별 최저가 날 (목표가 무관)
  const minIn1w   = findMinDay(forecast, 0, 7)
  const minIn3m   = findMinDay(forecast, 0, 90)

  const trend3m   = forecast[89]?.price - currentPrice   // 3개월 상승분

  // ── 현재가가 이미 목표가 이하 ──────────────────────────────────────────
  if (currentPrice <= targetPrice) {
    // 1주 내 더 낮은 날이 있으면 그날 추천
    if (bestIn1w && bestIn1w.price < currentPrice) {
      const daysUntil = forecast.findIndex((d) => d.date === bestIn1w.date) + 1
      return {
        badge: '⏳ 잠깐만 기다리세요',
        icon: '📉', title: `${bestIn1w.date} (${daysUntil}일 뒤) 구매를 추천합니다`,
        subtitle: `현재가(${fmtW(currentPrice)})보다 더 저렴한 날이 1주일 내에 예측됩니다.`,
        detail: `${bestIn1w.date} 예측 최저가: ${fmtW(bestIn1w.price)} — 현재보다 ${fmtW(currentPrice - bestIn1w.price)} 저렴`,
        bg: '#f0fdf4', border: '#16a34a', text: '#14532d',
      }
    }
    return {
      badge: '✅ 지금 구매 추천',
      icon: '🛒', title: '지금 사세요!',
      subtitle: `현재가(${fmtW(currentPrice)})가 목표가(${fmtW(targetPrice)}) 이하입니다. 앞으로 오를 가능성이 높습니다.`,
      detail: `1주일 내 최저 예측: ${fmtW(minIn1w?.price)} (${minIn1w?.date})`,
      bg: '#f0fdf4', border: '#16a34a', text: '#14532d',
    }
  }

  // ── 1주일 내 어느 날이든 목표가 이하 ────────────────────────────────────
  if (bestIn1w) {
    const daysUntil = forecast.findIndex((d) => d.date === bestIn1w.date) + 1
    return {
      badge: `⏰ ${daysUntil}일 뒤 구매 추천`,
      icon: '📅',
      title: `${bestIn1w.date} (${daysUntil}일 뒤)에 구매하세요`,
      subtitle: `1주일 내 목표가(${fmtW(targetPrice)}) 이하로 내려가는 날이 예측됩니다.`,
      detail: `해당일 예측가: ${fmtW(bestIn1w.price)} — 목표가보다 ${fmtW(targetPrice - bestIn1w.price)} 저렴`,
      bg: '#f0fdf4', border: '#16a34a', text: '#14532d',
    }
  }

  // ── 1개월 내 어느 날이든 목표가 이하 ────────────────────────────────────
  if (bestIn1m) {
    const daysUntil = forecast.findIndex((d) => d.date === bestIn1m.date) + 1
    return {
      badge: `🗓️ ${daysUntil}일 뒤 구매 추천`,
      icon: '🗓️',
      title: `${bestIn1m.date} (${daysUntil}일 뒤)에 구매 기회가 옵니다`,
      subtitle: `1개월 내 목표가(${fmtW(targetPrice)}) 이하로 내려가는 날이 예측됩니다.`,
      detail: `해당일 예측가: ${fmtW(bestIn1m.price)} — 목표가보다 ${fmtW(targetPrice - bestIn1m.price)} 저렴`,
      bg: '#eff6ff', border: '#2563eb', text: '#1e3a8a',
    }
  }

  // ── 3개월 내 어느 날이든 목표가 이하 ────────────────────────────────────
  if (bestIn3m) {
    const daysUntil = forecast.findIndex((d) => d.date === bestIn3m.date) + 1
    return {
      badge: `🔭 ${daysUntil}일 뒤 구매 추천`,
      icon: '🔭',
      title: `${bestIn3m.date} (${daysUntil}일 뒤)에 구매 기회가 옵니다`,
      subtitle: `3개월 내 목표가(${fmtW(targetPrice)}) 이하로 내려가는 날이 예측됩니다.`,
      detail: `해당일 예측가: ${fmtW(bestIn3m.price)} — 목표가보다 ${fmtW(targetPrice - bestIn3m.price)} 저렴`,
      bg: '#eff6ff', border: '#6366f1', text: '#1e1b4b',
    }
  }

  // ── 3개월 내 목표가 달성 불가 + 상승세 ──────────────────────────────────
  if (trend3m > currentPrice * 0.03) {
    return {
      badge: '📈 지금 구매가 유리',
      icon: '📈',
      title: '가격이 계속 오를 것으로 예측됩니다',
      subtitle: `3개월 내 목표가(${fmtW(targetPrice)}) 달성이 어렵고, 가격은 계속 상승할 것으로 보입니다.`,
      detail: `3개월 내 최저 예측: ${fmtW(minIn3m?.price)} (${minIn3m?.date}) — 지금이 상대적으로 저렴합니다`,
      bg: '#fff7ed', border: '#ea580c', text: '#7c2d12',
    }
  }

  // ── 목표가 달성 불가, 하락도 없음 ────────────────────────────────────────
  return {
    badge: '🚫 구매 비추천',
    icon: '⏳',
    title: '아직 기다리세요',
    subtitle: `3개월 내에 목표가(${fmtW(targetPrice)}) 도달이 어렵습니다. 목표가를 조정하거나 더 기다려보세요.`,
    detail: `3개월 내 최저 예측: ${fmtW(minIn3m?.price)} (${minIn3m?.date})`,
    bg: '#fef2f2', border: '#dc2626', text: '#7f1d1d',
  }
}

export default function Recommendation({ targetPrice, currentPrice, forecast }) {
  if (!targetPrice || !currentPrice) return null

  const rec = calcRecommendation(targetPrice, currentPrice, forecast)
  if (!rec) return null

  const barPct = Math.min(100,
    (Math.min(targetPrice, currentPrice) / Math.max(targetPrice, currentPrice)) * 100
  )

  return (
    <div style={{
      borderRadius: 14,
      padding: '22px 24px',
      background: rec.bg,
      border: `2px solid ${rec.border}`,
      color: rec.text,
    }}>
      {/* 배지 */}
      <div style={{
        display: 'inline-block',
        background: rec.border,
        color: '#fff',
        borderRadius: 20,
        padding: '4px 14px',
        fontSize: 12.5,
        fontWeight: 700,
        marginBottom: 14,
        letterSpacing: 0.3,
      }}>
        {rec.badge}
      </div>

      <div style={{ display: 'flex', alignItems: 'flex-start', gap: 14 }}>
        <div style={{ fontSize: 44, lineHeight: 1, flexShrink: 0 }}>{rec.icon}</div>
        <div>
          <div style={{ fontSize: 19, fontWeight: 800, marginBottom: 6 }}>{rec.title}</div>
          <div style={{ fontSize: 14, lineHeight: 1.65, opacity: 0.9, marginBottom: 4 }}>{rec.subtitle}</div>
          <div style={{ fontSize: 12.5, opacity: 0.7, fontStyle: 'italic' }}>{rec.detail}</div>
        </div>
      </div>

      {/* 현재가 vs 목표가 바 */}
      <div style={{
        marginTop: 18,
        background: 'rgba(0,0,0,.06)',
        borderRadius: 8,
        padding: '12px 14px',
      }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 13, marginBottom: 8 }}>
          <span>현재가: <strong>{fmtW(currentPrice)}</strong></span>
          <span>목표가: <strong>{fmtW(targetPrice)}</strong></span>
        </div>
        <div style={{ background: 'rgba(0,0,0,.12)', borderRadius: 999, height: 8, overflow: 'hidden' }}>
          <div style={{
            height: '100%',
            width: `${barPct}%`,
            background: rec.border,
            borderRadius: 999,
            transition: 'width .4s ease',
          }} />
        </div>
        <div style={{ textAlign: 'center', marginTop: 8, fontSize: 13, fontWeight: 600 }}>
          {currentPrice > targetPrice
            ? `현재가가 목표가보다 ${fmtW(currentPrice - targetPrice)} 비쌉니다`
            : `현재가가 목표가보다 ${fmtW(targetPrice - currentPrice)} 저렴합니다 🎉`}
        </div>
      </div>
    </div>
  )
}
