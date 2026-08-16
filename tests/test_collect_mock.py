import sys, os, types, datetime as _dt
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "scripts"))
import collect

collect.time.sleep = lambda s: None  # 跳过网络节流

CFG = {
  "profile": {"email": "", "keywords": ["cancer"], "methods": []},
  "sources": {
    "pubmed": {"max_results": 10},
    "openalex": {"max_results": 10},
    "crossref": {"max_results": 10},
    "semantic_scholar": {"max_results": 10},
    "wos": {"enabled": True, "api_key": "k", "base_url": "https://api.clarivate.com/apis/wos-starter/v1"},
    "wechat_rss": {"enabled": True, "feed_urls": ["http://rss/x"]},
  },
}

# ---------- PubMed ----------
def mock_pubmed(url, timeout=30, headers=None):
    if "esearch" in url:
        return {"esearchresult": {"idlist": ["111", "222"]}}
    if "esummary" in url:
        return {"result": {"uids": ["111", "222"],
            "111": {"title": "Title A", "authors": [{"name": "Alice"}], "source": "Nature",
                    "pubdate": "2025", "sortpubdate": "2025/01/15 00:00",
                    "articleids": [{"idtype": "doi", "value": "10.1/a"}], "elocationid": ""},
            "222": {"title": "Title B", "authors": [], "source": "Cell", "pubdate": "2025",
                    "sortpubdate": "2025/01/10 00:00",
                    "articleids": [{"idtype": "pubmed", "value": "222"}], "elocationid": "10.1/b"}}}
    raise AssertionError("unexpected url " + url)

def mock_pubmed_text(url, timeout=30):
    return "<PubmedArticleSet><PubmedArticle><MedlineCitation><PMID>111</PMID></MedlineCitation>" \
           "<Article><Abstract><AbstractText Label=\"BACKGROUND\">Hello world.</AbstractText></Abstract></Article>" \
           "</PubmedArticle></PubmedArticleSet>"

collect.http_get_json = mock_pubmed
collect.http_get_text = mock_pubmed_text
recs = collect.pubmed(CFG, 7)
assert len(recs) == 2, recs
by = {r["pmid"]: r for r in recs}
assert by["111"]["title"] == "Title A" and by["111"]["doi"] == "10.1/a"
assert by["111"]["abstract"] == "Hello world." and by["111"]["year"] == 2025
assert by["111"]["published_date"] == "2025-01-15"
assert by["111"]["url"].endswith("/111/")
assert by["222"]["doi"] == "10.1/b", by["222"]["doi"]  # 从 elocationid 回退
print("pubmed mock OK")

# ---------- OpenAlex ----------
def mock_oa(url, timeout=30, headers=None):
    return {"results": [{
        "title": "Spatial atlas", "publication_year": 2025, "publication_date": "2025-02-01",
        "doi": "https://doi.org/10.2/oa", "cited_by_count": 42,
        "primary_location": {"source": {"display_name": "Nat Methods"}},
        "open_access": {"is_oa": True, "oa_url": "https://oa.pdf"},
        "authorships": [{"author": {"display_name": "Bob"}}],
        "concepts": [{"display_name": "Genetics"}, {"display_name": "Cell Biology"}],
        "abstract_inverted_index": {"the": [0], "cell": [1]},
    }]}
collect.http_get_json = mock_oa
recs = collect.openalex(CFG, 7)
r = recs[0]
assert r["title"] == "Spatial atlas" and r["doi"] == "10.2/oa"
assert r["abstract"] == "the cell" and r["pdf_url"] == "https://oa.pdf"
assert r["is_open_access"] is True and r["citations"] == 42
assert r["keywords"][0] == "Genetics"
print("openalex mock OK")

