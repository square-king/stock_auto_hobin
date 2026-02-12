"""
Hobeen Macro Lab 자동매매 시스템 설정
"""
import os
from dotenv import load_dotenv

load_dotenv()

# =============================================================================
# 한국투자증권 API 설정
# =============================================================================
KIS_APP_KEY = os.getenv("KIS_APP_KEY", "YOUR_APP_KEY")
KIS_APP_SECRET = os.getenv("KIS_APP_SECRET", "YOUR_APP_SECRET")
KIS_ACCOUNT_NO = os.getenv("KIS_ACCOUNT_NO", "YOUR_ACCOUNT_NO")  # 계좌번호 (8자리-2자리)

# 실전투자 vs 모의투자
KIS_IS_PAPER = os.getenv("KIS_IS_PAPER", "True").lower() == "true"  # True: 모의투자, False: 실전

# API 베이스 URL
KIS_BASE_URL = "https://openapivts.koreainvestment.com:29443" if KIS_IS_PAPER else "https://openapi.koreainvestment.com:9443"

# =============================================================================
# 카카오톡 알림 설정
# =============================================================================
KAKAO_REST_API_KEY = os.getenv("KAKAO_REST_API_KEY", "YOUR_KAKAO_KEY")
KAKAO_ACCESS_TOKEN = os.getenv("KAKAO_ACCESS_TOKEN", "")  # 토큰 발급 후 설정
KAKAO_REFRESH_TOKEN = os.getenv("KAKAO_REFRESH_TOKEN", "")  # 자동 갱신용

# =============================================================================
# 투자 설정
# =============================================================================
TOTAL_CAPITAL = 2_000_000  # 총 투자금 200만원 (국내 주식 전용)
NUM_STRATEGIES = 5
CAPITAL_PER_STRATEGY = TOTAL_CAPITAL // NUM_STRATEGIES  # 40만원

# 리스크 관리
MAX_LOSS_PER_TRADE = 0.01  # 1회 최대 손실 = 자금의 1%
MAX_POSITIONS_PER_STRATEGY = 1  # 전략당 최대 종목 수

# =============================================================================
# 매매 시간 설정
# =============================================================================
MARKET_OPEN_KR = "09:00"
MARKET_CLOSE_KR = "15:30"
MARKET_OPEN_US = "22:30"  # 한국시간 기준 (서머타임 시 23:30)
MARKET_CLOSE_US = "05:00"

# =============================================================================
# 전략별 설정
# =============================================================================
STRATEGIES_CONFIG = {
    "pullback_20ma": {
        "name": "20일선 눌림목",
        "enabled": True,
        "market": "KR",
        "capital": CAPITAL_PER_STRATEGY,
    },
    "envelope_2020": {
        "name": "엔벨로프 20-20",
        "enabled": True,
        "market": "KR",
        "capital": CAPITAL_PER_STRATEGY,
    },
    "stoch_pullback": {
        "name": "스토캐스틱 눌림목",
        "enabled": True,
        "market": "KR",
        "capital": CAPITAL_PER_STRATEGY,
    },
    "bollinger_squeeze": {
        "name": "볼린저 Squeeze",
        "enabled": True,
        "market": "KR",
        "capital": CAPITAL_PER_STRATEGY,
    },
    "supply_demand": {
        "name": "수급 쌍끌이",
        "enabled": True,
        "market": "KR",
        "capital": CAPITAL_PER_STRATEGY,
    },
}

# =============================================================================
# 로깅 설정
# =============================================================================
LOG_DIR = "logs"
LOG_LEVEL = "INFO"
