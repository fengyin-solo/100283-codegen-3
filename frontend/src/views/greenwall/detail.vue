<template>
  <section class="page" data-module="greenwall-detail">
    <header class="page-head">
      <div>
        <h2>
          <button class="btn back-btn" type="button" @click="backToList">← 返回区域列表</button>
          垂直绿墙详情
        </h2>
        <p class="page-desc">
          达标率取自立体绿化视图同一份计算口径（最新一版巡检），本页不另行计算。
        </p>
      </div>
    </header>

    <div v-if="errorMessage" class="error-banner">{{ errorMessage }}</div>

    <template v-else-if="wall">
      <div class="stat-row">
        <article class="stat-card">
          <span class="stat-label">绿墙编号 / 名称</span>
          <strong class="stat-value detail-title">{{ wall.绿墙编号 }} · {{ wall.绿墙名称 }}</strong>
        </article>
        <article class="stat-card">
          <span class="stat-label">所属区域</span>
          <strong class="stat-value">{{ wall.所属区域 }}</strong>
        </article>
        <article class="stat-card">
          <span class="stat-label">绿墙面积</span>
          <strong class="stat-value">{{ wall.面积 || '未登记' }}</strong>
        </article>
        <article class="stat-card">
          <span class="stat-label">长势达标率（最新巡检）</span>
          <strong v-if="!wall.has_inspection" class="stat-value rate-na">暂无</strong>
          <strong v-else class="stat-value" :class="rateClass(wall.达标率)">
            {{ wall.达标率 === null ? '暂无' : formatRate(wall.达标率) }}
          </strong>
        </article>
      </div>

      <div class="detail-grid">
        <article class="detail-card">
          <h3>台账信息</h3>
          <dl class="info-list">
            <dt>养护班组</dt>
            <dd>
              <span v-if="wall.班组缺失" class="tag tag-miss">缺失 · 待补登记</span>
              <span v-else>{{ wall.养护班组 }}</span>
            </dd>
            <dt>灌溉方式</dt>
            <dd>
              <span v-if="wall.灌溉方式缺失" class="tag tag-miss">缺失 · 待补登记</span>
              <span v-else>{{ wall.灌溉方式 }}</span>
            </dd>
            <dt>植物配置</dt>
            <dd>{{ wall.植物配置 ?? '—' }}</dd>
            <dt>绿墙状态</dt>
            <dd>{{ wall.绿墙状态 ?? '—' }}</dd>
          </dl>
        </article>

        <article class="detail-card">
          <h3>最新一版巡检</h3>
          <dl v-if="latest" class="info-list">
            <dt>巡检编号</dt>
            <dd>{{ latest.巡检编号 }}</dd>
            <dt>巡检日期</dt>
            <dd>{{ latest.巡检日期 }}</dd>
            <dt>提交时间</dt>
            <dd>{{ formatTime(latest.提交时间) }}</dd>
            <dt>巡检人员</dt>
            <dd>{{ latest.巡检人员 }}</dd>
            <dt>长势评价</dt>
            <dd>
              <span v-if="wall.缺灌" class="tag tag-danger">缺灌</span>
              <span v-else-if="wall.达标率偏低" class="tag tag-warn">达标率偏低</span>
              {{ latest.长势评价 || '—' }}
            </dd>
            <dt>灌溉情况</dt>
            <dd :class="{ 'rate-low': wall.缺灌 }">{{ latest.灌溉情况 || '—' }}</dd>
            <dt>问题描述</dt>
            <dd>{{ latest.问题描述 || '无' }}</dd>
          </dl>
          <p v-else class="empty-block">
            暂无巡检记录，达标率显示「暂无」而非 0，请尽快安排首次巡检。
          </p>
        </article>
      </div>

      <article class="detail-card">
        <h3>巡检版本记录（重复提交只取最新一版计入达标率）</h3>
        <table v-if="inspections.length" class="data-table">
          <thead>
            <tr>
              <th>版本</th>
              <th>巡检编号</th>
              <th>巡检日期</th>
              <th>提交时间</th>
              <th>巡检人员</th>
              <th>长势评价</th>
              <th>长势达标率</th>
              <th>灌溉情况</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(item, index) in inspections" :key="item.id" :class="{ 'latest-row': index === 0 }">
              <td>
                <span v-if="index === 0" class="tag tag-latest">最新（计入达标率）</span>
                <span v-else class="muted">历史版本</span>
              </td>
              <td>{{ item.巡检编号 }}</td>
              <td>{{ item.巡检日期 }}</td>
              <td>{{ formatTime(item.提交时间) }}</td>
              <td>{{ item.巡检人员 }}</td>
              <td>{{ item.长势评价 }}</td>
              <td>{{ item.长势达标率 }}</td>
              <td :class="{ 'rate-low': item.灌溉情况 === '缺灌' }">{{ item.灌溉情况 }}</td>
            </tr>
          </tbody>
        </table>
        <p v-else class="empty-block">暂无巡检记录。</p>
      </article>

      <!-- 一致性自检：独立读数接口与详情主数据都来自后端同一计算函数 -->
      <article class="detail-card consistency-card">
        <h3>达标率口径一致性</h3>
        <p v-if="consistencyOk" class="ok-text">
          ✓ 独立读数接口 /api/greenwall/walls/{{ wall.id }}/rate 与本页达标率一致：
          <strong>{{ sharedRateText }}</strong>（与区域下钻视图同源，不存在第二套算法）
        </p>
        <p v-else class="error-text">正在核对独立读数接口……</p>
      </article>
    </template>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { fetchJson } from '@/api/client'
