/**
 * 预留的接口出口。本期 MVP 使用浏览器本地存储，
 * 后续接入地图、天气或协作服务时统一从此处导出。
 */
export { execute, type ExecuteOptions } from './client'
export type { QueryError, QueryResult } from './types'
