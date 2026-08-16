import sys, os, json, datetime as dt, shutil
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "scripts"))
import common, digest

# 用工作区内的临时目录（沙箱禁止在系统 Temp 下建子目录）
tmp = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_tmp_digest")
digest.ROOT = tmp
digest.DATA_DIR = os.path.join(tmp, "data")
os.makedirs(digest.DATA_DIR, exist_ok=True)

CFG = {
  "profile": {"researcher": "测试", "keywords": ["single-cell"], "methods": [],
              "databases": [], "negative_keywords": [], "email": ""},
  "sources": {},
  "schedule": {"timezone": "Asia/Shanghai", "since_days": 7},
  "digest": {"top_n": 20, "output_dir": "digest"},
  "anti_bubble": {"interval_days": 7, "suggest_keywords": ["review"]},
  "archive": {"root": "library", "index": "data/index.json", "methods_index": "data/methods.json"},
}
digest.load_config = lambda *a, **k: CFG

item = common.norm_record({
    "title": "Spatial atlas of the heart", "abstract": "single-cell RNA-seq",
    "published_date": dt.date.today().isoformat(), "url": "https://x/1",
    "doi": "10.9/x", "keywords": ["spatial transcriptomics", "atlas"]}, "openalex")
with open(os.path.join(digest.DATA_DIR, "raw.jsonl"), "w", encoding="utf-8") as f:
    f.write(json.dumps(item, ensure_ascii=False) + "\n")

try:
    sys.argv = ["digest.py", "--offline"]
    digest.main()

    dpath = os.path.join(tmp, "digest", dt.date.today().isoformat() + ".md")
    d = open(dpath, encoding="utf-8").read()
    assert "自动发现的相关主题词" in d, d
    assert "spatial transcriptomics" in d

    prefs = json.load(open(os.path.join(tmp, "config", "preferences.json"), encoding="utf-8"))
    assert prefs["keyword_history"] == ["single-cell"], prefs
    assert "spatial transcriptomics" in prefs["topic_distribution"], prefs
    assert prefs["last_run"] is not None and prefs["seen_count"] == 1

    # 第二遍：已推送过的应去重，不再出现在日报
    digest.main()
    prefs2 = json.load(open(os.path.join(tmp, "config", "preferences.json"), encoding="utf-8"))
    assert prefs2["seen_count"] == 1, prefs2
    print("DIGEST INTEGRATION TEST PASSED")
finally:
    shutil.rmtree(tmp, ignore_errors=True)
