"""
볼린저밴드 Squeeze & Break 전략 (블로그 원문 100% 반영)

블로그 원문:
- Squeeze: 밴드폭 수축 (6개월 최저 또는 <10%)
- Break: 상단밴드 종가 돌파 + 거래량 1.5배 + 양봉
- 불타기: 돌파 후 2일 연속 양봉+거래량 유지 시 50% 추가
- 손절: 20일선 이탈 또는 돌파 캔들 저가 이탈
- 익절: 1차 전고점/+15%에서 50%, 잔여는 전일저가/10일선 이탈 시
"""
import pandas as pd
from typing import Optional, List
from datetime import datetime
import sys
sys.path.append('..')
from strategies.base_strategy import BaseStrategy, Signal, SignalType, Position
from indicators.technical import sma, bollinger_bands
from data.market_data import market_data


class BollingerSqueezeStrategy(BaseStrategy):
    """볼린저밴드 Squeeze & Break 전략 (블로그 원문 100%)"""
    
    def __init__(self, capital: float):
        super().__init__("볼린저 Squeeze", capital)
        self.bb_period = 20
        self.bb_std = 2.0
        self.squeeze_threshold = 10.0  # 밴드폭 10% 이하
        self.volume_multiplier = 1.5  # 거래량 1.5배
        self.stop_loss_percent = 0.05
        
        self.watchlist = []
        self.partial_sold = {}  # 1차 익절 여부
        self.entry_candle_low = {}  # 돌파 캔들 저가 저장
        self.pyramiding_done = {}  # 불타기 완료 여부
    
    def set_watchlist(self, stocks: List[str]):
        self.watchlist = stocks
    
    def _is_squeeze(self, bandwidth: pd.Series) -> bool:
        """스퀴즈 상태 확인"""
        if len(bandwidth) < 120:
            return False
        
        current_bw = bandwidth.iloc[-1]
        min_bw_6m = bandwidth.iloc[-120:].min()
        
        return (current_bw <= min_bw_6m * 1.1) or (current_bw <= self.squeeze_threshold)
    
    def _is_breakout(self, df: pd.DataFrame, upper: pd.Series) -> bool:
        """상단밴드 종가 돌파 확인"""
        if len(df) < 2:
            return False
        
        today_close = df["close"].iloc[-1]
        today_upper = upper.iloc[-1]
        yesterday_close = df["close"].iloc[-2]
        yesterday_upper = upper.iloc[-2]
        
        return (today_close > today_upper) and (yesterday_close <= yesterday_upper)
    
    def _has_volume_surge(self, df: pd.DataFrame) -> bool:
        """거래량 급증 확인"""
        if len(df) < 20:
            return False
        
        volume = df["volume"]
        current_vol = volume.iloc[-1]
        avg_vol = volume.iloc[-20:-1].mean()  # 오늘 제외 평균
        
        return current_vol >= avg_vol * self.volume_multiplier
    
    def _check_pyramiding_signal(self, stock_code: str, df: pd.DataFrame) -> bool:
        """
        불타기 조건 확인 (블로그 원문)
        - 돌파 후 2일 연속 양봉 + 거래량 유지
        """
        if len(df) < 3:
            return False
        
        # 최근 2일 연속 양봉
        day1 = df.iloc[-2]
        day2 = df.iloc[-1]
        
        green1 = day1["close"] > day1["open"]
        green2 = day2["close"] > day2["open"]
        
        if not (green1 and green2):
            return False
        
        # 거래량 유지 (평균 이상)
        volume = df["volume"]
        avg_vol = volume.iloc[-20:-2].mean()
        vol1 = volume.iloc[-2]
        vol2 = volume.iloc[-1]
        
        return vol1 >= avg_vol and vol2 >= avg_vol * 0.8
    
    def scan_candidates(self) -> List[str]:
        """스퀴즈 상태 종목 스캔"""
        candidates = []
        
        for stock_code in self.watchlist:
            try:
                df = market_data.get_ohlcv(stock_code, count=150)
                if df.empty or len(df) < 120:
                    continue
                
                close = df["close"]
                middle, upper, lower, bandwidth = bollinger_bands(close, self.bb_period, self.bb_std)
                
                if self._is_squeeze(bandwidth):
                    candidates.append(stock_code)
                    
            except Exception as e:
                continue
        
        return candidates
    
    def check_entry_signal(self, stock_code: str, df: pd.DataFrame) -> Optional[Signal]:
        """
        매수 시그널 (블로그 원문)
        
        조건:
        1. 스퀴즈 상태
        2. 상단밴드 종가 돌파
        3. 거래량 1.5배 이상
        4. 양봉
        
        불타기:
        - 돌파 후 2일 연속 양봉+거래량 시 50% 추가
        """
        if df.empty or len(df) < 120:
            return None
        
        close = df["close"]
        middle, upper, lower, bandwidth = bollinger_bands(close, self.bb_period, self.bb_std)
        
        # 이미 포지션이 있으면 불타기 확인
        for pos in self.positions:
            if pos.stock_code == stock_code:
                if stock_code not in self.pyramiding_done:
                    if self._check_pyramiding_signal(stock_code, df):
                        self.pyramiding_done[stock_code] = True
                        
                        current_price = close.iloc[-1]
                        # 불타기는 원금의 50%만
                        pyramid_capital = self.capital / 2
                        quantity = int(pyramid_capital / current_price)
                        
                        if quantity > 0:
                            return Signal(
                                signal_type=SignalType.BUY,
                                stock_code=stock_code,
                                stock_name=stock_code,
                                reason=f"불타기: 2일 연속 양봉+거래량 유지",
                                price=int(current_price),
                                quantity=quantity,
                                stop_loss=pos.stop_loss,
                                take_profit=pos.take_profit,
                            )
                return None
        
        # 신규 진입 조건 확인
        if not self._is_squeeze(bandwidth):
            return None
        
        if not self._is_breakout(df, upper):
            return None
        
        if not self._has_volume_surge(df):
            return None
        
        # 양봉 확인
        today = df.iloc[-1]
        if today["close"] <= today["open"]:
            return None
        
        current_price = close.iloc[-1]
        sma20 = middle.iloc[-1]
        
        # 돌파 캔들 저가 저장
        self.entry_candle_low[stock_code] = today["low"]
        
        # 손절: 돌파 캔들 저가 또는 20일선 (먼저 오는 것)
        stop_loss = max(int(today["low"] * 0.98), int(sma20 * 0.98))
        
        # 목표: 전고점 또는 +15%
        recent_high = close.max()
        take_profit = max(int(recent_high), int(current_price * 1.15))
        
        quantity = self.calculate_position_size(current_price, stop_loss)
        
        if quantity == 0:
            return None
        
        return Signal(
            signal_type=SignalType.BUY,
            stock_code=stock_code,
            stock_name=stock_code,
            reason=f"스퀴즈 돌파 (밴드폭: {bandwidth.iloc[-1]:.1f}%, 거래량 급증)",
            price=int(current_price),
            quantity=quantity,
            stop_loss=stop_loss,
            take_profit=take_profit,
        )
    
    def check_exit_signal(self, position: Position, df: pd.DataFrame) -> Optional[Signal]:
        """
        매도 시그널 (블로그 원문)
        
        조건:
        1. 손절: 돌파 캔들 저가 이탈 또는 20일선 이탈
        2. 1차 익절: 전고점/+15% 도달 시 50%
        3. 2차: 전일 저가 이탈 또는 10일선 이탈
        """
        if df.empty or len(df) < 20:
            return None
        
        close = df["close"]
        current_price = close.iloc[-1]
        prev_low = df["low"].iloc[-2]
        sma20 = sma(close, 20).iloc[-1]
        sma10 = sma(close, 10).iloc[-1]
        
        # 돌파 캔들 저가 이탈
        entry_low = self.entry_candle_low.get(position.stock_code)
        if entry_low and current_price < entry_low:
            self._cleanup_position_data(position.stock_code)
            return Signal(
                signal_type=SignalType.SELL,
                stock_code=position.stock_code,
                stock_name=position.stock_name,
                reason=f"돌파 캔들 저가 이탈: {current_price:,}원",
                price=int(current_price),
                quantity=position.quantity,
            )
        
        # 손절: stop_loss 이탈
        if current_price <= position.stop_loss:
            self._cleanup_position_data(position.stock_code)
            return Signal(
                signal_type=SignalType.SELL,
                stock_code=position.stock_code,
                stock_name=position.stock_name,
                reason=f"손절: {current_price:,}원",
                price=int(current_price),
                quantity=position.quantity,
            )
        
        # 20일선 이탈
        if pd.notna(sma20) and current_price < sma20:
            profit_rate = (current_price - position.entry_price) / position.entry_price * 100
            self._cleanup_position_data(position.stock_code)
            return Signal(
                signal_type=SignalType.SELL,
                stock_code=position.stock_code,
                stock_name=position.stock_name,
                reason=f"20일선 이탈 (수익률: {profit_rate:+.1f}%)",
                price=int(current_price),
                quantity=position.quantity,
            )
        
        # 1차 익절: 목표가 도달 또는 중심선(20일선) 터치 (블로그 원문)
        # 돌파 후 상승했다가 20일선으로 회귀 시에도 1차 익절
        if position.stock_code not in self.partial_sold:
            # 조건1: 목표가(전고점/+15%) 도달
            target_reached = position.take_profit and current_price >= position.take_profit
            
            # 조건2: 중심선(20일선) 터치 - 단, 수익 상태일 때만
            # (돌파 후 상승했다가 20일선으로 회귀하는 경우)
            profit_rate = (current_price - position.entry_price) / position.entry_price * 100
            centerline_touch = pd.notna(sma20) and current_price <= sma20 * 1.02 and profit_rate > 0
            
            if target_reached or centerline_touch:
                self.partial_sold[position.stock_code] = True
                sell_qty = position.quantity // 2
                
                if sell_qty > 0:
                    reason = "목표가 도달" if target_reached else "중심선(20일선) 회귀"
                    return Signal(
                        signal_type=SignalType.SELL,
                        stock_code=position.stock_code,
                        stock_name=position.stock_name,
                        reason=f"1차 익절: {reason} (수익률: {profit_rate:+.1f}%)",
                        price=int(current_price),
                        quantity=sell_qty,
                    )
        
        # 2차: 전일 저가 이탈 (1차 익절 후)
        if position.stock_code in self.partial_sold and current_price < prev_low:
            profit_rate = (current_price - position.entry_price) / position.entry_price * 100
            self._cleanup_position_data(position.stock_code)
            return Signal(
                signal_type=SignalType.SELL,
                stock_code=position.stock_code,
                stock_name=position.stock_name,
                reason=f"전일 저가 이탈 (수익률: {profit_rate:+.1f}%)",
                price=int(current_price),
                quantity=position.quantity,
            )
        
        # 10일선 이탈 (1차 익절 후)
        if position.stock_code in self.partial_sold and pd.notna(sma10) and current_price < sma10:
            profit_rate = (current_price - position.entry_price) / position.entry_price * 100
            self._cleanup_position_data(position.stock_code)
            return Signal(
                signal_type=SignalType.SELL,
                stock_code=position.stock_code,
                stock_name=position.stock_name,
                reason=f"10일선 이탈 (수익률: {profit_rate:+.1f}%)",
                price=int(current_price),
                quantity=position.quantity,
            )
        
        return None
    
    def _cleanup_position_data(self, stock_code: str):
        """포지션 관련 데이터 정리"""
        if stock_code in self.partial_sold:
            del self.partial_sold[stock_code]
        if stock_code in self.entry_candle_low:
            del self.entry_candle_low[stock_code]
        if stock_code in self.pyramiding_done:
            del self.pyramiding_done[stock_code]
