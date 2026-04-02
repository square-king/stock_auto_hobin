"""
Hobeen Macro Lab 자동매매 시스템 메인

블로그 저자 방식 그대로:
- 전체 종목 스크리너로 후보 추출
- 장 마감 후(15:35) 시그널 스캔 → 익일 장 시작(09:01) 매수 실행
- 장중에는 청산(익절/손절) 시그널만 체크

5개 전략 동시 운용:
1. 20일선 눌림목 - 급등주 스크리닝
2. 엔벨로프 20-20 - 코스닥 고변동성
3. 스토캐스틱 눌림목 - 상승추세 조정중
4. 볼린저 Squeeze - 밴드폭 수축 종목
5. 수급 쌍끌이 - 거래대금 상위
"""
import schedule
import time
import json
import os
from datetime import datetime
from typing import List, Dict, Any

from config.settings import (
    CAPITAL_PER_STRATEGY, STRATEGIES_CONFIG,
    MARKET_OPEN_KR, MARKET_CLOSE_KR
)
from strategies import (
    Pullback20MAStrategy, Envelope2020Strategy,
)
from strategies.base_strategy import Signal, SignalType
from trading.order_manager import OrderManager, PortfolioManager
from data.market_data import market_data
from data.screener import screener
from api.kakao_notify import kakao_notifier


