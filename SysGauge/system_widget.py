#!/usr/bin/env python3
"""
SysGauge — 桌面系统状态小组件 v3
· 拖动 / 固定模式切换
· 多屏幕四角吸附
· 系统托盘 — 关闭即最小化到托盘
· CPU · 内存 · GPU · 磁盘 C/D

依赖: psutil, pystray, Pillow
打包: pyinstaller --onefile --windowed --name SysGauge system_widget.py
"""

import tkinter as tk
import psutil
import subprocess
import os
import threading
import ctypes
from ctypes import wintypes

import pystray
from PIL import Image, ImageDraw

# ── 配色 ──────────────────────────────────────────
BG     = "#0d1117"
FG     = "#c9d1d9"
BAR_BG = "#21262d"
ACCENT = "#58a6ff"
WARN   = "#d2991d"
DANGER = "#f85149"
GREEN  = "#3fb950"
FOOTER = "#484f58"

W = 200

# ── Win32 多屏 ────────────────────────────────────
MONITOR_DEFAULTTONEAREST = 2

class RECT(ctypes.Structure):
    _fields_ = [("left", ctypes.c_long), ("top", ctypes.c_long),
                ("right", ctypes.c_long), ("bottom", ctypes.c_long)]

class MONITORINFO(ctypes.Structure):
    _fields_ = [("cbSize", ctypes.c_ulong), ("rcMonitor", RECT),
                ("rcWork", RECT), ("dwFlags", ctypes.c_ulong)]

def get_monitor_work(x, y):
    pt = wintypes.POINT(x, y)
    hmon = ctypes.windll.user32.MonitorFromPoint(pt, MONITOR_DEFAULTTONEAREST)
    info = MONITORINFO()
    info.cbSize = ctypes.sizeof(MONITORINFO)
    ctypes.windll.user32.GetMonitorInfoW(hmon, ctypes.byref(info))
    return info.rcWork.left, info.rcWork.top, info.rcWork.right, info.rcWork.bottom


