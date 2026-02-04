import streamlit as st
import requests
import zipfile
from io import BytesIO

# 페이지 설정
st.set_page_config(page_title="이미지 수집기 Pro", page_icon="📸", layout="wide")

# --- CSS: 문제 요소(파란 테두리) 저격 및 레이아웃 완벽 정렬 ---
st.markdown("""
    <style>
    /* 1. 상단에 나타나는 파란색 빈 박스/포커스 테두리 강제 제거 */
    div[data-testid="stMarkdownContainer"] > p:empty,
    div[data-testid="stVerticalBlock"] > div:empty {
        display: none !important;
    }
    .stSelectbox div[data-baseweb="select"] {
        border: 1px solid #dcdfe6 !important;
    }
    *:focus {
        outline: none !important;
        box-shadow: none !important;
    }

    /* 2. 카드 통합 박스 디자인 */
    .image-card {
        background-color: #ffffff;
        border-radius: 12px;
        border: 1px solid #e1e4e8;
        padding: 15px;
        margin-bottom: 20px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.05);
    }
    
    /* 선택 시 카드 강조 */
    .selected-card {
        border: 2px solid #2196F3 !important;
        background-color: #f0f7ff !important;
    }

    /* 3. 버튼 및 체크박스 줄 맞춤 (높이와 간격 일치) */
    .button-row {
        display: flex;
        gap: 10px;
        align-items: stretch;
        margin-top: 10px;
    }
    
    .stButton > button {
        height: 45px !important;
        width: 100% !important;
        border-radius: 8px !important;
        margin: 0 !important;
    }

    div[data-testid="stCheckbox"] {
        height: 45px !important;
        width: 100% !important;
        background-color: white;
        border: 1px solid #dcdfe6;
        border-radius: 8px;
        display: flex;
        align-items: center;
        padding: 0 10px !important;
        margin: 0 !important;
    }

    /* 클릭 시 눌리는 애니메이션 */
    .stButton button:active, div[data-testid="stCheckbox"]:active {
        transform: translateY(2px);
        transition: 0.1s;
    }

    .source-label {
        font-size: 0.85rem;
        color: #777;
        margin: 8px 0;
        font-weight: bold;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 세션 및 초기값 설정 (0 방지) ---
if 'width_input' not in st.session_state: st.session_state['width_input'] = 1920
if 'height_input' not in st.session_state: st.session_state['height_input'] = 1080
if 'results' not in st.session_state: st.session_state['results'] = []
if 'search_clicked' not in st.session_state: st.session_state['search_clicked'] = False

# API 키 (Secrets)
try:
    PEXELS_API_KEY = st.secrets["PEXELS_API_KEY"]
    PIXABAY_API_KEY = st.secrets["PIXABAY_API_KEY"]
except:
    st.error("⚠️ API 키가 설정되지 않았습니다.")
    st.stop()

def on_ratio_change():
    ratio = st.session_state.orient_select
    if ratio == "가로형":
        st.session_state.width_input, st.session_state.height_input = 1920, 1080
    elif ratio == "세로형":
        st.session_state.width_input, st.session_state.height_input = 1080, 1920
    else:
        st.session_state.width_input, st.session_state.height_input = 1080, 1080

@st.dialog("🔍 이미지 크게 보기", width="large")
def show_full_image(img_url, source):
    st.write(f"출처: **{source}**")
    st.image(img_url, use_container_width=True)

# --- 상단 레이아웃 ---
st.title("📸 이미지 수집기 Pro")
st.write("PC와 스마트폰 어디서든 고화질 이미지를 수집하세요.")

with st.container():
    col_search, col_ratio = st.columns([3, 1])
    query = col_search.text_input("🔍 검색어", placeholder="예: 바다, 산, 고양이", label_visibility="collapsed")
    ratio_display = col_ratio.selectbox("📐 비율", ["가로형", "세로형", "정사각형"], key="orient_select", on_change=on_ratio_change, label_visibility="collapsed")
    
    with st.expander("⚙️ 고급 필터 (해상도 설정)"):
        f1, f2, f3 = st.columns(3)
        min_w = f1.number_input("최소 가로 (px)", key="width_input", step=10)
        min_h = f2.number_input("최소 세로 (px)", key="height_input", step=10)
        count = f3.slider("사이트당 검색 개수", 10, 80, 20)

    # 검색 버튼 스타일 복구
    if st.button("✅ 분석 완료 (다시 검색)" if st.session_state.search_clicked else "사진 검색 및 분석 시작"):
        if query:
            st.session_state.search_clicked = True
            results = []
            orient_map = {"가로형": "landscape", "세로형": "portrait", "정사각형": "square"}
            try:
                # API 호출 로직 생략 (기본 로직 유지)
                p_res = requests.get(f"https://api.pexels.com/v1/search?query={query}&per_page={count}&orientation={orient_map[ratio_display]}", 
                                     headers={"Authorization": PEXELS_API_KEY}).json()
                for img in p_res.get('photos', []):
                    if img['width'] >= min_w and img['height'] >= min_h:
                        results.append({'url': img['src']['large'], 'orig': img['src']['original'], 'source': 'Pexels'})
                
                px_res = requests.get(f"https://pixabay.com/api/?key={PIXABAY_API_KEY}&q={query}&image_type=photo&orientation={orient_map[ratio_display]}&per_page={count}").json()
                for img in px_res.get('hits', []):
                    if img['imageWidth'] >= min_w and img['imageHeight'] >= min_h:
                        results.append({'url': img['webformatURL'], 'orig': img['largeImageURL'], 'source': 'Pixabay'})
            except: pass
            st.session_state['results'] = results
            st.rerun()

# --- 결과 출력 영역 ---
if st.session_state.search_clicked:
    st.write(f"📊 결과: {len(st.session_state['results'])}장")
    selected_images = []
    cols = st.columns(3)
    
    for idx, img in enumerate(st.session_state['results']):
        is_selected = st.session_state.get(f"chk_{idx}", False)
        card_class = "image-card selected-card" if is_selected else "image-card"
        
        with cols[idx % 3]:
            # 하나의 박스로 완벽 통합
            st.markdown(f'<div class="{card_class}">', unsafe_allow_html=True)
            st.image(img['url'], use_container_width=True)
            st.markdown(f'<div class="source-label">📍 출처: {img["source"]}</div>', unsafe_allow_html=True)
            
            # 버튼과 체크박스를 가로로 정렬
            b_col1, b_col2 = st.columns(2)
            with b_col1:
                if st.button("🔍 보기", key=f"btn_{idx}"):
                    show_full_image(img['orig'], img['source'])
            with b_col2:
                if st.checkbox("선택", key=f"chk_{idx}"):
                    selected_images.append(img)
            st.markdown('</div>', unsafe_allow_html=True)
