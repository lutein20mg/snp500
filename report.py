"""HTML 리포트 조립."""

import os
import json
from datetime import datetime

from config import CRISES
from charts import scatter_crisis, bar_crises, sp500_history, vix_history


# ── 작은 컴포넌트 ──────────────────────────────────────────────

def _badge(signal):
    m = {
        "strong_buy": ("#e74c3c", "강한 매수 신호"),
        "buy":        ("#e67e22", "매수 신호"),
        "neutral":    ("#f39c12", "중립"),
        "no_signal":  ("#27ae60", "신호 없음"),
    }
    c, t = m.get(signal, ("#95a5a6", ""))
    return f'<span style="background:{c};color:#fff;padding:2px 8px;border-radius:12px;font-size:12px">{t}</span>'


def _card(title, value, sub, signal, detail=""):
    bgs = {"strong_buy":"#fdf2f2","buy":"#fff8f0","neutral":"#fffbf0","no_signal":"#f0fdf4"}
    bds = {"strong_buy":"#e74c3c","buy":"#e67e22","neutral":"#f39c12","no_signal":"#27ae60"}
    return f"""<div style="background:{bgs.get(signal,'#f8f8f8')};border:2px solid {bds.get(signal,'#ddd')};
      border-radius:12px;padding:18px 20px;min-width:170px;flex:1">
      <div style="font-size:13px;color:#666">{title}</div>
      <div style="font-size:24px;font-weight:700;color:#2c3e50;margin-top:4px">{value}</div>
      <div style="font-size:13px;color:#888;margin-top:4px">{sub}</div>
      {'<div style="font-size:12px;color:#aaa;margin-top:6px">'+detail+'</div>' if detail else ''}
      <div style="margin-top:8px">{_badge(signal)}</div></div>"""


def _tip(text):
    return f'<div style="background:#f0f7ff;border-left:4px solid #3d5a80;border-radius:0 8px 8px 0;padding:10px 14px;margin-bottom:14px;font-size:13px;color:#3d5a80;line-height:1.6">{text}</div>'


def _pbar(score, mx=100, label=None):
    pct = min(score / mx * 100, 100)
    c = "#c0392b" if score >= 70 else "#e74c3c" if score >= 50 else "#e67e22" if score >= 30 else "#f39c12" if score >= 15 else "#27ae60"
    lb = label or f"{score}점 (기본 100점 + 보정)"
    return f'''<div style="background:#eee;border-radius:8px;height:10px;margin-top:8px">
      <div style="background:{c};border-radius:8px;height:10px;width:{pct}%"></div></div>
      <div style="font-size:12px;color:#888;margin-top:4px">{lb}</div>'''


# ── 회복 계산기 JS ─────────────────────────────────────────────

