/**
 * API 通用类型
 *
 * 所有业务查询函数的返回值都包装成 QueryResult<T>，业务层不用 try/catch，
 * 直接判断 .ok 字段决定渲染分支。
 */

export interface QueryError {
  /** HTTP 状态码（非 200 时填，网络异常填 0） */
  status: number
  /** 简短错误描述（给业务层 toast 用，已国际化前的原始文案） */
  message: string
  /** 原始错误对象 / 响应文本（debug 用，不要直接渲染到 UI） */
  raw?: unknown
}

export type QueryResult<T> =
  | { ok: true; data: T; raw?: unknown }
  | { ok: false; error: QueryError; data?: undefined }

/**
 * Hi Work /api/mini-app/data-query/execute 的常见返回结构（多模板兼容）
 *
 * 不同 query 模板返回的 data 结构差异较大，业务方在自己的 queries/<code>.ts
 * 里定义具体的 Response 类型，client.ts 只兜底返回 unknown 让业务方自己 cast。
 */
export interface RawDibpResponse<T = unknown> {
  success?: boolean
  message?: string
  data?: T
  /** 部分模板把错误信息放在外层 errMsg */
  errMsg?: string
}
