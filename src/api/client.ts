/**
 * API client —— 统一调用 Hi Work /api/mini-app/data-query/execute
 *
 * 业务方不应直接 fetch；所有调用必须通过 queries/<code>.ts 里定义的业务函数，
 * 业务函数内部统一走 execute()。
 *
 * 关键约束（E13）：
 * 1. 必须用 Hi Work 主站绝对 URL（CDN 上线后相对路径会被浏览器解析到 fe-static.xhscdn.com 域，405）
 * 2. 必须带 credentials: 'include'（接口依赖 SSO cookie）
 * 3. 错误返回 { ok: false, error }，不抛异常（业务层判 .ok 决定渲染分支）
 */

import type { QueryResult, RawDibpResponse } from './types'

// 必须用 https：工程化产物部署在 HTTPS 的 picasso CDN / Hi Work 主站上下文，
// http 会被浏览器当作 mixed content 直接拦截（取数、聊天全部失败）。
const DATA_QUERY_API =
  'https://dibp.devops.xiaohongshu.com/api/mini-app/data-query/execute'

/** 单次请求默认超时（ms）。LLM 对话类查询慢，业务方可通过 options 覆盖 */
const DEFAULT_TIMEOUT_MS = 30000

export interface ExecuteOptions {
  /** 超时 ms，默认 30000；对话类建议传 180000 */
  timeoutMs?: number
  /** 外部 AbortSignal，用于业务层主动取消（如 React 卸载） */
  signal?: AbortSignal
}

/**
 * 调 Hi Work 数据查询接口
 *
 * @param code   miniapp-data-binding 注册的查询服务 code
 * @param params 业务参数（结构由查询模板决定）
 * @param opts   超时 / 取消
 * @returns { ok: true, data: T, raw } | { ok: false, error }
 */
export async function execute<T = unknown, P = unknown>(
  code: string,
  params: P,
  opts: ExecuteOptions = {},
): Promise<QueryResult<T>> {
  const { timeoutMs = DEFAULT_TIMEOUT_MS, signal: externalSignal } = opts

  const ctrl =
    typeof AbortController !== 'undefined' ? new AbortController() : null
  const timeoutId =
    ctrl && timeoutMs > 0
      ? setTimeout(() => {
          try {
            ctrl.abort()
          } catch {
            /* ignore */
          }
        }, timeoutMs)
      : null

  // 接管外部 signal（业务层卸载触发 abort）
  if (externalSignal && ctrl) {
    if (externalSignal.aborted) {
      ctrl.abort()
    } else {
      externalSignal.addEventListener('abort', () => {
        try {
          ctrl.abort()
        } catch {
          /* ignore */
        }
      })
    }
  }

  try {
    const res = await fetch(DATA_QUERY_API, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include',
      body: JSON.stringify({ code, params }),
      signal: ctrl?.signal,
    })

    if (timeoutId) clearTimeout(timeoutId)

    if (!res.ok) {
      const errText = await res.text().catch(() => '')
      return {
        ok: false,
        error: {
          status: res.status,
          message: `HTTP ${res.status}`,
          raw: errText.slice(0, 500),
        },
      }
    }

    const json = (await res.json().catch(() => null)) as RawDibpResponse<T> | null
    if (!json) {
      return {
        ok: false,
        error: { status: res.status, message: '响应体解析失败' },
      }
    }

    // 业务层错误（success=false 或 errMsg 非空）
    if (json.success === false || json.errMsg) {
      return {
        ok: false,
        error: {
          status: res.status,
          message: json.errMsg || json.message || '业务错误',
          raw: json,
        },
      }
    }

    return { ok: true, data: json.data as T, raw: json }
  } catch (err) {
    if (timeoutId) clearTimeout(timeoutId)
    const e = err as Error
    const aborted =
      e?.name === 'AbortError' || /aborted/i.test(String(e?.message ?? ''))
    return {
      ok: false,
      error: {
        status: 0,
        message: aborted ? '请求已取消' : `网络异常: ${e?.message ?? String(err)}`,
        raw: err,
      },
    }
  }
}
