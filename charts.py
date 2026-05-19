"""Plotly 차트 생성."""

import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime

from config import CRISES

TRIGGER_COLORS = {
    "지정학": "#e67e22", "지정학/에너지": "#e67e22", "지정학/테러": "#e67e22",
    "금융 시스템": "#c0392b", "금융/통화": "#c0392b", "금융/재정": "#c0392b",
    "버블 붕괴": "#8e44ad", "팬데믹": "#2980b9", "거시경제": "#16a085",
    "시스템 충격": "#7f8c8d", "금리/통화정책": "#d35400",
}

BL = dict(plot_bgcolor="white", paper_bgcolor="white",
          font=dict(family="Noto Sans KR, sans-serif", size=11))


def _html(fig):
    return fig.to_html(full_html=False, include_plotlyjs=False)


def _add_crisis_vrects(fig, cutoff="1970-01-01"):
    """차트에 위기 구간 음영 추가."""
    today = datetime.now().strftime("%Y-%m-%d")
    palette = ["#e74c3c","#e67e22","#9b59b6","#3498db","#1abc9c",
               "#c0392b","#d35400","#8e44ad","#2980b9","#16a085",
               "#e74c3c","#e67e22","#9b59b6","#e74c3c"]
    for i, c in enumerate(CRISES):
        if c["start"] < cutoff:
            continue
        ongoing = c.get("ongoing", False)
        end = today if ongoing else c.get("bottom")
        if not end:
            continue
        clr = "#e74c3c" if ongoing else palette[i % len(palette)]
        label = c["short"].split("(")[0] + (" (진행중)" if ongoing else "")
        fig.add_vrect(
            x0=c["start"], x1=end, fillcolor=clr,
            opacity=0.35 if ongoing else 0.18,
            layer="below", line_width=0,
            annotation_text=label, annotation_position="top left",
            annotation_font_size=8, annotation_font_color=clr)


# ── 1. 현재 vs 과거 산점도 ─────────────────────────────────────

def scatter_crisis(sp500_dd, vix_now):
    fig = go.Figure()
    fig.add_hrect(y0=35, y1=100, fillcolor="rgba(231,76,60,0.05)", layer="below", line_width=0)
    fig.add_vrect(x0=15, x1=70, fillcolor="rgba(231,76,60,0.05)", layer="below", line_width=0)

    valid = [c for c in CRISES if c["sp500_dd"] and c["vix_peak"] and not c.get("ongoing")]
    fig.add_trace(go.Scatter(
        x=[abs(c["sp500_dd"]) for c in valid],
        y=[c["vix_peak"] for c in valid],
        mode="markers+text",
        marker=dict(size=13, color="#95a5a6", line=dict(width=1.5, color="#7f8c8d")),
        text=[c["short"].split("(")[0] for c in valid],
        textposition="top center", textfont=dict(size=9, color="#555"),
        name="과거 위기",
        hovertemplate="<b>%{text}</b><br>하락 -%{x}%<br>VIX %{y}<extra></extra>"))

    if sp500_dd is not None and vix_now is not None:
        fig.add_trace(go.Scatter(
            x=[abs(sp500_dd)], y=[vix_now],
            mode="markers+text",
            marker=dict(size=20, color="#e74c3c", symbol="star", line=dict(width=2, color="#c0392b")),
            text=["현재"], textposition="top center", textfont=dict(size=12, color="#e74c3c"),
            name="현재"))

    fig.update_layout(**BL, height=360,
        xaxis=dict(title="S&P500 하락폭 (%) — 오른쪽일수록 큰 위기", gridcolor="#f0f0f0", range=[0, 65]),
        yaxis=dict(title="VIX — 높을수록 공포 극심", gridcolor="#f0f0f0"),
        margin=dict(t=20, b=60, l=70, r=40), legend=dict(orientation="h", y=1.05))
    return _html(fig)


# ── 2. 과거 위기 바차트 ────────────────────────────────────────

