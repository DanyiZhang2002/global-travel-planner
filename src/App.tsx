import { useEffect, useMemo, useRef, useState } from 'react'
import type { ReactNode } from 'react'
import type { ItemDetails, ItemType, ItineraryItem, Trip } from './types/trip'
import { ITEM_TYPES, TYPE_INFO } from './types/trip'
import { addDays, compressImage, datesBetween, diffDays, fmtDate, fmtMd, itemSort, loadData, monthGrid, parseDate, saveData, today, uid, weekday } from './lib'
import Icon from './components/TravelApp/Icon'
import './components/TravelApp/index.css'

type View =
  | { page: 'list' }
  | { page: 'trip'; tripId: string }
  | { page: 'day'; tripId: string; date: string }
  | { page: 'tripForm'; id?: string }
  | { page: 'itemForm'; tripId: string; date: string; id?: string }

type ItemDraft = Omit<ItineraryItem, 'id' | 'createdAt' | 'updatedAt' | 'sortIndex'>
const covers = [
  'linear-gradient(135deg,#6fb7f0,#c8e6fa)',
  'linear-gradient(135deg,#4fa8d8,#b7e2ef)',
  'linear-gradient(135deg,#5fae8b,#cbe8d6)',
  'linear-gradient(135deg,#f2a65e,#fbe3c0)',
  'linear-gradient(135deg,#8b7ce0,#dcd5f7)',
]

function typeIcon(type: ItemType) {
  return TYPE_INFO[type].icon as Parameters<typeof Icon>[0]['name']
}

function Cover({ trip, small = false }: { trip: Pick<Trip, 'coverImage' | 'destination' | 'name'>; small?: boolean }) {
  const style = trip.coverImage.startsWith('data:')
    ? { backgroundImage: `url(${trip.coverImage})`, backgroundSize: 'cover', backgroundPosition: 'center' }
    : { background: covers[Number(trip.coverImage.replace('preset:', '')) || 0] }
  return <div className={small ? 'cover small' : 'cover'} style={style}><span>{trip.destination.slice(0, 1) || trip.name.slice(0, 1) || '旅'}</span></div>
}

function TypeChip({ type }: { type: ItemType }) {
  const info = TYPE_INFO[type]
  return <span className="xl-type" style={{ color: info.color, background: info.bg }}><Icon name={typeIcon(type)} size={13}/>{info.label}</span>
}

function Progress({ value }: { value: number }) {
  return <div className="xl-progress"><i style={{ width: `${Math.max(0, Math.min(100, value))}%` }}/></div>
}

function Field({ label, required, children }: { label: string; required?: boolean; children: ReactNode }) {
  return <div className="xl-field"><label className="xl-label">{label}{required ? <i className="xl-req">*</i> : null}</label>{children}</div>
}

function Empty({ title, desc, action, onClick }: { title: string; desc: string; action: string; onClick: () => void }) {
  return <div className="xl-empty"><div className="xl-empty-icon"><Icon name="plane" size={42}/></div><h3>{title}</h3><p>{desc}</p><button className="xl-btn xl-primary" onClick={onClick}><Icon name="plus" size={17}/>{action}</button></div>
}

function makeDemo(): { trips: Trip[]; items: ItineraryItem[] } {
  const stamp = new Date().toISOString()
  const trip: Trip = { id: uid('trip'), name: '青岛海滨三日游', destination: '山东 · 青岛', startDate: '2026-10-01', endDate: '2026-10-03', coverImage: 'preset:1', totalBudget: 3000, notes: '提前订好酒店和栈桥附近的餐厅。', createdAt: stamp, updatedAt: stamp }
  const make = (date: string, type: ItemType, title: string, startTime = '', endTime = '', extra: Partial<ItineraryItem> = {}): ItineraryItem => ({ id: uid('item'), tripId: trip.id, date, startTime, endTime, type, title, location: '', address: '', transport: '', cost: null, precautions: '', notes: '', images: [], completed: false, sortIndex: 0, details: {}, createdAt: stamp, updatedAt: stamp, ...extra })
  return {
    trips: [trip],
    items: [
      make('2026-10-01', 'transport', '上海虹桥 → 青岛北', '08:16', '13:05', { transport: '高铁', cost: 640, location: '上海虹桥站', details: { vehicle: '高铁', flightNo: 'G222', fromPlace: '上海虹桥', toPlace: '青岛北' }, precautions: '提前 40 分钟到站。' }),
      make('2026-10-01', 'hotel', '入住：青岛海天大酒店', '16:00', '', { cost: 520, location: '市南区香港西路', details: { hotelName: '青岛海天大酒店', bookingNo: 'HT20261001' } }),
      make('2026-10-02', 'sightseeing', '八大关 · 公主楼', '09:00', '11:30', { cost: 40, location: '八大关风景区', details: { openTime: '全天', ticketInfo: '部分楼栋单独收费', duration: '约 2.5 小时' } }),
      make('2026-10-02', 'dining', '船歌鱼水饺', '12:00', '13:30', { cost: 110, details: { restaurantName: '船歌鱼水饺', recommendDish: '黄花鱼水饺', avgBudget: '90 元/人' } }),
      make('2026-10-03', 'transport', '青岛北 → 上海虹桥', '14:40', '20:05', { transport: '高铁', cost: 640, details: { vehicle: '高铁', flightNo: 'G234', fromPlace: '青岛北', toPlace: '上海虹桥' } }),
      make('2026-10-02', 'other', '给朋友寄明信片', '', '', { location: '邮电博物馆', notes: '记得带邮票。' }),
    ],
  }
}

