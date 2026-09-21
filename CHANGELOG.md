# CHANGELOG

> 本文件记录当前 miniapp 的版本演进历史。每次通过 app-engineering-builder 完成一次构建 + CDN 上传 + R15 决策后，由 LLM 在此追加一条对应版本号的变更说明。
>
> 版本号对齐规则：
> - 与 App 平台后端的 `version` 字段一致
> - 首次创建（R15 total=0）写入 v1
> - 已注册后的每次编辑 → 走 `app-update-version` 拿到 `NEW_VERSION` 再追加对应条目

## v1 — YYYY-MM-DD HH:mm:ss +08:00 (首次创建)

### Major Changes

- 初始化项目骨架（react-vite 模板）
- 落地业务模块（请补充本轮做了哪些模块、接了哪些数据、对话能力放在哪）

### Notes

- 后续每次编辑请在文件顶部追加新版本条目（v2、v3 …）
- 时间戳格式：`TZ=Asia/Shanghai date -Iseconds`，形如 `2026-06-01T21:18:00+08:00`
- 版本号来源：编辑场景必须用 `app-update-version` 接口返回的 `NEW_VERSION`，严禁凭印象写
