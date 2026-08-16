# Changelog

本项目的所有显著变更都会记录在此文件，格式遵循 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)。

## [0.1.0] - 2026-08-16

首个可用版本（v0.1.0）。

### 新增
- **检索**：PubMed（E-utilities）/ OpenAlex / Crossref / Semantic Scholar（免费）；Web of Science（可选 API 插件）；微信公众号（wewe-rss RSS 桥）
- **每日摘要** `digest.py`：按 DOI/title 去重、偏好打分排序、排除词降权、每 N 天自动插入「防信息茧房提示」、自动建议尚未覆盖的高频主题词
- **偏好管理** `feedback.py`：like / dislike / show，持续优化推送
- **中英对照精读** `summarize.py` + 模板：方法 / 结果 / 数据库与数据类型 / 创新点 / 不足 / 为何发此刊
- **归档** `archive.py`：add / index / skill（book-to-skill 化）/ methods（统计方法+复现代码 → data/methods.json）
- **调度**：GitHub Actions（每日 UTC 00:00）+ 本地计划任务（Windows PowerShell / Linux cron）

### 测试
- `tests/test_smoke.py`（核心逻辑）
- `tests/test_parsing.py`（OpenAlex 倒排索引 / PubMed 摘要 / 关键词建议）
- `tests/test_collect_mock.py`（6 个检索源解析，mock 验证）
- `tests/test_digest_integration.py`（日报生成 + 去重 + 偏好落盘）
