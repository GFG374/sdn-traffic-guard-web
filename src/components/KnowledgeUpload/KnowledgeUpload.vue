<template>
  <div class="min-h-screen bg-gradient-to-br from-blue-50 via-indigo-50 to-purple-50 p-6">
    <div class="max-w-6xl mx-auto space-y-6">
      <div class="flex items-center justify-between">
        <div>
          <p class="text-sm text-indigo-600 font-semibold">知识库</p>
          <h2 class="text-3xl font-bold text-gray-900 mt-1">文档管理与上传</h2>
          <p class="text-gray-600 mt-1">上传、预览并维护你的知识库文件，让 AI 更懂你的网络环境</p>
        </div>
        <div class="flex items-center space-x-3 bg-white/70 backdrop-blur rounded-full px-4 py-2 shadow">
          <span class="h-10 w-10 rounded-full bg-gradient-to-r from-purple-500 to-indigo-500 text-white flex items-center justify-center">
            <i class="fas fa-cloud-upload-alt"></i>
          </span>
          <div>
            <p class="text-xs text-gray-500">当前状态</p>
            <p class="text-sm font-semibold text-green-600">就绪</p>
          </div>
        </div>
      </div>

      <div class="grid lg:grid-cols-2 gap-6">
        <!-- 上传卡片 -->
        <div class="bg-white/80 backdrop-blur rounded-2xl shadow-xl p-6 space-y-4 border border-gray-100">
          <div class="flex items-center justify-between">
            <div>
              <h3 class="text-xl font-semibold text-gray-900">上传新文档</h3>
              <p class="text-sm text-gray-600">支持 TXT / PDF / CSV / DOCX，单文件不超过 10MB</p>
            </div>
            <button
              class="px-4 py-2 bg-gradient-to-r from-indigo-600 to-purple-600 text-white rounded-lg shadow hover:shadow-lg transition"
              @click="openFileSelector"
            >
              选择文件
            </button>
          </div>

          <div
            class="border-2 border-dashed border-indigo-200 rounded-xl p-6 bg-gradient-to-br from-indigo-50/60 to-purple-50/60 text-center transition hover:border-indigo-400"
            @dragover.prevent
            @drop.prevent="handleDrop"
          >
            <input
              ref="fileInput"
              type="file"
              multiple
              accept=".txt,.pdf,.csv,.docx"
              @change="handleFileSelect"
              class="hidden"
            />

            <div class="mx-auto h-14 w-14 rounded-full bg-gradient-to-r from-indigo-500 to-purple-600 flex items-center justify-center text-white text-2xl mb-3">
              <i class="fas fa-file-upload"></i>
            </div>
            <p class="text-lg font-semibold text-gray-900">拖拽文件到此处或点击按钮</p>
            <p class="text-sm text-gray-500 mt-1">批量上传将自动顺序写入知识库</p>
          </div>

          <div v-if="uploading" class="bg-indigo-50 rounded-xl p-4 border border-indigo-100">
            <div class="flex items-center justify-between text-sm text-indigo-700 mb-2">
              <span>上传中...</span>
              <span>{{ uploadProgress }}%</span>
            </div>
            <div class="h-2 bg-indigo-100 rounded-full overflow-hidden">
              <div class="h-full bg-gradient-to-r from-indigo-500 to-purple-500" :style="{ width: uploadProgress + '%' }"></div>
            </div>
          </div>

          <div v-if="uploadMessage" :class="[
            'rounded-xl p-4 text-sm border',
            uploadSuccess ? 'bg-green-50 border-green-200 text-green-700' : 'bg-red-50 border-red-200 text-red-700'
          ]">
            {{ uploadMessage }}
          </div>
        </div>

        <!-- 文档列表 -->
        <div class="bg-white/80 backdrop-blur rounded-2xl shadow-xl p-6 border border-gray-100">
          <div class="flex items-center justify-between mb-4">
            <div>
              <h3 class="text-xl font-semibold text-gray-900">已上传的文档</h3>
              <p class="text-sm text-gray-600">快速浏览并管理最新的知识文件</p>
            </div>
            <span class="px-3 py-1 rounded-full bg-indigo-50 text-indigo-700 text-sm font-medium">
              共 {{ documents.length }} 个
            </span>
          </div>

          <div v-if="loading" class="flex items-center justify-center h-40 text-gray-500">
            正在加载文档...
          </div>

          <div v-else-if="documents.length === 0" class="flex items-center justify-center h-40 text-gray-500 space-y-2 flex-col">
            <i class="fas fa-folder-open text-3xl text-indigo-400"></i>
            <p>暂无文档，先上传一个吧</p>
          </div>

          <div v-else class="space-y-3 max-h-[480px] overflow-y-auto pr-1">
            <div
              v-for="doc in documents"
              :key="doc.name"
              class="flex items-center justify-between p-4 rounded-xl border border-gray-100 hover:border-indigo-200 hover:shadow transition bg-white/70"
            >
              <div class="flex items-center space-x-3">
                <div class="h-11 w-11 rounded-xl bg-gradient-to-br from-indigo-500 to-purple-600 text-white flex items-center justify-center text-lg font-semibold">
                  {{ doc.name.charAt(0).toUpperCase() }}
                </div>
                <div>
                  <p class="font-semibold text-gray-900">{{ doc.name }}</p>
                  <p class="text-xs text-gray-500">{{ formatFileSize(doc.size) }} · {{ formatDate(doc.modified) }}</p>
                </div>
              </div>

              <button
                class="px-3 py-2 rounded-lg text-sm font-medium bg-red-50 text-red-600 hover:bg-red-100 transition disabled:opacity-60"
                @click="deleteDocument(doc.name)"
                :disabled="deleting === doc.name"
              >
                {{ deleting === doc.name ? '删除中...' : '删除' }}
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import axios from 'axios'

