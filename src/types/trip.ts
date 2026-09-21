export type ItemType = 'transport' | 'sightseeing' | 'dining' | 'hotel' | 'free' | 'other'

export interface ItemDetails {
  vehicle?: string
  flightNo?: string
  fromPlace?: string
  toPlace?: string
  openTime?: string
  ticketInfo?: string
  bookingReq?: string
  duration?: string
  hotelName?: string
  checkinTime?: string
  checkoutTime?: string
  bookingNo?: string
  restaurantName?: string
  reservationInfo?: string
  avgBudget?: string
  recommendDish?: string
}

export interface Trip {
  id: string
  name: string
  destination: string
  startDate: string
  endDate: string
  coverImage: string
  totalBudget: number | null
  notes: string
  createdAt: string
  updatedAt: string
}

export interface ItineraryItem {
  id: string
  tripId: string
  /** 行程开始日期；日历与时间轴归属到此日期。 */
  date: string
  /** 行程结束日期；未填写时与开始日期相同。 */
  endDate?: string
  startTime: string
  endTime: string
  type: ItemType
  title: string
  location: string
  address: string
  transport: string
  cost: number | null
  precautions: string
  notes: string
  images: string[]
  completed: boolean
  sortIndex: number
  details: ItemDetails
  createdAt: string
  updatedAt: string
}

export const ITEM_TYPES: ItemType[] = ['transport', 'sightseeing', 'dining', 'hotel', 'free', 'other']

export const TYPE_INFO: Record<ItemType, { label: string; color: string; bg: string; icon: string }> = {
  transport: { label: '交通', color: '#4E9CF0', bg: '#E9F2FE', icon: 'plane' },
  sightseeing: { label: '景点', color: '#45A97C', bg: '#E8F5EE', icon: 'camera' },
  dining: { label: '餐饮', color: '#E8944A', bg: '#FCF2E6', icon: 'utensils' },
  hotel: { label: '酒店', color: '#8B7CE0', bg: '#F1EEFC', icon: 'bed' },
  free: { label: '自由活动', color: '#7E93A8', bg: '#EFF3F7', icon: 'sun' },
  other: { label: '其他', color: '#3FAFA9', bg: '#E6F5F4', icon: 'flag' },
}
