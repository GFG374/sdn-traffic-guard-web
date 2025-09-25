<template>
  <div class="min-h-screen bg-gradient-to-br from-blue-50 via-indigo-50 to-purple-50 p-4">
    <div class="max-w-4xl mx-auto">
      <!-- 标题 -->
      <div class="text-center mb-8">
        <div class="inline-flex items-center justify-center w-16 h-16 bg-gradient-to-r from-indigo-500 to-purple-600 rounded-full mb-4">
          <i class="fas fa-user-cog text-white text-2xl"></i>
        </div>
        <h2 class="text-4xl font-bold bg-gradient-to-r from-indigo-600 to-purple-600 bg-clip-text text-transparent mb-2">
          账号详情
        </h2>
        <p class="text-gray-600">管理您的账号信息和设置</p>
      </div>

      <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <!-- 个人信息卡片 -->
        <div class="lg:col-span-2">
          <div class="bg-white/80 backdrop-blur-sm rounded-2xl shadow-xl p-6">
            <h3 class="text-xl font-semibold text-gray-900 mb-6 flex items-center">
              <i class="fas fa-user-circle mr-2 text-indigo-600"></i>
              个人信息
            </h3>
            
            <div class="space-y-6">
              <!-- 用户名 -->
              <div>
                <label class="block text-sm font-medium text-gray-700 mb-2">用户名</label>
                <input 
                  v-model="userInfo.username" 
                  type="text" 
                  class="w-full px-4 py-3 rounded-lg border border-gray-300 bg-gray-50 cursor-not-allowed"
                  readonly
                />
                <p class="text-xs text-gray-500 mt-1">用户名不可修改</p>
              </div>

              <!-- 邮箱 -->
              <div>
                <label class="block text-sm font-medium text-gray-700 mb-2">邮箱地址</label>
                <input 
                  v-model="userInfo.email" 
                  type="email" 
                  class="w-full px-4 py-3 rounded-lg border border-gray-300 focus:outline-none focus:ring-2 focus:ring-blue-500/30 focus:border-blue-500 transition-colors"
                  :readonly="!editingEmail"
                  :class="{ 'bg-gray-50 cursor-not-allowed': !editingEmail, 'bg-white': editingEmail }"
                />
                <div class="flex justify-between items-center mt-2">
                  <p class="text-xs text-gray-500">用于接收通知和密码重置</p>
                  <button 
                    @click="toggleEditEmail"
                    class="text-sm text-blue-600 hover:text-blue-800 transition-colors"
                  >
                    {{ editingEmail ? '取消' : '编辑' }}
                  </button>
                </div>
              </div>

              <!-- 角色 -->
              <div>
                <label class="block text-sm font-medium text-gray-700 mb-2">账号类型</label>
                <div class="px-4 py-3 rounded-lg border border-gray-300 bg-gray-50">
                  <span class="inline-flex items-center px-3 py-1 rounded-full text-sm font-medium"
                        :class="userInfo.role === 'admin' ? 'bg-red-100 text-red-800' : 'bg-blue-100 text-blue-800'">
                    {{ userInfo.role === 'admin' ? '管理员' : '普通用户' }}
                  </span>
                </div>
              </div>

              <!-- 注册时间 -->
              <div>
                <label class="block text-sm font-medium text-gray-700 mb-2">注册时间</label>
                <input 
                  :value="formatDate(userInfo.createdAt)" 
                  type="text" 
                  class="w-full px-4 py-3 rounded-lg border border-gray-300 bg-gray-50 cursor-not-allowed"
                  readonly
                />
              </div>

              <!-- 保存按钮 -->
              <div v-if="editingEmail" class="flex space-x-3">
                <button 
                  @click="saveEmail"
                  :disabled="loading"
                  class="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 transition-colors"
                >
                  保存邮箱
                </button>
                <button 
                  @click="cancelEditEmail"
                  class="px-6 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition-colors"
                >
                  取消
                </button>
              </div>
            </div>
          </div>

          <!-- 安全设置 -->
          <div class="bg-white/80 backdrop-blur-sm rounded-2xl shadow-xl p-6 mt-6">
            <h3 class="text-xl font-semibold text-gray-900 mb-6 flex items-center">
              <i class="fas fa-shield-alt mr-2 text-green-600"></i>
              安全设置
            </h3>
            
            <div class="space-y-4">
              <div class="flex items-center justify-between p-4 border border-gray-200 rounded-lg">
                <div>
                  <h4 class="font-medium text-gray-900">修改密码</h4>
                  <p class="text-sm text-gray-600">定期更新密码可以提高账号安全性</p>
                </div>
                <button 
                @click="navigateTo('/change-password')"
                class="px-4 py-2 bg-blue-600 text-white text-sm rounded-lg hover:bg-blue-700 transition-colors"
              >
                修改
              </button>
              </div>

              <div class="flex items-center justify-between p-4 border border-gray-200 rounded-lg">
                <div>
                  <h4 class="font-medium text-gray-900">登录历史</h4>
                  <p class="text-sm text-gray-600">查看最近的登录活动</p>
                </div>
                <button 
                  class="px-4 py-2 bg-gray-600 text-white text-sm rounded-lg hover:bg-gray-700 transition-colors"
                >
                  查看
                </button>
              </div>
            </div>
          </div>
        </div>

        <!-- 头像和快捷操作 -->
        <div class="lg:col-span-1">
          <!-- 头像卡片 -->
      <div class="bg-white/80 backdrop-blur-sm rounded-2xl shadow-xl p-6 mb-6">
        <h3 class="text-lg font-semibold text-gray-900 mb-4">头像</h3>
        <div class="text-center">
          <div v-if="!userInfo.avatar || userInfo.avatar.startsWith('bg-')" 
            :class="[
              'w-32 h-32 rounded-full mx-auto mb-4 flex items-center justify-center text-white font-bold text-4xl',
              userInfo.avatar || 'bg-gradient-to-r from-indigo-500 to-purple-600'
            ]"
          >
            {{ userInfo.username?.charAt(0).toUpperCase() || 'U' }}
          </div>
          <img v-else 
            :src="userInfo.avatar.startsWith('http') || userInfo.avatar.startsWith('data:') ? userInfo.avatar : 'http://localhost:8001' + userInfo.avatar" 
            alt="用户头像" 
            class="w-32 h-32 rounded-full mx-auto mb-4 object-cover border-4 border-gray-200"
            @error="handleImageError"
          />
          <button 
            @click="showAvatarModal = true"
            class="text-sm text-blue-600 hover:text-blue-800 transition-colors"
          >
            修改头像
          </button>
        </div>
      </div>

          <!-- 快捷操作 -->
      <div class="bg-white/80 backdrop-blur-sm rounded-2xl shadow-xl p-6">
        <h3 class="text-lg font-semibold text-gray-900 mb-4">快捷操作</h3>
        <div class="space-y-3">
          <button 
            @click="navigateTo('/dashboard')"
            class="w-full px-4 py-2 text-left text-gray-700 hover:bg-gray-50 rounded-lg transition-colors flex items-center"
          >
            <i class="fas fa-home mr-2"></i>
            返回首页
          </button>
        </div>
      </div>
        </div>
      </div>

      <!-- 错误提示 -->
      <div v-if="error" class="mt-6 p-4 bg-red-50 border border-red-200 rounded-lg">
        <p class="text-sm text-red-600">{{ error }}</p>
      </div>

      <!-- 成功提示 -->
  <div v-if="success" class="mt-6 p-4 bg-green-50 border border-green-200 rounded-lg">
    <p class="text-sm text-green-600">{{ success }}</p>
  </div>

  <!-- 修改头像弹窗 -->
  <ChangeAvatarModal 
    v-if="showAvatarModal" 
    @close="showAvatarModal = false"
    @avatar-updated="handleAvatarUpdated"
  />
