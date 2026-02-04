import streamlit as st
import requests
import zipfile
from io import BytesIO

# 페이지 설정
st.set_page_config(page_title="이미지 수집기 Pro", page_icon="📸", layout="wide")

# --- CSS: 버튼 칼정렬 및 선택 시 이미지 블러 효과 ---
st.markdown("""
    <style>
    /* 1. 상단 고정 레이아웃 */
    div[data-testid="stVerticalBlock"] > div:has(div.fixed-header) {
        position: sticky;
        top: 2.8rem;
        background-color: white;
        z-index: 999;
        padding-top: 10px;
        border-bottom: 2px solid #f0f2f6;
    }

    /* 2. 일체형 둥근 카드 박스 */
    .image-card-container {
        border: 1px solid #e1e4e8;
        border-radius: 20px;
        padding: 15px;
        margin-bottom: 20px;
        background-color: #ffffff;
        display: flex;
        flex-direction: column;
    }

    /* 3. [핵심] 이미지 블러 효과 - 선택 시 흐려짐 */
    .selected-img img {
        filter: blur(4px) grayscale(30%);
        transition: filter 0.3s ease;
    }

    /* 4. 보기/선택 버튼 높이 칼정렬 (45px 고정) */
    .stButton > button {
        height: 45px !important;
        border-radius: 12px !important;
        font-weight: bold !important;
        width: 100% !important;
        margin: 0 !important;
    }

    div[data-testid="stCheckbox"] {
        height: 45px !important;
        border-radius: 12px;
        border: 1px solid #dcdfe6;
        padding: 0 10px !important;
        width: 100% !important;
        display: flex;
        align-items: center;
        justify-content: center;
        margin-top: 0px !important; /* 위쪽 여백 제거로 버튼과 라인 맞춤 */
    }
    
    /* 선택 시 체크박스 배경 파란색으로 변경 */
    div[data-testid="stCheckbox"]:has(input[aria-checked="true"]) {
        background-color: #2196F3 !important;
        border-color: #2196F3 !important;
        color: white !important;
    }
    div[data-testid="stCheckbox"]:has(input[aria-checked="true"]) label {
        color: white !important;
    }

    .source-label { font-size: 0.85rem; color: #666; margin: 10px 0; font-weight: bold; }
    .stImage img { border-radius: 12px; }
    </style>
    """, unsafe_allow_html=True)

# --- 세션 초기화 ---
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
    query = col_search.text_input("검색어", placeholder="검색어를 입력하세요", label_visibility="collapsed")
    ratio_display = col_ratio.selectbox("비율", ["가로형", "세로형", "정사각형"], key="orient_select", on_change=on_ratio_change, label_visibility="collapsed")
    
    with st.expander("⚙️ 고급 필터 (해상도/개수)", expanded=True):
        f1, f2, f3 = st.columns(3)
        min_w = f1.number_input("가로(px)", key="width_input", min_value=0)
        min_h = f2.number_input("세로(px)", key="height_input", min_value=0)
        count = f3.slider("개수", 10, 80, 20)

    if st.button("📸 사진 검색 시작", use_container_width=True):
        if query:
            st.session_state.search_clicked = True
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
            st.rerun()

    if st.session_state.search_clicked:
        inf1, inf2, inf3 = st.columns([1, 1, 1.5])
        inf1.write(f"📊 결과: **{len(st.session_state['results'])}**장")
        sel_info = inf2.empty()
        dl_btn = inf3.empty()
    st.markdown('</div>', unsafe_allow_html=True)

# --- 결과 출력 ---
if st.session_state['results']:
    selected_images = []
    cols = st.columns(3)
    
    for idx, img in enumerate(st.session_state['results']):
        is_this_selected = st.session_state.get(f"chk_{idx}", False)
        
        with cols[idx % 3]:
            st.markdown('<div class="image-card-container">', unsafe_allow_html=True)
            
            # 선택 여부에 따라 'selected-img' 클래스 부여 (블러 처리용)
            img_class = "selected-img" if is_this_selected else ""
            st.markdown(f'<div class="{img_class}">', unsafe_allow_html=True)
            st.image(img['url'], use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)
            
            st.markdown(f'<div class="source-label">📍 {img["source"]}</div>', unsafe_allow_html=True)
            
            # 버튼 영역 (수평 정렬)
            b_col1, b_col2 = st.columns(2)
            with b_col1:
                if st.button("🔍 보기", key=f"btn_{idx}"):
                    show_full_image(img['orig'], img['source'])
            with b_col2:
                if st.checkbox("선택하기", key=f"chk_{idx}"):
                    selected_images.append(img)
            st.markdown('</div>', unsafe_allow_html=True)

    if selected_images:
        sel_info.write(f"📍 **{len(selected_images)}**장 선택됨")
        with dl_btn:
            zip_buffer = BytesIO()
            with zipfile.ZipFile(zip_buffer, "w") as zf:
                for i, si in enumerate(selected_images):
                    try:
                        res = requests.get(si['orig'], timeout=10)
                        zf.writestr(f"img_{i+1}.jpg", res.content)
                    except: continue
            st.download_button(f"📥 {len(selected_images)}장 다운로드", data=zip_buffer.getvalue(), file_name="images.zip")
