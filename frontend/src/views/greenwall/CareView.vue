<template>
  <section class="page" data-module="greenwall-care">
    <header class="page-head">
      <div>
        <h2>垂直绿墙养护视图</h2>
        <p class="page-desc">
          按区域汇总垂直绿墙面积与长势达标率；同一绿墙重复巡检只取最新一版，
          缺灌与达标率偏低的区域排在最前，点击区域可下钻到具体绿墙。
        </p>
      </div>
      <div class="page-actions">
        <RouterLink class="btn" to="/greenwall">立体绿化台账</RouterLink>
        <button class="btn ghost" type="button" @click="refresh">刷新最新巡检口径</button>
      </div>
    </header>

    <div class="stat-row">
      <article class="stat-card">
        <span class="stat-label">在养区域</span>
        <strong class="stat-value">{{ regions.length }}</strong>
      </article>
      <article class="stat-card">
        <span class="stat-label">缺灌区域</span>
        <strong class="stat-value danger">{{ shortCount }}</strong>
      </article>
      <article class="stat-card">
        <span class="stat-label">达标率偏低区域（&lt;{{ thresholdPercent }}%）</span>
        <strong class="stat-value" :class="{ danger: lowCount > 0 }">{{ lowCount }}</strong>
      </article>
      <article class="stat-card">
        <span class="stat-label">暂无巡检绿墙</span>
        <strong class="stat-value">{{ uninspectedWalls }}</strong>
      </article>
    </div>

    <p v-if="errorMessage" class="error-text">{{ errorMessage }}</p>

    <table class="data-table care-table">
      <thead>
        <tr>
          <th class="col-toggle"></th>
          <th>所属区域</th>
          <th>垂直绿墙面积（㎡）</th>
          <th>绿墙数</th>
          <th>长势达标率</th>
          <th>灌溉情况</th>
          <th>资料缺失</th>
        </tr>
      </thead>
      <tbody>
        <template v-for="region in regions" :key="region.所属区域">
          <tr
            class="region-row"
            :class="{
              expanded: expandedArea === region.所属区域,
              'row-danger': region.short_irrigation,
              'row-warn': !region.short_irrigation && region.low_rate,
            }"
            @click="toggleRegion(region.所属区域)"
          >
            <td class="col-toggle">{{ expandedArea === region.所属区域 ? '▾' : '▸' }}</td>
            <td class="strong">{{ region.所属区域 }}</td>
            <td>{{ region.总面积 }}</td>
            <td>{{ region.绿墙数量 }}（已巡检 {{ region.inspected_count }}）</td>
            <td>
              <span v-if="region.rate_percent === null" class="tag tag-empty">暂无</span>
              <span v-else :class="regionRateClass(region)">
                {{ region.rate_percent }}%
              </span>
            </td>
            <td>
              <span v-if="region.short_irrigation" class="tag tag-danger">缺灌</span>
              <span v-else class="tag tag-ok">正常</span>
            </td>
            <td>
              <span v-if="region.crew_missing_count" class="tag tag-warn">
                缺养护班组 ×{{ region.crew_missing_count }}
              </span>
              <span v-if="region.irrigation_missing_count" class="tag tag-warn">
                缺灌溉方式 ×{{ region.irrigation_missing_count }}
              </span>
              <span v-if="!region.crew_missing_count && !region.irrigation_missing_count" class="muted">—</span>
            </td>
          </tr>
          <template v-if="expandedArea === region.所属区域">
            <tr v-for="wall in wallsByRegion[region.所属区域] ?? []" :key="wall.编号" class="wall-row">
              <td class="col-toggle"></td>
              <td>
                <RouterLink class="link" :to="`/greenwall/${wall.id}`">{{ wall.编号 }} · {{ wall.名称 }}</RouterLink>
              </td>
              <td>{{ wall.面积 }}</td>
              <td :colspan="2">
                <span v-if="wall.rate_percent === null" class="tag tag-empty">暂无巡检</span>
                <span v-else :class="rateClass(wall.rate_percent, wall.short_irrigation)">
                  {{ wall.rate_percent }}%
                </span>
                <span v-if="wall.latest_patrol_date" class="muted">（最近巡检 {{ wall.latest_patrol_date }}）</span>
              </td>
              <td>
                <span v-if="wall.short_irrigation" class="tag tag-danger">缺灌</span>
                <span v-else-if="wall.irrigation_missing" class="tag tag-warn">灌溉方式缺失</span>
                <span v-else>{{ wall.灌溉方式 }}</span>
              </td>
              <td>
                <span v-if="wall.crew_missing" class="tag tag-warn">养护班组缺失</span>
                <span v-else>{{ wall.养护班组 }}</span>
              </td>
            </tr>
            <tr v-if="!(wallsByRegion[region.所属区域] ?? []).length">
              <td colspan="7" class="empty-state">绿墙明细加载中…</td>
            </tr>
          </template>
        </template>
        <tr v-if="!regions.length">
          <td colspan="7" class="empty-state">暂无垂直绿墙数据</td>
        </tr>
      </tbody>
    </table>

    <footer class="page-foot">
      <span>共 {{ regions.length }} 个区域，达标率与巡检记录同源，台账页与详情页读到的结果一致</span>
    </footer>
  </section>
