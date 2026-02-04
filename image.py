import streamlit as st
import requests
import zipfile
from io import BytesIO

# 페이지 설정
st.set_page_config(page_title="이미지 수집기 Pro", page_icon="📸", layout="wide")

# --- CSS: 유령 테두리 박멸 및 버튼 그룹화 ---
st.markdown("""
    <style>
    /* 1. 파란색 유령 테두리(빈 박스) 완전 제거 */
    div[data-testid="stVerticalBlock"] > div:empty,
    div[data-testid="stVerticalBlock"] > div > div:empty {
        display: none !important;
        height: 0px !important;
        margin: 0 !important;
        padding: 0 !important;
    }
    
    /* 포커스 시 생기는 모든 외곽선 차단 */
    *:focus { outline: none !important; box-shadow: none !important; }

    /* 2. 카드 박스 디자인 (더 직관적으로) */
    .image-card {
        background-color: #ffffff;
        border-radius: 15px;
        border: 1px solid #e0e0e0;
        padding: 12px;
        margin-bottom: 25px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.05);
        transition: transform 0.2s, border 0.2s;
    }
    
    .selected-card {
        border: 2px solid #2196F3 !important;
        background-color: #f0f7ff !important;
        transform: translateY(-3px);
    }

    /* 3. 출처 및 버튼 영역 칼정렬 */
    .info-section {
        margin-top: 10px;
        display: flex;
        flex-direction: column;
        gap: 8px;
    }

    .source-tag {
        font-size: 0.8rem;
        color: #888;
        font-weight: 600;
        display: flex;
        align-items: center;
        gap: 4px;
    }

    /* 4. 보기/선택 버튼 높이 일치 및 그룹화 */
    .stButton > button {
        height: 45px !important;
        border-radius: 10px !important;
        font-weight: bold !important;
        width: 100% !important;
    }

    div[data-testid="stCheckbox"] {
        height: 45px !important;
        background-color: #f8f9fa;
        border: 1px solid #dcdfe6;
        border-radius: 10px;
        display: flex;
        align-items: center;
        justify-content: center;
        width: 100% !important;
        margin: 0 !important;
    }
    
    div[data-testid="stCheckbox"]:hover {
        border-color: #2196F3;
    }

    /* 클릭 시 시각적 피드백 */
    .stButton button:active, div[data-testid="stCheckbox"]:active {
        transform: scale(0.97);
    }
    </style>
    """, unsafe_allow_html=True)

# --- 세션 및 초기값 (0 방지) ---
if 'width_input' not in st.session_state: st.session_state['width_input'] = 1920
if 'height_input' not in st.session_state: st.session_state['height_input'] = 1080
if 'results' not in st.session_state: st.session_state['results'] = []
if 'search_clicked' not in st.session_state: st.session_state['search_clicked'] = False

# API 키
try:
    PEXELS_API_KEY = st.secrets["PEXELS_API_KEY"]
    PIXABAY_API_KEY = st.secrets["PIXABAY_API_KEY"]
except:
    st.error("API 키가 없습니다. secrets.toml을 확인하세요.")
    st.stop()

def on_ratio_change():
    ratio = st.session_state.orient_select
    if ratio == "가로형":
        st.session_state.width_input, st.session_state.height_input = 1920, 1080
    elif ratio == "세로형":
        st.session_state.width_input, st.session_state.height_input = 1080, 1920
    else:
        st.session_state.width_input, st.session_state.height_input = 1080, 1080

# --- 상단 레이아웃 ---
st.title("📸 이미지 수집기 Pro")

with st.container():
    col_search, col_ratio = st.columns([3, 1])
    query = col_search.text_input("검색어 입력", placeholder="예: 고화질 배경화면", label_visibility="collapsed")
    ratio_display = col_ratio.selectbox("비율", ["가로형", "세로형", "정사각형"], key="orient_select", on_change=on_ratio_change, label_visibility="collapsed")
    
    # 고급 필터 기본 열림 설정 (expanded=True)
    with st.expander("⚙️ 고급 필터 (해상도/개수)", expanded=True):
        f1, f2, f3 = st.columns(3)
        min_w = f1.number_input("가로(px)", key="width_input", min_value=0)
        min_h = f2.number_input("세로(px)", key="height_input", min_value=0)
        count = f3.slider("개수", 10, 80, 20)

    if st.button("📸 사진 검색 시작", use_container_width=True):
        if query:
            st.session_state.search_clicked = True
            results = []
            orient_map = {"가로형": "landscape", "세로형": "portrait", "정사각형": "square"}
            try:
                # Pexels 검색
                p_res = requests.get(f"https://api.pexels.com/v1/search?query={query}&per_page={count}&orientation={orient_map[ratio_display]}", 
                                     headers={"Authorization": PEXELS_API_KEY}).json()
                for img in p_res.get('photos', []):
                    if img['width'] >= min_w and img['height'] >= min_h:
                        results.append({'url': img['src']['large'], 'orig': img['src']['original'], 'source': 'Pexels'})
                
                # Pixabay 검색
                px_res = requests.get(f"https://pixabay.com/api/?key={PIXABAY_API_KEY}&q={query}&image_type=photo&orientation={orient_map[ratio_display]}&per_page={count}").json()
                for img in px_res.get('hits', []):
                    if img['imageWidth'] >= min_w and img['imageHeight'] >= min_h:
                        results.append({'url': img['webformatURL'], 'orig': img['largeImageURL'], 'source': 'Pixabay'})
            except: pass
            st.session_state['results'] = results
            st.rerun()

# --- 결과 출력 ---
if st.session_state.search_clicked:
    st.subheader(f"📊 검색 결과: {len(st.session_state['results'])}장")
    selected_images = []
    cols = st.columns(3)
    
    for idx, img in enumerate(st.session_state['results']):
        is_selected = st.session_state.get(f"chk_{idx}", False)
        card_class = "image-card selected-card" if is_selected else "image-card"
        
        with cols[idx % 3]:
            st.markdown(f'<div class="{card_class}">', unsafe_allow_html=True)
            st.image(img['url'], use_container_width=True)
            
            # 출처 표시
            st.markdown(f'<div class="source-tag">📍 {img["source"]}</div>', unsafe_allow_html=True)
            
            # 버튼 영역 (정렬 일치)
            btn_col1, btn_col2 = st.columns(2)
            with btn_col1:
                if st.button("🔍 보기", key=f"btn_{idx}"):
                    st.toast(f"{img['source']} 원본 링크 준비 중...")
                    # 실제 다이얼로그 로직은 생략 가능하나 필요시 추가
            with btn_col2:
                if st.checkbox("선택", key=f"chk_{idx}"):
                    selected_images.append(img)
            st.markdown('</div>', unsafe_allow_html=True)

    # 선택된 이미지 다운로드 바 (하단 고정 느낌)
    if selected_images:
        st.divider()
        zip_buffer = BytesIO()
        with zipfile.ZipFile(zip_buffer, "w") as zf:
            for i, si in enumerate(selected_images):
                res = requests.get(si['orig'])
                zf.writestr(f"image_{i+1}.jpg", res.content)
        st.download_button(f"📥 {len(selected_images)}장 다운로드", data=zip_buffer.getvalue(), file_name="images.zip", use_container_width=True)
