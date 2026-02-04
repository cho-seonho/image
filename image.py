import streamlit as st
import requests
import zipfile
from io import BytesIO

# 페이지 설정
st.set_page_config(page_title="이미지 수집기 Pro", page_icon="📸", layout="wide")

# CSS: 타원형 제거 및 박스 내부 완전 통합
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
    
    /* 카드 전체 박스 스타일 */
    .image-card {
        background-color: #ffffff;
        border-radius: 12px;
        border: 2px solid #f0f2f6;
        padding: 12px;
        margin-bottom: 20px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.02);
        transition: all 0.2s ease;
    }

    /* 선택 시 카드 색상 변화 */
    .selected-card {
        border-color: #2196F3 !important;
        background-color: #f0f7ff !important;
    }

    /* 박스 내부 하단 정보 영역 */
    .info-container {
        margin-top: 12px;
        padding-top: 10px;
        border-top: 1px solid #eee;
    }

    /* 출처 텍스트 스타일 (상단 타원형 대신 텍스트로 깔끔하게) */
    .source-text {
        font-size: 0.85rem;
        color: #666;
        font-weight: bold;
        margin-bottom: 8px;
    }

    /* 클릭 시 눌리는 효과 */
    .stButton button:active, 
    div[data-testid="stCheckbox"]:active {
        transform: scale(0.95);
        transition: 0.1s;
    }

    .stImage img { border-radius: 8px; }
    .stButton>button { border-radius: 8px; font-weight: bold; width: 100%; height: 40px; }
    .stDownloadButton>button { background-color: #2196F3; color: white; border-radius: 8px; width: 100%; }

    /* 체크박스 디자인 최적화 */
    div[data-testid="stCheckbox"] {
        background: #f9f9f9;
        border: 1px solid #ddd;
        padding: 5px 10px;
        border-radius: 8px;
        width: 100%;
        height: 40px;
        display: flex;
        align-items: center;
    }
    </style>
    """, unsafe_allow_html=True)

# API 키 및 세션 초기화 (기본값 0 방지 포함)
try:
    PEXELS_API_KEY = st.secrets["PEXELS_API_KEY"]
    PIXABAY_API_KEY = st.secrets["PIXABAY_API_KEY"]
except:
    st.error("⚠️ API 키 설정 필요")
    st.stop()

if 'width_input' not in st.session_state: st.session_state['width_input'] = 1920
if 'height_input' not in st.session_state: st.session_state['height_input'] = 1080
if 'results' not in st.session_state: st.session_state['results'] = []
if 'search_clicked' not in st.session_state: st.session_state['search_clicked'] = False

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

# --- 상단 UI ---
with st.container():
    st.markdown('<div class="fixed-header">', unsafe_allow_html=True)
    st.title("📸 이미지 수집기 Pro")
    
    col_search, col_ratio = st.columns([3, 1])
    query = col_search.text_input("🔍 검색어", placeholder="검색어를 입력하세요", label_visibility="collapsed")
    ratio_display = col_ratio.selectbox("📐 비율", ["가로형", "세로형", "정사각형"], key="orient_select", on_change=on_ratio_change, label_visibility="collapsed")
    
    with st.expander("⚙️ 고급 필터 (해상도/개수)"):
        f1, f2, f3 = st.columns(3)
        min_w = f1.number_input("가로(px)", key="width_input", min_value=0, step=10)
        min_h = f2.number_input("세로(px)", key="height_input", min_value=0, step=10)
        count = f3.slider("개수", 10, 80, 20)

    if st.button("✅ 검색 완료 (다시 검색)" if st.session_state.search_clicked else "📸 사진 검색 시작"):
        if query:
            st.session_state.search_clicked = True
            results = []
            orient_map = {"가로형": "landscape", "세로형": "portrait", "정사각형": "square"}
            try:
                # Pexels & Pixabay 검색 로직
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

    if st.session_state.search_clicked:
        inf1, inf2, inf3 = st.columns([1, 1, 1.5])
        inf1.write(f"📊 검색: **{len(st.session_state['results'])}**장")
        select_placeholder = inf2.empty()
        download_placeholder = inf3.empty()
    st.markdown('</div>', unsafe_allow_html=True)

# --- 이미지 결과 영역 (박스 완전 통합) ---
if st.session_state['results']:
    selected_images = []
    cols = st.columns(3)
    
    for idx, img in enumerate(st.session_state['results']):
        is_selected = st.session_state.get(f"chk_{idx}", False)
        card_class = "image-card selected-card" if is_selected else "image-card"
        
        with cols[idx % 3]:
            # 하나의 박스로 시작
            st.markdown(f'<div class="{card_class}">', unsafe_allow_html=True)
            
            # 1. 사진
            st.image(img['url'], use_container_width=True)
            
            # 2. 하단 정보 통합 영역 (출처 + 보기 + 선택)
            st.markdown(f'''
                <div class="info-container">
                    <div class="source-text">📍 출처: {img["source"]}</div>
                </div>
            ''', unsafe_allow_html=True)
            
            b_col1, b_col2 = st.columns(2)
            with b_col1:
                if st.button("🔍 보기", key=f"exp_{idx}"):
                    show_full_image(img['orig'], img['source'])
            with b_col2:
                if st.checkbox("선택", key=f"chk_{idx}"):
                    selected_images.append(img)
            
            st.markdown('</div>', unsafe_allow_html=True)
    
    # 다운로드 로직
    if selected_images:
        select_placeholder.write(f"📍 **{len(selected_images)}**장 선택됨")
        with download_placeholder:
            zip_buffer = BytesIO()
            with zipfile.ZipFile(zip_buffer, "w") as zf:
                for i, si in enumerate(selected_images):
                    try:
                        res = requests.get(si['orig'], timeout=10)
                        zf.writestr(f"{i+1:02d}_{si['source']}.jpg", res.content)
                    except: continue
            st.download_button(f"📥 {len(selected_images)}장 다운로드", data=zip_buffer.getvalue(), file_name=f"{query}_수집.zip")
