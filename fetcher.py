"""실시간 시장 데이터 수집 및 매수 신호 계산."""

import yfinance as yf
import requests
import pandas as pd
from datetime import datetime

from config import TICKERS


def _safe(fn, label):
    try:
        return fn()
    except Exception as e:
        print(f"  [{label}] 오류: {e}")
        return None


def _to_str_index(df):
    """timezone-aware 인덱스를 문자열로 변환."""
    df = df.copy()
    df.index = df.index.strftime("%Y-%m-%d")
    return df


# ── 개별 지표 ──────────────────────────────────────────────────

def get_sp500():
    def _inner():
        tk = yf.Ticker(TICKERS["sp500"])
        h = tk.history(period="2y")
        if h.empty:
            return None

        current = float(h["Close"].iloc[-1])
        high_52w = float(h["High"].rolling(252).max().iloc[-1])
        dd = (current - high_52w) / high_52w * 100

        # 200일 이동평균 이격도
        ma200 = float(h["Close"].rolling(200).mean().iloc[-1])
        ma200_dev = (current - ma200) / ma200 * 100

        chart = _to_str_index(tk.history(period="max"))

        return {
            "current": round(current, 2),
            "high_52w": round(high_52w, 2),
            "drawdown": round(dd, 2),
            "ma200": round(ma200, 2),
            "ma200_dev": round(ma200_dev, 2),
            "chart": chart,
        }
    return _safe(_inner, "S&P500")


def get_kospi():
    def _inner():
        tk = yf.Ticker(TICKERS["kospi"])
        h = tk.history(period="2y")
        if h.empty:
            return None
        current = float(h["Close"].iloc[-1])
        high_52w = float(h["High"].rolling(252).max().iloc[-1])
        dd = (current - high_52w) / high_52w * 100
        chart = _to_str_index(tk.history(period="5y"))
        return {
            "current": round(current, 2),
            "high_52w": round(high_52w, 2),
            "drawdown": round(dd, 2),
            "chart": chart,
        }
    return _safe(_inner, "KOSPI")


def get_vix():
    def _inner():
        tk = yf.Ticker(TICKERS["vix"])
        h = tk.history(period="max")
        if h.empty:
            return None
        cur = float(h["Close"].iloc[-1])
        prev = float(h["Close"].iloc[-2])

        if cur >= 40:
            level, sig = "극단적 공포", "strong_buy"
        elif cur >= 30:
            level, sig = "높은 공포", "buy"
        elif cur >= 20:
            level, sig = "보통", "neutral"
        else:
            level, sig = "안정", "no_signal"

        chart = _to_str_index(h)

        return {
            "current": round(cur, 2),
            "change": round(cur - prev, 2),
            "level": level,
            "signal": sig,
            "chart": chart,
        }
    return _safe(_inner, "VIX")


def get_fear_greed():
    def _inner():
        url = "https://production.dataviz.cnn.io/index/fearandgreed/graphdata"
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}
        r = requests.get(url, headers=headers, timeout=10)
        d = r.json()["fear_and_greed"]
        score, prev = d["score"], d["previous_close"]

        if score <= 25:
            level, sig = "극단적 공포", "strong_buy"
        elif score <= 40:
            level, sig = "공포", "buy"
        elif score <= 60:
            level, sig = "중립", "neutral"
        elif score <= 75:
            level, sig = "탐욕", "no_signal"
        else:
            level, sig = "극단적 탐욕", "no_signal"

        return {
            "score": round(score, 1),
            "prev": round(prev, 1),
            "change": round(score - prev, 1),
            "level": level,
            "signal": sig,
        }
    return _safe(_inner, "공포탐욕")