def _calc_js(sp500_dd, kodex_price, kodex_ath, fx_rate, vix_now, fg_score):
    recs = []
    for c in CRISES:
        if not c["sp500_dd"] or not c["rec"]:
            continue
        vp = c["vix_peak"] or 25
        fg_approx = 10 if vp >= 40 else 22 if vp >= 30 else 35 if vp >= 20 else 55
        recs.append({
            "name": c["short"], "drawdown": abs(c["sp500_dd"]),
            "vix_peak": vp, "fg_approx": fg_approx,
            "rec": c["rec"], "dur": c["dur"],
        })

    dd  = abs(sp500_dd)  if sp500_dd  else 0
    kp  = kodex_price    if kodex_price else 0
    kath = kodex_ath     if kodex_ath  else 0
    fxr = fx_rate        if fx_rate    else 1400
    vn  = vix_now        if vix_now    else 20
    fgs = fg_score       if fg_score   else 50

    return f"""
<div style="background:#f8faff;border:2px solid #3d5a80;border-radius:12px;padding:24px">
  <div style="display:flex;gap:12px;flex-wrap:wrap;margin-bottom:20px">
    <div style="flex:1;min-width:120px;background:#fff;border-radius:8px;padding:12px 16px;border:1px solid #eee">
      <div style="font-size:11px;color:#888">KODEX S&P500 현재가</div>
      <div style="font-size:20px;font-weight:700;color:#2c3e50">{kp:,.0f}원</div></div>
    <div style="flex:1;min-width:120px;background:#fff;border-radius:8px;padding:12px 16px;border:1px solid #eee">
      <div style="font-size:11px;color:#888">KODEX S&P500 고점</div>
      <div style="font-size:20px;font-weight:700;color:#3d5a80">{kath:,.0f}원</div></div>
    <div style="flex:1;min-width:120px;background:#fff;border-radius:8px;padding:12px 16px;border:1px solid #eee">
      <div style="font-size:11px;color:#888">S&P500 고점 대비</div>
      <div style="font-size:20px;font-weight:700;color:#e74c3c">-{dd:.1f}%</div></div>
    <div style="flex:1;min-width:120px;background:#fff;border-radius:8px;padding:12px 16px;border:1px solid #eee">
      <div style="font-size:11px;color:#888">VIX / 공포탐욕</div>
      <div style="font-size:20px;font-weight:700;color:#c0392b">{vn:.1f} / {fgs:.0f}</div></div>
    <div style="flex:1;min-width:120px;background:#fff;border-radius:8px;padding:12px 16px;border:1px solid #eee">
      <div style="font-size:11px;color:#888">원/달러</div>
      <div style="font-size:20px;font-weight:700;color:#2c3e50">{fxr:,.0f}원</div></div>
  </div>
  <div style="display:flex;gap:16px;flex-wrap:wrap;margin-bottom:20px">
    <div style="flex:1;min-width:180px">
      <label style="font-size:13px;color:#555;display:block;margin-bottom:6px">내 평균 매입가 (원)</label>
      <input id="bp" type="number" placeholder="예: 20000" oninput="calcAndSave()"
        style="width:100%;padding:10px 14px;border:2px solid #ddd;border-radius:8px;font-size:16px;font-family:inherit;outline:none" /></div>
    <div style="flex:1;min-width:180px">
      <label style="font-size:13px;color:#555;display:block;margin-bottom:6px">보유 수량 (선택)</label>
      <input id="qt" type="number" placeholder="예: 100" oninput="calcAndSave()"
        style="width:100%;padding:10px 14px;border:2px solid #ddd;border-radius:8px;font-size:16px;font-family:inherit;outline:none" /></div>
  </div>
  <div id="res" style="display:none">
    <div style="border-top:1px solid #e0e0e0;padding-top:16px">
      <div style="display:flex;gap:12px;flex-wrap:wrap;margin-bottom:16px">
        <div style="flex:1;min-width:130px;background:#fff;border-radius:8px;padding:14px;border:1px solid #eee">
          <div style="font-size:12px;color:#888">현재 수익률</div>
          <div id="pnl" style="font-size:22px;font-weight:700;margin-top:4px"></div>
          <div id="amt" style="font-size:12px;color:#aaa;margin-top:2px"></div></div>
        <div style="flex:1;min-width:200px;background:#fff;border-radius:8px;padding:14px;border:1px solid #eee">
          <div style="font-size:12px;color:#888">전고점 회복 예상</div>
          <div id="rATH" style="font-size:14px;font-weight:700;color:#2c3e50;margin-top:4px;line-height:1.5"></div></div>
        <div style="flex:1;min-width:200px;background:#fff;border-radius:8px;padding:14px;border:1px solid #eee">
          <div style="font-size:12px;color:#888">내 평단가 회복 예상</div>
          <div id="rBP" style="font-size:14px;font-weight:700;color:#2c3e50;margin-top:4px;line-height:1.5"></div></div>
      </div>
      <div style="background:#fff;border-radius:8px;padding:14px;border:1px solid #eee">
        <div style="font-size:13px;font-weight:600;color:#2c3e50;margin-bottom:6px">
          유사 과거 위기 <span style="font-size:11px;font-weight:400;color:#aaa">(VIX 40% + 낙폭 35% + 공포탐욕 25% 가중)</span></div>
        <table style="width:100%;font-size:12px;border-collapse:collapse">
          <thead><tr style="background:#f8f9fa">
            <th style="padding:6px 8px;text-align:left;color:#666">사례</th>
            <th style="padding:6px 8px;text-align:right;color:#666">유사도</th>
            <th style="padding:6px 8px;text-align:right;color:#666">S&P500 최대하락</th>
            <th style="padding:6px 8px;text-align:right;color:#666">VIX 최고</th>
            <th style="padding:6px 8px;text-align:right;color:#666">하락 지속</th>
            <th style="padding:6px 8px;text-align:right;color:#666">전고점 회복</th>
          </tr></thead>
          <tbody id="rows"></tbody>
        </table>
        <div style="font-size:11px;color:#aaa;margin-top:10px;line-height:1.7">
          * 회복 기간은 S&P500 기준. KODEX는 원/달러 환율 영향 추가 반영.<br>
          * 평단가 회복은 S&P500이 현재가 대비 매입가까지의 회복 % 필요량에 근거해 선형 보간 추정.</div>
      </div>
    </div>
  </div>
</div>
<script>
const D={json.dumps(recs,ensure_ascii=False)};
const DD={dd},KP={kp},VX={vn},FG={fgs};
function sim(c){{
  return Math.max(0,1-(.40*Math.abs(c.vix_peak-VX)/90+.35*Math.abs(c.drawdown-DD)/60+.25*Math.abs(c.fg_approx-FG)/100));
}}
function estRec(pctNeeded, scored){{
  // 필요 회복 %에 대해 유사 위기 회복 시간을 선형 보간
  if(pctNeeded<=0) return null;
  const tw=scored.reduce((s,d)=>s+d.s,0);
  if(tw===0) return null;
  // 각 위기에서 pctNeeded/drawdown 비율만큼의 회복 기간 추정
  let est=0;
  scored.forEach(d=>{{
    const ratio=Math.min(pctNeeded/d.drawdown,1);
    est+=d.rec*ratio*d.s;
  }});
  return Math.round(est/tw);
}}
function calc(){{
  const bp=parseFloat(document.getElementById('bp').value);
  const qt=parseFloat(document.getElementById('qt').value)||0;
  if(!bp||bp<=0){{document.getElementById('res').style.display='none';return}}
  document.getElementById('res').style.display='block';
  const p=((KP-bp)/bp)*100;
  document.getElementById('pnl').textContent=(p>=0?'+':'')+p.toFixed(1)+'%';
  document.getElementById('pnl').style.color=p>=0?'#27ae60':'#e74c3c';
  const ae=document.getElementById('amt');
  if(qt>0){{const a=(KP-bp)*qt;ae.textContent=(a>=0?'+':'')+Math.round(a).toLocaleString()+'원';ae.style.color=a>=0?'#27ae60':'#e74c3c'}}else ae.textContent='';
  const sc=D.map(d=>({{...d,s:sim(d)}})).sort((a,b)=>b.s-a.s).slice(0,5);
  const tw=sc.reduce((s,d)=>s+d.s,0);
  // 전고점 회복 (S&P500 전체 drawdown 기준)
  const athRec=tw>0?Math.round(sc.reduce((s,d)=>s+d.rec*d.s,0)/tw):null;
  const mn=Math.min(...sc.map(d=>d.rec)),mx=Math.max(...sc.map(d=>d.rec));
  if(DD<3)document.getElementById('rATH').innerHTML='S&P500이 고점 근처. 전고점 회복 불필요.';
  else if(athRec)document.getElementById('rATH').innerHTML=`가중평균 <b style="color:#2980b9;font-size:17px">${{athRec}}일 (~${{Math.round(athRec/30)}}개월)</b><br><span style="font-size:11px;color:#888">범위 ${{mn}}~${{mx}}일</span>`;
  // 평단가 회복 (내 손실% 기준)
  if(p>=0){{document.getElementById('rBP').innerHTML='<span style="color:#27ae60">현재 수익 상태. 회복 불필요.</span>';}}
  else{{
    const needed=Math.abs(p);
    const bpRec=estRec(needed,sc);
    if(bpRec)document.getElementById('rBP').innerHTML=`필요 회복: +${{needed.toFixed(1)}}%<br>추정 <b style="color:#27ae60;font-size:17px">${{bpRec}}일 (~${{Math.round(bpRec/30)}}개월)</b>`;
    else document.getElementById('rBP').innerHTML='추정 불가';
  }}
  let r='';sc.forEach(d=>{{const sp=Math.round(d.s*100);const bc=sp>=70?'#e74c3c':sp>=50?'#e67e22':'#95a5a6';
    r+=`<tr><td style="padding:6px 8px"><b>${{d.name}}</b></td>
    <td style="padding:6px 8px;text-align:right"><div style="display:flex;align-items:center;justify-content:flex-end;gap:6px">
      <div style="width:50px;height:6px;background:#f0f0f0;border-radius:3px"><div style="width:${{sp}}%;height:6px;background:${{bc}};border-radius:3px"></div></div>
      <span style="font-weight:600;color:${{bc}}">${{sp}}%</span></div></td>
    <td style="padding:6px 8px;text-align:right;color:#e74c3c">-${{d.drawdown}}%</td>
    <td style="padding:6px 8px;text-align:right">${{d.vix_peak}}</td>
    <td style="padding:6px 8px;text-align:right">${{d.dur}}일</td>
    <td style="padding:6px 8px;text-align:right;color:#2980b9;font-weight:600">${{d.rec}}일</td></tr>`}});
  document.getElementById('rows').innerHTML=r;
}}
function calcAndSave(){{
  calc();
  const bp=document.getElementById('bp').value;
  const qt=document.getElementById('qt').value;
  if(bp) localStorage.setItem('sm_bp',bp); else localStorage.removeItem('sm_bp');
  if(qt) localStorage.setItem('sm_qt',qt); else localStorage.removeItem('sm_qt');
}}
// 페이지 로드 시 저장된 값 복원
window.addEventListener('DOMContentLoaded',function(){{
  const bp=localStorage.getItem('sm_bp');
  const qt=localStorage.getItem('sm_qt');
  if(bp){{document.getElementById('bp').value=bp;}}
  if(qt){{document.getElementById('qt').value=qt;}}
  if(bp) calc();
}});
</script>"""


