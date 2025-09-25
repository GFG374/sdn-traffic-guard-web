<template>
  <div class="min-h-screen bg-gradient-to-br from-blue-50 via-indigo-50 to-purple-50 flex items-center justify-center p-4">
    <div class="w-full max-w-md">
      <!-- 标题 -->
      <div class="text-center mb-8">
        <div class="inline-flex items-center justify-center w-16 h-16 bg-gradient-to-r from-indigo-500 to-purple-600 rounded-full mb-4">
          <i class="fas fa-key text-white text-2xl"></i>
        </div>
        <h2 class="text-4xl font-bold bg-gradient-to-r from-indigo-600 to-purple-600 bg-clip-text text-transparent mb-2">
          修改密码
        </h2>
        <p class="text-gray-600">请设置一个安全的新密码</p>
      </div>

      <!-- 表单卡片 -->
      <div class="bg-white/80 backdrop-blur-sm rounded-2xl shadow-xl p-8">
        <form @submit.prevent="handleChangePassword" class="space-y-6">
          <!-- 原密码 -->
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-2">
              原密码
            </label>
            <div class="relative">
              <input 
                v-model="oldPassword" 
                :type="showOldPassword ? 'text' : 'password'"
                placeholder="请输入原密码"
                class="w-full px-4 py-3 rounded-lg border border-gray-300 focus:outline-none focus:ring-2 focus:ring-blue-500/30 focus:border-blue-500 transition-colors"
                required
              />
              <button 
                type="button"
                @click="showOldPassword = !showOldPassword"
                class="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
              >
                <i :class="showOldPassword ? 'fas fa-eye-slash' : 'fas fa-eye'"></i>
              </button>
            </div>
          </div>

          <!-- 新密码 -->
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-2">
              新密码
            </label>
            <div class="relative">
              <input 
                v-model="newPassword" 
                :type="showNewPassword ? 'text' : 'password'"
                placeholder="请输入新密码"
                class="w-full px-4 py-3 rounded-lg border border-gray-300 focus:outline-none focus:ring-2 focus:ring-blue-500/30 focus:border-blue-500 transition-colors"
                required
                @input="validatePassword"
              />
              <button 
                type="button"
                @click="showNewPassword = !showNewPassword"
                class="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
              >
                <i :class="showNewPassword ? 'fas fa-eye-slash' : 'fas fa-eye'"></i>
              </button>
            </div>
            <div v-if="newPassword" class="mt-2 space-y-1">
              <div class="text-xs flex items-center" :class="passwordValid.length ? 'text-green-600' : 'text-red-600'">
                <i :class="passwordValid.length ? 'fas fa-check-circle' : 'fas fa-times-circle'" class="mr-1"></i>
                至少6个字符
              </div>
            </div>
          </div>

          <!-- 确认新密码 -->
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-2">
              确认新密码
            </label>
            <div class="relative">
              <input 
                v-model="confirmPassword" 
                :type="showConfirmPassword ? 'text' : 'password'"
                placeholder="请再次输入新密码"
                class="w-full px-4 py-3 rounded-lg border border-gray-300 focus:outline-none focus:ring-2 focus:ring-blue-500/30 focus:border-blue-500 transition-colors"
                required
              />
              <button 
                type="button"
                @click="showConfirmPassword = !showConfirmPassword"
                class="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
              >
                <i :class="showConfirmPassword ? 'fas fa-eye-slash' : 'fas fa-eye'"></i>
              </button>
            </div>
          </div>

          <!-- 错误提示 -->
          <div v-if="error" class="p-3 bg-red-50 border border-red-200 rounded-lg">
            <p class="text-sm text-red-600">{{ error }}</p>
          </div>

          <!-- 成功提示 -->
          <div v-if="success" class="p-3 bg-green-50 border border-green-200 rounded-lg">
            <p class="text-sm text-green-600">{{ success }}</p>
          </div>

          <!-- 提交按钮 -->
          <button 
            type="submit"
            :disabled="loading || !isFormValid"
            class="w-full py-3 bg-gradient-to-r from-indigo-500 to-purple-600 text-white rounded-lg font-medium hover:from-indigo-600 hover:to-purple-700 disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-300"
          >
            {{ loading ? '修改中...' : '确认修改' }}
          </button>
        </form>

        <!-- 返回按钮 -->
        <div class="mt-6 text-center">
          <button 
            @click="goBack"
            class="text-blue-600 hover:text-blue-800 text-sm font-medium transition-colors"
          >
            <i class="fas fa-arrow-left mr-1"></i>
            返回
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '../stores/user'

const router = useRouter()
const userStore = useUserStore()

// 状态
const oldPassword = ref('')
const newPassword = ref('')
const confirmPassword = ref('')
const loading = ref(false)
const error = ref('')
const success = ref('')
const showOldPassword = ref(false)
const showNewPassword = ref(false)
const showConfirmPassword = ref(false)

// 密码验证
const passwordValid = ref({
  length: false,
  uppercase: true,
  lowercase: true,
  number: true
})

// 表单验证
const isFormValid = computed(() => {
  return (
    oldPassword.value.trim() &&
    newPassword.value.trim() &&
    confirmPassword.value.trim() &&
    newPassword.value === confirmPassword.value &&
    passwordValid.value.length
  )
})

// 验证密码强度
const validatePassword = () => {
  const password = newPassword.value
  passwordValid.value = {
    length: password.length >= 6,
    uppercase: true,
    lowercase: true,
    number: true
  }
}

// 修改密码
const handleChangePassword = async () => {
  if (newPassword.value !== confirmPassword.value) {
    error.value = '两次输入的新密码不一致'
    return
  }

  loading.value = true
  error.value = ''
  success.value = ''

  try {
    const result = await userStore.changePassword(
      userStore.user?.username || '',
      oldPassword.value,
      newPassword.value
    )

    if (result.success) {
      success.value = result.message || '密码修改成功！'
      
      // 清空表单
      oldPassword.value = ''
      newPassword.value = ''
      confirmPassword.value = ''
      
      // 延迟跳转
      setTimeout(() => {
        router.push('/dashboard')
      }, 2000)
    } else {
      error.value = result.message || '密码修改失败'
    }
  } catch (err) {
    error.value = '修改密码时发生错误，请重试'
  } finally {
    loading.value = false
  }
}

// 返回
const goBack = () => {
  router.back()
}
</script>