"""
한국투자증권 API 클라이언트
"""
import requests
import json
import time
from datetime import datetime
from typing import Optional, Dict, Any
import sys
sys.path.append('..')
from config.settings import (
    KIS_APP_KEY, KIS_APP_SECRET, KIS_ACCOUNT_NO,
    KIS_BASE_URL, KIS_IS_PAPER
)


class KISApi:
    """한국투자증권 API 클라이언트"""
    
    def __init__(self):
        self.app_key = KIS_APP_KEY
        self.app_secret = KIS_APP_SECRET
        self.account_no = KIS_ACCOUNT_NO
        self.base_url = KIS_BASE_URL
        self.is_paper = KIS_IS_PAPER
        self.access_token: Optional[str] = None
        self.token_expired_at: Optional[datetime] = None
        
    def _get_headers(self, tr_id: str) -> Dict[str, str]:
        """API 요청 헤더 생성"""
        if not self.access_token:
            self._get_access_token()
            
        return {
            "Content-Type": "application/json; charset=utf-8",
            "authorization": f"Bearer {self.access_token}",
            "appkey": self.app_key,
            "appsecret": self.app_secret,
            "tr_id": tr_id,
        }
    
    def _get_access_token(self) -> str:
        """접근 토큰 발급"""
        url = f"{self.base_url}/oauth2/tokenP"
        headers = {"Content-Type": "application/json"}
        body = {
            "grant_type": "client_credentials",
            "appkey": self.app_key,
            "appsecret": self.app_secret,
        }
        
        response = requests.post(url, headers=headers, json=body)
        response.raise_for_status()
        
        data = response.json()
        self.access_token = data["access_token"]
        self.token_expired_at = datetime.now()
        
        return self.access_token
    
    def get_price(self, stock_code: str) -> Dict[str, Any]:
        """
        현재가 조회
        
        Args:
            stock_code: 종목코드 (6자리)
            
        Returns:
            현재가 정보 딕셔너리
        """
        tr_id = "FHKST01010100" if not self.is_paper else "FHKST01010100"
        url = f"{self.base_url}/uapi/domestic-stock/v1/quotations/inquire-price"
        
        headers = self._get_headers(tr_id)
        params = {
            "FID_COND_MRKT_DIV_CODE": "J",  # 주식
            "FID_INPUT_ISCD": stock_code,
        }
        
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        
        return response.json()
    
    def get_daily_price(self, stock_code: str, period: str = "D", count: int = 100) -> Dict[str, Any]:
        """
        일별 시세 조회
        
        Args:
            stock_code: 종목코드
            period: D(일), W(주), M(월)
            count: 조회 개수
            
        Returns:
            일별 시세 데이터
        """
        tr_id = "FHKST01010400"
        url = f"{self.base_url}/uapi/domestic-stock/v1/quotations/inquire-daily-price"
        
        headers = self._get_headers(tr_id)
        params = {
            "FID_COND_MRKT_DIV_CODE": "J",
            "FID_INPUT_ISCD": stock_code,
            "FID_PERIOD_DIV_CODE": period,
            "FID_ORG_ADJ_PRC": "0",  # 수정주가 원주가 (0: 수정주가)
        }
        
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        
        return response.json()
    
    def get_balance(self) -> Dict[str, Any]:
        """
        계좌 잔고 조회
        
        Returns:
            계좌 잔고 정보
        """
        tr_id = "VTTC8434R" if self.is_paper else "TTTC8434R"
        url = f"{self.base_url}/uapi/domestic-stock/v1/trading/inquire-balance"
        
        headers = self._get_headers(tr_id)
        account_parts = self.account_no.split("-")
        
        params = {
            "CANO": account_parts[0],
            "ACNT_PRDT_CD": account_parts[1],
            "AFHR_FLPR_YN": "N",
            "OFL_YN": "",
            "INQR_DVSN": "02",
            "UNPR_DVSN": "01",
            "FUND_STTL_ICLD_YN": "N",
            "FNCG_AMT_AUTO_RDPT_YN": "N",
            "PRCS_DVSN": "00",
            "CTX_AREA_FK100": "",
            "CTX_AREA_NK100": "",
        }
        
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        
        return response.json()
    
    def buy_stock(self, stock_code: str, quantity: int, price: int = 0) -> Dict[str, Any]:
        """
        매수 주문
        
        Args:
            stock_code: 종목코드
            quantity: 수량
            price: 가격 (0이면 시장가)
            
        Returns:
            주문 결과
        """
        tr_id = "VTTC0802U" if self.is_paper else "TTTC0802U"
        url = f"{self.base_url}/uapi/domestic-stock/v1/trading/order-cash"
        
        headers = self._get_headers(tr_id)
        account_parts = self.account_no.split("-")
        
        # 시장가 vs 지정가
        ord_dvsn = "01" if price == 0 else "00"  # 01: 시장가, 00: 지정가
        
        body = {
            "CANO": account_parts[0],
            "ACNT_PRDT_CD": account_parts[1],
            "PDNO": stock_code,
            "ORD_DVSN": ord_dvsn,
            "ORD_QTY": str(quantity),
            "ORD_UNPR": str(price),
        }
        
        response = requests.post(url, headers=headers, json=body)
        response.raise_for_status()
        
        return response.json()
    
    def sell_stock(self, stock_code: str, quantity: int, price: int = 0) -> Dict[str, Any]:
        """
        매도 주문
        
        Args:
            stock_code: 종목코드
            quantity: 수량
            price: 가격 (0이면 시장가)
            
        Returns:
            주문 결과
        """
        tr_id = "VTTC0801U" if self.is_paper else "TTTC0801U"
        url = f"{self.base_url}/uapi/domestic-stock/v1/trading/order-cash"
        
        headers = self._get_headers(tr_id)
        account_parts = self.account_no.split("-")
        
        ord_dvsn = "01" if price == 0 else "00"
        
        body = {
            "CANO": account_parts[0],
            "ACNT_PRDT_CD": account_parts[1],
            "PDNO": stock_code,
            "ORD_DVSN": ord_dvsn,
            "ORD_QTY": str(quantity),
            "ORD_UNPR": str(price),
        }
        
        response = requests.post(url, headers=headers, json=body)
        response.raise_for_status()
        
        return response.json()
    
    def get_investor_trend(self, stock_code: str) -> Dict[str, Any]:
        """
        투자자별 매매동향 조회 (수급 데이터)
        
        Args:
            stock_code: 종목코드
            
        Returns:
            투자자별 매매동향
        """
        tr_id = "FHKST01010900"
        url = f"{self.base_url}/uapi/domestic-stock/v1/quotations/inquire-investor"
        
        headers = self._get_headers(tr_id)
        params = {
            "FID_COND_MRKT_DIV_CODE": "J",
            "FID_INPUT_ISCD": stock_code,
        }
        
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        
        return response.json()


# 싱글톤 인스턴스
kis_api = KISApi()
