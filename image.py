import streamlit as st
import requests
import zipfile
from io import BytesIO
from datetime import datetime, timedelta, timezone
import time

# 페이지 설정
st.set_page_config(page_title="이미지 수집기 Pro", page_icon="📸", layout="wide")

# --- CSS: 기존 UI 보존 및 사진 움직임 방지 ---
st.markdown("""
    <style>
    div[data-testid="stVerticalBlock"] > div:has(div.fixed-header) {
        position: sticky;
        top: 0;
        background-color: white;
        z-index: 999;
        padding: 10px 15px 15px 15px;
        box-shadow: 0 8px 20px rgba(0,0,0,0.1); 
        border-bottom: 1px solid #e1e4e8;
    }
    .image-card-container {
        border: 1px solid #e1e4e8;
        border-radius: 20px;
        padding: 15px;
        margin-bottom: 20px;
        background-color: #ffffff;
        overflow: hidden; 
    }
    .stImage { margin-bottom: 0px !important; }
    .selected-img img {
        filter: blur(5px) grayscale(40%);
        transition: filter 0.2s ease-in-out;
    }
    .stButton > button {
        height: 45px !important;
        border-radius: 12px !important;
        font-weight: bold !important;
        width: 100% !important;
    }
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
        transition: background-color 0.2s;
    }
    div[data-testid="stCheckbox"]:has(input[aria-checked="true"]) {
        background-color: #2196F3 !important;
        border-color: #2196F3 !important;
    }
    div[data-testid="stCheckbox"]:has(input[aria-checked="true"]) label p {
        color: white !important;
        font-weight: bold !important;
    }
    @media (max-width: 768px) {
        div[data-testid="stVerticalBlock"] > div:has(div.fixed-header) { position: relative !important; box-shadow: none !important; }
        div[data-testid="column"]:has(button[key^="btn_"]) { display: none !important; }
        div[data-testid="column"]:has(div[data-testid="stCheckbox"]) { width: 100% !important; flex: 1 1 100% !important; }
    }
    .source-label { font-size: 0.85rem; color: #666; margin: 10px 0; font-weight: bold; }
    .stImage img { border-radius: 12px; }
    </style>
    """, unsafe_allow_html=True)

if 'results' not in st.session_state: st.session_state['results'] = []
if 'all_selected' not in st.session_state: st.session_state['all_selected'] = False

def toggle_all():
    st.session_state.all_selected = not st.session_state.all_selected
    for idx in range(len(st.session_state['results'])):
        st.session_state[f"chk_{idx}"] = st.session_state.all_selected

@st.dialog("🔍 이미지 크게 보기", width="large")
def show_full_image(img_url, source):
    st.write(f"출처: **{source}**")
    st.image(img_url, use_container_width=True)

# --- 상단 UI ---
with st.container():
    st.markdown('<div class="fixed-header">', unsafe_allow_html=True)
    st.title("📸 이미지 수집기 Pro")
    
    c1, c2 = st.columns([3, 1])
    query = c1.text_input("검색어", placeholder="검색어를 입력하세요", label_visibility="collapsed")
    ratio = c2.selectbox("비율", ["가로형", "세로형", "정사각형"], key="orient_select", label_visibility="collapsed")
    
    with st.expander("⚙️ 고급 필터", expanded=False):
        f1, f2, f3 = st.columns(3)
        min_w = f1.number_input("가로(px)", value=1920)
        min_h = f2.number_input("세로(px)", value=1080)
        count = f3.slider("개수", 10, 80, 20)

    if st.button("📸 사진 검색 시작", use_container_width=True):
        if query:
            with st.spinner("이미지를 불러오는 중입니다..."):
                results = []
                try:
                    p_key, px_key = st.secrets["PEXELS_API_KEY"], st.secrets["PIXABAY_API_KEY"]
                    p_res = requests.get(f"https://api.pexels.com/v1/search?query={query}&per_page={count}", headers={"Authorization": p_key}).json()
                    for img in p_res.get('photos', []): results.append({'url': img['src']['large'], 'orig': img['src']['original'], 'source': 'Pexels'})
                    px_res = requests.get(f"https://pixabay.com/api/?key={px_key}&q={query}&per_page={count}").json()
                    for img in px_res.get('hits', []): results.append({'url': img['webformatURL'], 'orig': img['largeImageURL'], 'source': 'Pixabay'})
                except: pass
                st.session_state['results'] = results
                st.session_state.all_selected = False

    if st.session_state['results']:
        temp_sel = [img for idx, img in enumerate(st.session_state['results']) if st.session_state.get(f"chk_{idx}", False)]
        inf1, inf2, inf3 = st.columns([1, 1, 1.5])
        inf1.markdown(f"📊 검색: **{len(st.session_state['results'])}**장")
        inf2.button("✅ 전체 선택/해제", on_click=toggle_all, use_container_width=True)
        
        if temp_sel:
            KST = timezone(timedelta(hours=9))
            now_str = datetime.now(KST).strftime("%Y%m%d_%H%M")
            zip_buf = BytesIO()
            with zipfile.ZipFile(zip_buf, "w") as zf:
                for i, si in enumerate(temp_sel):
                    try:
                        # [파일명 복구] 출처_검색어_숫자_날짜_시간
                        file_name = f"{si['source']}_{query.replace(' ','_')}_{i+1:02d}_{now_str}.jpg"
                        zf.writestr(file_name, requests.get(si['orig']).content)
                    except: continue
            inf3.download_button(f"📥 {len(temp_sel)}장 다운로드", zip_buf.getvalue(), f"{query}_{now_str}.zip", use_container_width=True, key="top_dl")
    st.markdown('</div>', unsafe_allow_html=True)

# --- 결과 출력 ---
if st.session_state['results']:
    cols = st.columns(3)
    for idx, img in enumerate(st.session_state['results']):
        with cols[idx % 3]:
            st.markdown('<div class="image-card-container">', unsafe_allow_html=True)
            img_style = "selected-img" if st.session_state.get(f"chk_{idx}", False) else ""
            st.markdown(f'<div class="{img_style}">', unsafe_allow_html=True)
            st.image(img['url'], use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="source-label">📍 {img["source"]}</div>', unsafe_allow_html=True)
            b_col1, b_col2 = st.columns([1, 1])
            with b_col1:
                if st.button("🔍 보기", key=f"btn_{idx}"): show_full_image(img['orig'], img['source'])
            with b_col2:
                st.checkbox("선택", key=f"chk_{idx}")
            st.markdown('</div>', unsafe_allow_html=True)

    if temp_sel:
        st.markdown("---")
        st.download_button(f"📥 선택한 {len(temp_sel)}장 최종 다운로드", zip_buf.getvalue(), f"{query}_final_{now_str}.zip", use_container_width=True, key="btm_dl")
