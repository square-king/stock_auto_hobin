"""
스캔 테스트 - 익일 매수 시그널 스캔 1회 실행
"""
import sys
sys.path.insert(0, '.')

from datetime import datetime
from data.market_data import market_data
from strategies import (
    Pullback20MAStrategy, Envelope2020Strategy, StochPullbackStrategy,
    BollingerSqueezeStrategy, SupplyDemandStrategy
)
from config.settings import CAPITAL_PER_STRATEGY

print("="*60)
print(f"🔍 익일 매수 시그널 스캔 테스트")
print(f"   {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("="*60)

# 전략 초기화
strategies = [
    Pullback20MAStrategy(CAPITAL_PER_STRATEGY),
    Envelope2020Strategy(CAPITAL_PER_STRATEGY),
    StochPullbackStrategy(CAPITAL_PER_STRATEGY),
    BollingerSqueezeStrategy(CAPITAL_PER_STRATEGY),
    SupplyDemandStrategy(CAPITAL_PER_STRATEGY),
]

# 관찰 종목
watchlist = [
    "005930",  # 삼성전자
    "000660",  # SK하이닉스
    "035720",  # 카카오
    "035420",  # NAVER
    "068270",  # 셀트리온
    "051910",  # LG화학
    "006400",  # 삼성SDI
    "028260",  # 삼성물산
    "207940",  # 삼성바이오로직스
    "373220",  # LG에너지솔루션
]

for strategy in strategies:
    strategy.set_watchlist(watchlist)

# 스캔 실행
signals_found = []

for strategy in strategies:
    print(f"\n[{strategy.name}]")
    
    candidates = strategy.scan_candidates()
    print(f"  후보 종목: {len(candidates)}개")
    
    for stock_code in candidates:
        df = market_data.get_ohlcv(stock_code, count=100)
        if df.empty:
            print(f"    - {stock_code}: 데이터 없음")
            continue
        
        entry_signal = strategy.check_entry_signal(stock_code, df)
        if entry_signal:
            signals_found.append({
                "strategy": strategy.name,
                "stock_code": stock_code,
                "reason": entry_signal.reason,
                "price": entry_signal.price,
                "quantity": entry_signal.quantity,
            })
            print(f"  ✅ 시그널: {stock_code} @ {entry_signal.price:,}원")
            print(f"     사유: {entry_signal.reason}")
            print(f"     수량: {entry_signal.quantity}주")
        else:
            print(f"    - {stock_code}: 후보지만 진입조건 미충족")

print("\n" + "="*60)
print(f"📊 결과 요약")
print("="*60)

if signals_found:
    print(f"\n🎯 익일 매수 시그널: {len(signals_found)}개\n")
    for sig in signals_found:
        print(f"  [{sig['strategy']}]")
        print(f"    종목: {sig['stock_code']}")
        print(f"    가격: {sig['price']:,}원")
        print(f"    수량: {sig['quantity']}주")
        print(f"    사유: {sig['reason']}")
        print()
else:
    print("\n❌ 오늘은 매수 시그널이 없습니다.")
    print("   (장 마감 후 종가 기준으로 다시 스캔됩니다)")

print("="*60)
