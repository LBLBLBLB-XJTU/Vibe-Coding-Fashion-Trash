# vibe coding 时尚小垃圾 🗑️✨

> 一些用 vibe 写出来的桌面小组件和小玩意，能用就行，别问代码质量。

---

## 🖥️ SysGauge — 系统状态小组件

一个贴在桌角的系统监控悬浮窗，CPU / 内存 / GPU / 磁盘 C D 一目了然。

- **拖动 / 固定模式**：右键菜单一键吸附四角，或随意拖拽
- **多屏支持**：Win32 原生 API 精确吸附到任意显示器
- **系统托盘**：点关闭不会退出，最小化到托盘继续跑
- **暗色主题**：GitHub 同款 `#0d1117` 暗黑配色

> 运行：直接打开 `SysGauge/dist/SysGauge.exe`  
> 依赖：psutil, pystray, Pillow  
> 打包：`SysGauge/build.bat`

---

## 💰 DeepSeek 余额组件 — API 余额监控

DeepSeek API 账户余额桌面悬浮窗，充值玩家的心理安慰剂（看着余额一点点掉）。

- **实时余额**：定时拉取 DeepSeek API 余额，显示可用金额和总余额
- **设置面板**：API Key 配置、透明度、刷新间隔、主题切换
- **拖动 / 固定**：同款多屏四角吸附逻辑
- **系统托盘**：最小化到托盘不碍眼

> 运行：`DeepSeek余额组件/dist/DeepSeekBalance.exe`  
> 配置：首次运行右键 → 设置 → 填入 API Key  
> 打包：`DeepSeek余额组件/build.bat`  
> ⚠️ 配置文件 `deepseek_widget_config.json` 含 API Key，已加入 `.gitignore`

---

## 🎆 爱心与烟花 — 浏览器浪漫小动画

Canvas 纯前端动画，打开浏览器就能看。心形粒子 + 烟花特效。

没啥用，但好看。

> 运行：浏览器打开 `爱心与烟花/index.html`

---

## 🛠️ 打包备忘

两个 tkinter 组件都用 PyInstaller 打包，**必须在 Anaconda 环境下排除全家桶**，否则 EXE 从 ~20MB 膨胀到 ~168MB：

```
--exclude-module numpy scipy pandas matplotlib jupyter sklearn torch tensorflow
```

各自的 `build.bat` 已经写好了这个配方，双击即可重新打包。
