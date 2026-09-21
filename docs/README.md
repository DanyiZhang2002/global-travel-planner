# 📚 项目文档

开发过程中产出的架构 / 功能 / 接口文档统一收纳在这里。

## 目录结构

```
docs/
├── README.md           # 本文件（索引）
├── architecture.md     # 项目架构总览（必填）
├── features/           # 业务功能设计文档
│   └── <功能名>.md
└── api/                # 接口契约文档
    └── <query-code>.md
```

## 命名约定

| 类型 | 路径 | 命名 | 示例 |
|---|---|---|---|
| 架构总览 | `docs/architecture.md` | 固定文件名 | - |
| 功能设计 | `docs/features/` | **小写连字符**，与功能模块对齐 | `lucky-draw.md` / `reward-trend.md` |
| 接口契约 | `docs/api/` | **query code**（来自 miniapp-data-binding 注册）| `DIBP_chat_xxx.md` / `BI_dau_trend.md` |

## 写什么 / 不写什么

### ✅ 应该写

- **架构决策的"为什么"** —— 选了 qiankun 而不是 iframe？为什么不用 X 库？
- **跨组件的交互流程** —— 数据从哪进来、经过哪几个模块、最后渲染在哪
- **业务规则的边界 / corner case** —— 哪些状态机分支必须处理、哪些数据缺失要降级
- **接口的字段口径** —— 这个字段什么时候 null、这个枚举有几个取值、单位是什么
- **踩过的坑 + 解法** —— 避免下次维护者重蹈覆辙

### ❌ 不需要写

- 单行代码就能看懂的注释（写代码注释更合适）
- 框架基础（React / Vite / qiankun 的用法）—— 看官方文档
- 业务无关的通用模式（如"useState 怎么用"）
- 写完就过期的临时调试 log

## 文档模板

### 架构文档 `architecture.md`

```markdown
# 架构

## 业务目标
（这个 app 是干嘛的，给谁用）

## 渲染链路
（qiankun → loadMicroApp → mount → React 渲染）

## 数据流
（用户操作 → 状态变更 → API → 渲染）

## 模块划分
（components/ 各组件的职责）

## 关键决策
- 决策 1：用 X 而不是 Y，因为...
- 决策 2：...
```

### 功能文档 `features/<name>.md`

```markdown
# 功能：抽奖（LuckyDraw）

## 产品需求
- 每日 N 次抽奖机会
- 分享得加成
- ...

## 状态机
[准备] → [抽奖中] → [中奖/未中奖] → [展示结果]

## 数据依赖
- 接口 1：拉用户剩余次数（query code: BI_xxx）
- 接口 2：触发抽奖（query code: DIBP_xxx）

## 边界 / 异常
- 网络失败 → 重试 3 次
- 次数耗尽 → 灰化按钮 + 提示
```

### 接口文档 `api/<query-code>.md`

```markdown
# DIBP_chat_activity_assistant

## 用途
活动助手对话，回答活动规则 / 奖品 / 抽奖技巧

## 入参
| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| question | string | ✅ | 用户问题 |
| context | string | ✅ | JSON 序列化的业务态 |

## 出参
| 字段 | 类型 | 说明 |
|---|---|---|
| data.answer | string | 模型回答正文 |
| data.took | number | 耗时 ms |

## 字段口径
- `answer` 为空时表示模型无法回答，调用方应展示降级文案
- `context.userName` 来自 `__MINIAPP_CONTEXT__.user.name`
```

## 与 AGENTS.md 的分工

| 文件 | 受众 | 写什么 |
|---|---|---|
| `AGENTS.md`（项目根） | LLM / 新接手维护者 | **怎么干活**：技术栈、命令、红线、约束 |
| `docs/`（本目录） | LLM / 业务方 / 产品 | **做了什么**：架构、需求、接口契约 |