import { useGreenwallStore } from '@/stores/greenwall'

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
  植物配置?: string
  绿墙状态: string
  has_inspection: boolean
  达标率: number | null
  长势评价: string
  灌溉情况: string
  缺灌: boolean
  达标率偏低: boolean
}

type Inspection = {
  id: number
  巡检编号: string
  巡检日期: string
  提交时间: string
  巡检人员: string
  长势评价: string
  长势达标率: string
  灌溉情况: string
  问题描述: string
}

const LOW_RATE = 0.85

const route = useRoute()
const router = useRouter()
const drillStore = useGreenwallStore()

const wall = ref<WallView | null>(null)
const inspections = ref<Inspection[]>([])
const sharedRate = ref<number | null>(null)
const sharedHasInspection = ref<boolean | null>(null)
const errorMessage = ref('')

const latest = computed<Inspection | null>(() => inspections.value[0] ?? null)

const consistencyOk = computed(() => {
  if (!wall.value || sharedHasInspection.value === null) return false
  return (
    sharedHasInspection.value === wall.value.has_inspection &&
    sharedRate.value === wall.value.达标率
  )
})

const sharedRateText = computed(() => {
  if (sharedHasInspection.value === false || sharedRate.value === null) return '暂无'
  return formatRate(sharedRate.value)
})

function formatRate(rate: number): string {
  return `${(rate * 100).toFixed(1)}%`
}

function rateClass(rate: number | null): string {
  if (rate === null) return 'rate-na'
  return rate < LOW_RATE ? 'rate-low' : 'rate-ok'
}

function formatTime(value: string): string {
  return value ? value.replace('T', ' ') : '—'
}

async function backToList() {
  // 列表页被 keep-alive 缓存，配合 store 里记录的展开区域与滚动位置，回到原处
  drillStore.saveScroll()
  if (window.history.state && window.history.state.back) {
    router.back()
  } else {
    router.push('/greenwall')
  }
}

onMounted(async () => {
  const wallId = Number(route.params.id)
  if (!Number.isFinite(wallId)) {
    errorMessage.value = '绿墙编号不合法'
    return
  }
  try {
    const payload = await fetchJson<{ wall: WallView; inspections: Inspection[] }>(
      `/api/greenwall/walls/${wallId}`,
    )
    wall.value = payload.wall
    inspections.value = payload.inspections ?? []

    const shared = await fetchJson<{ 达标率: number | null; has_inspection: boolean }>(
      `/api/greenwall/walls/${wallId}/rate`,
    )
    sharedRate.value = shared.达标率
    sharedHasInspection.value = shared.has_inspection
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '绿墙详情读取失败'
  }
})
</script>

<style scoped>
.back-btn {
  margin-right: 10px;
  padding: 3px 10px;
  font-size: 12px;
}
.detail-title {
  font-size: 16px;
}
.detail-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
  margin-bottom: 12px;
}
.detail-card {
  background: #fff;
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 12px 14px;
  margin-bottom: 12px;
}
.detail-card h3 {
  margin: 0 0 10px;
  font-size: 14px;
}
.info-list {
  display: grid;
  grid-template-columns: 110px 1fr;
  gap: 8px 12px;
  margin: 0;
  font-size: 13px;
}
.info-list dt {
  color: var(--muted);
}
.info-list dd {
  margin: 0;
}
.rate-ok {
  color: #067647;
}
.rate-low {
  color: #b42318;
}
.rate-na {
  color: var(--muted);
  font-style: italic;
  font-weight: 600;
}
.muted {
  color: var(--muted);
  font-size: 12px;
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
.tag-miss {
  background: #f4ebff;
  color: #6941c6;
  border: 1px solid #d9c9f7;
}
.tag-latest {
  background: #e6f4ea;
  color: #067647;
  border: 1px solid #a6dfbb;
}
.latest-row {
  background: #f3fbf6;
}
.empty-block {
  color: var(--muted);
  font-size: 13px;
  margin: 0;
  padding: 8px 0;
}
.error-banner {
  background: #fee4e2;
  border: 1px solid #fda29b;
  color: #b42318;
  border-radius: 8px;
  padding: 10px 14px;
}
.consistency-card .ok-text {
  color: #067647;
  font-size: 13px;
  margin: 0;
}
</style>
