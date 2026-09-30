import { defineStore } from 'pinia'

import { request } from '@/api/client'

/** 绿墙行数据：rate_percent 为后端统一口径，null 表示暂无巡检，前端任何地方不得自行计算。 */
export interface CareWall {
  id: number
  编号: string
  名称: string
  绿化类型: string
  所属区域: string
  面积: number
  养护班组: string
  灌溉方式: string
  rate_percent: number | null
  has_patrol: boolean
  short_irrigation: boolean
  crew_missing: boolean
  irrigation_missing: boolean
  latest_patrol_date?: string
}

export interface CareRegion {
  所属区域: string
  绿墙数量: number
  总面积: number
  rate_percent: number | null
  inspected_count: number
  short_irrigation: boolean
  crew_missing_count: number
  irrigation_missing_count: number
  low_rate: boolean
}

/**
 * 垂直绿墙养护视图的唯一数据入口。
 *
 * 列表页、台账页、详情页都从这里拿达标率：同一份缓存对应后端同一个接口口径，
 * 杜绝“视图算一套、台账写一套”。提交巡检后调用 invalidate()，所有页面下次
 * 读取都会重新向后端取数。
 */
export const useGreenwallCareStore = defineStore('greenwall-care', {
  state: () => ({
    regions: [] as CareRegion[],
    wallsByRegion: {} as Record<string, CareWall[]>,
    loaded: false,
    loading: false,
    /** 下钻展开的区域 + 滚动位置：从详情页返回时恢复，停在原处。 */
    expandedArea: '' as string,
    scrollTop: 0,
    lowRateThreshold: 0.8,
  }),
  getters: {
    /** 以绿墙编号为键的达标率索引，供其他页面（如立体绿化台账）读取同一份结果。 */
    rateByCode(state): Record<string, number | null> {
      const index: Record<string, number | null> = {}
      for (const walls of Object.values(state.wallsByRegion)) {
        for (const wall of walls) {
          index[wall.编号] = wall.rate_percent
        }
      }
      return index
    },
  },
  actions: {
    async ensureRegions(force = false) {
      if (this.loading || (this.loaded && !force)) return
      this.loading = true
      try {
        const response = await request('/api/greenwall-care/regions')
        if (!response.ok) throw new Error('区域养护视图读取失败')
        const payload = await response.json()
        this.regions = payload.items ?? []
        this.lowRateThreshold = payload.low_rate_threshold ?? 0.8
        this.loaded = true
      } finally {
        this.loading = false
      }
    },
    async ensureRegionWalls(area: string, force = false) {
      if (this.wallsByRegion[area] && !force) return this.wallsByRegion[area]
      const response = await request(`/api/greenwall-care/regions/${encodeURIComponent(area)}/walls`)
      if (!response.ok) throw new Error('区域绿墙明细读取失败')
      const payload = await response.json()
      this.wallsByRegion[area] = payload.items ?? []
      return this.wallsByRegion[area]
    },
    setExpanded(area: string) {
      this.expandedArea = area
    },
    saveScroll(top: number) {
      this.scrollTop = top
    },
    /** 巡检提交后调用：清空缓存，保证所有页面重新读到后端最新口径。 */
    invalidate() {
      this.loaded = false
      this.regions = []
      this.wallsByRegion = {}
    },
  },
})
