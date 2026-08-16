# 安装与配置

## 前置条件

- Python 3.10+（推荐 3.11+）
- 可访问互联网（PubMed/OpenAlex/Crossref 均为公开 API）

## 1. 克隆与安装

```bash
git clone <你的仓库地址> literature-lab
cd literature-lab
pip install -r requirements.txt
```

`feedparser`（微信源）与 `pdfminer.six`（PDF 抽取）为可选依赖，未装时对应功能自动跳过。

## 2. 填写配置

编辑 `config/config.yaml`：

- `profile.keywords`：主题关键词（每条跑一次检索）
- `profile.methods`：关注的统计方法/模型（命中加权更高）
- `profile.databases`：关注的数据库/数据类型（如 UK Biobank、GWAS）
- `profile.negative_keywords`：排除词（命中降 10 分）
- `profile.email`：强烈建议填，OpenAlex/Crossref/Semantic Scholar 会提高限流额度

私有项（如 WoS key、LLM key）建议放 `config/config.local.yaml`（已被 gitignore），会自动深合并覆盖。

## 3. 首次跑通

```bash
# 只检索，不生成摘要
python scripts/collect.py --since 7
# 检索 + 生成今日摘要（推荐直接跑这个）
python scripts/digest.py
```

日报在 `digest/YYYY-MM-DD.md`，检索原始结果在 `data/raw.jsonl`。

## 4. 安装为 Agent Skill

```bash
cp -r literature-lab ~/.claude/skills/       # Claude Code
cp -r literature-lab ~/.agents/skills/       # Codex
npx skills add <owner>/literature-lab@literature-lab   # skills CLI
```

之后在 agent 里说「用 literature-lab 检索 XX 领域近一周文献」即可。

## 5. 每日调度

- **GitHub Actions**：fork 后到 Settings → Actions → General，允许 workflow；再到 Actions 页手动触发一次测试。cron 为 UTC 00:00（北京 08:00），可在 `.github/workflows/daily-digest.yml` 改。
- **本地 Windows**：```powershell
powershell -ExecutionPolicy Bypass -File scripts/schedule_local.ps1
```
- **本地 Linux/macOS**：```bash
bash scripts/schedule_local.sh   # 打印 cron 行，复制进 crontab -e
```
