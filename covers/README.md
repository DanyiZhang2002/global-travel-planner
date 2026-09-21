# covers/

本目录用于存放当前 app 的**封面截图**（首屏视觉占位图），供 `<app cover>` 标签 / R15 注册接口 `cover` 字段使用。

## 命名建议

按版本号命名，便于和 CHANGELOG 对齐、追溯每个版本的视觉变更：

```
covers/
  v1.png    # 首次注册版本
  v2.png    # 第二次发布
  v3.png    # ...
```

可选后缀（如某一版有多张候选图供用户选）：
```
covers/v5-hero.png
covers/v5-overview.png
```

## 截图生成方式

用 skill 自带脚本一键截 1600x900 首屏（无需 puppeteer / playwright）：

```bash
# entryUrl 从 .last-build.json 读
ENTRY_URL="$(jq -r .entryUrl .last-build.json)"

# 输出到本目录（约定俗成的版本命名）
$SKILL_DIR/scripts/capture_cover.sh "$ENTRY_URL" ./covers/v3.png
```

然后把本地路径填到 `apply_changes.py` 的 `postBuild.r15.uploadCover`：

```json
{
  "postBuild": {
    "r15": {
      "uploadCover": "covers/v3.png"
    }
  }
}
```

脚本会自动把截图上传到同 buildId 的 CDN 目录，并把 CDN URL 写入注册接口 / `summary.r15.coverUrl`，供 `<app cover>` 标签透出。

## Git 管理

- ✅ **保留** `covers/README.md`（本文件，告诉协作者这个目录的用途）
- ❌ **不入仓** 图片产物本身（`*.png` / `*.jpg` 等）—— 已在 `.gitignore` 排除；图片上传 CDN 后，CDN URL 是唯一稳定来源
- ✅ **不进** `source.zip`：`tmp/` 已在 `build_and_upload.sh` 顶层排除清单，但 `covers/` 不在排除清单 —— 如果你想让 covers/ 也不进源码 zip，可以把图片放 `tmp/covers/` 替代

> **Why 不入仓**：截图属于「构建产物 + 视觉占位」性质，每次发版都会重截；图片二进制入 git 会让 repo 体积失控。CDN 已是事实上的存储，git 只留 README 占位即可。