</template>

<script setup lang="ts">
import { computed, nextTick, onActivated, onMounted, ref } from 'vue'
import { onBeforeRouteLeave } from 'vue-router'

import { useGreenwallCareStore } from '@/stores/greenwallCare'

const care = useGreenwallCareStore()
const errorMessage = ref('')

const regions = computed(() => care.regions)
const wallsByRegion = computed(() => care.wallsByRegion)
const expandedArea = computed(() => care.expandedArea)
const thresholdPercent = computed(() => Math.round(care.lowRateThreshold * 100))

const shortCount = computed(() => regions.value.filter((r) => r.short_irrigation).length)
const lowCount = computed(() => regions.value.filter((r) => r.low_rate).length)
const uninspectedWalls = computed(() => {
  let count = 0
  for (const region of regions.value) {
    count += region.绿墙数量 - region.inspected_count
  }
  return count
})

function rateClass(rate: number, short: boolean) {
  if (short || rate < care.lowRateThreshold * 100) return 'rate-danger'
  if (rate < 90) return 'rate-warn'
  return 'rate-ok'
}

function regionRateClass(region: { rate_percent: number | null; short_irrigation: boolean }) {
  return rateClass(region.rate_percent ?? 0, region.short_irrigation)
}

async function toggleRegion(area: string) {
  const opening = care.expandedArea !== area
  care.setExpanded(opening ? area : '')
  care.saveScroll(window.scrollY)
  if (opening) {
    try {
      await care.ensureRegionWalls(area)
    } catch (error) {
      errorMessage.value = error instanceof Error ? error.message : '区域明细读取失败'
    }
  }
}

async function refresh() {
  errorMessage.value = ''
  care.invalidate()
  const area = care.expandedArea
  try {
    await care.ensureRegions(true)
    if (area) {
      await care.ensureRegionWalls(area, true)
      care.setExpanded(area)
    }
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '养护视图读取失败'
  }
}

onMounted(async () => {
  try {
    await care.ensureRegions()
    if (care.expandedArea) await care.ensureRegionWalls(care.expandedArea)
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '养护视图读取失败'
  }
})

// keep-alive 缓存本页：从详情页返回时恢复展开区域与滚动位置，停在原处。
onActivated(async () => {
  if (care.expandedArea) await care.ensureRegionWalls(care.expandedArea)
  await nextTick()
  window.scrollTo(0, care.scrollTop)
})

// 点绿墙跳详情前记录滚动位置
onBeforeRouteLeave(() => {
  care.saveScroll(window.scrollY)
})
</script>

<style scoped>
.care-table .region-row { cursor: pointer; }
.col-toggle { width: 28px; text-align: center; color: var(--muted); }
.strong { font-weight: 600; }
.wall-row td { background: #f9fbfd; }
.row-danger { background: #fef3f2; }
.row-warn { background: #fffaeb; }
.expanded { background: #eef4ff; }
.rate-ok { font-weight: 600; color: #067647; }
.rate-warn { font-weight: 600; color: #b54708; }
.rate-danger { font-weight: 700; color: #b42318; }
.danger { color: #b42318; }
.muted { color: var(--muted); font-size: 12px; }
.tag { display: inline-block; padding: 1px 8px; border-radius: 10px; font-size: 12px; line-height: 18px; }
.tag-danger { background: #fee4e2; color: #b42318; }
.tag-warn { background: #fef0c7; color: #b54708; margin-right: 4px; }
.tag-ok { background: #dcfae6; color: #067647; }
.tag-empty { background: #e5e7eb; color: #475467; }
</style>
