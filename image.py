import streamlit as st
import requests
import os
import zipfile
from io import BytesIO

# 페이지 설정
st.set_page_config(page_title="이미지 수집기 Pro", page_icon="📸", layout="wide")

# CSS: 상단 UI 고정 및 스타일 설정
st.markdown("""
    <style>
    /* 상단 입력창 영역 고정 */
    [data-testid="stVerticalBlock"] > div:has(div.stHeaderContainer) {
        position: sticky;
        top: 0;
        background-color: white;
        z-index: 999;
        padding-bottom: 10px;
        border-bottom: 1px solid #f0f2f6;
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
    st.error("⚠️ API 키가 설정되지 않았습니다. Streamlit Secrets를 확인해주세요.")
    st.stop()

# --- 세션 상태 초기화 및 해상도 업데이트 로직 ---
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
    elif target_ratio in ["세로형", "정사각형"]:
        st.session_state.width_input, st.session_state.height_input = 1080, 1920 if target_ratio == "세로형" else 1080

# --- 상단 고정 UI 영역 ---
header_container = st.container()
with header_container:
    st.title("📸 이미지 수집기 Pro")
    
    col1, col2 = st.columns([2, 1])
    with col1:
        query = st.text_input("🔍 어떤 이미지를 찾으시나요?", placeholder="예: 바다, 산, 고양이")
    with col2:
        st.selectbox("📐 이미지 비율", ["가로형", "세로형", "정사각형"], key="orient_select", on_change=on_ratio_change)
        orient_map = {"가로형": "landscape", "세로형": "portrait", "정사각형": "square"}
        orientation = orient_map[st.session_state.orient_select]

    with st.expander("⚙️ 고급 필터 (해상도 설정)", expanded=False):
        c1, c2, c3 = st.columns(3)
        min_w = c1.number_input("최소 가로 (px)", key="width_input", step=1, format="%d")
        min_h = c2.number_input("최소 세로 (px)", key="height_input", step=1, format="%d")
        count = c3.slider("사이트당 검색 개수", 10, 80, 20)

    # 버튼 텍스트 변경 로직
    btn_label = "✅ 사진 검색 및 분석 완료" if st.session_state.search_clicked else "📸 사진 검색 및 분석 시작"
    search_btn = st.button(btn_label)

# 검색 실행 로직
if search_btn:
    if not query:
        st.warning("검색어를 입력해주세요!")
    else:
        st.session_state.search_clicked = True
        results = []
        with st.spinner(f"'{query}' 이미지 검색 중..."):
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
        st.rerun() # 버튼 이름 변경을 위해 페이지 즉시 갱신

# --- 결과 출력 및 선택 로직 ---
if 'results' in st.session_state:
    results = st.session_state['results']
    
    # 이미지 그리드
    cols = st.columns(3)
    selected_images = []
    for idx, img in enumerate(results):
        with cols[idx % 3]:
            st.image(img['url'], use_container_width=True)
            if st.checkbox(f"선택 ({img['source']})", key=f"chk_{idx}"):
                selected_images.append(img)

    # 하단 선택 정보 및 다운로드 버튼 (상단 UI에 붙여서 고정)
    with header_container:
        if selected_images:
            st.info(f"📍 현재 {len(selected_images)}개의 이미지가 선택되었습니다.")
            zip_buffer = BytesIO()
            if st.button(f"📥 선택한 {len(selected_images)}장 압축 준비"):
                with zipfile.ZipFile(zip_buffer, "w") as zf:
                    for i, img in enumerate(selected_images):
                        try:
                            res = requests.get(img['orig'], timeout=10)
                            zf.writestr(f"img_{i}_{img['source']}.jpg", res.content)
                        except: continue
                st.download_button(
                    label="📁 ZIP 파일 최종 다운로드",
                    data=zip_buffer.getvalue(),
                    file_name=f"{query}_images.zip",
                    mime="application/zip"
                )
        elif st.session_state.search_clicked:
            st.write(f"검색 결과: {len(results)}장")
