import streamlit as st
import requests
import zipfile
from io import BytesIO

# 페이지 설정
st.set_page_config(page_title="이미지 수집기 Pro", page_icon="📸", layout="wide")

# CSS: 직관적인 카드 UI 및 요소 배치
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
    
    /* 카드 전체 스타일 */
    .image-card {
        background-color: #ffffff;
        border-radius: 12px;
        border: 1px solid #e1e4e8;
        padding: 10px;
        margin-bottom: 15px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.05);
        position: relative;
    }

    /* 이미지 스타일 */
    .stImage img {
        border-radius: 8px;
        transition: 0.2s;
    }

    /* 출처 태그 오버레이 (우측 상단) */
    .source-overlay {
        position: absolute;
        top: 20px;
        right: 20px;
        background: rgba(0, 0, 0, 0.6);
        color: white;
        padding: 2px 8px;
        border-radius: 4px;
        font-size: 0.7rem;
        font-weight: bold;
        z-index: 10;
        pointer-events: none;
    }

    /* 하단 버튼 영역 간격 조절 */
    .button-container {
        margin-top: 8px;
        display: flex;
        gap: 5px;
    }

    .stButton>button { border-radius: 8px; height: 2.5em; font-size: 0.9rem; }
    .stDownloadButton>button { background-color: #2196F3; color: white; border-radius: 8px; }
    
    /* 체크박스 강조 */
    div[data-testid="stCheckbox"] {
        background-color: #f8f9fa;
        padding: 5px 10px;
        border-radius: 6px;
        border: 1px solid #dee2e6;
        width: 100%;
    }
    </style>
    """, unsafe_allow_html=True)

# API 키 불러오기
try:
    PEXELS_API_KEY = st.secrets["PEXELS_API_KEY"]
    PIXABAY_API_KEY = st.secrets["PIXABAY_API_KEY"]
except:
    st.error("⚠️ API 키가 설정되지 않았습니다.")
    st.stop()

# 세션 상태 초기화
if 'results' not in st.session_state: st.session_state['results'] = []
if 'search_clicked' not in st.session_state: st.session_state['search_clicked'] = False
if 'width_input' not in st.session_state: st.session_state['width_input'] = 1920
if 'height_input' not in st.session_state: st.session_state['height_input'] = 1080

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

# --- 상단 고정 UI ---
with st.container():
    st.markdown('<div class="fixed-header">', unsafe_allow_html=True)
    st.title("📸 이미지 수집기 Pro")
    
    col_search, col_ratio = st.columns([3, 1])
    query = col_search.text_input("🔍 검색어", placeholder="어떤 이미지를 찾으시나요?", label_visibility="collapsed")
    ratio_display = col_ratio.selectbox("📐 비율", ["가로형", "세로형", "정사각형"], key="orient_select", on_change=on_ratio_change, label_visibility="collapsed")
    
    with st.expander("⚙️ 고급 필터 (해상도/개수)"):
        f1, f2, f3 = st.columns(3)
        min_w = f1.number_input("가로(px)", key="width_input", step=1, format="%d")
        min_h = f2.number_input("세로(px)", key="height_input", step=1, format="%d")
        count = f3.slider("개수", 10, 80, 20)

    btn_label = "✅ 검색 완료 (다시 검색)" if st.session_state.search_clicked else "📸 사진 검색 및 분석 시작"
    if st.button(btn_label):
        if query:
            st.session_state.search_clicked = True
            results = []
            orient_map = {"가로형": "landscape", "세로형": "portrait", "정사각형": "square"}
            try:
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

# --- 이미지 결과 영역 ---
if st.session_state['results']:
    selected_images = []
    cols = st.columns(3)
    
    for idx, img in enumerate(st.session_state['results']):
        with cols[idx % 3]:
            # 카드 컨테이너 시작
            st.markdown(f'''
                <div class="image-card">
                    <div class="source-overlay">{img["source"]}</div>
            ''', unsafe_allow_html=True)
            
            # 이미지 출력
            st.image(img['url'], use_container_width=True)
            
            # 버튼 영역
            c_btn1, c_btn2 = st.columns([1, 1.2])
            with c_btn1:
                if st.button("🔍 보기", key=f"exp_{idx}"):
                    show_full_image(img['orig'], img['source'])
            with c_btn2:
                # 선택하기 텍스트를 포함한 직관적인 체크박스
                if st.checkbox(f"저장선택", key=f"chk_{idx}"):
                    selected_images.append(img)
            
            st.markdown('</div>', unsafe_allow_html=True)
    
    # 다운로드 업데이트
    if selected_images:
        select_placeholder.write(f"📍 **{len(selected_images)}**장 선택됨")
        with download_placeholder:
            zip_buffer = BytesIO()
            with zipfile.ZipFile(zip_buffer, "w") as zf:
                for i, si in enumerate(selected_images):
                    try:
                        res = requests.get(si['orig'], timeout=10)
                        file_name = f"{i+1:02d}_{si['source']}.jpg"
                        zf.writestr(file_name, res.content)
                    except: continue
            st.download_button(f"📥 {len(selected_images)}장 다운로드", data=zip_buffer.getvalue(), file_name=f"{query}_수집.zip")
    else:
        select_placeholder.write("📍 0장 선택됨")