</div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useUserStore } from '../stores/user'
import ChangeAvatarModal from './common/ChangeAvatarModal.vue'

const userStore = useUserStore()

// 状态
const userInfo = ref({
  username: '',
  email: '',
  role: 'user',
  createdAt: '',
  avatar: ''
})
const editingEmail = ref(false)
const originalEmail = ref('')
const loading = ref(false)
const error = ref<string>('')
const success = ref<string>('')
const showAvatarModal = ref(false)

// 处理图片加载错误
const handleImageError = (event: Event) => {
  const img = event.target as HTMLImageElement
  img.style.display = 'none'
  // 触发重新加载用户信息
  loadUserInfo()
}

// 格式化日期
const formatDate = (dateString: string) => {
  if (!dateString) return '未知'
  return new Date(dateString).toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  })
}

// 加载用户信息
const loadUserInfo = () => {
  if (userStore.user) {
    userInfo.value = {
      username: userStore.user.username,
      email: userStore.user.email || '',
      role: userStore.user.role,
      createdAt: userStore.user.createdAt,
      avatar: userStore.user.avatar || ''
    }
    originalEmail.value = userInfo.value.email
  }
}

// 切换邮箱编辑
const toggleEditEmail = () => {
  if (editingEmail.value) {
    userInfo.value.email = originalEmail.value
  }
  editingEmail.value = !editingEmail.value
}

// 取消编辑邮箱
const cancelEditEmail = () => {
  userInfo.value.email = originalEmail.value
  editingEmail.value = false
}

// 保存邮箱
const saveEmail = async () => {
  loading.value = true
  error.value = ''
  success.value = ''

  try {
    // 这里可以添加更新邮箱的API调用
    // 为了演示，我们直接更新本地数据
    if (userStore.user) {
      userStore.user.email = userInfo.value.email
      localStorage.setItem('currentUser', JSON.stringify(userStore.user))
      originalEmail.value = userInfo.value.email
      success.value = '邮箱地址更新成功！'
      editingEmail.value = false
    }
  } catch (err) {
    error.value = '更新邮箱失败，请重试'
  } finally {
    loading.value = false
  }
}

// 页面导航
const navigateTo = (path: string) => {
  window.location.href = path
}



// 头像更新处理
const handleAvatarUpdated = async () => {
  try {
    await userStore.getUserInfo()
    loadUserInfo() // 重新加载本地显示的用户信息
    showAvatarModal.value = false
    success.value = '头像更新成功！'
  } catch (err) {
    error.value = '头像更新失败，请重试'
  }
}

// 生命周期
onMounted(() => {
  loadUserInfo()
})
</script>