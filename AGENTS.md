# AGENTS.md — 项目级 LLM 工作手册

> 任何 LLM / 维护者打开本项目时，**先读本文件**，再动代码。

## 项目类型

Hi Work 工程化 MiniApp（React 18 + Vite 5 + TypeScript），通过 qiankun 微前端被加载到 `dibp.devops.xiaohongshu.com` 主站，由 `app-builder` skill 的 engineering 分支生成。

## 技术栈

| 项 | 选型 |
|---|---|
| 框架 | React 18 + TypeScript（strict mode）|
| 打包器 | Vite 5 + `@vitejs/plugin-react` |
| 微前端 | `vite-plugin-qiankun` + `renderWithQiankun` helper |
| 包管理 | **pnpm**（不要用 npm / yarn 装包）|
| 内网 npm registry | `https://artifactory.devops.xiaohongshu.com/artifactory/api/npm/npm-internal/`（`@xhs/*` 内网包走这个，已在 `.npmrc` 配好）|
| CDN | 腾讯云 COS `picasso-private-1251524319.cos.ap-shanghai.myqcloud.com` |

## 常用命令

```bash
pnpm install            # 装依赖
pnpm dev                # 本地独立开发（不带 qiankun 主站，走兜底渲染）
pnpm type-check         # TypeScript 类型校验（必须 0 错才能上线）
pnpm build              # 生产构建（必须注入 VITE_CDN_BASE，否则主动 throw）
ALLOW_LOCAL_BUILD=true pnpm build  # 本地预览构建（资源用根相对路径 /assets/...）
```

## 项目结构

```
.
├── AGENTS.md           # 本文件
├── README.md           # 给人看的项目说明
├── docs/               # 开发期文档（架构 / 功能 / 接口）
│   ├── README.md
│   ├── architecture.md
│   ├── features/       # 业务功能设计文档
│   └── api/            # 接口契约文档
├── index.html          # 唯一入口（含 #miniapp-root 挂载点）
├── miniapp.json        # 项目元信息（appCode / appName / 给 Hi Work 平台用）
├── public/             # 原样拷贝到产物根目录
├── src/
│   ├── main.tsx        # qiankun 生命周期（bootstrap/mount/unmount/update）+ 独立运行兜底
│   ├── main.css        # 全局样式（仅 .miniapp-root 命名空间 + 通用布局）
│   ├── App.tsx         # 根组件（主要业务编辑入口）
│   ├── components/     # 业务组件，每个组件一个目录
│   │   └── HelloPanel/
│   │       ├── index.tsx
│   │       └── index.css
│   └── types/
│       └── qiankun.ts  # IMiniAppHostContext / QiankunProps 类型契约
├── tsconfig.json
└── vite.config.ts      # CDN base 注入 + qiankun 插件配置
```

## 编辑红线（违反 = 产物上线后报废）

### 🚫 禁止改这些

| 文件 / 配置 | 原因 |
|---|---|
| `vite.config.ts` 的 `base = VITE_CDN_BASE` 注入逻辑 | 改成相对路径会让 qiankun 加载时资源 404 |
| `vite.config.ts` 的 `qiankun(appName, ...)` 插件 | 没它，Vite 默认 ESM 产物进 qiankun new Function 沙箱会撞 SyntaxError |
| `src/main.tsx` 的 `renderWithQiankun({ bootstrap, mount, unmount, update })` 签名 | 4 个生命周期必须全部 export，主应用 `loadMicroApp` 找不到契约会黑屏 |
| `index.html` 的 `<div id="miniapp-root"></div>` | 挂载点 id 固定 |
| 任何样式写 `position: fixed; inset: 0` | 会盖住 Hi Work 主站导航 |
| 任何样式写裸 `html/body/:root` 选择器 | 污染主站全局样式 |

### ✅ 必须遵守

