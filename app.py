import json
import os
from datetime import date

import feedparser
import google.generativeai as genai
import streamlit as st
from github import Github


# ──────────────────────────────────────────────
# 스토리지 헬퍼 함수
# USE_LOCAL_STORAGE가 true일 경우 로컬 JSON 파일로 관리하며,
# false일 경우 GitHub 리포지토리의 JSON 파일로 관리합니다.
# ──────────────────────────────────────────────


def get_github_repo():
    """st.secrets에 설정된 토큰과 리포지토리명으로 GitHub Repo 객체를 반환합니다."""
    g = Github(st.secrets["GITHUB_TOKEN"])
    return g.get_repo(st.secrets["GITHUB_REPO"])


def read_json_from_github(filename, default=None):
    """GitHub 리포지토리 또는 로컬 파일 시스템에서 JSON 파일을 읽어 파싱합니다.

    Args:
        filename: 읽을 JSON 파일명 (예: "feeds.json")
        default: 파일이 존재하지 않을 경우 반환할 기본값

    Returns:
        파싱된 JSON 데이터, 또는 파일이 없으면 default 값
    """
    # 로컬 스토리지 모드가 켜져 있는 경우, 로컬 파일 시스템을 조회합니다.
    if st.secrets.get("USE_LOCAL_STORAGE", False):
        try:
            if os.path.exists(filename):
                with open(filename, "r", encoding="utf-8") as f:
                    return json.load(f)
            return default if default is not None else {}
        except Exception:
            return default if default is not None else {}

    # 원격 GitHub 저장소 연동 모드
    try:
        repo = get_github_repo()
        content = repo.get_contents(filename)
        return json.loads(content.decoded_content.decode("utf-8"))
    except Exception:
        return default if default is not None else {}


def write_json_to_github(filename, data, message="Update data"):
    """GitHub 리포지토리 또는 로컬 파일 시스템에 JSON 파일을 저장합니다.

    로컬 모드 시에는 파일에 직접 기록하고, GitHub 모드 시에는 커밋(Commit) 처리합니다.

    Args:
        filename: 저장할 JSON 파일명
        data: JSON 직렬화 가능한 데이터
        message: Git 커밋 메시지
    """
    # 로컬 스토리지 모드가 켜져 있는 경우, 로컬 파일 시스템에 저장합니다.
    if st.secrets.get("USE_LOCAL_STORAGE", False):
        try:
            with open(filename, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            return
        except Exception as e:
            st.error(f"로컬 파일 저장에 실패했습니다 ({filename}): {e}")
            return

    # 원격 GitHub 저장소 연동 모드
    repo = get_github_repo()
    content_str = json.dumps(data, ensure_ascii=False, indent=2)
    try:
        existing = repo.get_contents(filename)
        repo.update_file(filename, message, content_str, existing.sha)
    except Exception:
        repo.create_file(filename, message, content_str)



# ──────────────────────────────────────────────
# 방문자 통계
# ──────────────────────────────────────────────


def increment_visitors():
    """방문자 수를 1 증가시키고 stats.json에 반영합니다."""
    stats = read_json_from_github("stats.json", {"visitors": 0})
    stats["visitors"] += 1
    write_json_to_github("stats.json", stats, "Update visitor count")
    return stats["visitors"]


# ──────────────────────────────────────────────
# RSS 피드 수집
# ──────────────────────────────────────────────


def fetch_news_from_feeds(feed_urls):
    """등록된 RSS 피드 URL 목록에서 최신 기사를 수집합니다.

    Args:
        feed_urls: RSS 피드 URL 리스트

    Returns:
        수집된 기사 딕셔너리 리스트 (title, link, summary 포함)
    """
    articles = []
    for url in feed_urls:
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:10]:  # 피드당 최대 10개 기사
                articles.append({
                    "title": entry.get("title", ""),
                    "link": entry.get("link", ""),
                    "summary": entry.get("summary", ""),
                })
        except Exception:
            st.warning(f"피드 수집 실패: {url}")
    return articles


# ──────────────────────────────────────────────
# Gemini API 브리핑 생성
# ──────────────────────────────────────────────


def generate_briefing(articles):
    """수집된 기사 목록을 Gemini API에 전달하여 요약 브리핑을 생성합니다.

    Args:
        articles: fetch_news_from_feeds()가 반환한 기사 리스트

    Returns:
        Gemini가 생성한 브리핑 텍스트 (마크다운 형식)
    """
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    model = genai.GenerativeModel("gemini-3.1-flash-lite")

    # 기사 정보를 프롬프트용 텍스트로 변환
    articles_text = "\n".join(
        f"- 제목: {a['title']}\n  요약: {a['summary']}"
        for a in articles
    )

    prompt = (
        "다음은 오늘의 주요 IT 뉴스 기사 목록입니다.\n"
        "이 기사들을 분석하여 한국어로 된 뉴스 브리핑을 작성해 주세요.\n"
        "주요 트렌드와 핵심 내용을 정리하고, 읽기 쉽게 구성해 주세요.\n\n"
        f"{articles_text}"
    )

    response = model.generate_content(prompt)
    return response.text


