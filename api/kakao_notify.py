"""
카카오톡 알림 모듈
"""
import requests
import json
from datetime import datetime
from typing import Optional
import sys
sys.path.append('..')
from config.settings import KAKAO_REST_API_KEY, KAKAO_ACCESS_TOKEN, KAKAO_REFRESH_TOKEN


class KakaoNotifier:
    """카카오톡 알림 발송"""

    def __init__(self):
        self.rest_api_key = KAKAO_REST_API_KEY
        self.access_token = KAKAO_ACCESS_TOKEN
        self.refresh_token = KAKAO_REFRESH_TOKEN
        self._token_refreshed = False

    def _refresh_access_token(self) -> bool:
        """refresh_token으로 access_token 자동 갱신"""
        if not self.refresh_token:
            return False

        try:
            url = "https://kauth.kakao.com/oauth/token"
            data = {
                "grant_type": "refresh_token",
                "client_id": self.rest_api_key,
                "refresh_token": self.refresh_token,
            }
            response = requests.post(url, data=data)
            result = response.json()

            if "access_token" in result:
                self.access_token = result["access_token"]
                print("[INFO] 카카오 access_token 자동 갱신 성공")

                # refresh_token도 갱신된 경우 (만료 1개월 이내일 때)
                if "refresh_token" in result:
                    self.refresh_token = result["refresh_token"]
                    print("[INFO] 카카오 refresh_token도 갱신됨")

                self._token_refreshed = True
                return True
            else:
                print(f"[ERROR] 카카오 토큰 갱신 실패: {result}")
                return False
        except Exception as e:
            print(f"[ERROR] 카카오 토큰 갱신 오류: {e}")
            return False

    def send_message(self, message: str) -> bool:
        """
        카카오톡 메시지 발송 (나에게 보내기)
        """
        if not self.access_token and not self.refresh_token:
            print("[WARN] 카카오톡 토큰이 설정되지 않았습니다.")
            print(f"[LOG] {message}")
            return False

        # refresh_token이 있으면 매 실행시 갱신
        if self.refresh_token and not self._token_refreshed:
            self._refresh_access_token()

        url = "https://kapi.kakao.com/v2/api/talk/memo/default/send"
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/x-www-form-urlencoded",
        }

        template = {
            "object_type": "text",
            "text": message,
            "link": {
                "web_url": "https://www.koreainvestment.com",
            }
        }

        data = {
            "template_object": json.dumps(template)
        }

        try:
            response = requests.post(url, headers=headers, data=data)

            # 401 = 토큰 만료 → 갱신 후 재시도
            if response.status_code == 401 and self.refresh_token:
                if self._refresh_access_token():
                    headers["Authorization"] = f"Bearer {self.access_token}"
                    response = requests.post(url, headers=headers, data=data)

            response.raise_for_status()
            return True
        except Exception as e:
            print(f"[ERROR] 카카오톡 알림 발송 실패: {e}")
            print(f"[LOG] {message}")
            return False
    
    def notify_buy(self, strategy: str, stock_name: str, stock_code: str, 
                   price: int, quantity: int, reason: str = "") -> bool:
        """
        매수 알림
        """
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        message = f"""🟢 [매수 완료]
━━━━━━━━━━━━
📊 전략: {strategy}
📈 종목: {stock_name} ({stock_code})
💰 가격: {price:,}원
📦 수량: {quantity}주
💵 금액: {price * quantity:,}원
━━━━━━━━━━━━
📝 사유: {reason}
🕐 시간: {timestamp}"""
        
        return self.send_message(message)
    
    def notify_sell(self, strategy: str, stock_name: str, stock_code: str,
                    price: int, quantity: int, profit_rate: float, reason: str = "") -> bool:
        """
        매도 알림
        """
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        emoji = "🔴" if profit_rate < 0 else "🟢"
        status = "손절" if profit_rate < 0 else "익절"
        
        message = f"""{emoji} [{status} 완료]
━━━━━━━━━━━━
📊 전략: {strategy}
📉 종목: {stock_name} ({stock_code})
💰 가격: {price:,}원
📦 수량: {quantity}주
💵 금액: {price * quantity:,}원
📊 수익률: {profit_rate:+.2f}%
━━━━━━━━━━━━
📝 사유: {reason}
🕐 시간: {timestamp}"""
        
        return self.send_message(message)
    
    def notify_signal(self, strategy: str, stock_name: str, stock_code: str,
                      signal_type: str, reason: str = "") -> bool:
        """
        시그널 알림 (관찰용)
        """
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        emoji = "🔔"
        
        message = f"""{emoji} [시그널 감지]
━━━━━━━━━━━━
📊 전략: {strategy}
📈 종목: {stock_name} ({stock_code})
⚡ 신호: {signal_type}
📝 사유: {reason}
🕐 시간: {timestamp}"""
        
        return self.send_message(message)
    
    def notify_error(self, error_msg: str) -> bool:
        """
        에러 알림
        """
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        message = f"""❌ [오류 발생]
━━━━━━━━━━━━
⚠️ {error_msg}
🕐 시간: {timestamp}"""
        
        return self.send_message(message)
    
    def notify_daily_summary(self, total_profit: float, trades_count: int,
                             win_count: int, positions: list) -> bool:
        """
        일일 리포트 알림
        """
        timestamp = datetime.now().strftime("%Y-%m-%d")
        win_rate = (win_count / trades_count * 100) if trades_count > 0 else 0
        
        positions_str = "\n".join([f"  • {p['name']}: {p['profit_rate']:+.2f}%" for p in positions]) if positions else "  없음"
        
        message = f"""📊 [일일 리포트] {timestamp}
━━━━━━━━━━━━
💰 오늘 수익: {total_profit:+,.0f}원
📈 거래 횟수: {trades_count}회
✅ 승률: {win_rate:.1f}%
━━━━━━━━━━━━
📦 보유 포지션:
{positions_str}"""
        
        return self.send_message(message)


# 싱글톤 인스턴스
kakao_notifier = KakaoNotifier()
