<script setup lang="ts">
import { onMounted, ref, h } from 'vue'
import { useRouter } from 'vue-router'
import { NButton, NInput, NCard, NDataTable, NPopconfirm, NTag, NSpace, NModal, NSpin, NDescriptions, NDescriptionsItem, NUpload, NImage, NProgress, useMessage } from 'naive-ui'
import { useJobsStore } from '../stores/jobs'
import { jobsApi } from '../api/jobs'
import api from '../api/client'

const store = useJobsStore()
const router = useRouter()
const message = useMessage()

const requirement = ref('')
const sourceUrl = ref('')
const analyzing = ref(false)
const showDetail = ref(false)
const researching = ref<Record<string, boolean>>({})
const editingId = ref('')
const editTitle = ref('')
const editCompany = ref('')
const saving = ref(false)

// 截图上传
const screenshotFile = ref<File | null>(null)
const screenshotPreview = ref('')
const screenshotBase64 = ref('')
const uploadMode = ref<'text' | 'screenshot'>('text')

// 进度轮询
const progressStage = ref('')
const progressMsg = ref('')
const progressPct = ref(0)
const pollingJobId = ref('')
let pollTimer: ReturnType<typeof setInterval> | null = null

onMounted(() => store.fetchAll())

const stageLabels: Record<string, string> = {
  pending: '⏳ 任务已创建',
  ocr: '🔍 OCR 识别截图文字',
  extracting: '🧠 AI 提取岗位关键信息',
  matching: '🎯 分析匹配度',
  researching: '🏢 查询企业信息',
  advising: '📋 生成投递建议',
  done: '✅ 分析完成',
  error: '❌ 分析失败',
}

const recMap: Record<string, { label: string; type: 'success' | 'warning' | 'error' | 'default' }> = {
  recommend: { label: '🟢 推荐', type: 'success' },
  cautious: { label: '🟡 谨慎', type: 'warning' },
  avoid: { label: '🔴 不建议', type: 'error' },
  unknown: { label: '❓ 未知', type: 'default' },
}

function normScore(raw: any): number {
  if (raw == null) return 0
  const n = Number(raw)
  if (isNaN(n)) return 0
  return n <= 1 ? Math.round(n * 100) : Math.round(n)
}

const columns = [
  { title: '岗位', key: 'title', ellipsis: { tooltip: true }, width: 160 },
  { title: '公司', key: 'company', width: 130 },
  {
    title: '匹配度', key: 'match', width: 80,
    render: (row: any) => {
      const score = normScore(row.match_result?.overall_match)
      const type = score >= 70 ? 'success' : score >= 50 ? 'warning' : 'error'
      return h(NTag, { type, size: 'small' }, () => `${score}%`)
    }
  },
  {
    title: '投递建议', key: 'recommendation', width: 100,
    render: (row: any) => {
      const r = recMap[row.recommendation] || recMap.unknown
      return h(NTag, { type: r.type, size: 'small' }, () => r.label)
    }
  },
  { title: '时间', key: 'created_at', width: 110, render: (row: any) => row.created_at?.slice(0, 10) },
  {
    title: '操作', key: 'actions', width: 260,
    render: (row: any) => h(NSpace, () => [
      h(NButton, { size: 'tiny', onClick: () => viewDetail(row) }, () => '查看'),
      h(NButton, { size: 'tiny', type: 'info', loading: researching.value[row.id], onClick: () => researchCompany(row) }, () => '查企业'),
      h(NButton, { size: 'tiny', type: 'primary', onClick: () => router.push(`/resume/${row.id}`) }, () => '生成简历'),
      h(NPopconfirm, { onPositiveClick: () => handleDelete(row.id) }, {
        trigger: () => h(NButton, { size: 'tiny', type: 'error' }, () => '删除'),
        default: () => '确认删除？',
      }),
    ]),
  },
]

function handleFileChange(options: { file: any; fileList: any[] }) {
  const file = options.file.file as File
  if (!file || !file.type.startsWith('image/')) return
  screenshotFile.value = file
  const reader = new FileReader()
  reader.onload = (e) => {
    screenshotBase64.value = e.target?.result as string
    screenshotPreview.value = e.target?.result as string
  }
  reader.readAsDataURL(file)
}