# ──────────────────────────────────────────────
# 페이지: 메인 뉴스룸
# ──────────────────────────────────────────────


def page_newsroom():
    """메인 뉴스룸 화면: news_data.json의 브리핑을 날짜별로 표시합니다."""
    st.title("📰 IT Newsroom")
    st.caption("국내 IT 뉴스 자동 브리핑 서비스")

    news_data = read_json_from_github("news_data.json", {})

    if not news_data:
        st.info("아직 생성된 뉴스 브리핑이 없습니다.")
        return

    # 최신 날짜순(내림차순)으로 정렬하여 표시
    sorted_dates = sorted(news_data.keys(), reverse=True)

    for i, date_key in enumerate(sorted_dates):
        # 가장 최신 날짜만 기본 펼침 상태로 표시
        with st.expander(f"📅 {date_key}", expanded=(i == 0)):
            st.markdown(news_data[date_key])


# ──────────────────────────────────────────────
# 페이지: 관리자 대시보드
# ──────────────────────────────────────────────


def page_admin():
    """관리자 대시보드: 인증 후 RSS 관리, 뉴스 수집, 통계를 제공합니다."""
    st.title("🔧 관리자 대시보드")

    # ── 비밀번호 인증 ──
    if "admin_authenticated" not in st.session_state:
        st.session_state.admin_authenticated = False

    if not st.session_state.admin_authenticated:
        password = st.text_input("관리자 비밀번호", type="password")
        if st.button("로그인"):
            if password == st.secrets["ADMIN_PASSWORD"]:
                st.session_state.admin_authenticated = True
                st.rerun()
            else:
                st.error("비밀번호가 올바르지 않습니다.")
        return

    # ── RSS 피드 관리 ──
    st.subheader("📡 RSS 피드 관리")
    feeds = read_json_from_github("feeds.json", [])

    # 새 피드 추가
    new_feed = st.text_input("새 RSS 피드 URL")
    if st.button("피드 추가") and new_feed:
        feeds.append(new_feed)
        write_json_to_github("feeds.json", feeds, "Add RSS feed")
        st.success(f"추가 완료: {new_feed}")
        st.rerun()

    # 등록된 피드 목록 표시 및 개별 삭제
    if feeds:
        st.write("**등록된 피드:**")
        for i, url in enumerate(feeds):
            col1, col2 = st.columns([4, 1])
            col1.write(url)
            if col2.button("삭제", key=f"del_{i}"):
                feeds.pop(i)
                write_json_to_github("feeds.json", feeds, "Remove RSS feed")
                st.rerun()
    else:
        st.info("등록된 피드가 없습니다.")

    st.divider()

    # ── 뉴스 수집 및 브리핑 생성 ──
    st.subheader("🤖 뉴스 수집 및 브리핑 생성")
    if st.button("오늘의 브리핑 생성"):
        if not feeds:
            st.warning("먼저 RSS 피드를 등록해 주세요.")
        else:
            with st.spinner("기사 수집 중..."):
                articles = fetch_news_from_feeds(feeds)

            if not articles:
                st.warning("수집된 기사가 없습니다.")
            else:
                st.info(f"{len(articles)}개 기사 수집 완료. 브리핑 생성 중...")
                with st.spinner("Gemini API로 브리핑 생성 중..."):
                    briefing = generate_briefing(articles)

                # 오늘 날짜를 키로 news_data.json에 저장
                today = date.today().isoformat()
                news_data = read_json_from_github("news_data.json", {})
                news_data[today] = briefing
                write_json_to_github(
                    "news_data.json", news_data, f"Add briefing for {today}"
                )

                st.success("브리핑이 생성되었습니다!")
                st.markdown(briefing)

    st.divider()

    # ── 접속자 통계 ──
    st.subheader("📊 접속자 통계")
    stats = read_json_from_github("stats.json", {"visitors": 0})
    st.metric("누적 방문자 수", stats["visitors"])


# ──────────────────────────────────────────────
# 메인 앱 실행
# ──────────────────────────────────────────────


def main():
    """앱 진입점: 페이지 설정, 방문자 카운트, 사이드바 라우팅을 처리합니다."""
    st.set_page_config(page_title="IT Newsroom", page_icon="📰", layout="wide")

    # 세션당 1회만 방문자 수 증가
    if "visited" not in st.session_state:
        st.session_state.visited = True
        increment_visitors()

    # 사이드바 네비게이션
    page = st.sidebar.radio("메뉴", ["📰 뉴스룸", "🔧 관리자"])

    if page == "📰 뉴스룸":
        page_newsroom()
    else:
        page_admin()


if __name__ == "__main__":
    main()