def get_exchange_rate():
    def _inner():
        tk = yf.Ticker(TICKERS["krw_usd"])
        h = tk.history(period="1y")
        if h.empty:
            return None
        cur = float(h["Close"].iloc[-1])
        prev = float(h["Close"].iloc[-2])
        hi, lo = float(h["High"].max()), float(h["Low"].min())
        pos = (cur - lo) / (hi - lo) * 100

        if pos >= 80:
            level, sig = "원화 극약세", "buy"
        elif pos >= 60:
            level, sig = "원화 약세", "neutral"
        elif pos >= 35:
            level, sig = "보통", "no_signal"
        else:
            level, sig = "원화 강세", "no_signal"

        chart = _to_str_index(h)

        return {
            "current": round(cur, 2),
            "change": round(cur - prev, 2),
            "high_52w": round(hi, 2),
            "low_52w": round(lo, 2),
            "pos_52w": round(pos, 1),
            "level": level,
            "signal": sig,
            "chart": chart,
        }
    return _safe(_inner, "환율")


def get_kodex():
    def _inner():
        tk = yf.Ticker(TICKERS["kodex_sp500"])
        h = tk.history(period="1y")
        if h.empty:
            return None
        current = round(float(h["Close"].iloc[-1]), 0)
        ath = round(float(h["High"].max()), 0)
        return {"current": current, "ath": ath}
    return _safe(_inner, "KODEX S&P500")


def get_hyg_lqd():
    """HYG/LQD 스프레드 — 신용 스트레스 선행 지표.
    HYG(하이일드) 대비 LQD(투자등급) 가격 비율이 하락하면 신용 위험 증가.
    60일 평균 대비 현재 비율이 1.5% 이상 하락 시 스트레스 신호."""
    def _inner():
        hyg = yf.Ticker(TICKERS["hyg"]).history(period="6mo")
        lqd = yf.Ticker(TICKERS["lqd"]).history(period="6mo")
        if hyg.empty or lqd.empty:
            return None

        # 날짜 맞춰서 비율 계산
        df = pd.DataFrame({"hyg": hyg["Close"], "lqd": lqd["Close"]}).dropna()
        df["ratio"] = df["hyg"] / df["lqd"]
        avg_60 = df["ratio"].rolling(60).mean().iloc[-1]
        cur_ratio = df["ratio"].iloc[-1]
        dev = (cur_ratio - avg_60) / avg_60 * 100

        stressed = dev < -1.5

        return {
            "ratio": round(cur_ratio, 4),
            "avg_60": round(avg_60, 4),
            "dev_pct": round(dev, 2),
            "stressed": stressed,
            "label": f"{'스트레스 감지' if stressed else '정상'} ({dev:+.2f}%)",
        }
    return _safe(_inner, "HYG/LQD")


# ── 매수 신호 ──────────────────────────────────────────────────

