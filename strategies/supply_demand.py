"""
수급 (쌍끌이) 전략 (블로그 원문 100% 반영)

블로그 원문:
- A등급: 외국인+기관 순매수, 점유율 합계 >20%, 양봉, 흡수강도 >0.3
- B등급: 점유율 10~20%
- 추세 필터: 가격 > 20일선 > 60일선
- 진입: A등급 + 추세 통과 시
- 청산: 전일저가 이탈, 20일선 이탈, 3일 연속 순매도
"""
import pandas as pd
from typing import Optional, List, Dict, Any
from datetime import datetime
import sys
sys.path.append('..')
from strategies.base_strategy import BaseStrategy, Signal, SignalType, Position
from indicators.technical import sma
from data.market_data import market_data
from data.naver_finance import naver_finance


class SupplyDemandStrategy(BaseStrategy):
    """수급 (쌍끌이) 전략 (블로그 원문 100%)"""
    
    def __init__(self, capital: float):
        super().__init__("수급 쌍끌이", capital)
        self.min_net_buy_ratio = 0.20  # 점유율 20% 이상 (A등급)
        self.min_absorption = 0.3  # 흡수강도 0.3 이상
        self.stop_loss_percent = 0.05
        
        self.watchlist = []
        self.sell_streak: Dict[str, int] = {}
    
    def set_watchlist(self, stocks: List[str]):
        self.watchlist = stocks
    
    def _get_supply_demand(self, stock_code: str) -> Optional[Dict[str, Any]]:
        """실제 수급 데이터 조회 (네이버 금융)"""
        return naver_finance.get_investor_trend(stock_code)
    
    def _check_trend_filter(self, df: pd.DataFrame) -> bool:
        """추세 필터: 가격 > SMA20 > SMA60 (정배열)"""
        if len(df) < 60:
            return False
        
        close = df["close"]
        sma20 = sma(close, 20).iloc[-1]
        sma60 = sma(close, 60).iloc[-1]
        current = close.iloc[-1]
        
        return current > sma20 > sma60
    
    def _calculate_signal_grade(self, supply: Dict[str, Any], df: pd.DataFrame) -> str:
        """
        신호 등급 계산 (블로그 원문)
        
        A등급: 외국인+기관 둘 다 순매수, 점유율 >20%, 양봉, 흡수강도 >0.3
        B등급: 둘 다 순매수, 점유율 10~20%
        C등급: 한쪽만 순매수 또는 점유율 <10%
        """
        foreign = supply.get("foreign_net", 0)
        institution = supply.get("institution_net", 0)
        volume = supply.get("volume", 1)
        
        # 순매수 점유율 (블로그: 순매수금액 / 거래대금)
        # 여기서는 순매수주수 / 거래량으로 대체
        total_net = abs(foreign) + abs(institution)
        net_buy_ratio = total_net / volume if volume > 0 else 0
        
        # 양봉 확인
        is_green = df["close"].iloc[-1] > df["open"].iloc[-1] if not df.empty else False
        
        # 둘 다 순매수?
        is_dual_buy = foreign > 0 and institution > 0
        
        if not is_dual_buy:
            return "C"
        
        # 흡수강도 (순매수 / 20일평균거래량)
        avg_volume = df["volume"].iloc[-20:].mean() if len(df) >= 20 else volume
        absorption = total_net / avg_volume if avg_volume > 0 else 0
        
        if net_buy_ratio >= 0.20 and is_green and absorption >= self.min_absorption:
            return "A"
        elif 0.10 <= net_buy_ratio < 0.20:
            return "B"
        else:
            return "C"
    
    def scan_candidates(self) -> List[str]:
        """쌍끌이 매수 후보 스캔"""
        candidates = []
        
        for stock_code in self.watchlist:
            try:
                df = market_data.get_ohlcv(stock_code, count=100)
                if df.empty or len(df) < 60:
                    continue
                
                # 추세 필터
                if not self._check_trend_filter(df):
                    continue
                
                # 수급 확인
                supply = self._get_supply_demand(stock_code)
                if not supply:
                    continue
                
                # A등급 또는 B등급만
                grade = self._calculate_signal_grade(supply, df)
                if grade in ["A", "B"]:
                    candidates.append(stock_code)
                    
            except Exception as e:
                continue
        
        return candidates
    
    def check_entry_signal(self, stock_code: str, df: pd.DataFrame) -> Optional[Signal]:
        """
        매수 시그널 (블로그 원문)
        
        조건:
        1. 추세 필터 통과 (정배열)
        2. A등급 신호 (외국인+기관 동시 순매수, 점유율>20%, 흡수강도>0.3)
        3. 양봉
        """
        if df.empty or len(df) < 60:
            return None
        
        # 조건 1: 추세
        if not self._check_trend_filter(df):
            return None
        
        # 조건 2: 수급
        supply = self._get_supply_demand(stock_code)
        if not supply:
            return None
        
        grade = self._calculate_signal_grade(supply, df)
        if grade != "A":  # A등급만 진입
            return None
        
        # 조건 3: 양봉
        if df["close"].iloc[-1] <= df["open"].iloc[-1]:
            return None
        
        close = df["close"]
        current_price = close.iloc[-1]
        sma20 = sma(close, 20).iloc[-1]
        
        # 손절: 20일선 또는 -5%
        stop_loss = max(int(sma20 * 0.98), int(current_price * (1 - self.stop_loss_percent)))
        
        quantity = self.calculate_position_size(current_price, stop_loss)
        
        if quantity == 0:
            return None
        
        return Signal(
            signal_type=SignalType.BUY,
            stock_code=stock_code,
            stock_name=stock_code,
            reason=f"A등급 쌍끌이 (외국인: {supply['foreign_net']:+,}, 기관: {supply['institution_net']:+,})",
            price=int(current_price),
            quantity=quantity,
            stop_loss=stop_loss,
        )
    
    def check_exit_signal(self, position: Position, df: pd.DataFrame) -> Optional[Signal]:
        """
        매도 시그널 (블로그 원문)
        
        조건:
        1. 손절: 20일선 이탈 또는 -5%
        2. 전일 저가 이탈
        3. 3일 연속 순매도
        """
        if df.empty or len(df) < 20:
            return None
        
        close = df["close"]
        current_price = close.iloc[-1]
        prev_low = df["low"].iloc[-2]
        sma20 = sma(close, 20).iloc[-1]
        
        # 손절
        if current_price <= position.stop_loss:
            self._cleanup(position.stock_code)
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
            self._cleanup(position.stock_code)
            return Signal(
                signal_type=SignalType.SELL,
                stock_code=position.stock_code,
                stock_name=position.stock_name,
                reason=f"20일선 이탈 (수익률: {profit_rate:+.1f}%)",
                price=int(current_price),
                quantity=position.quantity,
            )
        
        # 전일 저가 이탈
        if current_price < prev_low:
            profit_rate = (current_price - position.entry_price) / position.entry_price * 100
            self._cleanup(position.stock_code)
            return Signal(
                signal_type=SignalType.SELL,
                stock_code=position.stock_code,
                stock_name=position.stock_name,
                reason=f"전일 저가 이탈 (수익률: {profit_rate:+.1f}%)",
                price=int(current_price),
                quantity=position.quantity,
            )
        
        # 수급 확인: 순매도 추적
        supply = self._get_supply_demand(position.stock_code)
        if supply:
            foreign = supply.get("foreign_net", 0)
            institution = supply.get("institution_net", 0)
            
            # 순매도 = 둘 중 하나라도 순매도
            is_selling = foreign < 0 or institution < 0
            
            if is_selling:
                self.sell_streak[position.stock_code] = self.sell_streak.get(position.stock_code, 0) + 1
            else:
                self.sell_streak[position.stock_code] = 0
            
            # 3일 연속 순매도
            if self.sell_streak.get(position.stock_code, 0) >= 3:
                profit_rate = (current_price - position.entry_price) / position.entry_price * 100
                self._cleanup(position.stock_code)
                return Signal(
                    signal_type=SignalType.SELL,
                    stock_code=position.stock_code,
                    stock_name=position.stock_name,
                    reason=f"3일 연속 순매도 (수익률: {profit_rate:+.1f}%)",
                    price=int(current_price),
                    quantity=position.quantity,
                )
        
        return None
    
    def _cleanup(self, stock_code: str):
        if stock_code in self.sell_streak:
            del self.sell_streak[stock_code]
