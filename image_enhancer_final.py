"""
AI Image Enhancement & Analysis Studio
Dark Professional Edition — v4 (+ Weather Filters)

Dependencies:
pip install opencv-python numpy pillow matplotlib ttkbootstrap
"""
from tkinter import simpledialog
import tkinter as tk
from tkinter import filedialog, messagebox
import ttkbootstrap as tb
from ttkbootstrap.constants import *
import cv2
import numpy as np
from PIL import Image, ImageTk
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import os
from skimage.metrics import peak_signal_noise_ratio as psnr
from skimage.metrics import structural_similarity as ssim

# ─── Palette ──────────────────────────────────────────────────────────────────
BG_PANEL  = "#1e1e2e"
BG_CARD   = "#2a2a3e"
BG_CENTER = "#13131f"
ACCENT    = "#7c6af7"
ACCENT2   = "#56cfb2"
TEXT_PRI  = "#e0e0f0"
TEXT_SEC  = "#9090b0"
BORDER    = "#3a3a55"

MODE_SPLIT   = "split"
MODE_COMPARE = "compare"
MODE_DETAIL  = "detail"

# ═══════════════════════════════════════════════════════════════════════════════
#  WEATHER FILTERS
# ═══════════════════════════════════════════════════════════════════════════════

def weather_fog(img: np.ndarray, intensity: int) -> np.ndarray:
    """
    Kabut: blend gambar dengan layer putih.
    intensity=0 → tidak ada kabut, intensity=100 → kabut tebal (alpha 0.85)
    """
    fog   = np.ones_like(img, dtype=np.uint8) * 255
    alpha = (intensity / 100.0) * 0.85          # 0.0 – 0.85
    return cv2.addWeighted(img, 1.0 - alpha, fog, alpha, 0)


def weather_rain(img: np.ndarray, intensity: int, angle: int = 20) -> np.ndarray:
    """
    Hujan: gambar garis-garis diagonal tipis putih kebiruan.
    intensity=0 → tidak ada tetes, intensity=100 → 800 tetes deras
    angle: sudut kemiringan hujan (0=vertikal, 20=angin ringan)
    Juga menambahkan sedikit kabut basah sebanding intensitas.
    """
    if intensity == 0:
        return img.copy()

    out     = img.copy()
    h, w    = out.shape[:2]
    n_drops = int((intensity / 100.0) * 800)
    rng     = np.random.default_rng(0)          # seed tetap agar konsisten

    xs1 = rng.integers(0, w, n_drops)
    ys1 = rng.integers(0, h, n_drops)
    lens = rng.integers(10, 28, n_drops)

    rad = np.radians(angle)
    overlay = out.copy()
    for x1, y1, ln in zip(xs1, ys1, lens):
        x2 = int(min(w - 1, x1 + ln * np.sin(rad)))
        y2 = int(min(h - 1, y1 + ln * np.cos(rad)))
        cv2.line(overlay, (x1, y1), (x2, y2), (210, 215, 230), 1, cv2.LINE_AA)
    cv2.addWeighted(overlay, 0.6, out, 0.4, 0, out)

    # Wet-atmosphere fog ringan sebanding intensitas
    fog_alpha = (intensity / 100.0) * 0.20
    fog_layer = np.ones_like(img, dtype=np.uint8) * np.array([200, 210, 220], dtype=np.uint8)
    return cv2.addWeighted(out, 1 - fog_alpha, fog_layer, fog_alpha, 0)


def weather_snow(img: np.ndarray, intensity: int) -> np.ndarray:
    """
    Salju: titik-titik putih bundar + tint biru dingin.
    intensity=0 → tidak ada salju, intensity=100 → 700 keping salju
    """
    if intensity == 0:
        return img.copy()

    out  = img.copy()
    h, w = out.shape[:2]
    n    = int((intensity / 100.0) * 700)
    rng  = np.random.default_rng(1)

    xs    = rng.integers(0, w, n)
    ys    = rng.integers(0, h, n)
    sizes = rng.integers(1, 5, n)
    alphas = 0.6 + rng.random(n) * 0.4

    for x, y, s, a in zip(xs, ys, sizes, alphas):
        overlay = out.copy()
        cv2.circle(overlay, (int(x), int(y)), int(s), (255, 255, 255), -1, cv2.LINE_AA)
        cv2.addWeighted(overlay, a, out, 1 - a, 0, out)

    # Tint biru-putih dingin
    cold   = np.ones_like(img, dtype=np.uint8) * np.array([240, 248, 255], dtype=np.uint8)
    ca     = (intensity / 100.0) * 0.28
    return cv2.addWeighted(out, 1 - ca, cold, ca, 0)


def weather_drought(img: np.ndarray, intensity: int) -> np.ndarray:
    """
    Kemarau: tint oranye-coklat panas + gamma gelap + sedikit noise debu.
    intensity=0 → normal, intensity=100 → terik panas ekstrem
    """
    if intensity == 0:
        return img.copy()

    # Tint panas (BGR: lebih biru berkurang, merah bertambah)
    hot   = np.ones_like(img, dtype=np.uint8) * np.array([20, 80, 200], dtype=np.uint8)
    ta    = (intensity / 100.0) * 0.50
    result = cv2.addWeighted(img, 1 - ta, hot, ta, 0)

    # Gamma correction → buat lebih terang/overexposed
    gamma = 1.0 + (intensity / 100.0) * 0.9
    inv   = 1.0 / gamma
    lut   = np.array([min(255, int(((i / 255.0) ** inv) * 255))
                      for i in range(256)], dtype=np.uint8)
    result = cv2.LUT(result, lut)

    # Noise debu halus
    rng  = np.random.default_rng(2)
    dust = rng.integers(0, int(intensity * 0.3) + 1,
                        result.shape, dtype=np.uint8)
    return cv2.add(result, dust.astype(np.uint8))



