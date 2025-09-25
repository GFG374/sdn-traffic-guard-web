<template>
  <div class="min-h-screen flex items-center justify-center bg-gradient-to-br from-blue-50 via-indigo-50 to-purple-50 py-12 px-4 sm:px-6 lg:px-8">
    <div class="max-w-md w-full space-y-8">
      <div class="text-center">
        <div class="inline-flex items-center justify-center w-16 h-16 bg-gradient-to-r from-indigo-500 to-purple-600 rounded-full mb-4">
          <svg class="w-8 h-8 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z"></path>
          </svg>
        </div>
        <h2 class="text-4xl font-bold bg-gradient-to-r from-indigo-600 to-purple-600 bg-clip-text text-transparent">
          网络管理平台
        </h2>
        <p class="mt-3 text-center text-sm text-gray-600">
          安全高效的网络设备管理系统
        </p>
        <p class="mt-2 text-center text-sm">
          <a href="#" @click.prevent="showRegister = !showRegister" class="font-medium text-indigo-600 hover:text-indigo-500 transition-colors duration-200">
            {{ showRegister ? '已有账号？直接登录' : '创建新账号' }}
          </a>
        </p>
      </div>
      
      <form class="mt-8 space-y-6" @submit.prevent="handleSubmit">
        <div class="bg-white/80 backdrop-blur-sm p-8 rounded-2xl shadow-xl border border-gray-100">
          <div class="space-y-5">
            <!-- 头像选择 - 仅在注册时显示 -->
            <div v-if="showRegister" class="flex flex-col items-center space-y-4">
              <label class="block text-sm font-medium text-gray-700">设置头像</label>
              <!-- 头像预览区域 -->
              <div class="relative">
                <!-- 注册时的头像预览 -->
                <div v-if="showRegister" 
                  class="w-24 h-24 rounded-full flex items-center justify-center text-white text-3xl font-bold transition-all duration-200 bg-blue-500"
                >
                  {{ form.username.charAt(0).toUpperCase() || 'U' }}
                </div>
                <img
                  v-if="showRegister && previewAvatar"
                  :src="previewAvatar"
                  alt="头像预览"
                  class="w-24 h-24 rounded-full object-cover border-2 border-indigo-500 absolute top-0 left-0"
                />
                <!-- 登录时的用户头像显示 -->
                <div v-if="!showRegister" 
                  class="w-24 h-24 rounded-full flex items-center justify-center text-white text-3xl font-bold transition-all duration-200 bg-blue-500"
                >
                  {{ form.username.charAt(0).toUpperCase() || 'U' }}
                </div>
                <img
                  v-if="!showRegister && userAvatar"
                  :src="userAvatar"
                  alt="用户头像"
                  class="w-24 h-24 rounded-full object-cover border-2 border-indigo-500 absolute top-0 left-0"
                />
                <!-- 删除按钮 -->
                <button
                  v-if="previewAvatar"
                  @click="removeAvatar"
                  class="absolute -top-2 -right-2 w-6 h-6 bg-red-500 text-white rounded-full flex items-center justify-center text-xs hover:bg-red-600 transition-colors"
                  type="button"
                >
                  ×
                </button>
              </div>
              
              <!-- 文件上传按钮 -->
              <div class="flex space-x-2">
                <label class="cursor-pointer">
                  <input
                    type="file"
                    accept="image/*"
                    @change="handleAvatarChange"
                    class="hidden"
                  />
                  <div class="px-4 py-2 bg-indigo-600 text-white text-sm rounded-lg hover:bg-indigo-700 transition-colors">
                    选择头像
                  </div>
                </label>
              </div>
            </div>

            <div>
              <label for="username" class="block text-sm font-medium text-gray-700 mb-2">
                用户名
              </label>
              <div class="relative">
                <div class="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                  <svg class="h-5 w-5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z"></path>
                  </svg>
                </div>
                <input
                  id="username"
                  name="username"
                  type="text"
                  required
                  class="appearance-none relative block w-full pl-10 pr-3 py-3 border border-gray-300 placeholder-gray-500 text-gray-900 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent sm:text-sm transition-all duration-200"
                  placeholder="请输入用户名"
                  v-model="form.username"
                />
              </div>
            </div>
            
            <div>
              <label for="password" class="block text-sm font-medium text-gray-700 mb-2">
                密码
              </label>
              <div class="relative">
                <div class="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                  <svg class="h-5 w-5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z"></path>
                  </svg>
                </div>
                <input
                  id="password"
                  name="password"
                  type="password"
                  required
                  class="appearance-none relative block w-full pl-10 pr-3 py-3 border border-gray-300 placeholder-gray-500 text-gray-900 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent sm:text-sm transition-all duration-200"
                  placeholder="请输入密码"
                  v-model="form.password"
                />
              </div>
            </div>
            
            <div v-if="showRegister">
              <label for="confirmPassword" class="block text-sm font-medium text-gray-700 mb-2">
                确认密码
              </label>
              <div class="relative">
                <div class="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                  <svg class="h-5 w-5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z"></path>
                  </svg>
                </div>
                <input
                  id="confirmPassword"
                  name="confirmPassword"
                  type="password"
                  required
                  class="appearance-none relative block w-full pl-10 pr-3 py-3 border border-gray-300 placeholder-gray-500 text-gray-900 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent sm:text-sm transition-all duration-200"
                  placeholder="请再次输入密码"
                  v-model="form.confirmPassword"
                />
              </div>
            </div>
          </div>

          <div class="pt-6">
            <button
              type="submit"
              class="group relative w-full flex justify-center py-3 px-4 border border-transparent text-sm font-medium rounded-lg text-white bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-700 hover:to-purple-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 transform transition-all duration-200 hover:scale-[1.02] active:scale-[0.98] shadow-lg hover:shadow-xl"
            >
              <span class="absolute left-0 inset-y-0 flex items-center pl-3">
                <svg class="h-5 w-5 text-white group-hover:text-indigo-100 transition-colors duration-200" fill="currentColor" viewBox="0 0 20 20">
                  <path fill-rule="evenodd" d="M5 9V7a5 5 0 0110 0v2a2 2 0 012 2v5a2 2 0 01-2 2H5a2 2 0 01-2-2v-5a2 2 0 012-2zm8-2v2H7V7a3 3 0 016 0z" clip-rule="evenodd" />
                </svg>
              </span>
              {{ showRegister ? '创建账号' : '安全登录' }}
            </button>
          </div>

          <div v-if="!showRegister" class="text-center pt-4">
            <router-link to="/forgot-password" class="text-indigo-600 hover:text-indigo-500 text-sm font-medium transition-colors duration-200 hover:underline">
              忘记密码？立即找回
            </router-link>
          </div>

          <div v-if="error" class="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-sm text-center">
            <div class="flex items-center justify-center">
              <svg class="h-4 w-4 mr-2" fill="currentColor" viewBox="0 0 20 20">
                <path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clip-rule="evenodd" />
              </svg>
              {{ error }}
            </div>
          </div>
          
          <div v-if="success" class="bg-green-50 border border-green-200 text-green-700 px-4 py-3 rounded-lg text-sm text-center">
            <div class="flex items-center justify-center">
              <svg class="h-4 w-4 mr-2" fill="currentColor" viewBox="0 0 20 20">
                <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd" />
              </svg>
              {{ success }}
            </div>
          </div>
        </div>
      </form>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, watch } from 'vue'