# ── GPU ───────────────────────────────────────────
def get_gpu_usage():
    try:
        out = subprocess.run(
            ["nvidia-smi", "--query-gpu=utilization.gpu", "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=3,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
        )
        if out.returncode == 0 and out.stdout.strip():
            return float(out.stdout.strip().split("\n")[0])
    except Exception:
        pass
    try:
        import pynvml
        pynvml.nvmlInit()
        h = pynvml.nvmlDeviceGetHandleByIndex(0)
        u = pynvml.nvmlDeviceGetUtilizationRates(h)
        pynvml.nvmlShutdown()
        return float(u.gpu)
    except Exception:
        pass
    return None


def color_for(val):
    if val >= 90: return DANGER
    if val >= 70: return WARN
    return GREEN


# ── 托盘图标生成 ──────────────────────────────────
def _make_tray_icon(pct=50):
    """生成 32x32 彩色进度环图标"""
    img = Image.new("RGBA", (32, 32), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    # 外圈
    draw.ellipse((1, 1, 30, 30), outline="#58a6ff", width=2)
    # 填充弧（简易：画实心圆模拟）
    c = (13, 29, 18, 34)  # fallback
    draw.rectangle((7, 7, 24, 24), fill="#21262d")
    draw.ellipse((9, 9, 22, 22), fill="#58a6ff")
    return img


# ── 主类 ──────────────────────────────────────────
class SysGauge:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("SysGauge")
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        self.root.attributes("-alpha", 0.90)
        self.root.configure(bg=BG)

        self._drag_mode = True
        self._dx = self._dy = 0
        self._has_gpu = get_gpu_usage() is not None
        self._running = True

        self._build_ui()

        self.root.update_idletasks()
        h = self.root.winfo_reqheight()
        ml, mt, mr, mb = get_monitor_work(W // 2, h // 2)
        self.root.geometry(f"{W}x{h}+{mr - W - 12}+{mt + 20}")

        self._bind_drag()
        self._build_menu()

        # 托盘
        self._tray = None
        self._start_tray()

        self._update_loop()

        # 窗口关闭协议 → 最小化到托盘
        self.root.protocol("WM_DELETE_WINDOW", self._hide_to_tray)

    # ─── UI ────────────────────────────────────────

    def _build_ui(self):
        title = tk.Frame(self.root, bg=BG)
        title.pack(fill=tk.X, padx=8, pady=(6, 1))

        self._mode_lbl = tk.Label(title, text="🖥 SysGauge", bg=BG, fg=FG,
                                  font=("Segoe UI", 9, "bold"))
        self._mode_lbl.pack(side=tk.LEFT)

        cls = tk.Label(title, text="✕", bg=BG, fg=FOOTER,
                       font=("Segoe UI", 9), cursor="hand2")
        cls.pack(side=tk.RIGHT)
        cls.bind("<Button-1>", lambda e: self._on_close_click())
        cls.bind("<Enter>", lambda e: cls.configure(fg=DANGER))
        cls.bind("<Leave>", lambda e: cls.configure(fg=FOOTER))

        tk.Frame(self.root, bg=BAR_BG, height=1).pack(fill=tk.X, padx=8)

        self._bars = {}
        items = [("CPU %", "cpu"), ("RAM %", "mem")]
        if self._has_gpu:
            items.append(("GPU %", "gpu"))
        items.append(("C: %", "diskc"))
        if os.path.exists("D:"):
            items.append(("D: %", "diskd"))

        for name, key in items:
            self._bars[key] = self._make_bar(name)

        # 底部留白
        tk.Frame(self.root, bg=BG, height=6).pack(fill=tk.X)

    def _make_bar(self, name):
        f = tk.Frame(self.root, bg=BG)
        f.pack(fill=tk.X, padx=8, pady=(4, 0))
        row = tk.Frame(f, bg=BG)
        row.pack(fill=tk.X)
        tk.Label(row, text=name, bg=BG, fg=FG,
                 font=("Segoe UI", 9)).pack(side=tk.LEFT)
        lbl = tk.Label(row, text="--", bg=BG, fg=GREEN,
                       font=("Segoe UI", 9, "bold"))
        lbl.pack(side=tk.RIGHT)
        cv = tk.Canvas(f, height=5, bg=BAR_BG, highlightthickness=0, bd=0)
        cv.pack(fill=tk.X, pady=(1, 1))
        bar = cv.create_rectangle(0, 0, 0, 5, fill=GREEN, outline="")
        return {"canvas": cv, "label": lbl, "bar": bar}

    # ─── 菜单 ──────────────────────────────────────

    def _build_menu(self):
        self.menu = tk.Menu(self.root, tearoff=0, bg="#161b22", fg=FG,
                            activebackground=ACCENT, activeforeground="#fff",
                            font=("Segoe UI", 9))
        self._drag_var = tk.BooleanVar(value=True)
        self.menu.add_checkbutton(label="拖动模式", variable=self._drag_var,
                                  command=self._toggle_drag, selectcolor=BG)
        self._top_var = tk.BooleanVar(value=True)
        self.menu.add_checkbutton(label="置顶", variable=self._top_var,
                                  command=self._toggle_top, selectcolor=BG)
        self._pos_var = tk.StringVar(value="右上")
        pos_menu = tk.Menu(self.menu, tearoff=0, bg="#161b22", fg=FG,
                           font=("Segoe UI", 9))
        for c in ["左上", "右上", "左下", "右下"]:
            pos_menu.add_radiobutton(label=c, variable=self._pos_var,
                                     command=lambda v=c: self._snap_to_corner(v),
                                     selectcolor=BG)
        self.menu.add_cascade(label="固定位置", menu=pos_menu)
        alpha_menu = tk.Menu(self.menu, tearoff=0, bg="#161b22", fg=FG,
                             font=("Segoe UI", 9))
        for a, l in [(0.90, "90%"), (0.70, "70%"), (0.50, "50%")]:
            alpha_menu.add_command(label=l, command=lambda v=a: self._set_alpha(v))
        self.menu.add_cascade(label="透明度", menu=alpha_menu)
        self.menu.add_separator()
        self.menu.add_command(label="隐藏到托盘", command=self._hide_to_tray)

    # ─── 托盘 ──────────────────────────────────────

    def _start_tray(self):
        icon_img = _make_tray_icon()
        tray_menu = pystray.Menu(
            pystray.MenuItem("显示 SysGauge", self._restore_from_tray, default=True),
            pystray.MenuItem("退出", self._quit_app),
        )
        self._tray = pystray.Icon("SysGauge", icon_img, "SysGauge", tray_menu)
        t = threading.Thread(target=self._tray.run, daemon=True)
        t.start()

    def _on_close_click(self):
        """点 ✕ 弹出选择：退出 / 最小化到托盘 / 取消"""
        dlg = tk.Toplevel(self.root)
        dlg.title("SysGauge")
        dlg.geometry("260x160")
        dlg.resizable(False, False)
        dlg.configure(bg=BG)
        dlg.transient(self.root)
        dlg.grab_set()
        dlg.attributes("-topmost", True)

        # 定位在鼠标附近
        dlg.update_idletasks()
        mx = self.root.winfo_pointerx()
        my = self.root.winfo_pointery()
        dlg.geometry(f"+{mx - 130}+{my - 40}")

        # 外边框
        border = tk.Frame(dlg, bg=ACCENT)
        border.pack(fill="both", expand=True, padx=1, pady=1)
        inner = tk.Frame(border, bg=BG)
        inner.pack(fill="both", expand=True)

        tk.Label(inner, text="SysGauge", bg=BG, fg=FG,
                 font=("Segoe UI", 11, "bold")).pack(pady=(14, 4))

        btn_style = {"font": ("Segoe UI", 9), "relief": "flat",
                     "cursor": "hand2", "bd": 0, "padx": 12, "pady": 6}

        def do_exit():
            dlg.destroy()
            self._quit_app()

        def do_tray():
            dlg.destroy()
            self._hide_to_tray()

        btn_exit = tk.Button(inner, text="❌ 退出程序", bg=DANGER, fg="white",
                             activebackground="#B71C1C", command=do_exit, **btn_style)
        btn_exit.pack(fill="x", padx=20, pady=(8, 2))

        btn_tray = tk.Button(inner, text="🔽 最小化到托盘", bg="#1f6aa5", fg="white",
                             activebackground="#155a8a", command=do_tray, **btn_style)
        btn_tray.pack(fill="x", padx=20, pady=2)

        btn_cancel = tk.Button(inner, text="取消", bg=BAR_BG, fg=FG,
                               activebackground="#30363d", command=dlg.destroy, **btn_style)
        btn_cancel.pack(fill="x", padx=20, pady=(2, 10))

        # 强制弹窗到最前
        dlg.lift()
        dlg.focus_force()

    def _hide_to_tray(self):
        """关闭窗口 → 最小化到托盘"""
        self.root.withdraw()

    def _restore_from_tray(self):
        """托盘图标左键 → 恢复窗口"""
        self.root.after(0, self._do_restore)

    def _do_restore(self):
        self.root.deiconify()
        self.root.lift()
        self.root.attributes("-topmost", True)  # 确保弹到最前

    def _quit_app(self):
        """托盘退出 → 彻底关闭"""
        self._running = False
        if self._tray:
            self._tray.stop()
        self.root.after(0, self.root.destroy)

    # ─── 拖拽 ──────────────────────────────────────

    def _bind_drag(self):
        """绑定拖拽事件（始终绑定，flag 控制是否生效）"""
        self.root.bind("<Button-1>", self._on_click, add="+")
        self.root.bind("<B1-Motion>", self._on_move, add="+")
        self.root.bind("<ButtonRelease-1>", self._on_stop, add="+")
        self.root.bind("<Button-3>", self._on_right_click)

    def _toggle_drag(self):
        self._drag_mode = self._drag_var.get()
        self._mode_lbl.configure(
            text="🖥 SysGauge" if self._drag_mode else "📌 SysGauge")

    def _on_click(self, e):
        """左键：拖动模式才启动拖拽"""
        if not self._drag_mode:
            return
        self._dx, self._dy = e.x, e.y

    def _on_move(self, e):
        if not self._drag_mode:
            return
        x = self.root.winfo_x() + e.x - self._dx
        y = self.root.winfo_y() + e.y - self._dy
        self.root.geometry(f"+{x}+{y}")

    def _on_stop(self, e):
        if not self._drag_mode:
            return
        self._snap()

    def _on_right_click(self, e):
        self.menu.post(e.x_root, e.y_root)

    def _snap(self):
        cx = self.root.winfo_x() + W // 2
        cy = self.root.winfo_y() + self.root.winfo_height() // 2
        ml, mt, mr, mb = get_monitor_work(cx, cy)
        x, y = self.root.winfo_x(), self.root.winfo_y()
        D = 60
        h = self.root.winfo_height()
        if abs(x - ml) < D and abs(y - mt) < D:
            self.root.geometry(f"+{ml + 8}+{mt + 8}")
        elif abs(x + W - mr) < D and abs(y - mt) < D:
            self.root.geometry(f"+{mr - W - 8}+{mt + 8}")
        elif abs(x - ml) < D and abs(y + h - mb) < D:
            self.root.geometry(f"+{ml + 8}+{mb - h - 8}")
        elif abs(x + W - mr) < D and abs(y + h - mb) < D:
            self.root.geometry(f"+{mr - W - 8}+{mb - h - 8}")

    def _snap_to_corner(self, corner):
        cx = self.root.winfo_x() + W // 2
        cy = self.root.winfo_y() + self.root.winfo_height() // 2
        ml, mt, mr, mb = get_monitor_work(cx, cy)
        h = self.root.winfo_height()
        pos = {
            "左上": (ml + 8, mt + 8),
            "右上": (mr - W - 8, mt + 8),
            "左下": (ml + 8, mb - h - 8),
            "右下": (mr - W - 8, mb - h - 8),
        }
        if corner in pos:
            self.root.geometry(f"+{pos[corner][0]}+{pos[corner][1]}")
        # 吸附后自动切为固定模式（不可拖）
        self._drag_mode = False
        self._drag_var.set(False)
        self._mode_lbl.configure(text="📌 SysGauge")

    def _toggle_top(self):
        self.root.attributes("-topmost", self._top_var.get())

    def _set_alpha(self, v):
        self.root.attributes("-alpha", v)

    # ─── 刷新 ──────────────────────────────────────

    def _update_loop(self):
        if not self._running:
            return
        try:
            cpu = psutil.cpu_percent(interval=0.3)
            mem = psutil.virtual_memory().percent
            diskc = psutil.disk_usage("C:").percent
            self._set_bar("cpu", cpu)
            self._set_bar("mem", mem)
            self._set_bar("diskc", diskc)
            if "diskd" in self._bars:
                self._set_bar("diskd", psutil.disk_usage("D:").percent)
            if self._has_gpu and "gpu" in self._bars:
                gpu = get_gpu_usage()
                if gpu is not None:
                    self._set_bar("gpu", gpu)
                else:
                    self._bars["gpu"]["label"].configure(text="N/A", fg=FOOTER)
        except Exception:
            pass
        self.root.after(1000, self._update_loop)

    def _set_bar(self, key, val):
        b = self._bars[key]
        c = color_for(val)
        b["label"].configure(text=f"{val:.0f}%", fg=c)
        cv = b["canvas"]
        w = cv.winfo_width()
        if w > 1:
            fw = int(w * val / 100)
            cv.delete(b["bar"])
            b["bar"] = cv.create_rectangle(0, 0, fw, 5, fill=c, outline="")

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    SysGauge().run()
