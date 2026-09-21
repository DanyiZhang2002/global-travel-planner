/**
 * 与 Hi Work 主应用约定的 qiankun 通信契约。
 * 后续若主站发布到 npm 私包，应改为 import 自该包，确保类型唯一源。
 */

export interface IMiniAppHostContext {
  /** schema 版本，便于未来契约升级时识别老 MiniApp */
  v?: 1

  /** 当前登录用户基础信息 */
  user: {
    email: string
    name: string
    avatar?: string
  }

  /** 跟随 Hi Work 主题 */
  theme: 'light' | 'dark'

  /** 在主站打开链接（替代 window.open，可做埋点 / qiankun 上下文恢复） */
  openLink: (url: string, target?: '_blank' | '_self') => void

  /** 主站统一 toast */
  notify: (
    level: 'info' | 'success' | 'warn' | 'error',
    message: string,
  ) => void

  /** 上报埋点 */
  track: (event: string, props?: Record<string, unknown>) => void
}

/** qiankun 在生命周期里透传给 MiniApp 的 props */
export interface QiankunProps {
  /** 主应用提供的根容器节点 */
  container?: HTMLElement | string
  /** 主应用注入的上下文 / 能力 */
  contextProvider?: IMiniAppHostContext
  /** qiankun 内置字段：微应用名 */
  name?: string
  /** qiankun 内置字段：基础路由前缀 */
  setGlobalState?: (state: Record<string, unknown>) => void
  /** 其他主应用自定义字段，先开放透传 */
  [key: string]: unknown
}
