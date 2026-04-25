"""
PDF_Text_Enhancer.py
Copyright (c) 2026 zyutama
Released under the MIT license
https://opensource.org/licenses/mit-license.php

Note: 
- This software uses PyMuPDF (AGPL-3.0).
- This software uses Pillow (HPND License).
- This software uses OpenCV (Apache-2.0 License).
"""
import sys
import cv2
import numpy as np
import fitz  # PyMuPDF
import tkinter as tk
from tkinter import filedialog, ttk
from PIL import Image, ImageTk

class PDFEnhancerTk:
    def __init__(self, root):
        self.root = root
        self.root.title("PDF Text Enhancer (Tkinter Version)")
        self.root.geometry("1000x800")

        self.pdf_doc = None
        self.current_page = 0
        self.original_cv_rgb = None
        self.processing_mode_var = tk.StringVar(value="normal") # normal, stylish, blueprint, cyber
        self.debug_mode_var = tk.BooleanVar(value=False) # New: Debug mode variable
        self.fit_page_var = tk.BooleanVar(value=False)
        self.grayscale_save_var = tk.BooleanVar(value=False)
        self.photo_img = None # 参照保持用

        self.setup_ui()

    def setup_ui(self):
        # --- 操作パネル ---
        ctrl_frame = tk.Frame(self.root, pady=10)
        ctrl_frame.pack(side="top", fill="x")

        btn_open = tk.Button(ctrl_frame, text="PDFを開く", command=self.open_pdf)
        btn_open.pack(side="left", padx=10)

        # ページ切り替え
        btn_prev = tk.Button(ctrl_frame, text="< 前", command=lambda: self.load_page(self.current_page - 1))
        btn_prev.pack(side="left", padx=2)
        
        self.lbl_page = tk.Label(ctrl_frame, text="Page: 0/0")
        self.lbl_page.pack(side="left", padx=5)

        btn_next = tk.Button(ctrl_frame, text="次 >", command=lambda: self.load_page(self.current_page + 1))
        btn_next.pack(side="left", padx=2)

        tk.Label(ctrl_frame, text="黒の強調しきい値:").pack(side="left")
        
        self.threshold_var = tk.IntVar(value=180)
        self.slider = tk.Scale(ctrl_frame, from_=50, to=250, orient=tk.HORIZONTAL, 
                               variable=self.threshold_var, command=lambda e: self.update_preview())
        self.slider.pack(side="left", fill="x", expand=True, padx=10)

        self.lbl_value = tk.Label(ctrl_frame, text="強調度: 180")
        self.lbl_value.pack(side="left", padx=10)

        self.chk_fit = tk.Checkbutton(ctrl_frame, text="全体表示", variable=self.fit_page_var, command=self.update_preview)
        self.chk_fit.pack(side="left", padx=5)

        # --- 加工モードグループ ---
        mode_frame = tk.LabelFrame(ctrl_frame, text="加工モード", padx=5, pady=5)
        mode_frame.pack(side="left", padx=10)

        tk.Radiobutton(mode_frame, text="通常", variable=self.processing_mode_var, value="normal", command=self.update_preview).pack(side="left")
        tk.Radiobutton(mode_frame, text="加工その1 (紺背景)", variable=self.processing_mode_var, value="stylish", command=self.update_preview).pack(side="left")
        tk.Radiobutton(mode_frame, text="加工その2 (青焼き風)", variable=self.processing_mode_var, value="blueprint", command=self.update_preview).pack(side="left")
        tk.Radiobutton(mode_frame, text="加工その3 (サイバー)", variable=self.processing_mode_var, value="cyber", command=self.update_preview).pack(side="left")

        # New: Debug Mode Checkbutton
        self.chk_debug = tk.Checkbutton(ctrl_frame, text="デバッグ表示", variable=self.debug_mode_var, command=self.update_preview)
        self.chk_debug.pack(side="left", padx=5)

        self.chk_grayscale = tk.Checkbutton(ctrl_frame, text="白黒で保存", variable=self.grayscale_save_var)
        self.chk_grayscale.pack(side="left", padx=5)

        btn_save = tk.Button(ctrl_frame, text="保存 (現在の設定で)", command=self.save_pdf, bg="#00bfff")
        btn_save.pack(side="left", padx=10)

        # --- プレビューエリア (スクロール付き) ---
        self.preview_frame = tk.Frame(self.root)
        self.preview_frame.pack(side="top", fill="both", expand=True)

        # --- ステータスバー ---
        self.status_label = tk.Label(self.root, text="Ready", bd=1, relief=tk.SUNKEN, anchor=tk.W)
        self.status_label.pack(side=tk.BOTTOM, fill=tk.X)

        self.canvas = tk.Canvas(self.preview_frame, bg="gray")
        self.v_scroll = tk.Scrollbar(self.preview_frame, orient="vertical", command=self.canvas.yview)
        self.h_scroll = tk.Scrollbar(self.preview_frame, orient="horizontal", command=self.canvas.xview)
        self.canvas.configure(yscrollcommand=self.v_scroll.set, xscrollcommand=self.h_scroll.set)

        self.v_scroll.pack(side="right", fill="y")
        self.h_scroll.pack(side="bottom", fill="x")
        self.canvas.pack(side="left", fill="both", expand=True)

        self.canvas_img_id = self.canvas.create_image(0, 0, anchor="nw")
        
        # ウィンドウサイズ変更時にプレビューを更新
        self.canvas.bind("<Configure>", lambda e: self.update_preview())

    def open_pdf(self):
        path = filedialog.askopenfilename(filetypes=[("PDF Files", "*.pdf")])
        if path:
            self.status_label.config(text=f"PDFを読み込み中: {path}")
            self.pdf_doc = fitz.open(path)
            self.load_page(0)
            self.status_label.config(text=f"PDF読み込み完了: {len(self.pdf_doc)}ページ")

    def load_page(self, page_num):
        if not self.pdf_doc: self.status_label.config(text="エラー: PDFが読み込まれていません"); return
        # ページ範囲のチェック
        if page_num < 0 or page_num >= len(self.pdf_doc):
            return
            
        self.current_page = page_num
        self.lbl_page.config(text=f"Page: {self.current_page + 1} / {len(self.pdf_doc)}")

        page = self.pdf_doc.load_page(page_num)
        pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
        
        img_array = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.h, pix.w, pix.n)
        # カラー情報を保持（RGBAならRGBに変換）
        if pix.n == 4:
            self.original_cv_rgb = cv2.cvtColor(img_array, cv2.COLOR_RGBA2RGB)
        else:
            self.original_cv_rgb = img_array.copy()
        
        self.status_label.config(text=f"ページ {self.current_page + 1} / {len(self.pdf_doc)} を表示中")
        self.update_preview()

    def process_image(self, rgb_img, thresh):
        """カラーを維持しつつ、ノイズを抑えて黒を強調する共通ロジック"""
        if self.processing_mode_var.get() == "stylish":
            # --- 加工その1 (紺背景・白文字) ---
            gray = cv2.cvtColor(rgb_img, cv2.COLOR_RGB2GRAY)
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
            enhanced_gray = clahe.apply(gray)
            
            # 文字部分の抽出 (明るさがしきい値以下の部分)
            _, dark_mask = cv2.threshold(enhanced_gray, thresh, 255, cv2.THRESH_BINARY_INV)
            
            # 紺背景の作成 (RGB: 0, 0, 128)
            result = np.full(rgb_img.shape, [0, 0, 128], dtype=np.uint8)
            # 文字を白にする
            result[dark_mask == 255] = [255, 255, 255]
            
            # 色付き要素（赤ペンなど）の救済
            hsv = cv2.cvtColor(rgb_img, cv2.COLOR_RGB2HSV)
            s = hsv[:, :, 1]
            _, color_mask = cv2.threshold(s, 40, 255, cv2.THRESH_BINARY)
            # 文字マスクに含まれない色付き部分
            extra_color_mask = cv2.bitwise_and(color_mask, cv2.bitwise_not(dark_mask))
            
            # 色付き部分を少し明るくして合成
            hsv_bright = hsv.copy()
            hsv_bright[:, :, 2] = np.clip(hsv_bright[:, :, 2].astype(np.int16) + 50, 0, 255).astype(np.uint8)
            rgb_bright = cv2.cvtColor(hsv_bright, cv2.COLOR_HSV2RGB)
            result[extra_color_mask == 255] = rgb_bright[extra_color_mask == 255]
            
            return result # 処理をここで終了
        elif self.processing_mode_var.get() == "blueprint":
            # --- 加工その2 (青焼き風) ---
            gray = cv2.cvtColor(rgb_img, cv2.COLOR_RGB2GRAY)
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
            enhanced_gray = clahe.apply(gray)
            blurred_gray = cv2.GaussianBlur(enhanced_gray, (0, 0), 3)
            enhanced_gray = cv2.addWeighted(enhanced_gray, 1.5, blurred_gray, -0.5, 0)

            _, text_mask = cv2.threshold(enhanced_gray, thresh, 255, cv2.THRESH_BINARY_INV)
            
            blueprint_bg_color = [100, 40, 20] # BGR: R=20, G=40, B=100 (深い青)
            blueprint_text_color = [255, 250, 200] # BGR: R=200, G=250, B=255 (明るいシアン)
            
            result = np.full(rgb_img.shape, blueprint_bg_color, dtype=np.uint8)
            result[text_mask == 255] = blueprint_text_color
            
            hsv_orig = cv2.cvtColor(rgb_img, cv2.COLOR_RGB2HSV)
            s_orig = hsv_orig[:, :, 1]
            _, sat_mask = cv2.threshold(s_orig, 50, 255, cv2.THRESH_BINARY)
            colored_non_text_mask = cv2.bitwise_and(sat_mask, cv2.bitwise_not(text_mask))
            
            highlight_color = [0, 255, 255] # BGR: R=255, G=255, B=0 (明るい黄色)
            result[colored_non_text_mask == 255] = highlight_color
            
            return result # 処理をここで終了
        elif self.processing_mode_var.get() == "cyber":
            # --- 加工その3 (サイバー) ---
            gray = cv2.cvtColor(rgb_img, cv2.COLOR_RGB2GRAY)
            # コントラストを強めに調整してエッジを際立たせる
            clahe = cv2.createCLAHE(clipLimit=3.5, tileGridSize=(8, 8))
            enhanced_gray = clahe.apply(gray)
            
            _, text_mask = cv2.threshold(enhanced_gray, thresh, 255, cv2.THRESH_BINARY_INV)
            
            # 背景: ディープナイトパープル
            result = np.full(rgb_img.shape, [20, 0, 40], dtype=np.uint8)
            
            # 文字部分にゲーミングPCのような7色グラデーション（1枚に3波長分）を適用
            h, w = rgb_img.shape[:2]
            # y座標に応じて色相(0-179)を変化させる。540 = 180度（1周期）× 3波長
            hue_map = (np.linspace(0, 540, h, endpoint=False) % 180).astype(np.uint8)
            hue_2d = np.tile(hue_map[:, np.newaxis], (1, w))
            hsv_rainbow = np.stack([hue_2d, np.full((h, w), 255, dtype=np.uint8), np.full((h, w), 255, dtype=np.uint8)], axis=2)
            rgb_rainbow = cv2.cvtColor(hsv_rainbow, cv2.COLOR_HSV2RGB)
            result[text_mask == 255] = rgb_rainbow[text_mask == 255]
            
            # 彩度ベースでカラー要素（ペン書きなど）を抽出
            hsv = cv2.cvtColor(rgb_img, cv2.COLOR_RGB2HSV)
            s_mask = cv2.threshold(hsv[:, :, 1], 50, 255, cv2.THRESH_BINARY)[1]
            extra_color = cv2.bitwise_and(s_mask, cv2.bitwise_not(text_mask))
            # カラー部分: ネオンピンク
            result[extra_color == 255] = [255, 20, 147]
            return result # 処理をここで終了
        
        # --- 通常モード (白背景・黒強調) ---
        lab = cv2.cvtColor(rgb_img, cv2.COLOR_RGB2LAB)
        l, a, b = cv2.split(lab)

        # 1. 文字をはっきりさせる (CLAHE: 局所的なコントラスト強調)
        # これにより、薄い文字が浮き上がり、背景との境界が明確になります
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        l = clahe.apply(l)

        # 2. シャープネス（アンシャープマスキング）
        # 文字のエッジを立たせて読みやすくします
        blurred = cv2.GaussianBlur(l, (0, 0), 3)
        l = cv2.addWeighted(l, 1.5, blurred, -0.5, 0)

        # 3. トーンカーブ処理による背景飛ばしと黒強調
        # thresh以上の明るい色は「白(255)」に固定。
        # それ以下の色は、コントラストを広げて「黒」をより深くします。
        # これにより、薄い背景色が濃くなるのを防ぎます。
        
        # ルックアップテーブル(LUT)を作成して高速処理
        black_point = 30  # これ以下の暗い色は真っ黒にする
        white_point = thresh
        
        table = np.array([
            np.clip((i - black_point) * 255 / (white_point - black_point), 0, 255)
            if i < white_point else 255
            for i in range(256)
        ]).astype("uint8")
        
        l = cv2.LUT(l, table)

        # 5. RGBに戻す
        return cv2.cvtColor(cv2.merge([l, a, b]), cv2.COLOR_LAB2RGB)

    def get_debug_view(self, rgb_img, thresh):
        """各チャンネルの内部状態を可視化した2x2のタイル画像を作成"""
        h, w = rgb_img.shape[:2]
        # 最終結果を計算
        result = self.process_image(rgb_img, thresh)

        # Lチャンネル (LAB空間の明るさ)
        # 1. 輝度処理(L)の可視化 (スライダー値 thresh の影響を反映)
        lab = cv2.cvtColor(rgb_img, cv2.COLOR_RGB2LAB)
        l, a, b = cv2.split(lab)
        
        # Sチャンネル (HSV空間の彩度 - 色付き部分の判定用)
        # 内部処理(CLAHE + シャープネス)を再現してスライダーの影響を反映
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        l_proc = clahe.apply(l)
        blurred = cv2.GaussianBlur(l_proc, (0, 0), 3)
        l_proc = cv2.addWeighted(l_proc, 1.5, blurred, -0.5, 0)
        
        if self.processing_mode_var.get() != "normal":
            # 加工モード時は、スライダーで決まる「文字抽出マスク」を表示
            _, l_debug = cv2.threshold(l_proc, thresh, 255, cv2.THRESH_BINARY_INV)
        else:
            # 通常モード時は、トーンカーブ適用後の輝度分布を表示
            black_point = 30
            table = np.array([
                np.clip((i - black_point) * 255 / (thresh - black_point), 0, 255)
                if i < thresh else 255
                for i in range(256)
            ]).astype("uint8")
            l_debug = cv2.LUT(l_proc, table)
        l_chan_view = cv2.cvtColor(l_debug, cv2.COLOR_GRAY2RGB)
        
        # 2. 彩度(S)マスクの可視化 (色付き部分の判定状態)
        hsv = cv2.cvtColor(rgb_img, cv2.COLOR_RGB2HSV)
        s = hsv[:, :, 1]
        # 彩度（色の鮮やかさ）が40以上の場所を白く表示する
        _, color_mask = cv2.threshold(s, 40, 255, cv2.THRESH_BINARY)
        s_chan_view = cv2.cvtColor(color_mask, cv2.COLOR_GRAY2RGB)

        # ラベルの描画 (OpenCVで画像に文字を入れる)
        font = cv2.FONT_HERSHEY_SIMPLEX
        def add_lbl(img, txt):
            tmp = img.copy()
            cv2.putText(tmp, txt, (30, 80), font, 1.5, (255, 0, 0), 3)
            return tmp

        tile1 = add_lbl(rgb_img, "1.Original")
        tile2 = add_lbl(l_chan_view, f"2.L-Channel (Applied)")
        tile3 = add_lbl(s_chan_view, "3.S-Channel (Color Mask)")
        tile4 = add_lbl(result, "4.Final Result")

        # 2x2に結合
        top = np.hstack([tile1, tile2])
        bottom = np.hstack([tile3, tile4])
        tiled = np.vstack([top, bottom])
        
        return tiled

    def update_preview(self):
        if self.original_cv_rgb is None:
            return

        thresh_val = self.threshold_var.get()
        self.lbl_value.config(text=f"強調度: {thresh_val}")

        if self.debug_mode_var.get():
            enhanced = self.get_debug_view(self.original_cv_rgb, thresh_val)
        else:
            enhanced = self.process_image(self.original_cv_rgb, thresh_val)

        # OpenCV(numpy) -> PIL -> ImageTk
        pil_img = Image.fromarray(enhanced)
        
        # キャンバスの幅に合わせてリサイズ（アスペクト比維持）
        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()
        if canvas_width > 50 and canvas_height > 50:
            w, h = pil_img.size
            if self.fit_page_var.get():
                # 幅と高さの両方に収める (全体表示)
                scale = min((canvas_width - 20) / w, (canvas_height - 20) / h)
            else:
                # 幅のみ合わせる
                scale = (canvas_width - 20) / w
            pil_img = pil_img.resize((int(w * scale), int(h * scale)), Image.Resampling.LANCZOS)

        self.photo_img = ImageTk.PhotoImage(pil_img)
        self.canvas.itemconfig(self.canvas_img_id, image=self.photo_img)
        self.canvas.config(scrollregion=self.canvas.bbox("all"))

    def save_pdf(self):
        if not self.pdf_doc: return
        
        save_path = filedialog.asksaveasfilename(defaultextension=".pdf", filetypes=[("PDF Files", "*.pdf")])
        if save_path:
            self.status_label.config(text="PDFを保存中...")
            output_pages = []
            thresh_val = self.threshold_var.get()
            
            for page_num in range(len(self.pdf_doc)):
                page = self.pdf_doc.load_page(page_num)
                pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
                img_array = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.h, pix.w, pix.n)
                
                if pix.n == 4:
                    rgb = cv2.cvtColor(img_array, cv2.COLOR_RGBA2RGB)
                else:
                    rgb = img_array.copy()
                
                enhanced = self.process_image(rgb, thresh_val)
                if self.grayscale_save_var.get():
                    # 加工後の画像をグレースケールに変換
                    enhanced = cv2.cvtColor(enhanced, cv2.COLOR_RGB2GRAY)
                
                output_pages.append(Image.fromarray(enhanced))
            self.status_label.config(text="保存処理完了。PDFを書き出し中...")
            if output_pages:
                output_pages[0].save(save_path, save_all=True, append_images=output_pages[1:])
                self.status_label.config(text=f"PDF保存完了: {save_path}")
                tk.messagebox.showinfo("完了", f"PDFの保存が完了しました。\n{save_path}")

if __name__ == "__main__":
    root = tk.Tk()
    # スライダーのリアルタイム更新をスムーズにするために初期サイズを設定
    root.update()
    app = PDFEnhancerTk(root)
    root.mainloop()