export default function App() {
  const initial = loadData()
  const [trips, setTrips] = useState<Trip[]>(initial.trips)
  const [items, setItems] = useState<ItineraryItem[]>(initial.items)
  const [view, setView] = useState<View>({ page: 'list' })
  const [storageError, setStorageError] = useState('')
  const root = useRef<HTMLDivElement>(null)

  useEffect(() => {
    setStorageError(saveData(trips, items) ? '' : '本地存储空间不足，请删除部分图片或旧数据后重试。')
  }, [trips, items])
  useEffect(() => { root.current?.scrollTo({ top: 0 }) }, [view])

  const findTrip = (id: string) => trips.find(t => t.id === id)
  const removeTrip = (trip: Trip) => {
    if (!window.confirm(`确定删除「${trip.name}」及其全部行程吗？`)) return
    setTrips(v => v.filter(t => t.id !== trip.id))
    setItems(v => v.filter(i => i.tripId !== trip.id))
    setView({ page: 'list' })
  }

  let page: ReactNode = null
  if (view.page === 'list') {
    page = <TripList trips={trips} items={items} onOpen={id => setView({ page: 'trip', tripId: id })} onCreate={() => setView({ page: 'tripForm' })} onEdit={id => setView({ page: 'tripForm', id })} onRemove={removeTrip} onDemo={() => { const d = makeDemo(); setTrips(v => [...v, ...d.trips]); setItems(v => [...v, ...d.items]) }} />
  }
  if (view.page === 'tripForm') {
    const editing = view.id ? findTrip(view.id) : undefined
    page = <TripForm trip={editing} onBack={() => setView({ page: 'list' })} onRemove={editing ? () => removeTrip(editing) : undefined} onSave={draft => {
      if (editing) {
        setTrips(v => v.map(t => t.id === editing.id ? { ...t, ...draft, updatedAt: new Date().toISOString() } : t))
        setView({ page: 'list' })
      } else {
        const trip: Trip = { ...draft, id: uid('trip'), createdAt: new Date().toISOString(), updatedAt: new Date().toISOString() }
        setTrips(v => [...v, trip])
        setView({ page: 'trip', tripId: trip.id })
      }
    }} />
  }
  if (view.page === 'trip') {
    const trip = findTrip(view.tripId)
    page = trip ? <TripPage trip={trip} items={items.filter(i => i.tripId === trip.id)} onBack={() => setView({ page: 'list' })} onEdit={() => setView({ page: 'tripForm', id: trip.id })} onOpenDay={date => setView({ page: 'day', tripId: trip.id, date })} onAdd={date => setView({ page: 'itemForm', tripId: trip.id, date })} onEditItem={id => {
      const item = items.find(i => i.id === id)
      setView({ page: 'itemForm', tripId: trip.id, date: item?.date || trip.startDate, id })
    }} /> : <Empty title="旅行不存在" desc="这段旅行可能已被删除" action="返回列表" onClick={() => setView({ page: 'list' })}/>
  }
  if (view.page === 'day') {
    const trip = findTrip(view.tripId)
    page = trip ? <DayPage trip={trip} date={view.date} items={items.filter(i => i.tripId === trip.id && i.date === view.date)} onBack={() => setView({ page: 'trip', tripId: trip.id })} onAdd={() => setView({ page: 'itemForm', tripId: trip.id, date: view.date })} onEdit={id => setView({ page: 'itemForm', tripId: trip.id, date: view.date, id })} onToggle={id => setItems(v => v.map(i => i.id === id ? { ...i, completed: !i.completed, updatedAt: new Date().toISOString() } : i))} onCopy={to => {
      const source = items.filter(i => i.tripId === trip.id && i.date === view.date)
      const now = new Date().toISOString()
      setItems(v => [...v, ...source.map(i => ({ ...i, id: uid('item'), date: to, completed: false, createdAt: now, updatedAt: now }))])
    }} /> : <Empty title="旅行不存在" desc="这段旅行可能已被删除" action="返回列表" onClick={() => setView({ page: 'list' })}/>
  }
  if (view.page === 'itemForm') {
    const trip = findTrip(view.tripId)
    const editing = view.id ? items.find(i => i.id === view.id) : undefined
    page = trip ? <ItemForm trip={trip} item={editing} date={view.date} onBack={() => setView({ page: 'day', tripId: trip.id, date: view.date })} onRemove={editing ? () => {
      setItems(v => v.filter(i => i.id !== editing.id))
      setView({ page: 'day', tripId: trip.id, date: editing.date })
    } : undefined} onSave={draft => {
      if (editing) setItems(v => v.map(i => i.id === editing.id ? { ...i, ...draft, updatedAt: new Date().toISOString() } : i))
      else setItems(v => [...v, { ...draft, id: uid('item'), sortIndex: items.filter(i => i.tripId === trip.id && i.date === draft.date && !i.startTime).length, createdAt: new Date().toISOString(), updatedAt: new Date().toISOString() }])
      setView({ page: 'day', tripId: trip.id, date: draft.date })
    }} /> : <Empty title="旅行不存在" desc="这段旅行可能已被删除" action="返回列表" onClick={() => setView({ page: 'list' })}/>
  }

  return <div ref={root} className="miniapp-root"><main className="xl-shell">{storageError ? <div className="xl-toast">{storageError}</div> : null}{page}</main></div>
}