1. **根 className 必须是 `miniapp-root`** —— qiankun `experimentalStyleIsolation` 依赖此命名空间
2. **所有静态资源 URL 必须是 CDN 绝对路径** —— 通过 `VITE_CDN_BASE` 注入；缺失时构建主动失败
3. **业务组件目录化** —— `components/<Name>/{ index.tsx, index.css }`；样式跟组件就近放置
4. **跨组件 import 路径多一层** —— `import Foo from '../Foo'`（同组件内拆子组件仍是 `'./Wheel'`）
5. **调主站能力走 `window.__MINIAPP_CONTEXT__`** —— 类型在 `src/types/qiankun.ts`；toast / openLink / track 都走这里
6. **TypeScript strict mode 必须 0 错** —— 上线前 `pnpm type-check` 必跑
7. **新依赖装到内网 registry** —— `@xhs/*` 包自动走内网，其他公网包正常装
8. **复杂交互组件必须用成熟 UI 组件库（E15）** —— Modal / Drawer / Popover / Tooltip / Dropdown / Select / DatePicker / Form / Table 等带弹层 / 表单校验 / 复杂选择的组件**禁止手写**，从成熟 UI 组件库（antd / arco / @xhs 内部 / shadcn 等，由业务方诉求或会话上下文选）里挑成品用；选定后 `pnpm add` 安装，不预装、不强制特定库；任何 portal 类组件（弹层/浮层/下拉）必须把容器挂到 `.miniapp-root` 内（如 antd 用 `getPopupContainer={(node) => node?.parentElement || document.body}`），避免 qiankun unmount 后浮层残留；纯静态展示（Card / Banner / Badge）可以手写

## 数据接入约定

任何动态数据（图表 / 表格 / 卡片 / 下拉 / 对话）**必须通过 `miniapp-data-binding` skill 注册查询服务**，拿到 `code` 后按 **E13 收拢于 `src/api/`**。

### 目录结构

```
src/api/
├── client.ts                  # 底层 fetch 封装（execute() 函数）
├── types.ts                   # QueryResult / QueryError 通用类型
├── index.ts                   # 桶导出（业务组件统一从 './api' import）
└── queries/                   # 每个 code 一个文件
    ├── BI_dau_trend.ts        # 一个 query code = 一个 ts 文件 = 一个 docs/api/<code>.md
    └── DIBP_chat_xxx.ts
```

### 新增一个接口的标准流程（4 步）

1. **注册**：走 `miniapp-data-binding` skill 拿 code（如 `BI_dau_trend`）
2. **建 ts 文件**：`src/api/queries/BI_dau_trend.ts` 定义 `CODE` / `Params` / `Response` 类型 + 业务函数
3. **桶导出**：`src/api/index.ts` 追加一行 `export` 让组件能短路径 import
4. **写文档**：`docs/api/BI_dau_trend.md` 写契约（入参 / 出参 / 字段口径）

### 业务函数模板（照葫芦画瓢）

```ts
// src/api/queries/BI_dau_trend.ts
import { execute } from '../client'
import type { QueryResult } from '../types'

export const CODE = 'BI_dau_trend' as const

export interface Params {
  startDate: string  // YYYY-MM-DD
  endDate: string
}

export interface Row { date: string; dau: number; wau: number }
export type Response = { rows: Row[] }

export async function getDauTrend(params: Params): Promise<QueryResult<Response>> {
  return execute<Response>(CODE, params)
}
```

### 组件里的使用方式

```tsx
import { useEffect, useState } from 'react'
import { getDauTrend, type HelloResponse } from './api'

function DauChart() {
  const [data, setData] = useState<HelloResponse | null>(null)
  const [err, setErr] = useState<string | null>(null)

  useEffect(() => {
    getDauTrend({ startDate: '2026-01-01', endDate: '2026-01-31' }).then(res => {
      if (res.ok) setData(res.data)
      else setErr(res.error.message)
    })
  }, [])

  if (err) return <div>加载失败：{err}</div>
  if (!data) return <div>加载中…</div>
  return <Chart rows={data.rows} />
}
```

### 严禁

