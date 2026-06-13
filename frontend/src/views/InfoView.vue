<script setup lang="ts">
import { onMounted, ref, h } from 'vue'
import { NButton, NInput, NSelect, NUpload, NDataTable, NModal, NPopconfirm, NTag, NSpace, NCard, NSpin, NCheckbox, useMessage } from 'naive-ui'
import type { UploadFileInfo } from 'naive-ui'
import { useInfoStore } from '../stores/info'
import { checkHasKey } from '../api/info'
import type { OptimizeResult, DuplicateResult, DuplicateGroup } from '../api/info'

const store = useInfoStore()
const message = useMessage()

const categoryOptions = [
  { label: '全部', value: '' },
  { label: '工作经历', value: 'work_experience' },
  { label: '项目经验', value: 'project' },
  { label: '教育经历', value: 'education' },
  { label: '技能', value: 'skill' },
  { label: '证书', value: 'certification' },
  { label: '个人项目', value: 'personal_project' },
]

const showModal = ref(false)
const form = ref({ title: '', category: 'work_experience', company: '', content: '' })
const editingId = ref<string | null>(null)

// Optimize state
const optimizeModal = ref(false)
const optimizing = ref(false)
const optimizeResult = ref<OptimizeResult | null>(null)
const optimizeEntryId = ref<string>('')


// Quick text state
const quickText = ref('')
const quickAnalyzing = ref(false)
const quickSaving = ref(false)
const quickPreview = ref<any>(null)

// Upload state
const uploadedFiles = ref<File[]>([])
const recognizing = ref(false)
const showApiMissing = ref(false)

// Dedup state
const dedupModal = ref(false)
const dedupLoading = ref(false)
const dedupResult = ref<DuplicateResult | null>(null)
const merging = ref(false)
const selectedGroupIdx = ref<Set<number>>(new Set())

onMounted(() => store.fetchEntries())

const columns = [
  { title: '分类', key: 'category', width: 100, render: (row: any) => { const label = categoryOptions.find(o => o.value === row.category)?.label || row.category; return h(NTag, { type: 'info', size: 'small', style: { marginRight: '8px' } }, () => label) } },
  { title: '标题', key: 'title', width: 300, ellipsis: { tooltip: true } },
  { title: '公司/机构', key: 'company', width: 130 },
  { title: '时间', key: 'date', width: 150, render: (row: any) => row.start_date ? `${row.start_date} ~ ${row.end_date || '至今'}` : '-' },
  {
    title: '操作', key: 'actions', width: 220,
    render: (row: any) => h(NSpace, () => [
      h(NButton, { size: 'tiny', type: 'info', secondary: true, onClick: () => handleOptimize(row) }, () => 'AI 调优'),
      h(NButton, { size: 'tiny', onClick: () => editEntry(row) }, () => '编辑'),
      h(NPopconfirm, { onPositiveClick: () => handleDelete(row.id) }, {
        trigger: () => h(NButton, { size: 'tiny', type: 'error' }, () => '删除'),
        default: () => '确认删除？',
      }),
    ]),
  },
]

function editEntry(row: any) {
  editingId.value = row.id
  form.value = { title: row.title, category: row.category, company: row.company || '', content: row.content || '' }
  showModal.value = true
}

async function handleSubmit() {
  if (editingId.value) {
    await store.updateEntry(editingId.value, form.value)
    message.success('已更新')
  } else {
    await store.createEntry(form.value)
    message.success('已创建')
  }
  showModal.value = false
  editingId.value = null
  form.value = { title: '', category: 'work_experience', company: '', content: '' }
}

async function handleDelete(id: string) {
  await store.deleteEntry(id)
  message.success('已删除')
}

function handleFileChange({ file }: { file: UploadFileInfo }) {
  if (file.status !== 'pending') return
  if (file.file) {
    uploadedFiles.value.push(file.file)
  }
}

