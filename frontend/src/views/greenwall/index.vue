<template>
  <section class="page" data-module="greenwall">
    <header class="page-head">
      <div>
        <h2>立体绿化台账</h2>
        <p class="page-desc">
          垂直绿墙与屋顶花园统一登记在此；长势达标率取自养护视图的同一口径，
          本页不另行计算，避免与下钻视图出现两套数字。
        </p>
      </div>
      <div class="page-actions">
        <RouterLink class="btn primary" to="/greenwall-care">垂直绿墙养护视图</RouterLink>
      </div>
    </header>

    <form class="filter-bar" @submit.prevent="reload">
      <label class="filter-item">
        <span>编号/名称</span>
        <input v-model="keyword" placeholder="按编号或名称检索" />
      </label>
      <label class="filter-item">
        <span>所属区域</span>
        <input v-model="area" placeholder="按区域检索" />
      </label>
      <label class="filter-item">
        <span>绿化类型</span>
        <select v-model="greenType">
          <option value="">全部</option>
          <option value="垂直绿墙">垂直绿墙</option>
          <option value="屋顶花园">屋顶花园</option>
        </select>
      </label>
      <button class="btn" type="submit">查询</button>
      <button class="btn ghost" type="button" @click="resetFilters">重置条件</button>
    </form>

    <p v-if="errorMessage" class="error-text">{{ errorMessage }}</p>

    <table class="data-table">
      <thead>
        <tr>
          <th v-for="column in columns" :key="column">{{ column }}</th>
          <th>长势达标率</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="row in rows" :key="String(row.id)">
          <td>
            <RouterLink class="link" :to="`/greenwall/${row.id}`">{{ row['编号'] }}</RouterLink>
          </td>
          <td>{{ row['名称'] }}</td>
          <td>{{ row['绿化类型'] }}</td>
          <td>{{ row['所属区域'] }}</td>
          <td>{{ row['面积'] }}</td>
          <td>
            <span v-if="row.crew_missing" class="tag tag-warn">养护班组缺失</span>
            <span v-else>{{ row['养护班组'] || '—' }}</span>
          </td>
          <td>
            <span v-if="row.irrigation_missing" class="tag tag-warn">灌溉方式缺失</span>
            <span v-else>{{ row['灌溉方式'] || '—' }}</span>
          </td>
          <td>
            <!-- 与养护视图同源：优先用共享 store 里按编号索引的达标率 -->
            <span v-if="sharedRate(row['编号']) === null" class="tag tag-empty">暂无</span>
            <span
              v-else
              :class="rateClass(sharedRate(row['编号']) as number)"
            >{{ sharedRate(row['编号']) }}%</span>
          </td>
        </tr>
        <tr v-if="!rows.length">
          <td :colspan="columns.length + 1" class="empty-state">暂无立体绿化数据</td>
        </tr>
      </tbody>
    </table>

    <footer class="page-foot">
      <span>共 {{ total }} 条记录；达标率为 null 表示暂无巡检，不计为 0%</span>
    </footer>
  </section>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'

import { request } from '@/api/client'
import { useGreenwallCareStore, type CareWall } from '@/stores/greenwallCare'

type LedgerRow = CareWall

const columns = ['编号', '名称', '绿化类型', '所属区域', '面积', '养护班组', '灌溉方式']

const care = useGreenwallCareStore()
const rows = ref<LedgerRow[]>([])
const total = ref(0)
const errorMessage = ref('')
const keyword = ref('')
const area = ref('')
const greenType = ref('')

/** 台账接口本身已带 rate_percent；这里再用共享 store 的索引覆盖一遍，
 *  保证巡检刚提交、台账分页尚未刷新时，两个页面读到的仍是同一份数字。 */
function sharedRate(code: string): number | null {
  if (Object.prototype.hasOwnProperty.call(care.rateByCode, code)) {
    return care.rateByCode[code]
  }
  const row = rows.value.find((item) => item.编号 === code)
  return row?.rate_percent ?? null
}

function rateClass(rate: number) {
  if (rate < care.lowRateThreshold * 100) return 'rate-danger'
  if (rate < 90) return 'rate-warn'
  return 'rate-ok'
}

function resetFilters() {
  keyword.value = ''
  area.value = ''
  greenType.value = ''
  void reload()
}

async function reload() {
  errorMessage.value = ''
  const params = new URLSearchParams()
  if (keyword.value) params.set('keyword', keyword.value)
  if (area.value) params.set('area', area.value)
  if (greenType.value) params.set('green_type', greenType.value)
  try {
    const response = await request(`/api/greenwall?${params.toString()}`)
    if (!response.ok) throw new Error('立体绿化台账读取失败')
    const payload = await response.json()
    rows.value = payload.items ?? []
    total.value = payload.total ?? rows.value.length
    // 预热共享口径：下钻视图与详情页随后读到的是同一份区域数据
    await care.ensureRegions().catch(() => undefined)
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '立体绿化台账读取失败'
  }
}

onMounted(reload)
</script>

<style scoped>
.rate-ok { font-weight: 600; color: #067647; }
.rate-warn { font-weight: 600; color: #b54708; }
.rate-danger { font-weight: 700; color: #b42318; }
.tag { display: inline-block; padding: 1px 8px; border-radius: 10px; font-size: 12px; line-height: 18px; }
.tag-warn { background: #fef0c7; color: #b54708; }
.tag-empty { background: #e5e7eb; color: #475467; }
</style>
