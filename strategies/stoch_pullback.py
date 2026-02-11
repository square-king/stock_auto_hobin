"""
스토캐스틱 눌림목 스윙 전략

블로그 원문:
- 매수 조건 (3가지 동시):
  1. 추세: 가격 > SMA20 and SMA20 > SMA60
  2. 과매도: Stoch K(12,5,5) < 20
  3. 트리거: %K > %D 골든크로스
- 매도 조건:
  1. 1차: Stoch K >= 80이면 50% 익절
  2. 2차: 데드크로스 발생 시 전량 청산
"""
import pandas as pd
from typing import Optional, List
from datetime import datetime
import sys
sys.path.append('..')
from strategies.base_strategy import BaseStrategy, Signal, SignalType, Position
from indicators.technical import sma, stochastic_slow, is_golden_cross, is_dead_cross
from data.market_data import market_data


class StochPullbackStrategy(BaseStrategy):
    """스토캐스틱 눌림목 스윙 전략"""
    
    def __init__(self, capital: float):
        super().__init__("스토캐스틱 눌림목", capital)
        self.stoch_k = 12
        self.stoch_d = 5
        self.stoch_smooth = 5
        self.oversold = 20
        self.overbought = 80
        self.stop_loss_percent = 0.05  # 5%
        
        self.watchlist = []
        self.partial_sold = {}  # 1차 익절 여부 추적
    
    def set_watchlist(self, stocks: List[str]):
        """관찰 종목 설정"""
        self.watchlist = stocks
    
    def scan_candidates(self) -> List[str]:
        """
        매수 후보 종목 스캔
        추세 상승 + 스토캐스틱 과매도 종목
        """
        candidates = []
        
        for stock_code in self.watchlist:
            try:
                df = market_data.get_ohlcv(stock_code, count=100)
                if df.empty or len(df) < 60:
                    continue
                
                close = df["close"]
                sma20 = sma(close, 20)
                sma60 = sma(close, 60)
                stoch_k, stoch_d = stochastic_slow(
                    df["high"], df["low"], close,
                    self.stoch_k, self.stoch_d, self.stoch_smooth
                )
                
                current_price = close.iloc[-1]
                current_sma20 = sma20.iloc[-1]
                current_sma60 = sma60.iloc[-1]
                current_k = stoch_k.iloc[-1]
                
                # 추세 조건: 가격 > SMA20 > SMA60
                if current_price > current_sma20 > current_sma60:
                    # 과매도 조건: K < 20
                    if current_k < self.oversold:
                        candidates.append(stock_code)
                    
            except Exception as e:
                print(f"[ERROR] {stock_code} 스캔 실패: {e}")
                continue
        
        return candidates
    
    def check_entry_signal(self, stock_code: str, df: pd.DataFrame) -> Optional[Signal]:
        """
        매수 시그널 확인
        
        조건:
        1. 추세: 가격 > SMA20 > SMA60
        2. 과매도: Stoch K < 20
        3. 골든크로스: K > D (상향 돌파)
        """
        if df.empty or len(df) < 60:
            return None
        
        close = df["close"]
        high = df["high"]
        low = df["low"]
        
        # 이동평균
        sma20 = sma(close, 20)
        sma60 = sma(close, 60)
        
        # 스토캐스틱
        stoch_k, stoch_d = stochastic_slow(
            high, low, close,
            self.stoch_k, self.stoch_d, self.stoch_smooth
        )
        
        current_price = close.iloc[-1]
        current_sma20 = sma20.iloc[-1]
        current_sma60 = sma60.iloc[-1]
        current_k = stoch_k.iloc[-1]
        
        # 조건 1: 추세 확인
        if not (current_price > current_sma20 > current_sma60):
            return None
        
        # 조건 2: 과매도
        if current_k >= self.oversold:
            return None
        
        # 조건 3: 골든크로스
        golden = is_golden_cross(stoch_k, stoch_d)
        if not golden.iloc[-1]:
            return None
        
        # 손절가
        stop_loss = int(current_price * (1 - self.stop_loss_percent))
        
        # 포지션 사이즈
        quantity = self.calculate_position_size(current_price, stop_loss)
        
        if quantity == 0:
            return None
        
        return Signal(
            signal_type=SignalType.BUY,
            stock_code=stock_code,
            stock_name=stock_code,
            reason=f"스토캐스틱 골든크로스 (K={current_k:.1f}, 추세: 가격>SMA20>SMA60)",
            price=int(current_price),
            quantity=quantity,
            stop_loss=stop_loss,
        )
    
    def check_exit_signal(self, position: Position, df: pd.DataFrame) -> Optional[Signal]:
        """
        매도 시그널 확인 (블로그 원문)
        
        조건:
        1. 손절: -5% 또는 전일 저가 이탈
        2. 1차 익절: K >= 80이면 50% 매도
        3. 2차 청산: 데드크로스 발생 시 전량
        """
        if df.empty or len(df) < 60:
            return None
        
        close = df["close"]
        current_price = close.iloc[-1]
        prev_low = df["low"].iloc[-2]  # 전일 저가
        
        # 손절 확인 (-5%)
        if current_price <= position.stop_loss:
            if position.stock_code in self.partial_sold:
                del self.partial_sold[position.stock_code]
            return Signal(
                signal_type=SignalType.SELL,
                stock_code=position.stock_code,
                stock_name=position.stock_name,
                reason=f"손절: {current_price:,}원 <= {position.stop_loss:,.0f}원 (-5%)",
                price=int(current_price),
                quantity=position.quantity,
            )
        
        # 손절: 전일 저가 이탈 (블로그 원문)
        if current_price < prev_low:
            if position.stock_code in self.partial_sold:
                del self.partial_sold[position.stock_code]
            return Signal(
                signal_type=SignalType.SELL,
                stock_code=position.stock_code,
                stock_name=position.stock_name,
                reason=f"손절: 전일 저가 이탈 {current_price:,}원 < {prev_low:,.0f}원",
                price=int(current_price),
                quantity=position.quantity,
            )
        
        # 스토캐스틱 계산
        stoch_k, stoch_d = stochastic_slow(
            df["high"], df["low"], close,
            self.stoch_k, self.stoch_d, self.stoch_smooth
        )
        current_k = stoch_k.iloc[-1]
        
        # 1차 익절: K >= 80 (50% 매도)
        if current_k >= self.overbought:
            if position.stock_code not in self.partial_sold:
                self.partial_sold[position.stock_code] = True
                sell_qty = position.quantity // 2
                
                if sell_qty > 0:
                    profit_rate = (current_price - position.entry_price) / position.entry_price * 100
                    return Signal(
                        signal_type=SignalType.SELL,
                        stock_code=position.stock_code,
                        stock_name=position.stock_name,
                        reason=f"1차 익절 (K={current_k:.1f} >= 80, 수익률: {profit_rate:+.1f}%)",
                        price=int(current_price),
                        quantity=sell_qty,
                    )
        
        # 2차 청산: 데드크로스
        dead = is_dead_cross(stoch_k, stoch_d)
        if dead.iloc[-1]:
            profit_rate = (current_price - position.entry_price) / position.entry_price * 100
            # 청산 완료 후 추적 정보 삭제
            if position.stock_code in self.partial_sold:
                del self.partial_sold[position.stock_code]
            
            return Signal(
                signal_type=SignalType.SELL,
                stock_code=position.stock_code,
                stock_name=position.stock_name,
                reason=f"전량 청산: 데드크로스 발생 (수익률: {profit_rate:+.1f}%)",
                price=int(current_price),
                quantity=position.quantity,
            )
        
        return None