async function handleRecognize() {
  if (uploadedFiles.value.length === 0) {
    message.warning('请先选择文件')
    return
  }
  // 检查是否配置了 API Key
  try {
    const res = await checkHasKey()
    if (!res.data.has_key) {
      showApiMissing.value = true
      return
    }
  } catch {
    showApiMissing.value = true
    return
  }
  // 有 API Key，开始识别
  recognizing.value = true
  try {
    for (const file of uploadedFiles.value) {
      await store.uploadFile(file)
    }
    message.success('识别完成，共处理 ' + uploadedFiles.value.length + ' 个文件')
    uploadedFiles.value = []
  } catch (e: any) {
    message.error('识别失败: ' + (e.response?.data?.detail || e.message))
  } finally {
    recognizing.value = false
  }
}

function goToSettings() {
  showApiMissing.value = false
  // 触发打开设置面板（通过事件总线或直接操作）
  window.dispatchEvent(new CustomEvent('open-settings', { detail: 'api-keys' }))
}

function handleFilter(cat: string) {
  store.fetchEntries(cat || undefined)
}

// ── AI 调优 ──
async function handleOptimize(row: any) {
  optimizeEntryId.value = row.id
  optimizeResult.value = null
  optimizing.value = true
  optimizeModal.value = true
  try {
    optimizeResult.value = await store.optimizeEntry(row.id)
  } catch (e: any) {
    message.error('AI 调优失败: ' + (e.response?.data?.detail || e.message))
    optimizeModal.value = false
  } finally {
    optimizing.value = false
  }
}

async function confirmOptimize() {
  if (!optimizeResult.value) return
  const { title, content } = optimizeResult.value.optimized
  await store.updateEntry(optimizeEntryId.value, { title, content })
  message.success('已保存优化结果')
  optimizeModal.value = false
  optimizeResult.value = null
}


// ── 文本快速录入 ──
async function handleQuickAnalyze() {
  if (!quickText.value.trim()) return
  quickAnalyzing.value = true
  quickPreview.value = null
  try {
    const res = await store.analyzeText(quickText.value)
    quickPreview.value = res
  } catch (e: any) {
    message.error('识别失败: ' + (e.response?.data?.detail || e.message))
  } finally {
    quickAnalyzing.value = false
  }
}

async function handleQuickSave() {
  if (!quickPreview.value) return
  quickSaving.value = true
  try {
    const { category, title, company, content } = quickPreview.value
    await store.createEntry({ category, title, company: company || '', content })
    message.success('已保存')
    quickText.value = ''
    quickPreview.value = null
  } catch (e: any) {
    message.error('保存失败: ' + (e.response?.data?.detail || e.message))
  } finally {
    quickSaving.value = false
  }
}

// ── 去重合并 ──
async function handleDetectDuplicates() {
  dedupLoading.value = true
  dedupResult.value = null
  selectedGroupIdx.value = new Set()
  dedupModal.value = true
  try {
    const cat = store.selectedCategory || undefined
    dedupResult.value = await store.detectDuplicates(cat)
    if (dedupResult.value.duplicate_groups === 0) {
      message.success('没有发现重复条目')
      dedupModal.value = false
    }
  } catch (e: any) {
    message.error('检测失败: ' + (e.response?.data?.detail || e.message))
    dedupModal.value = false
  } finally {
    dedupLoading.value = false
  }
}

function toggleGroup(idx: number) {
  const s = new Set(selectedGroupIdx.value)
  if (s.has(idx)) s.delete(idx)
  else s.add(idx)
  selectedGroupIdx.value = s
}

function toggleAllGroups() {
  if (!dedupResult.value) return
  if (selectedGroupIdx.value.size === dedupResult.value.groups.length) {
    selectedGroupIdx.value = new Set()
  } else {
    selectedGroupIdx.value = new Set(dedupResult.value.groups.map((_, i) => i))
  }
}

async function handleMergeGroup(group: DuplicateGroup) {
  merging.value = true
  try {
    const ids = group.entries.map(e => e.id)
    const result = await store.mergeEntries(ids, false)
    message.success(`已合并为「${result.merged.title}」，删除 ${result.deleted_count} 条`)
    // Refresh dedup results
    const cat = store.selectedCategory || undefined
    dedupResult.value = await store.detectDuplicates(cat)
    selectedGroupIdx.value = new Set()
    if (dedupResult.value.duplicate_groups === 0) {
      dedupModal.value = false
      message.success('所有重复已清理')
    }
  } catch (e: any) {
    message.error('合并失败: ' + (e.response?.data?.detail || e.message))
  } finally {
    merging.value = false
  }
}