- ❌ 组件里直接 `fetch('https://dibp.../execute')` —— 必须走 `src/api/queries/<code>.ts`
- ❌ 把所有查询塞进 `src/api/queries.ts` 一个胖文件
- ❌ Params / Response 用 `any` 逃避口径
- ❌ 写死 mock 数据 / 假 fetch / setTimeout 模拟接口 / 注释 "TODO 接真实接口"
- ❌ 改写 `dibp-chat-bridge` snippet 内的 fetch 把它挪到 `api/` 下 —— snippet 是自治组件，保持原状

## 对话能力约定

每个 app **默认内置** Hi Work 对话能力（不要跳转 Hi Work 主站 / 嵌入第三方 chatbot iframe）：

- 走 `miniapp-data-binding` 注册 Hi Work 模板拿到 `code`
- 用 `app-builder` skill 的 `engineering/components/dibp-chat-bridge/snippet.tsx` 接入
- 默认在 App.tsx 挂 `<DibpChatFloatingButton />`（右端浮动按钮 + 抽屉对话面板）

## 构建、注册与预览交付

完成本轮编辑与验证后，准备一份 manifest，正常交付同时包含构建与注册配置：

```json
{
  "projectDir": "<本项目绝对路径>",
  "typeCheck": true,
  "build": true,
  "postBuild": {
    "r15": { "appCode": "<miniapp.json 中的原 appCode>" }
  }
}
```

首次创建另在 r15 内填写 appName，名称取 miniapp.json；作者由后端从当前登录上下文获取，无需读取 USER.md 或填写作者字段。已改好的源码无需重复声明 edits；需要批量改动时可放进同一 manifest。

```bash
python3 <SKILL_DIR>/engineering/scripts/apply_changes.py --manifest '<本轮manifest绝对路径>'
```

`<SKILL_DIR>` 是当前 app-builder 安装目录。该调用自动处理必要依赖、类型检查、CDN base / buildId、构建上传、源码包、资源清单和草稿注册，无需提前手工构建或调用外部上传 skill。封面沿用工程化默认流程，项目日志按需配置。

退出码 0、summary.ok=true 且 summary.r15.ok=true / stage=complete 后，从 summary.build 取 appUrl / sourceZipUrl / distManifestUrl，从 summary.r15 取 version / timestamp / coverUrl，输出一次 `<app appUrl="..." appType="vite-qiankun" appCode="..." sourceZipUrl="..." distManifestUrl="..." version="..." timestamp="..." [cover] [workId]></app>`。方括号表示条件属性：封面成功才加 cover，已有后端时保留真实 workId。不要改用单 HTML 的 url 属性。

注册失败仅用 `<SKILL_DIR>/scripts/app_registration.py --resume-from '<summary.r15.resultFile>'` 恢复，继续复用原 summary.build；写入未知先核实，不整套重跑。已确认草稿不再次注册，时间戳直接复用结果。正式发布由用户在当前会话右侧 app 预览中点击完成。

## docs/ 目录用法

开发过程中产出的文档统一收到 `docs/`：

| 文件 | 用途 |
|---|---|
| `docs/README.md` | 索引（列出本项目有哪些文档） |
| `docs/architecture.md` | 架构概览 / 数据流 / 模块划分 |
| `docs/features/<name>.md` | 单个业务功能的产品需求 + 状态机 + 边界 |
| `docs/api/<code>.md` | 单个接口的契约（query code + 入参 + 出参字段口径）|

LLM 编辑前**先扫 `docs/` 里有没有相关上下文**，没找到再写代码；写完后**反向把决策记到 docs/**，让后续维护者能溯源。

## 相关 Skills

| Skill | 用途 |
|---|---|
| `app-builder` | 创建 / 编辑本项目的主 skill（engineering 分支，构建上传与注册合并执行） |
| `miniapp-data-binding` | 注册业务数据查询服务（拿 `code`） |
| `hi-docs` | 拉/写 REDoc 文档（写架构文档可用） |
