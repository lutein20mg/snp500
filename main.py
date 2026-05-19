"""
시장 모니터링 리포트 — 로컬 서버 모드 (기본) / 단발 생성 모드.

  python main.py              로컬 서버 시작 + 브라우저 열기
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


def generate():
    print("  데이터 수집 중...")
    data = fetch_all()
    print("  HTML 생성 중...")
    path, latest = save(data, OUT)
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
