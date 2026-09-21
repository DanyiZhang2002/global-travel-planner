import type { ItineraryItem, Trip } from './types/trip'

const KEY_TRIPS = 'xinglvriji.v1.trips'
const KEY_ITEMS = 'xinglvriji.v1.items'

export const uid = (prefix: string) => `${prefix}-${crypto.randomUUID?.() ?? `${Date.now().toString(36)}${Math.random().toString(36).slice(2)}`}`
export const now = () => new Date().toISOString()
export const today = () => dateKey(new Date())
export function dateKey(d: Date) { return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}` }
export function parseDate(s: string) { const [y, m, d] = s.split('-').map(Number); return new Date(y, (m ?? 1) - 1, d ?? 1) }
export function addDays(s: string, n: number) { const d = parseDate(s); d.setDate(d.getDate() + n); return dateKey(d) }
export function diffDays(a: string, b: string) { return Math.round((parseDate(a).getTime() - parseDate(b).getTime()) / 86400000) }
export function datesBetween(start: string, end: string) { const n = Math.max(0, diffDays(end, start)); return Array.from({ length: n + 1 }, (_, i) => addDays(start, i)) }
export function fmtMd(s: string) { const d = parseDate(s); return `${d.getMonth() + 1}月${d.getDate()}日` }
export function weekday(s: string) { return ['周日', '周一', '周二', '周三', '周四', '周五', '周六'][parseDate(s).getDay()] }
export function fmtDate(s: string) { return `${fmtMd(s)} ${weekday(s)}` }
export function monthGrid(year: number, month: number) { const first = new Date(year, month, 1); const offset = (first.getDay() + 6) % 7; const count = new Date(year, month + 1, 0).getDate(); const cells: (string | null)[] = [...Array(offset).fill(null)]; for (let day = 1; day <= count; day += 1) cells.push(dateKey(new Date(year, month, day))); while (cells.length % 7) cells.push(null); return Array.from({ length: cells.length / 7 }, (_, i) => cells.slice(i * 7, i * 7 + 7)) }
export function loadData(): { trips: Trip[]; items: ItineraryItem[] } { try { return { trips: JSON.parse(localStorage.getItem(KEY_TRIPS) || '[]'), items: JSON.parse(localStorage.getItem(KEY_ITEMS) || '[]') } } catch { return { trips: [], items: [] } } }
export function saveData(trips: Trip[], items: ItineraryItem[]) { try { localStorage.setItem(KEY_TRIPS, JSON.stringify(trips)); localStorage.setItem(KEY_ITEMS, JSON.stringify(items)); return true } catch { return false } }
export function compressImage(file: File, max = 1080) { return new Promise<string>((resolve, reject) => { if (!file.type.startsWith('image/')) return reject(new Error('请选择图片文件')); const reader = new FileReader(); reader.onerror = () => reject(new Error('图片读取失败')); reader.onload = () => { const image = new Image(); image.onerror = () => reject(new Error('图片格式暂不支持')); image.onload = () => { const ratio = Math.min(1, max / Math.max(image.width, image.height)); const canvas = document.createElement('canvas'); canvas.width = Math.max(1, Math.round(image.width * ratio)); canvas.height = Math.max(1, Math.round(image.height * ratio)); const ctx = canvas.getContext('2d'); if (!ctx) return reject(new Error('图片处理失败')); ctx.drawImage(image, 0, 0, canvas.width, canvas.height); resolve(canvas.toDataURL('image/jpeg', 0.72)) }; image.src = String(reader.result) }; reader.readAsDataURL(file) }) }
export function itemSort(a: ItineraryItem, b: ItineraryItem) { if (!a.startTime && !b.startTime) return a.sortIndex - b.sortIndex; if (!a.startTime) return 1; if (!b.startTime) return -1; return a.startTime.localeCompare(b.startTime) || a.createdAt.localeCompare(b.createdAt) }
