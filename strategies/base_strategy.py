"""
전략 베이스 클래스
"""
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from enum import Enum
import pandas as pd


class SignalType(Enum):
    """시그널 타입"""
    BUY = "매수"
    SELL = "매도"
    HOLD = "관망"


@dataclass
class Signal:
    """매매 시그널"""
    signal_type: SignalType
    stock_code: str
    stock_name: str
    reason: str
    price: Optional[int] = None
    quantity: Optional[int] = None
    stop_loss: Optional[int] = None
    take_profit: Optional[int] = None


@dataclass
class Position:
    """포지션 정보"""
    stock_code: str
    stock_name: str
    quantity: int
    entry_price: float
    entry_date: str
    stop_loss: float
    take_profit: Optional[float] = None
    strategy_name: str = ""


class BaseStrategy(ABC):
    """전략 베이스 클래스"""
    
    def __init__(self, name: str, capital: float):
        """
        Args:
            name: 전략 이름
            capital: 배정 자금
        """
        self.name = name
        self.capital = capital
        self.positions: List[Position] = []
        self.max_positions = 1
        
    @abstractmethod
    def scan_candidates(self) -> List[str]:
        """
        매수 후보 종목 스캔
        
        Returns:
            종목코드 리스트
        """
        pass
    
    @abstractmethod
    def check_entry_signal(self, stock_code: str, df: pd.DataFrame) -> Optional[Signal]:
        """
        매수 시그널 확인
        
        Args:
            stock_code: 종목코드
            df: OHLCV DataFrame
            
        Returns:
            Signal 또는 None
        """
        pass
    
    @abstractmethod
    def check_exit_signal(self, position: Position, df: pd.DataFrame) -> Optional[Signal]:
        """
        매도 시그널 확인 (익절/손절)
        
        Args:
            position: 현재 포지션
            df: OHLCV DataFrame
            
        Returns:
            Signal 또는 None
        """
        pass
    
    def calculate_position_size(self, entry_price: float, stop_loss: float) -> int:
        """
        포지션 사이즈 계산 (1% 리스크 룰)
        
        Args:
            entry_price: 진입가
            stop_loss: 손절가
            
        Returns:
            매수 수량
        """
        risk_per_trade = self.capital * 0.01  # 자금의 1%
        risk_per_share = entry_price - stop_loss
        
        if risk_per_share <= 0:
            return 0
            
        quantity = int(risk_per_trade / risk_per_share)
        
        # 최대 자금의 50%까지만 투입
        max_quantity = int((self.capital * 0.5) / entry_price)
        
        return min(quantity, max_quantity) if quantity > 0 else 0
    
    def can_open_position(self) -> bool:
        """새 포지션 오픈 가능 여부"""
        return len(self.positions) < self.max_positions
    
    def add_position(self, position: Position):
        """포지션 추가"""
        position.strategy_name = self.name
        self.positions.append(position)
    
    def remove_position(self, stock_code: str):
        """포지션 제거"""
        self.positions = [p for p in self.positions if p.stock_code != stock_code]
    
    def get_position(self, stock_code: str) -> Optional[Position]:
        """특정 종목 포지션 조회"""
        for p in self.positions:
            if p.stock_code == stock_code:
                return p
        return None