# ── 위기 DB 테이블 ─────────────────────────────────────────────

def _crisis_table():
    rows = ""
    for c in CRISES:
        kd  = f"{c['kospi_dd']}%" if c["kospi_dd"] else "-"
        vp  = str(c["vix_peak"]) if c["vix_peak"] else "-"
        dur = f"{c['dur']}일" if c["dur"] else "진행중"
        rec = f"{c['rec']}일" if c["rec"] else "진행중"
        rows += f"""<tr>
          <td><b>{c['short']}</b></td>
          <td style="color:#e74c3c">{c['sp500_dd']}%</td><td>{kd}</td>
          <td>{dur}</td><td>{rec}</td><td>{vp}</td>
          <td><span style="background:#f0f0f0;padding:2px 6px;border-radius:4px;font-size:11px">{c['trigger']}</span></td></tr>"""
    return rows


# ── HTML 조립 ──────────────────────────────────────────────────

def build_html(data, ai_text=None):
    vix   = data["vix"]
    fg    = data["fg"]
    sp    = data["sp500"]
    ks    = data["kospi"]
    fx    = data["fx"]
    kodex = data["kodex"]
    sig   = data["signal"]
    hyg   = data.get("hyg_lqd")

    c_scatter = scatter_crisis(sp["drawdown"] if sp else None, vix["current"] if vix else None)
    c_bars    = bar_crises(sp["drawdown"] if sp else None)
    c_sp500   = sp500_history(sp["chart"] if sp else None)
    c_vix     = vix_history(vix["chart"] if vix else None)
    c_calc    = _calc_js(
        sp["drawdown"] if sp else None,
        kodex["current"] if kodex else None,
        kodex.get("ath") if kodex else None,
        fx["current"] if fx else None,
        vix["current"] if vix else None,
        fg["score"] if fg else None,
    )

    def _sp_sig(d):
        dd = abs(d["drawdown"])
        return "strong_buy" if dd >= 20 else "buy" if dd >= 10 else "neutral" if dd >= 5 else "no_signal"

    cards = ""
    if vix:
        cards += _card("VIX 공포지수", vix["current"], vix["level"], vix["signal"],
                       f"전일 대비 {'+' if vix['change']>0 else ''}{vix['change']:.1f}")
    if fg:
        cards += _card("공포탐욕지수", fg["score"], fg["level"], fg["signal"],
                       f"전일 대비 {'+' if fg['change']>0 else ''}{fg['change']:.1f}")
    if sp:
        ma_info = f"52주 고점: {sp['high_52w']:,.0f} · 200일선 이격 {sp['ma200_dev']:+.1f}%"
        cards += _card("S&P500", f"{sp['current']:,.0f}",
                       f"52주 고점 대비 {sp['drawdown']:.1f}%", _sp_sig(sp), ma_info)
    if ks:
        cards += _card("KOSPI", f"{ks['current']:,.0f}",
                       f"52주 고점 대비 {ks['drawdown']:.1f}%", _sp_sig(ks),
                       f"52주 고점: {ks['high_52w']:,.0f}")
    if fx:
        cards += _card("원/달러 환율", f"{fx['current']:,.1f}원", fx["level"], fx["signal"],
                       f"52주 범위 상위 {fx['pos_52w']:.0f}%")
    if hyg:
        hyg_sig = "buy" if hyg["stressed"] else "no_signal"
        cards += _card("HYG/LQD 스프레드", hyg["label"].split("(")[0].strip(),
                       f"60일 평균 대비 {hyg['dev_pct']:+.2f}%", hyg_sig,
                       "VIX 선행 신용 스트레스 지표")

    # 신호 세부 (기본 + 보정 분리 표시)
    detail_rows = ""
    for name, (s, mx) in sig["details"].items():
        is_bonus = isinstance(mx, str)  # "+5" 같은 보정 항목
        if is_bonus:
            c = "#9b59b6" if s > 0 else "#ccc"
            detail_rows += f"""<div style="display:flex;align-items:center;gap:10px;margin-bottom:6px">
              <div style="width:110px;font-size:13px;color:#9b59b6">{name}</div>
              <div style="flex:1;font-size:13px;color:{c};font-weight:600">{'+' + str(s) + '점' if s > 0 else '해당없음'}</div></div>"""
        else:
            pct = s / mx * 100 if mx > 0 else 0
            c = "#e74c3c" if pct >= 70 else "#e67e22" if pct >= 40 else "#27ae60"
            detail_rows += f"""<div style="display:flex;align-items:center;gap:10px;margin-bottom:6px">
              <div style="width:110px;font-size:13px;color:#555">{name}</div>
              <div style="flex:1;background:#eee;border-radius:4px;height:8px">
                <div style="width:{pct:.0f}%;background:{c};border-radius:4px;height:8px"></div></div>
              <div style="width:60px;text-align:right;font-size:12px;color:#888">{s}/{mx}</div></div>"""

    ai_block = ""
    if ai_text:
        ai_block = f"""<div class="sec" style="background:#f8f4ff;border:2px solid #9b59b6">
          <h2 style="color:#6c3483">AI 종합 해석</h2>
          <div style="line-height:1.8;white-space:pre-wrap">{ai_text}</div></div>"""

    dd_now = abs(sp["drawdown"]) if sp else 0
    vix_now = vix["current"] if vix else 0
    fg_now = fg["score"] if fg else 50

    return f"""<!DOCTYPE html>
<html lang="ko"><head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>공포에 S&P500 한놈만 패는 리포트 — {data['ts']}</title>
<script src="https://cdn.plot.ly/plotly-2.27.0.min.js"></script>
<link href="https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;500;700&display=swap" rel="stylesheet">
<style>
*{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:'Noto Sans KR',sans-serif;background:#f5f6fa;color:#2c3e50}}
.wrap{{max-width:1280px;margin:0 auto;padding:24px}}
.hdr{{background:linear-gradient(135deg,#2c3e50,#3d5a80);color:#fff;border-radius:16px;padding:28px 32px;margin-bottom:24px}}
.hdr h1{{font-size:24px;font-weight:700}}
.sec{{background:#fff;border-radius:12px;padding:24px;margin-bottom:24px;box-shadow:0 1px 4px rgba(0,0,0,.06)}}
.sec h2{{font-size:17px;font-weight:700;margin-bottom:16px;padding-bottom:10px;border-bottom:2px solid #f0f0f0}}
.cards{{display:flex;gap:14px;flex-wrap:wrap}}
table{{width:100%;border-collapse:collapse;font-size:13px}}
th{{background:#f8f9fa;padding:10px 12px;text-align:left;font-weight:600;color:#555;border-bottom:2px solid #e9ecef}}
td{{padding:10px 12px;border-bottom:1px solid #f0f0f0}}
tr:hover td{{background:#fafbfc}}
input:focus{{border-color:#3d5a80!important}}
</style></head><body>
<div class="wrap">

<div class="hdr">
  <div style="display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:12px">
    <div>
      <h1>공포에 S&P500 한놈만 패는 리포트</h1>
      <div style="font-size:14px;opacity:.75;margin-top:4px">{data['ts']}</div>
      <div style="margin-top:8px;font-size:13px;opacity:.6">전략: 천재지변급 시장 폭락 시 우상향 자산 매수. 그 외 관망.</div>
    </div>
    <button id="rfBtn" onclick="rfData()" style="background:rgba(255,255,255,.15);border:1px solid rgba(255,255,255,.4);color:#fff;padding:8px 20px;border-radius:20px;cursor:pointer;font-size:14px;font-family:inherit;white-space:nowrap;margin-top:4px;transition:opacity .2s">새로고침</button>
  </div>
</div>
<script>
if(location.protocol==='file:')document.getElementById('rfBtn').style.display='none';
function rfData(){{
  const b=document.getElementById('rfBtn');
  b.textContent='수집 중...';b.disabled=true;b.style.opacity='.5';
  fetch('/refresh').then(r=>r.json()).then(d=>{{
    if(d.ok)location.reload();
    else{{b.textContent='오류 발생';b.disabled=false;b.style.opacity='1';}}
  }}).catch(()=>{{b.textContent='서버 없음';b.disabled=false;b.style.opacity='1';}});
}}
</script>

<div class="sec">
  <h2>종합 매수 신호</h2>
  <div style="border:2px solid {sig['color']};background:{sig['bg']};border-radius:12px;padding:20px 24px;margin-bottom:12px">
    <div style="font-size:13px;color:#888">현재 시장 상태</div>
    <div style="font-size:32px;font-weight:700;color:{sig['color']};margin-top:4px">{sig['verdict']}</div>
    <div style="font-size:14px;color:#666;margin-top:8px;line-height:1.5">{sig['desc']}</div>
    <div style="margin-top:14px;padding:14px 16px;background:rgba(255,255,255,0.6);border-radius:8px;font-size:13px;color:#555;line-height:1.8">{sig.get('analysis','')}</div>
  </div>
  {_pbar(sig['score'], 110, f"{sig['score']}점 (기본 {sig['base']}/100 + 보정 {sig['score']-sig['base']})")}
  <div style="margin-top:14px">{detail_rows}</div>
  <div style="font-size:12px;color:#aaa;margin-top:10px;line-height:1.8">
    기본 100점: VIX(30) + 공포탐욕(25) + S&P500 낙폭(30) + 환율(15, 극약세 역감점)<br>
    보정: HYG/LQD 스프레드 스트레스(+5) + 200일선 이격 -5~15%(+3) / -15%초과(+5)<br>
    70+ 강력매수 / 50-69 매수고려 / 30-49 관망 / 15-29 중립 / 0-14 고점근처</div>
</div>

{ai_block}

<div class="sec">
  <h2>실시간 시장 지표</h2>
  <div class="cards">{cards}</div>
</div>

<div class="sec">
  <h2>현재 위치 vs 과거 위기</h2>
  {_tip("가로: S&P500 하락폭 — 오른쪽일수록 큰 위기<br>"
        "세로: VIX — 높을수록 극심한 공포<br>"
        "별(현재)이 오른쪽 위에 있을수록 과거 대형 위기와 유사 → 매수 구간")}
  {c_scatter}
</div>

<div class="sec">
  <h2>과거 위기 이벤트 분석</h2>
  {_tip("왼쪽: 각 위기 최대 하락폭. 빨간 점선 = 현재 하락 수준<br>"
        "오른쪽: 파란 = 고점→저점 기간, 초록 = 저점→전고점 회복 기간. 진행중 이벤트는 현재까지 경과일수 표시")}
  {c_bars}
</div>

<div class="sec">
  <h2>S&P500 장기 추이 (1970~현재)</h2>
  {_tip("실제 등락 선형 차트. 색칠 구간 = 위기 시점<br>"
        "핵심: 모든 위기 이후 반드시 전고점 경신 → 우상향의 근거")}
  {c_sp500}
</div>

<div class="sec">
  <h2>VIX 전체 역사 (1990~현재)</h2>
  {_tip("VIX = 시장 공포 온도계. 매 위기마다 급등 → 해소 패턴 확인 가능<br>"
        "초록(~20) 안정 / 노란(20~30) 주의 / 주황(30~40) 공포 / 빨간(40+) 극단적 공포")}
  {c_vix}
</div>

<div class="sec">
  <h2>KODEX S&P500 회복 계산기</h2>
  {_tip("매입가 입력 → 전고점 회복 / 내 평단가 회복 별도 추정<br>"
        f"현재 VIX({vix_now:.1f}), 공포탐욕({fg_now:.0f}), 낙폭(-{dd_now:.1f}%) 기반 유사도 가중 계산")}
  {c_calc}
</div>

<div class="sec">
  <h2>과거 위기 이벤트 DB</h2>
  <div style="overflow-x:auto"><table>
    <thead><tr>
      <th>이벤트</th><th>S&P500 최대하락</th><th>KOSPI 최대하락</th>
      <th>하락 지속</th><th>고점 회복</th><th>VIX 최고</th><th>유형</th>
    </tr></thead>
    <tbody>{_crisis_table()}</tbody>
  </table></div>
</div>

<div style="text-align:center;color:#bbb;font-size:12px;padding:20px;line-height:1.8">
  투자 참고용. 투자 결정은 본인 판단.<br>데이터: Yahoo Finance, CNN Fear &amp; Greed Index</div>
</div></body></html>"""


def save(data, ai_text=None, out_dir="reports"):
    os.makedirs(out_dir, exist_ok=True)
    ts = datetime.now()
    path = os.path.join(out_dir, f"report_{ts:%Y%m%d_%H%M}.html")
    latest = os.path.join(out_dir, "latest.html")
    html = build_html(data, ai_text)
    for p in (path, latest):
        with open(p, "w", encoding="utf-8") as f:
            f.write(html)
    return path, latest
