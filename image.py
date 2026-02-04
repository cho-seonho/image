import streamlit as st
import requests
import zipfile
from io import BytesIO
from datetime import datetime, timedelta, timezone
import time

# 페이지 설정
st.set_page_config(page_title="이미지 수집기 Pro", page_icon="📸", layout="wide")

# --- CSS: 높이 강제 고정 및 레이아웃 정렬 ---
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

    /* 2. [핵심] 모든 버튼과 체크박스 높이/정렬 통일 (틀어짐 방지) */
    .stButton > button, div[data-testid="stCheckbox"] {
        height: 45px !important;
        min-height: 45px !important;
        max-height: 45px !important;
        margin-top: 0px !important;
        margin-bottom: 0px !important;
        border-radius: 12px !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
    }

    /* 3. 모바일에서만 특정 요소 숨기기 (최후의 수단) */
    @media (max-width: 768px) {
        div[data-testid="stVerticalBlock"] > div:has(div.fixed-header) {
            position: relative !important;
            box-shadow: none !important;
        }
        /* 보기 버튼이 포함된 컬럼 자체를 모바일에서 숨김 */
        div[data-testid="column"]:has(button[key^="btn_"]) {
            display: none !important;
        }
        /* 선택 버튼 컬럼을 100%로 */
        div[data-testid="column"]:has(div[data-testid="stCheckbox"]) {
            width: 100% !important;
            flex: 1 1 100% !important;
        }
    }

    /* 4. 이미지 카드 스타일 */
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

    /* 5. 파란색 선택 UI 고정 */
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
    </style>
    """, unsafe_allow_html=True)

# --- 세션 초기화 ---
if 'results' not in st.session_state: st.session_state['results'] = []
if 'all_selected' not in st.session_state: st.session_state['all_selected'] = False

def toggle_all():
    msg_text = "처리 중..."
    with st.spinner(msg_text):
        st.session_state.all_selected = not st.session_state.all_selected
        for idx in range(len(st.session_state['results'])):
            st.session_state[f"chk_{idx}"] = st.session_state.all_selected
        time.sleep(0.3)

@st.dialog("🔍 이미지 크게 보기", width="large")
def show_full_image(img_url, source):
    st.write(f"출처: **{source}**")
    st.image(img_url, use_container_width=True)

# --- 상단 UI (웹 다운로드 버튼 고정) ---
with st.container():
    st.markdown('<div class="fixed-header">', unsafe_allow_html=True)
    st.title("📸 이미지 수집기 Pro")
    
    c1, c2 = st.columns([3, 1])
    query = c1.text_input("검색어", placeholder="검색어를 입력하세요", label_visibility="collapsed")
    ratio_display = c2.selectbox("비율", ["가로형", "세로형", "정사각형"], key="orient_select", label_visibility="collapsed")
    
    with st.expander("⚙️ 고급 필터", expanded=False):
        f1, f2, f3 = st.columns(3)
        min_w = f1.number_input("가로(px)", value=1920)
        min_h = f2.number_input("세로(px)", value=1080)
        count = f3.slider("개수", 10, 80, 20)

    if st.button("📸 사진 검색 시작", use_container_width=True):
        if query:
            with st.spinner("검색 중..."):
                results = []
                try:
                    p_key, px_key = st.secrets["PEXELS_API_KEY"], st.secrets["PIXABAY_API_KEY"]
                    # (검색 로직 생략 없이 그대로 유지)
                    p_res = requests.get(f"https://api.pexels.com/v1/search?query={query}&per_page={count}", headers={"Authorization": p_key}).json()
                    for img in p_res.get('photos', []): results.append({'url': img['src']['large'], 'orig': img['src']['original'], 'source': 'Pexels'})
                    px_res = requests.get(f"https://pixabay.com/api/?key={px_key}&q={query}&per_page={count}").json()
                    for img in px_res.get('hits', []): results.append({'url': img['webformatURL'], 'orig': img['largeImageURL'], 'source': 'Pixabay'})
                except: pass
                st.session_state['results'] = results
                st.session_state.all_selected = False

    # 상단 다운로드 버튼 영역
    if st.session_state['results']:
        temp_sel = [img for idx, img in enumerate(st.session_state['results']) if st.session_state.get(f"chk_{idx}", False)]
        inf1, inf2, inf3 = st.columns([1, 1, 1.5])
        inf1.markdown(f"📊 검색: **{len(st.session_state['results'])}**장")
        inf2.button("✅ 전체 선택/해제", on_click=toggle_all, use_container_width=True)
        if temp_sel:
            zip_buffer = BytesIO()
            with zipfile.ZipFile(zip_buffer, "w") as zf:
                for i, si in enumerate(temp_sel):
                    try: zf.writestr(f"img_{i}.jpg", requests.get(si['orig']).content)
                    except: continue
            inf3.download_button(f"📥 {len(temp_sel)}장 다운로드", zip_buffer.getvalue(), f"images.zip", use_container_width=True, key="top_dl")
    st.markdown('</div>', unsafe_allow_html=True)

# --- 결과 출력 ---
if st.session_state['results']:
    cols = st.columns(3)
    for idx, img in enumerate(st.session_state['results']):
        with cols[idx % 3]:
            st.markdown('<div class="image-card-container">', unsafe_allow_html=True)
            if st.session_state.get(f"chk_{idx}", False):
                st.markdown('<div class="selected-img">', unsafe_allow_html=True)
            st.image(img['url'], use_container_width=True)
            if st.session_state.get(f"chk_{idx}", False): st.markdown('</div>', unsafe_allow_html=True)
            
            st.markdown(f'<div class="source-label">📍 {img["source"]}</div>', unsafe_allow_html=True)
            
            # [수정된 버튼 영역] 
            # col1: 보기(웹 전용), col2: 선택(공통)
            b_col1, b_col2 = st.columns([1, 1])
            with b_col1:
                # 이 버튼은 CSS에 의해 모바일에서 컬럼 자체가 display:none 됨
                if st.button("🔍 보기", key=f"btn_{idx}"):
                    show_full_image(img['orig'], img['source'])
            with b_col2:
                # 이 체크박스는 모바일에서 부모 컬럼이 100%가 됨
                st.checkbox("선택", key=f"chk_{idx}")
            st.markdown('</div>', unsafe_allow_html=True)

    # 하단 다운로드 버튼
    temp_sel_btm = [img for idx, img in enumerate(st.session_state['results']) if st.session_state.get(f"chk_{idx}", False)]
    if temp_sel_btm:
        st.markdown("---")
        st.download_button(f"📥 선택한 {len(temp_sel_btm)}장 최종 다운로드", zip_buffer.getvalue(), "final_images.zip", use_container_width=True, key="btm_dl")
