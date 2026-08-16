# literature-lab

面向课题组的「文献雷达 + 精读 + 归档」Agent Skill：检索 → 每日推送 → 中英精读 → book-to-skill 归档 → 方法复现。

## 它能做什么（对照四大目标）

1. **检索与每日推送** — 输入关键词/方法/数据库，自动从 **PubMed / OpenAlex / Crossref / Semantic Scholar**（免费）检索；**Web of Science**（可选 API）与**微信公众号**（wewe-rss 桥）为插件。定时生成 `digest/YYYY-MM-DD.md`，去重、按偏好打分排序；`config/preferences.json` 记住偏好，每 7 天自动插入「防信息茧房提示」。
2. **list + 链接** — 摘要里每条带 DOI、PubMed/原文链接、OA PDF 链接，手动点击下载。
3. **中英对照精读** — 按模板总结：方法 / 结果 / 数据库与数据类型 / 创新点 / 不足 / 为何发此刊（中英双语）。
4. **归档即技能** — `archive.py` 把论文归档到 `library/<year>/<slug>/`；精读笔记可转成 book-to-skill 的 `SKILL.md`；`methods` 子命令抽取「统计模型 → 应用 → 复现代码」到 `data/methods.json`。

## 快速开始

```bash
git clone <你的仓库地址> literature-lab
cd literature-lab
# 1. 编辑 config/config.yaml 填入关键词/方法/数据库/邮箱（可选）
# 2. 一键初始化：建 venv + 装依赖 + 连通性自检 + 首次运行
python scripts/bootstrap.py --run
# 以后每天生成日报（依赖装在 .venv 里）：
.venv/Scripts/python scripts/digest.py
```

生成的日报在 `digest/YYYY-MM-DD.md`。

> 只想先确认网络/检索是否正常：`python scripts/bootstrap.py --check`。

## 安装为 Agent Skill

把整个仓库复制到你的技能目录，即可在 Claude Code / Codex 等 agent 里用 `literature-lab` 触发：

```bash
# Claude Code
cp -r literature-lab ~/.claude/skills/
# Codex
cp -r literature-lab ~/.agents/skills/
# 或用 skills CLI
npx skills add <owner>/literature-lab@literature-lab
```

## 命令速查

| 命令 | 作用 |
|---|---|
| `python scripts/collect.py --since 7` | 检索各源 → `data/raw.jsonl` |
| `python scripts/digest.py` | 生成今日摘要（去重+打分+防茧房） |
| `python scripts/summarize.py prep <doi|pdf>` | 生成中英对照总结脚手架 |
| `python scripts/archive.py add <doi|pdf>` | 归档一篇论文 + 建 notes |
| `python scripts/archive.py index` | 重建 `data/index.json` |
| `python scripts/archive.py skill <slug>` | 精读笔记 → book-to-skill `SKILL.md` |
| `python scripts/archive.py methods` | 抽取方法+复现代码 → `data/methods.json` |
| `python scripts/feedback.py like/dislike <词>` | 标记喜欢/不喜欢的主题词，优化推送 |
| `python scripts/feedback.py show` | 查看偏好 / 关键词历史 / 主题分布 |
| `python scripts/bootstrap.py --run` | 一键初始化（venv+依赖+自检）并首次运行 |
| `python scripts/smoke_online.py` | 连通性 + 真实检索自检 |
| `python scripts/export.py bibtex/csv` | 导出文献库 → `data/library.bib` / `library.csv` |
| `python scripts/search.py "词"` | 一次性检索某关键词（并记入偏好记忆），`--save` 追加进 config |
| `python scripts/fetch_journal_metrics.py` | 下载影响因子/JCR分区/中科院分区数据 → `data/journal_metrics.csv` |

## 每日自动调度（两者都支持）

- **GitHub Actions**：仓库自带 `.github/workflows/daily-digest.yml`（UTC 00:00 = 北京 08:00）。fork 后到 Actions 开启即可；状态文件（`seen.json`/`preferences.json`）自动提交回仓库。
- **本地**：Windows 运行 `scripts/schedule_local.ps1`（注册计划任务）；Linux/macOS 用 `scripts/schedule_local.sh` 打印 cron 行。
- **推送通知（可选）**：在 `config.yaml` 的 `notify:` 段填企业微信/钉钉 webhook，日报生成后自动推送到群；不填则日报以文件形式提交到仓库。

## 期刊指标（影响因子 / JCR 分区 / 中科院分区）

日报里的 `- 期刊指标：IF xx | JCR Q1 | 中科院 1区` 来自本地数据文件 `data/journal_metrics.csv`：

1. 先下载一次数据（约 7MB，两个开源镜像）：
   `python scripts/fetch_journal_metrics.py`
2. 之后每次 `digest.py` / `search.py` 会自动按 ISSN（优先）或期刊名匹配并显示。

- 影响因子 = **JIF 2024**（JCR 2024 版，最新公开版）
- JCR 分区 = Q1-Q4
- 中科院分区 = **2025 版**（2025-03-20 发布）

数据源为开源镜像（[IvyScience/journalQuartile](https://github.com/IvyScience/journalQuartile)、[theabhijitdn/WoS-JCR-Impact-Factor-Explorer-2025](https://github.com/theabhijitdn/WoS-JCR-Impact-Factor-Explorer-2025)），仅供课题组内部研究参考；如需官方数据请通过机构订阅 JCR / 中科院分区表。

## 目录结构

```
literature-lab/
  SKILL.md                  # Agent Skill 主指令
  config/
    config.yaml             # 关键词/来源/调度/防茧房（可 config.local.yaml 覆盖）
    preferences.json        # 偏好记忆（自动更新）
  scripts/
    collect.py              # 检索（PubMed/OpenAlex/Crossref/SemanticScholar/WoS/微信）
    digest.py               # 每日摘要 + 去重 + 打分 + 防茧房
    summarize.py            # 中英对照精读脚手架
    archive.py              # 归档 + book-to-skill + 方法复现代码抽取
    schedule_local.ps1/.sh  # 本地调度
  templates/                # 中英总结模板 / book-to-skill 模板
  data/                     # seen.json / index.json / methods.json（运行生成）
  digest/                   # 每日日报（YYYY-MM-DD.md）
  library/                  # 个人文献库（本地，默认不入库）
```

## 更多文档

- [安装与配置](docs/installation.md)
- [接入微信公众号（wewe-rss）](docs/wechat-setup.md)
- [接入 Web of Science](docs/wos-plugin.md)
- [课题组使用说明](docs/group-usage.md)
- [常见问题排查](docs/troubleshooting.md)
- [日报输出示例](examples/digest-example.md)

## 基于哪些开源项目改造

- [Leutenegger/book-to-skill](https://github.com/Leutenegger/book-to-skill) — 文档 → Skill 的精读归档思路
- [ClawBio lit-synthesizer](https://github.com/ClawBio/ClawBio) — 检索+总结+引用图
- [cooderl/wewe-rss](https://github.com/cooderl/wewe-rss) — 公众号 RSS 桥（外部依赖）

## License

MIT
