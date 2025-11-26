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
                <div class="w-full px-4 py-3 rounded-lg border border-gray-100 bg-gray-50 flex items-center justify-between">
                  <div class="flex items-center space-x-3">
                    <span class="inline-flex h-10 w-10 items-center justify-center rounded-full bg-gradient-to-r from-indigo-500 to-purple-600 text-white font-semibold text-lg">
                      {{ userInfo.username?.charAt(0).toUpperCase() || 'U' }}
                    </span>
                    <div>
                      <p class="text-gray-900 font-medium">{{ userInfo.username }}</p>
                      <p class="text-xs text-gray-500">账号不可编辑</p>
                    </div>
                  </div>
                </div>
              </div>

              <!-- 角色 -->
              <div>
                <label class="block text-sm font-medium text-gray-700 mb-2">账号类型</label>
                <div class="px-4 py-3 rounded-lg border border-gray-100 bg-gray-50 flex items-center justify-between">
                  <div class="flex items-center space-x-2">
                    <span class="inline-flex items-center justify-center h-9 w-9 rounded-full bg-gradient-to-r from-purple-500 to-indigo-500 text-white">
                      <i class="fas fa-crown"></i>
                    </span>
                    <div>
                      <p class="text-gray-900 font-semibold">管理员</p>
                      <p class="text-xs text-gray-500">默认授予全部控制权限</p>
                    </div>
                  </div>
                  <span class="px-3 py-1 rounded-full text-sm font-medium bg-purple-100 text-purple-700">Admin</span>
                </div>
              </div>

              <!-- 注册时间 -->
              <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div class="p-4 rounded-xl border border-gray-100 bg-gradient-to-br from-white to-indigo-50">
                  <p class="text-sm text-gray-500 mb-1">注册时间</p>
                  <p class="text-lg font-semibold text-gray-900">{{ formatDate(userInfo.createdAt) }}</p>
                </div>
                <div class="p-4 rounded-xl border border-gray-100 bg-gradient-to-br from-white to-purple-50">
                  <p class="text-sm text-gray-500 mb-1">当前状态</p>
                  <p class="text-lg font-semibold text-green-600 flex items-center space-x-2">
                    <i class="fas fa-check-circle"></i>
                    <span>活跃</span>
                  </p>
                </div>
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
            :src="userInfo.avatar.startsWith('http') || userInfo.avatar.startsWith('data:') ? userInfo.avatar : 'http://localhost:8000' + userInfo.avatar" 
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
  role: 'user',
  createdAt: '',
  avatar: ''
})
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
      role: userStore.user.role || 'admin',
      createdAt: userStore.user.createdAt,
      avatar: userStore.user.avatar || ''
    }
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