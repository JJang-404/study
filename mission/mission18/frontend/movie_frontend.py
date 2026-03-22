import datetime
import streamlit as st
import requests
import pandas as pd
from utils import icon

# 1. UI Configuration
st.set_page_config(page_title="팝콘 감성 측정소", page_icon="🍿", layout="wide")

API_URL = "http://localhost:8000"
MAIN_COLOR_BLUE = "#5597DD"
MAIN_COLOR_PINK = "#D86EA3"

icon.show_icon("🎬")
st.markdown(
    f"<h1 style='color:{MAIN_COLOR_BLUE};'>🍿 팝콘 감성 측정소</h1>",
    unsafe_allow_html=True,
)
st.markdown(
    f"<p style='color:{MAIN_COLOR_PINK}; font-weight:bold;'>Mood & Movie 분석합니다.</p>",
    unsafe_allow_html=True,
)


# 캐시된 API 호출
@st.cache_data(ttl=60)
def fetch_movies():
    res = requests.get(f"{API_URL}/movies/")
    if res.status_code == 200:
        return res.json()
    return []


@st.cache_data(ttl=60)
def fetch_reviews(movie_id=None):
    params = {"movie_id": movie_id} if movie_id is not None else {}
    res = requests.get(f"{API_URL}/reviews/", params=params)
    if res.status_code == 200:
        return res.json()
    return []


# 세션 상태 초기화
if "selected_movie_id" not in st.session_state:
    st.session_state.selected_movie_id = None
if "editing_movie" not in st.session_state:
    st.session_state.editing_movie = None
if "pending_movie" not in st.session_state:
    st.session_state.pending_movie = None
if "duplicate_id" not in st.session_state:
    st.session_state.duplicate_id = None

# 2. 영화 데이터 로드
movies = []
try:
    movies = fetch_movies()
except Exception:
    st.error("백엔드 서버를 확인해주세요 (포트 8000)")

# 3. Sidebar
editing = st.session_state.editing_movie
is_edit_mode = editing is not None

with st.sidebar:
    if is_edit_mode:
        st.markdown(
            f"<h2 style='color:{MAIN_COLOR_PINK};'>✏️ 영화 수정</h2>",
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            f"<h2 style='color:{MAIN_COLOR_BLUE};'>🎥 영화 추가</h2>",
            unsafe_allow_html=True,
        )

    # 수정 모드일 때 개봉일 파싱
    default_date = datetime.date.today()
    if editing and editing.get("release_date"):
        try:
            default_date = datetime.date.fromisoformat(editing["release_date"])
        except Exception:
            pass

    with st.form("movie_form"):
        title = st.text_input("영화 제목", value=editing["title"] if editing else "")
        release_date = st.date_input("개봉일", value=default_date)
        director = st.text_input("감독", value=editing["director"] if editing else "")
        genre = st.text_input("장르", value=editing["genre"] if editing else "")
        poster_url = st.text_input(
            "포스터 이미지 URL", value=editing["poster_url"] if editing else ""
        )

        btn_label = "영화 수정" if is_edit_mode else "영화 등록"
        submitted = st.form_submit_button(btn_label, type="primary")

        if submitted:
            if title and poster_url:
                movie_data = {
                    "title": title,
                    "release_date": str(release_date),
                    "director": director,
                    "genre": genre,
                    "poster_url": poster_url,
                }
                if is_edit_mode:
                    # 수정 모드: 확인 없이 바로 PUT
                    try:
                        response = requests.put(
                            f"{API_URL}/movies/{editing['id']}", json=movie_data
                        )
                        if response.status_code == 200:
                            st.success(f"'{title}' 수정 완료!")
                            fetch_movies.clear()
                            st.session_state.editing_movie = None
                        else:
                            st.error("수정 실패")
                    except Exception as e:
                        st.error(f"서버 연결 오류: {e}")
                    st.rerun()
                else:
                    # 등록 모드: 중복 제목 체크
                    duplicate = next((m for m in movies if m["title"] == title), None)
                    if duplicate:
                        st.session_state.pending_movie = movie_data
                        st.session_state.duplicate_id = duplicate["id"]
                        st.rerun()
                    else:
                        registered = False
                        try:
                            response = requests.post(
                                f"{API_URL}/movies/", json=movie_data
                            )
                            if response.status_code == 200:
                                st.success(f"'{title}' 등록 완료!")
                                fetch_movies.clear()
                                registered = True
                            else:
                                st.error("등록 실패")
                        except Exception as e:
                            st.error(f"서버 연결 오류: {e}")
                        if registered:
                            st.rerun()
            else:
                st.warning("제목과 포스터 URL은 필수입니다.")

    # 수정 취소 버튼 (폼 밖)
    if is_edit_mode:
        if st.button("✕ 수정 취소", use_container_width=True):
            st.session_state.editing_movie = None
            st.rerun()

    # 중복 영화 확인 UI
    if st.session_state.pending_movie:
        dup_title = st.session_state.pending_movie["title"]
        st.warning(f"**'{dup_title}'** 영화가 이미 존재합니다.\n\n변경하시겠습니까?")
        btn_col1, btn_col2 = st.columns(2)
        with btn_col1:
            if st.button("변경", type="primary", use_container_width=True):
                try:
                    response = requests.put(
                        f"{API_URL}/movies/{st.session_state.duplicate_id}",
                        json=st.session_state.pending_movie,
                    )
                    if response.status_code == 200:
                        fetch_movies.clear()
                        st.session_state.pending_movie = None
                        st.session_state.duplicate_id = None
                        st.rerun()
                except Exception:
                    st.error("변경 실패")
        with btn_col2:
            if st.button("취소", use_container_width=True):
                st.session_state.pending_movie = None
                st.session_state.duplicate_id = None
                st.rerun()

