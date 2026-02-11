"""
20일선 눌림목 전략 (블로그 원문 100% 반영)

블로그 원문:
- 종목 선정: 최근 1개월 +30% 급등, 거래대금 충분
- 셋업: Volume Dry-up (거래량 감소)
- 트리거: 20일선 부근에서 지지 신호 (아래꼬리/양봉전환/전일고가 돌파)
- 진입: 지지 신호 캔들 발생 → 다음 거래일 그 캔들 고가 돌파 시 진입
- 손절: 20일선 이탈 또는 지지 캔들 저가 이탈 (먼저 오는것)
- 익절: 전고점 50% 분할, 잔여는 전일저가/10일선 이탈 시 청산
"""
import pandas as pd
from typing import Optional, List, Dict
from datetime import datetime
import sys
sys.path.append('..')
from strategies.base_strategy import BaseStrategy, Signal, SignalType, Position
from indicators.technical import sma, volume_dry_up
from data.market_data import market_data


class Pullback20MAStrategy(BaseStrategy):
    """20일선 눌림목 전략 (블로그 원문 100%)"""
    
    def __init__(self, capital: float):
        super().__init__("20일선 눌림목", capital)
        self.ma_period = 20
        self.stop_loss_percent = 0.05
        
        self.watchlist = []
        self.partial_sold = {}  # 1차 익절 여부
        self.pending_entry = {}  # 대기 중인 진입 (익일 고가 돌파 대기)
    
    def set_watchlist(self, stocks: List[str]):
        self.watchlist = stocks
    
    def _is_surge_stock(self, df: pd.DataFrame, threshold: float = 0.30) -> bool:
        """최근 1개월 급등 여부 (30% 이상)"""
        if len(df) < 20:
            return False
        
        close = df["close"]
        month_ago = close.iloc[-20]
        recent_high = close.iloc[-20:].max()
        
        return (recent_high - month_ago) / month_ago >= threshold
    
    def _has_volume_dryup(self, df: pd.DataFrame) -> bool:
        """거래량 드라이업 확인"""
        if len(df) < 20:
            return False
        
        volume = df["volume"]
        dryup = volume_dry_up(volume, period=20, threshold=0.7)
        
        return dryup.iloc[-1] if pd.notna(dryup.iloc[-1]) else False
    
    def _has_support_signal(self, df: pd.DataFrame) -> Dict:
        """
        지지 신호 확인 (블로그 원문)
        - 아래꼬리 (저가 대비 종가가 높음)
        - 양봉 전환
        - 전일 고가 돌파형
        
        Returns:
            {found: bool, candle_high: float, candle_low: float}
        """
        if len(df) < 2:
            return {"found": False}
        
        today = df.iloc[-1]
        yesterday = df.iloc[-2]
        
        # 오늘 양봉
        is_green = today["close"] > today["open"]
        
        # 아래꼬리: (종가 - 저가) > 몸통 * 1.5
        body = abs(today["close"] - today["open"])
        lower_tail = min(today["open"], today["close"]) - today["low"]
        has_lower_tail = lower_tail > body * 1.5 if body > 0 else lower_tail > 0
        
        # 어제 음봉 → 오늘 양봉 (양봉 전환)
        was_red = yesterday["close"] < yesterday["open"]
        reversal = was_red and is_green
        
        # 전일 고가 돌파
        breaks_prev_high = today["close"] > yesterday["high"]
        
        found = (is_green and has_lower_tail) or reversal or breaks_prev_high
        
        return {
            "found": found,
            "candle_high": today["high"],
            "candle_low": today["low"],
        }
    
    def scan_candidates(self) -> List[str]:
        """
        매수 후보 스캔
        - 최근 1개월 30% 이상 급등
        - 20일선 근처
        - Volume Dry-up
        - 지지 신호 발생 → 익일 고가 돌파 대기 종목으로 등록
        """
        candidates = []
        
        for stock_code in self.watchlist:
            try:
                df = market_data.get_ohlcv(stock_code, count=100)
                if df.empty or len(df) < 30:
                    continue
                
                # 급등주 필터
                if not self._is_surge_stock(df):
                    continue
                
                # Volume Dry-up 필터
                if not self._has_volume_dryup(df):
                    continue
                
                # 20일선 근처 (+/- 5%)
                close = df["close"]
                sma20 = sma(close, 20)
                current_price = close.iloc[-1]
                current_sma = sma20.iloc[-1]
                
                if pd.isna(current_sma):
                    continue
                
                distance = abs(current_price - current_sma) / current_sma
                if distance <= 0.05:
                    candidates.append(stock_code)
                    
            except Exception as e:
                continue
        
        return candidates
    
    def check_entry_signal(self, stock_code: str, df: pd.DataFrame) -> Optional[Signal]:
        """
        매수 시그널 확인 (블로그 원문대로)
        
        2단계 프로세스:
        1. 지지 신호 발생 → pending_entry에 등록 (고가, 저가 기록)
        2. 다음 스캔에서 고가 돌파 확인 → 진입
        """
        if df.empty or len(df) < 30:
            return None
        
        close = df["close"]
        current_price = close.iloc[-1]
        
        # 이미 대기 중인 진입이 있으면 고가 돌파 확인
        if stock_code in self.pending_entry:
            pending = self.pending_entry[stock_code]
            entry_high = pending["candle_high"]
            entry_low = pending["candle_low"]
            
            # 고가 돌파 확인
            if current_price > entry_high:
                # 손절가: 지지 캔들 저가 또는 20일선 (먼저 오는 것)
                sma20 = sma(close, 20).iloc[-1]
                stop_loss = min(int(entry_low * 0.98), int(sma20 * 0.98)) if pd.notna(sma20) else int(entry_low * 0.98)
                
                # 목표가: 최근 고점
                recent_high = close.iloc[-30:].max()
                
                # 포지션 사이즈
                quantity = self.calculate_position_size(current_price, stop_loss)
                
                # 대기 목록에서 제거
                del self.pending_entry[stock_code]
                
                if quantity == 0:
                    return None
                
                return Signal(
                    signal_type=SignalType.BUY,
                    stock_code=stock_code,
                    stock_name=stock_code,
                    reason=f"지지 캔들 고가 돌파 진입 ({entry_high:,.0f}원 돌파)",
                    price=int(current_price),
                    quantity=quantity,
                    stop_loss=stop_loss,
                    take_profit=int(recent_high),
                )
            else:
                # 아직 돌파 안함 - 대기 유지
                return None
        
        # 새로운 지지 신호 확인
        if not self._is_surge_stock(df):
            return None
        
        if not self._has_volume_dryup(df):
            return None
        
        sma20 = sma(close, 20)
        current_sma = sma20.iloc[-1]
        
        if pd.isna(current_sma):
            return None
        
        distance = abs(current_price - current_sma) / current_sma
        if distance > 0.05:
            return None
        
        support = self._has_support_signal(df)
        if support["found"]:
            # 익일 고가 돌파 대기로 등록
            self.pending_entry[stock_code] = {
                "candle_high": support["candle_high"],
                "candle_low": support["candle_low"],
                "registered_date": datetime.now().strftime("%Y-%m-%d"),
            }
            print(f"  [대기 등록] {stock_code}: 익일 {support['candle_high']:,.0f}원 돌파 시 진입")
        
        return None  # 오늘은 진입 X, 익일 대기
    
    def check_exit_signal(self, position: Position, df: pd.DataFrame) -> Optional[Signal]:
        """
        매도 시그널 확인 (블로그 원문대로)
        
        조건 (먼저 오는 것):
        1. 손절: 지지 캔들 저가 이탈 또는 20일선 이탈
        2. 1차 익절: 전고점 도달 시 50%
        3. 2차: 전일 저가 이탈 또는 10일선 이탈
        """
        if df.empty or len(df) < 20:
            return None
        
        close = df["close"]
        current_price = close.iloc[-1]
        prev_low = df["low"].iloc[-2]
        
        sma20 = sma(close, 20).iloc[-1]
        sma10 = sma(close, 10).iloc[-1]
        
        # 손절: stop_loss 이탈 (지지 캔들 저가 기준)
        if current_price <= position.stop_loss:
            if position.stock_code in self.partial_sold:
                del self.partial_sold[position.stock_code]
            return Signal(
                signal_type=SignalType.SELL,
                stock_code=position.stock_code,
                stock_name=position.stock_name,
                reason=f"손절: 지지 캔들 저가 이탈 {current_price:,}원",
                price=int(current_price),
                quantity=position.quantity,
            )
        
        # 20일선 이탈
        if pd.notna(sma20) and current_price < sma20:
            profit_rate = (current_price - position.entry_price) / position.entry_price * 100
            if position.stock_code in self.partial_sold:
                del self.partial_sold[position.stock_code]
            return Signal(
                signal_type=SignalType.SELL,
                stock_code=position.stock_code,
                stock_name=position.stock_name,
                reason=f"20일선 이탈 청산 (수익률: {profit_rate:+.1f}%)",
                price=int(current_price),
                quantity=position.quantity,
            )
        
        # 1차 익절: 전고점 도달 시 50%
        if position.take_profit and current_price >= position.take_profit:
            if position.stock_code not in self.partial_sold:
                self.partial_sold[position.stock_code] = True
                sell_qty = position.quantity // 2
                
                if sell_qty > 0:
                    profit_rate = (current_price - position.entry_price) / position.entry_price * 100
                    return Signal(
                        signal_type=SignalType.SELL,
                        stock_code=position.stock_code,
                        stock_name=position.stock_name,
                        reason=f"1차 익절: 전고점 도달 (수익률: {profit_rate:+.1f}%)",
                        price=int(current_price),
                        quantity=sell_qty,
                    )
        
        # 2차: 전일 저가 이탈 (1차 익절 후)
        if position.stock_code in self.partial_sold and current_price < prev_low:
            profit_rate = (current_price - position.entry_price) / position.entry_price * 100
            del self.partial_sold[position.stock_code]
            return Signal(
                signal_type=SignalType.SELL,
                stock_code=position.stock_code,
                stock_name=position.stock_name,
                reason=f"전일 저가 이탈 청산 (수익률: {profit_rate:+.1f}%)",
                price=int(current_price),
                quantity=position.quantity,
            )
        
        # 10일선 이탈 (1차 익절 후)
        if position.stock_code in self.partial_sold and pd.notna(sma10) and current_price < sma10:
            profit_rate = (current_price - position.entry_price) / position.entry_price * 100
            del self.partial_sold[position.stock_code]
            return Signal(
                signal_type=SignalType.SELL,
                stock_code=position.stock_code,
                stock_name=position.stock_name,
                reason=f"10일선 이탈 청산 (수익률: {profit_rate:+.1f}%)",
                price=int(current_price),
                quantity=position.quantity,
            )
        
        return None
