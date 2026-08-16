# 接入微信公众号（wewe-rss）

literature-lab 通过「公众号 → RSS」桥来抓公众号文章，推荐 [wewe-rss](https://github.com/cooderl/wewe-rss)（免费、可私有化部署）。

## 1. 部署 wewe-rss

按 wewe-rss 仓库 README，用 Docker 起一个实例（需要一个微信公众号的读书/订阅权限账号，具体见其文档）：

```bash
docker run -d --name wewe-rss -p 4000:4000 \
  -e DATABASE_URL="file:../data/wewe-rss.db" \
  -e AUTH_CODE="你的授权码" \
  -v $(pwd)/data:/app/data \
  cooderl/wewe-rss-sqlite:latest
```

## 2. 获取公众号 RSS 地址

打开 `http://localhost:4000`，添加你要订阅的公众号（如「BioArt」「丁香学术」「iNature」等学术号），每个公众号会生成一个 RSS/ATOM 地址。

## 3. 填入配置

在 `config/config.yaml`：

```yaml
sources:
  wechat_rss:
    enabled: true
    feed_urls:
      - "http://localhost:4000/feeds/xxxx.atom"
      - "http://localhost:4000/feeds/yyyy.atom"
```

## 4. 注意事项

- `feed_urls` 填的是 wewe-rss 生成的 RSS 地址，不是公众号原始链接。
- wewe-rss 需要常驻运行；若放在服务器上，`localhost` 改成服务器地址。
- 抓到的公众号文章会进日报（source=wechat），标题/摘要会被打分，可结合 `profile.negative_keywords` 过滤无关推送。