# 4. 메인 레이아웃
col_main, col_reviews = st.columns([2, 1])

with col_main:
    # 상세 보기 모드
    if st.session_state.selected_movie_id is not None:
        movie = next(
            (m for m in movies if m["id"] == st.session_state.selected_movie_id), None
        )

        if st.button("← 목록으로 돌아가기"):
            st.session_state.selected_movie_id = None
            st.session_state.editing_movie = None
            st.rerun()

        if movie:
            st.markdown(f"## {movie['title']}")
            c1, c2 = st.columns([1, 2])
            with c1:
                st.image(movie["poster_url"], use_column_width=True)
            with c2:
                st.write(f"**감독:** {movie['director']}")
                st.write(f"**장르:** {movie['genre']}")
                st.write(f"**개봉일:** {movie['release_date']}")
                st.markdown(
                    f"**평균 평점(감성 점수):** <span style='color:{MAIN_COLOR_PINK}; font-weight:bold;'>{movie['average_rating']} / 5.0</span>",
                    unsafe_allow_html=True,
                )

            btn_c1, btn_c2 = st.columns(2)
            with btn_c1:
                if st.button("영화 정보 반영", use_container_width=True):
                    st.session_state.editing_movie = movie
                    st.rerun()
            with btn_c2:
                if st.button("영화 삭제", type="secondary", use_container_width=True):
                    need_rerun = False
                    try:
                        requests.delete(f"{API_URL}/movies/{movie['id']}")
                        fetch_movies.clear()
                        st.session_state.selected_movie_id = None
                        st.session_state.editing_movie = None
                        need_rerun = True
                    except Exception:
                        st.error("삭제 실패")
                    if need_rerun:
                        st.rerun()

            st.divider()
            st.markdown(f"### 💬 '{movie['title']}' 리뷰 쓰기")
            author = st.text_input("작성자", key="detail_author")
            content = st.text_area("리뷰 내용", key="detail_content")
            need_rerun = False
            if st.button("리뷰 등록", type="primary"):
                if author and content:
                    try:
                        rev_data = {
                            "movie_id": movie["id"],
                            "author": author,
                            "content": content,
                        }
                        res = requests.post(f"{API_URL}/reviews/", json=rev_data)
                        if res.status_code == 200:
                            st.toast("리뷰가 등록되었습니다!", icon="🍿")
                            fetch_movies.clear()
                            fetch_reviews.clear()
                            need_rerun = True
                    except Exception:
                        st.error("리뷰 등록 실패")
                else:
                    st.warning("작성자와 내용을 입력해주세요.")
            if need_rerun:
                st.rerun()

    # 갤러리 모드
    else:
        st.markdown(
            f"<h2 style='color:{MAIN_COLOR_BLUE};'>🍿 영화 목록</h2>",
            unsafe_allow_html=True,
        )
        if not movies:
            st.info("등록된 영화가 없습니다. 사이드바에서 영화를 추가해보세요.")
        else:
            cols_per_row = 3
            for i in range(0, len(movies), cols_per_row):
                cols = st.columns(cols_per_row)
                for j, movie in enumerate(movies[i : i + cols_per_row]):
                    with cols[j]:
                        st.image(movie["poster_url"], use_column_width=True)
                        st.markdown(f"**{movie['title']}**")
                        st.caption(f"⭐ {movie['average_rating']} / 5.0")
                        if st.button("자세히 보기", key=f"sel_{movie['id']}"):
                            st.session_state.selected_movie_id = movie["id"]
                            st.rerun()

