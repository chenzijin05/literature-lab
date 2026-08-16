"""literature-lab 公共工具：配置加载、JSON 读写、HTTP、归一化。"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
import re
import sys
import urllib.request

# Windows 控制台可能非 UTF-8：强制 stdout/stderr 用 UTF-8，避免打印中文/箭头时 UnicodeEncodeError
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(ROOT, "data")
UA = "literature-lab/0.1"


def _deep_merge(base: dict, override: dict) -> dict:
    out = dict(base)
    for k, v in override.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _deep_merge(out[k], v)
        else:
            out[k] = v
    return out


def load_config(path=None) -> dict:
    """加载 config/config.yaml，并用 config.local.yaml 深合并覆盖。"""
    try:
        import yaml
    except ImportError:
        raise SystemExit("缺少 pyyaml，请先: pip install -r requirements.txt")
    base_path = path or os.path.join(ROOT, "config", "config.yaml")
    with open(base_path, encoding="utf-8") as f:
        cfg = yaml.safe_load(f) or {}
    local_path = os.path.join(ROOT, "config", "config.local.yaml")
    if os.path.exists(local_path):
        with open(local_path, encoding="utf-8") as f:
            cfg = _deep_merge(cfg, yaml.safe_load(f) or {})
    return cfg


def load_json(path: str, default):
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    return default


def save_json(path: str, data) -> None:
    d = os.path.dirname(path)
    if d:
        os.makedirs(d, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def http_get_json(url: str, timeout: int = 30, headers=None):
    h = {"User-Agent": UA}
    if headers:
        h.update(headers)
    req = urllib.request.Request(url, headers=h)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def http_get_text(url: str, timeout: int = 30) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", errors="replace")


def make_id(record: dict) -> str:
    key = (record.get("doi") or record.get("pmid") or record.get("title") or "").strip().lower()
    return hashlib.sha1(key.encode("utf-8")).hexdigest()[:16]


def slugify(text: str, maxlen: int = 80) -> str:
    text = re.sub(r"[^\w\- ]", "", text, flags=re.UNICODE)
    text = re.sub(r"\s+", "-", text.strip()).strip("-")
    return text[:maxlen].rstrip("-").lower() or "untitled"


def strip_tags(html: str) -> str:
    return re.sub(r"<[^>]+>", " ", html or "")


def now_iso() -> str:
    return dt.datetime.now().isoformat(timespec="seconds")


def norm_record(raw: dict, source: str) -> dict:
    rec = {
        "id": "",
        "source": source,
        "title": "",
        "abstract": "",
        "authors": [],
        "year": None,
        "journal": "",
        "doi": "",
        "pmid": "",
        "url": "",
        "pdf_url": "",
        "keywords": [],
        "published_date": "",
        "citations": None,
        "journal_tier": None,
        "is_open_access": False,
        "issn": "",
        "impact_factor": "",
        "jcr_quartile": "",
        "cas_partition": "",
    }
    rec.update(raw)
    rec["title"] = (rec.get("title") or "").strip()
    rec["abstract"] = (rec.get("abstract") or "").strip()
    rec["doi"] = (rec.get("doi") or "").lower().replace("https://doi.org/", "").strip()
    rec["id"] = make_id(rec)
    return rec