async function handleMergeSelected() {
  if (!dedupResult.value || selectedGroupIdx.value.size === 0) return
  merging.value = true
  try {
    let totalDeleted = 0
    for (const idx of selectedGroupIdx.value) {
      const group = dedupResult.value.groups[idx]
      const ids = group.entries.map(e => e.id)
      const result = await store.mergeEntries(ids, false)
      totalDeleted += result.deleted_count
    }
    message.success(`合并完成，清理 ${totalDeleted} 条重复`)
    const cat = store.selectedCategory || undefined
    dedupResult.value = await store.detectDuplicates(cat)
    selectedGroupIdx.value = new Set()
    if (dedupResult.value.duplicate_groups === 0) {
      dedupModal.value = false
    }
  } catch (e: any) {
    message.error('合并失败: ' + (e.response?.data?.detail || e.message))
  } finally {
    merging.value = false
  }
}
</script>

<template>
  <div>
    <div class="flex items-center justify-between mb-6">
      <h2 class="text-2xl font-bold text-blue-600">📊 信息统计</h2>
      <n-space>
        <n-button type="warning" secondary @click="handleDetectDuplicates">
          🔍 检测去重
        </n-button>
        <n-button type="primary" @click="showModal = true; editingId = null; form = { title: '', category: 'work_experience', company: '', content: '' }">
          添加条目
        </n-button>
      </n-space>
    </div>

    <!-- 上传区 -->
    <n-card class="bg-white border border-slate-200 mb-6">
      <div class="flex items-center gap-4">
        <n-upload
          multiple
          :max="5"
          accept=".pdf,.docx,.xlsx,.txt,.md"
          :on-change="handleFileChange"
          :show-file-list="true"
          :default-upload="false"
        >
          <n-button type="default" class="upload-btn">📎 选择文件</n-button>
        </n-upload>
        <n-button
          type="primary"
          :disabled="uploadedFiles.length === 0 || recognizing"
          :loading="recognizing"
          @click="handleRecognize"
        >
          🤖 识别内容
        </n-button>
        <span class="text-xs text-slate-400">PDF / Word / Excel</span>
      </div>

      <!-- API Key 缺失弹窗 -->
      <n-modal v-model:show="showApiMissing" preset="dialog" title="未配置模型" positive-text="去设置" negative-text="取消" @positive-click="goToSettings">
        <p>您还没有添加 API Key，无法使用 AI 识别功能。</p>
        <p>请先在设置中添加 API Key。</p>
      </n-modal>

      <!-- 文本快速录入 -->
      <div class="mt-4 pt-4 border-t border-slate-100">
        <div class="flex items-center gap-2 mb-3">
          <span class="text-sm font-semibold text-slate-600">📝 文本快速录入</span>
          <span class="text-xs text-slate-400">粘贴一段经历，AI 自动识别分类并预览</span>
        </div>
        <n-input
          v-model:value="quickText"
          type="textarea"
          :rows="3"
          placeholder="例如：2024年负责某市政务云项目，完成VMware到国产化平台的迁移，涉及200+虚拟机，中标金额700万..."
          class="mb-3"
        />
        <div class="flex gap-2">
          <n-button
            type="primary" size="small"
            :disabled="!quickText.trim() || quickAnalyzing"
            :loading="quickAnalyzing"
            @click="handleQuickAnalyze"
          >
            🤖 AI 识别
          </n-button>
          <n-button v-if="quickPreview" size="small" secondary @click="quickText = ''; quickPreview = null">
            清空
          </n-button>
        </div>

        <!-- 识别预览 -->
        <div v-if="quickPreview" class="mt-4 p-4 bg-blue-50 border border-blue-200 rounded-lg">
          <div class="text-sm font-semibold text-blue-700 mb-3">📋 AI 识别结果预览</div>
          <div class="space-y-2 text-sm">
            <div class="flex gap-2">
              <span class="text-slate-500 w-16 shrink-0">分类：</span>
              <n-select
                v-model:value="quickPreview.category"
                :options="categoryOptions.filter(o => o.value !== '').map(o => ({label: o.label, value: o.value}))"
                size="tiny"
                style="width: 180px"
              />
            </div>
            <div class="flex gap-2">
              <span class="text-slate-500 w-16 shrink-0">标题：</span>
              <n-input v-model:value="quickPreview.title" size="tiny" style="flex:1" />
            </div>
            <div class="flex gap-2">
              <span class="text-slate-500 w-16 shrink-0">公司：</span>
              <n-input v-model:value="quickPreview.company" size="tiny" style="flex:1" placeholder="可选" />
            </div>
            <div class="flex gap-2">
              <span class="text-slate-500 w-16 shrink-0">内容：</span>
              <div class="text-slate-700 flex-1 whitespace-pre-wrap">{{ quickPreview.content }}</div>
            </div>
          </div>
          <div class="mt-3 flex gap-2">
            <n-button size="small" type="primary" :disabled="quickSaving" :loading="quickSaving" @click="handleQuickSave">
              ✅ 确认保存
            </n-button>
            <n-button size="small" @click="quickPreview = null; quickText = ''">取消</n-button>
          </div>
        </div>
      </div>
    </n-card>

    <!-- 分类筛选 -->
    <div class="flex flex-wrap gap-2 mb-6">
      <n-tag
        v-for="opt in categoryOptions.filter(o => o.value !== '')"
        :key="opt.value"
        :type="store.selectedCategory === opt.value ? 'primary' : 'default'"
        size="large"
        class="cursor-pointer hover:scale-105 transition-transform"
        @click="handleFilter(opt.value)"
      >
        {{ opt.label }}
      </n-tag>
    </div>

    <!-- 数据表格 -->
    <n-dataTable
      :columns="columns"
      :data="store.entries"
      :loading="store.loading"
      :bordered="false"
      class="bg-white border border-slate-200 rounded-lg"
      size="small"
    />

    <!-- 添加/编辑弹窗 -->
    <n-modal v-model:show="showModal" preset="card" title="信息条目" style="width: 600px">
      <n-space vertical>
        <n-select v-model:value="form.category" :options="categoryOptions.filter(o => o.value)" placeholder="分类" />
        <n-input v-model:value="form.title" placeholder="标题（如：XX公司系统管理员）" />
        <n-input v-model:value="form.company" placeholder="公司/机构名称" />
        <n-input
          v-model:value="form.content"
          type="textarea"
          :rows="6"
          placeholder="详细内容描述，尽量包含量化数据..."
        />
      </n-space>
      <template #footer>
        <n-button @click="showModal = false">取消</n-button>
        <n-button type="primary" @click="handleSubmit">保存</n-button>
      


