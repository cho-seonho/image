import streamlit as st
import requests
import zipfile
from io import BytesIO

# 페이지 설정
st.set_page_config(page_title="이미지 수집기 Pro", page_icon="📸", layout="wide")

# CSS: 상단 고정, 이미지 클릭 효과, 전체 화면 모달 스타일
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
    
    /* 이미지 클릭 유도 */
    .stImage img {
        transition: 0.3s;
        cursor: zoom-in;
    }

    /* 전체 화면 모달 스타일 (UI 전체를 가림) */
    .modal-overlay {
        position: fixed;
        top: 0; left: 0; width: 100%; height: 100%;
        background-color: rgba(0,0,0,0.9);
        z-index: 9999;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
    }
    .modal-content {
        max-width: 90%;
        max-height: 80%;
        border-radius: 10px;
    }
    .close-btn {
        position: absolute;
        top: 20px; right: 30px;
        color: white; font-size: 40px; font-weight: bold;
        cursor: pointer;
        background: none; border: none;
    }

    .stButton>button { width: 100%; border-radius: 10px; font-weight: bold; }
    .stDownloadButton>button { width: 100%; background-color: #2196F3; color: white; border-radius: 10px; }
    </style>
    """, unsafe_allow_html=True)

# API 키 불러오기
try:
    PEXELS_API_KEY = st.secrets["PEXELS_API_KEY"]
    PIXABAY_API_KEY = st.secrets["PIXABAY_API_KEY"]
except:
    st.error("⚠️ API 키가 설정되지 않았습니다. Streamlit Secrets를 확인해주세요.")
    st.stop()

# 세션 상태 초기화
if 'results' not in st.session_state: st.session_state['results'] = []
if 'search_clicked' not in st.session_state: st.session_state['search_clicked'] = False
if 'expanded_img' not in st.session_state: st.session_state['expanded_img'] = None
if 'width_input' not in st.session_state: st.session_state['width_input'] = 1920
if 'height_input' not in st.session_state: st.session_state['height_input'] = 1080

def on_ratio_change():
    ratio = st.session_state.orient_select
    if ratio == "가로형":
        st.session_state.width_input, st.session_state.height_input = 1920, 1080
    elif ratio == "세로형":
        st.session_state.width_input, st.session_state.height_input = 1080, 1920
    else: # 정사각형
        st.session_state.width_input, st.session_state.height_input = 1080, 1080

# 전체 화면 모달 로직
if st.session_state.expanded_img:
    st.markdown(f"""
        <div class="modal-overlay">
            <button class="close-btn" onclick="window.location.reload()">×</button>
            <img src="{st.session_state.expanded_img}" class="modal-content">
            <p style="color:white; margin-top:20px;">화면 아무 곳이나 새로고침하거나 X를 눌러 닫으세요</p>
        </div>
    """, unsafe_allow_html=True)
    if st.button("닫기 (모달 종료)"):
        st.session_state.expanded_img = None
        st.rerun()

# 상단 고정 UI
with st.container():
    st.markdown('<div class="fixed-header">', unsafe_allow_html=True)
    st.title("📸 이미지 수집기 Pro")
    
    col_search, col_ratio = st.columns([3, 1])
    query = col_search.text_input("🔍 검색어", placeholder="예: 바다, 커피", label_visibility="collapsed")
    ratio_display = col_ratio.selectbox("📐 비율", ["가로형", "세로형", "정사각형"], key="orient_select", on_change=on_ratio_change, label_visibility="collapsed")
    
    # 상세 검색 기능 (복구됨)
    with st.expander("⚙️ 고급 필터 (해상도/개수)", expanded=False):
        f1, f2, f3 = st.columns(3)
        min_w = f1.number_input("가로(px)", key="width_input", step=1, format="%d")
        min_h = f2.number_input("세로(px)", key="height_input", step=1, format="%d")
        count = f3.slider("개수", 10, 80, 20)

    # 검색 버튼
    btn_label = "✅ 분석 완료 (다시 검색)" if st.session_state.search_clicked else "📸 사진 검색 및 분석 시작"
    if st.button(btn_label):
        if query:
            st.session_state.search_clicked = True
            results = []
            orient_map = {"가로형": "landscape", "세로형": "portrait", "정사각형": "square"}
            try:
                # Pexels
                p_res = requests.get(f"https://api.pexels.com/v1/search?query={query}&per_page={count}&orientation={orient_map[ratio_display]}", 
                                     headers={"Authorization": PEXELS_API_KEY}).json()
                for img in p_res.get('photos', []):
                    if img['width'] >= min_w and img['height'] >= min_h:
                        results.append({'url': img['src']['large'], 'orig': img['src']['original'], 'source': 'Pexels'})
                # Pixabay
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

# 이미지 리스트 출력
if st.session_state['results']:
    selected_images = []
    cols = st.columns(3)
    
    for idx, img in enumerate(st.session_state['results']):
        with cols[idx % 3]:
            st.image(img['url'], use_container_width=True)
            c1, c2 = st.columns([1, 1])
            # 이미지 원본 확대를 위한 버튼
            if c1.button("🔍 크게보기", key=f"exp_{idx}"):
                st.session_state.expanded_img = img['orig']
                st.rerun()
            if c2.checkbox(f"선택하기", key=f"chk_{idx}"):
                selected_images.append(img)
    
    if selected_images:
        select_placeholder.write(f"📍 **{len(selected_images)}**장 선택됨")
        with download_placeholder:
            zip_buffer = BytesIO()
            with zipfile.ZipFile(zip_buffer, "w") as zf:
                for i, si in enumerate(selected_images):
                    try:
                        res = requests.get(si['orig'], timeout=10)
                        zf.writestr(f"img_{i}.jpg", res.content)
                    except: continue
            st.download_button(f"📥 {len(selected_images)}장 다운로드", data=zip_buffer.getvalue(), file_name=f"{query}.zip")
    else:
        select_placeholder.write("📍 0장 선택됨")
