"""
GitHub Actions용 태스크 러너

사용법:
    python run_task.py morning_buy    # 09:01 매수 실행
    python run_task.py exit_check     # 장중 청산 체크
    python run_task.py scan           # 15:35 스크리닝
    python run_task.py report         # 15:40 일일 리포트
"""
import sys
import os

# 프로젝트 루트를 기준으로 실행
os.chdir(os.path.dirname(os.path.abspath(__file__)))

from main import TradingBot


def run():
    if len(sys.argv) < 2:
        print("사용법: python run_task.py [morning_buy|exit_check|scan|report]")
        sys.exit(1)

    task = sys.argv[1]
    bot = TradingBot()

    if task == "morning_buy":
        bot.execute_morning_buy()
    elif task == "exit_check":
        if bot.is_market_open():
            bot.check_exit_signals()
        else:
            print("[INFO] 장 운영시간이 아닙니다. 스킵.")
    elif task == "scan":
        bot.scan_after_close()
    elif task == "report":
        bot.daily_report()
    else:
        print(f"[ERROR] 알 수 없는 태스크: {task}")
        sys.exit(1)

    print(f"[DONE] {task} 완료")


if __name__ == "__main__":
    run()
