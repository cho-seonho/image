import streamlit as st
import requests
import zipfile
from io import BytesIO

# 페이지 설정
st.set_page_config(page_title="이미지 수집기 Pro", page_icon="📸", layout="wide")

# CSS: 상단 고정, 이미지 클릭 효과, 모달창 스타일
st.markdown("""
    <style>
    /* 상단 UI 고정 */
    div[data-testid="stVerticalBlock"] > div:has(div.fixed-header) {
        position: sticky;
        top: 2.8rem;
        background-color: white;
        z-index: 999;
        padding-top: 10px;
        border-bottom: 2px solid #f0f2f6;
    }
    
    /* 이미지 마우스 오버 시 클릭 유도 효과 */
    .stImage img {
        transition: 0.3s;
        cursor: zoom-in;
    }
    .stImage img:hover {
        opacity: 0.8;
        transform: scale(1.02);
    }

    /* 버튼 스타일 */
    .stButton>button { width: 100%; border-radius: 10px; font-weight: bold; }
    .stDownloadButton>button { width: 100%; background-color: #2196F3; color: white; border-radius: 10px; }
    </style>
    """, unsafe_allow_html=True)

# API 키 불러오기
try:
    PEXELS_API_KEY = st.secrets["PEXELS_API_KEY"]
    PIXABAY_API_KEY = st.secrets["PIXABAY_API_KEY"]
except:
    st.error("⚠️ API 키가 설정되지 않았습니다. Streamlit Secrets를 확인해주세요.")
    st.stop()

# 세션 상태 초기화
if 'results' not in st.session_state: st.session_state['results'] = []
if 'search_clicked' not in st.session_state: st.session_state['search_clicked'] = False
if 'expanded_img' not in st.session_state: st.session_state['expanded_img'] = None

# 이미지 확대/축소 함수
def set_expanded_img(url): st.session_state.expanded_img = url
def close_expanded_img(): st.session_state.expanded_img = None

# 상단 고정 UI
with st.container():
    st.markdown('<div class="fixed-header">', unsafe_allow_html=True)
    st.title("📸 이미지 수집기 Pro")
    
    col_search, col_ratio = st.columns([3, 1])
    query = col_search.text_input("🔍 검색어", placeholder="예: 바다, 커피", label_visibility="collapsed")
    ratio = col_ratio.selectbox("📐 비율", ["가로형", "세로형", "정사각형"], label_visibility="collapsed")
    
    # 검색 버튼
    btn_label = "✅ 분석 완료 (다시 검색)" if st.session_state.search_clicked else "📸 사진 검색 및 분석 시작"
    if st.button(btn_label):
        if query:
            st.session_state.search_clicked = True
            results = []
            orient_map = {"가로형": "landscape", "세로형": "portrait", "정사각형": "square"}
            # API 호출 로직 (Pexels & Pixabay)
            try:
                p_res = requests.get(f"https://api.pexels.com/v1/search?query={query}&per_page=40&orientation={orient_map[ratio]}", 
                                     headers={"Authorization": PEXELS_API_KEY}).json()
                for img in p_res.get('photos', []):
                    results.append({'url': img['src']['large'], 'orig': img['src']['original'], 'source': 'Pexels'})
                px_res = requests.get(f"https://pixabay.com/api/?key={PIXABAY_API_KEY}&q={query}&image_type=photo&orientation={orient_map[ratio]}&per_page=40").json()
                for img in px_res.get('hits', []):
                    results.append({'url': img['webformatURL'], 'orig': img['largeImageURL'], 'source': 'Pixabay'})
            except: pass
            st.session_state['results'] = results
            st.rerun()

    # 정보 표시 및 다운로드 버튼 (선택됨 옆에 배치)
    if st.session_state.search_clicked:
        inf1, inf2, inf3 = st.columns([1, 1, 1.5])
        inf1.write(f"📊 검색: **{len(st.session_state['results'])}**장")
        select_placeholder = inf2.empty()
        download_placeholder = inf3.empty()
    st.markdown('</div>', unsafe_allow_html=True)

# 이미지 클릭 확대 모달 구현
if st.session_state.expanded_img:
    with st.container():
        st.markdown("---")
        m1, m2 = st.columns([9, 1])
        m1.subheader("🔍 이미지 크게 보기")
        if m2.button("❌ 닫기"): 
            close_expanded_img()
            st.rerun()
        st.image(st.session_state.expanded_img, use_container_width=True)
        if st.button("이미지 닫기 (원래대로)"): 
            close_expanded_img()
            st.rerun()
        st.markdown("---")

# 이미지 리스트 출력
if st.session_state['results']:
    selected_images = []
    cols = st.columns(3)
    
    for idx, img in enumerate(st.session_state['results']):
        with cols[idx % 3]:
            # 이미지 클릭 시 세션 상태 변경 (확대)
            st.image(img['url'], use_container_width=True)
            c1, c2 = st.columns([1, 1])
            if c1.button("🔍 크게보기", key=f"exp_{idx}"):
                set_expanded_img(img['orig'])
                st.rerun()
            if c2.checkbox(f"선택하기", key=f"chk_{idx}"):
                selected_images.append(img)
    
    # 선택 개수 및 다운로드 버튼 실시간 업데이트
    if selected_images:
        select_placeholder.write(f"📍 **{len(selected_images)}**장 선택됨")
        with download_placeholder:
            zip_buffer = BytesIO()
            with zipfile.ZipFile(zip_buffer, "w") as zf:
                for i, si in enumerate(selected_images):
                    try:
                        res = requests.get(si['orig'], timeout=10)
                        zf.writestr(f"img_{i}.jpg", res.content)
                    except: continue
            st.download_button(f"📥 {len(selected_images)}장 다운로드", data=zip_buffer.getvalue(), file_name=f"{query}.zip")
    else:
        select_placeholder.write("📍 0장 선택됨")
