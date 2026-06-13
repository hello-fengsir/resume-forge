import api from './client'

export interface QualityReview {
  id: string
  resume_id: string
  scores?: any
  issues?: any[]
  suggestions?: any[]
  improved_resume?: string
  created_at: string
}

export const reviewsApi = {
  assess: (resumeId: string) =>
    api.post<QualityReview>('/reviews/assess', { resume_id: resumeId }, { timeout: 180000 }),
  get: (id: string) => api.get<QualityReview>(`/reviews/${id}`),
  improve: (reviewId: string) =>
    api.post<any>(`/reviews/${reviewId}/improve`, {}, { timeout: 300000 }),
}
