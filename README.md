# Hobeen Macro Lab 자동매매 시스템

## 개요
Hobeen Macro Lab 블로그의 5개 매매 전략을 통합한 자동매매 시스템

## 설정
- 총 투자금: 200만원
- 전략당: 40만원
- 증권사: 한국투자증권
- 알림: 카카오톡

## 사용법

### 1. 의존성 설치
```bash
pip install -r requirements.txt
```

### 2. 설정 파일 수정
`config/settings.py`에서 API 키 설정

### 3. 실행
```bash
python main.py
```

## 전략 목록
1. 20일선 눌림목 (국내)
2. 엔벨로프 20-20 (국내)
3. 스토캐스틱 눌림목 (국내)
4. 볼린저 Squeeze (국내)
5. 수급 쌍끌이 (국내)

## 주의사항
- 실제 투자 전 모의투자로 테스트 권장
- API 키는 절대 공개 저장소에 업로드 금지