class TradingBot:
    """블로그 저자 방식 자동매매 봇"""
    
    def __init__(self):
        # 전략 초기화
        self.strategies = {
            "눌림목": Pullback20MAStrategy(CAPITAL_PER_STRATEGY),
            "엔벨로프": Envelope2020Strategy(CAPITAL_PER_STRATEGY),
        }
        
        # 매니저 초기화
        self.order_manager = OrderManager()
        self.portfolio_manager = PortfolioManager(list(self.strategies.values()))
        
        # 익일 매수 대기 시그널 저장 경로
        self.pending_signals_path = "logs/pending_signals.json"
    
    def is_market_open(self) -> bool:
        """장 운영 시간 확인"""
        now = datetime.now()
        current_time = now.strftime("%H:%M")
        
        if now.weekday() >= 5:
            return False
        
        return MARKET_OPEN_KR <= current_time <= MARKET_CLOSE_KR
    
    def save_pending_signals(self, signals: List[Dict[str, Any]]):
        """익일 매수 시그널 저장"""
        os.makedirs("logs", exist_ok=True)
        with open(self.pending_signals_path, "w", encoding="utf-8") as f:
            json.dump(signals, f, ensure_ascii=False, indent=2)
        print(f"[INFO] 익일 매수 대기 시그널 {len(signals)}개 저장됨")
    
    def load_pending_signals(self) -> List[Dict[str, Any]]:
        """익일 매수 시그널 로드"""
        if not os.path.exists(self.pending_signals_path):
            return []
        try:
            with open(self.pending_signals_path, "r") as f:
                return json.load(f)
        except:
            return []
    
    def clear_pending_signals(self):
        """대기 시그널 초기화"""
        if os.path.exists(self.pending_signals_path):
            os.remove(self.pending_signals_path)
    
    def scan_after_close(self):
        """
        [장 마감 후 실행] 블로그 저자 방식 스캔
        1. 각 전략별 스크리너로 후보 추출
        2. 후보에 대해 진입 조건 체크
        3. 시그널 저장
        """
        print(f"\n{'='*60}")
        print(f"[SCAN - 장 마감 후] {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*60}")
        
        pending_signals = []
        
        # 1. 눌림목 전략: 급등주 스크리닝
        print("\n[1/2] 눌림목 전략 - 급등주 스크리닝")
        strategy = self.strategies["눌림목"]
        if strategy.can_open_position():
            surge_stocks = screener.get_surge_stocks(min_surge=0.30, days=20)
            strategy.set_watchlist(surge_stocks)
            self._scan_strategy(strategy, pending_signals)

        # 2. 엔벨로프 전략: 코스닥 고변동성
        print("\n[2/2] 엔벨로프 전략 - 코스닥 고변동성")
        strategy = self.strategies["엔벨로프"]
        if strategy.can_open_position():
            volatile_stocks = screener.get_high_volatility_kosdaq(min_volatility=0.03)
            strategy.set_watchlist(volatile_stocks)
            self._scan_strategy(strategy, pending_signals)
        
        # 시그널 저장
        if pending_signals:
            self.save_pending_signals(pending_signals)
            
            msg = f"📊 익일 매수 시그널 발생!\n\n"
            for sig in pending_signals:
                msg += f"• [{sig['strategy']}] {sig['stock_code']}\n  {sig['reason']}\n\n"
            kakao_notifier.send_message(msg)
        else:
            print("\n[INFO] 오늘 시그널 없음")
        
        market_data.clear_cache()
    
    def _scan_strategy(self, strategy, pending_signals: List):
        """개별 전략 스캔"""
        candidates = strategy.scan_candidates()
        print(f"  스크리너 후보: {len(strategy.watchlist)}개 → 전략 후보: {len(candidates)}개")
        
        for stock_code in candidates:
            df = market_data.get_ohlcv(stock_code, count=100)
            if df.empty:
                continue
            
            entry_signal = strategy.check_entry_signal(stock_code, df)
            if entry_signal:
                signal_data = {
                    "strategy": strategy.name,
                    "stock_code": entry_signal.stock_code,
                    "stock_name": entry_signal.stock_name,
                    "reason": entry_signal.reason,
                    "signal_price": entry_signal.price,
                    "quantity": entry_signal.quantity,
                    "stop_loss": entry_signal.stop_loss,
                    "take_profit": entry_signal.take_profit,
                    "scan_date": datetime.now().strftime("%Y-%m-%d"),
                }
                pending_signals.append(signal_data)
                print(f"  ✅ 시그널: {stock_code} - {entry_signal.reason}")
                break  # 전략당 1종목
    
    def execute_morning_buy(self):
        """[장 시작 시 실행] 대기 중인 시그널 매수 실행"""
        print(f"\n{'='*60}")
        print(f"[EXECUTE - 장 시작] {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*60}")
        
        pending = self.load_pending_signals()
        
        if not pending:
            print("[INFO] 대기 중인 매수 시그널 없음")
            return
        
        print(f"[INFO] 대기 시그널 {len(pending)}개 실행 시작")
        
        for sig in pending:
            try:
                current = market_data.get_current_price(sig["stock_code"])
                if not current:
                    continue
                
                current_price = current["price"]
                signal_price = sig.get("signal_price", current_price)
                
                # 5% 이상 갭 스킵
                if abs(current_price - signal_price) / signal_price > 0.05:
                    print(f"[SKIP] {sig['stock_code']} 가격 괴리 5% 초과")
                    continue
                
                signal = Signal(
                    signal_type=SignalType.BUY,
                    stock_code=sig["stock_code"],
                    stock_name=sig["stock_name"],
                    reason=sig["reason"],
                    price=current_price,
                    quantity=sig["quantity"],
                    stop_loss=sig["stop_loss"],
                    take_profit=sig.get("take_profit"),
                )
                
                strategy = self.strategies.get(sig["strategy"].replace("20일선 ", "").replace(" 눌림목", ""))
                if not strategy:
                    for s in self.strategies.values():
                        if s.name == sig["strategy"]:
                            strategy = s
                            break
                
                if strategy and strategy.can_open_position():
                    position = self.order_manager.execute_buy(signal, strategy.name)
                    if position:
                        strategy.add_position(position)
                        self.portfolio_manager._save_positions()
                
            except Exception as e:
                print(f"[ERROR] {sig['stock_code']} 매수 오류: {e}")
        
        self.clear_pending_signals()
        market_data.clear_cache()
    
    def check_exit_signals(self):
        """[장중 실행] 보유 포지션 청산 시그널 체크"""
        if not self.is_market_open():
            return
        
        for strategy in self.strategies.values():
            for position in strategy.positions[:]:
                try:
                    df = market_data.get_ohlcv(position.stock_code, count=100)
                    if df.empty:
                        continue
                    
                    exit_signal = strategy.check_exit_signal(position, df)
                    if exit_signal:
                        success = self.order_manager.execute_sell(exit_signal, position)
                        if success:
                            strategy.remove_position(position.stock_code)
                            self.portfolio_manager._save_positions()
                            
                except Exception as e:
                    print(f"[ERROR] {position.stock_code} 청산 체크 오류: {e}")
    
    def daily_report(self):
        """일일 리포트"""
        positions = self.portfolio_manager.get_all_positions()
        
        msg = f"📈 일일 리포트 ({datetime.now().strftime('%Y-%m-%d')})\n\n"
        msg += f"보유 포지션: {len(positions)}개\n"
        
        for pos in positions:
            current = market_data.get_current_price(pos.stock_code)
            if current:
                profit_rate = (current["price"] - pos.entry_price) / pos.entry_price * 100
                msg += f"• {pos.stock_name}: {profit_rate:+.1f}%\n"
        
        kakao_notifier.send_message(msg)
    
    def run(self):
        """봇 실행"""
        print("="*60)
        print("🤖 Hobeen Macro Lab 자동매매 시스템")
        print("   (블로그 저자 방식 - 전체 종목 스크리닝)")
        print("="*60)
        print(f"전략 수: {len(self.strategies)}")
        print(f"전략당 자금: {CAPITAL_PER_STRATEGY:,}원")
        print("="*60)
        print("\n📅 스케줄:")
        print("  - 09:01: 대기 시그널 매수 실행")
        print("  - 09:05~15:25: 5분마다 청산 시그널 체크")
        print("  - 15:35: 전체 종목 스크리닝 + 익일 시그널 스캔")
        print("  - 15:40: 일일 리포트")
        print("="*60)
        
        kakao_notifier.send_message(
            f"🤖 자동매매 시스템 시작\n"
            f"(블로그 저자 방식 - 전체 종목 스크리닝)\n"
            f"전략: {len(self.strategies)}개\n"
            f"자금: {CAPITAL_PER_STRATEGY * len(self.strategies):,}원"
        )
        
        # 스케줄링
        schedule.every().day.at("09:01").do(self.execute_morning_buy)
        schedule.every(5).minutes.do(self.check_exit_signals)
        schedule.every().day.at("15:35").do(self.scan_after_close)
        schedule.every().day.at("15:40").do(self.daily_report)
        
        print("\n[초기 실행] 청산 시그널 체크...")
        self.check_exit_signals()
        
        while True:
            schedule.run_pending()
            time.sleep(1)


def main():
    bot = TradingBot()
    
    try:
        bot.run()
    except KeyboardInterrupt:
        print("\n[INFO] 시스템 종료")
        kakao_notifier.send_message("🛑 자동매매 시스템 종료")


if __name__ == "__main__":
    main()
