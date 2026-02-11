"""
엔벨로프 20-20 전략 (블로그 원문 100% 반영)

블로그 원문:
- 매수: 엔벨로프 하한선(-20%) 터치 시 1차 진입
- 분할매수: 추가 하락 시 2차 진입 (물타기 아님, 계획된 분할)
- 매도: 중심선(20일선) 터치 시 전량 매도
- 손절: 진입 후 -5% 추가 하락 시
"""
import pandas as pd
from typing import Optional, List
from datetime import datetime
import sys
sys.path.append('..')
from strategies.base_strategy import BaseStrategy, Signal, SignalType, Position
from indicators.technical import envelope, sma
from data.market_data import market_data


class Envelope2020Strategy(BaseStrategy):
    """엔벨로프 20-20 전략 (분할매수 포함)"""
    
    def __init__(self, capital: float):
        super().__init__("엔벨로프 20-20", capital)
        self.ma_period = 20
        self.envelope_percent = 20.0
        self.stop_loss_percent = 0.05  # 5%
        
        self.watchlist = []
        self.entry_stage = {}  # 종목별 진입 단계 추적 (1차/2차)
    
    def set_watchlist(self, stocks: List[str]):
        """관찰 종목 설정"""
        self.watchlist = stocks
    
    def scan_candidates(self) -> List[str]:
        """
        매수 후보 종목 스캔
        하한선 근접(-18% ~ -25%) 종목 찾기
        """
        candidates = []
        
        for stock_code in self.watchlist:
            try:
                df = market_data.get_ohlcv(stock_code, count=30)
                if df.empty:
                    continue
                
                close = df["close"]
                center, upper, lower = envelope(close, self.ma_period, self.envelope_percent)
                
                current_price = close.iloc[-1]
                current_lower = lower.iloc[-1]
                current_center = center.iloc[-1]
                
                if pd.isna(current_lower) or current_lower == 0:
                    continue
                
                # 중심선 대비 이격률
                deviation = (current_price - current_center) / current_center * 100
                
                # -18% ~ -25% 구간 (하한선 근처)
                if -25 <= deviation <= -18:
                    candidates.append(stock_code)
                    
            except Exception as e:
                continue
        
        return candidates
    
    def check_entry_signal(self, stock_code: str, df: pd.DataFrame) -> Optional[Signal]:
        """
        매수 시그널 확인 (분할 매수)
        
        1차 진입: 하한선(-20%) 터치
        2차 진입: 1차 진입 후 추가 -3% 하락 시
        """
        if df.empty or len(df) < self.ma_period + 5:
            return None
        
        close = df["close"]
        center, upper, lower = envelope(close, self.ma_period, self.envelope_percent)
        
        current_price = close.iloc[-1]
        current_lower = lower.iloc[-1]
        current_center = center.iloc[-1]
        
        if pd.isna(current_lower) or pd.isna(current_center):
            return None
        
        stage = self.entry_stage.get(stock_code, 0)
        
        # 1차 진입: 하한선 터치
        if stage == 0 and current_price <= current_lower:
            self.entry_stage[stock_code] = 1
            
            stop_loss = int(current_price * (1 - self.stop_loss_percent))
            take_profit = int(current_center)
            
            # 1차는 자금의 50%만 사용
            half_capital = self.capital / 2
            quantity = int(half_capital / current_price)
            
            if quantity == 0:
                return None
            
            return Signal(
                signal_type=SignalType.BUY,
                stock_code=stock_code,
                stock_name=stock_code,
                reason=f"1차 진입: 하한선(-20%) 터치 {current_price:,}원",
                price=int(current_price),
                quantity=quantity,
                stop_loss=stop_loss,
                take_profit=take_profit,
            )
        
        # 2차 진입: 1차 진입 후 추가 -3% 하락
        elif stage == 1:
            # 이미 포지션이 있는지 확인
            for pos in self.positions:
                if pos.stock_code == stock_code:
                    # 1차 진입가 대비 -3% 추가 하락
                    if current_price <= pos.entry_price * 0.97:
                        self.entry_stage[stock_code] = 2
                        
                        stop_loss = int(current_price * (1 - self.stop_loss_percent))
                        
                        # 2차도 나머지 50%
                        half_capital = self.capital / 2
                        quantity = int(half_capital / current_price)
                        
                        if quantity == 0:
                            return None
                        
                        return Signal(
                            signal_type=SignalType.BUY,
                            stock_code=stock_code,
                            stock_name=stock_code,
                            reason=f"2차 분할 진입: 추가 하락 {current_price:,}원",
                            price=int(current_price),
                            quantity=quantity,
                            stop_loss=stop_loss,
                            take_profit=int(current_center),
                        )
                    break
        
        return None
    
    def check_exit_signal(self, position: Position, df: pd.DataFrame) -> Optional[Signal]:
        """
        매도 시그널 확인
        
        조건:
        1. 익절: 중심선(20일선) 터치
        2. 손절: 진입가 대비 -5%
        """
        if df.empty or len(df) < self.ma_period + 5:
            return None
        
        close = df["close"]
        current_price = close.iloc[-1]
        
        # 손절 확인 (-5%)
        if current_price <= position.stop_loss:
            # 진입 단계 초기화
            if position.stock_code in self.entry_stage:
                del self.entry_stage[position.stock_code]
            
            return Signal(
                signal_type=SignalType.SELL,
                stock_code=position.stock_code,
                stock_name=position.stock_name,
                reason=f"손절: {current_price:,}원 <= {position.stop_loss:,}원 (-5%)",
                price=int(current_price),
                quantity=position.quantity,
            )
        
        # 익절 확인 (20일선 터치)
        center = sma(close, self.ma_period).iloc[-1]
        
        if pd.notna(center) and current_price >= center:
            profit_rate = (current_price - position.entry_price) / position.entry_price * 100
            
            # 진입 단계 초기화
            if position.stock_code in self.entry_stage:
                del self.entry_stage[position.stock_code]
            
            return Signal(
                signal_type=SignalType.SELL,
                stock_code=position.stock_code,
                stock_name=position.stock_name,
                reason=f"익절: 20일선 도달 {current_price:,}원 (수익률: {profit_rate:+.1f}%)",
                price=int(current_price),
                quantity=position.quantity,
            )
        
        return None
