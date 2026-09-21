import React from 'react'
import { createRoot, type Root } from 'react-dom/client'
import {
  qiankunWindow,
  renderWithQiankun,
  type QiankunProps as PluginQiankunProps,
} from 'vite-plugin-qiankun/dist/helper'
import App from './App'
import type { IMiniAppHostContext } from './types/qiankun'
import './main.css'

/**
 * qiankun 微前端生命周期适配（React 18）
 *
 * 设计要点：
 * 1. 用 vite-plugin-qiankun 的 renderWithQiankun 包装生命周期：
 *    - 该 helper 把 bootstrap/mount/unmount 暴露到 window 上的 qiankun 约定字段，
 *      让主应用 qiankun loadMicroApp 能识别本子应用
 *    - 同时配合 vite.config.ts 里的 qiankun() 插件把 Vite 默认的原生 ESM 产物
 *      包装成 qiankun 沙箱可 eval 的格式（解决 import/export SyntaxError）
 *
 * 2. React 18 用 createRoot 挂载，unmount 时必须显式 root.unmount()
 *    并把 root 引用置空，否则 qiankun 切换子应用时会内存泄漏
 *
 * 3. 主站通过 qiankun props 传 contextProvider（user/theme/notify/openLink/track 等），
 *    挂到 window.__MINIAPP_CONTEXT__ 供业务代码同步取用
 *
 * 4. 通过 vite.config.ts 的 base = VITE_CDN_BASE 已保证产物里所有静态资源走 CDN 绝对路径，
 *    qiankun import-html-entry 见到绝对 URL 不会再做相对路径改写，正常加载
 */

let root: Root | null = null

function resolveContainer(rawContainer?: HTMLElement): Element {
  if (!rawContainer) {
    const el = document.getElementById('miniapp-root')
    if (!el) throw new Error('[miniapp] 找不到挂载点 #miniapp-root')
    return el
  }
  // qiankun 会传整个微应用容器；内部约定挂在 #miniapp-root 上，找不到就退回容器本身
  return rawContainer.querySelector('#miniapp-root') || rawContainer
}

function render(props: PluginQiankunProps = {}) {
  const container = resolveContainer(props.container)
  root = createRoot(container)
  root.render(
    <React.StrictMode>
      <App />
    </React.StrictMode>,
  )
}

/* ---------------- qiankun 生命周期（通过 vite-plugin-qiankun 暴露） ---------------- */

renderWithQiankun({
  bootstrap() {
    // 一次性初始化钩子；当前无需操作
  },
  mount(props: PluginQiankunProps) {
    const contextProvider = (props as { contextProvider?: IMiniAppHostContext })
      .contextProvider
    if (contextProvider) {
      ;(window as unknown as { __MINIAPP_CONTEXT__?: IMiniAppHostContext }).__MINIAPP_CONTEXT__ =
        contextProvider
    }
    render(props)
  },
  unmount() {
    root?.unmount()
    root = null
    delete (window as unknown as { __MINIAPP_CONTEXT__?: IMiniAppHostContext }).__MINIAPP_CONTEXT__
  },
  update() {
    // 本期不使用 update 钩子，预留
  },
})

/* ---------------- 独立运行（pnpm dev，未被 qiankun 加载） ---------------- */

if (!qiankunWindow.__POWERED_BY_QIANKUN__) {
  render()
}