function clearScreenshot() {
  screenshotFile.value = null
  screenshotPreview.value = ''
  screenshotBase64.value = ''
}

function stopPolling() {
  if (pollTimer) { clearInterval(pollTimer); pollTimer = null }
}

async function startPolling(jobId: string) {
  pollingJobId.value = jobId
  stopPolling()
  pollTimer = setInterval(async () => {
    try {
      const resp = await jobsApi.getStatus(jobId)
      const s = resp.data
      progressStage.value = s.stage
      progressMsg.value = s.message
      progressPct.value = s.pct
      if (s.stage === 'done' || s.stage === 'error') {
        stopPolling()
        if (s.stage === 'done') {
          try {
            const full = await jobsApi.get(jobId)
            store.analyses.unshift(full.data)
            store.current = full.data
            message.success('截图分析完成')
            if (full.data.advice) message.info(full.data.advice)
            clearScreenshot()
          } catch (e: any) {
            message.error('获取分析结果失败，请刷新页面查看')
          }
        }
        if (s.stage === 'error') {
          message.error(s.message || '分析失败')
        }
        // 无论成功失败都清理状态
        analyzing.value = false
        progressStage.value = ''
        progressMsg.value = ''
        progressPct.value = 0
      }
    } catch {
      // ignore polling errors
    }
  }, 1500)
}

async function handleAnalyze() {
  // 截图模式
  if (uploadMode.value === 'screenshot' && screenshotBase64.value) {
    analyzing.value = true
    progressStage.value = 'pending'
    progressMsg.value = '任务已创建，等待处理...'
    progressPct.value = 0
    try {
      const resp = await jobsApi.analyzeScreenshot(screenshotBase64.value)
      const jobId = resp.data.job_id
      startPolling(jobId)
    } catch (e: any) {
      message.error('分析失败: ' + (e.response?.data?.detail || e.message))
      analyzing.value = false
      progressStage.value = ''
    }
    return
  }

  // 文本模式
  if (!requirement.value.trim()) {
    message.warning('请输入岗位要求或上传截图')
    return
  }
  analyzing.value = true
  try {
    const resp = await store.analyze(requirement.value, sourceUrl.value || undefined)
    message.success('分析完成')
    if (resp?.advice) message.info(resp.advice)
    requirement.value = ''
    sourceUrl.value = ''
  } catch (e: any) {
    message.error('分析失败: ' + (e.response?.data?.detail || e.message))
  } finally { analyzing.value = false }
}

async function researchCompany(row: any) {
  researching.value[row.id] = true
  try {
    const resp = await api.post(`/jobs/${row.id}/research`)
    if (resp.data) {
      store.updateAnalysis(row.id, resp.data)
      if (resp.data.cached) {
        message.success('企业信息已缓存，直接调取')
      } else {
        message.success('企业调研完成')
      }
      if (resp.data.advice) message.info(resp.data.advice)
      // Auto-open detail to show enterprise info
      store.current = store.analyses.find(a => a.id === row.id) || resp.data
      showDetail.value = true
    }
  } catch (e: any) {
    message.error('调研失败: ' + (e.response?.data?.detail || e.message))
  } finally { researching.value[row.id] = false }
}

async function saveEdit() {
  if (!editingId.value) return
  saving.value = true
  try {
    const updated = await store.saveEdit(editingId.value, {
      title: editTitle.value,
      company: editCompany.value,
    })
    if (store.current?.id === editingId.value) {
      store.current.title = updated.title
      store.current.company = updated.company
    }
    message.success('已保存')
    editingId.value = ''
  } catch (e: any) {
    message.error('保存失败: ' + (e.response?.data?.detail || e.message))
  } finally { saving.value = false }
}

function startEdit(row: any) {
  editingId.value = row.id
  editTitle.value = row.title
  editCompany.value = row.company || ''
}

function cancelEdit() {
  editingId.value = ''
}

function viewDetail(row: any) {
  store.current = row
  showDetail.value = true
}

async function handleDelete(id: string) {
  await store.deleteAnalysis(id)
  message.success('已删除')
}
</script>

