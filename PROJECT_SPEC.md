# 프로젝트 명세서: Automated IT Newsroom (PROJECT_SPEC.md)

## 1. 프로젝트 개요
본 프로젝트는 국내 IT 뉴스 RSS 피드를 자동으로 수집하고, Google Gemini API를 활용해 날짜별 뉴스 브리핑을 생성하는 웹 애플리케이션입니다. 데이터베이스(DB) 없이 **GitHub 리포지토리를 스토리지로 활용**하는 것이 핵심입니다.

## 2. 기술 스택 (Tech Stack)
- **Framework:** Python, Streamlit
- **AI Model:** Google Gemini API (gemini-3.1-flash-lite)
- **RSS Parser:** feedparser
- **Storage:** GitHub Repository (JSON 파일 관리)
- **Deployment:** Streamlit Community Cloud

## 3. 파일 및 데이터 구조
모든 데이터는 JSON 파일 형태로 GitHub에 저장합니다.
- `app.py`: 메인 애플리케이션 코드
- `requirements.txt`: 의존성 패키지 명세
- `feeds.json`: RSS 피드 URL 리스트 `List[str]`
- `news_data.json`: 날짜별 뉴스 데이터 `Dict[str, str]` (Key: "YYYY-MM-DD")
- `stats.json`: 방문자 통계 `Dict[str, int]` {"visitors": int}

## 4. 기능 요구사항

### 4.1. 메인 뉴스룸 (사용자 화면)
- 날짜별 주요 뉴스 브리핑을 1장짜리 화면으로 제공.
- `news_data.json`에서 데이터를 불러와 최신 날짜순(내림차순)으로 정렬.
- 각 날짜별로 `st.expander`를 사용하여 가독성 확보 (최신 데이터는 기본 펼침 상태).

### 4.2. 관리자 대시보드 (Admin)
- `st.secrets`에 정의된 비밀번호로 접근 제어.
- **RSS 피드 관리:** URL 추가 및 삭제(JSON 동기화).
- **수집 및 분석:** 
    - 등록된 RSS 피드에서 최신 기사 수집.
    - Gemini API를 호출하여 요약 브리핑 생성.
    - 결과물을 날짜별로 `news_data.json`에 저장.
- **접속자 통계:** `stats.json`을 기반으로 누적 방문자 수 표시.

## 5. 기술적 구현 제약 조건 (GitHub Storage)
- **휘발성 스토리지 대응:** Streamlit Cloud는 서버 재시작 시 로컬 데이터가 초기화됨.
- **GitHub API 활용:** `PyGithub` 라이브러리를 사용하여 모든 데이터는 리포지토리 내 JSON 파일로 실시간 Read/Write.
- **인증:** GitHub Token을 통해 인증하며, 모든 데이터 업데이트는 커밋(Commit) 처리를 포함해야 함.

## 6. 개발 지침 (For AI Assistant)
1. 코드를 작성할 때 항상 `@PROJECT_SPEC.md`의 구조를 준수할 것.
2. 모든 API Key 및 설정값은 `st.secrets`를 사용하는 구조로 작성할 것.
3. GitHub 스토리지 연동 시 예외 처리를 포함하여 네트워크 오류에 대비할 것.
4. 사용자 인터페이스는 Streamlit의 레이아웃 기능을 최대한 활용하여 깔끔하게 구성할 것.