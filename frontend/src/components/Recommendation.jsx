/**
 * 구매 추천 로직
 *
 * targetPrice  : 사용자가 원하는 구매 가격 (원화)
 * currentPrice : 오늘 실제 가격
 * pred1d / pred1w / pred1m : 1일·1주·1개월 예측 가격
 */
function calcRecommendation(targetPrice, currentPrice, pred1d, pred1w, pred1m) {
  const fmtW = (n) => `₩${Number(n).toLocaleString()}`
  const trend3m = pred1m - currentPrice   // 양수 = 상승세

  // ── 현재 가격이 목표가 이하 ──────────────────────────────────────────────
  if (currentPrice <= targetPrice) {
    // 내일 더 내릴 것 같으면 조금 기다려
    if (pred1d < currentPrice * 0.98) {
      return {
        level: 'wait_short',
        icon: '⏳',
        title: '하루만 더 기다려 보세요',
        subtitle: `오늘 가격(${fmtW(currentPrice)})이 목표가 이하지만 내일 더 내릴 것으로 예측됩니다.`,
        detail: `내일 예측: ${fmtW(pred1d)}`,
        bg: '#fef9c3', border: '#eab308', text: '#713f12',
        badge: '⚠️ 단기 대기',
      }
    }
    return {
      level: 'buy_now',
      icon: '🛒',
      title: '지금 사세요!',
      subtitle: `현재 가격(${fmtW(currentPrice)})이 목표가(${fmtW(targetPrice)})보다 저렴합니다.`,
      detail: `앞으로 가격이 오를 것으로 예측되어 지금이 최적 타이밍입니다.`,
      bg: '#dcfce7', border: '#16a34a', text: '#14532d',
      badge: '✅ 구매 추천',
    }
  }

  // ── 1일 안에 목표가 도달 ──────────────────────────────────────────────────
  if (pred1d <= targetPrice) {
    return {
      level: 'wait_1d',
      icon: '⏰',
      title: '하루만 기다리세요!',
      subtitle: `내일 가격이 목표가(${fmtW(targetPrice)})에 도달할 것으로 예측됩니다.`,
      detail: `내일 예측: ${fmtW(pred1d)}`,
      bg: '#dcfce7', border: '#16a34a', text: '#14532d',
      badge: '✅ 내일 구매 추천',
    }
  }

  // ── 1주일 안에 목표가 도달 ────────────────────────────────────────────────
  if (pred1w <= targetPrice) {
    const gap = currentPrice - pred1w
    return {
      level: 'wait_1w',
      icon: '📅',
      title: '1주일 내 구매 타이밍 옵니다',
      subtitle: `1주일 후 가격(${fmtW(pred1w)})이 목표가 이하로 예측됩니다.`,
      detail: `현재보다 약 ${fmtW(gap)} 하락 예상`,
      bg: '#dbeafe', border: '#2563eb', text: '#1e3a8a',
      badge: '🕐 1주일 대기 권장',
    }
  }

  // ── 1개월 안에 목표가 도달 ────────────────────────────────────────────────
  if (pred1m <= targetPrice) {
    return {
      level: 'wait_1m',
      icon: '🗓️',
      title: '한 달 내 구매 기회가 올 수 있어요',
      subtitle: `1개월 후 가격(${fmtW(pred1m)})이 목표가 이하로 예측됩니다.`,
      detail: `목표가까지 약 ₩${(currentPrice - targetPrice).toLocaleString()} 하락 필요`,
      bg: '#dbeafe', border: '#6366f1', text: '#1e1b4b',
      badge: '🗓️ 1개월 대기 권장',
    }
  }

  // ── 3개월 내 목표가 달성 불가 + 상승세 ────────────────────────────────────
  if (trend3m > currentPrice * 0.03) {
    return {
      level: 'buy_rising',
      icon: '📈',
      title: '지금 구매가 더 유리합니다',
      subtitle: `가격이 계속 오를 것으로 예측됩니다. 목표가(${fmtW(targetPrice)})는 3개월 내 도달이 어렵습니다.`,
      detail: `3개월 후 예측 ${fmtW(pred1m)} → 지금(${fmtW(currentPrice)})이 상대적으로 저렴`,
      bg: '#ffedd5', border: '#ea580c', text: '#7c2d12',
      badge: '📈 상승세 전 구매',
    }
  }

  // ── 목표가 달성 불가, 하락도 없음 ────────────────────────────────────────
  return {
    level: 'not_yet',
    icon: '🚫',
    title: '아직 구매하지 마세요',
    subtitle: `3개월 내에 목표가(${fmtW(targetPrice)})에 도달하기 어려울 것으로 보입니다.`,
    detail: `현재가 ${fmtW(currentPrice)} | 목표가까지 ₩${(currentPrice - targetPrice).toLocaleString()} 필요`,
    bg: '#fee2e2', border: '#dc2626', text: '#7f1d1d',
    badge: '🚫 구매 비추천',
  }
}

