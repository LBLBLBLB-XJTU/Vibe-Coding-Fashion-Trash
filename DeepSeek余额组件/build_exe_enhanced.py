"""
DeepSeek 余额小组件 - 增强版构建脚本

自动安装依赖并打包为 Windows EXE 文件。
"""

import subprocess
import sys
import os
import shutil
import time


def run_command(cmd, description="", check=True):
    """运行命令并打印输出"""
    print(f"\n{'='*60}")
    print(f"  [{description}]")
    print(f"  $ {cmd}")
    print(f"{'='*60}")
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=300,
        )
        if result.stdout:
            print(result.stdout)
        if result.stderr:
            # 只打印非 pip 进度条的错误信息
            for line in result.stderr.splitlines():
                stripped = line.strip()
                if stripped and not stripped.startswith("WARNING: Ignoring"):
                    print(stripped)
        if check and result.returncode != 0:
            raise RuntimeError(
                f"命令失败 (exit code {result.returncode}): {cmd}"
            )
        return result
    except subprocess.TimeoutExpired:
        raise RuntimeError(f"命令超时: {cmd}")


def install_dependencies():
    """安装项目依赖"""
    print("\n" + "=" * 60)
    print("  步骤 1/4: 安装项目依赖")
    print("=" * 60)

    packages = ["customtkinter", "requests", "pyinstaller", "pystray", "Pillow"]

    for pkg in packages:
        print(f"\n  -> 安装 {pkg} ...")
        try:
            result = run_command(
                f'"{sys.executable}" -m pip install {pkg}',
                description=f"安装 {pkg}",
                check=False,
            )
            if result.returncode == 0:
                print(f"  [OK] {pkg} 安装成功")
            else:
                # 尝试带 --break-system-packages
                print(f"  -> 重试 {pkg} (带 --break-system-packages) ...")
                result = run_command(
                    f'"{sys.executable}" -m pip install {pkg} --break-system-packages',
                    description=f"安装 {pkg} (强制)",
                    check=True,
                )
                print(f"  [OK] {pkg} 安装成功")
        except RuntimeError as e:
            print(f"  [ERROR] 安装 {pkg} 失败: {e}")
            raise

    print("\n  [OK] 所有依赖安装完成")


def build_exe():
    """使用 PyInstaller 打包 EXE"""
    print("\n" + "=" * 60)
    print("  步骤 2/4: 使用 PyInstaller 打包 EXE")
    print("=" * 60)

    # 获取当前目录（脚本所在目录）
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)

    # PyInstaller 命令
    pyinstaller_args = [
        sys.executable, "-m", "PyInstaller",
        "--onefile",
        "--windowed",
        "--name", "DeepSeekBalance",
        "--add-data", f"deepseek_api.py{os.pathsep}.",
        "--add-data", f"config.py{os.pathsep}.",
        "--add-data", f"widget.py{os.pathsep}.",
        "--hidden-import", "customtkinter",
        "--hidden-import", "requests",
        "--hidden-import", "pystray",
        "--hidden-import", "PIL",
        "--hidden-import", "PIL._tkinter_finder",
        "--clean",
        "main.py",
    ]

    cmd = " ".join(pyinstaller_args)
    print(f"  运行: {cmd}")
    print("  这可能需要 1-3 分钟...\n")

    try:
        result = run_command(cmd, "PyInstaller 打包")
        print("  [OK] PyInstaller 打包完成")
    except RuntimeError as e:
        print(f"  [ERROR] PyInstaller 打包失败: {e}")
        # 运行详细版以便调试
        print("\n  -> 尝试详细模式重试...")
        pyinstaller_args.insert(1, "--debug")
        cmd = " ".join(pyinstaller_args)
        try:
            run_command(cmd, "PyInstaller 打包 (详细模式)", check=True)
        except RuntimeError as e2:
            print(f"  [ERROR] 打包仍然失败: {e2}")
            raise


def copy_exe():
    """复制生成的 EXE 到桌面目录"""
    print("\n" + "=" * 60)
    print("  步骤 3/4: 复制 EXE 到目标目录")
    print("=" * 60)

    script_dir = os.path.dirname(os.path.abspath(__file__))
    dist_exe = os.path.join(script_dir, "dist", "DeepSeekBalance.exe")
    target_exe = os.path.join(script_dir, "DeepSeekBalance.exe")

    if not os.path.exists(dist_exe):
        raise FileNotFoundError(
            f"未找到生成的 EXE 文件: {dist_exe}"
        )

    print(f"  源文件: {dist_exe}")
    print(f"  目标位置: {target_exe}")

    # 如果已有旧文件，先删除
    if os.path.exists(target_exe):
        os.remove(target_exe)
        print("  已删除旧的 EXE 文件")

    shutil.copy2(dist_exe, target_exe)
    file_size = os.path.getsize(target_exe)
    print(f"  [OK] EXE 已复制完成 ({file_size / 1024 / 1024:.1f} MB)")


def clean_up():
    """清理构建临时文件"""
    print("\n" + "=" * 60)
    print("  步骤 4/4: 清理构建临时文件")
    print("=" * 60)

    script_dir = os.path.dirname(os.path.abspath(__file__))

    # 要清理的目录和文件
    dirs_to_remove = [
        os.path.join(script_dir, "build"),
        os.path.join(script_dir, "dist"),
        os.path.join(script_dir, "__pycache__"),
    ]

    files_to_remove = [
        os.path.join(script_dir, "main.spec"),
    ]

    for d in dirs_to_remove:
        if os.path.exists(d):
            shutil.rmtree(d, ignore_errors=True)
            print(f"  已删除目录: {d}")

    for f in files_to_remove:
        if os.path.exists(f):
            os.remove(f)
            print(f"  已删除文件: {f}")

    print("  [OK] 清理完成")


def verify_result():
    """验证构建结果"""
    print("\n" + "=" * 60)
    print("  验证构建结果")
    print("=" * 60)

    script_dir = os.path.dirname(os.path.abspath(__file__))
    exe_path = os.path.join(script_dir, "DeepSeekBalance.exe")

    if os.path.exists(exe_path):
        file_size = os.path.getsize(exe_path)
        print(f"\n  [SUCCESS] 构建成功!")
        print(f"  EXE 位置: {exe_path}")
        print(f"  文件大小: {file_size / 1024 / 1024:.1f} MB")
        return True
    else:
        print(f"\n  [FAILED] EXE 文件未找到: {exe_path}")
        return False


def main():
    """主流程"""
    start_time = time.time()

    print("=" * 60)
    print("  DeepSeek 余额小组件 - EXE 构建工具 (增强版)")
    print("  " + time.strftime("%Y-%m-%d %H:%M:%S"))
    print("=" * 60)

    try:
        # 步骤 1: 安装依赖
        install_dependencies()

        # 步骤 2: 打包 EXE
        build_exe()

        # 步骤 3: 复制 EXE
        copy_exe()

        # 步骤 4: 清理临时文件
        clean_up()

        # 验证
        success = verify_result()

        elapsed = time.time() - start_time
        print(f"\n{'='*60}")
        if success:
            print(f"  总耗时: {elapsed:.1f} 秒")
            print(f"  构建成功！请运行 DeepSeekBalance.exe")
        else:
            print(f"  构建失败！")
        print(f"{'='*60}")

        return 0 if success else 1

    except Exception as e:
        print(f"\n{'='*60}")
        print(f"  [ERROR] 构建过程中出现错误:")
        print(f"  {e}")
        print(f"{'='*60}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
