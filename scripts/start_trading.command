#!/bin/bash
# 더블클릭으로 실행 가능한 스크립트

echo "=========================================="
echo "🤖 Hobeen Macro Lab 자동매매 봇"
echo "=========================================="
echo ""
echo "봇을 실행합니다..."
echo "이 창을 닫으면 봇이 종료됩니다."
echo "슬립 방지도 함께 실행됩니다."
echo ""

cd /Users/jiho_dt/Desktop/stock_auto_test

# 슬립 방지 (백그라운드)
caffeinate -i -w $$ &

# 봇 실행
python3 main.py