def calc_signal(vix, fg, sp500, fx, hyg_lqd):
    """
    기본 100점: VIX(30) + 공포탐욕(25) + S&P500 낙폭(30) + 환율(15)
    보정 (100점 외):
      HYG/LQD 스프레드 스트레스 → +5
      200일선 이격: -5~-15% → +3, -15% 초과 → +5
    """
    score = 0
    details = {}

    # VIX — 30점
    if vix:
        v = vix["current"]
        s = 30 if v >= 45 else 26 if v >= 40 else 20 if v >= 35 else 15 if v >= 30 else 8 if v >= 25 else 3 if v >= 20 else 0
        score += s
        details["VIX"] = (s, 30)

    # 공포탐욕 — 25점
    if fg:
        f = fg["score"]
        s = 25 if f <= 15 else 20 if f <= 25 else 14 if f <= 35 else 7 if f <= 45 else 2 if f <= 55 else 0
        score += s
        details["공포탐욕"] = (s, 25)

    # S&P500 낙폭 — 30점
    if sp500:
        d = abs(sp500["drawdown"])
        s = 30 if d >= 35 else 25 if d >= 25 else 20 if d >= 20 else 14 if d >= 15 else 8 if d >= 10 else 3 if d >= 7 else 0
        score += s
        details["S&P500 낙폭"] = (s, 30)

    # 환율 — 15점 (60-80% 최적, 극약세 역감점)
    if fx:
        p = fx["pos_52w"]
        s = 15 if 60 <= p < 80 else 10 if 80 <= p < 90 else 5 if p >= 90 else 7 if 40 <= p < 60 else 0
        score += s
        details["환율"] = (s, 15)

    base_score = score

    # ── 보정 (100점 외) ──

    # HYG/LQD 스프레드 → +5
    hyg_bonus = 0
    if hyg_lqd and hyg_lqd["stressed"]:
        hyg_bonus = 5
        score += 5
    details["HYG/LQD 보정"] = (hyg_bonus, "+5")

    # 200일선 이격도 → +3 또는 +5
    ma_bonus = 0
    if sp500 and sp500.get("ma200_dev") is not None:
        dev = sp500["ma200_dev"]
        if dev <= -15:
            ma_bonus = 5
        elif dev <= -5:
            ma_bonus = 3
        score += ma_bonus
    details["200일선 보정"] = (ma_bonus, "+5")

    # ── 분석 텍스트 생성 ──
    analysis_parts = []

    if vix:
        v = vix["current"]
        vs = details["VIX"][0]
        if v >= 40:
            analysis_parts.append(f"VIX {v:.1f}은 극단적 공포 수준으로, 역사적으로 강한 매수 기회와 겹칩니다 ({vs}/30점).")
        elif v >= 30:
            analysis_parts.append(f"VIX {v:.1f}은 공포 구간(30+)에 진입했으나, 극단(40+) 수준에는 미달합니다 ({vs}/30점).")
        elif v >= 20:
            analysis_parts.append(f"VIX {v:.1f}은 보통 수준으로, 아직 뚜렷한 공포 신호가 아닙니다 ({vs}/30점).")
        else:
            analysis_parts.append(f"VIX {v:.1f}은 안정 구간으로, 시장에 공포가 없습니다 ({vs}/30점).")

    if fg:
        f = fg["score"]
        fs = details["공포탐욕"][0]
        if f <= 25:
            analysis_parts.append(f"공포탐욕지수 {f:.0f}은 극단적 공포 구간으로, 투자 심리가 극도로 위축되어 있습니다 ({fs}/25점).")
        elif f <= 40:
            analysis_parts.append(f"공포탐욕지수 {f:.0f}은 공포 구간이지만 극단은 아닙니다 ({fs}/25점).")
        else:
            analysis_parts.append(f"공포탐욕지수 {f:.0f}은 중립~탐욕 구간으로, 공포 신호 미약합니다 ({fs}/25점).")

    if sp500:
        d = abs(sp500["drawdown"])
        ss = details["S&P500 낙폭"][0]
        if d >= 20:
            analysis_parts.append(f"S&P500이 고점 대비 -{d:.1f}% 하락해 공식 베어마켓 진입. 역사적 매수 구간입니다 ({ss}/30점).")
        elif d >= 10:
            analysis_parts.append(f"S&P500 -{d:.1f}% 하락으로 조정(correction) 구간에 진입했습니다 ({ss}/30점).")
        elif d >= 7:
            analysis_parts.append(f"S&P500 -{d:.1f}% 하락은 경미한 조정 시작 수준입니다. 본격 진입 신호에는 부족합니다 ({ss}/30점).")
        else:
            analysis_parts.append(f"S&P500 -{d:.1f}% 하락은 정상 변동 범위로, 낙폭 점수가 반영되지 않습니다 ({ss}/30점).")

    if fx:
        p = fx["pos_52w"]
        fxs = details["환율"][0]
        if p >= 90:
            analysis_parts.append(f"원/달러 환율이 52주 범위 상위 {p:.0f}%로 극약세 구간. KODEX 매수 단가가 비싸 역감점이 적용됩니다 ({fxs}/15점).")
        elif p >= 60:
            analysis_parts.append(f"원/달러 환율이 52주 범위 상위 {p:.0f}%. 위기 맥락이 반영된 적정 구간입니다 ({fxs}/15점).")
        else:
            analysis_parts.append(f"원/달러 환율이 52주 범위 상위 {p:.0f}%로 안정적. 위기 신호가 약합니다 ({fxs}/15점).")

    if hyg_lqd:
        if hyg_lqd["stressed"]:
            analysis_parts.append(f"HYG/LQD 스프레드가 60일 평균 대비 {hyg_lqd['dev_pct']:+.2f}% 이탈해 신용 스트레스 감지. VIX 선행 신호로 +5점 보정.")
        else:
            analysis_parts.append(f"HYG/LQD 스프레드는 정상 범위({hyg_lqd['dev_pct']:+.2f}%). 신용 시장 스트레스 없음.")

    if sp500 and sp500.get("ma200_dev") is not None:
        dev = sp500["ma200_dev"]
        if dev <= -15:
            analysis_parts.append(f"200일 이평선 대비 {dev:+.1f}% 이격으로 심각한 추세 이탈. +5점 보정 적용.")
        elif dev <= -5:
            analysis_parts.append(f"200일 이평선 대비 {dev:+.1f}% 이격으로 추세 이탈 진행 중. +3점 보정 적용.")
        else:
            analysis_parts.append(f"200일 이평선 대비 {dev:+.1f}%로 아직 추세 내 위치. 이격 보정 해당 없음.")

    # 다음 단계 전환 조건
    next_thresholds = {70: "강력 매수", 50: "매수 고려", 30: "관망", 15: "중립"}
    for t, lbl in next_thresholds.items():
        if score < t:
            gap = t - score
            analysis_parts.append(f"현재 판정에서 '{lbl}'으로 전환하려면 {gap}점이 추가로 필요합니다.")
            break

    analysis = " ".join(analysis_parts)

    # 5단계 판정
    levels = [
        (70, "강력 매수", "#c0392b", "#fdf0f0", "복수 지표 극단적 공포. 금융위기·코로나 수준의 역사적 매수 구간."),
        (50, "매수 고려", "#e74c3c", "#fdf2f2", "상당한 공포 신호. 분할매수를 검토할 구간."),
        (30, "관망",     "#e67e22", "#fef9f0", "일부 신호 감지. 아직 진입 미달. 추이 모니터링."),
        (15, "중립",     "#f39c12", "#fffbf0", "공포 신호 미약. 대기."),
        (0,  "고점 근처", "#27ae60", "#f0fdf4", "공포 없음. 본 전략 매수 타이밍 아님."),
    ]
    for threshold, label, color, bg, desc in levels:
        if score >= threshold:
            return {
                "score": score,
                "base": base_score,
                "verdict": label,
                "color": color,
                "bg": bg,
                "desc": desc,
                "details": details,
                "analysis": analysis,
            }


# ── 전체 수집 ──────────────────────────────────────────────────

def fetch_all():
    print("데이터 수집 중...")
    print("  VIX")
    vix = get_vix()
    print("  공포탐욕지수")
    fg = get_fear_greed()
    print("  S&P500")
    sp500 = get_sp500()
    print("  KOSPI")
    kospi = get_kospi()
    print("  환율")
    fx = get_exchange_rate()
    print("  KODEX S&P500")
    kodex = get_kodex()
    print("  HYG/LQD 스프레드")
    hyg_lqd = get_hyg_lqd()
    print("  신호 계산")
    signal = calc_signal(vix, fg, sp500, fx, hyg_lqd)

    return {
        "ts": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "vix": vix, "fg": fg, "sp500": sp500, "kospi": kospi,
        "fx": fx, "kodex": kodex, "hyg_lqd": hyg_lqd, "signal": signal,
    }