# 5. 최근 리뷰 탭
with col_reviews:
    current_movie_id = st.session_state.selected_movie_id
    if current_movie_id is not None:
        selected_movie = next((m for m in movies if m["id"] == current_movie_id), None)
        review_title = (
            f"💬 '{selected_movie['title']}' 리뷰" if selected_movie else "💬 리뷰"
        )
    else:
        review_title = "💬 최근 리뷰 (Top 10)"

    st.markdown(
        f"<h2 style='color:{MAIN_COLOR_PINK};'>{review_title}</h2>",
        unsafe_allow_html=True,
    )

    LABEL_COLORS = {"positive": "#007BFF", "negative": "#FF4444"}

    def render_reviews(data, tab_key):
        if data.empty:
            st.info("리뷰가 없습니다.")
            return
        for _, row in data.iterrows():
            with st.chat_message("user"):
                st.write(f"**{row['author']}** ({row['날짜']})")
                st.write(row["content"])
                label = row["sentiment_label"]
                color = LABEL_COLORS.get(label, "#888888")
                rc1, rc2 = st.columns([3, 1])
                with rc1:
                    st.markdown(
                        f"분석 결과: <span style='color:{color}; font-weight:bold;'>{label.upper()}</span> ({row['감성점수(%)']}%)",
                        unsafe_allow_html=True,
                    )
                with rc2:
                    if st.button("🗑️", key=f"del_rev_{tab_key}_{row['id']}"):
                        try:
                            requests.delete(f"{API_URL}/reviews/{int(row['id'])}")
                            fetch_reviews.clear()
                            fetch_movies.clear()
                        except Exception:
                            pass
                        st.rerun()

    try:
        reviews = fetch_reviews(movie_id=current_movie_id)
        if not reviews:
            st.info("등록된 리뷰가 없습니다.")
        else:
            df = pd.DataFrame(reviews)
            df["날짜"] = df["created_at"].str[:10]
            df["감성점수(%)"] = (df["sentiment_score"] * 100).round(1)

            tab_all, tab_pos, tab_neg = st.tabs(["전체", "긍정 😊", "부정 😞"])
            with tab_all:
                render_reviews(df, "all")
            with tab_pos:
                render_reviews(df[df["sentiment_label"] == "positive"], "pos")
            with tab_neg:
                render_reviews(df[df["sentiment_label"] == "negative"], "neg")
    except Exception:
        pass

# Footer
st.divider()
st.markdown(
    f"<div style='text-align: center; color: grey;'> © 2026 팝콘 감성 측정소 - Built with Streamlit & FastAPI By Jarnfrid.Jang</div>",
    unsafe_allow_html=True,
)
