import streamlit as st
import requests
import os
import zipfile
from io import BytesIO

# ----------------------------------------------------------------
# 주의: 이 코드에는 'import tkinter'가 절대 포함되면 안 됩니다!
# ----------------------------------------------------------------

# 페이지 설정
st.set_page_config(page_title="이미지 수집기 Pro", page_icon="📸", layout="wide")

# 모바일/웹 최적화 CSS
st.markdown("""
    <style>
    .stButton>button { width: 100%; border-radius: 10px; height: 3em; font-weight: bold; }
    .stDownloadButton>button { width: 100%; background-color: #2196F3; color: white; }
    [data-testid="stImage"] { border-radius: 15px; border: 2px solid #f0f2f6; }
    </style>
    """, unsafe_allow_html=True)

# 사이드바 API 설정
st.sidebar.title("🔑 API 키 설정")
pexels_key = st.sidebar.text_input("Pexels API Key", type="password")
pixabay_key = st.sidebar.text_input("Pixabay API Key", type="password")

st.title("📸 이미지 수집기 Pro")
st.write("PC와 스마트폰 어디서든 고화질 이미지를 수집하세요.")

# 입력 영역
with st.container():
    col1, col2 = st.columns([2, 1])
    with col1:
        query = st.text_input("🔍 검색어", placeholder="예: mountain, ocean")
    with col2:
        orientation = st.selectbox("📐 비율", ["landscape", "portrait", "square"])

    with st.expander("⚙️ 상세 필터"):
        c1, c2, c3 = st.columns(3)
        min_w = c1.number_input("최소 가로(px)", value=1920)
        min_h = c2.number_input("최소 세로(px)", value=1080)
        count = c3.slider("사이트당 개수", 10, 80, 20)

# 검색 실행
if st.button("사진 검색 시작"):
    if not pexels_key or not pixabay_key:
        st.error("사이드바에 API 키를 입력해주세요.")
    elif not query:
        st.warning("검색어를 입력해주세요.")
    else:
        results = []
        with st.spinner(f"'{query}' 이미지 수집 중..."):
            # Pexels API
            try:
                p_url = f"https://api.pexels.com/v1/search?query={query}&per_page={count}&orientation={orientation}"
                p_res = requests.get(p_url, headers={"Authorization": pexels_key}, timeout=5).json()
                for img in p_res.get('photos', []):
                    if img['width'] >= min_w and img['height'] >= min_h:
                        results.append({'url': img['src']['large'], 'orig': img['src']['original'], 'source': 'Pexels'})
            except: pass

            # Pixabay API
            try:
                px_url = f"https://pixabay.com/api/?key={pixabay_key}&q={query}&image_type=photo&orientation={orientation}&safesearch=true&per_page={count}"
                px_res = requests.get(px_url, timeout=5).json()
                for img in px_res.get('hits', []):
                    if img['imageWidth'] >= min_w and img['imageHeight'] >= min_h:
                        results.append({'url': img['webformatURL'], 'orig': img['largeImageURL'], 'source': 'Pixabay'})
            except: pass

        if results:
            st.session_state['results'] = results
            st.success(f"총 {len(results)}개의 이미지를 찾았습니다!")
        else:
            st.info("검색 결과가 없습니다.")

# 결과 표시 및 선택
if 'results' in st.session_state:
    results = st.session_state['results']
    cols = st.columns(3)
    selected_urls = []

    for idx, img in enumerate(results):
        with cols[idx % 3]:
            st.image(img['url'], use_container_width=True)
            if st.checkbox(f"선택 ({img['source']})", key=f"chk_{idx}"):
                selected_urls.append(img)

    if selected_urls:
        st.divider()
        if st.button(f"📥 선택한 {len(selected_urls)}장 ZIP으로 압축"):
            zip_buffer = BytesIO()
            with zipfile.ZipFile(zip_buffer, "w") as zf:
                for i, img in enumerate(selected_urls):
                    try:
                        res = requests.get(img['orig'], timeout=10)
                        zf.writestr(f"img_{i}_{img['source']}.jpg", res.content)
                    except: continue
            
            st.download_button(
                label="📁 ZIP 파일 다운로드",
                data=zip_buffer.getvalue(),
                file_name=f"{query}_images.zip",
                mime="application/zip"
            )