</template>
    </n-modal>

    <!-- AI 调优预览弹窗 -->
    <n-modal v-model:show="optimizeModal" preset="card" title="🤖 AI 调优预览" style="width: 720px" :mask-closable="false">
      <n-spin :show="optimizing" description="AI 正在优化...">
        <div v-if="optimizeResult" class="space-y-4">
          <div v-if="optimizeResult.optimized.improvements?.length" class="bg-blue-50 border border-blue-200 rounded-lg p-3">
            <div class="text-sm font-semibold text-blue-700 mb-2">📝 改进点</div>
            <ul class="text-sm text-blue-600 space-y-1">
              <li v-for="(imp, i) in optimizeResult.optimized.improvements" :key="i">• {{ imp }}</li>
            </ul>
          </div>
          <div class="grid grid-cols-2 gap-4">
            <div class="border border-gray-200 rounded-lg p-3">
              <div class="text-xs text-slate-500 mb-1">原标题</div>
              <div class="text-sm text-slate-600">{{ optimizeResult.original.title }}</div>
            </div>
            <div class="border border-green-300 bg-green-50 rounded-lg p-3">
              <div class="text-xs text-green-600 mb-1">优化标题</div>
              <div class="text-sm font-semibold text-green-800">{{ optimizeResult.optimized.title }}</div>
            </div>
          </div>
          <div class="grid grid-cols-2 gap-4">
            <div class="border border-gray-200 rounded-lg p-3">
              <div class="text-xs text-slate-500 mb-1">原内容</div>
              <div class="text-sm text-slate-600 whitespace-pre-wrap">{{ optimizeResult.original.content || '(空)' }}</div>
            </div>
            <div class="border border-green-300 bg-green-50 rounded-lg p-3">
              <div class="text-xs text-green-600 mb-1">优化内容</div>
              <div class="text-sm text-slate-800 whitespace-pre-wrap">{{ optimizeResult.optimized.content }}</div>
            </div>
          </div>
        </div>
      </n-spin>
      <template #footer>
        <n-button @click="optimizeModal = false" :disabled="optimizing">取消</n-button>
        <n-button type="primary" @click="confirmOptimize" :disabled="optimizing || !optimizeResult">确认保存</n-button>
      


