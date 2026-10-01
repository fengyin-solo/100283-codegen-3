<template>
  <section class="page" data-module="greenwall">
    <header class="page-head">
      <div>
        <h2>立体绿化养护</h2>
        <p class="page-desc">
          按区域查看垂直绿墙的面积与长势达标率；同一绿墙重复提交巡检时只取最新一版，
          缺灌与达标率偏低的区域排在最前，点击区域可下钻到具体绿墙。
        </p>
      </div>
      <div class="page-actions">
        <button class="btn" type="button" @click="reload">刷新达标率</button>
      </div>
    </header>

    <div class="stat-row">
      <article v-for="item in stats" :key="item.label" class="stat-card">
        <span class="stat-label">{{ item.label }}</span>
        <strong class="stat-value" :class="item.tone">{{ item.value }}</strong>
      </article>
    </div>

    <table class="data-table greenwall-table">
      <thead>
        <tr>
          <th class="col-toggle"></th>
          <th>所属区域</th>
          <th>垂直绿墙数</th>
          <th>总面积</th>
          <th>长势达标率（面积加权）</th>
          <th>异常提示</th>
        </tr>
      </thead>
      <tbody>
        <template v-for="region in regions" :key="region.所属区域">
          <tr
            class="region-row"
            :class="{ expanded: isExpanded(region.所属区域) }"
            @click="toggle(region.所属区域)"
          >
            <td class="col-toggle"><span class="caret">{{ isExpanded(region.所属区域) ? '▾' : '▸' }}</span></td>
            <td class="region-name">{{ region.所属区域 }}</td>
            <td>{{ region.绿墙数量 }}</td>
            <td>{{ region.总面积平方米 }} ㎡</td>
            <td>
              <span v-if="region.达标率 === null || region.达标率 === undefined" class="rate-na">暂无</span>
              <span v-else :class="rateClass(region.达标率)">{{ formatRate(region.达标率) }}</span>
            </td>
            <td class="tip-cell">
              <span v-if="region.缺灌数量" class="tag tag-danger">缺灌 {{ region.缺灌数量 }}</span>
              <span v-if="region.低达标数量" class="tag tag-warn">达标率偏低 {{ region.低达标数量 }}</span>
              <span v-if="region.无巡检数量" class="tag tag-na">暂无巡检 {{ region.无巡检数量 }}</span>
              <span v-if="region.班组缺失数量" class="tag tag-miss">班组缺失 {{ region.班组缺失数量 }}</span>
              <span v-if="region.灌溉方式缺失数量" class="tag tag-miss">灌溉方式缺失 {{ region.灌溉方式缺失数量 }}</span>
              <span v-if="!hasAnyTip(region)" class="ok-text">正常</span>
            </td>
          </tr>
          <template v-if="isExpanded(region.所属区域)">
            <tr v-for="wall in region.walls" :key="wall.id" class="wall-row">
              <td class="col-toggle"></td>
              <td class="wall-indent">
                <RouterLink class="link" :to="`/greenwall/wall/${wall.id}`" @click="rememberScroll">
                  {{ wall.绿墙编号 }} · {{ wall.绿墙名称 }}
                </RouterLink>
              </td>
              <td>—</td>
              <td>{{ wall.面积 }}</td>
              <td>
                <span v-if="!wall.has_inspection || wall.达标率 === null" class="rate-na">暂无</span>
                <span v-else :class="rateClass(wall.达标率)">{{ formatRate(wall.达标率) }}</span>
              </td>
              <td class="tip-cell">
                <span v-if="wall.缺灌" class="tag tag-danger">缺灌</span>
                <span v-else-if="wall.达标率偏低" class="tag tag-warn">达标率偏低</span>
                <span v-if="!wall.has_inspection" class="tag tag-na">暂无巡检</span>
                <span v-if="wall.班组缺失" class="tag tag-miss">班组缺失</span>
                <span v-if="wall.灌溉方式缺失" class="tag tag-miss">灌溉方式缺失</span>
                <span v-if="wallTippable(wall)" class="wall-meta">{{ wall.长势评价 }}</span>
                <span v-else class="ok-text">{{ wall.长势评价 || '正常' }}</span>
              </td>
            </tr>
          </template>
        </template>
        <tr v-if="!regions.length && !errorMessage">
          <td colspan="6" class="empty-state">暂无立体绿化区域数据</td>
        </tr>
      </tbody>
    </table>

    <footer class="page-foot">
      <span>共 {{ regions.length }} 个区域 · 达标率口径与绿墙详情、其它页面一致</span>
      <span v-if="errorMessage" class="error-text">{{ errorMessage }}</span>
    </footer>
  </section>
</template>

<script setup lang="ts">
import { computed, onActivated, onMounted, ref } from 'vue'

import { fetchJson } from '@/api/client'
import { useGreenwallStore } from '@/stores/greenwall'

// 配合 App.vue 的 <KeepAlive include>：详情页返回时列表实例不销毁，展开与滚动位置保留
defineOptions({ name: 'GreenwallListView' })