<template>
  <div>
    <h2 class="text-2xl font-bold text-blue-600 mb-6">🎯 应聘分析</h2>

    <!-- 输入区 -->
    <n-card class="bg-white border border-slate-200 mb-6">
      <n-space vertical>
        <!-- 模式切换 -->
        <div class="flex gap-2">
          <n-tag :type="uploadMode === 'text' ? 'primary' : 'default'" class="cursor-pointer" @click="uploadMode = 'text'">📝 粘贴文本</n-tag>
          <n-tag :type="uploadMode === 'screenshot' ? 'primary' : 'default'" class="cursor-pointer" @click="uploadMode = 'screenshot'">📸 上传截图</n-tag>
        </div>

        <!-- 文本模式 -->
        <template v-if="uploadMode === 'text'">
          <n-input
            v-model:value="requirement"
            type="textarea"
            :rows="6"
            placeholder="粘贴招聘要求内容（自动提取公司名并查询企业信息）..."
          />
          <n-input v-model:value="sourceUrl" placeholder="招聘链接（可选）" />
        </template>

        <!-- 截图模式 -->
        <template v-else>
          <div v-if="!screenshotPreview"
            class="border-2 border-dashed border-slate-300 rounded-xl p-8 text-center cursor-pointer hover:border-blue-400 hover:bg-blue-50/30 transition-colors"
            @click="($refs.uploadRef as any)?.openOpenFileDialog?.()"
          >
            <div class="text-4xl mb-2">📸</div>
            <p class="text-slate-500 font-medium">点击或拖拽上传招聘截图</p>
            <p class="text-slate-400 text-sm mt-1">支持 JPG、PNG、WebP</p>
          </div>
          <div v-else class="relative">
            <img :src="screenshotPreview" class="max-h-64 rounded-xl border border-slate-200 shadow-sm" />
            <n-button size="tiny" type="error" circle class="absolute top-2 right-2 opacity-80" @click="clearScreenshot">✕</n-button>
          </div>
          <n-upload
            ref="uploadRef"
            :show-file-list="false"
            accept="image/*"
            @change="handleFileChange"
            style="display:none"
          />
        </template>

        <n-button type="primary" :loading="analyzing && !progressStage" @click="handleAnalyze" block size="large">
          {{ analyzing ? (progressStage ? '⏳ AI 分析中...' : 'AI 分析中（含企业调研）...') : (uploadMode === 'screenshot' ? '📸 开始识别分析' : '开始分析') }}
        </n-button>

        <!-- 进度条 -->
        <div v-if="progressStage" class="mt-2">
          <div class="flex items-center justify-between mb-1">
            <span class="text-sm font-medium text-blue-600">{{ stageLabels[progressStage] || progressStage }}</span>
            <span class="text-xs text-slate-400">{{ progressPct }}%</span>
          </div>
          <n-progress
            type="line"
            :percentage="progressPct"
            :color="progressStage === 'error' ? '#ef4444' : '#3b82f6'"
            :height="8"
            :border-radius="4"
            :indicator-placement="'inside'"
          />
          <p v-if="progressMsg" class="text-xs text-slate-400 mt-1">{{ progressMsg }}</p>
        </div>
      </n-space>
    </n-card>

    <!-- 历史列表 -->
    <n-dataTable
      :columns="columns"
      :data="store.analyses"
      :loading="store.loading"
      :bordered="false"
      class="bg-white border border-slate-200 rounded-lg"
    />

    <!-- 无数据 / 错误提示 -->
    <n-card v-if="!store.loading && store.analyses.length === 0" class="bg-white border border-slate-200 mt-4 text-center py-8">
      <p class="text-slate-400 text-lg mb-2">📭 {{ store.error || '暂无应聘分析记录' }}</p>
      <p class="text-slate-400 text-sm">粘贴岗位要求或上传截图，开始第一份分析</p>
    </n-card>

    <!-- 详情弹窗 -->
    <n-modal v-model:show="showDetail" preset="card" title="分析详情" style="width: 800px">
      <n-spin :show="!store.current">
        <n-space vertical v-if="store.current">
          <div class="flex items-center gap-3 mb-2 flex-wrap">
            <!-- 编辑模式 -->
            <template v-if="editingId === store.current.id">
              <n-input v-model:value="editTitle" size="small" placeholder="岗位名称" style="width:200px" />
              <span class="text-slate-400">@</span>
              <n-input v-model:value="editCompany" size="small" placeholder="公司名称" style="width:180px" />
              <n-button size="tiny" type="primary" :loading="saving" @click="saveEdit">保存</n-button>
              <n-button size="tiny" @click="cancelEdit">取消</n-button>
            </template>
            <!-- 查看模式 -->
            <template v-else>
              <span class="text-lg font-bold">{{ store.current.title }}</span>
              <span class="text-slate-400">@</span>
              <span class="text-blue-500 font-medium">{{ store.current.company }}</span>
              <n-button size="tiny" type="tertiary" @click="startEdit(store.current)" class="ml-1">✏️</n-button>
            </template>
            <n-tag :type="normScore(store.current.match_result?.overall_match)>=70?'success':'warning'" size="medium">
              匹配 {{ normScore(store.current.match_result?.overall_match) }}%
            </n-tag>
            <n-tag v-if="store.current.recommendation"
              :type="recMap[store.current.recommendation]?.type || 'default'" size="medium">
              {{ recMap[store.current.recommendation]?.label }}
            </n-tag>
          </div>

          <n-card v-if="store.current.enterprise_info" title="🏢 企业信息" size="small" class="bg-blue-50/50">
            <n-descriptions :column="2" size="small" label-placement="left">
              <n-descriptions-item label="成立时间">{{ store.current.enterprise_info.established || '-' }}</n-descriptions-item>
              <n-descriptions-item label="注册资本">{{ store.current.enterprise_info.registered_capital ? store.current.enterprise_info.registered_capital + '万' : '-' }}</n-descriptions-item>
              <n-descriptions-item label="规模">{{ store.current.enterprise_info.employee_count || '-' }}</n-descriptions-item>
              <n-descriptions-item label="地址">{{ store.current.enterprise_info.address || '-' }}</n-descriptions-item>
              <n-descriptions-item label="业务" :span="2">{{ store.current.enterprise_info.business_scope || '-' }}</n-descriptions-item>
              <n-descriptions-item v-if="store.current.enterprise_info.qualifications?.length" label="资质">
                <n-space>
                  <n-tag v-for="q in store.current.enterprise_info.qualifications" :key="q" type="info" size="small">{{ q }}</n-tag>
                </n-space>
              </n-descriptions-item>
              <n-descriptions-item v-if="store.current.enterprise_info.risk_signals?.length" label="⚠️ 风险">
                <n-space>
                  <n-tag v-for="r in store.current.enterprise_info.risk_signals" :key="r" type="error" size="small">{{ r }}</n-tag>
                </n-space>
              </n-descriptions-item>
            </n-descriptions>
          </n-card>

          <n-card v-else-if="store.current.company" title="🏢 企业信息" size="small" class="bg-slate-50">
            <div class="text-center text-slate-400 py-2">
              尚未查询企业信息
              <n-button size="tiny" type="info" class="ml-2" @click="researchCompany(store.current)">点击查询</n-button>
            </div>
          </n-card>

          <n-card v-if="store.current.advice" title="💬 AI 投递建议" size="small" class="bg-green-50/50">
            <p class="text-slate-600 text-sm">{{ store.current.advice }}</p>
          </n-card>

          <n-card title="📌 简历重点" size="small">
            <ul class="list-disc pl-5 text-slate-500 space-y-1">
              <li v-for="f in store.current.resume_focus?.focus" :key="f">{{ f }}</li>
            </ul>
          </n-card>
          <n-card title="📝 简历策略" size="small">
            <p class="text-slate-500">{{ store.current.resume_focus?.strategy }}</p>
          </n-card>
          <n-card title="⚠️ 不满足项" size="small">
            <ul class="list-disc pl-5 text-red-400 space-y-1">
              <li v-for="g in store.current.match_result?.gap_points" :key="g">{{ g }}</li>
            </ul>
          </n-card>
          <n-card title="✅ 优势项" size="small">
            <ul class="list-disc pl-5 text-green-500 space-y-1">
              <li v-for="s in store.current.match_result?.strength_points" :key="s">{{ s }}</li>
            </ul>
          </n-card>
        </n-space>
      </n-spin>
    </n-modal>
  </div>
</template>