function TripList({ trips, items, onOpen, onCreate, onEdit, onRemove, onDemo }: { trips: Trip[]; items: ItineraryItem[]; onOpen: (id: string) => void; onCreate: () => void; onEdit: (id: string) => void; onRemove: (trip: Trip) => void; onDemo: () => void }) {
  const sorted = useMemo(() => [...trips].sort((a, b) => a.startDate.localeCompare(b.startDate)), [trips])
  return <>
    <header className="list-head"><div><h1>行旅日记</h1><p>记录与规划你的每一段旅程</p></div><button className="add-round" onClick={onCreate} aria-label="新建旅行"><Icon name="plus"/></button></header>
    {sorted.length === 0 ? <Empty title="还没有旅行计划" desc="创建第一段旅行，把每天的安排记下来" action="新建旅行" onClick={onCreate} /> : <div className="trip-list">{sorted.map(trip => {
      const list = items.filter(i => i.tripId === trip.id)
      const complete = list.filter(i => i.completed).length
      return <article className="trip-card" key={trip.id} onClick={() => onOpen(trip.id)}>
        <Cover trip={trip} small/>
        <div className="trip-body"><div className="trip-name"><b>{trip.name}</b><span><button onClick={e => { e.stopPropagation(); onEdit(trip.id) }} aria-label="编辑"><Icon name="edit" size={16}/></button><button onClick={e => { e.stopPropagation(); onRemove(trip) }} aria-label="删除"><Icon name="trash" size={16}/></button></span></div><p><Icon name="pin" size={13}/>{trip.destination} · {fmtMd(trip.startDate)} – {fmtMd(trip.endDate)}</p><Progress value={list.length ? complete / list.length * 100 : 0}/><small>{list.length ? `已完成 ${complete}/${list.length}` : '还没有行程安排'}</small></div>
      </article>
    })}</div>}
    <div className="demo-line"><button onClick={onDemo}>载入示例旅行</button><span>数据保存在本机浏览器</span></div>
  </>
}

function TripForm({ trip, onBack, onSave, onRemove }: { trip?: Trip; onBack: () => void; onSave: (draft: Omit<Trip, 'id' | 'createdAt' | 'updatedAt'>) => void; onRemove?: () => void }) {
  const [name, setName] = useState(trip?.name || '')
  const [destination, setDestination] = useState(trip?.destination || '')
  const [startDate, setStartDate] = useState(trip?.startDate || today())
  const [endDate, setEndDate] = useState(trip?.endDate || addDays(today(), 2))
  const [budget, setBudget] = useState(trip?.totalBudget?.toString() || '')
  const [notes, setNotes] = useState(trip?.notes || '')
  const [cover, setCover] = useState(trip?.coverImage || 'preset:0')
  const submit = () => {
    if (!name.trim() || !destination.trim() || endDate < startDate) return
    onSave({ name: name.trim(), destination: destination.trim(), startDate, endDate, coverImage: cover, totalBudget: budget ? Number(budget) : null, notes })
  }
  const upload = async (file?: File) => { if (file) try { setCover(await compressImage(file)) } catch { window.alert('图片处理失败，请换一张图片重试。') } }
  const coverTrip = { name, destination, coverImage: cover }
  return <>
    <header className="xl-page-head"><button className="xl-back" onClick={onBack}><Icon name="back"/></button><div className="xl-page-title">{trip ? '编辑旅行' : '新建旅行'}</div><button className="xl-save" onClick={submit}>保存</button></header>
    <div className="form-card xl-card">
      <div className="cover-select"><Cover trip={coverTrip}/><div><b>旅行封面</b><div className="swatches">{covers.map((bg, index) => <button key={bg} style={{ background: bg }} className={cover === `preset:${index}` ? 'active' : ''} onClick={() => setCover(`preset:${index}`)}/>) }<label className="upload"><Icon name="image" size={16}/><input hidden type="file" accept="image/*" onChange={e => upload(e.target.files?.[0])}/></label></div></div></div>
      <Field label="旅行名称" required><input className="xl-input" value={name} onChange={e => setName(e.target.value)} placeholder="如：青岛海滨三日游"/></Field>
      <Field label="目的地" required><input className="xl-input" value={destination} onChange={e => setDestination(e.target.value)} placeholder="如：山东 · 青岛"/></Field>
      <Field label="起止日期" required><div className="date-row"><input className="xl-input" type="date" value={startDate} onChange={e => setStartDate(e.target.value)}/><span>至</span><input className="xl-input" type="date" min={startDate} value={endDate} onChange={e => setEndDate(e.target.value)}/></div></Field>
      <Field label="总预算（元）"><input className="xl-input" inputMode="decimal" value={budget} onChange={e => setBudget(e.target.value)} placeholder="选填，如 3000"/></Field>
      <Field label="旅行备注"><textarea className="xl-textarea" value={notes} onChange={e => setNotes(e.target.value)} placeholder="装备、预订或同行提醒…"/></Field>
    </div>
    <div className="xl-bottom"><button className="xl-btn xl-primary" onClick={submit}>保存旅行</button>{onRemove ? <button className="xl-btn xl-danger" onClick={onRemove}>删除</button> : null}</div>
  </>
}

