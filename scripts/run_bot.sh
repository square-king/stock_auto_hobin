#!/bin/bash
# 자동매매 봇 실행 스크립트

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR/.."

# 로그 디렉토리 생성
mkdir -p logs

# Python 경로 확인
PYTHON="/usr/bin/python3"

# 로그 파일
LOG_FILE="logs/bot_$(date +%Y%m%d).log"

echo "[$(date)] 자동매매 봇 시작..." >> "$LOG_FILE"

# 봇 실행
$PYTHON main.py >> "$LOG_FILE" 2>&1
