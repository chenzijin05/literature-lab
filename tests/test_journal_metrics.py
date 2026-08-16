import sys, os, csv, shutil
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "scripts"))
import common, journal_metrics, digest
import fetch_journal_metrics as fetch

tmp = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_tmp_jm")
os.makedirs(tmp, exist_ok=True)
csv_path = os.path.join(tmp, "journal_metrics.csv")
with open(csv_path, "w", encoding="utf-8", newline="") as f:
    w = csv.writer(f)
    w.writerow(["issn", "journal", "impact_factor", "jcr_quartile", "cas_partition"])
    w.writerow(["0028-0836", "Nature", "50.5", "Q1", "1区"])
    w.writerow(["", "Science", "44.7", "Q1", "1区"])

# 1. 按 ISSN 匹配
by_issn, by_name = journal_metrics.load(csv_path)
r1 = common.norm_record({"title": "t", "journal": "Nature", "issn": "0028-0836"}, "x")
journal_metrics.enrich(r1, by_issn, by_name)
assert r1["impact_factor"] == "50.5" and r1["jcr_quartile"] == "Q1" and r1["cas_partition"] == "1区", r1

# 2. 按期刊名匹配
r2 = common.norm_record({"title": "t", "journal": "science", "issn": ""}, "x")
journal_metrics.enrich(r2, by_issn, by_name)
assert r2["impact_factor"] == "44.7", r2
print("journal_metrics load/enrich OK")

# 3. render 显示指标行
cfg = {"profile": {"researcher": "t", "keywords": [], "methods": [], "databases": []}}
md = digest.render([r1], cfg, {})
assert "期刊指标" in md and "IF 50.5" in md and "JCR Q1" in md and "中科院 1区" in md, md
print("render metrics OK")

# 4. fetch 解析逻辑（合成表头）
cas = fetch._parse_cas(
    "Journal,年份,ISSN,Review,OA Journal Index（OAJ）,Open Access,Web of Science,标注,大类,大类分区,Top,小类1,小类1分区\n"
    "NATURE,2025,0028-0836,否,否,否,SCIE,,综合性期刊,1,是,MULTIDISCIPLINARY,1\n")
assert cas.get("0028-0836", {}).get("cas_partition") == "1区", cas
jcr = fetch._parse_jcr(
    "Rank,Journal Name,JIF 2024,JIF Quartile,Areas,Publisher,Country,JIF Rank,5-Year JIF,JCI,ISSN,eISSN,Abbreviated Journal,Total Cites,Total Articles,Citable Items,Cited Half-Life,Citing Half-Life,JIF Without Self-Cites,JCR Year\n"
    "1,NATURE,50.5,Q1,Medicine,WILEY,US,1/100,60,10,0028-0836,1476-4687,NATURE,100,2,3,4,5,50.4,2024\n")
assert jcr.get("0028-0836", {}).get("impact_factor") == "50.5", jcr
assert jcr.get("0028-0836", {}).get("jcr_quartile") == "Q1", jcr
print("fetch parse OK (真实表头)")

shutil.rmtree(tmp, ignore_errors=True)
print("JOURNAL METRICS TESTS PASSED")