function TripPage({ trip, items, onBack, onEdit, onOpenDay, onAdd, onEditItem }: { trip: Trip; items: ItineraryItem[]; onBack: () => void; onEdit: () => void; onOpenDay: (date: string) => void; onAdd: (date: string) => void; onEditItem: (id: string) => void }) {
  const [tab, setTab] = useState<'calendar' | 'timeline' | 'overview'>('calendar')
  const days = datesBetween(trip.startDate, trip.endDate)
  const byDate = (date: string) => items.filter(i => i.date === date).sort(itemSort)
  const spent = items.reduce((sum, item) => sum + (item.cost || 0), 0)
  const completed = items.filter(i => i.completed).length
  const firstCalendarDate = today() >= trip.startDate && today() <= trip.endDate ? today() : trip.startDate
  const initialMonth = parseDate(firstCalendarDate)
  const [month, setMonth] = useState({ year: initialMonth.getFullYear(), month: initialMonth.getMonth() })
  const [selectedDate, setSelectedDate] = useState(firstCalendarDate)
  const shiftMonth = (delta: number) => setMonth(current => { const next = new Date(current.year, current.month + delta, 1); return { year: next.getFullYear(), month: next.getMonth() } })
  const defaultDate = selectedDate
  return <>
    <section className="hero"><Cover trip={trip}/><button className="hero-back" onClick={onBack}><Icon name="back"/></button><button className="hero-edit" onClick={onEdit}><Icon name="edit" size={17}/></button><div><h1>{trip.name}</h1><p><Icon name="pin" size={13}/>{trip.destination} · {fmtMd(trip.startDate)} – {fmtMd(trip.endDate)} · {days.length}天</p></div></section>
    <div className="tabline">{(['calendar', 'timeline', 'overview'] as const).map(key => <button key={key} className={tab === key ? 'active' : ''} onClick={() => setTab(key)}><Icon name={key === 'calendar' ? 'calendar' : key === 'timeline' ? 'list' : 'grid'} size={15}/>{key === 'calendar' ? '日历' : key === 'timeline' ? '时间轴' : '概览'}</button>)}</div>
    {tab === 'calendar' ? <MonthCalendar trip={trip} month={month} selectedDate={selectedDate} items={items} onPrev={() => shiftMonth(-1)} onNext={() => shiftMonth(1)} onSelect={setSelectedDate} onEditItem={onEditItem} /> : null}
    {tab === 'timeline' ? <section className="timeline-all">{days.map((date, index) => { const list = byDate(date); return <div className="all-day" key={date}><button className="all-head" onClick={() => onOpenDay(date)}><span><b>{fmtMd(date)}</b><small>{weekday(date)} · 第{index + 1}天</small></span><i>{list.length ? `${list.length} 项` : '暂无安排'}</i><Icon name="right" size={14}/></button>{list.map(item => <button className="compact" key={item.id} onClick={() => onEditItem(item.id)}><time>{item.startTime || '待定'}</time><em style={{ background: TYPE_INFO[item.type].color }}/><Icon name={typeIcon(item.type)} size={14}/><span>{item.completed ? <s>{item.title}</s> : item.title}</span></button>)}</div> })}</section> : null}
    {tab === 'overview' ? <section className="overview"><div className="xl-card budget"><h3><Icon name="wallet" size={17}/>预算与花费</h3><b>¥ {spent}</b>{trip.totalBudget !== null ? <><span>/ 预算 ¥ {trip.totalBudget}</span><Progress value={trip.totalBudget ? spent / trip.totalBudget * 100 : 0}/><p>{spent <= trip.totalBudget ? `还剩 ¥${trip.totalBudget - spent} 可花` : `已超支 ¥${spent - trip.totalBudget}`}</p></> : <p>暂未设置总预算</p>}</div><div className="xl-card stats"><b>{completed}/{items.length}<small>已完成</small></b>{ITEM_TYPES.map(type => { const count = items.filter(i => i.type === type).length; return count ? <span key={type} style={{ color: TYPE_INFO[type].color }}>{count}<small>{TYPE_INFO[type].label}</small></span> : null })}</div><div className="xl-card overview-days"><h3>每日安排</h3>{days.map((date, index) => { const list = byDate(date); return <button key={date} onClick={() => onOpenDay(date)}><span><b>{fmtMd(date)}</b><small>{weekday(date)} · 第{index + 1}天</small></span><i>{list.length ? `${list.length} 项 · 完成 ${list.filter(i => i.completed).length}` : '暂无安排'}</i><Icon name="right" size={14}/></button> })}</div></section> : null}
    {tab !== 'overview' ? <div className="xl-fab-row"><button className="xl-fab" onClick={() => onAdd(defaultDate)}><Icon name="plus" size={27}/></button></div> : null}
  </>
}

