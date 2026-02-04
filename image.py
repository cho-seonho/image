import streamlit as st
import requests
import zipfile
from io import BytesIO
from datetime import datetime, timedelta, timezone

# 페이지 설정
st.set_page_config(page_title="이미지 수집기 Pro", page_icon="📸", layout="wide")

# --- CSS: 웹 상단 고정 및 파란색 선택 버튼 UI 유지 ---
st.markdown("""
    <style>
    /* 1. 상단 UI (PC 고정) */
    div[data-testid="stVerticalBlock"] > div:has(div.fixed-header) {
        position: sticky;
        top: 0;
        background-color: white;
        z-index: 999;
        padding: 10px 15px 15px 15px;
        box-shadow: 0 8px 20px rgba(0,0,0,0.1); 
        border-bottom: 1px solid #e1e4e8;
    }

    /* 모바일 대응: 스크롤을 위해 sticky 해제 */
    @media (max-width: 768px) {
        div[data-testid="stVerticalBlock"] > div:has(div.fixed-header) {
            position: relative !important;
            box-shadow: none !important;
            padding: 10px 5px;
        }
        /* 모바일에서만 버튼 가로 정렬 */
        div[data-testid="column"] {
            width: 48% !important;
            flex: 1 1 48% !important;
            min-width: 48% !important;
        }
    }

    /* 2. 이미지 카드 및 선택 효과 */
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

    /* 3. [UI 고정] 버튼 및 선택 체크박스 스타일 */
    .stButton > button {
        height: 45px !important;
        border-radius: 12px !important;
        font-weight: bold !important;
    }
    div[data-testid="stCheckbox"] {
        height: 45px !important;
        border-radius: 12px !important;
        border: 1px solid #dcdfe6;
        padding: 0 10px !important;
        display: flex;
        align-items: center;
        justify-content: center;
    }
    /* 파란색 선택 상태 고정 */
    div[data-testid="stCheckbox"]:has(input[aria-checked="true"]) {
        background-color: #2196F3 !important;
        border-color: #2196F3 !important;
    }
    div[data-testid="stCheckbox"]:has(input[aria-checked="true"]) label p {
        color: white !important;
        font-weight: bold !important;
    }

    .source-label { font-size: 0.85rem; color: #666; margin: 10px 0; font-weight: bold; }
    .stImage img { border-radius: 12px; }

    /* 다크모드 대응 */
    @media (prefers-color-scheme: dark) {
        div[data-testid="stVerticalBlock"] > div:has(div.fixed-header) { background-color: #0e1117; }
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

# --- 상단 UI (웹 버전 다운로드 버튼 포함) ---
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

    # 검색 버튼
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

    # [중요] 상단 UI 영역 내부의 다운로드 버튼 표시줄
    if st.session_state['results']:
        # 현재 선택된 이미지 리스트 미리 계산
        temp_selected = [img for idx, img in enumerate(st.session_state['results']) if st.session_state.get(f"chk_{idx}", False)]
        
        inf_col1, inf_col2 = st.columns([1, 1.5])
        inf_col1.markdown(f"📊 검색: **{len(st.session_state['results'])}**장")
        
        if temp_selected:
            zip_buffer = BytesIO()
            KST = timezone(timedelta(hours=9))
            now_str = datetime.now(KST).strftime("%Y%m%d_%H%M")
            with zipfile.ZipFile(zip_buffer, "w") as zf:
                for i, si in enumerate(temp_selected):
                    try:
                        res = requests.get(si['orig'], timeout=10)
                        zf.writestr(f"{query.replace(' ','_')}_{si['source'].lower()}_{i+1:02d}_{now_str}.jpg", res.content)
                    except: continue
            
            # 상단 UI에 다운로드 버튼 고정
            inf_col2.download_button(
                label=f"📥 {len(temp_selected)}장 다운로드",
                data=zip_buffer.getvalue(),
                file_name=f"{query}_{now_str}.zip",
                use_container_width=True,
                key="top_dl_btn"
            )
    st.markdown('</div>', unsafe_allow_html=True)

# --- 결과 출력 ---
if st.session_state['results']:
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
                # 선택 시 상단 다운로드 버튼이 즉시 갱신되도록 체크박스 배치
                st.checkbox("선택", key=f"chk_{idx}")
            st.markdown('</div>', unsafe_allow_html=True)