# Daftar filter cuaca: (key, label, emoji, fungsi)
WEATHER_FILTERS = [
    ("fog",     "Kabut",   "🌫",  weather_fog),
    ("rain",    "Hujan",   "🌧",  weather_rain),
    ("snow",    "Salju",   "❄",  weather_snow),
    ("drought", "Kemarau", "☀",  weather_drought)
]


# ═══════════════════════════════════════════════════════════════════════════════
#  UI HELPERS (sama seperti v3)
# ═══════════════════════════════════════════════════════════════════════════════

class SectionFrame(tb.Frame):
    def __init__(self, parent, title="", **kwargs):
        super().__init__(parent, bootstyle="dark", padding=(10, 8), **kwargs)
        self.configure(style="Card.TFrame")
        if title:
            tb.Label(self, text=title.upper(), font=("Segoe UI", 7, "bold"),
                     foreground=TEXT_SEC, bootstyle="secondary").pack(anchor="w", pady=(0, 6))

    def pack(self, **kw):
        kw.setdefault("fill", "x"); kw.setdefault("pady", 6)
        super().pack(**kw)


class SliderRow(tb.Frame):
    def __init__(self, parent, label, variable, from_, to, command, fmt="{:.0f}", **kw):
        super().__init__(parent, bootstyle="dark")
        self._var = variable; self._fmt = fmt; self._cmd = command
        tb.Label(self, text=label, width=11, anchor="w", font=("Segoe UI", 9),
                 foreground=TEXT_PRI, bootstyle="inverse-dark").pack(side="left")
        tb.Scale(self, from_=from_, to=to, variable=variable,
                 bootstyle="info", command=self._on_change
                 ).pack(side="left", fill="x", expand=True, padx=(4, 6))
        self._badge = tb.Label(self, text=self._fmt.format(variable.get()),
                               width=5, anchor="e", font=("Consolas", 9),
                               foreground=ACCENT2, bootstyle="inverse-dark")
        self._badge.pack(side="left")
        self._min = from_
        self._max = to

        self._entry_var = tk.StringVar(value=str(variable.get()))

        self._entry = tb.Entry(
            self,
            textvariable=self._entry_var,
            width=7
        )
        self._entry.pack(side="left", padx=(4, 0))

        self._entry.bind("<Return>", self._entry_changed)
        self._entry.bind("<FocusOut>", self._entry_changed)

    def _on_change(self, _=None):
        value = self._var.get()

        self._badge.configure(text=self._fmt.format(value))
        self._entry_var.set(str(round(value, 2)))

        if self._cmd:
            self._cmd()

    def _entry_changed(self, event=None):
        try:
            value = float(self._entry_var.get())
        except ValueError:
            value = self._var.get()

        # Clamp ke batas minimum dan maksimum
        value = max(self._min, min(self._max, value))

        self._var.set(value)

        self._badge.configure(text=self._fmt.format(value))
        self._entry_var.set(str(round(value, 2)))

        if self._cmd:
            self._cmd()

    def pack(self, **kw):
        kw.setdefault("fill", "x"); kw.setdefault("pady", 3)
        super().pack(**kw)


class DarkSaveDialog(tk.Toplevel):
    def __init__(self, parent, default_name="output"):
        super().__init__(parent)
        self.title("Save Result")
        self.configure(bg=BG_PANEL)
        self.resizable(False, False)
        self.grab_set()
        self.result_path = None
        self._default = default_name
        self._build()
        self.transient(parent)
        self.update_idletasks()
        px = parent.winfo_rootx() + parent.winfo_width()  // 2 - self.winfo_width()  // 2
        py = parent.winfo_rooty() + parent.winfo_height() // 2 - self.winfo_height() // 2
        self.geometry(f"+{px}+{py}")
        self.deiconify()
        self.focus_force()
        self.wait_window()

    def _build(self):
        pad = dict(padx=16, pady=6)
        tk.Label(self, text="Save Processed Image", bg=BG_PANEL, fg=ACCENT,
                 font=("Segoe UI", 11, "bold")).pack(**pad, pady=(14, 4))
        tk.Label(self, text="File name", bg=BG_PANEL, fg=TEXT_SEC,
                 font=("Segoe UI", 8)).pack(anchor="w", padx=16)
        name_row = tk.Frame(self, bg=BG_PANEL)
        name_row.pack(fill="x", padx=16, pady=(2, 8))
        self._name_var = tk.StringVar(value=self._default)
        e = tk.Entry(name_row, textvariable=self._name_var,
                     bg=BG_CARD, fg=TEXT_PRI, insertbackground=ACCENT,
                     font=("Segoe UI", 10), relief="flat",
                     highlightbackground=BORDER, highlightthickness=1, width=28)
        e.pack(side="left", ipady=4); e.select_range(0, "end"); e.focus_set()
        tk.Label(self, text="Format", bg=BG_PANEL, fg=TEXT_SEC,
                 font=("Segoe UI", 8)).pack(anchor="w", padx=16)
        fmt_row = tk.Frame(self, bg=BG_PANEL)
        fmt_row.pack(fill="x", padx=16, pady=(2, 12))
        self._fmt_var = tk.StringVar(value=".png")
        for ext in (".png", ".jpg", ".bmp"):
            tk.Radiobutton(fmt_row, text=ext, variable=self._fmt_var, value=ext,
                           bg=BG_PANEL, fg=TEXT_PRI, selectcolor=BG_CARD,
                           activebackground=BG_PANEL, activeforeground=ACCENT,
                           font=("Segoe UI", 9)).pack(side="left", padx=(0, 12))
        tk.Label(self, text="Destination folder", bg=BG_PANEL, fg=TEXT_SEC,
                 font=("Segoe UI", 8)).pack(anchor="w", padx=16)
        folder_row = tk.Frame(self, bg=BG_PANEL)
        folder_row.pack(fill="x", padx=16, pady=(2, 14))
        self._folder_var = tk.StringVar(value=os.path.expanduser("~"))
        fe = tk.Entry(folder_row, textvariable=self._folder_var,
                      bg=BG_CARD, fg=TEXT_PRI, insertbackground=ACCENT,
                      font=("Segoe UI", 9), relief="flat",
                      highlightbackground=BORDER, highlightthickness=1, width=24)
        fe.pack(side="left", ipady=4, padx=(0, 6))
        tk.Button(folder_row, text="Browse…", bg=BG_CARD, fg=TEXT_PRI,
                  activebackground=ACCENT, activeforeground="#fff",
                  relief="flat", font=("Segoe UI", 8),
                  command=self._browse).pack(side="left", ipady=4)
        tk.Frame(self, bg=BORDER, height=1).pack(fill="x", padx=16, pady=(0, 10))
        btn_row = tk.Frame(self, bg=BG_PANEL)
        btn_row.pack(fill="x", padx=16, pady=(0, 14))
        tk.Button(btn_row, text="Cancel", bg=BG_CARD, fg=TEXT_SEC,
                  activebackground=BORDER, relief="flat",
                  font=("Segoe UI", 9), command=self.destroy,
                  width=10).pack(side="right", padx=(6, 0), ipady=4)
        tk.Button(btn_row, text="Save", bg=ACCENT, fg="#fff",
                  activebackground="#9d8eff", relief="flat",
                  font=("Segoe UI", 9, "bold"), command=self._save,
                  width=10).pack(side="right", ipady=4)
        self.bind("<Return>", lambda _: self._save())
        self.bind("<Escape>", lambda _: self.destroy())

    def _browse(self):
        d = filedialog.askdirectory(initialdir=self._folder_var.get())
        if d: self._folder_var.set(d)

    def _save(self):
        name = self._name_var.get().strip()
        folder = self._folder_var.get().strip()
        ext = self._fmt_var.get()
        if not name:
            messagebox.showwarning("Missing name", "Enter a file name.", parent=self)
            return
        if not name.endswith(ext): name += ext
        self.result_path = os.path.join(folder, name)
        self.destroy()