function MonthCalendar({ trip, month, selectedDate, items, onPrev, onNext, onSelect, onEditItem }: { trip: Trip; month: { year: number; month: number }; selectedDate: string; items: ItineraryItem[]; onPrev: () => void; onNext: () => void; onSelect: (date: string) => void; onEditItem: (id: string) => void }) {
  const cells = monthGrid(month.year, month.month).flat()
  const typeDots = (date: string) => [...new Set(items.filter(item => item.date === date).map(item => item.type))].slice(0, 3)
  return <section className="month-calendar"><section className="xl-card cal"><div className="cal-head"><button onClick={onPrev}><Icon name="back"/></button><b>{month.year}年{month.month + 1}月</b><button onClick={onNext}><Icon name="right"/></button></div><div className="week">{['一', '二', '三', '四', '五', '六', '日'].map(day => <span key={day}>{day}</span>)}</div><div className="grid">{cells.map((date, index) => { if (!date) return <span key={index}/>; const active = date >= trip.startDate && date <= trip.endDate; const types = typeDots(date); return <button key={date} className={`${active ? 'inside' : ''} ${date === selectedDate ? 'selected' : ''} ${date === today() ? 'today' : ''}`} onClick={() => active && onSelect(date)}><b>{Number(date.slice(-2))}</b><i>{types.map(type => <em key={type} style={{ background: TYPE_INFO[type].color }}/>)}</i></button> })}</div><p className="cal-tip">选择日期，在下方查看完整时间轴</p></section><DayTimeline trip={trip} date={selectedDate} items={items} onEditItem={onEditItem}/></section>
}

