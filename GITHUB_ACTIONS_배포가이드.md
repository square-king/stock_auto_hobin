# GitHub Actions 배포 가이드

내 컴퓨터를 켜두지 않아도 GitHub 서버에서 자동매매 봇이 돌아갑니다.

## 1단계: GitHub Private Repo 생성

1. https://github.com/new 접속
2. **Repository name**: `stock-auto-trading` (원하는 이름)
3. **Private** 선택 (코드 비공개)
4. **Create repository** 클릭

## 2단계: 코드 Push

터미널에서:
```bash
cd ~/Desktop/stock_auto_test
git add -A
git commit -m "init: 자동매매 봇"
git remote add origin https://github.com/<내GitHub아이디>/stock-auto-trading.git
git push -u origin main
```

## 3단계: Secrets 등록 (API키 설정)

GitHub 웹에서:
1. 내 repo 페이지 → **Settings** → **Secrets and variables** → **Actions**
2. **New repository secret** 으로 아래 6개 등록:

| Name | 값 |
|------|-----|
| `KIS_APP_KEY` | 한국투자증권 앱키 |
| `KIS_APP_SECRET` | 한국투자증권 시크릿 |
| `KIS_ACCOUNT_NO` | 계좌번호 (예: 12345678-01) |
| `KIS_IS_PAPER` | True (모의투자) 또는 False (실전) |
| `KAKAO_REST_API_KEY` | 카카오 REST API키 |
| `KAKAO_ACCESS_TOKEN` | 카카오 액세스 토큰 |

> .env 파일 내용을 그대로 넣으면 됩니다.

## 4단계: 끝!

Push하면 자동으로 스케줄이 돌아갑니다:

| KST 시간 | 작업 |
|-----------|------|
| **09:01** | 전일 시그널 → 매수 실행 |
| **09:10~15:20** | 10분마다 청산 시그널 체크 |
| **15:35** | 전략별 스크리닝 + 익일 시그널 |
| **15:40** | 일일 리포트 카카오톡 발송 |

## 실행 확인 방법

1. GitHub 웹 → 내 repo → **Actions** 탭
2. 워크플로우 실행 기록 확인 가능
3. 초록색 체크 = 성공, 빨간 X = 실패

## 수동 실행 (테스트)

1. **Actions** 탭 → **Stock Auto Trading** 클릭
2. **Run workflow** 버튼 클릭
3. 로그 확인

## 무료 사용량

- Private repo: 월 2,000분 무료
- 이 봇: 하루 약 45회 실행 × 1분 = 약 45분/일
- 월 약 990분 사용 → **넉넉함**

## 주의사항

1. `.env` 파일은 Git에 올라가지 않음 (Secrets으로 대체)
2. 상태 파일 (positions.json 등)은 Git에서 자동 관리
3. GitHub Actions cron은 ±5분 오차가 있을 수 있음 (스윙 매매라 문제없음)
