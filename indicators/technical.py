"""
기술적 지표 계산 모듈 - 이동평균, 엔벨로프, 스토캐스틱, 볼린저밴드
"""
import pandas as pd
import numpy as np
from typing import Tuple


def sma(prices: pd.Series, period: int) -> pd.Series:
    """
    단순 이동평균 (Simple Moving Average)
    
    Args:
        prices: 가격 시리즈
        period: 기간
    
    Returns:
        SMA 시리즈
    """
    return prices.rolling(window=period).mean()


def ema(prices: pd.Series, period: int) -> pd.Series:
    """
    지수 이동평균 (Exponential Moving Average)
    
    Args:
        prices: 가격 시리즈
        period: 기간
    
    Returns:
        EMA 시리즈
    """
    return prices.ewm(span=period, adjust=False).mean()


def envelope(prices: pd.Series, period: int = 20, percent: float = 20.0) -> Tuple[pd.Series, pd.Series, pd.Series]:
    """
    엔벨로프 (Envelope) 계산
    
    Args:
        prices: 가격 시리즈
        period: 이동평균 기간 (기본 20)
        percent: 밴드 폭 (기본 20%)
    
    Returns:
        (중심선, 상단밴드, 하단밴드)
    """
    center = sma(prices, period)
    upper = center * (1 + percent / 100)
    lower = center * (1 - percent / 100)
    
    return center, upper, lower


def stochastic_slow(high: pd.Series, low: pd.Series, close: pd.Series,
                    k_period: int = 12, d_period: int = 5, smooth: int = 5) -> Tuple[pd.Series, pd.Series]:
    """
    스토캐스틱 슬로우 (Stochastic Slow)
    
    블로그 설정: 12, 5, 5
    
    Args:
        high: 고가 시리즈
        low: 저가 시리즈
        close: 종가 시리즈
        k_period: %K 기간 (기본 12)
        d_period: %D 기간 (기본 5)
        smooth: 스무딩 기간 (기본 5)
    
    Returns:
        (%K, %D)
    """
    # 최저가, 최고가
    low_min = low.rolling(window=k_period).min()
    high_max = high.rolling(window=k_period).max()
    
    # Raw %K
    raw_k = (close - low_min) / (high_max - low_min) * 100
    
    # Slow %K (스무딩)
    stoch_k = raw_k.rolling(window=smooth).mean()
    
    # %D
    stoch_d = stoch_k.rolling(window=d_period).mean()
    
    return stoch_k, stoch_d


def bollinger_bands(prices: pd.Series, period: int = 20, num_std: float = 2.0) -> Tuple[pd.Series, pd.Series, pd.Series, pd.Series]:
    """
    볼린저밴드 (Bollinger Bands)
    
    Args:
        prices: 가격 시리즈
        period: 이동평균 기간 (기본 20)
        num_std: 표준편차 배수 (기본 2)
    
    Returns:
        (중심선, 상단밴드, 하단밴드, 밴드폭)
    """
    middle = sma(prices, period)
    std = prices.rolling(window=period).std()
    
    upper = middle + (num_std * std)
    lower = middle - (num_std * std)
    
    # 밴드폭 (%)
    bandwidth = (upper - lower) / middle * 100
    
    return middle, upper, lower, bandwidth


def cci(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 20) -> pd.Series:
    """
    CCI (Commodity Channel Index)
    
    Args:
        high: 고가 시리즈
        low: 저가 시리즈
        close: 종가 시리즈
        period: 기간 (기본 20)
    
    Returns:
        CCI 시리즈
    """
    # Typical Price
    tp = (high + low + close) / 3
    
    # SMA of Typical Price
    tp_sma = sma(tp, period)
    
    # Mean Deviation
    mean_dev = tp.rolling(window=period).apply(lambda x: np.abs(x - x.mean()).mean())
    
    # CCI
    cci_value = (tp - tp_sma) / (0.015 * mean_dev)
    
    return cci_value


def lwti(close: pd.Series, n1: int = 10, n2: int = 21) -> pd.Series:
    """
    LWTI (LazyBear WaveTrend Indicator) - 간소화 버전
    
    Args:
        close: 종가 시리즈
        n1: 채널 기간 (기본 10)
        n2: 평균 기간 (기본 21)
    
    Returns:
        LWTI 시리즈 (WT1)
    """
    # Average Price
    ap = close
    
    # ESA (EMA of AP)
    esa = ema(ap, n1)
    
    # D = EMA of |AP - ESA|
    d = ema(np.abs(ap - esa), n1)
    
    # CI (Channel Index)
    ci = (ap - esa) / (0.015 * d)
    
    # WT1 = EMA of CI
    wt1 = ema(ci, n2)
    
    return wt1


def volume_dry_up(volume: pd.Series, period: int = 20, threshold: float = 0.7) -> pd.Series:
    """
    거래량 드라이업 (Volume Dry-up) 확인
    
    급등 후 조정 구간에서 거래량이 감소하는 현상
    
    Args:
        volume: 거래량 시리즈
        period: 평균 기간
        threshold: 임계값 (평균 대비 비율, 기본 0.7 = 70%)
    
    Returns:
        드라이업 여부 (True/False) 시리즈
    """
    avg_volume = sma(volume, period)
    
    # 최근 5일 평균 거래량이 20일 평균의 70% 이하면 드라이업
    recent_avg = volume.rolling(window=5).mean()
    
    return recent_avg < (avg_volume * threshold)


def is_golden_cross(fast: pd.Series, slow: pd.Series) -> pd.Series:
    """
    골든크로스 판별
    
    Args:
        fast: 빠른 지표 (예: %K)
        slow: 느린 지표 (예: %D)
    
    Returns:
        골든크로스 발생 여부 시리즈
    """
    # 현재 fast > slow 이고 이전에 fast <= slow 였다면 골든크로스
    cross = (fast > slow) & (fast.shift(1) <= slow.shift(1))
    return cross


def is_dead_cross(fast: pd.Series, slow: pd.Series) -> pd.Series:
    """
    데드크로스 판별
    
    Args:
        fast: 빠른 지표 (예: %K)
        slow: 느린 지표 (예: %D)
    
    Returns:
        데드크로스 발생 여부 시리즈
    """
    # 현재 fast < slow 이고 이전에 fast >= slow 였다면 데드크로스
    cross = (fast < slow) & (fast.shift(1) >= slow.shift(1))
    return cross
