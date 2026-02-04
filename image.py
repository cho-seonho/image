import streamlit as st
import requests
import os
import zipfile
from io import BytesIO

# 페이지 설정
st.set_page_config(page_title="이미지 수집기 Pro", page_icon="📸", layout="wide")

# CSS: 상단 고정 및 카드 스타일 UI
st.markdown("""
    <style>
    /* 1. 상단 UI 고정 (Sticky Header) */
    div[data-testid="stVerticalBlock"] > div:has(div.fixed-header) {
        position: sticky;
        top: 2.8rem;
        background-color: white;
        z-index: 999;
        padding-top: 10px;
        border-bottom: 2px solid #f0f2f6;
    }
    
    /* 2. 이미지 카드 및 체크박스 스타일 */
    .img-container {
        position: relative;
        border-radius: 15px;
        overflow: hidden;
        margin-bottom: 20px;
    }
    .stCheckbox {
        background-color: rgba(255, 255, 255, 0.8);
        padding: 5px 10px;
        border-radius: 5px;
        margin-top: -10px; /* 사진에 바짝 붙임 */
    }

    .stButton>button { width: 100%; border-radius: 10px; height: 3em; font-weight: bold; }
    .stDownloadButton>button { width: 100%; background-color: #2196F3; color: white; }
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
if 'width_input' not in st.session_state: st.session_state['width_input'] = 1920
if 'height_input' not in st.session_state: st.session_state['height_input'] = 1080
if 'search_clicked' not in st.session_state: st.session_state['search_clicked'] = False
if 'results' not in st.session_state: st.session_state['results'] = []

def on_ratio_change():
    ratio = st.session_state.orient_select
    if ratio == "가로형":
        st.session_state.width_input, st.session_state.height_input = 1920, 1080
    elif ratio == "세로형":
        st.session_state.width_input, st.session_state.height_input = 1080, 1920
    else: # 정사각형
        st.session_state.width_input, st.session_state.height_input = 1080, 1080

# --- 상단 고정 UI (fixed-header 클래스 부여) ---
with st.container():
    st.markdown('<div class="fixed-header">', unsafe_allow_html=True)
    st.title("📸 이미지 수집기 Pro")
    
    c1, c2 = st.columns([3, 1])
    query = c1.text_input("🔍 검색어", placeholder="예: 바다, 산, 고양이", label_visibility="collapsed")
    ratio_display = c2.selectbox("📐 비율", ["가로형", "세로형", "정사각형"], key="orient_select", on_change=on_ratio_change, label_visibility="collapsed")
    
    with st.expander("⚙️ 고급 필터 (해상도/개수)"):
        f1, f2, f3 = st.columns(3)
        min_w = f1.number_input("가로(px)", key="width_input", step=1, format="%d")
        min_h = f2.number_input("세로(px)", key="height_input", step=1, format="%d")
        count = f3.slider("개수", 10, 80, 20)

    # 검색 버튼 및 상태 표시
    btn_label = "✅ 분석 완료 (다시 검색)" if st.session_state.search_clicked else "📸 사진 검색 및 분석 시작"
    if st.button(btn_label):
        if query:
            st.session_state.search_clicked = True
            results = []
            with st.spinner("이미지 검색 중..."):
                orient_map = {"가로형": "landscape", "세로형": "portrait", "정사각형": "square"}
                # Pexels
                try:
                    p_res = requests.get(f"https://api.pexels.com/v1/search?query={query}&per_page={count}&orientation={orient_map[ratio_display]}", 
                                         headers={"Authorization": PEXELS_API_KEY}).json()
                    for img in p_res.get('photos', []):
                        if img['width'] >= min_w and img['height'] >= min_h:
                            results.append({'url': img['src']['large'], 'orig': img['src']['original'], 'source': 'Pexels'})
                except: pass
                # Pixabay
                try:
                    px_res = requests.get(f"https://pixabay.com/api/?key={PIXABAY_API_KEY}&q={query}&image_type=photo&orientation={orient_map[ratio_display]}&per_page={count}").json()
                    for img in px_res.get('hits', []):
                        if img['imageWidth'] >= min_w and img['imageHeight'] >= min_h:
                            results.append({'url': img['webformatURL'], 'orig': img['largeImageURL'], 'source': 'Pixabay'})
                except: pass
            st.session_state['results'] = results
            st.rerun()

    # 검색 및 선택 정보 요약 (한 줄에 표시)
    if st.session_state.search_clicked:
        info_col1, info_col2 = st.columns([1, 1])
        info_col1.write(f"📊 검색 결과: **{len(st.session_state['results'])}**장")
        # 선택 개수는 아래 결과 루프에서 수집 후 placeholder로 표시하기 위해 임시 생성
        select_status = info_col2.empty()
    st.markdown('</div>', unsafe_allow_html=True)

# --- 이미지 결과 영역 ---
if st.session_state['results']:
    selected_images = []
    cols = st.columns(3)
    
    for idx, img in enumerate(st.session_state['results']):
        with cols[idx % 3]:
            # 체크박스를 사진 위로 바짝 붙여 표시
            st.image(img['url'], use_container_width=True)
            if st.checkbox(f"선택하기 ({img['source']})", key=f"chk_{idx}"):
                selected_images.append(img)
    
    # 상단 고정 영역에 선택 개수 업데이트 및 다운로드 버튼 생성
    if selected_images:
        select_status.write(f"📍 **{len(selected_images)}**장 선택됨")
        with st.container(): # 다운로드 버튼도 상단에 붙임
            zip_buffer = BytesIO()
            if st.button(f"📥 {len(selected_images)}장 ZIP 압축 후 다운로드"):
                with zipfile.ZipFile(zip_buffer, "w") as zf:
                    for i, si in enumerate(selected_images):
                        try:
                            res = requests.get(si['orig'], timeout=10)
                            zf.writestr(f"img_{i}.jpg", res.content)
                        except: continue
                st.download_button("📁 최종 파일 받기", data=zip_buffer.getvalue(), file_name=f"{query}.zip")
    elif st.session_state.search_clicked:
        select_status.write("📍 선택된 사진 없음")
