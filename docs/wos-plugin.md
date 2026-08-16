# 接入 Web of Science（可选插件）

Web of Science 无免费公开 API。literature-lab 将其做成可选插件，接 Clarivate 的 **Web of Science Starter API**（付费，需机构订阅）。

## 1. 获取 API key

- 前往 Clarivate Developer Portal（[api.clarivate.com](https://api.clarivate.com)）
- 申请 Web of Science Starter API 的 API key（需机构授权）

## 2. 填入配置

在 `config/config.local.yaml`（勿提交 key 到公开仓库）：

```yaml
sources:
  wos:
    enabled: true
    api_key: "你的Clarivate-API-key"
    base_url: "https://api.clarivate.com/apis/wos-starter/v1"
```

## 3. 说明

- 未启用或无 key 时，`wos` 源自动跳过并在日志打印提示，不影响其它源。
- 免费源（PubMed/OpenAlex/Crossref/Semantic Scholar）已覆盖绝大多数场景；WoS 主要用于补「被引/期刊分区」等指标。
- 若用更高级的 WoS Expanded API，可自行在 `scripts/collect.py` 的 `wos()` 函数里扩展字段。