</template>
    </n-modal>

    <!-- 去重检测结果弹窗 -->
    <n-modal v-model:show="dedupModal" preset="card" title="🔍 重复检测结果" style="width: 800px; max-height: 80vh" :mask-closable="false">
      <n-spin :show="dedupLoading" description="正在扫描重复...">
        <div v-if="dedupResult && dedupResult.duplicate_groups > 0">
          <div class="flex items-center justify-between mb-4">
            <div class="text-sm text-slate-500">
              共 {{ dedupResult.total_entries }} 条，发现 <span class="text-orange-600 font-bold">{{ dedupResult.duplicate_groups }}</span> 组疑似重复
            </div>
            <n-space>
              <n-button size="small" @click="toggleAllGroups">
                {{ selectedGroupIdx.size === dedupResult.groups.length ? '取消全选' : '全选' }}
              </n-button>
              <n-button size="small" type="primary" :disabled="selectedGroupIdx.size === 0 || merging" @click="handleMergeSelected">
                批量合并 ({{ selectedGroupIdx.size }})
              </n-button>
            </n-space>
          </div>

          <div class="space-y-3 max-h-[55vh] overflow-y-auto">
            <div
              v-for="(group, gi) in dedupResult.groups"
              :key="gi"
              class="border rounded-lg p-3"
              :class="selectedGroupIdx.has(gi) ? 'border-orange-300 bg-orange-50' : 'border-gray-200'"
            >
              <div class="flex items-start gap-3">
                <n-checkbox :checked="selectedGroupIdx.has(gi)" @update:checked="toggleGroup(gi)" class="mt-1" />
                <div class="flex-1 min-w-0">
                  <div class="flex items-center gap-2 mb-2">
                    <n-tag size="tiny" type="warning">{{ group.entries.length }} 条重复</n-tag>
                    <span class="text-sm font-semibold text-slate-700 truncate">{{ group.entries[0].title }}</span>
                    <span v-if="group.entries[0].company" class="text-xs text-slate-500">@{{ group.entries[0].company }}</span>
                  </div>
                  <div class="space-y-1">
                    <div
                      v-for="(entry, ei) in group.entries"
                      :key="ei"
                      class="text-xs text-slate-500 pl-2 border-l-2 border-gray-200"
                    >
                      <span class="text-slate-700">{{ entry.title }}</span>
                      <span v-if="entry.company" class="text-slate-500 ml-1">@{{ entry.company }}</span>
                      <span v-if="entry._reason" class="text-orange-500 ml-2">— {{ entry._reason }}</span>
                    </div>
                  </div>
                  <div class="mt-2">
                    <n-button size="tiny" type="warning" secondary :disabled="merging" @click="handleMergeGroup(group)">
                      ⚡ 合并此组
                    </n-button>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </n-spin>
      <template #footer>
        <n-button @click="dedupModal = false" :disabled="merging">关闭</n-button>
      


</template>
    </n-modal>
  </div>



</template>