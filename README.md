# miniapp-react-starter

Hi Work MiniApp 工程化骨架 —— **React 18 + Vite + qiankun** 微前端版本。

> 基于《MiniApp 工程化改造技术方案》落地，框架选型由原方案的 Vue3 调整为 **React**。
> 其他设计原则（qiankun 加载、CDN 绝对路径、生命周期暴露、不绑组件库 / 状态管理）保持一致。

---

## 目录结构

```
.
├── README.md
├── package.json
├── tsconfig.json
├── vite.config.ts          # CDN 绝对路径注入逻辑都在这里
├── index.html              # 唯一入口，含 #miniapp-root 挂载点
├── miniapp.json            # 项目级元信息（POD/Skill 用，不参与运行）
├── public/                 # 原样拷贝到产物根目录
└── src/
    ├── main.tsx            # qiankun 生命周期（bootstrap/mount/unmount）+ 独立运行兜底
    ├── main.css            # 全局样式（.miniapp-root 命名空间 + 通用布局）
    ├── App.tsx             # 根组件（LLM 主要编辑入口）
    ├── components/         # 业务组件，每个组件一个目录
    │   └── HelloPanel/
    │       ├── index.tsx   # 组件入口（顶部 import './index.css'）
    │       └── index.css   # 组件私有样式（.hello-panel* 前缀作命名空间）
    └── types/
        └── qiankun.ts      # IMiniAppHostContext / QiankunProps 类型契约
```

> 组件目录化约定：每个业务组件占一个目录（`components/<Name>/{ index.tsx, index.css }`），子组件就近拆同目录（`Wheel.tsx`），不再嵌套子文件夹。详见 SKILL.md E9。

---

## 本地开发

```bash
pnpm install
pnpm dev
```

浏览器与服务同环境时，打开 Vite 实际返回的 HTTP 地址；浏览器在独立环境时使用平台实际返回的转发地址，不假定 localhost 互通，也不使用 file://。复用已有服务。独立模式下会走 `if (!window.__POWERED_BY_QIANKUN__) render()` 分支；登录与宿主接口仍在原 HiWork 上下文验证。

---

## 生产构建（关键约束 ⚠️）

**所有产物里的资源路径都必须是 CDN 绝对路径**（避免被 qiankun 注入 dibp.devops.xiaohongshu.com 后找不到资源）。

正常交付按 AGENTS.md 准备含 `typeCheck`、`build: true`、`postBuild.r15` 的 manifest，然后一次执行：

```bash
python3 <SKILL_DIR>/engineering/scripts/apply_changes.py --manifest '<本轮manifest绝对路径>'
```

脚本自动安装缺失依赖、生成 buildId、注入以 `/` 结尾的 VITE_CDN_BASE、构建上传并注册草稿。首次创建需在 r15 提供应用名称，作者由后端从当前登录上下文获取；已有应用沿用原 appCode。不要先手工构建、外部上传或在成功后重复注册。

确认 summary.r15.ok=true / stage=complete 后，用 summary.build 的 appUrl / sourceZipUrl / distManifestUrl 和 summary.r15 的 version / timestamp / coverUrl 输出工程化标签。正式发布由用户在当前会话的 app 预览中完成。注册失败按返回的 resultFile 单独恢复，不重跑构建上传。

底层 `vite.config.ts` 在缺少 VITE_CDN_BASE 时仍主动阻断生产构建；`ALLOW_LOCAL_BUILD=true` 仅用于本地预览。

产出位于 `dist/`，目录结构：

```
dist/
├── index.html             # <script src="https://cdn/.../assets/xxx.js"> 全是绝对路径
├── manifest.json          # Vite 自带的产物清单（hash 索引）
└── assets/
    ├── react-vendor-[hash].js
    ├── index-[hash].js
    ├── index-[hash].css
    └── ...
```

---

## qiankun 接入约定

### 生命周期

`src/main.tsx` 已按 qiankun 约定导出：

- `bootstrap()` —— 一次性初始化
- `mount(props)` —— 主应用 `loadMicroApp` 时调用，传入 `container` + `contextProvider`
- `unmount()` —— 卸载时清理 React root
- `update(props)` —— 预留，本期未使用

### 主站 → MiniApp 上下文

主应用通过 qiankun props 注入 `contextProvider`，MiniApp 在业务代码里这样取：

```ts
const ctx = (window as any).__MINIAPP_CONTEXT__ as IMiniAppHostContext | undefined
ctx?.notify('success', '保存成功')
ctx?.openLink('https://dibp.devops.xiaohongshu.com/apps/aibibp')
```

类型契约见 `src/types/qiankun.ts`（`IMiniAppHostContext`）。

### SSO Cookie

因 qiankun 把脚本注入主站 `window`，所有 `fetch` / `XHR` 默认相对 `dibp.devops.xiaohongshu.com`，**SSO Cookie 自动随请求携带**，无需额外处理。

---

## LLM 编辑红线

| 文件 | 规则 |
|---|---|
| `node_modules/` `dist/` `pnpm-lock.yaml` | ❌ 禁止编辑 |
| `src/main.tsx` 顶部生命周期导出 | ❌ 禁止删除 / 改签名 |
| `index.html` 的 `#miniapp-root` 节点 | ❌ 禁止改 id |
| `vite.config.ts` 的 `base` 注入逻辑 | ❌ 禁止改成相对路径 |
| `App.tsx` 根元素的 `.miniapp-root` 类名 | ❌ 禁止删 |
| 全局样式 | ❌ 禁止裸 `html` / `body` / `:root` 选择器；❌ 禁止霸屏 `position: fixed; inset: 0` |
| 新装 npm 包 | 按需填入 apply_changes.py manifest 的 installDeps，沿用项目 pnpm / registry；已有依赖直接复用 |
