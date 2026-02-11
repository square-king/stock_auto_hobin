"""
포트폴리오 및 주문 관리 모듈
"""
from typing import Dict, List, Optional, Any
from datetime import datetime
import json
import os
import sys
sys.path.append('..')
from strategies.base_strategy import Signal, SignalType, Position
from api.kis_api import kis_api
from api.kakao_notify import kakao_notifier


class OrderManager:
    """주문 실행 관리"""
    
    def __init__(self):
        self.api = kis_api
        self.notifier = kakao_notifier
        self.trades_log_path = "logs/trades.json"
        self._ensure_log_dir()
    
    def _ensure_log_dir(self):
        """로그 디렉토리 생성"""
        os.makedirs("logs", exist_ok=True)
        if not os.path.exists(self.trades_log_path):
            with open(self.trades_log_path, "w") as f:
                json.dump([], f)
    
    def execute_buy(self, signal: Signal, strategy_name: str) -> Optional[Position]:
        """
        매수 주문 실행
        
        Args:
            signal: 매수 시그널
            strategy_name: 전략 이름
            
        Returns:
            Position 또는 None
        """
        try:
            # 주문 실행
            result = self.api.buy_stock(
                signal.stock_code,
                signal.quantity,
                0  # 시장가
            )
            
            if result.get("rt_cd") != "0":
                print(f"[ERROR] 매수 주문 실패: {result.get('msg1')}")
                self.notifier.notify_error(f"매수 실패: {signal.stock_code} - {result.get('msg1')}")
                return None
            
            # 포지션 생성
            position = Position(
                stock_code=signal.stock_code,
                stock_name=signal.stock_name,
                quantity=signal.quantity,
                entry_price=signal.price,
                entry_date=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                stop_loss=signal.stop_loss,
                take_profit=signal.take_profit,
                strategy_name=strategy_name,
            )
            
            # 카톡 알림
            self.notifier.notify_buy(
                strategy=strategy_name,
                stock_name=signal.stock_name,
                stock_code=signal.stock_code,
                price=signal.price,
                quantity=signal.quantity,
                reason=signal.reason,
            )
            
            # 로그 저장
            self._log_trade("BUY", signal, strategy_name)
            
            print(f"[BUY] {strategy_name} | {signal.stock_code} | {signal.quantity}주 @ {signal.price:,}원")
            
            return position
            
        except Exception as e:
            print(f"[ERROR] 매수 실행 오류: {e}")
            self.notifier.notify_error(f"매수 오류: {signal.stock_code} - {e}")
            return None
    
    def execute_sell(self, signal: Signal, position: Position) -> bool:
        """
        매도 주문 실행
        
        Args:
            signal: 매도 시그널
            position: 현재 포지션
            
        Returns:
            성공 여부
        """
        try:
            # 주문 실행
            result = self.api.sell_stock(
                signal.stock_code,
                signal.quantity,
                0  # 시장가
            )
            
            if result.get("rt_cd") != "0":
                print(f"[ERROR] 매도 주문 실패: {result.get('msg1')}")
                self.notifier.notify_error(f"매도 실패: {signal.stock_code} - {result.get('msg1')}")
                return False
            
            # 수익률 계산
            profit_rate = (signal.price - position.entry_price) / position.entry_price * 100
            
            # 카톡 알림
            self.notifier.notify_sell(
                strategy=position.strategy_name,
                stock_name=signal.stock_name,
                stock_code=signal.stock_code,
                price=signal.price,
                quantity=signal.quantity,
                profit_rate=profit_rate,
                reason=signal.reason,
            )
            
            # 로그 저장
            self._log_trade("SELL", signal, position.strategy_name, profit_rate)
            
            print(f"[SELL] {position.strategy_name} | {signal.stock_code} | {signal.quantity}주 @ {signal.price:,}원 | {profit_rate:+.1f}%")
            
            return True
            
        except Exception as e:
            print(f"[ERROR] 매도 실행 오류: {e}")
            self.notifier.notify_error(f"매도 오류: {signal.stock_code} - {e}")
            return False
    
    def _log_trade(self, action: str, signal: Signal, strategy: str, profit_rate: float = None):
        """매매 로그 저장"""
        try:
            with open(self.trades_log_path, "r") as f:
                logs = json.load(f)
            
            log_entry = {
                "timestamp": datetime.now().isoformat(),
                "action": action,
                "strategy": strategy,
                "stock_code": signal.stock_code,
                "stock_name": signal.stock_name,
                "price": signal.price,
                "quantity": signal.quantity,
                "reason": signal.reason,
            }
            
            if profit_rate is not None:
                log_entry["profit_rate"] = round(profit_rate, 2)
            
            logs.append(log_entry)
            
            with open(self.trades_log_path, "w", encoding="utf-8") as f:
                json.dump(logs, f, ensure_ascii=False, indent=2)
                
        except Exception as e:
            print(f"[WARN] 로그 저장 실패: {e}")


class PortfolioManager:
    """포트폴리오 관리"""
    
    def __init__(self, strategies: List):
        self.strategies = {s.name: s for s in strategies}
        self.positions_path = "logs/positions.json"
        self._load_positions()
    
    def _load_positions(self):
        """저장된 포지션 로드"""
        if os.path.exists(self.positions_path):
            try:
                with open(self.positions_path, "r") as f:
                    data = json.load(f)
                
                for pos_data in data:
                    strategy_name = pos_data.get("strategy_name")
                    if strategy_name in self.strategies:
                        position = Position(**pos_data)
                        self.strategies[strategy_name].add_position(position)
                        
            except Exception as e:
                print(f"[WARN] 포지션 로드 실패: {e}")
    
    def _save_positions(self):
        """포지션 저장"""
        try:
            all_positions = []
            for strategy in self.strategies.values():
                for pos in strategy.positions:
                    all_positions.append({
                        "stock_code": pos.stock_code,
                        "stock_name": pos.stock_name,
                        "quantity": pos.quantity,
                        "entry_price": pos.entry_price,
                        "entry_date": pos.entry_date,
                        "stop_loss": pos.stop_loss,
                        "take_profit": pos.take_profit,
                        "strategy_name": pos.strategy_name,
                    })
            
            os.makedirs("logs", exist_ok=True)
            with open(self.positions_path, "w", encoding="utf-8") as f:
                json.dump(all_positions, f, ensure_ascii=False, indent=2)
                
        except Exception as e:
            print(f"[WARN] 포지션 저장 실패: {e}")
    
    def get_all_positions(self) -> List[Position]:
        """전체 포지션 조회"""
        positions = []
        for strategy in self.strategies.values():
            positions.extend(strategy.positions)
        return positions
    
    def update_position(self, strategy_name: str, position: Position):
        """포지션 추가/업데이트"""
        if strategy_name in self.strategies:
            self.strategies[strategy_name].add_position(position)
            self._save_positions()
    
    def remove_position(self, strategy_name: str, stock_code: str):
        """포지션 제거"""
        if strategy_name in self.strategies:
            self.strategies[strategy_name].remove_position(stock_code)
            self._save_positions()


# 싱글톤 인스턴스
order_manager = OrderManager()
