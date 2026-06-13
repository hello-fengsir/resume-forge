import api from './client'

export interface InfoEntry {
  id: string
  category: string
  title: string
  company?: string
  start_date?: string
  end_date?: string
  content?: string
  raw_input?: string
  source_file?: string
  created_at: string
}

export interface OptimizeResult {
  entry_id: string
  original: { title: string; content?: string }
  optimized: { title: string; content: string; improvements: string[] }
}

export interface DuplicateGroupEntry {
  id: string
  category: string
  title: string
  company?: string
  content: string
  _reason?: string
  _title_sim?: number
  _content_sim?: number
}

export interface DuplicateGroup {
  entries: DuplicateGroupEntry[]
  total: number
}

export interface DuplicateResult {
  total_entries: number
  duplicate_groups: number
  groups: DuplicateGroup[]
}

export interface TextAnalysisResult {
  category: string
  title: string
  company?: string
  content: string
  raw_text: string
}
export interface MergeResult {
  merged: { id: string; title: string; content: string; category: string }
  deleted: string[]
  deleted_count: number
}

export const infoApi = {
  list: (category?: string) => api.get<InfoEntry[]>('/info/entries', { params: { category } }),
  get: (id: string) => api.get<InfoEntry>(`/info/entries/${id}`),
  create: (data: Partial<InfoEntry>) => api.post<InfoEntry>('/info/entries', data),
  update: (id: string, data: Partial<InfoEntry>) => api.put<InfoEntry>(`/info/entries/${id}`, data),
  delete: (id: string) => api.delete(`/info/entries/${id}`),
  upload: (formData: FormData) => api.post<InfoEntry>('/info/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 180000,
  }),
  optimize: (id: string) => api.post<OptimizeResult>(`/info/entries/${id}/optimize`, {}, { timeout: 60000 }),
  detectDuplicates: (category?: string) => api.post<DuplicateResult>('/info/detect-duplicates', { category }, { timeout: 30000 }),
  merge: (entryIds: string[], useAi = false) => api.post<MergeResult>('/info/merge', { entry_ids: entryIds, use_ai: useAi }, { timeout: 120000 }),
  analyzeText: (text: string) => api.post<TextAnalysisResult>('/info/analyze-text', { text }, { timeout: 30000 }),
}

// 检查用户是否配置了 API Key
export const checkHasKey = () => api.get<{ has_key: boolean }>('/config/has-key')
