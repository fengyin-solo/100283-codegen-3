<template>
  <section class="page" data-module="greenwall-detail">
    <header class="page-head">
      <div>
        <h2>{{ entry?.['名称'] ?? '立体绿化详情' }}</h2>
        <p class="page-desc">
          编号 {{ entry?.['编号'] }} · {{ entry?.['绿化类型'] }} · {{ entry?.['所属区域'] }}
          ；达标率与养护视图同源，提交新巡检后列表与视图都会刷新到最新版本。
        </p>
      </div>
      <div class="page-actions">
        <button class="btn" type="button" @click="goBack">返回列表（停在原处）</button>
      </div>
    </header>

    <p v-if="errorMessage" class="error-text">{{ errorMessage }}</p>

    <div v-if="entry" class="detail-grid">
      <article class="stat-card">
        <span class="stat-label">绿化面积（㎡）</span>
        <strong class="stat-value">{{ entry['面积'] }}</strong>
      </article>
      <article class="stat-card">
        <span class="stat-label">长势达标率</span>
        <strong v-if="entry.rate_percent === null" class="stat-value muted">暂无</strong>
        <strong v-else class="stat-value" :class="rateClass(entry.rate_percent)">
          {{ entry.rate_percent }}%
        </strong>
        <span v-if="entry.latest_patrol_date" class="stat-label">
          最近巡检：{{ entry.latest_patrol_date }}
        </span>
      </article>
      <article class="stat-card">
        <span class="stat-label">养护班组</span>
        <strong v-if="entry.crew_missing" class="stat-value warn">未配置</strong>
        <strong v-else class="stat-value">{{ entry['养护班组'] }}</strong>
      </article>
      <article class="stat-card">
        <span class="stat-label">灌溉方式</span>
        <strong v-if="entry.irrigation_missing" class="stat-value warn">未配置</strong>
        <strong v-else class="stat-value">{{ entry['灌溉方式'] }}</strong>
      </article>
    </div>

    <div v-if="entry" class="panel">
      <h3>提交巡检（重复提交只认最新一版）</h3>
      <form class="patrol-form" @submit.prevent="submitPatrol">
        <label class="filter-item">
          <span>巡检日期</span>
          <input v-model="form.巡检日期" type="date" />
        </label>
        <label class="filter-item">
          <span>巡检点数</span>
          <input v-model.number="form.巡检点数" type="number" min="1" />
        </label>
        <label class="filter-item">
          <span>达标点数</span>
          <input v-model.number="form.达标点数" type="number" min="0" />
        </label>
        <label class="filter-item">
          <span>灌溉情况</span>
          <select v-model="form.灌溉情况">
            <option value="正常">正常</option>
            <option value="缺灌">缺灌</option>
          </select>
        </label>
        <label class="filter-item">
          <span>巡检人员</span>
          <input v-model="form.巡检人员" placeholder="巡检人员" />
        </label>
        <label class="filter-item grow">
          <span>备注</span>
          <input v-model="form.备注" placeholder="长势、缺灌原因等" />
        </label>
        <button class="btn primary" type="submit">提交巡检</button>
      </form>
      <p v-if="actionMessage" :class="actionOk ? 'ok-text' : 'error-text'">{{ actionMessage }}</p>
    </div>

    <div v-if="entry" class="panel">
      <h3>巡检历史（最新在前）</h3>
      <table class="data-table">
        <thead>
          <tr>
            <th>巡检编号</th><th>巡检日期</th><th>达标点数/巡检点数</th>
            <th>版本达标率</th><th>灌溉情况</th><th>巡检人员</th><th>备注</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(record, index) in entry.patrol_history" :key="record.id"
              :class="{ 'latest-row': index === 0 }">
            <td>
              {{ record['巡检编号'] }}
              <span v-if="index === 0" class="tag tag-ok">当前生效版本</span>
            </td>
            <td>{{ record['巡检日期'] }}</td>
            <td>{{ record['达标点数'] }} / {{ record['巡检点数'] }}</td>
            <td :class="rateClass(Number(record['达标点数']) / Number(record['巡检点数']) * 100)">
              {{ ((Number(record['达标点数']) / Number(record['巡检点数'])) * 100).toFixed(1) }}%
            </td>
            <td>
              <span v-if="record['灌溉情况'] === '缺灌'" class="tag tag-danger">缺灌</span>
              <span v-else>正常</span>
            </td>
            <td>{{ record['巡检人员'] || '—' }}</td>
            <td>{{ record['备注'] || '—' }}</td>
          </tr>
          <tr v-if="!entry.patrol_history.length">
            <td colspan="7" class="empty-state">暂无巡检记录，达标率显示为“暂无”</td>
          </tr>
        </tbody>
      </table>
    </div>
  </section>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { request } from '@/api/client'