class DetailWindow(tk.Toplevel):
    def __init__(self, parent, img_bgr, title="Detail View"):
        super().__init__(parent)
        self.title(title)
        self.configure(bg=BG_CENTER)
        self.geometry("900x700")
        self._img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
        self._zoom = 1.0; self._off_x = 0; self._off_y = 0
        self._drag_start = None
        hdr = tk.Frame(self, bg=BG_PANEL); hdr.pack(fill="x")
        tk.Label(hdr, text=title, bg=BG_PANEL, fg=ACCENT,
                 font=("Segoe UI", 9, "bold")).pack(side="left", padx=10, pady=6)
        tk.Label(hdr, text="Scroll=zoom  Drag=pan  R=reset",
                 bg=BG_PANEL, fg=TEXT_SEC, font=("Segoe UI", 8)).pack(side="left")
        tk.Button(hdr, text="✕ Close", bg=BG_PANEL, fg=TEXT_SEC,
                  relief="flat", command=self.destroy).pack(side="right", padx=8)
        self._canvas = tk.Canvas(self, bg=BG_CENTER, cursor="fleur",
                                 highlightthickness=0)
        self._canvas.pack(fill="both", expand=True)
        self._canvas.bind("<MouseWheel>",    self._on_scroll)
        self._canvas.bind("<Button-4>",      self._on_scroll)
        self._canvas.bind("<Button-5>",      self._on_scroll)
        self._canvas.bind("<ButtonPress-1>", self._on_drag_start)
        self._canvas.bind("<B1-Motion>",     self._on_drag)
        self._canvas.bind("<Configure>",     lambda _: self._draw())
        self.bind("<r>", lambda _: self._reset())

    def _reset(self):
        self._zoom = 1.0; self._off_x = 0; self._off_y = 0; self._draw()

    def _on_scroll(self, e):
        delta = getattr(e, "delta", 0) or (120 if e.num == 4 else -120)
        self._zoom = max(0.1, min(10.0, self._zoom * (1.1 if delta > 0 else 0.9)))
        self._draw()

    def _on_drag_start(self, e): self._drag_start = (e.x, e.y)

    def _on_drag(self, e):
        if self._drag_start:
            self._off_x += e.x - self._drag_start[0]
            self._off_y += e.y - self._drag_start[1]
            self._drag_start = (e.x, e.y); self._draw()

    def _draw(self):
        cw = self._canvas.winfo_width() or 800
        ch = self._canvas.winfo_height() or 600
        h, w = self._img_rgb.shape[:2]
        nw, nh = max(1, int(w * self._zoom)), max(1, int(h * self._zoom))
        resized = cv2.resize(self._img_rgb, (nw, nh), interpolation=cv2.INTER_LINEAR)
        photo = ImageTk.PhotoImage(Image.fromarray(resized))
        self._canvas.delete("all")
        self._canvas.create_image(cw//2 + self._off_x, ch//2 + self._off_y,
                                  anchor="center", image=photo)
        self._canvas.image = photo
        self._canvas.create_text(cw-8, ch-8, anchor="se",
                                 text=f"{self._zoom*100:.0f}%",
                                 fill=ACCENT2, font=("Consolas", 9))


