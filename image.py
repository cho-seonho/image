import streamlit as st
import requests
import os
import zipfile
from io import BytesIO

# 페이지 설정
st.set_page_config(page_title="이미지 수집기 Pro", page_icon="📸", layout="wide")

# UI 스타일 설정
st.markdown("""
    <style>
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

def on_ratio_change():
    """비율 선택 시 세션 상태의 해상도 값을 직접 수정"""
    target_ratio = st.session_state.orient_select
    if target_ratio == "가로형":
        st.session_state.width_input = 1920
        st.session_state.height_input = 1080
    elif target_ratio == "세로형":
        st.session_state.width_input = 1080
        st.session_state.height_input = 1920
    elif target_ratio == "정사각형":
        st.session_state.width_input = 1080
        st.session_state.height_input = 1080

st.title("📸 이미지 수집기 Pro")
st.write("PC와 스마트폰 어디서든 고화질 이미지를 수집하세요.")

# 입력 영역
with st.container():
    col1, col2 = st.columns([2, 1])
    with col1:
        query = st.text_input("🔍 어떤 이미지를 찾으시나요?", placeholder="예: 바다, 산, 고양이")
    with col2:
        # on_change를 통해 즉각 업데이트
        st.selectbox(
            "📐 이미지 비율", 
            ["가로형", "세로형", "정사각형"], 
            key="orient_select",
            on_change=on_ratio_change
        )
        orient_map = {"가로형": "landscape", "세로형": "portrait", "정사각형": "square"}
        orientation = orient_map[st.session_state.orient_select]

    with st.expander("⚙️ 고급 필터 (해상도 설정)", expanded=True):
        c1, c2, c3 = st.columns(3)
        # 중요: value를 쓰지 않고 key만 사용하여 세션 상태와 직접 결합합니다.
        min_w = c1.number_input("최소 가로 (px)", key="width_input")
        min_h = c2.number_input("최소 세로 (px)", key="height_input")
        count = c3.slider("사이트당 검색 개수", 10, 80, 20)

# 검색 실행
if st.button("사진 검색 및 분석 시작"):
    if not query:
        st.warning("검색어를 입력해주세요!")
    else:
        results = []
        with st.spinner(f"'{query}' 이미지 검색 중..."):
            # Pexels 검색
            try:
                p_url = f"https://api.pexels.com/v1/search?query={query}&per_page={count}&orientation={orientation}"
                p_res = requests.get(p_url, headers={"Authorization": PEXELS_API_KEY}, timeout=5).json()
                for img in p_res.get('photos', []):
                    if img['width'] >= min_w and img['height'] >= min_h:
                        results.append({'url': img['src']['large'], 'orig': img['src']['original'], 'source': 'Pexels'})
            except: pass

            # Pixabay 검색
            try:
                px_url = f"https://pixabay.com/api/?key={PIXABAY_API_KEY}&q={query}&image_type=photo&orientation={orientation}&safesearch=true&per_page={count}"
                px_res = requests.get(px_url, timeout=5).json()
                for img in px_res.get('hits', []):
                    if img['imageWidth'] >= min_w and img['imageHeight'] >= min_h:
                        results.append({'url': img['webformatURL'], 'orig': img['largeImageURL'], 'source': 'Pixabay'})
            except: pass

        if results:
            st.session_state['results'] = results
            st.success(f"총 {len(results)}개의 이미지를 찾았습니다!")
        else:
            st.info("조건에 맞는 사진이 없습니다.")

# 결과 출력
if 'results' in st.session_state:
    results = st.session_state['results']
    cols = st.columns(3)
    selected_images = []

    for idx, img in enumerate(results):
        with cols[idx % 3]:
            st.image(img['url'], use_container_width=True)
            if st.checkbox(f"선택 ({img['source']})", key=f"chk_{idx}"):
                selected_images.append(img)

    if selected_images:
        st.divider()
        if st.button(f"📥 선택한 {len(selected_images)}장 압축 다운로드"):
            zip_buffer = BytesIO()
            with zipfile.ZipFile(zip_buffer, "w") as zf:
                for i, img in enumerate(selected_images):
                    try:
                        res = requests.get(img['orig'], timeout=10)
                        zf.writestr(f"img_{i}.jpg", res.content)
                    except: continue
            
            st.download_button(
                label="📁 ZIP 파일 받기",
                data=zip_buffer.getvalue(),
                file_name=f"{query}_images.zip",
                mime="application/zip"
            )