function DayTimeline({ trip, date, items, onEditItem }: { trip: Trip; date: string; items: ItineraryItem[]; onEditItem: (id: string) => void }) {
  const hourStart = 0, hourEnd = 24, hourHeight = 62
  const hotels = items.filter(item => item.type === 'hotel' && item.date <= date && (item.endDate || item.date) >= date)
  const timed = items.filter(item => item.type !== 'hotel' && item.startTime && item.date <= date && (item.endDate || item.date) >= date).sort(itemSort)
  const pending = items.filter(item => item.type !== 'hotel' && item.date === date && !item.startTime)
  const minutes = (value: string) => { const [h = '0', m = '0'] = value.split(':'); return Number(h) * 60 + Number(m) }
  const segment = (item: ItineraryItem) => ({ start: item.date === date ? minutes(item.startTime) : 0, end: (item.endDate || item.date) === date ? (item.endTime ? minutes(item.endTime) : minutes(item.startTime) + 60) : 24 * 60 })
  const blocks = timed.map(item => { const piece = segment(item); const start = Math.max(hourStart * 60, piece.start); const end = Math.min(hourEnd * 60, Math.max(start + 30, piece.end)); const overlaps = timed.filter(other => { if (other.id === item.id) return false; const otherPiece = segment(other); return otherPiece.start < end && otherPiece.end > start }); const ordered = [item, ...overlaps].sort((a,b) => a.id.localeCompare(b.id)); const slot = ordered.findIndex(x => x.id === item.id); return { item, start, end, top: (start - hourStart * 60) / 60 * hourHeight, height: Math.max(38, (end - start) / 60 * hourHeight), width: 100 / ordered.length, left: slot * 100 / ordered.length } })
  const dayItemCount = [...new Set([...hotels, ...timed, ...pending].map(item => item.id))].length
  return <section className="day-schedule xl-card"><div className="day-schedule-head"><div><b>{fmtDate(date)}</b><small>第 {diffDays(date, trip.startDate) + 1} 天 · {dayItemCount} 项安排</small></div></div>{hotels.length ? <div className="day-all-day"><span>全天</span><div>{hotels.map(item => <button key={item.id} onClick={() => onEditItem(item.id)}><Icon name="bed" size={14}/>{item.details.hotelName || item.title}</button>)}</div></div> : null}<div className="day-timeline"><div className="day-time-labels">{Array.from({ length: hourEnd - hourStart + 1 }, (_, index) => <span key={index} style={{ top: index * hourHeight }}>{String(hourStart + index).padStart(2, '0')}:00</span>)}</div><div className="day-time-grid" style={{ height: (hourEnd - hourStart) * hourHeight }}>{blocks.map(({ item, start, end, top, height, width, left }) => { const continuedFromPrevious = item.date < date; const continuesNext = (item.endDate || item.date) > date; return <button key={`${item.id}-${date}`} className={`day-time-event ${continuedFromPrevious ? 'continued-from' : ''} ${continuesNext ? 'continues-next' : ''}`} style={{ top, height, width: `calc(${width}% - 4px)`, left: `calc(${left}% + 2px)`, borderColor: TYPE_INFO[item.type].color, background: TYPE_INFO[item.type].bg, color: TYPE_INFO[item.type].color }} onClick={() => onEditItem(item.id)}><b>{item.title}</b><small>{String(Math.floor(start / 60)).padStart(2, '0')}:{String(start % 60).padStart(2, '0')} – {end === 1440 ? '24:00' : `${String(Math.floor(end / 60)).padStart(2, '0')}:${String(end % 60).padStart(2, '0')}`}{item.location ? ` · ${item.location}` : ''}</small>{continuedFromPrevious || continuesNext ? <i>{continuedFromPrevious ? '接续前日' : '次日抵达'}</i> : null}</button> })}</div></div>{pending.length ? <div className="day-pending"><b>待定事项</b>{pending.map(item => <button key={item.id} onClick={() => onEditItem(item.id)}><i style={{ background: TYPE_INFO[item.type].color }}/>{item.title}</button>)}</div> : null}{!hotels.length && !timed.length && !pending.length ? <div className="day-schedule-empty">这一天还没有安排</div> : null}</section>
}

function DayPage({ trip, date, items, onBack, onAdd, onEdit, onToggle, onCopy }: { trip: Trip; date: string; items: ItineraryItem[]; onBack: () => void; onAdd: () => void; onEdit: (id: string) => void; onToggle: (id: string) => void; onCopy: (date: string) => void }) {
  const sorted = [...items].sort(itemSort)
  const completed = items.filter(i => i.completed).length
  const copy = () => { const target = window.prompt('复制到哪一天？（YYYY-MM-DD）', addDays(date, 1)); if (target && target >= trip.startDate && target <= trip.endDate) onCopy(target) }
  return <>
    <header className="xl-page-head"><button className="xl-back" onClick={onBack}><Icon name="back"/></button><div className="xl-page-title"><div>{fmtDate(date)}</div><div className="xl-page-sub">第 {diffDays(date, trip.startDate) + 1} 天 · {items.length} 项安排 · 已完成 {completed}</div></div></header>
    {items.length === 0 ? <Empty title="今天还没有安排" desc="添加一条行程吧" action="添加行程" onClick={onAdd} /> : <div className="day-list">{sorted.map(item => <article className={`day-item ${item.completed ? 'done' : ''}`} key={item.id} onClick={() => onEdit(item.id)}><div className="time"><b>{item.startTime || '待定'}</b><small>{item.endTime}{item.endDate && item.endDate !== item.date ? ` · ${fmtMd(item.endDate)}到` : ''}</small></div><div className="rail"><i style={{ background: TYPE_INFO[item.type].color }}/></div><div className="day-card"><div><TypeChip type={item.type}/><button className="check" onClick={e => { e.stopPropagation(); onToggle(item.id) }}><Icon name={item.completed ? 'check' : 'circle'} size={20}/></button></div><h3>{item.title}</h3>{item.location ? <p><Icon name="pin" size={13}/>{item.location}</p> : null}{item.details.fromPlace || item.details.toPlace ? <p><Icon name="right" size={13}/>{item.details.fromPlace} → {item.details.toPlace}</p> : null}{item.precautions ? <p className="warn"><Icon name="alert" size={13}/>{item.precautions}</p> : null}{item.notes ? <p><Icon name="note" size={13}/>{item.notes}</p> : null}{item.cost !== null ? <p><Icon name="wallet" size={13}/>预估 ¥{item.cost}</p> : null}{item.images.length ? <div className="thumbs">{item.images.slice(0, 3).map((src, index) => <img src={src} key={index}/>)}</div> : null}</div></article>)}</div>}
    <div className="xl-bottom"><button className="xl-btn xl-ghost" onClick={copy}><Icon name="copy" size={16}/>复制这天</button><button className="xl-btn xl-primary" onClick={onAdd}><Icon name="plus" size={17}/>添加行程</button></div>
  </>
}