class CompareCanvas(tk.Frame):
    def __init__(self, parent, **kw):
        super().__init__(parent, bg=BG_CENTER, **kw)
        self._orig = None; self._proc = None; self._split = 0.5; self._dragging = False
        self._canvas = tk.Canvas(self, bg=BG_CENTER, cursor="sb_h_double_arrow",
                                 highlightthickness=0)
        self._canvas.pack(fill="both", expand=True)
        self._canvas.bind("<Configure>",     lambda _: self._draw())
        self._canvas.bind("<ButtonPress-1>", self._on_press)
        self._canvas.bind("<B1-Motion>",     self._on_drag)

    def set_images(self, orig_bgr, proc_bgr):
        self._orig = cv2.cvtColor(orig_bgr, cv2.COLOR_BGR2RGB)
        self._proc = cv2.cvtColor(proc_bgr, cv2.COLOR_BGR2RGB)
        self._draw()

    def _on_press(self, e):
        self._dragging = abs(e.x - int(self._split * self._canvas.winfo_width())) < 20

    def _on_drag(self, e):
        if self._dragging:
            self._split = max(0.05, min(0.95, e.x / max(1, self._canvas.winfo_width())))
            self._draw()

    def _draw(self):
        if self._orig is None: return
        cw = self._canvas.winfo_width() or 800
        ch = self._canvas.winfo_height() or 500
        sx = int(self._split * cw)
        h, w = self._orig.shape[:2]
        scale = ch / h
        nw, nh = max(1, int(w * scale)), max(1, int(h * scale))
        orig_r = cv2.resize(self._orig, (nw, nh), interpolation=cv2.INTER_AREA)
        proc_r = cv2.resize(self._proc, (nw, nh), interpolation=cv2.INTER_AREA)
        canvas_img = np.zeros((ch, cw, 3), dtype=np.uint8)
        ox = (cw - nw) // 2
        for x in range(cw):
            ix = x - ox
            if 0 <= ix < nw:
                canvas_img[:, x] = orig_r[:, ix] if x <= sx else proc_r[:, ix]
        photo = ImageTk.PhotoImage(Image.fromarray(canvas_img))
        self._canvas.delete("all")
        self._canvas.create_image(0, 0, anchor="nw", image=photo)
        self._canvas.image = photo
        self._canvas.create_line(sx, 0, sx, ch, fill=ACCENT, width=2)
        self._canvas.create_text(max(sx-8, 60), 14, anchor="e",
                                 text="ORIGINAL", fill=TEXT_SEC,
                                 font=("Segoe UI", 8, "bold"))
        self._canvas.create_text(min(sx+8, cw-60), 14, anchor="w",
                                 text="PROCESSED", fill=ACCENT2,
                                 font=("Segoe UI", 8, "bold"))
        self._canvas.create_oval(sx-10, ch//2-10, sx+10, ch//2+10, fill=ACCENT, outline="")
        self._canvas.create_text(sx, ch//2, text="⇔", fill="#fff",
                                 font=("Segoe UI", 10, "bold"))


# ═══════════════════════════════════════════════════════════════════════════════
#  MAIN APPLICATION
# ═══════════════════════════════════════════════════════════════════════════════

class App:
    def __init__(self, root):
        self.root = root
        self.root.title("AI Image Enhancement & Analysis Studio")
        self.root.configure(bg=BG_CENTER)
        try: self.root.state("zoomed")
        except Exception: self.root.attributes("-fullscreen", True)

        self.original   = None
        self.processed  = None
        self._view_mode = MODE_SPLIT
        self._stem      = "output"

        # ── Enhancement vars
        self.brightness = tk.IntVar(value=0)
        self.contrast   = tk.DoubleVar(value=1.0)
        self.clahe_var  = tk.IntVar(value=0)
        self.laplacian_var = tk.IntVar(value=0)
        self._noise_var = tk.IntVar(value=0)

        # ── Weather vars: satu IntVar per filter (0 = off)
        self._weather_vars = {key: tk.IntVar(value=0)
                              for key, *_ in WEATHER_FILTERS}
        # Track tombol aktif (hanya satu weather aktif sekaligus)
        self._active_weather = None
        self._weather_btns   = {}

        self._build_styles()
        self._build_ui()

    def _build_styles(self):
        s = tb.Style()
        s.configure("Card.TFrame",    background=BG_CARD,   relief="flat")
        s.configure("Sidebar.TFrame", background=BG_PANEL)
        s.configure("Canvas.TFrame",  background=BG_CENTER)

    # ── UI Build ──────────────────────────────────────────────────────────────

    def _build_ui(self):
        self.root.columnconfigure(1, weight=1)
        self.root.rowconfigure(0, weight=1)

        left = tb.Frame(self.root, padding=(10, 12), width=230, style="Sidebar.TFrame")
        left.grid(row=0, column=0, sticky="nsew"); left.grid_propagate(False)
        self._build_left(left)

        center = tb.Frame(self.root, style="Canvas.TFrame", padding=8)
        center.grid(row=0, column=1, sticky="nsew")
        self._build_center(center)

        right = tb.Frame(self.root, padding=(10, 12), width=290, style="Sidebar.TFrame")
        right.grid(row=0, column=2, sticky="nsew"); right.grid_propagate(False)
        self._build_right(right)

        sb = tk.Frame(self.root, bg="#0d0d1a", height=26)
        sb.grid(row=1, column=0, columnspan=3, sticky="ew")
        self.status_res  = tk.Label(sb, text="No image loaded", bg="#0d0d1a",
                                    fg=TEXT_SEC, font=("Segoe UI", 8), padx=12)
        self.status_res.pack(side="left")
        self.status_file = tk.Label(sb, text="", bg="#0d0d1a", fg=ACCENT2,
                                    font=("Segoe UI", 8), padx=12)
        self.status_file.pack(side="right")

        self.root.bind("<Control-o>", lambda e: self.open_image())
        self.root.bind("<Control-s>", lambda e: self.save_image())
        self.root.bind("<F11>",       self.toggle_fullscreen)
        self.root.bind("<Escape>",    self.exit_fullscreen)

    def _build_left(self, p):
        tb.Label(p, text="✦ IMAGE STUDIO", font=("Segoe UI", 11, "bold"),
                 foreground=ACCENT, bootstyle="inverse-dark").pack(anchor="w", pady=(0, 14))

        # Actions
        sec = SectionFrame(p, title="Actions")
        for text, style, cmd, hint in [
            ("Open Image",  PRIMARY, self.open_image,  "Ctrl+O"),
            ("Save Result", SUCCESS, self.save_image,  "Ctrl+S"),
            ("Reset",       WARNING, self.reset,       ""),
            ("Auto Detect", INFO,    self.auto_detect, ""),
        ]:
            row = tb.Frame(sec, bootstyle="dark"); row.pack(fill="x", pady=2)
            tb.Button(row, text=text, bootstyle=style,
                      command=cmd, width=14).pack(side="left")
            if hint:
                tb.Label(row, text=hint, font=("Segoe UI", 7),
                         foreground=TEXT_SEC, bootstyle="inverse-dark").pack(side="left", padx=6)
        sec.pack()

        # Adjustments
        sec2 = SectionFrame(p, title="Adjustments")
        SliderRow(sec2, "Brightness", self.brightness,   -100, 100, self.update_all, "{:+.0f}").pack()
        SliderRow(sec2, "Contrast",   self.contrast,      0.5, 3.0, self.update_all, "{:.2f}").pack()
        SliderRow(sec2, "CLAHE",      self.clahe_var,       0, 100, self.update_all, "{:.0f}").pack()
        SliderRow(sec2, "Sharpening", self.laplacian_var,   0, 100, self.update_all, "{:.0f}").pack()
        SliderRow(sec2, "Noise Reduction", self._noise_var, 0, 10, self.update_all, "{:.0f}").pack()
        sec2.pack()

        # ── Weather Filters ───────────────────────────────────────────────
        sec3 = SectionFrame(p, title="Weather Filters")

        # Info kecil
        tk.Label(sec3, text="Click to select  •  slider = intensity",
                 bg=BG_CARD, fg=TEXT_SEC, font=("Segoe UI", 7)).pack(anchor="w", pady=(0, 6))

        # Grid tombol 2 kolom
        btn_grid = tk.Frame(sec3, bg=BG_CARD)
        btn_grid.pack(fill="x")
        btn_grid.columnconfigure(0, weight=1)
        btn_grid.columnconfigure(1, weight=1)

        for i, (key, label, emoji, _fn) in enumerate(WEATHER_FILTERS):
            col = i % 2
            row = i // 2
            btn = tk.Button(
                btn_grid,
                text=f"{emoji}  {label}",
                bg=BG_PANEL, fg=TEXT_PRI,
                activebackground=ACCENT, activeforeground="#fff",
                relief="flat", font=("Segoe UI", 9),
                padx=6, pady=5,
                command=lambda k=key: self._toggle_weather(k)
            )
            btn.grid(row=row, column=col, sticky="ew", padx=2, pady=2)
            self._weather_btns[key] = btn

        # Slider intensitas cuaca (muncul di bawah grid)
        tk.Frame(sec3, bg=BORDER, height=1).pack(fill="x", pady=(8, 4))
        self._weather_intensity_label = tk.Label(
            sec3, text="Intensitas Cuaca", bg=BG_CARD, fg=TEXT_SEC,
            font=("Segoe UI", 8))
        self._weather_intensity_label.pack(anchor="w")

        self._weather_intensity_var = tk.IntVar(value=50)
        self._weather_slider_row = SliderRow(
            sec3, "Intensitas", self._weather_intensity_var,
            0, 100, self._on_weather_slider, "{:.0f}")
        self._weather_slider_row.pack()

        # Tombol clear cuaca
        tk.Button(sec3, text="✕  Clear Weather", bg=BG_CARD, fg=TEXT_SEC,
                  activebackground="#c0392b", activeforeground="#fff",
                  relief="flat", font=("Segoe UI", 8),
                  command=self._clear_weather).pack(fill="x", pady=(4, 0))
        sec3.pack()

        # View mode
        sec4 = SectionFrame(p, title="View Mode")
        self._mode_var = tk.StringVar(value=MODE_SPLIT)
        for label, mode in [("Split (side-by-side)", MODE_SPLIT),
                             ("Compare (drag slider)", MODE_COMPARE),
                             ("Detail / Zoom", MODE_DETAIL)]:
            tk.Radiobutton(sec4, text=label, variable=self._mode_var, value=mode,
                           command=self._switch_view,
                           bg=BG_CARD, fg=TEXT_PRI, selectcolor=BG_PANEL,
                           activebackground=BG_CARD, activeforeground=ACCENT,
                           font=("Segoe UI", 9)).pack(anchor="w", pady=2)
        sec4.pack()

    def _build_center(self, p):
        p.columnconfigure(0, weight=1); p.rowconfigure(1, weight=1)
        self._tab_bar = tk.Frame(p, bg=BG_PANEL)
        self._tab_bar.grid(row=0, column=0, sticky="ew", pady=(0, 6))
        self._tab_labels = {}
        for label, mode in [("Split", MODE_SPLIT), ("Compare", MODE_COMPARE), ("Detail", MODE_DETAIL)]:
            btn = tk.Button(self._tab_bar, text=label,
                            bg=BG_PANEL, fg=TEXT_SEC,
                            activebackground=ACCENT, activeforeground="#fff",
                            relief="flat", font=("Segoe UI", 9), padx=14, pady=4,
                            command=lambda m=mode: self._set_mode(m))
            btn.pack(side="left", padx=2, pady=4)
            self._tab_labels[mode] = btn

        self._view_container = tk.Frame(p, bg=BG_CENTER)
        self._view_container.grid(row=1, column=0, sticky="nsew")
        self._view_container.columnconfigure(0, weight=1)
        self._view_container.columnconfigure(1, weight=1)
        self._view_container.rowconfigure(1, weight=1)

        self._split_frame = tk.Frame(self._view_container, bg=BG_CENTER)
        self._split_frame.grid(row=0, column=0, columnspan=2, sticky="nsew", rowspan=2)
        self._split_frame.columnconfigure(0, weight=1)
        self._split_frame.columnconfigure(1, weight=1)
        self._split_frame.rowconfigure(1, weight=1)

        for col, title in enumerate(("Original", "Processed")):
            hdr = tk.Frame(self._split_frame, bg=BG_CARD, height=28)
            hdr.grid(row=0, column=col, sticky="ew",
                     padx=(0,4) if col==0 else (4,0), pady=(0,4))
            tk.Label(hdr, text=title, bg=BG_CARD, fg=TEXT_SEC,
                     font=("Segoe UI", 8, "bold")).pack(pady=4)

        def make_panel(col):
            f = tk.Frame(self._split_frame, bg=BG_PANEL,
                         highlightbackground=BORDER, highlightthickness=1)
            f.grid(row=1, column=col, sticky="nsew",
                   padx=(0,4) if col==0 else (4,0))
            return f

        self._orig_frame = make_panel(0)
        self._proc_frame = make_panel(1)

        self.orig_label = tk.Label(self._orig_frame, bg=BG_PANEL,
                                   text="Open an image to begin",
                                   fg=TEXT_SEC, font=("Segoe UI", 10))
        self.orig_label.pack(expand=True, fill="both")
        self.proc_label = tk.Label(self._proc_frame, bg=BG_PANEL,
                                   text="Processed output",
                                   fg=TEXT_SEC, font=("Segoe UI", 10))
        self.proc_label.pack(expand=True, fill="both")

        for col, (lbl, which) in enumerate([("🔍 Detail: Original", "orig"),
                                             ("🔍 Detail: Processed", "proc")]):
            tk.Button(self._split_frame, text=lbl,
                      bg=BG_CARD, fg=TEXT_SEC,
                      activebackground=ACCENT, activeforeground="#fff",
                      relief="flat", font=("Segoe UI", 8),
                      command=lambda w=which: self._open_detail(w)
                      ).grid(row=2, column=col, sticky="ew",
                             padx=(0,4) if col==0 else (4,0), pady=(4,0))

        self._compare_frame = CompareCanvas(self._view_container)
        self._set_mode(MODE_SPLIT)

    def _build_right(self, p):
        tb.Label(p, text="ANALYSIS", font=("Segoe UI", 8, "bold"),
                 foreground=ACCENT, bootstyle="inverse-dark").pack(anchor="w", pady=(0, 6))
        wrap = tk.Frame(p, bg=BORDER, padx=1, pady=1); wrap.pack(fill="x")
        self.analysis = tk.Text(wrap, width=32, height=12,
                                bg=BG_CARD, fg=TEXT_PRI, font=("Consolas", 8),
                                insertbackground=ACCENT, relief="flat",
                                padx=8, pady=6, wrap="word")
        metrics_row = tb.Frame(self.analysis.master, bootstyle="dark")
        metrics_row.pack(fill="x", pady=(4, 0))
        self.lbl_psnr = tb.Label(metrics_row, text="PSNR  —",
                                font=("Consolas", 9), foreground=ACCENT2,
                                bootstyle="inverse-dark")
        self.lbl_psnr.pack(side="left", padx=(0, 16))
        self.lbl_ssim = tb.Label(metrics_row, text="SSIM  —",
                                font=("Consolas", 9), foreground=ACCENT2,
                                bootstyle="inverse-dark")
        self.lbl_ssim.pack(side="left")    
        self.analysis.pack(fill="x")
        self.analysis.insert("end", "Run 'Auto Detect' to analyze\nthe loaded image.\n")
        self.analysis.configure(state="disabled")

        tb.Label(p, text="RGB HISTOGRAM", font=("Segoe UI", 8, "bold"),
                 foreground=ACCENT, bootstyle="inverse-dark").pack(anchor="w", pady=(14, 4))
        hw = tk.Frame(p, bg=BORDER, padx=1, pady=1); hw.pack(fill="both", expand=True)
        fig = Figure(figsize=(3.2, 2.4), facecolor=BG_CARD)
        self.ax = fig.add_subplot(111)
        self.ax.set_facecolor(BG_PANEL)
        fig.tight_layout(pad=1.2)
        self.hist_canvas = FigureCanvasTkAgg(fig, master=hw)
        self.hist_canvas.get_tk_widget().configure(bg=BG_CARD, highlightthickness=0)
        self.hist_canvas.get_tk_widget().pack(fill="both", expand=True)

    # ── View mode ─────────────────────────────────────────────────────────────

    def _set_mode(self, mode):
        self._view_mode = mode; self._mode_var.set(mode)
        for m, btn in self._tab_labels.items():
            btn.configure(bg=ACCENT if m == mode else BG_PANEL,
                          fg="#fff" if m == mode else TEXT_SEC)
        if mode == MODE_COMPARE:
            self._split_frame.grid_remove()
            self._compare_frame.grid(row=0, column=0, columnspan=2,
                                     sticky="nsew", rowspan=2,
                                     in_=self._view_container)
            if self.original is not None and self.processed is not None:
                self._compare_frame.set_images(self.original, self.processed)
        elif mode == MODE_DETAIL:
            self._split_frame.grid_remove(); self._compare_frame.grid_remove()
            if self.original is not None:
                self._open_detail("orig"); self._open_detail("proc")
            else:
                messagebox.showinfo("No image", "Load an image first.")
            self._split_frame.grid(); self._set_mode(MODE_SPLIT); return
        else:
            self._compare_frame.grid_remove(); self._split_frame.grid()

    def _switch_view(self): self._set_mode(self._mode_var.get())

    def _open_detail(self, which):
        if self.original is None:
            messagebox.showinfo("No image", "Load an image first."); return
        img   = self.original if which == "orig" else self.processed
        title = "Detail — Original" if which == "orig" else "Detail — Processed"
        DetailWindow(self.root, img, title)

    # ── Weather control ───────────────────────────────────────────────────────

    def _toggle_weather(self, key):
        """Pilih satu filter cuaca; klik lagi = non-aktifkan."""
        if self._active_weather == key:
            # Klik tombol yang sama → matikan
            self._active_weather = None
            self._weather_vars[key].set(0)
            self._weather_btns[key].configure(bg=BG_PANEL, fg=TEXT_PRI)
        else:
            # Matikan tombol sebelumnya
            if self._active_weather:
                self._weather_btns[self._active_weather].configure(
                    bg=BG_PANEL, fg=TEXT_PRI)
                self._weather_vars[self._active_weather].set(0)
            # Aktifkan yang baru
            self._active_weather = key
            self._weather_vars[key].set(self._weather_intensity_var.get())
            self._weather_btns[key].configure(bg=ACCENT, fg="#fff")

        # Update label slider
        if self._active_weather:
            label = next(l for k, l, *_ in WEATHER_FILTERS if k == self._active_weather)
            self._weather_intensity_label.configure(
                text=f"Intensitas — {label}", fg=ACCENT2)
        else:
            self._weather_intensity_label.configure(
                text="Intensitas Cuaca", fg=TEXT_SEC)

        self.update_all()

    def _on_weather_slider(self):
        """Slider intensitas cuaca digeser."""
        if self._active_weather:
            self._weather_vars[self._active_weather].set(
                self._weather_intensity_var.get())
            self.update_all()

    def _clear_weather(self):
        if self._active_weather:
            self._weather_btns[self._active_weather].configure(
                bg=BG_PANEL, fg=TEXT_PRI)
            self._weather_vars[self._active_weather].set(0)
            self._active_weather = None
        self._weather_intensity_var.set(0)
        self._weather_intensity_label.configure(text="Intensitas Cuaca", fg=TEXT_SEC)
        self.update_all()

    # ── Image pipeline ────────────────────────────────────────────────────────

    def apply_pipeline(self):
        if self.original is None: return
        img = self.original.copy()

        # 1. Brightness & contrast
        img = cv2.convertScaleAbs(img,
                                alpha=self.contrast.get(),
                                beta=self.brightness.get())

        # 2. Noise Reduction DULU sebelum CLAHE
        # (noise di area gelap harus ditekan sebelum CLAHE memperkuatnya)
        # 2. Noise Reduction
        if self._noise_var.get() > 0:
            ksize = int(self._noise_var.get())
            ksize = ksize if ksize % 2 == 1 else ksize + 1
            ksize = max(3, min(ksize, 7))  # maksimal 7, bukan 11
            # Gaussian lebih aman untuk gambar dengan gradasi halus
            img = cv2.GaussianBlur(img, (ksize, ksize), 0)

        # 3. CLAHE
        if self.clahe_var.get() > 0:
            clip = 1 + self.clahe_var.get() / 100 * 7
            lab  = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
            l, a, b = cv2.split(lab)
            h_img, w_img = img.shape[:2]
            tile_h = max(8, h_img // 32)
            tile_w = max(8, w_img // 32)
            l = cv2.createCLAHE(clipLimit=clip, tileGridSize=(tile_w, tile_h)).apply(l)
            img = cv2.cvtColor(cv2.merge([l, a, b]), cv2.COLOR_LAB2BGR)

        # 4. Laplacian sharpening
        if self.laplacian_var.get() > 0:
            k        = 0.5 + self.laplacian_var.get() / 100 * 1.5
            blurred  = cv2.GaussianBlur(img, (3, 3), 0)
            # Unsharp masking: kurangkan versi blur dari asli = hanya detail/tepi
            detail   = cv2.subtract(img, blurred)          # hanya komponen tajam, selalu >= 0
            img      = cv2.addWeighted(img, 1.0, detail, k, 0)

        # 5. Weather filter
        if self._active_weather:
            fn_map = {k: fn for k, _l, _e, fn in WEATHER_FILTERS}
            fn     = fn_map[self._active_weather]
            iv     = self._weather_intensity_var.get()
            img    = fn(img, iv)

        self.processed = img

    def open_image(self):
        path = filedialog.askopenfilename(
            filetypes=[("Images", "*.png *.jpg *.jpeg *.bmp *.tiff")])
        if not path: return
        self.original  = cv2.imread(path)
        self.processed = self.original.copy()
        self._stem     = os.path.splitext(os.path.basename(path))[0]
        self.refresh()
        self.status_file.configure(text=os.path.basename(path))

    def save_image(self):
        if self.processed is None:
            messagebox.showwarning("No image", "Load an image first."); return

        choice_var = tk.StringVar(value="1")
        confirmed  = [False]

        popup = tk.Toplevel(self.root)
        popup.title("Save Mode")
        popup.configure(bg=BG_PANEL)
        popup.geometry("300x160")
        popup.resizable(False, False)
        popup.transient(self.root)
        popup.grab_set()
        popup.deiconify()
        popup.focus_force()

        tk.Label(popup, text="Pilih mode simpan:",
                bg=BG_PANEL, fg=TEXT_PRI, font=("Segoe UI", 10)).pack(pady=(16, 8))
        tk.Radiobutton(popup, text="Hasil saja",
                    variable=choice_var, value="1",
                    bg=BG_PANEL, fg=TEXT_PRI, selectcolor=BG_CARD).pack(anchor="w", padx=40)
        tk.Radiobutton(popup, text="Side-by-side (original + hasil)",
                    variable=choice_var, value="2",
                    bg=BG_PANEL, fg=TEXT_PRI, selectcolor=BG_CARD).pack(anchor="w", padx=40)

        def confirm():
            confirmed[0] = True
            popup.destroy()

        tk.Button(popup, text="OK", command=confirm,
                bg=ACCENT, fg="#fff", width=10,
                relief="flat").pack(pady=12)

        popup.wait_window()
        if not confirmed[0]: return

        # Gunakan dialog native OS — tidak ada wait_window kedua
        default = self._stem + "_processed"
        if self._active_weather:
            default += f"_{self._active_weather}"
        if choice_var.get() == "2":
            default += "_comparison"

        path = filedialog.asksaveasfilename(
            initialfile=default,
            defaultextension=".png",
            filetypes=[("PNG", "*.png"), ("JPEG", "*.jpg"), ("BMP", "*.bmp")],
            title="Save Result"
        )
        if not path: return

        if choice_var.get() == "2":
            h        = max(self.original.shape[0], self.processed.shape[0])
            orig_rs  = cv2.resize(self.original,  (int(self.original.shape[1]  * h / self.original.shape[0]),  h))
            proc_rs  = cv2.resize(self.processed, (int(self.processed.shape[1] * h / self.processed.shape[0]), h))
            divider  = np.ones((h, 3, 3), dtype=np.uint8) * 200
            combined = np.hstack([orig_rs, divider, proc_rs])
            cv2.imwrite(path, combined)
        else:
            cv2.imwrite(path, self.processed)

        messagebox.showinfo("Saved", f"Saved to:\n{path}")

    def reset(self):
        if self.original is None: return
        self.brightness.set(0); self.contrast.set(1.0)
        self.clahe_var.set(0);  self.laplacian_var.set(0)
        self._clear_weather()
        self.processed = self.original.copy()
        self.refresh()

    def auto_detect(self):
        if self.original is None:
            messagebox.showwarning("No image", "Load an image first."); return

        gray       = cv2.cvtColor(self.original, cv2.COLOR_BGR2GRAY)
        brightness = np.mean(gray)
        blur_score = cv2.Laplacian(gray, cv2.CV_64F).var()
        noise      = np.std(gray)

        lines = ["IMAGE ANALYSIS REPORT", "─" * 30,
                f"Brightness   {brightness:>8.2f}",
                f"Blur Score   {blur_score:>8.2f}",
                f"Noise Level  {noise:>8.2f}", "─" * 30]

        actions = []

        # Reset semua dulu
        self.clahe_var.set(0)
        self.laplacian_var.set(0)
        self._noise_var.set(0)
        self.brightness.set(0)
        self.contrast.set(1.0)

        # Gambar sangat gelap — noise reduction dulu, baru CLAHE kuat
        if brightness < 50:
            self._noise_var.set(5)
            self.clahe_var.set(95)
            self.laplacian_var.set(60)
            actions.append("Very dark → Noise reduction + CLAHE kuat + Sharpening")

        # Gambar gelap biasa
        elif brightness < 85:
            self._noise_var.set(3)
            self.clahe_var.set(80)
            self.laplacian_var.set(50)
            actions.append("Low-light → Noise reduction ringan + CLAHE + Sharpening")

        # Gambar overexposed
        elif brightness > 200:
            self.brightness.set(-40)
            self.contrast.set(0.8)
            actions.append("Overexposed → Brightness & contrast diturunkan")

        # Gambar normal tapi blur
        elif blur_score < 120:
            self.laplacian_var.set(80)
            actions.append("Blur → Sharpening diterapkan")

        # Noise tinggi pada gambar terang
        if noise > 60 and brightness > 85:
            self._noise_var.set(5)
            actions.append("Noise tinggi → Noise reduction diterapkan")

        if not actions:
            actions.append("Normal → Tidak ada penyesuaian")

        lines += ["Tindakan:"]
        lines += [f"  • {a}" for a in actions]

        self.analysis.configure(state="normal")
        self.analysis.delete("1.0", "end")
        self.analysis.insert("end", "\n".join(lines))
        self.analysis.configure(state="disabled")
        self.update_all()

    def update_metrics(self):
        if self.original is None or self.processed is None: return
        try:
            orig_rgb = cv2.cvtColor(self.original,   cv2.COLOR_BGR2RGB)
            proc_rgb = cv2.cvtColor(self.processed,  cv2.COLOR_BGR2RGB)
            psnr_val = psnr(orig_rgb, proc_rgb, data_range=255)
            ssim_val = ssim(orig_rgb, proc_rgb, channel_axis=2, data_range=255)
            self.lbl_psnr.configure(text=f"PSNR  {psnr_val:>6.2f} dB")
            self.lbl_ssim.configure(text=f"SSIM  {ssim_val:>6.4f}")
        except Exception:
            self.lbl_psnr.configure(text="PSNR  —")
            self.lbl_ssim.configure(text="SSIM  —")

    def update_histogram(self):
        if self.processed is None: return
        self.ax.clear(); self.ax.set_facecolor(BG_PANEL)
        rgb = cv2.cvtColor(self.processed, cv2.COLOR_BGR2RGB)
        for i, color in enumerate(("#ff6b6b","#6bcb77","#4d96ff")):
            hist = cv2.calcHist([rgb],[i],None,[256],[0,256])
            self.ax.fill_between(range(256), hist.flatten(), alpha=0.35, color=color)
            self.ax.plot(hist, color=color, linewidth=0.8)
        self.ax.set_xlim(0,255)
        self.ax.tick_params(colors=TEXT_SEC, labelsize=6)
        for sp in self.ax.spines.values(): sp.set_edgecolor(BORDER)
        self.hist_canvas.draw()

    def update_all(self):
        if self.original is None: return
        self.apply_pipeline(); self.refresh()

    def show_image(self, label, img):
        rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        h, w = rgb.shape[:2]
        label.update_idletasks()
        lw = label.winfo_width()  or 600
        lh = label.winfo_height() or 500
        scale = min(lw/w, lh/h, 1.0)
        nw, nh = max(1, int(w*scale)), max(1, int(h*scale))
        rgb   = cv2.resize(rgb, (nw, nh), interpolation=cv2.INTER_AREA)
        photo = ImageTk.PhotoImage(Image.fromarray(rgb))
        label.configure(image=photo, text="")
        label.image = photo

    def refresh(self):
        if self.original is None: return
        self.show_image(self.orig_label, self.original)
        self.show_image(self.proc_label, self.processed)
        self.update_histogram()
        self.update_metrics()
        if self._view_mode == MODE_COMPARE:
            self._compare_frame.set_images(self.original, self.processed)
        h, w = self.original.shape[:2]
        self.status_res.configure(text=f"Resolution: {w} × {h} px")

    def toggle_fullscreen(self, _=None):
        self.root.attributes("-fullscreen", not self.root.attributes("-fullscreen"))

    def exit_fullscreen(self, _=None):
        self.root.attributes("-fullscreen", False)


if __name__ == "__main__":
    root = tb.Window(themename="darkly")
    root.minsize(960, 620)
    App(root)
    root.mainloop()
