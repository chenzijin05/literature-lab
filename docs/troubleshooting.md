# 常见问题排查

## 运行前

- **`pip install` 很慢/超时**：换国内镜像
  ```bash
  pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
  ```
- **提示缺少 pyyaml**：`pip install -r requirements.txt`（未装全）。

## 检索时

- **OpenAlex 报 429 Too Many Requests**：
  - 在 `config.yaml` 的 `profile.email` 填邮箱（提高限流额度）；
  - 学校/公司共享 IP 容易限流，可临时把 `sources.openalex.enabled` 设为 false（PubMed/Crossref 仍可用）。
- **全部源 FAIL / 连不上**：多为网络/代理问题。先跑 `python scripts/smoke_online.py` 看哪个源通、哪个不通。
- **日报为空「今日无新增文献」**：
  - 关键词太窄、或最近 `schedule.since_days` 天确实无新文献；
  - 用 `smoke_online.py` 的「真实检索自检」确认能不能取到数据。

## 公众号

- **微信源没有输出**：`sources.wechat_rss.feed_urls` 填的是 wewe-rss 生成的 RSS 地址，不是公众号原始链接；wewe-rss 需常驻运行。见 [wechat-setup.md](wechat-setup.md)。

## 调度

- **GitHub Actions 不触发**：fork 后到 Settings → Actions → General 开启 workflow，再去 Actions 页手动 Run workflow 一次测试。
- **中文显示乱码**：已内置强制 UTF-8 输出；建议用 Windows Terminal / VS Code 终端（而非老式 cmd）。

## 期刊指标

- **日报里没有「期刊指标」行**：先运行 `python scripts/fetch_journal_metrics.py` 下载数据（生成 `data/journal_metrics.csv`）；下载失败多为网络，可换代理重试。
- **部分期刊匹配不到**：按 ISSN（优先）和期刊名匹配；新刊/改名刊可能缺失，可在 `data/journal_metrics.csv` 手工补一行。

## 其他

- **想临时换关键词**：改 `config/config.local.yaml`（不会被提交），会覆盖 `config.yaml` 同名项。
