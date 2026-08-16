"""校验 config/config.yaml 能被正确解析、结构完整。需 pyyaml（CI 已装，本地无则跳过）。"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "scripts"))

try:
    import yaml  # noqa: F401
except ImportError:
    print("SKIP: 未安装 pyyaml，跳过 config 校验")
    sys.exit(0)

import common

cfg = common.load_config()
assert "profile" in cfg and "sources" in cfg and "digest" in cfg
assert isinstance(cfg["profile"]["keywords"], list)
for s in ("pubmed", "openalex", "crossref", "semantic_scholar", "wos", "wechat_rss"):
    assert s in cfg["sources"], s
assert "top_n" in cfg["digest"] and "serendipity" in cfg["digest"]
assert "notify" in cfg and "anti_bubble" in cfg and "archive" in cfg
print("CONFIG VALIDATION PASSED")
