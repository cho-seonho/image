import streamlit as st
import requests
import os
import zipfile
from io import BytesIO

# 페이지 설정
st.set_page_config(page_title="이미지 수집기 Pro", page_icon="📸", layout="wide")

# CSS: 상단 UI 강제 고정 (최신 스트림릿 전용)
st.markdown("""
    <style>
    /* 상단 메뉴(검색바) 영역 고정 */
    [data-testid="stHeader"] {
        background-color: rgba(255, 255, 255, 0.9);
        backdrop-filter: blur(10px);
    }
    
    /* 실제 입력폼이 들어가는 상단 컨테이너 고정 */
    .sticky-header {
        position: fixed;
        top: 3.5rem;
        left: 0;
        right: 0;
        background-color: white;
        z-index: 1000;
        padding: 1rem 5rem;
        border-bottom: 2px solid #f0f2f6;
    }

    /* 본문 콘텐츠가 상단 고정 바에 가려지지 않게 여백 추가 */
    .main-content {
        margin-top: 18rem;
    }

    .stButton>button { width: 100%; border-radius: 10px; height: 3em; font-weight: bold; }
    .stDownloadButton>button { width: 100%; background-color: #2196F3; color: white; }
    [data-testid="stImage"] { border-radius: 15px; border: 2px solid #f0f2f6; }
    </style>
    """, unsafe_allow_html=True)

# API 키 불러오기
try:
    PEXELS_API_KEY = st.secrets["PEXELS_API_KEY"]
    PIXABAY_API_KEY = st.secrets["PIXABAY_API_KEY"]
except:
    st.error("⚠️ API 키가 설정되지 않았습니다. Streamlit Cloud의 Secrets 설정을 확인해주세요.")
    st.stop()

# --- 세션 상태 초기화 ---
if 'width_input' not in st.session_state:
    st.session_state['width_input'] = 1920
if 'height_input' not in st.session_state:
    st.session_state['height_input'] = 1080
if 'search_clicked' not in st.session_state:
    st.session_state['search_clicked'] = False

def on_ratio_change():
    target_ratio = st.session_state.orient_select
    if target_ratio == "가로형":
        st.session_state.width_input, st.session_state.height_input = 1920, 1080
    elif target_ratio == "세로형":
        st.session_state.width_input, st.session_state.height_input = 1080, 1920
    elif target_ratio == "정사각형":
        st.session_state.width_input, st.session_state.height_input = 1080, 1080

# --- 상단 고정 UI 시작 ---
st.markdown('<div class="sticky-header">', unsafe_allow_html=True)
st.title("📸 이미지 수집기 Pro")

col1, col2 = st.columns([2, 1])
with col1:
    query = st.text_input("🔍 검색어", placeholder="예: 바다, 고양이", label_visibility="collapsed")
with col2:
    st.selectbox("📐 비율", ["가로형", "세로형", "정사각형"], key="orient_select", on_change=on_ratio_change, label_visibility="collapsed")
    orient_map = {"가로형": "landscape", "세로형": "portrait", "정사각형": "square"}
    orientation = orient_map[st.session_state.orient_select]

with st.expander("⚙️ 고급 필터 (해상도 설정)"):
    c1, c2, c3 = st.columns(3)
    min_w = c1.number_input("가로 (px)", key="width_input", step=1, format="%d")
    min_h = c2.number_input("세로 (px)", key="height_input", step=1, format="%d")
    count = c3.slider("개수", 10, 80, 20)

# 검색 버튼 및 선택 정보 영역
btn_col1, btn_col2 = st.columns([1, 1])
with btn_col1:
    btn_label = "✅ 분석 완료 (다시 검색)" if st.session_state.search_clicked else "📸 사진 검색 및 분석 시작"
    search_btn = st.button(btn_label)

# 선택 개수 및 다운로드 버튼 표시를 위한 placeholder
info_placeholder = st.empty()
st.markdown('</div>', unsafe_allow_html=True) # 상단 고정 끝
# --- 상단 고정 UI 끝 ---

# 본문 시작 여백
st.markdown('<div class="main-content">', unsafe_allow_html=True)

# 검색 실행 로직
if search_btn and query:
    st.session_state.search_clicked = True
    results = []
    with st.spinner("이미지 검색 중..."):
        try:
            p_url = f"https://api.pexels.com/v1/search?query={query}&per_page={count}&orientation={orientation}"
            p_res = requests.get(p_url, headers={"Authorization": PEXELS_API_KEY}, timeout=5).json()
            for img in p_res.get('photos', []):
                if img['width'] >= min_w and img['height'] >= min_h:
                    results.append({'url': img['src']['large'], 'orig': img['src']['original'], 'source': 'Pexels'})
        except: pass
        try:
            px_url = f"https://pixabay.com/api/?key={PIXABAY_API_KEY}&q={query}&image_type=photo&orientation={orientation}&safesearch=true&per_page={count}"
            px_res = requests.get(px_url, timeout=5).json()
            for img in px_res.get('hits', []):
                if img['imageWidth'] >= min_w and img['imageHeight'] >= min_h:
                    results.append({'url': img['webformatURL'], 'orig': img['largeImageURL'], 'source': 'Pixabay'})
        except: pass
    st.session_state['results'] = results
    st.rerun()

# 결과 표시
if 'results' in st.session_state:
    results = st.session_state['results']
    cols = st.columns(3)
    selected_images = []
    
    for idx, img in enumerate(results):
        with cols[idx % 3]:
            st.image(img['url'], use_container_width=True)
            if st.checkbox(f"선택 ({img['source']})", key=f"chk_{idx}"):
                selected_images.append(img)

    # 상단 고정 영역의 placeholder에 선택 정보 업데이트
    with info_placeholder:
        if selected_images:
            info_col1, info_col2 = st.columns([1, 1])
            info_col1.info(f"📍 {len(selected_images)}장 선택됨")
            if info_col2.button(f"📥 {len(selected_images)}장 ZIP 압축"):
                zip_buffer = BytesIO()
                with zipfile.ZipFile(zip_buffer, "w") as zf:
                    for i, img in enumerate(selected_images):
                        try:
                            res = requests.get(img['orig'], timeout=10)
                            zf.writestr(f"img_{i}.jpg", res.content)
                        except: continue
                st.download_button("📁 최종 다운로드", data=zip_buffer.getvalue(), file_name=f"{query}.zip", mime="application/zip")

st.markdown('</div>', unsafe_allow_html=True)
