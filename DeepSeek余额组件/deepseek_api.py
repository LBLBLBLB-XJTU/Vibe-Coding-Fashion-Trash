"""
DeepSeek API 调用模块
负责获取账户余额
"""

import requests
import time
from typing import Optional, Dict, Any


class DeepSeekAPI:
    """DeepSeek API 客户端"""

    BASE_URL = "https://api.deepseek.com"

    def __init__(self, api_key: str = ""):
        self.api_key = api_key
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {self.api_key}",
            "Accept": "application/json"
        })
        self._last_balance_check = 0
        self._cached_balance = None
        self._cache_ttl = 30

    def set_api_key(self, api_key: str):
        """更新 API Key"""
        self.api_key = api_key
        self.session.headers.update({
            "Authorization": f"Bearer {self.api_key}"
        })
        self._cached_balance = None
        self._last_balance_check = 0

    def get_balance(self, force_refresh: bool = False) -> Optional[Dict[str, Any]]:
        """
        获取账户余额
        GET https://api.deepseek.com/user/balance

        返回示例:
        {
            "is_available": True,
            "balance_infos": [
                {
                    "currency": "CNY",
                    "total_balance": "100.00",
                    "granted_balance": "50.00",
                    "topped_up_balance": "50.00"
                }
            ]
        }
        """
        if not self.api_key:
            return None

        now = time.time()
        if not force_refresh and self._cached_balance is not None:
            if now - self._last_balance_check < self._cache_ttl:
                return self._cached_balance

        try:
            resp = self.session.get(
                f"{self.BASE_URL}/user/balance",
                timeout=10
            )
            if resp.status_code == 200:
                data = resp.json()
                self._cached_balance = data
                self._last_balance_check = now
                return data
            elif resp.status_code == 401:
                return {"error": "API Key 无效或已过期"}
            else:
                return {"error": f"HTTP {resp.status_code}: {resp.text}"}
        except requests.exceptions.Timeout:
            return {"error": "请求超时，请检查网络"}
        except requests.exceptions.ConnectionError:
            return {"error": "网络连接失败"}
        except Exception as e:
            return {"error": f"请求异常: {str(e)}"}

    def get_available_balance(self, force_refresh: bool = False) -> float:
        """获取可用余额（优先 topped_up_balance）"""
        data = self.get_balance(force_refresh)
        if not data or "error" in data or "balance_infos" not in data:
            return 0.0
        balance_infos = data.get("balance_infos", [])
        if not balance_infos:
            return 0.0
        info = balance_infos[0]
        topped_up = info.get("topped_up_balance", "0")
        if topped_up and float(topped_up) > 0:
            return float(topped_up)
        return float(info.get("total_balance", "0"))

    def get_total_balance(self, force_refresh: bool = False) -> float:
        """获取总余额（含赠送）"""
        data = self.get_balance(force_refresh)
        if not data or "error" in data or "balance_infos" not in data:
            return 0.0
        infos = data.get("balance_infos", [])
        if not infos:
            return 0.0
        return float(infos[0].get("total_balance", "0"))

    def format_balance(self, amount: float) -> str:
        """格式化余额显示"""
        if amount >= 10000:
            return f"¥{amount:,.2f}"
        elif amount >= 1:
            return f"¥{amount:,.2f}"
        elif amount > 0:
            return f"¥{amount:.4f}"
        else:
            return "¥0.00"


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        key = sys.argv[1]
        api = DeepSeekAPI(key)
        print("正在查询余额...")
        result = api.get_balance()
        if result:
            if "error" in result:
                print(f"错误: {result['error']}")
            else:
                print(f"余额信息: {result}")
                print(f"可用余额: {api.format_balance(api.get_available_balance())}")
                print(f"总余额: {api.format_balance(api.get_total_balance())}")
    else:
        print("用法: python deepseek_api.py <your_api_key>")
