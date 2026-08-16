---
name: literature-lab
description: Use when the user wants to search or monitor scientific literature, set up a daily literature digest/push, or archive and summarize papers. Triggers include 文献检索, 每日文献推送, 精读总结, 文献库, book-to-skill, 统计模型复现, 防信息茧房, Web of Science, 微信公众号.
---

# literature-lab

一个面向课题组的「文献雷达 + 精读 + 归档」技能：检索 → 每日推送 → 中英精读 → book-to-skill 归档 → 方法复现。

## Overview

四条核心原则：
1. **检索可复现**：所有来源都走公开 API（PubMed E-utilities / OpenAlex / Crossref / Semantic Scholar；WoS 与微信公众号为可选插件），输出统一 JSON 记录，带 DOI/链接。
2. **推送要防茧房**：偏好记忆存 `config/preferences.json`；每 `anti_bubble.interval_days` 天在摘要里强制插入「邻域/反向关键词」提示，绝不无限收敛到单一主题。
3. **精读结构化**：按 `templates/summary-bilingual.md` 产出中英对照（方法/结果/数据库与数据类型/创新点/不足/为何发此刊）。
4. **归档即技能**：每篇精读论文在 `library/<year>/<slug>/` 落一份 `SKILL.md`（book-to-skill 化），统计方法+复现代码进 `data/methods.json` 可检索。

## When to Use

- 用户给关键词/方法/数据库，要自动检索 PubMed / WoS / 公众号好文
- 要「每日推送相关领域文献」，且要记住偏好、定期防信息茧房
- 要「list + 链接」手动下载
- 要「中英对照」总结一篇论文（方法/结果/数据/创新/不足/为何发此刊）
- 要长期归档、从精读文献里提取「某统计模型怎么用」并复现

**不用于**：一次性查某个 PMID/DOI（直接 `archive.py add` 或检索即可）；写正式综述投稿（那是 `literature-review` 类 skill 的事，但可复用本库的检索输出）。

## Quick Reference（CLI）

| 命令 | 作用 |
|---|---|
| `python scripts/collect.py --since 7` | 按关键词检索各源，写 `data/raw.jsonl` |
| `python scripts/digest.py` | 生成当日摘要 `digest/YYYY-MM-DD.md`（去重+打分+防茧房） |
| `python scripts/archive.py add <doi|pdf路径>` | 归档一篇论文到 `library/` 并建 notes 脚手架 |
| `python scripts/archive.py index` | 重建 `data/index.json` |
| `python scripts/archive.py skill <slug>` | 把一篇精读 notes 转成 book-to-skill `SKILL.md` |
| `python scripts/archive.py methods` | 抽取所有统计方法+复现代码 → `data/methods.json` |
| `python scripts/feedback.py like <词>` | 标记喜欢的主题词（加权优化推送） |
| `python scripts/feedback.py dislike <词>` | 标记不喜欢的主题词（降权） |
| `python scripts/feedback.py show` | 查看当前偏好 / 关键词历史 / 主题分布 |
| `python scripts/bootstrap.py --run` | 一键初始化（venv+依赖+自检）并首次运行 |
| `python scripts/smoke_online.py` | 连通性 + 真实检索自检 |
| `python scripts/export.py bibtex/csv` | 导出文献库 → `data/library.bib` / `library.csv` |
| `python scripts/search.py "词"` | 一次性检索某关键词（记入记忆），`--save` 追加进 config |
| `python scripts/summarize.py prep <doi|pdf>` | 取原文材料，生成中英对照总结脚手架 |

## Workflow

```
检索 collect.py ──► 推送 digest.py ──► 精读 summarize.py ──► 归档 archive.py ──► 复现 methods
```

1. **首次**：编辑 `config/config.yaml`（关键词/方法/数据库/排除词/时区），`pip install -r requirements.txt`。
2. **检索**：`collect.py` 把所有来源归一化成一条 JSON：`{id, source, title, abstract, authors, year, journal, doi, url, pdf_url, keywords, published_date, citations, journal_tier}`。
3. **推送**：`digest.py` 去重（DOI/title hash）、打分排序、渲染摘要；命中排除词直接 -10 分。摘要末尾按周期放「防信息茧房提示」，并自动建议尚未覆盖的高频主题词（持续优化关键词）。用 `feedback.py like/dislike` 反馈偏好。
4. **精读**：`summarize.py prep` 取摘要/全文材料，Agent 按模板填中英对照分析。
5. **归档**：`archive.py add` 建目录+`metadata.json`+`notes.md`；`skill` 子命令把它转成可被检索的 mini-SKILL.md；`methods` 子命令抽取「模型→应用→代码」。
6. **调度**：GitHub Actions（`.github/workflows/daily-digest.yml`）或本地 `scripts/schedule_local.ps1`（Windows 计划任务）。

## Common Mistakes

- **忘配 `mailto`**：OpenAlex/Crossref/Semantic Scholar 建议填 `profile.email`，否则易被限流。
- **关键词太窄 → 茧房**：只给一个主题词会越来越窄；按提示定期补邻域/反向词。
- **把 digest 当已读**：`seen.json` 记录的是「已推送」，不是「已精读」；精读后要 `archive.py add` 才算入库。
- **WoS 未配 key 就启用**：WoS 是付费 API，`sources.wos.enabled` 为 true 但无 key 会跳过并告警。
- **微信源没跑 wewe-rss**：`sources.wechat_rss.feed_urls` 填的是 wewe-rss 产出的 RSS 地址，不是公众号原始链接。
