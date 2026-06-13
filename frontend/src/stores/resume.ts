import { defineStore } from 'pinia'
import { ref } from 'vue'
import { resumesApi, type ResumeVersion, type GenerateProgress } from '../api/resume'

export const useResumeStore = defineStore('resume', () => {
  const resumes = ref<ResumeVersion[]>([])
  const current = ref<ResumeVersion | null>(null)
  const loading = ref(false)
  const generating = ref(false)

  // 进度追踪
  const genProgress = ref<GenerateProgress | null>(null)
  const genId = ref<string | null>(null)
  let pollTimer: ReturnType<typeof setInterval> | null = null

  async function fetchAll() {
    loading.value = true
    try {
      const res = await resumesApi.list()
      resumes.value = res.data
    } finally {
      loading.value = false
    }
  }

  // 按岗位筛选历史版本
  async function fetchByJob(jobId: string) {
    loading.value = true
    try {
      const res = await resumesApi.list(jobId)
      resumes.value = res.data
    } finally {
      loading.value = false
    }
  }

  // 新：异步启动生成 + 轮询进度
  async function startGenerate(jobAnalysisId: string) {
    generating.value = true
    genProgress.value = { stage: 'preparing', pct: 0, message: '正在启动...', updated_at: Date.now() }
    try {
      const res = await resumesApi.generateAsync(jobAnalysisId)
      genId.value = res.data.gen_id
      // 开始轮询
      return new Promise<ResumeVersion>((resolve, reject) => {
        pollTimer = setInterval(async () => {
          try {
            const statusRes = await resumesApi.generateStatus(res.data.gen_id)
            genProgress.value = statusRes.data

            if (statusRes.data.stage === 'done' && statusRes.data.resume_id) {
              clearInterval(pollTimer!)
              pollTimer = null
              generating.value = false
              const resumeRes = await resumesApi.get(statusRes.data.resume_id)
              resumes.value.unshift(resumeRes.data)
              current.value = resumeRes.data
              resolve(resumeRes.data)
            } else if (statusRes.data.stage === 'error') {
              clearInterval(pollTimer!)
              pollTimer = null
              generating.value = false
              reject(new Error(statusRes.data.error || '生成失败'))
            }
          } catch (e) {
            // 轮询出错不停止
          }
        }, 2000)
      })
    } catch (e) {
      generating.value = false
      throw e
    }
  }

  function cancelPolling() {
    if (pollTimer) {
      clearInterval(pollTimer)
      pollTimer = null
    }
    generating.value = false
    genProgress.value = null
    genId.value = null
  }

  // 旧接口保留兼容
  async function generate(jobAnalysisId: string) {
    generating.value = true
    try {
      const res = await resumesApi.generate(jobAnalysisId)
      resumes.value.unshift(res.data)
      current.value = res.data
      return res.data
    } finally {
      generating.value = false
    }
  }

  async function getResume(id: string) {
    const res = await resumesApi.get(id)
    current.value = res.data
    return res.data
  }

  async function updateResume(id: string, data: Partial<ResumeVersion>) {
    const res = await resumesApi.update(id, data)
    current.value = res.data
    return res.data
  }

  async function deleteResume(id: string) {
    await resumesApi.delete(id)
    resumes.value = resumes.value.filter((r) => r.id !== id)
    if (current.value?.id === id) current.value = null
  }

  return {
    resumes, current, loading, generating,
    genProgress, genId,
    fetchAll, fetchByJob, generate, startGenerate, cancelPolling,
    getResume, updateResume, deleteResume
  }
})