function ItemForm({ trip, item, date, onBack, onSave, onRemove }: { trip: Trip; item?: ItineraryItem; date: string; onBack: () => void; onSave: (draft: ItemDraft) => void; onRemove?: () => void }) {
  const [type, setType] = useState<ItemType>(item?.type || 'sightseeing')
  const [title, setTitle] = useState(item?.title || '')
  const [day, setDay] = useState(item?.date || date)
  const [endDate, setEndDate] = useState(item?.endDate || item?.date || date)
  const [startTime, setStartTime] = useState(item?.startTime || '')
  const [endTime, setEndTime] = useState(item?.endTime || '')
  const [location, setLocation] = useState(item?.location || '')
  const [address, setAddress] = useState(item?.address || '')
  const [transport, setTransport] = useState(item?.transport || '')
  const [cost, setCost] = useState(item?.cost?.toString() || '')
  const [precautions, setPrecautions] = useState(item?.precautions || '')
  const [notes, setNotes] = useState(item?.notes || '')
  const [completed, setCompleted] = useState(item?.completed || false)
  const [details, setDetails] = useState<ItemDetails>(item?.details || {})
  const [images, setImages] = useState<string[]>(item?.images || [])
  const [formError, setFormError] = useState('')
  const setDetail = (key: keyof ItemDetails, value: string) => setDetails(v => ({ ...v, [key]: value }))
  const upload = async (files: FileList | null) => {
    if (!files) return
    try { const next = await Promise.all(Array.from(files).slice(0, 4 - images.length).map(file => compressImage(file, 900))); setImages(v => [...v, ...next]) } catch { window.alert('图片处理失败，请换一张图片重试。') }
  }
  const submit = () => {
    const autoTitleByType: Record<ItemType, string> = {
      transport: [details.fromPlace, details.toPlace].filter(Boolean).join(' → '),
      sightseeing: details.ticketInfo || details.openTime || location,
      dining: details.restaurantName || location,
      hotel: details.hotelName || location,
      free: location,
      other: location,
    }
    const finalTitle = title.trim() || autoTitleByType[type] || TYPE_INFO[type].label
    if (!day || !endDate || day < trip.startDate || day > trip.endDate || endDate < trip.startDate || endDate > trip.endDate) {
      setFormError(`开始和结束日期都需要在 ${fmtMd(trip.startDate)} 至 ${fmtMd(trip.endDate)} 之间`)
      return
    }
    if (endDate < day) {
      setFormError('结束日期不能早于开始日期')
      return
    }
    if (endDate === day && startTime && endTime && endTime < startTime) {
      setFormError('同一天的结束时间不能早于开始时间；跨天请调整结束日期')
      return
    }
    setFormError('')
    onSave({ tripId: trip.id, date: day, endDate, startTime, endTime: startTime ? endTime : '', type, title: finalTitle, location, address, transport, cost: cost ? Number(cost) : null, precautions, notes, images, completed, details })
  }
  return <>
    <header className="xl-page-head"><button className="xl-back" onClick={onBack}><Icon name="back"/></button><div className="xl-page-title">{item ? '编辑行程' : '添加行程'}</div><button className="xl-save" onClick={submit}>保存</button></header>
    <div className="form-card xl-card">
      <Field label="行程类型"><div className="types">{ITEM_TYPES.map(key => <button key={key} className={type === key ? 'selected' : ''} style={type === key ? { color: TYPE_INFO[key].color, background: TYPE_INFO[key].bg, borderColor: TYPE_INFO[key].color } : {}} onClick={() => setType(key)}><Icon name={typeIcon(key)} size={17}/>{TYPE_INFO[key].label}</button>)}</div></Field>
      <Field label="行程标题" required><input className="xl-input" value={title} onChange={e => setTitle(e.target.value)} placeholder="如：参观栈桥、入住酒店"/></Field>
      <Field label={type === 'transport' ? '出发 / 到达日期' : type === 'hotel' ? '入住 / 退房日期' : '日期'} required><div className="date-row"><input className="xl-input" type="date" min={trip.startDate} max={trip.endDate} value={day} onChange={e => { setDay(e.target.value); if (endDate < e.target.value) setEndDate(e.target.value) }}/><span>至</span><input className="xl-input" type="date" min={day || trip.startDate} max={trip.endDate} value={endDate} onChange={e => setEndDate(e.target.value)}/></div>{type === 'transport' ? <p className="xl-hint">跨天航班、夜车等可把到达日期设为次日</p> : null}</Field>
      {type === 'transport' ? <Field label="出发 / 到达时间"><div className="date-row"><input className="xl-input" type="time" value={startTime} onChange={e => setStartTime(e.target.value)}/><span>至</span><input className="xl-input" type="time" value={endTime} onChange={e => setEndTime(e.target.value)}/></div></Field> : null}
      {type !== 'transport' && type !== 'hotel' ? <Field label="开始 / 结束时间"><div className="date-row"><input className="xl-input" type="time" value={startTime} onChange={e => setStartTime(e.target.value)}/><span>至</span><input className="xl-input" type="time" value={endTime} onChange={e => setEndTime(e.target.value)}/></div><p className="xl-hint">不填开始时间会归入「待定事项」</p></Field> : null}
      {type !== 'transport' ? <><Field label={type === 'hotel' ? '酒店位置' : '地点'}><input className="xl-input" value={location} onChange={e => setLocation(e.target.value)} placeholder={type === 'hotel' ? '酒店所在区域或地标' : '景点、餐厅或集合点'}/></Field><Field label="地址"><input className="xl-input" value={address} onChange={e => setAddress(e.target.value)} placeholder="详细地址（选填）"/></Field></> : null}
      {type !== 'transport' && type !== 'hotel' ? <Field label="交通方式"><input className="xl-input" value={transport} onChange={e => setTransport(e.target.value)} placeholder="如：步行、地铁、打车"/></Field> : null}
      <TypeFields type={type} details={details} setDetail={setDetail}/>
      <Field label="预估花费（元）"><input className="xl-input" inputMode="decimal" value={cost} onChange={e => setCost(e.target.value)} placeholder="选填"/></Field>
      <Field label="注意事项"><textarea className="xl-textarea" value={precautions} onChange={e => setPrecautions(e.target.value)} placeholder="预约、证件、天气或排队提醒…"/></Field>
      <Field label="备注"><textarea className="xl-textarea" value={notes} onChange={e => setNotes(e.target.value)} placeholder="补充想法或旅行记录…"/></Field>
      <Field label="图片"><div className="images">{images.map((src, index) => <span key={src}><img src={src}/><button onClick={() => setImages(v => v.filter((_, i) => i !== index))}><Icon name="x" size={13}/></button></span>)}{images.length < 4 ? <label><Icon name="image"/><input hidden type="file" multiple accept="image/*" onChange={e => upload(e.target.files)}/></label> : null}</div></Field>
      <Field label="是否已完成"><button className={`finish ${completed ? 'yes' : ''}`} onClick={() => setCompleted(v => !v)}><Icon name={completed ? 'check' : 'circle'} size={18}/>{completed ? '已完成' : '未完成'}</button></Field>
    </div>
    <div className="xl-bottom">{formError ? <p className="xl-form-error" role="alert">{formError}</p> : null}<button className="xl-btn xl-primary" onClick={submit}>保存行程</button>{onRemove ? <button className="xl-btn xl-danger" onClick={() => { if (window.confirm('确定删除这条行程吗？')) onRemove() }}>删除</button> : null}</div>
  </>
}

