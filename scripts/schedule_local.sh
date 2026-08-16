#!/usr/bin/env bash
# 本地 cron（Linux/macOS）。运行一次会打印需要加入 crontab 的行。
set -e
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
echo "请运行 crontab -e 并加入下面这一行（每天 08:00 运行）："
echo "0 8 * * * cd ${ROOT} && python scripts/digest.py >> digest.log 2>&1"
