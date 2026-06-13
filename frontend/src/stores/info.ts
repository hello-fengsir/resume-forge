import { defineStore } from 'pinia'
import { ref } from 'vue'
import { infoApi, type InfoEntry, type OptimizeResult, type DuplicateResult, type MergeResult } from '../api/info'

export const useInfoStore = defineStore('info', () => {
  const entries = ref<InfoEntry[]>([])
  const loading = ref(false)
  const selectedCategory = ref<string>()

  async function fetchEntries(category?: string) {
    loading.value = true
    try {
      const res = await infoApi.list(category)
      entries.value = res.data
      selectedCategory.value = category
    } finally {
      loading.value = false
    }
  }

  async function createEntry(data: Partial<InfoEntry>) {
    const res = await infoApi.create(data)
    entries.value.unshift(res.data)
    return res.data
  }

  async function updateEntry(id: string, data: Partial<InfoEntry>) {
    const res = await infoApi.update(id, data)
    const idx = entries.value.findIndex((e) => e.id === id)
    if (idx >= 0) entries.value[idx] = res.data
    return res.data
  }

  async function deleteEntry(id: string) {
    await infoApi.delete(id)
    entries.value = entries.value.filter((e) => e.id !== id)
  }

  async function uploadFile(file: File) {
    const formData = new FormData()
    formData.append('file', file)
    const res = await infoApi.upload(formData)
    entries.value.unshift(res.data)
    return res.data
  }

  async function optimizeEntry(id: string): Promise<OptimizeResult> {
    const res = await infoApi.optimize(id)
    return res.data
  }

  async function detectDuplicates(category?: string): Promise<DuplicateResult> {
    const res = await infoApi.detectDuplicates(category)
    return res.data
  }

  async function analyzeText(text: string) {
    const res = await infoApi.analyzeText(text)
    return res.data
  }

  async function mergeEntries(entryIds: string[], useAi = false): Promise<MergeResult> {
    const res = await infoApi.merge(entryIds, useAi)
    // Remove deleted entries from local state
    if (res.data.deleted) {
      entries.value = entries.value.filter((e) => !res.data.deleted.includes(e.id))
    }
    // Refresh to get merged entry
    await fetchEntries(selectedCategory.value)
    return res.data
  }

  return { entries, loading, selectedCategory, fetchEntries, createEntry, updateEntry, deleteEntry, uploadFile, optimizeEntry, detectDuplicates, mergeEntries, analyzeText }
})
