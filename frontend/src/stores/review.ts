import { defineStore } from 'pinia'
import { ref } from 'vue'
import { reviewsApi, type QualityReview } from '../api/review'

export const useReviewStore = defineStore('review', () => {
  const current = ref<QualityReview | null>(null)
  const loading = ref(false)
  const improving = ref(false)

  async function assess(resumeId: string) {
    loading.value = true
    try {
      const res = await reviewsApi.assess(resumeId)
      current.value = res.data
      return res.data
    } finally {
      loading.value = false
    }
  }

  async function getReview(id: string) {
    const res = await reviewsApi.get(id)
    current.value = res.data
    return res.data
  }

  async function improve(reviewId: string) {
    improving.value = true
    try {
      const res = await reviewsApi.improve(reviewId)
      return res.data
    } finally {
      improving.value = false
    }
  }

  return { current, loading, improving, assess, getReview, improve }
})
