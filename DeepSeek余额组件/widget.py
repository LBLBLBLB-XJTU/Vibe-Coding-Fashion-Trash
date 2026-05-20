"""
DeepSeek 余额桌面小组件 - 核心界面
使用 customtkinter 构建的现代化浮动窗口
支持：实时余额、退出弹窗选择、系统托盘运行
"""

import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import customtkinter as ctk
from datetime import datetime
import threading
import time
import sys
import os
import ctypes
from ctypes import wintypes

# ── Win32 多屏支持 ──
MONITOR_DEFAULTTONEAREST = 2

class RECT(ctypes.Structure):
    _fields_ = [("left", ctypes.c_long), ("top", ctypes.c_long),
                ("right", ctypes.c_long), ("bottom", ctypes.c_long)]

class MONITORINFO(ctypes.Structure):
    _fields_ = [("cbSize", ctypes.c_ulong), ("rcMonitor", RECT),
                ("rcWork", RECT), ("dwFlags", ctypes.c_ulong)]

def get_monitor_work(x: int, y: int):
    """返回包含 (x,y) 的显示器工作区 left,top,right,bottom（不含任务栏）"""
    pt = wintypes.POINT(x, y)
    hmon = ctypes.windll.user32.MonitorFromPoint(pt, MONITOR_DEFAULTTONEAREST)
    info = MONITORINFO()
    info.cbSize = ctypes.sizeof(MONITORINFO)
    ctypes.windll.user32.GetMonitorInfoW(hmon, ctypes.byref(info))
    return (info.rcWork.left, info.rcWork.top,
            info.rcWork.right, info.rcWork.bottom)


def _get_fallback_monitor(x: int, y: int):
    """备用：枚举所有显示器，返回包含 (x,y) 的那个"""
    monitors = []

    def _callback(hmon, hdc, rect, param):
        info = MONITORINFO()
        info.cbSize = ctypes.sizeof(MONITORINFO)
        ctypes.windll.user32.GetMonitorInfoW(hmon, ctypes.byref(info))
        monitors.append(info)
        return True

    ctypes.windll.user32.EnumDisplayMonitors(
        None, None,
        ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HMONITOR, wintypes.HDC,
                          ctypes.POINTER(RECT), wintypes.LPARAM)(_callback),
        0)

    for m in monitors:
        if m.rcMonitor.left <= x < m.rcMonitor.right and m.rcMonitor.top <= y < m.rcMonitor.bottom:
            return (m.rcWork.left, m.rcWork.top, m.rcWork.right, m.rcWork.bottom)

    # 兜底：返回主屏
    if monitors:
        m = monitors[0]
        return (m.rcWork.left, m.rcWork.top, m.rcWork.right, m.rcWork.bottom)
    return (0, 0, 2560, 1440)

# 系统托盘支持（可选依赖）
try:
    import pystray
    from PIL import Image, ImageDraw, ImageFont
    HAS_TRAY = True
except ImportError:
    HAS_TRAY = False

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from deepseek_api import DeepSeekAPI
from config import Config


ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


