<script setup lang="ts">
import { NCard, NButton } from 'naive-ui'
import { useRouter } from 'vue-router'

const router = useRouter()

const modules = [
  {
    title: '📊 信息统计',
    desc: '录入工作经历、项目经验、技能证书，支持附件上传 AI 自动提取',
    route: '/info',
    color: 'border-blue-500',
  },
  {
    title: '🎯 应聘分析',
    desc: '粘贴招聘要求，AI 分析匹配度，给出简历策略和重点',
    route: '/jobs',
    color: 'border-green-500',
  },
  {
    title: '📝 制作简历',
    desc: '四维度独立生成：核心优势、工作经历、项目经验、教育经历',
    route: '/resume',
    color: 'border-purple-500',
  },
  {
    title: '🔍 质量评估',
    desc: 'AI 以极度严格标准评审简历，找出问题并自动优化',
    route: '/review',
    color: 'border-orange-500',
  },
]
</script>

<template>
  <div>
    <div class="text-center mb-10">
      <h1 class="text-4xl font-bold text-blue-600 mb-3">🔥 Resume Forge</h1>
      <p class="text-slate-500 text-lg">简历熔炉 — 将原始素材熔炼成定制简历</p>
    </div>

    <div class="grid grid-cols-1 md:grid-cols-2 gap-6 max-w-4xl mx-auto">
      <n-card
        v-for="m in modules" :key="m.route"
        :class="`bg-white border border-slate-200 cursor-pointer hover:bg-surface-hover transition-all border-l-4 ${m.color}`"
        @click="router.push(m.route)"
      >
        <h3 class="text-xl font-bold text-slate-800 mb-2">{{ m.title }}</h3>
        <p class="text-slate-500">{{ m.desc }}</p>
      </n-card>
    </div>

    <div class="text-center mt-10 text-text-muted text-sm">
      <p>技术栈：Vue 3 + NaiveUI + FastAPI + PostgreSQL + DeepSeek AI</p>
      <p class="mt-1">每个模块独立运作，AI 驱动全流程</p>
    </div>
  </div>
</template>