import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "scripts"))
import collect, digest


def test_oa_abstract():
    inv = {"the": [0, 2], "cat": [1], "sat": [3]}
    assert collect._oa_abstract(inv) == "the cat the sat"
    assert collect._oa_abstract(None) == ""


def test_pubmed_abstracts():
    xml = '''<PubmedArticleSet>
<PubmedArticle><MedlineCitation><PMID>123</PMID></MedlineCitation>
<Article><Abstract><AbstractText Label="BACKGROUND">Hello world.</AbstractText>
<AbstractText Label="METHODS">We did X.</AbstractText></Abstract></Article>
</PubmedArticle>
<PubmedArticle><MedlineCitation><PMID>456</PMID></MedlineCitation>
<Article><Abstract><AbstractText>No label.</AbstractText></Abstract></Article>
</PubmedArticle>
</PubmedArticleSet>'''
    m = collect._parse_pubmed_abstracts(xml)
    assert m["123"] == "Hello world. We did X.", m["123"]
    assert m["456"] == "No label.", m["456"]


def test_suggest_keywords():
    cfg = {"profile": {"keywords": ["single-cell"], "methods": ["Mendelian randomization"]}}
    items = [
        {"keywords": ["single-cell", "spatial transcriptomics", "atlas", "Mendelian randomization"]},
        {"keywords": ["spatial transcriptomics", "imaging"]},
    ]
    s = digest.suggest_keywords(items, cfg, {})
    assert "spatial transcriptomics" in s
    assert "single-cell" not in s
    assert "Mendelian randomization" not in s  # methods 也应排除
    print("suggest:", s)


test_oa_abstract()
test_pubmed_abstracts()
test_suggest_keywords()
print("PARSING TESTS PASSED")