export default function Recommendation({ targetPrice, currentPrice, predictions }) {
  if (!targetPrice || !currentPrice || !predictions) {
    return (
      <div style={{
        background: '#1e293b', borderRadius: 14, padding: '28px 30px',
        border: '1px solid #334155', textAlign: 'center', color: '#64748b',
      }}>
        <div style={{ fontSize: 36, marginBottom: 10 }}>💬</div>
        <div style={{ fontSize: 15 }}>구매 희망 가격을 입력하면 구매 추천 여부를 알려드릴게요</div>
      </div>
    )
  }

  const rec = calcRecommendation(
    targetPrice,
    currentPrice,
    predictions['1week'].price,   // 1일 예측 없으면 1주로 대체
    predictions['1week'].price,
    predictions['1month'].price,
  )

  return (
    <div style={{
      borderRadius: 16,
      padding: '28px 30px',
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
        padding: '3px 14px',
        fontSize: 13,
        fontWeight: 700,
        marginBottom: 14,
        letterSpacing: 0.3,
      }}>
        {rec.badge}
      </div>

      <div style={{ display: 'flex', alignItems: 'flex-start', gap: 16 }}>
        <div style={{ fontSize: 48, lineHeight: 1 }}>{rec.icon}</div>
        <div>
          <h2 style={{ margin: '0 0 6px', fontSize: 22, fontWeight: 800 }}>{rec.title}</h2>
          <p style={{ margin: '0 0 8px', fontSize: 15, lineHeight: 1.6, opacity: 0.9 }}>{rec.subtitle}</p>
          <p style={{ margin: 0, fontSize: 13, opacity: 0.75, fontStyle: 'italic' }}>{rec.detail}</p>
        </div>
      </div>

      {/* 비교 바 */}
      <div style={{ marginTop: 20, background: 'rgba(0,0,0,.08)', borderRadius: 8, padding: '12px 16px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 13, marginBottom: 8 }}>
          <span>현재가: <strong>₩{currentPrice.toLocaleString()}</strong></span>
          <span>목표가: <strong>₩{targetPrice.toLocaleString()}</strong></span>
        </div>
        <div style={{ background: 'rgba(0,0,0,.15)', borderRadius: 999, height: 8, overflow: 'hidden' }}>
          <div style={{
            height: '100%',
            width: `${Math.min(100, (targetPrice / Math.max(currentPrice, targetPrice)) * 100)}%`,
            background: rec.border,
            borderRadius: 999,
            transition: 'width .4s ease',
          }} />
        </div>
        <div style={{ textAlign: 'center', marginTop: 8, fontSize: 13, fontWeight: 600 }}>
          {currentPrice > targetPrice
            ? `현재가가 목표가보다 ₩${(currentPrice - targetPrice).toLocaleString()} 비쌉니다`
            : `현재가가 목표가보다 ₩${(targetPrice - currentPrice).toLocaleString()} 저렴합니다 🎉`}
        </div>
      </div>
    </div>
  )
}
