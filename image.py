import streamlit as st
import requests
import zipfile
from io import BytesIO
from datetime import datetime, timedelta, timezone

# 페이지 설정
st.set_page_config(page_title="이미지 수집기 Pro", page_icon="📸", layout="wide")

# --- CSS: 모바일 버튼 가로 정렬 및 하단 다운로드 바 고정 ---
st.markdown("""
    <style>
    /* 1. 상단 UI (PC 고정, 모바일 해제) */
    div[data-testid="stVerticalBlock"] > div:has(div.fixed-header) {
        position: sticky;
        top: 0;
        background-color: white;
        z-index: 999;
        padding: 10px 15px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.1); 
        border-bottom: 1px solid #e1e4e8;
    }

    @media (max-width: 768px) {
        div[data-testid="stVerticalBlock"] > div:has(div.fixed-header) {
            position: relative !important;
            box-shadow: none !important;
            padding: 10px 5px;
        }
    }

    /* 2. 하단 다운로드 바 고정 (핵심 수정사항) */
    .download-bar {
        position: fixed;
        bottom: 0;
        left: 0;
        width: 100%;
        background-color: rgba(255, 255, 255, 0.95);
        padding: 15px;
        box-shadow: 0 -4px 15px rgba(0,0,0,0.1);
        z-index: 1000;
        display: flex;
        justify-content: center;
        align-items: center;
        gap: 20px;
    }

    /* 3. 이미지 카드 및 버튼 스타일 */
    .image-card-container {
        border: 1px solid #e1e4e8;
        border-radius: 20px;
        padding: 15px;
        margin-bottom: 20px;
        background-color: #ffffff;
    }

    /* 모바일에서 버튼 두 개가 한 줄에 나오도록 강제 설정 */
    [data-testid="column"] {
        width: 48% !important;
        flex: 1 1 48% !important;
        min-width: 48% !important;
    }

    .stButton > button, div[data-testid="stCheckbox"] {
        height: 45px !important;
        border-radius: 12px !important;
        font-weight: bold !important;
        width: 100% !important;
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
    }
    div[data-testid="stCheckbox"]:has(input[aria-checked="true"]) label p {
        color: white !important;
    }

    /* 다크모드 대응 */
    @media (prefers-color-scheme: dark) {
        div[data-testid="stVerticalBlock"] > div:has(div.fixed-header), .download-bar { 
            background-color: #0e1117; 
        }
        .image-card-container { background-color: #262730; border-color: #31333f; }
    }
    </style>
    """, unsafe_allow_html=True)

# --- 세션 초기화 ---
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

# --- 상단 UI ---
with st.container():
    st.markdown('<div class="fixed-header">', unsafe_allow_html=True)
    st.title("📸 이미지 수집기 Pro")
    
    col_search, col_ratio = st.columns([3, 1])
    query = col_search.text_input("검색어", placeholder="검색어를 입력하세요", label_visibility="collapsed")
    ratio_display = col_ratio.selectbox("비율", ["가로형", "세로형", "정사각형"], key="orient_select", on_change=on_ratio_change, label_visibility="collapsed")
    
    with st.expander("⚙️ 고급 필터 (해상도/개수)", expanded=True):
        f1, f2, f3 = st.columns(3)
        min_w = f1.number_input("가로(px)", key="width_input", min_value=0, value=1920)
        min_h = f2.number_input("세로(px)", key="height_input", min_value=0, value=1080)
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
    st.markdown('</div>', unsafe_allow_html=True)

# --- 결과 출력 ---
if st.session_state['results']:
    selected_images = []
    # 모바일에서 한 줄에 두 개 버튼이 깨지지 않게 3열 구조 유지
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
            
            # 버튼 가로 배치를 위한 컬럼 생성
            b_col1, b_col2 = st.columns(2)
            with b_col1:
                if st.button("🔍 보기", key=f"btn_{idx}"):
                    show_full_image(img['orig'], img['source'])
            with b_col2:
                if st.checkbox("선택", key=f"chk_{idx}"):
                    selected_images.append(img)
            st.markdown('</div>', unsafe_allow_html=True)

    # --- 하단 고정 다운로드 바 ---
    if selected_images:
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
        
        # 하단 바 구현
        st.markdown(f"""
            <div class="download-bar">
                <span style="font-weight:bold; color:#2196F3;">📍 {len(selected_images)}장 선택됨</span>
            </div>
        """, unsafe_allow_html=True)
        # 하단 바 위에 실제 클릭 가능한 버튼 배치 (Streamlit 제한상 바 위에 겹침)
        st.sidebar.markdown("---") # 사이드바는 모바일에서 숨겨지므로 사용 X
        
        # 실제 버튼은 스크롤 최하단에도 배치하여 편의성 제공
        st.download_button(
            label=f"📥 {len(selected_images)}장 최종 다운로드",
            data=zip_buffer.getvalue(),
            file_name=f"{query}_{now_str}.zip",
            use_container_width=True
        )