function TypeFields({ type, details, setDetail }: { type: ItemType; details: ItemDetails; setDetail: (key: keyof ItemDetails, value: string) => void }) {
  const input = (label: string, key: keyof ItemDetails, placeholder: string, kind = 'text') => <Field label={label}><input className="xl-input" type={kind} value={details[key] || ''} onChange={e => setDetail(key, e.target.value)} placeholder={placeholder}/></Field>
  if (type === 'transport') return <>{input('交通工具', 'vehicle', '飞机 / 高铁 / 打车')}{input('航班号 / 车次', 'flightNo', '如 G222 / MU5137')}{input('出发地', 'fromPlace', '如 上海虹桥')}{input('目的地', 'toPlace', '如 青岛北')}</>
  if (type === 'sightseeing') return <>{input('开放时间', 'openTime', '如 08:30–17:00')}{input('门票信息', 'ticketInfo', '价格、优惠或购票入口')}{input('预约要求', 'bookingReq', '是否需提前预约')}{input('预计游玩时长', 'duration', '如 约 2 小时')}</>
  if (type === 'hotel') return <>{input('酒店名称', 'hotelName', '酒店名称')}{input('入住时间', 'checkinTime', '', 'time')}{input('退房时间', 'checkoutTime', '', 'time')}{input('预订编号', 'bookingNo', '订单号 / 确认号')}</>
  if (type === 'dining') return <>{input('餐厅名称', 'restaurantName', '餐厅名称')}{input('预约信息', 'reservationInfo', '如 已订 19:00 · 4 人')}{input('人均预算', 'avgBudget', '如 80 元/人')}{input('推荐菜', 'recommendDish', '想吃的菜 / 招牌菜')}</>
  return null
}