def bar_crises(sp500_dd, current_crisis_dur=None):
    today = datetime.now()
    items = []
    for c in CRISES:
        if not c["sp500_dd"]:
            continue
        ongoing = c.get("ongoing", False)
        if ongoing:
            from datetime import datetime as dt
            start = dt.strptime(c["start"], "%Y-%m-%d")
            dur = (today - start).days
            rec = None
        else:
            dur = c["dur"]
            rec = c["rec"]
        items.append({
            "name": c["short"], "dd": abs(c["sp500_dd"]),
            "dur": dur, "rec": rec if rec else 0,
            "trigger": c["trigger"], "ongoing": ongoing,
        })

    names = [it["name"] for it in items]
    dds = [it["dd"] for it in items]
    durs = [it["dur"] for it in items]
    recs = [it["rec"] for it in items]
    colors = [("#e74c3c" if it["ongoing"] else TRIGGER_COLORS.get(it["trigger"], "#95a5a6")) for it in items]

    fig = make_subplots(1, 2,
        subplot_titles=("S&P500 최대 하락폭 (%) — 높을수록 큰 위기",
                        "하락 지속 vs 고점 회복 기간 (일)"),
        horizontal_spacing=0.12)

    fig.add_trace(go.Bar(x=names, y=dds, marker_color=colors,
        text=[f"-{d}%" for d in dds], textposition="outside",
        name="하락폭"), 1, 1)

    if sp500_dd is not None:
        fig.add_hline(y=abs(sp500_dd), line_dash="dash", line_color="#e74c3c",
            annotation_text=f"  현재 -{abs(sp500_dd):.1f}%",
            annotation_font_color="#e74c3c", row=1, col=1)

    fig.add_trace(go.Bar(x=names, y=durs, name="하락 지속 (고점→저점)", marker_color="#3498db"), 1, 2)
    fig.add_trace(go.Bar(x=names, y=recs, name="회복 기간 (저점→전고점)", marker_color="#2ecc71"), 1, 2)

    fig.update_layout(**BL, height=480, barmode="group",
        legend=dict(orientation="h", y=1.02, xanchor="right", x=1),
        margin=dict(t=60, b=120, l=40, r=40))
    fig.update_xaxes(tickangle=-45)
    fig.update_yaxes(gridcolor="#f0f0f0")
    return _html(fig)


# ── 3. S&P500 장기 (1970~, 선형) ──────────────────────────────

def sp500_history(chart_df):
    if chart_df is None or chart_df.empty:
        return "<p>데이터 없음</p>"
    df = chart_df[chart_df.index >= "1970-01-01"]
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=list(df.index), y=df["Close"].tolist(),
        mode="lines", line=dict(color="#2c3e50", width=1.3),
        name="S&P500", hovertemplate="%{x}<br>%{y:,.0f}<extra></extra>"))
    _add_crisis_vrects(fig, "1970-01-01")
    fig.update_layout(**BL, height=430, hovermode="x unified",
        xaxis=dict(type="date", gridcolor="#f5f5f5", title="연도",
                   range=["1970-01-01", list(df.index)[-1]]),
        yaxis=dict(gridcolor="#f5f5f5", title="S&P500", tickformat=",d"),
        margin=dict(t=20, b=40, l=80, r=40))
    return _html(fig)


# ── 4. VIX 전체 역사 (1990~) + 위기 이벤트 ────────────────────

def vix_history(chart_df):
    if chart_df is None or chart_df.empty:
        return "<p>데이터 없음</p>"

    # VIX는 1990년부터 데이터 존재
    df = chart_df[chart_df.index >= "1990-01-01"]
    x = list(df.index)
    y = df["Close"].tolist()
    ymax = max(max(y) * 1.1, 50)

    fig = go.Figure()

    # 구간 배경
    fig.add_hrect(y0=0,  y1=20,   fillcolor="#e8f8e8", opacity=0.3, layer="below", line_width=0)
    fig.add_hrect(y0=20, y1=30,   fillcolor="#fff8e8", opacity=0.3, layer="below", line_width=0)
    fig.add_hrect(y0=30, y1=40,   fillcolor="#fff0e0", opacity=0.3, layer="below", line_width=0)
    fig.add_hrect(y0=40, y1=ymax, fillcolor="#fde8e8", opacity=0.3, layer="below", line_width=0)

    fig.add_trace(go.Scatter(
        x=x, y=y, mode="lines",
        line=dict(color="#c0392b", width=1.2), name="VIX",
        hovertemplate="%{x}<br>VIX %{y:.1f}<extra></extra>"))

    # 위기 이벤트 표시
    _add_crisis_vrects(fig, "1990-01-01")

    for lv, clr, lbl in [(20,"#27ae60","20"),(30,"#e67e22","30"),(40,"#e74c3c","40")]:
        fig.add_hline(y=lv, line_dash="dot", line_color=clr, line_width=1,
            annotation_text=lbl, annotation_font_color=clr, annotation_position="right")

    fig.update_layout(**BL, height=400, showlegend=False,
        xaxis=dict(type="date", gridcolor="#f5f5f5", title="연도", range=[x[0], x[-1]]),
        yaxis=dict(gridcolor="#f5f5f5", title="VIX", range=[0, ymax]),
        margin=dict(t=20, b=40, l=60, r=80), hovermode="x unified")
    return _html(fig)
