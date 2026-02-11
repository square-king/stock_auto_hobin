"""
전체 종목 스크리닝 테스트 (간소화 버전)
"""
import sys
sys.path.insert(0, '.')

from datetime import datetime
from data.screener import screener

print("="*60)
print(f"🔍 전체 종목 스크리닝 테스트")
print(f"   {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("="*60)

# 빠른 테스트: 거래대금 상위만
print("\n[테스트] 거래대금 상위 50개 스캔...")
top_stocks = screener.get_top_volume_stocks(top_n=50)
print(f"결과: {top_stocks[:10]}... (총 {len(top_stocks)}개)")

print("\n✅ 스크리너 정상 작동!")
print("\n※ 전체 스캔(급등주, 고변동성 등)은 15:35에 자동 실행됩니다.")
print("="*60)
