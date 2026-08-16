# 课题组使用说明

## 模式一：共享一个仓库（推荐）

1. 组长把 literature-lab 推到一个 GitHub 仓库，开启 Actions 每日摘要。
2. 成员 fork，各自在 `config/config.local.yaml` 写自己的关键词（本地覆盖，不入库）。
3. 组内共享的「精读笔记 + 方法索引」通过 `data/index.json` / `data/methods.json` / `library/*/notes.md` 提交回主仓库（PDF 本体默认 gitignore，留在本地）。

## 模式二：每人独立使用

- 每人 clone 一份，`config.local.yaml` 写自己的偏好，`library/ ` 本地私有。

## 精读笔记入库约定（保证 methods 抽取有效）

每篇论文的 `notes.md` 建议按以下小节写：

```
## 一句话
## 统计方法 / 模型
## 数据
## 关键结果
## 创新点 / 不足
## 复现代码
```

`archive.py methods` 会自动抽取「统计方法」段落 + 所有 python 代码块，生成可检索的 `data/methods.json`。这样任何人问「某模型（如 Cox、MR、LASSO）在哪些文献里怎么用的」，都能直接定位并拿到复现代码。

## 分享个人文献库（可选）

- 把 `library/` 从 `.gitignore` 移除后，可连同 PDF 一起提交（注意仓库体积/版权）；或只用 git-lfs 存 PDF。
- 团队规模大时，建议 PDF 走私有网盘/Nextcloud，仓库只存元数据与笔记。
