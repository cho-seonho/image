import os
import requests
import platform
import threading
import tkinter as tk
from tkinter import messagebox, ttk
from PIL import Image, ImageTk
from io import BytesIO

class ImageCollector:
    def __init__(self, root):
        self.root = root
        self.root.title("이미지 수집기 Pro (비율 정밀 필터)")
        self.root.geometry("380x550")
        self.selected_images = []
        self.is_searching = False
        self.spinner_idx = 0
        self.session = None
        self.setup_main_ui()

    def setup_main_ui(self):
        tk.Label(self.root, text="🔍 검색어:").pack(pady=(10, 0))
        self.entry_query = tk.Entry(self.root, width=35); self.entry_query.pack(pady=5)

        tk.Label(self.root, text="📐 이미지 비율:").pack(pady=5)
        self.combo_orient = ttk.Combobox(self.root, values=["가로형 (Landscape)", "세로형 (Portrait)", "정사각형 (Square)"], state="readonly", width=32)
        self.combo_orient.current(0); self.combo_orient.pack()
        self.combo_orient.bind("<<ComboboxSelected>>", self.update_resolution_presets)

        tk.Label(self.root, text="⚙️ 해상도 필터 옵션:").pack(pady=5)
        self.combo_filter = ttk.Combobox(self.root, values=["지정 크기 이상", "정확히 일치"], state="readonly", width=32)
        self.combo_filter.current(0); self.combo_filter.pack()

        tk.Label(self.root, text="↔️ 가로 해상도 (px):").pack(pady=5)
        self.entry_width = tk.Entry(self.root, width=35); self.entry_width.insert(0, "1920"); self.entry_width.pack()

        tk.Label(self.root, text="↕️ 세로 해상도 (px):").pack(pady=5)
        self.entry_height = tk.Entry(self.root, width=35); self.entry_height.insert(0, "1080"); self.entry_height.pack()

        tk.Label(self.root, text="🔢 최대 검색 개수 (사이트당):").pack(pady=5)
        self.entry_count = tk.Entry(self.root, width=35); self.entry_count.insert(0, "20"); self.entry_count.pack()

        self.label_status = tk.Label(self.root, text="준비 완료", fg="black", bg="#f0f0f0", 
                                     font=("Arial", 10, "bold"), width=40, pady=5)
        self.label_status.pack(pady=10)

        self.btn_search = tk.Button(self.root, text="📸 사진 검색 및 선택", command=self.toggle_search, 
                                     bg="#4CAF50", fg="white", font=("Arial", 11, "bold"), width=25, height=2)
        self.btn_search.pack(pady=10)

    def update_resolution_presets(self, event):
        orient = self.combo_orient.get()
        self.entry_width.delete(0, tk.END); self.entry_height.delete(0, tk.END)
        if "가로형" in orient: self.entry_width.insert(0, "1920"); self.entry_height.insert(0, "1080")
        elif "세로형" in orient: self.entry_width.insert(0, "1080"); self.entry_height.insert(0, "1920")
        elif "정사각형" in orient: self.entry_width.insert(0, "1080"); self.entry_height.insert(0, "1080")

    def toggle_search(self):
        if not self.is_searching:
            self.start_search()
        else:
            self.is_searching = False
            # 세션을 닫아 모든 대기 중인 네트워크 요청을 즉시 파괴
            if self.session:
                self.session.close()
            self.stop_search(cancelled=True)

    def stop_search(self, cancelled=False):
        self.is_searching = False
        self.btn_search.config(text="📸 사진 검색 및 선택", bg="#4CAF50", state="normal")
        if cancelled:
            self.label_status.config(text="⏹ 검색이 중단되었습니다.", bg="#ffcccc", fg="red")
        else:
            self.label_status.config(text="준비 완료", bg="#f0f0f0", fg="black")

    def animate_spinner(self, query):
        if not self.is_searching: return
        spinners = ["◐", "◓", "◑", "◒"]
        current_spin = spinners[self.spinner_idx % 4]
        self.label_status.config(text=f"{current_spin} '{query}' 분석 중 {current_spin}")
        self.spinner_idx += 1
        self.root.after(100, lambda: self.animate_spinner(query))

    def start_search(self):
        query = self.entry_query.get()
        if not query:
            messagebox.showwarning("입력 오류", "검색어를 입력해주세요!"); return
        
        try:
            min_w, min_h, count = int(self.entry_width.get()), int(self.entry_height.get()), int(self.entry_count.get())
        except:
            messagebox.showwarning("입력 오류", "숫자를 입력해주세요!"); return

        self.is_searching = True
        self.session = requests.Session()
        self.btn_search.config(text="❌ 즉시 중단하기", bg="#f44336")
        self.label_status.config(bg="#e3f2fd", fg="#1976d2")
        
        self.animate_spinner(query)
        threading.Thread(target=self.search_thread, args=(query, count, min_w, min_h), daemon=True).start()

    def search_thread(self, query, count, min_w, min_h):
        selected_orient = self.combo_orient.get()
        filter_mode = self.combo_filter.get()
        preview_list = []
        orient_key = "landscape" if "가로" in selected_orient else "portrait" if "세로" in selected_orient else "square"

        sources = [
            {'name': 'pexels', 'url': f"https://api.pexels.com/v1/search?query={query}&per_page=80&orientation={orient_key}", 'headers': {"Authorization": PEXELS_API_KEY}},
            {'name': 'pixabay', 'url': f"https://pixabay.com/api/?key={PIXABAY_API_KEY}&q={query}&image_type=photo&safesearch=true&per_page=80&orientation={orient_key}", 'headers': {}}
        ]

        # 1단계: API에서 목록 가져오기
        for src in sources:
            if not self.is_searching: break
            try:
                # timeout을 3초로 줄여 반응성 확보
                res = self.session.get(src['url'], headers=src['headers'], timeout=3).json()
                items = res.get('photos') if src['name'] == 'pexels' else res.get('hits')
                if not items: continue
                
                for item in items:
                    if not self.is_searching: break
                    if len([p for p in preview_list if p['source'] == src['name']]) >= count: break
                    
                    w = item.get('width') if src['name'] == 'pexels' else item.get('imageWidth')
                    h = item.get('height') if src['name'] == 'pexels' else item.get('imageHeight')
                    
                    is_size_ok = (w == min_w and h == min_h) if filter_mode == "정확히 일치" else (w >= min_w and h >= min_h)
                    is_ratio_ok = ("가로" in selected_orient and w > h) or ("세로" in selected_orient and h > w) or ("정사각형" in selected_orient and 0.9 <= w/h <= 1.1)

                    if is_size_ok and is_ratio_ok:
                        p_url = item['src']['large'] if src['name'] == 'pexels' else item['webformatURL']
                        o_url = item['src']['original'] if src['name'] == 'pexels' else item['largeImageURL']
                        preview_list.append({'url': p_url, 'orig': o_url, 'source': src['name']})
            except: break

        # 메인 스레드로 결과 전달
        self.root.after(0, lambda: self.finish_search(preview_list, query, selected_orient))

    def finish_search(self, preview_list, query, orient):
        if not self.is_searching: return
        self.stop_search(cancelled=False)
        if not preview_list:
            self.label_status.config(text="❌ 조건에 맞는 사진이 없습니다.", bg="#ffebee", fg="red")
        else:
            self.show_preview_window(preview_list, query, orient)

    def show_preview_window(self, images, query, orientation_text):
        self.preview_win = tk.Toplevel(self.root)
        self.preview_win.title(f"미리보기: {query}")
        self.preview_win.geometry("1050x900")
        self.selected_images = []

        control_frame = tk.Frame(self.preview_win, pady=10)
        control_frame.pack(fill="x", side="top")

        self.btn_bulk_download = tk.Button(control_frame, text="📥 선택한 이미지 다운로드 시작", 
                                          command=lambda: self.bulk_save(query), 
                                          bg="#2196F3", fg="white", font=("Arial", 12, "bold"), height=2)
        self.btn_bulk_download.pack(fill="x", padx=20)

        self.progress = ttk.Progressbar(control_frame, orient="horizontal", length=400, mode="determinate")
        self.progress.pack(fill="x", padx=20, pady=5)

        self.lbl_count_info = tk.Label(control_frame, text=f"검색 결과: {len(images)}장 (현재 0장 선택됨)", font=("Arial", 10, "bold"))
        self.lbl_count_info.pack()

        canvas = tk.Canvas(self.preview_win)
        scrollbar = ttk.Scrollbar(self.preview_win, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        scrollable_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.bind_all("<MouseWheel>", lambda e: canvas.yview_scroll(int(-1*(e.delta/120)), "units"))

        # 별도 스레드에서 이미지 로딩 (UI 프리징 방지)
        threading.Thread(target=self.load_images_into_frame, args=(images, scrollable_frame), daemon=True).start()

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

    def load_images_into_frame(self, images, frame):
        """미리보기 창의 이미지를 한 장씩 로드하며 중단 여부를 체크"""
        row, col = 0, 0
        for img_info in images:
            # 중단 버튼이 눌렸거나 미리보기 창이 닫혔다면 즉시 로딩 중단
            if not self.preview_win.winfo_exists(): break
            
            try:
                res = requests.get(img_info['url'], timeout=3) # 타임아웃 단축
                img = Image.open(BytesIO(res.content))
                img.thumbnail((180, 120))
                photo = ImageTk.PhotoImage(img)
                
                # GUI 업데이트는 after를 통해 안전하게 처리
                self.root.after(0, lambda p=photo, r=row, c=col, i=img_info: self.add_image_label(frame, p, r, c, i, len(images)))
                
                col += 1
                if col > 4: col = 0; row += 1
            except: continue

    def add_image_label(self, parent, photo, row, col, info, total):
        if not self.preview_win.winfo_exists(): return
        f = tk.Frame(parent, bd=3, relief="flat", bg="white")
        f.grid(row=row, column=col, padx=8, pady=8)
        lbl = tk.Label(f, image=photo, cursor="hand2", bg="white")
        lbl.image = photo; lbl.pack()
        lbl.bind("<Button-1>", lambda e, fr=f, i=info: self.toggle_selection(fr, i, total))
        tk.Label(f, text=f"[{info['source'].upper()}]", font=("Arial", 7, "bold"), bg="white").pack()

    def toggle_selection(self, frame, img_info, total):
        if img_info in self.selected_images:
            self.selected_images.remove(img_info)
            frame.config(bg="white")
            for c in frame.winfo_children(): c.config(bg="white")
        else:
            self.selected_images.append(img_info)
            frame.config(bg="#FFEB3B")
            for c in frame.winfo_children(): c.config(bg="#FFEB3B")
        self.lbl_count_info.config(text=f"검색 결과: {total}장 (현재 {len(self.selected_images)}장 선택됨)")

    def bulk_save(self, query):
        if not self.selected_images:
            messagebox.showwarning("경고", "사진을 선택해주세요!"); return

        save_dir = os.path.join(os.getcwd(), "downloads", f"{query}")
        if not os.path.exists(save_dir): os.makedirs(save_dir)

        self.btn_bulk_download.config(state="disabled", text="⏳ 다운로드 진행 중...")
        self.progress['value'] = 0
        self.progress['maximum'] = len(self.selected_images)

        threading.Thread(target=self.download_thread, args=(query, save_dir), daemon=True).start()

    def download_thread(self, query, save_dir):
        success = 0
        for info in self.selected_images:
            try:
                f_name = f"{info['source']}_{query}_{success+1}_{os.urandom(2).hex()}.jpg"
                img_res = requests.get(info['orig'], timeout=10)
                if img_res.status_code == 200:
                    with open(os.path.join(save_dir, f_name), 'wb') as f:
                        f.write(img_res.content)
                    success += 1
                self.root.after(0, lambda: self.progress.step(1))
            except: continue

        self.root.after(0, lambda: self.finish_download(success, save_dir))

    def finish_download(self, success, save_dir):
        messagebox.showinfo("완료", f"{success}장의 사진을 저장했습니다.")
        if self.preview_win.winfo_exists():
            self.preview_win.destroy()
        self.stop_search(cancelled=False)
        if platform.system() == "Windows": os.startfile(save_dir)

# ==========================================
PEXELS_API_KEY = 'jqU0beN1rY3SWkm4sQ4i8m3kK7QjOUsTXICijwgvED78TxCq0mCxML4L'
PIXABAY_API_KEY = '54504229-10010352e9ef9596235672a57'
# ==========================================

if __name__ == "__main__":
    root = tk.Tk(); app = ImageCollector(root); root.mainloop()