class SettingsDialog(ctk.CTkToplevel):
    """设置对话框"""

    def __init__(self, parent, config: Config, on_save_callback=None):
        super().__init__(parent)
        self.config = config
        self.on_save = on_save_callback
        self.title("⚙ DeepSeek 小组件设置")
        self.geometry("420x520")
        self.resizable(False, False)
        self.after(100, self._center_on_parent)
        self.transient(parent)
        self.grab_set()
        self._build_ui()

    def _center_on_parent(self):
        self.update_idletasks()
        pw = self.master.winfo_width()
        ph = self.master.winfo_height()
        px = self.master.winfo_x()
        py = self.master.winfo_y()
        w = self.winfo_width()
        h = self.winfo_height()
        x = px + (pw - w) // 2
        y = py + (ph - h) // 2
        self.geometry(f"+{max(0,x)}+{max(0,y)}")

    def _build_ui(self):
        scroll_frame = ctk.CTkScrollableFrame(self, width=400, height=480)
        scroll_frame.pack(fill="both", expand=True, padx=15, pady=15)

        # API 设置
        api_section = ctk.CTkFrame(scroll_frame)
        api_section.pack(fill="x", pady=(0, 15))
        ctk.CTkLabel(api_section, text="🔑 DeepSeek API 设置",
                     font=ctk.CTkFont(size=14, weight="bold")).pack(anchor="w", padx=10, pady=(10, 5))
        self.api_key_var = ctk.StringVar(value=self.config.api_key)
        api_entry = ctk.CTkEntry(api_section, textvariable=self.api_key_var,
                                 placeholder_text="sk-... 输入你的 DeepSeek API Key",
                                 width=350, show="*")
        api_entry.pack(padx=10, pady=5)
        btn_frame = ctk.CTkFrame(api_section, fg_color="transparent")
        btn_frame.pack(fill="x", padx=10, pady=(0, 10))
        self.show_key = False
        self.toggle_key_btn = ctk.CTkButton(btn_frame, text="👁 显示", width=80, command=self._toggle_api_key_visibility)
        self.toggle_key_btn.pack(side="left", padx=(0, 5))
        ctk.CTkButton(btn_frame, text="🔄 测试连接", width=100, command=self._test_connection).pack(side="left", padx=5)

        # 外观设置
        appearance_section = ctk.CTkFrame(scroll_frame)
        appearance_section.pack(fill="x", pady=(0, 15))
        ctk.CTkLabel(appearance_section, text="🎨 外观设置",
                     font=ctk.CTkFont(size=14, weight="bold")).pack(anchor="w", padx=10, pady=(10, 5))
        ctk.CTkLabel(appearance_section, text=f"背景透明度: {int(self.config.transparency * 100)}%",
                     font=ctk.CTkFont(size=12)).pack(anchor="w", padx=10, pady=(5, 0))
        self.transparency_var = ctk.DoubleVar(value=self.config.transparency)
        transparency_slider = ctk.CTkSlider(appearance_section, from_=0.1, to=1.0,
            variable=self.transparency_var, number_of_steps=18, command=self._on_transparency_change)
        transparency_slider.pack(fill="x", padx=10, pady=5)
        self.transparency_label = ctk.CTkLabel(appearance_section, text=f"{int(self.config.transparency * 100)}%",
            font=ctk.CTkFont(size=12))
        self.transparency_label.pack(anchor="e", padx=15)
        theme_frame = ctk.CTkFrame(appearance_section, fg_color="transparent")
        theme_frame.pack(fill="x", padx=10, pady=(5, 10))
        ctk.CTkLabel(theme_frame, text="主题模式:", font=ctk.CTkFont(size=12)).pack(side="left")
        self.theme_var = ctk.StringVar(value=self.config.get("theme", "dark"))
        theme_menu = ctk.CTkOptionMenu(theme_frame, values=["dark", "light"],
            variable=self.theme_var, width=100, command=self._on_theme_change)
        theme_menu.pack(side="right")

        # 位置设置
        position_section = ctk.CTkFrame(scroll_frame)
        position_section.pack(fill="x", pady=(0, 15))
        ctk.CTkLabel(position_section, text="📍 位置设置",
                     font=ctk.CTkFont(size=14, weight="bold")).pack(anchor="w", padx=10, pady=(10, 5))
        self.position_var = ctk.StringVar(value=self.config.position)
        positions = [("自由拖拽", "free"), ("左上角", "top-left"), ("右上角", "top-right"),
                     ("左下角", "bottom-left"), ("右下角", "bottom-right")]
        pos_grid = ctk.CTkFrame(position_section, fg_color="transparent")
        pos_grid.pack(padx=10, pady=5)
        for i, (label, value) in enumerate(positions):
            rb = ctk.CTkRadioButton(pos_grid, text=label, value=value,
                variable=self.position_var, font=ctk.CTkFont(size=12))
            rb.grid(row=i // 2, column=i % 2, sticky="w", padx=5, pady=3)

        # 刷新设置
        refresh_section = ctk.CTkFrame(scroll_frame)
        refresh_section.pack(fill="x", pady=(0, 15))
        ctk.CTkLabel(refresh_section, text="🔄 刷新设置",
                     font=ctk.CTkFont(size=14, weight="bold")).pack(anchor="w", padx=10, pady=(10, 5))
        refresh_frame = ctk.CTkFrame(refresh_section, fg_color="transparent")
        refresh_frame.pack(fill="x", padx=10, pady=5)
        ctk.CTkLabel(refresh_frame, text="自动刷新间隔:", font=ctk.CTkFont(size=12)).pack(side="left")
        self.refresh_var = ctk.StringVar(value=str(self.config.refresh_interval))
        refresh_entry = ctk.CTkEntry(refresh_frame, textvariable=self.refresh_var, width=60, justify="center")
        refresh_entry.pack(side="left", padx=(10, 5))
        ctk.CTkLabel(refresh_frame, text="秒", font=ctk.CTkFont(size=12)).pack(side="left")
        top_frame = ctk.CTkFrame(refresh_section, fg_color="transparent")
        top_frame.pack(fill="x", padx=10, pady=(5, 10))
        self.always_on_top_var = ctk.BooleanVar(value=self.config.always_on_top)
        ctk.CTkSwitch(top_frame, text="窗口置顶", variable=self.always_on_top_var,
                      font=ctk.CTkFont(size=12)).pack(side="left")

        # 操作按钮
        button_frame = ctk.CTkFrame(scroll_frame, fg_color="transparent")
        button_frame.pack(fill="x", pady=(5, 10))
        ctk.CTkButton(button_frame, text="💾 保存设置", command=self._save_settings,
                      height=35).pack(side="left", padx=(0, 10), fill="x", expand=True)
        ctk.CTkButton(button_frame, text="↩ 重置默认", command=self._reset_settings,
                      height=35, fg_color="gray40", hover_color="gray30").pack(side="right", fill="x", expand=True)

    def _toggle_api_key_visibility(self):
        self.show_key = not self.show_key
        for child in self.winfo_children():
            self._toggle_entry_show(child)

    def _toggle_entry_show(self, widget):
        if isinstance(widget, ctk.CTkEntry):
            widget.configure(show="" if self.show_key else "*")
            self.toggle_key_btn.configure(text="🙈 隐藏" if self.show_key else "👁 显示")
        for child in widget.winfo_children():
            self._toggle_entry_show(child)

    def _on_transparency_change(self, value):
        pct = int(value * 100)
        self.transparency_label.configure(text=f"{pct}%")

    def _on_theme_change(self, choice):
        ctk.set_appearance_mode(choice)

    def _test_connection(self):
        key = self.api_key_var.get().strip()
        if not key:
            messagebox.showwarning("提示", "请先输入 API Key")
            return
        self._show_test_result("正在测试连接...", "yellow")
        self.update()

        def test():
            api = DeepSeekAPI(key)
            result = api.get_balance()
            if result:
                if "error" in result:
                    self._show_test_result(f"❌ {result['error']}", "red")
                else:
                    balance = api.format_balance(api.get_available_balance())
                    self._show_test_result(f"✅ 连接成功！余额: {balance}", "green")
            else:
                self._show_test_result("❌ 连接失败，请检查 API Key", "red")

        threading.Thread(target=test, daemon=True).start()

    def _show_test_result(self, msg, color):
        def update():
            self.test_result_label.configure(text=msg)
        if hasattr(self, "test_result_label"):
            self.after(0, update)
        else:
            self.test_result_label = ctk.CTkLabel(self, text=msg, font=ctk.CTkFont(size=12), text_color=color)
            self.test_result_label.pack(padx=15, pady=(0, 10))
            self.after(0, update)

    def _save_settings(self):
        try:
            interval = int(self.refresh_var.get())
            if interval < 10:
                messagebox.showwarning("提示", "刷新间隔不能小于 10 秒")
                return
        except ValueError:
            messagebox.showwarning("提示", "刷新间隔必须为数字（秒）")
            return
        self.config.update(
            api_key=self.api_key_var.get().strip(),
            window_position=self.position_var.get(),
            transparency=round(self.transparency_var.get(), 2),
            refresh_interval=interval,
            always_on_top=self.always_on_top_var.get(),
            theme=self.theme_var.get(),
        )
        if self.on_save:
            self.on_save(self.config)
        messagebox.showinfo("完成", "设置已保存！")
        self.destroy()

    def _reset_settings(self):
        if messagebox.askyesno("确认", "确定要重置所有设置为默认值吗？"):
            self.config.reset()
            self.destroy()
            if self.on_save:
                self.on_save(self.config)


class ExitDialog(ctk.CTkToplevel):
    """退出确认对话框"""

    def __init__(self, parent, on_exit_callback, on_tray_callback):
        super().__init__(parent)
        self.title("退出确认")
        self.geometry("340x220")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()
        self.after(100, self._center_on_parent)
        self.on_exit = on_exit_callback
        self.on_tray = on_tray_callback
        self._build_ui()

    def _center_on_parent(self):
        self.update_idletasks()
        try:
            pw = self.master.winfo_width()
            ph = self.master.winfo_height()
            px = self.master.winfo_x()
            py = self.master.winfo_y()
            w = self.winfo_width()
            h = self.winfo_height()
            x = px + (pw - w) // 2
            y = py + (ph - h) // 2
            self.geometry(f"+{max(0,x)}+{max(0,y)}")
        except Exception:
            pass

    def _build_ui(self):
        ctk.CTkLabel(self, text="🤖", font=ctk.CTkFont(size=36)).pack(pady=(20, 5))
        ctk.CTkLabel(self, text="确认退出 DeepSeek 余额？",
                     font=ctk.CTkFont(size=14, weight="bold")).pack(pady=(0, 5))
        ctk.CTkLabel(self, text="选择退出后，小组件将停止更新余额信息",
                     font=ctk.CTkFont(size=11), text_color="gray50").pack(pady=(0, 15))
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(fill="x", padx=25)
        ctk.CTkButton(btn_frame, text="❌ 直接退出", command=self._on_exit_click,
                      height=36, fg_color="#D32F2F", hover_color="#B71C1C").pack(fill="x", pady=(0, 6))
        ctk.CTkButton(btn_frame, text="🔽 作为小托盘继续运行", command=self._on_tray_click,
                      height=36, fg_color="#388E3C", hover_color="#1B5E20").pack(fill="x", pady=(0, 6))
        ctk.CTkButton(btn_frame, text="↩ 取消", command=self._on_cancel,
                      height=30, fg_color="gray40", hover_color="gray30").pack(fill="x")

    def _on_exit_click(self):
        self.destroy()
        if self.on_exit:
            self.after(50, self.on_exit)

    def _on_tray_click(self):
        self.destroy()
        if self.on_tray:
            self.after(50, self.on_tray)

    def _on_cancel(self):
        self.destroy()


class SystemTrayManager:
    """系统托盘管理"""

    def __init__(self, widget: 'DeepSeekWidget'):
        self.widget = widget
        self.icon = None
        self._running = False
        self._thread = None

    def start(self):
        if not HAS_TRAY or self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._run_tray, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False
        if self.icon:
            try:
                self.icon.stop()
            except Exception:
                pass
            self.icon = None

    def _create_image(self) -> Image.Image:
        size = 64
        img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        margin = 4
        draw.ellipse([margin, margin, size - margin, size - margin], fill="#1f6aa5", outline="#4FC3F7", width=2)
        try:
            font = ImageFont.truetype("arial.ttf", 36)
        except Exception:
            font = ImageFont.load_default()
        bbox = draw.textbbox((0, 0), "D", font=font)
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]
        tx = (size - tw) // 2
        ty = (size - th) // 2 - 1
        draw.text((tx, ty), "D", fill="white", font=font)
        return img

    def _run_tray(self):
        try:
            image = self._create_image()
            menu = pystray.Menu(
                pystray.MenuItem("📊 显示窗口", self._on_show),
                pystray.MenuItem("🔄 立即刷新", self._on_refresh),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem("❌ 退出应用", self._on_quit)
            )
            self.icon = pystray.Icon("deepseek_balance", image, "DeepSeek 余额\n余额: 加载中...", menu)
            self.icon.run()
        except Exception as e:
            print(f"托盘图标启动失败: {e}")
            self._running = False

    def update_tooltip(self, balance_text: str = ""):
        if self.icon and self._running:
            try:
                self.icon.title = f"DeepSeek 余额\n余额: {balance_text}" if balance_text else "DeepSeek 余额"
            except Exception:
                pass

    def _on_show(self):
        self.stop()
        if self.widget.window:
            self.widget.window.after(0, self._restore_window)

    def _restore_window(self):
        try:
            self.widget.window.deiconify()
            self.widget.window.lift()
            self.widget.window.focus_force()
            self.widget._in_tray = False
        except Exception:
            pass

    def _on_refresh(self):
        if self.widget.window:
            self.widget.window.after(0, self.widget._refresh_data)

    def _on_quit(self):
        self.stop()
        if self.widget.window:
            self.widget.window.after(0, self._do_quit)

    def _do_quit(self):
        self.widget._really_quit = True
        try:
            self.widget.window.destroy()
        except Exception:
            os._exit(0)


