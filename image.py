import streamlit as st
import requests
import zipfile
from io import BytesIO
from datetime import datetime, timedelta, timezone

# 페이지 설정
st.set_page_config(page_title="이미지 수집기 Pro", page_icon="📸", layout="wide")

# --- CSS: 모바일 스크롤 버그 해결을 위한 조건부 레이아웃 ---
st.markdown("""
    <style>
    /* 1. 기본 레이아웃 (PC 기준 고정) */
    .fixed-header-container {
        position: sticky;
        top: 0;
        background-color: white;
        z-index: 999;
        padding-bottom: 10px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.1); 
        border-bottom: 1px solid #e1e4e8;
    }

    /* 2. [핵심] 모바일 전용 대응 (화면 너비가 768px 이하일 때) */
    @media (max-width: 768px) {
        /* 고정 해제: 모바일에서 스크롤이 막히는 주범인 sticky를 제거 */
        div[data-testid="stVerticalBlock"] > div:has(div.fixed-header) {
            position: relative !important;
            top: auto !important;
            box-shadow: none !important;
            padding-bottom: 0px !important;
        }
        
        /* 모바일에서는 각 카드를 꽉 차게 표시 */
        .image-card-container {
            margin-bottom: 15px !important;
        }
    }

    /* 공통 스타일 유지 */
    .image-card-container {
        border: 1px solid #e1e4e8;
        border-radius: 20px;
        padding: 15px;
        margin-bottom: 20px;
        background-color: #ffffff;
    }

    .selected-img img {
        filter: blur(5px) grayscale(40%);
        transition: filter 0.3s ease;
    }

    .stButton > button, div[data-testid="stCheckbox"] {
        height: 45px !important;
        border-radius: 12px !important;
        font-weight: bold !important;
        margin-top: 0px !important;
    }

    div[data-testid="stCheckbox"] {
        border: 1px solid #dcdfe6;
        display: flex;
        align-items: center;
        justify-content: center;
    }
    
    div[data-testid="stCheckbox"]:has(input[aria-checked="true"]) {
        background-color: #2196F3 !important;
        border-color: #2196F3 !important;
        color: white !important;
    }

    .source-label { font-size: 0.85rem; color: #666; margin: 10px 0; font-weight: bold; }
    .stImage img { border-radius: 12px; }

    /* 다크모드 대응 */
    @media (prefers-color-scheme: dark) {
        .fixed-header-container { background-color: #0e1117; border-bottom-color: #31333f; }
        .image-card-container { background-color: #262730; border-color: #31333f; }
        div[data-testid="stCheckbox"] { border-color: #4b4b4b; }
    }
    </style>
    """, unsafe_allow_html=True)

# --- 세션 초기화 ---
if 'width_input' not in st.session_state: st.session_state['width_input'] = 1920
if 'height_input' not in st.session_state: st.session_state['height_input'] = 1080
if 'results' not in st.session_state: st.session_state['results'] = []

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

# --- 상단 UI (헤더) ---
# div.fixed-header 클래스를 사용해 CSS에서 직접 제어
st.markdown('<div class="fixed-header">', unsafe_allow_html=True)
st.title("📸 이미지 수집기 Pro")

col_search, col_ratio = st.columns([3, 1])
query = col_search.text_input("검색어", placeholder="검색어를 입력하세요", label_visibility="collapsed")
ratio_display = col_ratio.selectbox("비율", ["가로형", "세로형", "정사각형"], key="orient_select", on_change=on_ratio_change, label_visibility="collapsed")

with st.expander("⚙️ 고급 필터 (해상도/개수)", expanded=True):
    f1, f2, f3 = st.columns(3)
    min_w = f1.number_input("가로(px)", key="width_input", min_value=0)
    min_h = f2.number_input("세로(px)", key="height_input", min_value=0)
    count = f3.slider("개수", 10, 80, 20)

if st.button("📸 사진 검색 시작", use_container_width=True):
    if query:
        results = []
        try:
            p_key = st.secrets["PEXELS_API_KEY"]
            px_key = st.secrets["PIXABAY_API_KEY"]
            orient_map = {"가로형": "landscape", "세로형": "portrait", "정사각형": "square"}
            
            p_res = requests.get(f"https://api.pexels.com/v1/search?query={query}&per_page={count}&orientation={orient_map[ratio_display]}", headers={"Authorization": p_key}).json()
            for img in p_res.get('photos', []):
                if img['width'] >= min_w and img['height'] >= min_h:
                    results.append({'url': img['src']['large'], 'orig': img['src']['original'], 'source': 'Pexels'})
            
            px_res = requests.get(f"https://pixabay.com/api/?key={px_key}&q={query}&image_type=photo&orientation={orient_map[ratio_display]}&per_page={count}").json()
            for img in px_res.get('hits', []):
                if img['imageWidth'] >= min_w and img['imageHeight'] >= min_h:
                    results.append({'url': img['webformatURL'], 'orig': img['largeImageURL'], 'source': 'Pixabay'})
        except: pass
        st.session_state['results'] = results

if st.session_state['results']:
    inf1, inf2, inf3 = st.columns([1, 1, 1.5])
    inf1.write(f"📊 결과: **{len(st.session_state['results'])}**")
    sel_info = inf2.empty()
    dl_btn = inf3.empty()
st.markdown('</div>', unsafe_allow_html=True)

# --- 결과 출력 영역 ---
if st.session_state['results']:
    selected_images = []
    cols = st.columns(3)
    
    for idx, img in enumerate(st.session_state['results']):
        is_this_selected = st.session_state.get(f"chk_{idx}", False)
        
        with cols[idx % 3]:
            st.markdown('<div class="image-card-container">', unsafe_allow_html=True)
            img_class = "selected-img" if is_this_selected else ""
            st.markdown(f'<div class="{img_class}">', unsafe_allow_html=True)
            st.image(img['url'], use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="source-label">📍 {img["source"]}</div>', unsafe_allow_html=True)
            
            b_col1, b_col2 = st.columns(2)
            with b_col1:
                if st.button("🔍 보기", key=f"btn_{idx}"):
                    show_full_image(img['orig'], img['source'])
            with b_col2:
                if st.checkbox("선택", key=f"chk_{idx}"):
                    selected_images.append(img)
            st.markdown('</div>', unsafe_allow_html=True)

    if selected_images:
        sel_info.write(f"📍 **{len(selected_images)}**장")
        with dl_btn:
            zip_buffer = BytesIO()
            KST = timezone(timedelta(hours=9))
            now_str = datetime.now(KST).strftime("%Y%m%d_%H%M")
            
            with zipfile.ZipFile(zip_buffer, "w") as zf:
                for i, si in enumerate(selected_images):
                    try:
                        res = requests.get(si['orig'], timeout=10)
                        clean_query = query.replace(" ", "_")
                        file_name = f"{clean_query}_{si['source'].lower()}_{i+1:02d}_{now_str}.jpg"
                        zf.writestr(file_name, res.content)
                    except: continue
            st.download_button(f"📥 다운로드", data=zip_buffer.getvalue(), file_name=f"{query}_{now_str}.zip", use_container_width=True)
