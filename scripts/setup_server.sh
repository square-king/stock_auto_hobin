#!/bin/bash
# Oracle Cloud 서버 초기 셋업 스크립트
# 사용법: ssh 접속 후 ~/stock_auto_test/scripts/setup_server.sh 실행

set -e

echo "========================================"
echo " Oracle Cloud 서버 셋업 시작"
echo "========================================"

# OS 감지
if [ -f /etc/oracle-release ] || [ -f /etc/redhat-release ]; then
    PKG_MANAGER="yum"
    echo "[INFO] Oracle Linux / RHEL 감지"
elif [ -f /etc/debian_version ]; then
    PKG_MANAGER="apt"
    echo "[INFO] Ubuntu / Debian 감지"
else
    echo "[ERROR] 지원하지 않는 OS입니다."
    exit 1
fi

# 1. 시스템 업데이트
echo ""
echo "[1/6] 시스템 업데이트..."
if [ "$PKG_MANAGER" = "yum" ]; then
    sudo yum update -y
    sudo yum install python39 python39-pip -y
else
    sudo apt update && sudo apt upgrade -y
    sudo apt install python3 python3-pip python3-venv -y
fi

# 2. 시간대 설정
echo ""
echo "[2/6] 시간대를 Asia/Seoul로 설정..."
sudo timedatectl set-timezone Asia/Seoul
echo "  현재 시간: $(date)"

# 3. 프로젝트 디렉토리 확인
echo ""
echo "[3/6] 프로젝트 디렉토리 확인..."
PROJECT_DIR="$HOME/stock_auto_test"
if [ ! -d "$PROJECT_DIR" ]; then
    echo "[ERROR] $PROJECT_DIR 디렉토리가 없습니다."
    echo "  먼저 scp로 프로젝트를 업로드해주세요:"
    echo "  scp -i <key> -r stock_auto_test <user>@<ip>:~/"
    exit 1
fi
echo "  프로젝트 경로: $PROJECT_DIR"

# 4. 의존성 설치
echo ""
echo "[4/6] Python 의존성 설치..."
cd "$PROJECT_DIR"
pip3 install --user -r requirements.txt

# 필요 디렉토리 생성
mkdir -p logs data

# 5. .env 파일 확인
echo ""
echo "[5/6] .env 파일 확인..."
if [ ! -f "$PROJECT_DIR/.env" ]; then
    echo "[WARN] .env 파일이 없습니다!"
    echo "  .env.example을 복사 후 실제 값을 입력해주세요:"
    echo "  cp .env.example .env && vi .env"
else
    echo "  .env 파일 확인됨"
fi

# 6. systemd 서비스 등록
echo ""
echo "[6/6] systemd 서비스 등록..."
PYTHON_PATH=$(which python3)
CURRENT_USER=$(whoami)

sudo tee /etc/systemd/system/stock-bot.service > /dev/null << EOF
[Unit]
Description=Stock Auto Trading Bot
After=network.target

[Service]
Type=simple
User=$CURRENT_USER
WorkingDirectory=$PROJECT_DIR
ExecStart=$PYTHON_PATH $PROJECT_DIR/main.py
Restart=always
RestartSec=10
StandardOutput=append:$PROJECT_DIR/logs/service.log
StandardError=append:$PROJECT_DIR/logs/service_error.log

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable stock-bot

echo ""
echo "========================================"
echo " 셋업 완료!"
echo "========================================"
echo ""
echo " 다음 단계:"
echo "  1. .env 설정 확인:  vi ~/stock_auto_test/.env"
echo "  2. 테스트 실행:     cd ~/stock_auto_test && python3 main.py"
echo "  3. 서비스 시작:     sudo systemctl start stock-bot"
echo "  4. 상태 확인:       sudo systemctl status stock-bot"
echo "  5. 로그 확인:       tail -f ~/stock_auto_test/logs/service.log"
echo ""
echo " 기타 명령어:"
echo "  - 재시작: sudo systemctl restart stock-bot"
echo "  - 중지:   sudo systemctl stop stock-bot"
echo ""
