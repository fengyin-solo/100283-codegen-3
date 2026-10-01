import { defineStore } from 'pinia'

/**
 * 立体绿化下钻视图的列表态：展开了哪些区域、滚动到了哪里。
 * 从绿墙详情返回时读这里，保证列表停在原处，而不是重新折叠回顶部。
 */
export const useGreenwallStore = defineStore('greenwall', {
  state: () => ({
    /** 已展开的区域名集合（下钻到绿墙层级后仍保留） */
    expandedRegions: [] as string[],
    /** 列表页上次的滚动位置（基于 window 滚动条） */
    scrollY: 0,
  }),
  actions: {
    toggleRegion(region: string) {
      const index = this.expandedRegions.indexOf(region)
      if (index >= 0) {
        this.expandedRegions.splice(index, 1)
      } else {
        this.expandedRegions.push(region)
      }
    },
    saveScroll() {
      this.scrollY = window.scrollY
    },
    restoreScroll() {
      const y = this.scrollY
      window.requestAnimationFrame(() => window.scrollTo(0, y))
    },
  },
})