# ---------- Crossref ----------
def mock_cr(url, timeout=30, headers=None):
    return {"message": {"items": [
        {
            "title": ["CR Title"], "DOI": "10.3/cr",
            "published": {"date-parts": [[2025, 3, 1]]},
            "container-title": ["J Clin Invest"],
            "author": [{"given": "C", "family": "D"}],
            "abstract": "<jats:p>Abstract text</jats:p>", "is-referenced-by-count": 7,
            "URL": "https://example.org/cr",
            "link": [{"content-type": "application/pdf", "URL": "https://example.org/cr.pdf"}],
        },
        {"title": ["Null Pub"], "DOI": "10.3/null", "published": None, "author": None, "link": None},
    ]}}
collect.http_get_json = mock_cr
recs = collect.crossref(CFG, 7)
assert len(recs) == 2, recs  # null 字段不应导致崩溃
r = recs[0]
assert r["title"] == "CR Title" and r["doi"] == "10.3/cr"
assert r["abstract"] == "Abstract text" and r["pdf_url"] == "https://example.org/cr.pdf"
assert r["citations"] == 7 and r["authors"] == ["C D"] and r["year"] == 2025
assert recs[1]["year"] is None and recs[1]["authors"] == []
print("crossref mock OK")

# ---------- Semantic Scholar ----------
def mock_s2(url, timeout=30, headers=None):
    return {"data": [{
        "title": "S2 Title", "abstract": "S2 abstract", "year": 2025, "venue": "Science",
        "url": "https://s2.org/x", "externalIds": {"DOI": "10.4/s2", "PubMed": "999"},
        "openAccessPdf": {"url": "https://s2.pdf"}, "citationCount": 11,
        "publicationDate": "2025-04-01",
    }]}
collect.http_get_json = mock_s2
recs = collect.semantic_scholar(CFG, 7)
r = recs[0]
assert r["doi"] == "10.4/s2" and r["pmid"] == "999"
assert r["pdf_url"] == "https://s2.pdf" and r["is_open_access"] is True
print("semantic_scholar mock OK")

# ---------- Web of Science ----------
def mock_wos(url, timeout=30, headers=None):
    assert headers and headers.get("X-ApiKey") == "k", headers
    return {"hits": [{
        "title": "WoS T", "source": {"publishYear": 2025, "sourceTitle": "Lancet", "publishDate": "2025-05-01"},
        "identifiers": {"doi": "10.5/w"}, "links": {"record": "https://wos/x"},
        "citations": [{"count": 3}], "names": {"authors": [{"displayName": "E"}]},
    }]}
collect.http_get_json = mock_wos
recs = collect.wos(CFG, 7)
r = recs[0]
assert r["title"] == "WoS T" and r["doi"] == "10.5/w" and r["citations"] == 3
print("wos mock OK")

# ---------- 微信公众号 RSS ----------
class Entry(dict):
    def __getattr__(self, name):
        return self.get(name)

now = _dt.datetime.now()
fake_fp = types.ModuleType("feedparser")
fake_fp.parse = lambda url: {"entries": [
    Entry(title="WX Title", summary="<p>sum text</p>", link="https://wx/x", published_parsed=now.timetuple())
]}
sys.modules["feedparser"] = fake_fp
recs = collect.wechat(CFG, 7)
r = recs[0]
assert r["title"] == "WX Title" and r["abstract"] == "sum text"
assert r["url"] == "https://wx/x" and r["source"] == "wechat"
print("wechat mock OK")

# ---------- 跨源去重 + 合并 (H1) ----------
def test_collect_all_dedup():
    cfg = {"sources": {"a": {"enabled": True}, "b": {"enabled": True}}}
    def fa(cfg, d):
        return [collect.norm_record({"title": "Same", "doi": "10.1/x", "abstract": ""}, "a")]
    def fb(cfg, d):
        return [collect.norm_record({"title": "Same", "doi": "10.1/x", "abstract": "filled"}, "b")]
    orig = collect.SOURCES
    collect.SOURCES = [("a", fa), ("b", fb)]
    try:
        out = collect.collect_all(cfg, 7)
        assert len(out) == 1, out
        assert out[0]["abstract"] == "filled", out[0]  # 合并补全摘要
        print("collect_all dedup+merge OK")
    finally:
        collect.SOURCES = orig

test_collect_all_dedup()

print("COLLECT MOCK TESTS PASSED (6 sources + dedup)")