import { useUserStore } from '../stores/user'
import { useRouter } from 'vue-router'

const router = useRouter()
const userStore = useUserStore()

const showRegister = ref(false)
const error = ref('')
const success = ref('')

const form = reactive({
  username: '',
  password: '',
  confirmPassword: '',
  avatar: null as string | null
})

const previewAvatar = ref<string>('')
const userAvatar = ref<string>('')

// 监听用户名变化，自动获取用户头像
const fetchUserAvatar = async (username: string) => {
  if (!username.trim()) {
    userAvatar.value = ''
    return
  }
  
  try {
    const response = await fetch(`/api/auth/user-avatar/${username}`)
    const data = await response.json()
    if (data.success && data.avatar) {
      userAvatar.value = data.avatar
    } else {
      userAvatar.value = ''
    }
  } catch (error) {
    console.error('获取用户头像失败:', error)
    userAvatar.value = ''
  }
}

// 监听用户名输入
watch(() => form.username, (newUsername) => {
  if (!showRegister.value) {
    fetchUserAvatar(newUsername)
  }
})

const handleAvatarChange = (event: Event) => {
  const target = event.target as HTMLInputElement
  const file = target.files?.[0]
  
  if (file) {
    // 检查文件类型
    if (!file.type.startsWith('image/')) {
      error.value = '请选择图片文件'
      return
    }
    
    // 检查文件大小 (最大2MB)
    if (file.size > 2 * 1024 * 1024) {
      error.value = '图片文件不能超过2MB'
      return
    }
    
    const reader = new FileReader()
    reader.onload = (e) => {
      previewAvatar.value = e.target?.result as string
      form.avatar = previewAvatar.value // 使用Base64字符串作为头像
    }
    reader.readAsDataURL(file)
  }
}

const removeAvatar = () => {
  previewAvatar.value = ''
  form.avatar = null
  const fileInput = document.querySelector('input[type="file"]') as HTMLInputElement
  if (fileInput) {
    fileInput.value = ''
  }
}

const handleSubmit = async () => {
  error.value = ''
  success.value = ''

  if (showRegister.value) {
    if (form.password !== form.confirmPassword) {
      error.value = '两次输入的密码不一致'
      return
    }
    
    const result = await userStore.register(form.username, form.password, undefined, form.avatar || undefined)
    if (result.success) {
      success.value = '注册成功！正在跳转到登录...'
      setTimeout(() => {
        showRegister.value = false
        success.value = ''
        form.username = ''
        form.password = ''
        form.confirmPassword = ''
        previewAvatar.value = ''
        form.avatar = null
      }, 1500)
    } else {
      error.value = result.message
    }
  } else {
    const result = await userStore.login(form.username, form.password)
    if (result.success) {
      router.push('/dashboard')
    } else {
      error.value = result.message
    }
  }
}
</script>