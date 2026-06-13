import api from './client'

export interface ResumeVersion {
  id: string
  job_analysis_id?: string
  job_title?: string
  company?: string
  version: number
  core_strengths?: string
  work_experience?: string
  project_exp?: string
  education?: string
  full_resume?: string
  status: string
  created_at: string
}

export interface GenerateProgress {
  stage: string
  pct: number
  message: string
  resume_id?: string
  error?: string
  updated_at: number
}

export const resumesApi = {
  // 旧接口保留兼容
  generate: (jobAnalysisId: string) =>
    api.post<ResumeVersion>('/resumes/generate', { job_analysis_id: jobAnalysisId }, { timeout: 300000 }),

  // 新接口：异步启动生成
  generateAsync: (jobAnalysisId: string) =>
    api.post<{ gen_id: string; status: string }>('/resumes/generate-async', { job_analysis_id: jobAnalysisId }),

  // 查询生成进度
  generateStatus: (genId: string) =>
    api.get<GenerateProgress>(`/resumes/generate-status/${genId}`),

  list: (jobId?: string) => {
    const params = jobId ? { job_id: jobId } : {}
    return api.get<ResumeVersion[]>('/resumes/', { params })
  },
  get: (id: string) => api.get<ResumeVersion>(`/resumes/${id}`),
  update: (id: string, data: Partial<ResumeVersion>) => api.put<ResumeVersion>(`/resumes/${id}`, data),
  delete: (id: string) => api.delete(`/resumes/${id}`),
  exportDoc: (id: string) => api.get(`/resumes/${id}/export`, { responseType: 'blob' }),
}
