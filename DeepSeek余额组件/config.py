"""
配置管理模块
负责存储和读取用户配置（API Key、位置、透明度、刷新间隔等）
"""

import json
import os
from typing import Optional


class Config:
    """应用配置管理"""

    CONFIG_DIR = os.path.dirname(os.path.abspath(__file__))
    CONFIG_FILE = os.path.join(CONFIG_DIR, "deepseek_widget_config.json")

    DEFAULTS = {
        "api_key": "",
        "window_position": "free",      # free | top-left | top-right | bottom-left | bottom-right
        "window_x": None,                # 自定义位置 X
        "window_y": None,                # 自定义位置 Y
        "window_width": 280,
        "window_height": 200,
        "transparency": 0.9,             # 0.1 ~ 1.0
        "refresh_interval": 60,          # 刷新间隔（秒）
        "always_on_top": True,
        "theme": "dark",                 # dark | light
        "show_balance_only": False,      # 仅显示余额（简化模式）
    }

    def __init__(self):
        self._data = dict(self.DEFAULTS)
        self.load()

    @property
    def file_path(self) -> str:
        return self.CONFIG_FILE

    def load(self):
        """从 JSON 文件加载配置"""
        try:
            if os.path.exists(self.CONFIG_FILE):
                with open(self.CONFIG_FILE, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                    # 合并，保留默认值中缺失的字段
                    self._data = {**self.DEFAULTS, **loaded}
        except (json.JSONDecodeError, IOError) as e:
            print(f"配置文件读取失败，使用默认配置: {e}")
            self._data = dict(self.DEFAULTS)

    def save(self):
        """保存配置到 JSON 文件"""
        try:
            data_to_save = {k: v for k, v in self._data.items()}
            with open(self.CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(data_to_save, f, ensure_ascii=False, indent=2)
            return True
        except IOError as e:
            print(f"配置文件保存失败: {e}")
            return False

    def get(self, key: str, default=None):
        """获取配置项"""
        return self._data.get(key, default)

    def set(self, key: str, value):
        """设置配置项"""
        self._data[key] = value
        return self.save()

    def update(self, **kwargs):
        """批量更新配置"""
        self._data.update(kwargs)
        return self.save()

    def reset(self):
        """重置为默认配置"""
        self._data = dict(self.DEFAULTS)
        return self.save()

    @property
    def api_key(self) -> str:
        return self._data.get("api_key", "")

    @api_key.setter
    def api_key(self, value: str):
        self._data["api_key"] = value

    @property
    def transparency(self) -> float:
        return self._data.get("transparency", 0.9)

    @transparency.setter
    def transparency(self, value: float):
        self._data["transparency"] = max(0.1, min(1.0, value))

    @property
    def refresh_interval(self) -> int:
        """获取刷新间隔（秒）"""
        return self._data.get("refresh_interval", 60)

    @property
    def position(self) -> str:
        return self._data.get("window_position", "free")

    @property
    def always_on_top(self) -> bool:
        return self._data.get("always_on_top", True)

    def __repr__(self):
        safe_data = {k: v for k, v in self._data.items() if k != "api_key"}
        return f"Config({safe_data})"


if __name__ == "__main__":
    cfg = Config()
    print(f"当前配置路径: {cfg.file_path}")
    print(f"当前配置: {cfg}")
    print(f"透明度: {cfg.transparency}")
    print(f"刷新间隔: {cfg.refresh_interval}秒")
    print(f"位置: {cfg.position}")
