"""
시장 데이터 수집 모듈
FinanceDataReader + KIS API 혼합 사용
"""
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
import FinanceDataReader as fdr


class MarketData:
    """시장 데이터 수집 및 관리"""
    
    def __init__(self):
        self.cache: Dict[str, pd.DataFrame] = {}
        self.cache_time: Dict[str, datetime] = {}
        
    def get_ohlcv(self, stock_code: str, period: str = "D", count: int = 100) -> pd.DataFrame:
        """
        OHLCV 데이터 조회 (FinanceDataReader 사용)
        
        Args:
            stock_code: 종목코드
            period: D(일), W(주), M(월)
            count: 조회 개수
            
        Returns:
            DataFrame with columns: date, open, high, low, close, volume
        """
        cache_key = f"{stock_code}_{period}_{count}"
        
        # 캐시 확인 (5분 이내면 캐시 사용)
        if cache_key in self.cache:
            cache_age = datetime.now() - self.cache_time.get(cache_key, datetime.min)
            if cache_age.total_seconds() < 300:  # 5분
                return self.cache[cache_key]
        
        try:
            # 시작일 계산 (여유있게 +50일)
            start_date = (datetime.now() - timedelta(days=count + 50)).strftime("%Y-%m-%d")
            
            # FinanceDataReader로 데이터 조회
            df = fdr.DataReader(stock_code, start_date)
            
            if df.empty:
                print(f"[WARN] {stock_code} 데이터 없음")
                return pd.DataFrame()
            
            # 컬럼명 정리
            df = df.reset_index()
            df.columns = [c.lower() for c in df.columns]
            
            # 컬럼명 매핑
            rename_map = {
                "index": "date",
                "날짜": "date",
            }
            df = df.rename(columns=rename_map)
            
            # 필요한 컬럼 확인
            required = ["date", "open", "high", "low", "close", "volume"]
            for col in required:
                if col not in df.columns:
                    print(f"[WARN] {stock_code} 누락된 컬럼: {col}")
                    return pd.DataFrame()
            
            # 최근 count개만 선택
            df = df.tail(count).reset_index(drop=True)
            
            # 캐시 저장
            self.cache[cache_key] = df
            self.cache_time[cache_key] = datetime.now()
            
            return df
            
        except Exception as e:
            print(f"[ERROR] {stock_code} OHLCV 조회 실패: {e}")
            return pd.DataFrame()
    
    def get_current_price(self, stock_code: str) -> Optional[Dict[str, Any]]:
        """
        현재가 조회 (FinanceDataReader 최신 데이터)
        
        Args:
            stock_code: 종목코드
            
        Returns:
            현재가 정보 딕셔너리
        """
        try:
            df = self.get_ohlcv(stock_code, count=5)
            
            if df.empty:
                return None
            
            latest = df.iloc[-1]
            prev = df.iloc[-2] if len(df) > 1 else latest
            
            change_rate = (latest["close"] - prev["close"]) / prev["close"] * 100
            
            return {
                "price": int(latest["close"]),
                "change_rate": round(change_rate, 2),
                "volume": int(latest["volume"]),
                "high": int(latest["high"]),
                "low": int(latest["low"]),
                "open": int(latest["open"]),
            }
            
        except Exception as e:
            print(f"[ERROR] {stock_code} 현재가 조회 실패: {e}")
            return None
    
    def get_investor_trend(self, stock_code: str) -> Optional[Dict[str, Any]]:
        """
        투자자별 매매동향 조회 (수급 데이터)
        FinanceDataReader는 수급 데이터를 직접 제공하지 않으므로
        간단한 더미 데이터 반환 (추후 확장 가능)
        
        Args:
            stock_code: 종목코드
            
        Returns:
            수급 정보 딕셔너리 (현재 더미)
        """
        # TODO: 실제 수급 데이터 연동 (네이버 금융 크롤링 등)
        return {
            "foreign_net": 0,
            "institution_net": 0,
            "individual_net": 0,
        }
    
    def clear_cache(self):
        """캐시 초기화"""
        self.cache = {}
        self.cache_time = {}


# 싱글톤 인스턴스
market_data = MarketData()
