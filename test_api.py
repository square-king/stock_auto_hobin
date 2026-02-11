"""
API 연결 테스트 스크립트
"""
import os
import sys
from dotenv import load_dotenv

# 환경변수 로드
load_dotenv()

print("=" * 50)
print("🔍 한국투자증권 API 연결 테스트")
print("=" * 50)

# 설정 확인
app_key = os.getenv("KIS_APP_KEY", "")
app_secret = os.getenv("KIS_APP_SECRET", "")
account_no = os.getenv("KIS_ACCOUNT_NO", "")
is_paper = os.getenv("KIS_IS_PAPER", "True")

print(f"\n📋 설정 확인:")
print(f"  - App Key: {app_key[:10]}... (앞 10자리)")
print(f"  - Account: {account_no}")
print(f"  - 모의투자: {is_paper}")

if not app_key or not app_secret or not account_no:
    print("\n❌ 에러: .env 파일에 필수 값이 없습니다!")
    sys.exit(1)

print("\n✅ 환경변수 로드 성공!")

# API 테스트
try:
    from api.kis_api import kis_api
    
    print("\n🔄 API 토큰 발급 테스트...")
    
    # 삼성전자 현재가 조회 테스트
    print("\n📈 삼성전자(005930) 현재가 조회 테스트...")
    result = kis_api.get_price("005930")
    
    if result.get("rt_cd") == "0":
        output = result.get("output", {})
        price = output.get("stck_prpr", "N/A")
        change = output.get("prdy_ctrt", "N/A")
        print(f"\n✅ API 연결 성공!")
        print(f"  - 삼성전자 현재가: {int(price):,}원")
        print(f"  - 전일대비: {change}%")
    else:
        print(f"\n⚠️ API 응답 에러: {result.get('msg1', 'Unknown error')}")
        print(f"  - 에러코드: {result.get('msg_cd', 'N/A')}")
        
except Exception as e:
    print(f"\n❌ API 테스트 실패: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 50)
