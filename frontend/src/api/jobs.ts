import api from './client'

export interface JobAnalysis {
  id: string
  title: string
  company?: string
  raw_requirement: string
  source_url?: string
  structured_req?: any
  match_result?: any
  resume_focus?: any
  enterprise_info?: any
  recommendation?: string
  advice?: string
  status?: string
  cached?: boolean
  created_at: string
}

export interface AnalysisStatus {
  stage: string
  message: string
  pct: number
  updated_at: string
}

export const jobsApi = {
  analyze: (data: { requirement: string; source_url?: string }) =>
    api.post<JobAnalysis>('/jobs/analyze', data, { timeout: 180000 }),
  analyzeScreenshot: (image: string) =>
    api.post<{ job_id: string; status: string }>('/jobs/analyze-screenshot', { image }),
  getStatus: (jobId: string) =>
    api.get<AnalysisStatus>(`/jobs/${jobId}/status`),
  list: () => api.get<JobAnalysis[]>('/jobs/'),
  get: (id: string) => api.get<JobAnalysis>(`/jobs/${id}/`),
  delete: (id: string) => api.delete(`/jobs/${id}`),
  update: (id: string, data: Partial<JobAnalysis>) =>
    api.put<JobAnalysis>(`/jobs/${id}`, data),
  research: (id: string) => api.post<JobAnalysis>(`/jobs/${id}/research`),
}
