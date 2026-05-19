"""
자동 스케줄러.

  python scheduler.py                    매일 07:00 실행 (Python 상주)
  python scheduler.py --time 08:30       시간 지정
  python scheduler.py --setup-task       Windows 작업 스케줄러 등록
  python scheduler.py --setup-task --ai  AI 해석 포함
"""

import sys, os, subprocess, schedule, time
from datetime import datetime

DIR    = os.path.dirname(os.path.abspath(__file__))
MAIN   = os.path.join(DIR, "main.py")
PYTHON = sys.executable


def run():
    print(f"\n[{datetime.now():%Y-%m-%d %H:%M}] 리포트 생성...")
    args = [PYTHON, MAIN, "--no-browser"]
    if "--ai" in sys.argv:
        args.append("--ai")
    r = subprocess.run(args, cwd=DIR)
    print("[완료]" if r.returncode == 0 else "[오류]")


def setup_task():
    t = "07:00"
    for i, a in enumerate(sys.argv):
        if a == "--time" and i + 1 < len(sys.argv):
            t = sys.argv[i + 1]
    ai = " --ai" if "--ai" in sys.argv else ""
    cmd = f'schtasks /create /tn "StockMonitor" /tr "\\"{PYTHON}\\" \\"{MAIN}\\" --no-browser{ai}" /sc DAILY /st {t} /f /rl HIGHEST'
    print(f"작업 스케줄러 등록: 매일 {t}")
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if r.returncode == 0:
        print(f"등록 완료. 확인: 작업 스케줄러 → StockMonitor")
    else:
        print(f"실패: {r.stderr}\n수동 명령:\n{cmd}")


def main():
    if "--setup-task" in sys.argv:
        setup_task()
        return

    t = "07:00"
    for i, a in enumerate(sys.argv):
        if a == "--time" and i + 1 < len(sys.argv):
            t = sys.argv[i + 1]

    print(f"스케줄러: 매일 {t} | 종료 Ctrl+C")
    schedule.every().day.at(t).do(run)

    while True:
        try:
            schedule.run_pending()
            time.sleep(30)
        except KeyboardInterrupt:
            print("\n종료.")
            break


if __name__ == "__main__":
    main()
