import sys, os, re, datetime as dt
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "scripts"))
import common, digest, archive, collect, summarize

# 1. common 归一化与 slug
r = common.norm_record({"title": "  A Study  ", "doi": "https://doi.org/10.1/x"}, "test")
assert r["title"] == "A Study", r
assert r["doi"] == "10.1/x", r
assert r["id"] == common.make_id(r)
assert common.slugify("单细胞 RNA 测序 空间 转录组") == "单细胞-rna-测序-空间-转录组"
print("common OK")

# 2. digest 打分
cfg = {"profile": {"keywords": ["single-cell"], "methods": ["deep learning"],
                   "databases": ["UK Biobank"], "negative_keywords": ["case report"]},
       "anti_bubble": {"interval_days": 7, "suggest_keywords": ["review"]},
       "digest": {"top_n": 20, "output_dir": "digest"}}
prefs = {"liked_topics": [], "disliked_topics": []}
good = common.norm_record({"title": "single-cell deep learning atlas",
                           "abstract": "UK Biobank cohort",
                           "published_date": dt.date.today().isoformat(),
                           "url": "https://example.com/x", "doi": "10.1/a",
                           "pdf_url": "https://example.com/x.pdf"}, "x")
bad = common.norm_record({"title": "a case report of one patient",
                          "abstract": "", "published_date": dt.date.today().isoformat()}, "x")
assert digest.score(good, cfg, prefs) > 0
assert digest.score(bad, cfg, prefs) < 0
print("digest.score OK")

# 3. 防茧房
prefs2 = {"last_explore_prompt": None}
msg = digest.anti_bubble_section(prefs2, cfg, [good])
assert "防信息茧房" in msg and prefs2["last_explore_prompt"] is not None
assert digest.anti_bubble_section(prefs2, cfg, [good]) == ""
print("anti_bubble OK")

# 4. 渲染
md = digest.render([good], cfg, prefs)
assert "single-cell deep learning atlas" in md and "链接" in md
print("render OK")

# 5. archive 模板与 fence
assert "复现代码" in archive.NOTES_TEMPLATE and archive.FENCE in archive.NOTES_TEMPLATE
print("archive template OK")

# 6. 方法段 + 代码块抽取
notes = ("## 一句话\n这是摘要\n\n## 统计方法 / 模型\n用 Cox 回归建模\n\n"
         "## 复现代码\n" + archive.FENCE + "python\nimport lifelines\n" + archive.FENCE + "\n")
def section(n, prefix):
    pat = re.compile(r"##\s*" + re.escape(prefix) + r"[^\n]*\n(.*?)(?=\n## |\Z)", re.S)
    m = pat.search(n)
    return m.group(1).strip() if m else ""
assert section(notes, "统计方法") == "用 Cox 回归建模"
codes = re.findall(archive.FENCE + r"(?:python|py)?\s*\n(.*?)" + archive.FENCE, notes, re.S)
assert codes[0].strip().startswith("import lifelines")
print("archive extraction OK")

# 7. collect 字段完整
full = common.norm_record({"title": "t", "doi": "10.2/y"}, "pubmed")
for k in ["id","source","title","abstract","authors","year","journal","doi","pmid","url","pdf_url","keywords","published_date","citations","journal_tier","is_open_access"]:
    assert k in full, k
print("collect schema OK")

print("ALL SMOKE TESTS PASSED")