import { useGreenwallCareStore, type CareWall } from '@/stores/greenwallCare'

interface PatrolRecord {
  id: number
  巡检编号: string
  巡检日期: string
  巡检点数: number
  达标点数: number
  灌溉情况: string
  巡检人员: string
  备注: string
}

type DetailEntry = CareWall & { patrol_history: PatrolRecord[] }

const route = useRoute()
const router = useRouter()
const care = useGreenwallCareStore()

const entry = ref<DetailEntry | null>(null)
const errorMessage = ref('')
const actionMessage = ref('')
const actionOk = ref(false)

const today = new Date().toISOString().slice(0, 10)
const form = reactive({
  巡检日期: today,
  巡检点数: 20,
  达标点数: 16,
  灌溉情况: '正常',
  巡检人员: '',
  备注: '',
})

function rateClass(rate: number) {
  if (rate < care.lowRateThreshold * 100) return 'rate-danger'
  if (rate < 90) return 'rate-warn'
  return 'rate-ok'
}

async function load() {
  errorMessage.value = ''
  try {
    const response = await request(`/api/greenwall/${route.params.id}`)
    if (!response.ok) throw new Error('立体绿化详情读取失败')
    entry.value = await response.json()
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '详情读取失败'
  }
}

async function submitPatrol() {
  actionMessage.value = ''
  try {
    const response = await request(`/api/greenwall/${route.params.id}/patrols`, {
      method: 'POST',
      body: JSON.stringify({ values: { ...form } }),
    })
    const payload = await response.json()
    if (!response.ok || !payload.ok) {
      throw new Error(payload.message || '巡检提交失败')
    }
    actionOk.value = true
    actionMessage.value = payload.message
    // 关键：让所有页面共享的达标率缓存失效，返回列表后看到的就是新版本算出来的值
    care.invalidate()
    await load()
    await care.ensureRegions(true).catch(() => undefined)
  } catch (error) {
    actionOk.value = false
    actionMessage.value = error instanceof Error ? error.message : '巡检提交失败'
  }
}

function goBack() {
  // 回到养护视图：keep-alive + store 里的展开区域/滚动位置会让页面停在原处；
  // 若来自台账页则回台账。
  if (window.history.state?.back) {
    router.back()
  } else {
    router.push('/greenwall-care')
  }
}

onMounted(load)
</script>

<style scoped>
.detail-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin-bottom: 12px; }
.panel { background: #fff; border: 1px solid var(--border); border-radius: 8px; padding: 12px 16px; margin-bottom: 16px; }
.panel h3 { margin: 0 0 10px; font-size: 15px; }
.patrol-form { display: flex; flex-wrap: wrap; gap: 10px; align-items: flex-end; }
.patrol-form .grow { flex: 1; min-width: 200px; }
.latest-row { background: #f0fdf4; }
.rate-ok { font-weight: 600; color: #067647; }
.rate-warn { font-weight: 600; color: #b54708; }
.rate-danger { font-weight: 700; color: #b42318; }
.warn { color: #b54708; }
.muted { color: var(--muted); }
.ok-text { color: #067647; font-size: 12px; }
.tag { display: inline-block; padding: 1px 8px; border-radius: 10px; font-size: 12px; line-height: 18px; margin-left: 6px; }
.tag-danger { background: #fee4e2; color: #b42318; }
.tag-ok { background: #dcfae6; color: #067647; }
</style>
