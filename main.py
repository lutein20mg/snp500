"""
시장 모니터링 리포트 — 로컬 서버 모드 (기본) / 단발 생성 모드.

  python main.py              로컬 서버 시작 + 브라우저 열기
  python main.py --ai         AI 해석 포함 (ANTHROPIC_API_KEY 필요)
  python main.py --no-browser 브라우저 안 열기
  python main.py --once       서버 없이 HTML 한 번만 생성
"""

import sys, os, io, json, webbrowser
from http.server import HTTPServer, BaseHTTPRequestHandler
from dotenv import load_dotenv

if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

load_dotenv()

from fetcher import fetch_all
from report import save

OUT = os.path.join(os.path.dirname(__file__), "reports")
PORT = 8765
_use_ai = False


def ai_interpret(data):
    try:
        import anthropic
        c = anthropic.Anthropic()
        vix   = data.get("vix")
        fg    = data.get("fg")
        sp    = data.get("sp500")
        ks    = data.get("kospi")
        fx    = data.get("fx")
        sig   = data.get("signal")

        prompt = f"""당신은 장기 투자 전략 분석가입니다.
투자자 전략: 천재지변급 시장 전체 폭락(코로나, 금융위기 등) 시 S&P500, 고배당ETF 등 우상향 자산 매수. 그 외 관망.

현재 데이터:
- VIX: {vix['current'] if vix else 'N/A'} ({vix['level'] if vix else ''})
- 공포탐욕: {fg['score'] if fg else 'N/A'} ({fg['level'] if fg else ''})
- S&P500: {sp['current'] if sp else 'N/A'} (고점 대비 {sp['drawdown'] if sp else 'N/A'}%)
- KOSPI: {ks['current'] if ks else 'N/A'} (고점 대비 {ks['drawdown'] if ks else 'N/A'}%)
- 원/달러: {fx['current'] if fx else 'N/A'}원 (52주 범위 {fx['pos_52w'] if fx else 'N/A'}%)
- 종합: {sig['score']}/100점 → {sig['verdict']}

한국어 300-400자로 분석:
1. 이 전략 기준 현재 어떤 단계인지
2. 주목할 지표와 이유
3. 과거 유사 위기 (있다면)
4. 결론 (매수고려/관망/대기)"""

        msg = c.messages.create(model="claude-sonnet-4-6", max_tokens=600,
                                messages=[{"role": "user", "content": prompt}])
        return msg.content[0].text
    except Exception as e:
        print(f"  AI 해석 실패: {e}")
        return None


def generate():
    print("  데이터 수집 중...")
    data = fetch_all()
    ai = ai_interpret(data) if _use_ai else None
    print("  HTML 생성 중...")
    path, latest = save(data, ai, OUT)
    sig = data["signal"]
    print(f"  완료: {path}")
    print(f"  판정: {sig['verdict']} ({sig['score']}/100)")
    if data["vix"]:
        print(f"  VIX: {data['vix']['current']} ({data['vix']['level']})")
    if data["fg"]:
        print(f"  공포탐욕: {data['fg']['score']} ({data['fg']['level']})")
    if data["sp500"]:
        print(f"  S&P500: {data['sp500']['current']:,.0f} ({data['sp500']['drawdown']:.1f}%)")
    return latest


class Handler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

    def do_GET(self):
        if self.path == "/refresh":
            try:
                generate()
                body = b'{"ok":true}'
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
            except Exception as e:
                body = json.dumps({"ok": False, "error": str(e)}).encode()
                self.send_response(500)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
        elif self.path in ("/", "/index.html", "/latest.html"):
            latest = os.path.join(OUT, "latest.html")
            with open(latest, "rb") as f:
                content = f.read()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(content)))
            self.end_headers()
            self.wfile.write(content)
        else:
            self.send_response(404)
            self.end_headers()


def main():
    global _use_ai
    _use_ai = "--ai" in sys.argv
    no_browser = "--no-browser" in sys.argv
    once = "--once" in sys.argv

    print("=" * 48)
    print("  시장 모니터링 리포트")
    print("=" * 48)

    latest = generate()

    if once:
        if not no_browser:
            webbrowser.open(f"file:///{latest.replace(os.sep, '/')}")
        return

    print()
    print(f"  서버: http://localhost:{PORT}")
    print("  종료: Ctrl+C")

    if not no_browser:
        webbrowser.open(f"http://localhost:{PORT}")

    server = HTTPServer(("0.0.0.0", PORT), Handler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n  종료.")
        server.shutdown()


if __name__ == "__main__":
    main()
