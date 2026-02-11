import sys
import os

# 현재 디렉토리를 경로에 추가하여 모듈 임포트 가능하게 함
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from api.kakao_notify import kakao_notifier

def test_kakao_message():
    print("🔔 카카오톡 테스트 메시지 전송 시도 중...")
    try:
        success = kakao_notifier.send_message("테스트 메시지입니다.\n이 메시지가 보이면 카카오톡 설정이 성공적으로 완료된 것입니다! 🎉")
        if success:
            print("✅ 카카오톡 메시지 전송 성공!")
        else:
            print("❌ 카카오톡 메시지 전송 실패 (로그 확인 필요)")
    except Exception as e:
        print(f"❌ 에러 발생: {e}")

if __name__ == "__main__":
    test_kakao_message()
