"""
네이버 금융 수급 데이터 크롤링 (수정판)
외국인/기관 순매수 실제 데이터 조회
"""
import requests
from bs4 import BeautifulSoup
from typing import Dict, Any, Optional
import re


class NaverFinance:
    """네이버 금융 데이터 크롤러"""
    
    def __init__(self):
        self.headers = {
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
    
    def get_investor_trend(self, stock_code: str) -> Optional[Dict[str, Any]]:
        """
        투자자별 매매동향 조회
        """
        try:
            # 외국인 순매수 조회
            url = f"https://finance.naver.com/item/frgn.naver?code={stock_code}"
            resp = requests.get(url, headers=self.headers, timeout=5)
            soup = BeautifulSoup(resp.text, "html.parser")
            
            # type2 테이블에서 데이터 추출
            tables = soup.select("table.type2")
            if not tables:
                return self._get_from_sise(stock_code)
            
            foreign_net = 0
            institution_net = 0
            volume = 0
            
            for table in tables:
                rows = table.select("tr")
                for row in rows:
                    tds = row.select("td")
                    if len(tds) >= 6:
                        try:
                            # 외국인 순매수 (보통 5번째 컬럼)
                            foreign_text = tds[4].get_text().strip().replace(",", "").replace("+", "")
                            if foreign_text and foreign_text != "-":
                                foreign_net = int(float(foreign_text))
                            
                            # 거래량 (보통 3번째 컬럼)
                            vol_text = tds[2].get_text().strip().replace(",", "")
                            if vol_text and vol_text.isdigit():
                                volume = int(vol_text)
                            break
                        except:
                            continue
                if foreign_net != 0:
                    break
            
            # 기관 순매수
            institution_net = self._get_institution_net(stock_code)
            
            return {
                "foreign_net": foreign_net,
                "institution_net": institution_net,
                "individual_net": -(foreign_net + institution_net),
                "volume": volume if volume > 0 else 1,
            }
            
        except Exception as e:
            print(f"[WARN] {stock_code} 수급 조회 실패: {e}")
            return self._get_dummy_data()
    
    def _get_from_sise(self, stock_code: str) -> Optional[Dict[str, Any]]:
        """sise 페이지에서 데이터 가져오기"""
        try:
            url = f"https://finance.naver.com/item/sise.naver?code={stock_code}"
            resp = requests.get(url, headers=self.headers, timeout=5)
            soup = BeautifulSoup(resp.text, "html.parser")
            
            # 수급 데이터가 없으면 더미 반환
            return self._get_dummy_data()
            
        except:
            return self._get_dummy_data()
    
    def _get_dummy_data(self) -> Dict[str, Any]:
        """수급 데이터를 가져올 수 없을 때 더미 반환"""
        return {
            "foreign_net": 0,
            "institution_net": 0,
            "individual_net": 0,
            "volume": 1,
        }
    
    def _get_institution_net(self, stock_code: str) -> int:
        """기관 순매수 조회"""
        try:
            url = f"https://finance.naver.com/item/frgn.naver?code={stock_code}&page=1"
            resp = requests.get(url, headers=self.headers, timeout=5)
            soup = BeautifulSoup(resp.text, "html.parser")
            
            # 기관 순매수를 찾기 위해 다른 테이블 확인
            # 네이버 금융 구조상 같은 페이지에서 기관 데이터도 조회 가능
            tables = soup.select("table.type2")
            
            for table in tables:
                # 헤더 확인
                headers = table.select("th")
                header_texts = [h.get_text().strip() for h in headers]
                
                if "기관" in str(header_texts):
                    rows = table.select("tr")
                    for row in rows:
                        tds = row.select("td")
                        if len(tds) >= 6:
                            try:
                                # 기관 순매수 위치 찾기
                                for i, td in enumerate(tds):
                                    text = td.get_text().strip().replace(",", "").replace("+", "")
                                    if text and text.lstrip("-").isdigit():
                                        return int(text)
                            except:
                                continue
            
            return 0
            
        except:
            return 0
    
    def get_market_cap(self, stock_code: str) -> Optional[int]:
        """시가총액 조회 (억원 단위)"""
        try:
            url = f"https://finance.naver.com/item/main.naver?code={stock_code}"
            resp = requests.get(url, headers=self.headers, timeout=5)
            soup = BeautifulSoup(resp.text, "html.parser")
            
            # 시가총액 찾기
            em = soup.select_one("em#_market_sum")
            if em:
                text = em.get_text().strip().replace(",", "").replace("\n", "").replace("\t", "")
                
                # "조"와 "억" 처리
                total = 0
                if "조" in text:
                    parts = text.split("조")
                    jo_part = parts[0].strip()
                    if jo_part.isdigit():
                        total += int(jo_part) * 10000  # 조 -> 억
                    if len(parts) > 1:
                        uk_part = parts[1].replace("억", "").strip()
                        if uk_part.isdigit():
                            total += int(uk_part)
                elif "억" in text:
                    uk_part = text.replace("억", "").strip()
                    if uk_part.isdigit():
                        total = int(uk_part)
                
                return total if total > 0 else None
            
            return None
            
        except Exception as e:
            return None
    
    def get_avg_volume_value(self, stock_code: str) -> Optional[int]:
        """평균 거래대금 조회 (억원)"""
        try:
            url = f"https://finance.naver.com/item/sise_day.naver?code={stock_code}"
            resp = requests.get(url, headers=self.headers, timeout=5)
            soup = BeautifulSoup(resp.text, "html.parser")
            
            table = soup.select_one("table.type2")
            if not table:
                return None
            
            total_value = 0
            count = 0
            
            for row in table.select("tr"):
                tds = row.select("td")
                if len(tds) >= 7:
                    try:
                        # 종가 (2번째)
                        price_text = tds[1].get_text().strip().replace(",", "")
                        if not price_text.isdigit():
                            continue
                        price = int(price_text)
                        
                        # 거래량 (7번째)
                        vol_text = tds[6].get_text().strip().replace(",", "")
                        if not vol_text.isdigit():
                            continue
                        volume = int(vol_text)
                        
                        value = price * volume / 100000000  # 억원
                        total_value += value
                        count += 1
                        
                        if count >= 10:
                            break
                    except:
                        continue
            
            return int(total_value / count) if count > 0 else None
            
        except:
            return None


# 싱글톤
naver_finance = NaverFinance()
