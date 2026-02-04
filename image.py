import streamlit as st
import requests
import zipfile
from io import BytesIO
from datetime import datetime, timedelta, timezone
import time

# 페이지 설정
st.set_page_config(page_title="이미지 수집기 Pro", page_icon="📸", layout="wide")

# --- 기기 판별 로직 (모바일 여부 확인) ---
# 가로 너비가 768px 미만이면 모바일로 간주
is_mobile = False
if "viewport" in st.session_state and st.session_state.viewport.get("width", 1000) < 768:
    is_mobile = True

# --- CSS: 기존 파란색 버튼 스타일 복구 및 정렬 고정 ---
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

    /* 2. 웹 버전 버튼 스타일 복구 (파란색 박스) */
    .stButton > button {
        height: 45px !important;
        border-radius: 12px !important;
        font-weight: bold !important;
        width: 100% !important;
    }
    
    /* 체크박스를 버튼처럼 보이게 하는 핵심 스타일 (복구) */
    div[data-testid="stCheckbox"] {
        height: 45px !important;
        border-radius: 12px !important;
        border: 1px solid #dcdfe6;
        padding: 0 10px !important;
        display: flex;
        align-items: center;
        justify-content: center;
        margin-top: 0px !important;
        background-color: white;
    }
    
    /* 선택 시 파란색 배경으로 변경 (복구) */
    div[data-testid="stCheckbox"]:has(input[aria-checked="true"]) {
        background-color: #2196F3 !important;
        border-color: #2196F3 !important;
    }
    div[data-testid="stCheckbox"]:has(input[aria-checked="true"]) label p {
        color: white !important;
        font-weight: bold !important;
    }

    /* 3. 모바일 전용 레이아웃 보정 */
    @media (max-width: 768px) {
        div[data-testid="stVerticalBlock"] > div:has(div.fixed-header) {
            position: relative !important;
            box-shadow: none !important;
        }
    }

    /* 이미지 카드 스타일 */
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
    .source-label { font-size: 0.85rem; color: #666; margin: 10px 0; font-weight: bold; }
    .stImage img { border-radius: 12px; }
    </style>
    """, unsafe_allow_html=True)

# --- 세션 초기화 ---
if 'results' not in st.session_state: st.session_state['results'] = []
if 'all_selected' not in st.session_state: st.session_state['all_selected'] = False

def toggle_all():
    msg_text = "전체 선택 처리 중..."
    with st.spinner(msg_text):
        st.session_state.all_selected = not st.session_state.all_selected
        for idx in range(len(st.session_state['results'])):
            st.session_state[f"chk_{idx}"] = st.session_state.all_selected
        time.sleep(0.3)

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
    ratio_display = col_ratio.selectbox("비율", ["가로형", "세로형", "정사각형"], key="orient_select", label_visibility="collapsed")
    
    # 모바일은 필터 닫아두기
    with st.expander("⚙️ 고급 필터 (해상도/개수)", expanded=False):
        f1, f2, f3 = st.columns(3)
        min_w = f1.number_input("가로(px)", value=1920)
        min_h = f2.number_input("세로(px)", value=1080)
        count = f3.slider("개수", 10, 80, 20)

    if st.button("📸 사진 검색 시작", use_container_width=True):
        if query:
            with st.spinner("이미지를 불러오는 중입니다..."):
                results = []
                try:
                    p_key = st.secrets["PEXELS_API_KEY"]
                    px_key = st.secrets["PIXABAY_API_KEY"]
                    # 검색 API 호출 로직은 기존과 동일하게 유지
                    p_res = requests.get(f"https://api.pexels.com/v1/search?query={query}&per_page={count}", headers={"Authorization": p_key}).json()
                    for img in p_res.get('photos', []): results.append({'url': img['src']['large'], 'orig': img['src']['original'], 'source': 'Pexels'})
                    px_res = requests.get(f"https://pixabay.com/api/?key={px_key}&q={query}&per_page={count}").json()
                    for img in px_res.get('hits', []): results.append({'url': img['webformatURL'], 'orig': img['largeImageURL'], 'source': 'Pixabay'})
                except: pass
                st.session_state['results'] = results
                st.session_state.all_selected = False

    if st.session_state['results']:
        temp_selected = [img for idx, img in enumerate(st.session_state['results']) if st.session_state.get(f"chk_{idx}", False)]
        inf_col1, inf_col2, inf_col3 = st.columns([1, 1, 1.5])
        inf_col1.markdown(f"📊 검색: **{len(st.session_state['results'])}**장")
        inf_col2.button("✅ 전체 선택/해제", on_click=toggle_all, use_container_width=True)
        
        if temp_selected:
            zip_buffer = BytesIO()
            with zipfile.ZipFile(zip_buffer, "w") as zf:
                for i, si in enumerate(temp_selected):
                    try: zf.writestr(f"image_{i}.jpg", requests.get(si['orig']).content)
                    except: continue
            inf_col3.download_button(f"📥 {len(temp_selected)}장 다운로드", zip_buffer.getvalue(), "download.zip", use_container_width=True, key="top_dl_btn")
    st.markdown('</div>', unsafe_allow_html=True)

# --- 결과 출력 ---
if st.session_state['results']:
    # 메인 그리드 (웹 3열)
    cols = st.columns(3)
    for idx, img in enumerate(st.session_state['results']):
        with cols[idx % 3]:
            st.markdown('<div class="image-card-container">', unsafe_allow_html=True)
            if st.session_state.get(f"chk_{idx}", False):
                st.markdown('<div class="selected-img">', unsafe_allow_html=True)
            st.image(img['url'], use_container_width=True)
            if st.session_state.get(f"chk_{idx}", False): st.markdown('</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="source-label">📍 {img["source"]}</div>', unsafe_allow_html=True)
            
            # --- [수정] 모바일/웹 버튼 분기 ---
            # CSS display:none은 가끔 무시되므로, 컬럼 구조 자체를 다르게 짭니다.
            # PC 너비일 때는 2컬럼(보기, 선택), 모바일 너비일 때는 1컬럼(선택)
            
            # 꼼수: CSS 클래스명을 직접 주입하여 모바일에서 특정 컬럼만 날립니다.
            btn_container = st.columns([1, 1])
            
            with btn_container[0]:
                # 모바일 화면(768px 이하)에서 이 버튼이 포함된 <div>를 보이지 않게 처리
                st.markdown('<div class="mobile-view-hide" style="display: var(--mobile-hide, block);">', unsafe_allow_html=True)
                st.markdown("""<style>@media (max-width: 768px) {.mobile-view-hide {display: none !important;}}</style>""", unsafe_allow_html=True)
                if st.button("🔍 보기", key=f"btn_{idx}"):
                    show_full_image(img['orig'], img['source'])
                st.markdown('</div>', unsafe_allow_html=True)
                
            with btn_container[1]:
                # 모바일에서는 이 체크박스가 부모 너비를 다 쓰도록 설정
                st.markdown("""<style>@media (max-width: 768px) {div[data-testid="column"]:has(div.mobile-view-full) {width: 100% !important; flex: 1 1 100% !important;}}</style>""", unsafe_allow_html=True)
                st.markdown('<div class="mobile-view-full">', unsafe_allow_html=True)
                st.checkbox("선택", key=f"chk_{idx}")
                st.markdown('</div>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)

    # 하단 다운로드 버튼 (모바일 사용자를 위해 추가)
    if temp_selected:
        st.markdown("---")
        st.download_button(f"📥 선택한 {len(temp_selected)}장 최종 다운로드", zip_buffer.getvalue(), "final.zip", use_container_width=True, key="bottom_dl_btn")
