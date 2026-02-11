"""
종목 스크리너 - 블로그 저자 방식 100%

블로그 원문:
- 시가총액 3,000억 이상
- 20일 평균 거래대금 > 50억
- 각 전략별 사전 필터링
"""
import FinanceDataReader as fdr
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Dict
from data.market_data import market_data
from data.naver_finance import naver_finance
from indicators.technical import sma, bollinger_bands, stochastic_slow


class StockScreener:
    """블로그 저자 방식 스크리너 (시총/거래대금 필터 포함)"""
    
    def __init__(self):
        self.kospi_stocks = []
        self.kosdaq_stocks = []
        self.filtered_stocks = []  # 시총/거래대금 필터 통과 종목
        self._load_stock_list()
    
    def _load_stock_list(self):
        """코스피/코스닥 전체 종목 로드"""
        try:
            kospi = fdr.StockListing('KOSPI')
            self.kospi_stocks = kospi[['Code', 'Name']].to_dict('records')
            
            kosdaq = fdr.StockListing('KOSDAQ')
            self.kosdaq_stocks = kosdaq[['Code', 'Name']].to_dict('records')
            
            print(f"[SCREENER] 종목 로드: 코스피 {len(self.kospi_stocks)}개, 코스닥 {len(self.kosdaq_stocks)}개")
            
        except Exception as e:
            print(f"[ERROR] 종목 리스트 로드 실패: {e}")
    
    def filter_by_market_cap_and_volume(self, min_cap_억: int = 3000, min_volume_억: int = 50) -> List[str]:
        """
        시가총액 + 거래대금 필터 (블로그 원문)
        - 시가총액 3,000억 이상
        - 20일 평균 거래대금 50억 이상
        """
        if self.filtered_stocks:
            return self.filtered_stocks
        
        all_stocks = self.kospi_stocks + self.kosdaq_stocks
        print(f"[SCREENER] 시총/거래대금 필터 적용 중... ({len(all_stocks)}개)")
        
        filtered = []
        checked = 0
        
        for stock in all_stocks:
            code = stock['Code']
            
            try:
                # 시가총액 확인
                cap = naver_finance.get_market_cap(code)
                if cap is None or cap < min_cap_억:
                    continue
                
                # 거래대금 확인
                vol_value = naver_finance.get_avg_volume_value(code)
                if vol_value is None or vol_value < min_volume_억:
                    continue
                
                filtered.append(code)
                checked += 1
                
                if checked % 50 == 0:
                    print(f"  통과: {len(filtered)}개 / 확인: {checked}개")
                    
            except Exception as e:
                continue
        
        self.filtered_stocks = filtered
        print(f"[SCREENER] 시총/거래대금 필터 완료: {len(filtered)}개")
        return filtered
    
    def get_surge_stocks(self, min_surge: float = 0.30, days: int = 20) -> List[str]:
        """
        최근 N일간 급등주 (눌림목 전략용)
        
        조건 (블로그):
        - 최근 1개월 +30% 이상 급등
        - 시총 3000억+, 거래대금 50억+
        """
        base_stocks = self.filter_by_market_cap_and_volume()
        surge_stocks = []
        
        print(f"[SCREENER] 급등주 스캔 중... ({len(base_stocks)}개)")
        
        for i, code in enumerate(base_stocks):
            if i % 50 == 0:
                print(f"  진행: {i}/{len(base_stocks)}")
            
            try:
                df = market_data.get_ohlcv(code, count=days + 5)
                
                if df.empty or len(df) < days:
                    continue
                
                close = df['close']
                start_price = close.iloc[0]
                max_price = close.max()
                
                surge = (max_price - start_price) / start_price
                
                if surge >= min_surge:
                    surge_stocks.append(code)
                    
            except:
                continue
        
        print(f"[SCREENER] 급등주: {len(surge_stocks)}개")
        return surge_stocks
    
    def get_high_volatility_kosdaq(self, min_volatility: float = 0.03) -> List[str]:
        """
        코스닥 고변동성 종목 (엔벨로프 전략용)
        
        조건 (블로그):
        - 코스닥
        - 일평균 변동폭 3% 이상
        - 시총 3000억+, 거래대금 50억+
        """
        base_stocks = self.filter_by_market_cap_and_volume()
        kosdaq_codes = [s['Code'] for s in self.kosdaq_stocks]
        
        # 코스닥만 필터
        kosdaq_base = [c for c in base_stocks if c in kosdaq_codes]
        volatile_stocks = []
        
        print(f"[SCREENER] 코스닥 고변동성 스캔 중... ({len(kosdaq_base)}개)")
        
        for i, code in enumerate(kosdaq_base):
            if i % 50 == 0:
                print(f"  진행: {i}/{len(kosdaq_base)}")
            
            try:
                df = market_data.get_ohlcv(code, count=20)
                
                if df.empty or len(df) < 10:
                    continue
                
                df['range'] = (df['high'] - df['low']) / df['close']
                avg_volatility = df['range'].mean()
                
                if avg_volatility >= min_volatility:
                    volatile_stocks.append(code)
                    
            except:
                continue
        
        print(f"[SCREENER] 고변동성: {len(volatile_stocks)}개")
        return volatile_stocks
    
    def get_uptrend_pullback(self) -> List[str]:
        """
        상승추세 + 눌림 중인 종목 (스토캐스틱 전략용)
        
        조건 (블로그):
        - 가격 > SMA20 > SMA60 (정배열)
        - 스토캐스틱 K < 30 (과매도 근처)
        """
        base_stocks = self.filter_by_market_cap_and_volume()
        candidates = []
        
        print(f"[SCREENER] 상승추세 눌림목 스캔 중... ({len(base_stocks)}개)")
        
        for i, code in enumerate(base_stocks):
            if i % 50 == 0:
                print(f"  진행: {i}/{len(base_stocks)}")
            
            try:
                df = market_data.get_ohlcv(code, count=70)
                
                if df.empty or len(df) < 60:
                    continue
                
                close = df['close']
                high = df['high']
                low = df['low']
                
                sma20 = sma(close, 20)
                sma60 = sma(close, 60)
                stoch_k, _ = stochastic_slow(high, low, close, 12, 5, 5)
                
                current = close.iloc[-1]
                current_sma20 = sma20.iloc[-1]
                current_sma60 = sma60.iloc[-1]
                current_k = stoch_k.iloc[-1]
                
                # 정배열 + 스토캐스틱 과매도 근처
                if current > current_sma20 > current_sma60 and current_k < 30:
                    candidates.append(code)
                    
            except:
                continue
        
        print(f"[SCREENER] 상승추세 눌림: {len(candidates)}개")
        return candidates
    
    def get_squeeze_stocks(self) -> List[str]:
        """
        볼린저밴드 수축 중인 종목 (볼린저 전략용)
        
        조건 (블로그):
        - 밴드폭이 6개월 최저 근처 또는 10% 이하
        """
        base_stocks = self.filter_by_market_cap_and_volume()
        squeeze_stocks = []
        
        print(f"[SCREENER] 볼린저 스퀴즈 스캔 중... ({len(base_stocks)}개)")
        
        for i, code in enumerate(base_stocks):
            if i % 50 == 0:
                print(f"  진행: {i}/{len(base_stocks)}")
            
            try:
                df = market_data.get_ohlcv(code, count=130)
                
                if df.empty or len(df) < 120:
                    continue
                
                close = df['close']
                _, _, _, bandwidth = bollinger_bands(close, 20, 2.0)
                
                current_bw = bandwidth.iloc[-1]
                min_bw = bandwidth.iloc[-120:].min()
                
                if current_bw <= min_bw * 1.1 or current_bw <= 10:
                    squeeze_stocks.append(code)
                    
            except:
                continue
        
        print(f"[SCREENER] 스퀴즈: {len(squeeze_stocks)}개")
        return squeeze_stocks
    
    def get_top_volume_stocks(self, top_n: int = 100) -> List[str]:
        """
        거래대금 상위 종목 (수급 전략용)
        
        조건 (블로그):
        - 시총 3000억+
        - 거래대금 상위 100개
        """
        base_stocks = self.filter_by_market_cap_and_volume()
        
        # 이미 거래대금 필터를 통과했으므로 그대로 반환
        print(f"[SCREENER] 거래대금 상위: {min(len(base_stocks), top_n)}개")
        return base_stocks[:top_n]


# 싱글톤
screener = StockScreener()