interface Document {
  name: string
  path: string
  size: number
  modified: string
}

const fileInput = ref<HTMLInputElement | null>(null)
const documents = ref<Document[]>([])
const loading = ref(false)
const uploading = ref(false)
const uploadProgress = ref(0)
const uploadMessage = ref('')
const uploadSuccess = ref(false)
const deleting = ref('')

// 加载文档列表
const loadDocuments = async () => {
  loading.value = true
  try {
    const response = await axios.get('/v1/knowledge/documents')
    if (response.data.success) {
      documents.value = response.data.documents
      console.log('[✅] 文档列表加载成功:', documents.value.length, '个文档')
    }
  } catch (error) {
    console.error('[❌] 加载文档列表失败:', error)
  } finally {
    loading.value = false
  }
}

// 处理文件选择
const handleFileSelect = async (event: Event) => {
  const input = event.target as HTMLInputElement
  if (input.files) {
    await uploadFiles(Array.from(input.files))
    input.value = '' // 重置input
  }
}

// 打开文件选择器
const openFileSelector = () => {
  fileInput.value?.click()
}

// 处理拖拽
const handleDrop = async (event: DragEvent) => {
  if (event.dataTransfer?.files) {
    await uploadFiles(Array.from(event.dataTransfer.files))
  }
}

// 上传文件
const uploadFiles = async (files: File[]) => {
  if (files.length === 0) return

  uploading.value = true
  uploadProgress.value = 0
  uploadMessage.value = ''

  try {
    for (let i = 0; i < files.length; i++) {
      const file = files[i]

      // 验证文件类型
      const allowedExtensions = ['.txt', '.pdf', '.csv', '.docx']
      const fileExt = file.name.substring(file.name.lastIndexOf('.')).toLowerCase()

      if (!allowedExtensions.includes(fileExt)) {
        uploadMessage.value = `❌ 不支持的文件格式: ${fileExt}`
        uploadSuccess.value = false
        continue
      }

      // 验证文件大小
      if (file.size > 10 * 1024 * 1024) {
        uploadMessage.value = `❌ 文件过大: ${file.name} (最大10MB)`
        uploadSuccess.value = false
        continue
      }

      // 上传文件
      const formData = new FormData()
      formData.append('file', file)

      try {
        console.log(`[📤] 开始上传文件: ${file.name}`)
        const response = await axios.post('/v1/knowledge/upload', formData, {
          headers: {
            'Content-Type': 'multipart/form-data'
          }
        })

        if (response.data.success) {
          uploadMessage.value = `✅ 文件上传成功: ${file.name} (${response.data.chunks_count} 个块)`
          uploadSuccess.value = true
          console.log('[✅] 文件上传成功:', response.data)
        } else {
          uploadMessage.value = `❌ 上传失败: ${response.data.message}`
          uploadSuccess.value = false
        }
      } catch (error: any) {
        uploadMessage.value = `❌ 上传失败: ${error.response?.data?.detail || error.message}`
        uploadSuccess.value = false
        console.error('[❌] 上传失败:', error)
      }

      // 更新进度
      uploadProgress.value = Math.round(((i + 1) / files.length) * 100)
    }

    // 重新加载文档列表
    await loadDocuments()

  } finally {
    uploading.value = false
  }
}

// 删除文档
const deleteDocument = async (filename: string) => {
  if (!confirm(`确定要删除文档 "${filename}" 吗？`)) {
    return
  }

  deleting.value = filename
  try {
    console.log(`[🗑️] 删除文档: ${filename}`)
    const response = await axios.delete(`/v1/knowledge/documents/${filename}`)

    if (response.data.success) {
      uploadMessage.value = `✅ 文档已删除: ${filename}`
      uploadSuccess.value = true
      console.log('[✅] 文档删除成功')

      // 重新加载文档列表
      await loadDocuments()
    } else {
      uploadMessage.value = `❌ 删除失败: ${response.data.message}`
      uploadSuccess.value = false
    }
  } catch (error: any) {
    uploadMessage.value = `❌ 删除失败: ${error.response?.data?.detail || error.message}`
    uploadSuccess.value = false
    console.error('[❌] 删除失败:', error)
  } finally {
    deleting.value = ''
  }
}

// 格式化文件大小
const formatFileSize = (bytes: number): string => {
  if (bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return Math.round((bytes / Math.pow(k, i)) * 100) / 100 + ' ' + sizes[i]
}

// 格式化日期
const formatDate = (dateString: string): string => {
  const date = new Date(dateString)
  return date.toLocaleString('zh-CN')
}

// 页面加载时获取文档列表
onMounted(() => {
  loadDocuments()
})
</script>
