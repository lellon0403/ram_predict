const fmtW = (n) => `₩${Number(n).toLocaleString()}`

function calcRecommendation(targetPrice, currentPrice, pred1w, pred1m, pred3m) {
  const trend = pred3m - currentPrice  // 양수 = 3개월 뒤 상승세

  // ── 현재가가 이미 목표가 이하 ──────────────────────────────────────────────
  if (currentPrice <= targetPrice) {
    if (pred1w > currentPrice * 1.02) {
      // 1주 뒤 오를 것 같으면 지금 바로 구매
      return {
        badge: '✅ 지금 구매 추천',
        icon: '🛒', title: '지금 사세요!',
        subtitle: `현재가(${fmtW(currentPrice)})가 목표가(${fmtW(targetPrice)}) 이하입니다. 1주일 뒤 가격이 오를 것으로 예측됩니다.`,
        detail: `1주일 뒤 예측: ${fmtW(pred1w)} (+${((pred1w/currentPrice-1)*100).toFixed(1)}%)`,
        bg: '#f0fdf4', border: '#16a34a', text: '#14532d',
      }
    }
    return {
      badge: '✅ 구매 가능',
      icon: '👍', title: '목표가 도달!',
      subtitle: `현재가(${fmtW(currentPrice)})가 목표가(${fmtW(targetPrice)}) 이하입니다.`,
      detail: '단, 가격이 더 내려갈 수도 있어 아래 예측 카드도 참고하세요.',
      bg: '#f0fdf4', border: '#16a34a', text: '#14532d',
    }
  }

  // ── 1주일 뒤 목표가 도달 ──────────────────────────────────────────────────
  if (pred1w <= targetPrice) {
    return {
      badge: '⏰ 1주일 내 구매 추천',
      icon: '📅', title: '1주일 내 구매 타이밍입니다',
      subtitle: `1주일 후 예측가(${fmtW(pred1w)})가 목표가(${fmtW(targetPrice)}) 이하로 예측됩니다.`,
      detail: `현재가 ${fmtW(currentPrice)} → 1주일 뒤 ${fmtW(pred1w)} (${((pred1w/currentPrice-1)*100).toFixed(1)}%)`,
      bg: '#f0fdf4', border: '#16a34a', text: '#14532d',
    }
  }

  // ── 1개월 뒤 목표가 도달 ──────────────────────────────────────────────────
  if (pred1m <= targetPrice) {
    return {
      badge: '🗓️ 1개월 내 구매 추천',
      icon: '🗓️', title: '한 달 안에 구매 기회가 옵니다',
      subtitle: `1개월 후 예측가(${fmtW(pred1m)})가 목표가(${fmtW(targetPrice)}) 이하로 예측됩니다.`,
      detail: `현재가 ${fmtW(currentPrice)} → 1개월 뒤 ${fmtW(pred1m)} (${((pred1m/currentPrice-1)*100).toFixed(1)}%)`,
      bg: '#eff6ff', border: '#2563eb', text: '#1e3a8a',
    }
  }

  // ── 3개월 뒤 목표가 도달 ──────────────────────────────────────────────────
  if (pred3m <= targetPrice) {
    return {
      badge: '🔭 3개월 내 구매 추천',
      icon: '🔭', title: '3개월 안에 구매 기회가 올 수 있습니다',
      subtitle: `3개월 후 예측가(${fmtW(pred3m)})가 목표가(${fmtW(targetPrice)}) 이하로 예측됩니다.`,
      detail: `현재가 ${fmtW(currentPrice)} → 3개월 뒤 ${fmtW(pred3m)} (${((pred3m/currentPrice-1)*100).toFixed(1)}%)`,
      bg: '#eff6ff', border: '#6366f1', text: '#1e1b4b',
    }
  }

  // ── 3개월 내 목표가 달성 불가 + 상승세 ────────────────────────────────────
  if (trend > currentPrice * 0.03) {
    return {
      badge: '📈 지금 구매가 유리',
      icon: '📈', title: '가격이 계속 오를 것으로 예측됩니다',
      subtitle: `3개월 내 목표가(${fmtW(targetPrice)}) 달성이 어려우며, 가격은 계속 상승할 것으로 보입니다.`,
      detail: `현재 ${fmtW(currentPrice)} → 3개월 뒤 ${fmtW(pred3m)} — 지금이 상대적으로 저렴합니다.`,
      bg: '#fff7ed', border: '#ea580c', text: '#7c2d12',
    }
  }

  // ── 목표가 달성 불가 ───────────────────────────────────────────────────────
  return {
    badge: '🚫 구매 비추천',
    icon: '⏳', title: '아직 기다리세요',
    subtitle: `3개월 내에 목표가(${fmtW(targetPrice)}) 도달이 어렵습니다. 목표가를 조정하거나 더 기다려보세요.`,
    detail: `현재가 ${fmtW(currentPrice)} | 목표가까지 ${fmtW(currentPrice - targetPrice)} 차이`,
    bg: '#fef2f2', border: '#dc2626', text: '#7f1d1d',
  }
}

export default function Recommendation({ targetPrice, currentPrice, predictions }) {
  if (!targetPrice || !currentPrice || !predictions) return null

  const rec = calcRecommendation(
    targetPrice,
    currentPrice,
    predictions['1week']?.price,
    predictions['1month']?.price,
    predictions['3months']?.price,
  )

  const barPct = Math.min(100, (Math.min(targetPrice, currentPrice) / Math.max(targetPrice, currentPrice)) * 100)

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
          <div style={{ fontSize: 20, fontWeight: 800, marginBottom: 6 }}>{rec.title}</div>
          <div style={{ fontSize: 14, lineHeight: 1.65, opacity: 0.9, marginBottom: 4 }}>{rec.subtitle}</div>
          <div style={{ fontSize: 12.5, opacity: 0.7, fontStyle: 'italic' }}>{rec.detail}</div>
        </div>
      </div>

      {/* 현재가 vs 목표가 비교 바 */}
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
