<script setup lang="ts">
import { onMounted, ref, watch, computed, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { NButton, NCard, NSpin, NSpace, NTag, NEmpty, NProgress, NPopconfirm, useMessage } from 'naive-ui'
import { useResumeStore } from '../stores/resume'
import { useJobsStore } from '../stores/jobs'
import { resumesApi } from '../api/resume'

const store = useResumeStore()
const jobsStore = useJobsStore()
const route = useRoute()
const router = useRouter()
const message = useMessage()
const jobId = computed(() => route.params.jobId as string)

const currentTab = ref<string>('full')
const selectedResumeId = ref<string | null>(null)
const showPreview = ref(false)
const selectedJob = ref<any>(null)

function normScore(raw: any): number {
  if (raw == null) return 0
  const n = Number(raw)
  if (isNaN(n)) return 0
  return n <= 1 ? Math.round(n * 100) : Math.round(n)
}

function stripMarkdown(text: string | null | undefined): string {
  if (!text) return ''
  return text
    .replace(/^#{1,6}\s+/gm, '')
    .replace(/\*{1,3}([^*]+)\*{1,3}/g, '$1')
    .replace(/^[\s]*[-*+]\s+/gm, '  • ')
    .replace(/^(\d+)\.\s+/gm, '$1. ')
    .replace(/^[-*_]{3,}\s*$/gm, '')
    .replace(/`([^`]+)`/g, '$1')
    .replace(/\[([^\]]+)\]\([^)]+\)/g, '$1')
    .replace(/\n{3,}/g, '\n\n')
    .trim()
}

function getCurrentContent(): string {
  if (!store.current) return ''
  let raw = ''
  switch (currentTab.value) {
    case 'full': raw = store.current.full_resume || ''; break
    case 'strengths': raw = store.current.core_strengths || ''; break
    case 'work': raw = store.current.work_experience || ''; break
    case 'projects': raw = store.current.project_exp || ''; break
    case 'education': raw = store.current.education || ''; break
  }
  return stripMarkdown(raw) || '暂无内容'
}

onMounted(async () => {
  await store.fetchAll()
  await jobsStore.fetchAll()
})

onUnmounted(() => {
  store.cancelPolling()
})

function selectJob(j: any) {
  selectedJob.value = j
  showPreview.value = false
  store.current = null
  store.cancelPolling()
  // 筛选该岗位的历史版本
  store.fetchByJob(j.id)
}

async function handleStartGenerate() {
  if (!selectedJob.value) return
  showPreview.value = false
  try {
    await store.startGenerate(selectedJob.value.id)
    // 生成完成，不自动预览，显示"点击预览"
    showPreview.value = false
  } catch (e: any) {
    message.error('生成失败: ' + (e.message || '未知错误'))
  }
}

function handlePreview() {
  showPreview.value = true
  currentTab.value = 'full'
}

async function viewResume(id: string) {
  selectedJob.value = null
  selectedResumeId.value = id
  showPreview.value = true
  currentTab.value = 'full'
  await store.getResume(id)
}

async function handleDeleteResume(id: string) {
  await store.deleteResume(id)
  if (selectedResumeId.value === id) {
    selectedResumeId.value = null
    store.current = null
    showPreview.value = false
  }
  message.success('已删除')
}

async function handleExportResume(id: string) {
  try {
    const res = await resumesApi.exportDoc(id)
    const url = window.URL.createObjectURL(new Blob([res.data]))
    const a = document.createElement('a')
    a.href = url
    a.download = 'resume-v' + (store.resumes.find((r: any) => r.id === id)?.version || '') + '.md'
    a.click()
    window.URL.revokeObjectURL(url)
    message.success('导出成功')
  } catch (e) {
    message.error('导出失败')
  }
}

const tabs = [
  { key: 'full', label: '📄 完整简历' },
  { key: 'strengths', label: '💪 核心优势' },
  { key: 'work', label: '💼 工作经历' },
  { key: 'projects', label: '🚀 项目经验' },
  { key: 'education', label: '🎓 教育经历' },
]
</script>

<template>
  <div>
    <h2 class="text-2xl font-bold text-blue-600 mb-6">📝 制作简历</h2>

    <div class="flex gap-6" style="min-height: 70vh;">

      <!-- ====== 左侧 ====== -->
      <div class="flex flex-col gap-4" style="width: 380px; flex-shrink: 0;">

        <n-card title="📋 选择岗位" class="bg-white border border-slate-200" size="small">
          <div v-if="jobsStore.analyses.length === 0" class="text-slate-400 text-sm py-2">
            暂无岗位，请先去 <router-link to="/jobs" class="text-blue-500 hover:underline">应聘分析</router-link>
          </div>
          <div v-for="j in jobsStore.analyses" :key="j.id"
            class="flex items-center justify-between py-2 px-2 border-b border-slate-100 last:border-0 rounded cursor-pointer transition-colors"
            :class="selectedJob?.id === j.id ? 'bg-blue-50 border-blue-200' : 'hover:bg-slate-50'"
            @click="selectJob(j)">
            <div class="min-w-0 flex-1">
              <div class="font-medium text-sm truncate">{{ j.title || '未命名岗位' }}</div>
              <div class="text-xs text-slate-400 truncate">{{ j.company || '未知公司' }}</div>
            </div>
            <n-tag :type="normScore(j.match_result?.overall_match)>=70?'success':'warning'" size="tiny" class="ml-2 shrink-0">
              {{ normScore(j.match_result?.overall_match) }}%
            </n-tag>
          </div>
        </n-card>

        <n-card title="📜 历史版本" class="bg-white border border-slate-200 flex-1 overflow-hidden" size="small">
          <div v-if="!selectedJob" class="text-slate-400 text-sm py-4 text-center">请先选择一个岗位</div>
          <div v-else-if="store.resumes.length === 0" class="text-slate-400 text-sm py-4 text-center">该岗位还没有简历</div>
          <div class="overflow-y-auto" style="max-height: 45vh;">
            <div v-for="r in store.resumes" :key="r.id"
              class="py-2.5 px-2 border-b border-slate-100 last:border-0 rounded cursor-pointer transition-colors"
              :class="selectedResumeId === r.id && showPreview ? 'bg-blue-50' : 'hover:bg-slate-50'"
              @click="viewResume(r.id)">
              <div class="flex items-center justify-between mb-1">
                <span class="font-medium text-sm">版本 {{ r.version }}</span>
                <n-tag :type="r.status === 'reviewed' ? 'success' : 'default'" size="tiny">
                  {{ r.status === 'reviewed' ? '已评估' : '草稿' }}
                </n-tag>
              </div>
              <div class="text-xs text-slate-400 truncate" v-if="r.job_title">{{ r.job_title }} @ {{ r.company }}</div>
              <div class="text-xs text-slate-300 mt-1">{{ r.created_at?.slice(0, 10) }}</div>
              <div class="flex gap-1.5 mt-2">
                <n-button size="tiny" type="success" @click.stop="handleExportResume(r.id)">导出</n-button>
                <router-link :to="`/review/${r.id}`"><n-button size="tiny" type="warning" @click.stop>评估</n-button></router-link>
                <n-popconfirm @positive-click="() => handleDeleteResume(r.id)">
                  <template #trigger><n-button size="tiny" type="error" @click.stop>删除</n-button></template>
                  确认删除版本 {{ r.version }}？
                </n-popconfirm>
              </div>
            </div>
          </div>
        </n-card>
      </div>

      <!-- ====== 右侧 ====== -->
      <div class="flex-1 min-w-0 flex flex-col gap-4">

        <!-- 未选择 -->
        <n-card v-if="!selectedJob && !showPreview && !store.generating && store.genProgress?.stage !== 'done'" class="bg-white border border-slate-200 flex-1">
          <div class="flex flex-col items-center justify-center py-20 text-slate-400">
            <div class="text-5xl mb-4">👈</div>
            <p class="text-lg font-medium">请从左侧选择一个岗位</p>
            <p class="text-sm mt-1">选择岗位后点击「立即生成」按钮开始制作简历</p>
          </div>
        </n-card>

        <!-- 已选岗位，显示"立即生成" -->
        <n-card v-if="selectedJob && !store.generating && store.genProgress?.stage !== 'done' && !showPreview" class="bg-white border border-slate-200 flex-1">
          <div class="flex flex-col items-center justify-center py-16">
            <div class="text-4xl mb-4">🎯</div>
            <p class="text-xl font-bold text-slate-800 mb-1">{{ selectedJob.title || '未命名岗位' }}</p>
            <p class="text-base text-blue-500 font-medium mb-2">{{ selectedJob.company || '未知公司' }}</p>
            <n-tag :type="normScore(selectedJob.match_result?.overall_match)>=70?'success':'warning'" size="medium" class="mb-6">
              匹配度 {{ normScore(selectedJob.match_result?.overall_match) }}%
            </n-tag>
            <n-button type="primary" size="large" @click="handleStartGenerate" style="min-width: 200px;">
              🚀 立即生成简历
            </n-button>
            <p class="text-xs text-slate-400 mt-3">AI 将根据你的个人信息库，结合该岗位要求定制生成</p>
          </div>
        </n-card>

        <!-- 生成中：进度条 -->
        <n-card v-if="store.generating && store.genProgress" class="bg-white border border-blue-200 flex-1">
          <div class="flex flex-col items-center justify-center py-16 px-8">
            <div class="text-4xl mb-6">⏳</div>
            <p class="text-lg font-bold text-blue-600 mb-6">AI 正在制作简历...</p>

            <div class="w-full max-w-md mb-4">
              <n-progress type="line" :percentage="store.genProgress.pct" :height="12" :border-radius="6"
                :color="store.genProgress.stage === 'error' ? '#ef4444' : '#3b82f6'" :indicator-placement="'inside'" />
            </div>

            <p class="text-sm text-slate-600 mb-2 font-medium">{{ store.genProgress.message || '处理中...' }}</p>

            <div class="mt-6 text-sm space-y-1.5">
              <p :class="store.genProgress.pct >= 25 ? 'text-green-600 font-medium' : 'text-slate-400'">
                {{ store.genProgress.pct >= 25 ? '✅' : store.genProgress.stage === 'core' ? '⏳' : '○' }} 提炼核心优势
              </p>
              <p :class="store.genProgress.pct >= 50 ? 'text-green-600 font-medium' : 'text-slate-400'">
                {{ store.genProgress.pct >= 50 ? '✅' : store.genProgress.stage === 'work' ? '⏳' : '○' }} 匹配岗位梳理工作经历
              </p>
              <p :class="store.genProgress.pct >= 75 ? 'text-green-600 font-medium' : 'text-slate-400'">
                {{ store.genProgress.pct >= 75 ? '✅' : store.genProgress.stage === 'projects' ? '⏳' : '○' }} 整理项目经验
              </p>
              <p :class="store.genProgress.pct >= 85 ? 'text-green-600 font-medium' : 'text-slate-400'">
                {{ store.genProgress.pct >= 85 ? '✅' : store.genProgress.stage === 'education' ? '⏳' : '○' }} 提取教育经历
              </p>
              <p :class="store.genProgress.pct >= 100 ? 'text-green-600 font-medium' : 'text-slate-400'">
                {{ store.genProgress.pct >= 100 ? '✅' : store.genProgress.stage === 'merge' ? '⏳' : '○' }} 整合生成完整简历
              </p>
            </div>

            <p class="text-xs text-slate-300 mt-6">预计需要 1-3 分钟，请耐心等待</p>
          </div>
        </n-card>

        <!-- 生成完成：提示预览 -->
        <n-card v-if="!store.generating && store.genProgress?.stage === 'done' && !showPreview" class="bg-white border border-green-300 flex-1">
          <div class="flex flex-col items-center justify-center py-16">
            <div class="text-5xl mb-4">🎉</div>
            <p class="text-xl font-bold text-green-600 mb-2">简历制作完成！</p>
            <p class="text-sm text-slate-500 mb-6">版本 {{ store.current?.version }} · {{ selectedJob?.title }} @ {{ selectedJob?.company }}</p>
            <n-space>
              <n-button type="primary" size="large" @click="handlePreview">👁️ 预览简历</n-button>
              <n-button type="success" size="large" @click="handleExportResume(store.current!.id)">📤 导出简历</n-button>
            </n-space>
          </div>
        </n-card>

        <!-- 历史版本预览 -->
        <template v-if="showPreview && store.current">
          <div class="flex gap-2 flex-wrap">
            <n-tag v-for="tab in tabs" :key="tab.key"
              :type="currentTab === tab.key ? 'primary' : 'default'"
              :bordered="false" class="cursor-pointer" @click="currentTab = tab.key">
              {{ tab.label }}
            </n-tag>
          </div>

          <n-card class="bg-white border border-slate-200 flex-1 overflow-hidden">
            <div class="overflow-y-auto" style="max-height: 60vh;">
              <div class="whitespace-pre-wrap text-slate-700 leading-relaxed text-sm" style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'PingFang SC', 'Microsoft YaHei', sans-serif;">
                {{ getCurrentContent() }}
              </div>
            </div>
          </n-card>

          <div class="flex justify-between">
            <n-button @click="showPreview = false; selectedJob = null">← 返回选择</n-button>
            <n-button type="success" @click="handleExportResume(store.current!.id)">📤 导出简历</n-button>
          </div>
        </template>
      </div>
    </div>
  </div>
</template>
