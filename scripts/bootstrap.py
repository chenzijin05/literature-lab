"""一键初始化：建虚拟环境 + 装依赖 + 连通性/检索自检 + 可选首次运行。

用法：
    python scripts/bootstrap.py            # 完整初始化（venv + pip + 自检）
    python scripts/bootstrap.py --no-venv  # 用当前 python，只装依赖 + 自检
    python scripts/bootstrap.py --check    # 只做自检（不装依赖）
    python scripts/bootstrap.py --run      # 初始化后立即跑一次 digest
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-venv", action="store_true", help="不建虚拟环境，直接用当前 python")
    ap.add_argument("--check", action="store_true", help="只做连通性/检索自检")
    ap.add_argument("--run", action="store_true", help="初始化后立即跑一次 digest")
    args = ap.parse_args()

    if args.check:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        import smoke_online
        return smoke_online.main()

    py = sys.executable
    if not args.no_venv:
        venv = os.path.join(ROOT, ".venv")
        if not os.path.exists(venv):
            print("[1/3] 创建虚拟环境 .venv ...")
            subprocess.run([sys.executable, "-m", "venv", venv], check=True)
        py = os.path.join(venv, "Scripts", "python.exe") if os.name == "nt" else os.path.join(venv, "bin", "python")

    print("[2/3] 安装依赖 ...")
    subprocess.run([py, "-m", "pip", "install", "-r", os.path.join(ROOT, "requirements.txt")], check=True)

    print("[3/3] 自检 ...")
    subprocess.run([py, os.path.join(ROOT, "scripts", "smoke_online.py")])

    if args.run:
        print("首次运行 digest ...")
        subprocess.run([py, os.path.join(ROOT, "scripts", "digest.py")])
    else:
        print("初始化完成。以后每天运行：")
        print("  " + py + " " + os.path.join(ROOT, "scripts", "digest.py"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