type WallView = {
  id: number
  绿墙编号: string
  绿墙名称: string
  所属区域: string
  面积: string
  面积平方米: number
  养护班组: string
  灌溉方式: string
  班组缺失: boolean
  灌溉方式缺失: boolean
  has_inspection: boolean
  达标率: number | null
  长势评价: string
  灌溉情况: string
  缺灌: boolean
  达标率偏低: boolean
}

type RegionSummary = {
  所属区域: string
  绿墙数量: number
  总面积平方米: number
  达标率: number | null
  has_inspection: boolean
  缺灌数量: number
  无巡检数量: number
  低达标数量: number
  班组缺失数量: number
  灌溉方式缺失数量: number
  walls: WallView[]
}

const LOW_RATE = 0.85

const drillStore = useGreenwallStore()
const regions = ref<RegionSummary[]>([])
const errorMessage = ref('')

const stats = computed(() => {
  const walls = regions.value.flatMap((region) => region.walls)
  const inspected = walls.filter((wall) => wall.达标率 !== null)
  const totalArea = walls.reduce((sum, wall) => sum + wall.面积平方米, 0)
  const weighted = inspected.reduce(
    (sum, wall) => sum + (wall.达标率 ?? 0) * wall.面积平方米,
    0,
  )
  const inspectedArea = inspected.reduce((sum, wall) => sum + wall.面积平方米, 0)
  const overall = inspectedArea > 0 ? weighted / inspectedArea : null
  return [
    {
      label: '在养垂直绿墙',
      value: `${walls.length} 片`,
      tone: '',
    },
    {
      label: '绿墙总面积',
      value: `${Math.round(totalArea)} ㎡`,
      tone: '',
    },
    {
      label: '整体长势达标率',
      value: overall === null ? '暂无' : formatRate(overall),
      tone: overall === null ? '' : overall < LOW_RATE ? 'rate-low' : 'rate-ok',    },
    {
      label: '缺灌 / 无巡检',
      value: `${walls.filter((wall) => wall.缺灌).length} / ${walls.filter((wall) => !wall.has_inspection).length}`,
      tone: 'rate-low',
    },
  ]
})

function formatRate(rate: number): string {
  return `${(rate * 100).toFixed(1)}%`
}

function rateClass(rate: number | null): string {
  if (rate === null || rate === undefined) return 'rate-na'
  return rate < LOW_RATE ? 'rate-low' : 'rate-ok'
}

function isExpanded(region: string): boolean {
  return drillStore.expandedRegions.includes(region)
}

function toggle(region: string) {
  drillStore.toggleRegion(region)
}

function rememberScroll() {
  drillStore.saveScroll()
}

function hasAnyTip(region: RegionSummary): boolean {
  return (
    region.缺灌数量 > 0 ||
    region.低达标数量 > 0 ||
    region.无巡检数量 > 0 ||
    region.班组缺失数量 > 0 ||
    region.灌溉方式缺失数量 > 0
  )
}

function wallTippable(wall: WallView): boolean {
  return wall.缺灌 || wall.达标率偏低 || !wall.has_inspection
}

async function reload() {
  errorMessage.value = ''
  try {
    const payload = await fetchJson<{ items: RegionSummary[] }>('/api/greenwall/regions')
    regions.value = payload.items ?? []
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '立体绿化视图读取失败'
  }
}

onMounted(reload)
// keep-alive 缓存下从详情页返回时恢复滚动位置
onActivated(() => drillStore.restoreScroll())
</script>

<style scoped>
.greenwall-table .region-row {
  cursor: pointer;
  background: #f8fafc;
  font-weight: 600;
}
.greenwall-table .region-row:hover {
  background: #eef4ff;
}
.greenwall-table .region-row.expanded {
  background: #eaf2ff;
}
.caret {
  color: var(--brand);
  font-size: 12px;
}
.region-name {
  font-size: 14px;
}
.wall-row td {
  background: #fff;
  color: #334155;
}
.wall-indent {
  padding-left: 34px;
}
.col-toggle {
  width: 36px;
  text-align: center;
}
.rate-ok {
  color: #067647;
  font-weight: 600;
}
.rate-low {
  color: #b42318;
  font-weight: 700;
}
.rate-na {
  color: var(--muted);
  font-style: italic;
}
.tag {
  display: inline-block;
  border-radius: 4px;
  padding: 1px 7px;
  margin-right: 6px;
  font-size: 12px;
  line-height: 1.7;
  white-space: nowrap;
}
.tag-danger {
  background: #fee4e2;
  color: #b42318;
  border: 1px solid #fda29b;
}
.tag-warn {
  background: #fef0c7;
  color: #b54708;
  border: 1px solid #fedf89;
}
.tag-na {
  background: #e9edf2;
  color: #475467;
  border: 1px solid #cbd5e1;
}
.tag-miss {
  background: #f4ebff;
  color: #6941c6;
  border: 1px solid #d9c9f7;
}
.tip-cell {
  white-space: nowrap;
}
.wall-meta {
  margin-left: 4px;
  color: var(--muted);
  font-size: 12px;
}
.ok-text {
  color: #067647;
  font-size: 12px;
}
</style>
