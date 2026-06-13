<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { NButton, NCard, NSpin, NTag, NSpace, NProgress, NEmpty, useMessage } from 'naive-ui'
import { useReviewStore } from '../stores/review'
import { useResumeStore } from '../stores/resume'

const reviewStore = useReviewStore()
const resumeStore = useResumeStore()
const route = useRoute()
const router = useRouter()
const message = useMessage()
const resumeId = route.params.resumeId as string | undefined

const improved = ref<any>(null)

onMounted(async () => {
  await resumeStore.fetchAll()
  if (resumeId) {
    await resumeStore.getResume(resumeId)
    try { await reviewStore.assess(resumeId) } catch (e: any) {
      message.error('评估失败: ' + (e.response?.data?.detail || e.message))
    }
  }
})

watch(() => route.params.resumeId, (newId) => {
  if (newId) {
    resumeStore.getResume(newId as string).then(() => {
      reviewStore.assess(newId as string).catch(() => {})
    })
  }
})

async function handleImprove() {
  if (!reviewStore.current) return
  try {
    const result = await reviewStore.improve(reviewStore.current.id)
    improved.value = result
    // Refresh resume list so new version appears
    await resumeStore.fetchAll()
    message.success('已生成优化版本')
  } catch (e: any) {
    message.error('优化失败: ' + (e.response?.data?.detail || e.message))
  }
}

function selectResume(id: string) {
  router.push(`/review/${id}`)
}

function severityColor(s: string) {
  return s === "critical" ? "error" : s === "major" ? "warning" : "info"
}
</script>

<template>
  <div>
    <h2 class="text-2xl font-bold text-blue-600 mb-6">⭐ 质量评估</h2>

    <n-card v-if="!reviewStore.current && !resumeId" class="bg-white border border-slate-200 mb-4">
      <n-empty description="尚未选择简历进行评估">
        <template #extra>
          <n-space vertical align="center">
            <p class="text-slate-500 text-sm">选择一份已生成的简历，AI 将从多个维度评估质量并给出优化建议</p>
            <router-link to="/resume">
              <n-button type="primary" size="large">📝 前往制作简历选择</n-button>
            </router-link>
          </n-space>
        </template>
      </n-empty>
    </n-card>

    <n-spin :show="reviewStore.loading">
      <n-card v-if="reviewStore.current" class="bg-white border border-slate-200 mb-4">
        <div class="text-center mb-4">
          <div class="text-4xl font-bold" :class="
            (reviewStore.current.scores?.overall_score || 0) >= 80 ? 'text-green-600' :
            (reviewStore.current.scores?.overall_score || 0) >= 60 ? 'text-yellow-500' : 'text-red-500'
          ">
            {{ reviewStore.current.scores?.overall_score ?? '--' }}
          </div>
          <div class="text-slate-400 text-sm">综合评分</div>
        </div>
        <div v-if="reviewStore.current.scores" class="grid grid-cols-2 gap-3">
          <div v-for="(score, dim) in reviewStore.current.scores" :key="dim" class="flex items-center justify-between">
            <span class="text-slate-500 text-sm">{{ dim }}</span>
            <n-progress type="line" :percentage="score" :height="8" :border-radius="4" style="width: 120px" />
          </div>
        </div>
      </n-card>

      <n-card title="⚠️ 发现的问题" v-if="reviewStore.current?.issues" class="bg-white border border-slate-200 mb-4">
        <div v-for="(issue, idx) in reviewStore.current.issues" :key="idx" class="border-b border-slate-100 py-3 last:border-0">
          <div class="flex items-center gap-2 mb-1">
            <n-tag :type="severityColor(issue.severity)" size="tiny">{{ issue.severity === "critical" ? "严重" : issue.severity === "major" ? "重要" : "次要" }}</n-tag>
            <n-tag size="tiny">{{ issue.dimension }}</n-tag>
          </div>
          <p class="text-slate-800 text-sm">{{ issue.description }}</p>
          <p class="text-green-600 text-sm mt-1">→ {{ issue.suggestion }}</p>
        </div>
      </n-card>

      <n-card title="✅ 简历优点" v-if="reviewStore.current?.scores?.strengths" class="bg-white border border-slate-200 mb-4">
        <ul class="list-disc pl-5 text-slate-500">
          <li v-for="s in reviewStore.current.scores?.strengths" :key="s">{{ s }}</li>
        </ul>
      </n-card>

      <div v-if="reviewStore.current" class="flex justify-center gap-3">
        <n-button type="primary" size="large" :loading="reviewStore.improving" @click="handleImprove">
          ✨ 基于评估优化简历
        </n-button>
      </div>

      <n-card v-if="improved" class="bg-white border-2 border-green-400 mt-4">
        <p class="text-slate-500 text-sm mb-2">✅ 新版本已生成 (v{{ improved.version }})</p>
        <n-space>
          <router-link :to="`/resume/${resumeStore.current?.job_analysis_id}`">
            <n-button type="primary" size="small">查看优化版简历</n-button>
          </router-link>
        </n-space>
      </n-card>
    </n-spin>

    <n-card v-if="resumeStore.resumes.length > 0" title="📜 可评估的简历" class="bg-white border border-slate-200 mt-4" size="small">
      <div v-for="r in resumeStore.resumes" :key="r.id" class="flex items-center justify-between py-2 border-b border-slate-100 last:border-0">
        <div>
          <span>版本 {{ r.version }}</span>
          <span v-if="r.job_title" class="text-slate-500 text-sm ml-2">{{ r.job_title }} @ {{ r.company }}</span>
          <n-tag :type="r.status === 'reviewed' ? 'success' : 'default'" size="tiny" class="ml-2">{{ r.status === "reviewed" ? "已评估" : "草稿" }}</n-tag>
          <span class="text-slate-400 text-sm ml-2">{{ r.created_at?.slice(0, 10) }}</span>
        </div>
        <n-button size="tiny" type="primary" @click="selectResume(r.id)">开始评估</n-button>
      </div>
    </n-card>

    <n-card v-if="!reviewStore.current && !resumeId && resumeStore.resumes.length === 0" class="bg-white border border-slate-200 mt-4">
      <n-empty description="还没有简历">
        <template #extra>
          <p class="text-slate-400 text-sm">先去应聘分析页面生成第一份简历吧</p>
        </template>
      </n-empty>
    </n-card>
  </div>
</template>