class DeepSeekWidget:
    """DeepSeek 余额桌面小组件"""

    def __init__(self):
        self.config = Config()
        self.api = DeepSeekAPI(self.config.api_key)
        self._dragging = False
        self._drag_start_x = 0
        self._drag_start_y = 0
        self._drag_start_win_x = 0
        self._drag_start_win_y = 0
        self._really_quit = False
        self._in_tray = False

        self.window = ctk.CTk()
        self.window.title("DeepSeek 余额")
        self.window.overrideredirect(True)
        self.window.attributes("-topmost", self.config.always_on_top)
        self.window.attributes("-alpha", self.config.transparency)

        self.window_width = self.config.get("window_width", 280)
        self.window_height = self.config.get("window_height", 200)

        self._apply_position()
        self._build_ui()
        self._schedule_refresh()
        self.window.protocol("WM_DELETE_WINDOW", self._on_close)

    def _apply_position(self, ref_x=None, ref_y=None):
        """启动/设置面板时定位"""
        pos = self.config.position
        if pos == "free":
            self.window.update_idletasks()
            w = max(self.window.winfo_width(), self.window_width, 10)
            h = max(self.window.winfo_height(), self.window_height, 10)
            sx = self.config.get("window_x")
            sy = self.config.get("window_y")
            if sx is not None and sy is not None:
                x, y = sx, sy
            else:
                x = self.window.winfo_screenwidth() - w - 50
                y = 100
            hwnd = int(self.window.frame(), 16)
            ctypes.windll.user32.SetWindowPos(hwnd, 0, x, y, w, h, 0x0001)
            self.window.after(100, lambda: self.config.update(window_x=x, window_y=y))
        else:
            self._do_snap(pos)

    def _build_ui(self):
        self.main_frame = ctk.CTkFrame(self.window, corner_radius=12, border_width=1, border_color="gray30")
        self.main_frame.pack(fill="both", expand=True, padx=2, pady=2)

        # 标题栏
        self.title_bar = ctk.CTkFrame(self.main_frame, height=36, corner_radius=0, fg_color="transparent")
        self.title_bar.pack(fill="x", padx=0, pady=0)
        self.title_bar.pack_propagate(False)

        self.drag_area = ctk.CTkFrame(self.title_bar, fg_color="transparent", height=36)
        self.drag_area.pack(side="left", fill="x", expand=True)
        self.drag_area.pack_propagate(False)

        ctk.CTkLabel(self.drag_area, text="🤖 DeepSeek v2",
                     font=ctk.CTkFont(size=13, weight="bold")).pack(side="left", padx=(10, 0))

        self.status_indicator = ctk.CTkLabel(self.drag_area, text="●",
            font=ctk.CTkFont(size=10), text_color="gray")
        self.status_indicator.pack(side="right", padx=(0, 5))

        # 托盘按钮
        self.tray_btn = ctk.CTkButton(self.title_bar, text="▬", width=24, height=22,
            font=ctk.CTkFont(size=12), fg_color="transparent", hover_color="gray30",
            corner_radius=4, command=self._on_tray)
        self.tray_btn.pack(side="right", padx=(0, 2), pady=2)

        # 关闭按钮
        self.close_btn = ctk.CTkButton(self.title_bar, text="✕", width=24, height=22,
            font=ctk.CTkFont(size=13), fg_color="transparent", hover_color="#FF4444",
            corner_radius=4, command=self._on_close)
        self.close_btn.pack(side="right", padx=(0, 5), pady=2)

        for widget in [self.drag_area, self.title_bar]:
            widget.bind("<Button-1>", self._on_drag_start)
            widget.bind("<B1-Motion>", self._on_drag_motion)
            widget.bind("<ButtonRelease-1>", self._on_drag_end)

        # 内容区域
        self.content_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.content_frame.pack(fill="both", expand=True, padx=15, pady=(5, 10))

        ctk.CTkLabel(self.content_frame, text="💰 账户余额",
                     font=ctk.CTkFont(size=11), text_color="gray60").pack(anchor="w")

        self.balance_label = ctk.CTkLabel(self.content_frame, text="--.--",
            font=ctk.CTkFont(size=32, weight="bold"))
        self.balance_label.pack(anchor="w", pady=(0, 8))

        ctk.CTkFrame(self.content_frame, height=1, fg_color="gray30").pack(fill="x", pady=(0, 8))

        # 总余额
        info_frame = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        info_frame.pack(fill="x")
        ctk.CTkLabel(info_frame, text="📊 总余额（含赠送）:",
                     font=ctk.CTkFont(size=11), text_color="gray60").pack(side="left")
        self.total_balance_label = ctk.CTkLabel(info_frame, text="--.--",
            font=ctk.CTkFont(size=12, weight="bold"), text_color="#4FC3F7")
        self.total_balance_label.pack(side="right")

        # 更新时间
        time_frame = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        time_frame.pack(fill="x", pady=(5, 0))
        ctk.CTkLabel(time_frame, text="🕐 更新于:",
                     font=ctk.CTkFont(size=10), text_color="gray50").pack(side="left")
        self.update_time_label = ctk.CTkLabel(time_frame, text="--:--:--",
            font=ctk.CTkFont(size=10), text_color="gray50")
        self.update_time_label.pack(side="left", padx=(4, 0))

        self.error_label = ctk.CTkLabel(self.content_frame, text="",
            font=ctk.CTkFont(size=10), text_color="#FF6B6B", wraplength=250)

        # 右键菜单
        self._build_context_menu()
        self._bind_right_click(self.main_frame)
        self.window.after(500, self._refresh_data)

    def _build_context_menu(self):
        self.context_menu = tk.Menu(self.window, tearoff=0, bg="#2b2b2b",
            fg="white", activebackground="#1f6aa5", activeforeground="white",
            font=("Microsoft YaHei", 10))
        self.context_menu.add_command(label="🔄 立即刷新", command=self._refresh_data)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="⚙ 设置", command=self._open_settings)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="📌 置顶窗口", command=self._toggle_topmost)
        self.pos_menu = tk.Menu(self.context_menu, tearoff=0, bg="#2b2b2b",
            fg="white", activebackground="#1f6aa5", activeforeground="white",
            font=("Microsoft YaHei", 10))
        self.pos_menu.add_command(label="↕ 自由拖拽", command=lambda: None)
        self.pos_menu.add_command(label="↖ 左上角", command=lambda: None)
        self.pos_menu.add_command(label="↗ 右上角", command=lambda: None)
        self.pos_menu.add_command(label="↙ 左下角", command=lambda: None)
        self.pos_menu.add_command(label="↘ 右下角", command=lambda: None)
        self.context_menu.add_cascade(label="📍 固定位置", menu=self.pos_menu)
        self.context_menu.add_separator()
        self.opacity_menu = tk.Menu(self.context_menu, tearoff=0, bg="#2b2b2b",
            fg="white", activebackground="#1f6aa5", activeforeground="white",
            font=("Microsoft YaHei", 10))
        for pct in [30, 50, 60, 70, 80, 90, 100]:
            self.opacity_menu.add_command(label=f"{pct}% 透明度",
                command=lambda v=pct/100: self._set_transparency(v))
        self.context_menu.add_cascade(label="🔆 背景透明度", menu=self.opacity_menu)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="🔽 最小化到托盘", command=self._on_tray)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="❌ 退出", command=self._on_close)

    def _bind_right_click(self, widget):
        widget.bind("<Button-3>", self._show_context_menu)
        for child in widget.winfo_children():
            self._bind_right_click(child)

    def _show_context_menu(self, event):
        # 把坐标直接绑定到菜单命令里
        ex, ey = event.x_root, event.y_root
        # 重建位置子菜单（用当前点击坐标）
        self.pos_menu.delete(0, "end")
        self.pos_menu.add_command(label="↕ 自由拖拽", command=lambda: self._set_position_at("free", ex, ey))
        self.pos_menu.add_command(label="↖ 左上角", command=lambda: self._set_position_at("top-left", ex, ey))
        self.pos_menu.add_command(label="↗ 右上角", command=lambda: self._set_position_at("top-right", ex, ey))
        self.pos_menu.add_command(label="↙ 左下角", command=lambda: self._set_position_at("bottom-left", ex, ey))
        self.pos_menu.add_command(label="↘ 右下角", command=lambda: self._set_position_at("bottom-right", ex, ey))
        try:
            self.context_menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.context_menu.grab_release()

    # ===== 拖拽 =====
    def _on_drag_start(self, event):
        if self.config.position == "free":
            self._dragging = True
            self._drag_start_x = event.x_root
            self._drag_start_y = event.y_root
            self._drag_start_win_x = self.window.winfo_x()
            self._drag_start_win_y = self.window.winfo_y()
            self.window.attributes("-alpha", min(1.0, self.config.transparency + 0.1))

    def _on_drag_motion(self, event):
        if self._dragging:
            dx = event.x_root - self._drag_start_x
            dy = event.y_root - self._drag_start_y
            self.window.geometry(f"+{self._drag_start_win_x + dx}+{self._drag_start_win_y + dy}")

    def _on_drag_end(self, event):
        if self._dragging:
            self._dragging = False
            self.window.attributes("-alpha", self.config.transparency)
            self.config.update(window_x=self.window.winfo_x(), window_y=self.window.winfo_y())

    def _set_position_at(self, pos: str, ex: int, ey: int):
        """右键菜单选固定位置 — 完全复用 SysGauge 逻辑"""
        self.config.set("window_position", pos)
        self._do_snap(pos)

    def _do_snap(self, pos: str):
        """核心吸附逻辑 — 同 SysGauge._snap_to_corner"""
        self.window.update_idletasks()
        w = max(self.window.winfo_width(), self.window_width, 10)
        h = max(self.window.winfo_height(), self.window_height, 10)
        cx = self.window.winfo_x() + w // 2
        cy = self.window.winfo_y() + h // 2
        ml, mt, mr, mb = get_monitor_work(cx, cy)
        if ml == 0 and mt == 0 and mr == 0 and mb == 0:
            ml, mt, mr, mb = _get_fallback_monitor(cx, cy)

        corners = {
            "top-left":     (ml + 20, mt + 20),
            "top-right":    (mr - w - 20, mt + 20),
            "bottom-left":  (ml + 20, mb - h - 20),
            "bottom-right": (mr - w - 20, mb - h - 20),
        }
        x, y = corners.get(pos, corners["top-right"])

        hwnd = int(self.window.frame(), 16)
        ctypes.windll.user32.SetWindowPos(hwnd, 0, x, y, w, h, 0x0001)
        self.window.after(300, lambda h=hwnd, xx=x, yy=y, ww=w, hh=h:
            ctypes.windll.user32.SetWindowPos(h, 0, xx, yy, ww, hh, 0x0001))
        self.config.update(window_x=x, window_y=y)
        value = max(0.1, min(1.0, value))
        self.config.set("transparency", value)
        self.window.attributes("-alpha", value)

    def _toggle_topmost(self):
        new_state = not self.config.always_on_top
        self.config.set("always_on_top", new_state)
        self.window.attributes("-topmost", new_state)

    # ===== 数据刷新 =====
    def _refresh_data(self):
        if not self.config.api_key:
            self.balance_label.configure(text="未设置 API Key")
            self.total_balance_label.configure(text="右键设置")
            self.update_time_label.configure(text="--:--:--")
            self.status_indicator.configure(text_color="orange")
            return
        self.status_indicator.configure(text_color="yellow")
        threading.Thread(target=self._do_refresh, daemon=True).start()

    def _do_refresh(self):
        try:
            result = self.api.get_balance()
            if result:
                if "error" in result:
                    self._update_error(result["error"])
                else:
                    available = self.api.get_available_balance()
                    total = self.api.get_total_balance()
                    now = datetime.now().strftime("%H:%M:%S")
                    balance_text = self.api.format_balance(available)

                    self.window.after(0, lambda: self.balance_label.configure(text=balance_text))
                    self.window.after(0, lambda: self.total_balance_label.configure(
                        text=self.api.format_balance(total)))
                    self.window.after(0, lambda: self.update_time_label.configure(text=now))
                    self.window.after(0, lambda: self.status_indicator.configure(text_color="#4CAF50"))
                    self.window.after(0, self._hide_error)

                    if hasattr(self, 'tray_manager') and self.tray_manager:
                        self.tray_manager.update_tooltip(balance_text)
            else:
                self._update_error("API Key 未配置")
        except Exception as e:
            self._update_error(str(e))

    def _update_error(self, msg: str):
        self.window.after(0, lambda: self.error_label.configure(text=f"⚠ {msg}"))
        self.window.after(0, lambda: self.error_label.pack(anchor="w", pady=(5, 0)))
        self.window.after(0, lambda: self.status_indicator.configure(text_color="red"))

    def _hide_error(self):
        self.error_label.pack_forget()

    def _schedule_refresh(self):
        interval = self.config.refresh_interval * 1000
        self._refresh_data()
        self.window.after(interval, self._schedule_refresh)

    # ===== 系统托盘 =====
    def _init_tray(self):
        if not hasattr(self, 'tray_manager') or not self.tray_manager:
            self.tray_manager = SystemTrayManager(self)

    def _on_tray(self):
        self._init_tray()
        if not HAS_TRAY:
            messagebox.showinfo("提示",
                "系统托盘功能需要安装 pystray 和 Pillow 库。\n请运行: pip install pystray Pillow")
            return
        self._in_tray = True
        self.window.withdraw()
        self.tray_manager.start()

    # ===== 窗口操作 =====
    def _on_close(self):
        if self.config.position == "free":
            self.config.update(window_x=self.window.winfo_x(), window_y=self.window.winfo_y())
        ExitDialog(self.window, on_exit_callback=self._do_exit, on_tray_callback=self._do_tray)

    def _do_exit(self):
        self._really_quit = True
        if hasattr(self, 'tray_manager') and self.tray_manager:
            self.tray_manager.stop()
        self.window.destroy()

    def _do_tray(self):
        self._on_tray()

    def _open_settings(self):
        SettingsDialog(self.window, self.config, on_save_callback=self._on_settings_saved)

    def _on_settings_saved(self, config: Config):
        self.api.set_api_key(config.api_key)
        self.window.attributes("-alpha", config.transparency)
        self.window.attributes("-topmost", config.always_on_top)
        self._apply_position()
        self._refresh_data()

    def run(self):
        try:
            self.window.mainloop()
        except KeyboardInterrupt:
            self._do_exit()


if __name__ == "__main__":
    widget = DeepSeekWidget()
    widget.run()
