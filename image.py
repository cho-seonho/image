import streamlit as st
import requests
import zipfile
from io import BytesIO
from datetime import datetime, timedelta, timezone
import time

# 페이지 설정
st.set_page_config(page_title="이미지 수집기 Pro", page_icon="📸", layout="wide")

# --- CSS: 기존 UI 및 정렬 절대 보존 ---
st.markdown("""
    <style>
    @media (min-width: 769px) {
        div[data-testid="stVerticalBlock"] > div:has(div.fixed-header) {
            position: sticky; top: 0; background-color: white; z-index: 999;
            padding: 10px 15px 15px 15px; box-shadow: 0 8px 20px rgba(0,0,0,0.1); 
            border-bottom: 1px solid #e1e4e8;
        }
    }
    @media (max-width: 768px) {
        div[data-testid="stVerticalBlock"] > div:has(div.fixed-header) {
            position: relative !important; box-shadow: none !important; padding: 10px 5px !important;
        }
    }
    .image-card-container {
        border: 1px solid #e1e4e8; border-radius: 20px; padding: 15px;
        margin-bottom: 10px; background-color: #ffffff; overflow: hidden;
    }
    .stImage { margin-bottom: 0px !important; }
    .selected-img img { filter: blur(5px) grayscale(40%); transition: filter 0.2s ease-in-out; }
    .stButton > button { height: 45px !important; border-radius: 12px !important; font-weight: bold !important; width: 100% !important; }
    div[data-testid="stCheckbox"] {
        height: 45px !important; border-radius: 12px !important; border: 1px solid #dcdfe6;
        padding: 0 10px !important; display: flex; align-items: center; justify-content: center;
        background-color: white; margin-top: 0px !important;
    }
    div[data-testid="stCheckbox"]:has(input[aria-checked="true"]) { background-color: #2196F3 !important; border-color: #2196F3 !important; }
    div[data-testid="stCheckbox"]:has(input[aria-checked="true"]) label p { color: white !important; font-weight: bold !important; }
    .source-label { font-size: 0.8rem; color: #666; margin: 8px 0; font-weight: bold; }
    .stImage img { border-radius: 12px; }
    </style>
    """, unsafe_allow_html=True)

# --- 세션 초기화 및 비율 변경 콜백 ---
if 'results' not in st.session_state: st.session_state['results'] = []
if 'all_selected' not in st.session_state: st.session_state['all_selected'] = False

def on_ratio_change():
    # 비율에 맞춰 검색 필터 수치 자동 조정
    if st.session_state.orient_select == "가로형":
        st.session_state.width_val, st.session_state.height_val = 1920, 1080
    elif st.session_state.orient_select == "세로형":
        st.session_state.width_val, st.session_state.height_val = 1080, 1920
    else: # 정사각형
        st.session_state.width_val, st.session_state.height_val = 1080, 1080

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
    # 비율 변경 시 수치 자동 변환 콜백 추가
    ratio_sel = c2.selectbox("비율", ["가로형", "세로형", "정사각형"], key="orient_select", on_change=on_ratio_change, label_visibility="collapsed")
    
    with st.expander("⚙️ 고급 필터", expanded=False):
        f1, f2, f3 = st.columns(3)
        # 세션 스테이트를 사용하여 비율 변경과 연동
        min_w = f1.number_input("가로 최소(px)", value=1920, key="width_val")
        min_h = f2.number_input("세로 최소(px)", value=1080, key="height_val")
        count = f3.slider("개수", 10, 80, 20)

    if st.button("📸 사진 검색 시작", use_container_width=True):
        if query:
            with st.spinner("이미지를 불러오는 중입니다..."):
                results = []
                try:
                    p_key, px_key = st.secrets["PEXELS_API_KEY"], st.secrets["PIXABAY_API_KEY"]
                    orient_map = {"가로형": "landscape", "세로형": "portrait", "정사각형": "square"}
                    
                    # Pexels 검색
                    p_res = requests.get(f"https://api.pexels.com/v1/search?query={query}&per_page={count}&orientation={orient_map[ratio_sel]}", headers={"Authorization": p_key}).json()
                    for img in p_res.get('photos', []):
                        if img['width'] >= min_w and img['height'] >= min_h:
                            results.append({'url': img['src']['large'], 'orig': img['src']['original'], 'source': 'Pexels'})
                    
                    # Pixabay 검색
                    px_res = requests.get(f"https://pixabay.com/api/?key={px_key}&q={query}&image_type=photo&orientation={orient_map[ratio_sel]}&per_page={count}").json()
                    for img in px_res.get('hits', []):
                        if img['imageWidth'] >= min_w and img['imageHeight'] >= min_h:
                            results.append({'url': img['webformatURL'], 'orig': img['largeImageURL'], 'source': 'Pixabay'})
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
                        file_name = f"{si['source']}_{query.replace(' ','_')}_{i+1:02d}_{now_str}.jpg"
                        zf.writestr(file_name, requests.get(si['orig']).content)
                    except: continue
            inf3.download_button(f"📥 {len(temp_sel)}장 다운로드", zip_buf.getvalue(), f"{query}_{now_str}.zip", use_container_width=True, key="top_dl")
    st.markdown('</div>', unsafe_allow_html=True)

# --- 결과 출력 ---
if st.session_state['results']:
    for i in range(0, len(st.session_state['results']), 2):
        row_cols = st.columns(2)
        for j in range(2):
            idx = i + j
            if idx < len(st.session_state['results']):
                img = st.session_state['results'][idx]
                with row_cols[j]:
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
