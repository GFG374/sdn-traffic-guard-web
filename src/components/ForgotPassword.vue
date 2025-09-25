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
          密码管理
        </h2>
        <p class="mt-3 text-center text-sm text-gray-600">
          找回或修改您的账户密码
        </p>
      </div>

      <!-- 标签页切换 -->
      <div class="flex bg-gray-100 rounded-lg p-1">
        <button
          @click="activeTab = 'recover'"
          :class="[
            activeTab === 'recover' 
              ? 'bg-white text-indigo-600 shadow-sm' 
              : 'text-gray-500 hover:text-gray-700',
            'flex-1 py-2 px-4 rounded-md text-sm font-medium transition-all duration-200'
          ]"
        >
          找回密码
        </button>
        <button
          @click="activeTab = 'change'"
          :class="[
            activeTab === 'change' 
              ? 'bg-white text-indigo-600 shadow-sm' 
              : 'text-gray-500 hover:text-gray-700',
            'flex-1 py-2 px-4 rounded-md text-sm font-medium transition-all duration-200'
          ]"
        >
          修改密码
        </button>
      </div>

      <!-- 找回密码表单 -->
      <form v-if="activeTab === 'recover'" class="mt-8 space-y-6" @submit.prevent="handleGetPassword">
        <div class="bg-white/80 backdrop-blur-sm p-8 rounded-2xl shadow-xl border border-gray-100">
          <div class="space-y-5">
            <div>
              <label for="recover-username" class="block text-sm font-medium text-gray-700 mb-2">
                用户名
              </label>
              <div class="relative">
                <div class="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                  <svg class="h-5 w-5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z"></path>
                  </svg>
                </div>
                <input
                  id="recover-username"
                  v-model="recoverUsername"
                  name="username"
                  type="text"
                  required
                  class="appearance-none relative block w-full pl-10 pr-3 py-3 border border-gray-300 placeholder-gray-500 text-gray-900 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent sm:text-sm transition-all duration-200"
                  placeholder="请输入用户名"
                />
              </div>
            </div>

            <div v-if="recoverError" class="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-sm text-center">
              <div class="flex items-center justify-center">
                <svg class="h-4 w-4 mr-2" fill="currentColor" viewBox="0 0 20 20">
                  <path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clip-rule="evenodd" />
                </svg>
                {{ recoverError }}
              </div>
            </div>

            <div v-if="recoverSuccess" class="bg-green-50 border border-green-200 text-green-700 px-4 py-3 rounded-lg text-sm text-center">
              <div class="flex items-center justify-center">
                <svg class="h-4 w-4 mr-2" fill="currentColor" viewBox="0 0 20 20">
                  <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd" />
                </svg>
                {{ recoverSuccess }}
              </div>
            </div>

            <div v-if="showPassword" class="bg-gradient-to-r from-indigo-50 to-purple-50 p-4 rounded-lg border border-indigo-200">
              <div class="flex items-center">
                <svg class="h-5 w-5 text-indigo-600 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"></path>
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"></path>
                </svg>
                <div>
                  <p class="text-sm font-medium text-gray-700">您的密码是：</p>
                  <p class="text-lg font-bold text-transparent bg-clip-text bg-gradient-to-r from-indigo-600 to-purple-600">{{ showPassword }}</p>
                </div>
              </div>
            </div>

            <div>
              <button
                type="submit"
                :disabled="loading"
                class="group relative w-full flex justify-center py-3 px-4 border border-transparent text-sm font-medium rounded-lg text-white bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-700 hover:to-purple-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:opacity-50 transition-all duration-200 shadow-lg hover:shadow-xl"
              >
                <span class="absolute left-0 inset-y-0 flex items-center pl-3">
                  <svg class="h-5 w-5 text-white group-hover:text-indigo-100 transition-colors duration-200" fill="currentColor" viewBox="0 0 20 20">
                    <path fill-rule="evenodd" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" clip-rule="evenodd" />
                    <path d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                  </svg>
                </span>
                {{ loading ? '查询中...' : '找回密码' }}
              </button>
            </div>
          </div>
        </div>
      </form>

      <!-- 修改密码表单 -->
      <form v-if="activeTab === 'change'" class="mt-8 space-y-6" @submit.prevent="handleChangePassword">
        <div class="bg-white/80 backdrop-blur-sm p-8 rounded-2xl shadow-xl border border-gray-100">
          <div class="space-y-5">
            <div>
              <label for="change-username" class="block text-sm font-medium text-gray-700 mb-2">
                用户名
              </label>
              <div class="relative">
                <div class="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                  <svg class="h-5 w-5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z"></path>
                  </svg>
                </div>
                <input
                  id="change-username"
                  v-model="changeUsername"
                  name="username"
                  type="text"
                  required
                  class="appearance-none relative block w-full pl-10 pr-3 py-3 border border-gray-300 placeholder-gray-500 text-gray-900 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent sm:text-sm transition-all duration-200"
                  placeholder="请输入用户名"
                />
              </div>
            </div>
            
            <div>
              <label for="old-password" class="block text-sm font-medium text-gray-700 mb-2">
                原密码
              </label>
              <div class="relative">
                <div class="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                  <svg class="h-5 w-5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z"></path>
                  </svg>
                </div>
                <input
                  id="old-password"
                  v-model="oldPassword"
                  name="old-password"
                  type="password"
                  required
                  class="appearance-none relative block w-full pl-10 pr-3 py-3 border border-gray-300 placeholder-gray-500 text-gray-900 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent sm:text-sm transition-all duration-200"
                  placeholder="请输入原密码"
                />
              </div>
            </div>
            
            <div>
              <label for="new-password" class="block text-sm font-medium text-gray-700 mb-2">
                新密码
              </label>
              <div class="relative">
                <div class="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                  <svg class="h-5 w-5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z"></path>
                  </svg>
                </div>
                <input
                  id="new-password"
                  v-model="newPassword"
                  name="new-password"
                  type="password"
                  required
                  class="appearance-none relative block w-full pl-10 pr-3 py-3 border border-gray-300 placeholder-gray-500 text-gray-900 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent sm:text-sm transition-all duration-200"
                  placeholder="请输入新密码"
                />
              </div>
            </div>
          </div>

          <div v-if="changeError" class="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-sm text-center">
            <div class="flex items-center justify-center">
              <svg class="h-4 w-4 mr-2" fill="currentColor" viewBox="0 0 20 20">
                <path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clip-rule="evenodd" />
              </svg>
              {{ changeError }}
            </div>
          </div>
          
          <div v-if="changeSuccess" class="bg-green-50 border border-green-200 text-green-700 px-4 py-3 rounded-lg text-sm text-center">
            <div class="flex items-center justify-center">
              <svg class="h-4 w-4 mr-2" fill="currentColor" viewBox="0 0 20 20">
                <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd" />
              </svg>
              {{ changeSuccess }}
            </div>
          </div>

          <div>
            <button
              type="submit"
              :disabled="loading"
              class="group relative w-full flex justify-center py-3 px-4 border border-transparent text-sm font-medium rounded-lg text-white bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-700 hover:to-purple-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:opacity-50 transition-all duration-200 shadow-lg hover:shadow-xl"
            >
              <span class="absolute left-0 inset-y-0 flex items-center pl-3">
                <svg class="h-5 w-5 text-white group-hover:text-indigo-100 transition-colors duration-200" fill="currentColor" viewBox="0 0 20 20">
                  <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd" />
                </svg>
              </span>
              {{ loading ? '修改中...' : '修改密码' }}
            </button>
          </div>
        </div>
      </form>

      <div class="text-center">
        <router-link to="/login" class="text-indigo-600 hover:text-indigo-500 text-sm font-medium transition-colors duration-200 hover:underline">
          返回登录
        </router-link>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useUserStore } from '../stores/user'

const userStore = useUserStore()

// 标签页状态
const activeTab = ref<'recover' | 'change'>('recover')

// 找回密码相关状态
const recoverUsername = ref('')
const recoverError = ref('')
const recoverSuccess = ref('')
const showPassword = ref('')

// 修改密码相关状态
const changeUsername = ref('')
const oldPassword = ref('')
const newPassword = ref('')
const changeError = ref('')
const changeSuccess = ref('')

const loading = ref(false)

// 找回密码功能
const handleGetPassword = async () => {
  loading.value = true
  recoverError.value = ''
  recoverSuccess.value = ''
  showPassword.value = ''

  if (!recoverUsername.value.trim()) {
    recoverError.value = '请输入用户名'
    loading.value = false
    return
  }

  try {
    const result = await userStore.getPassword(recoverUsername.value.trim())
    
    if (result.success && result.password) {
      showPassword.value = result.password
      recoverSuccess.value = '密码获取成功！请妥善保管您的密码'
    } else {
      recoverError.value = result.message || '获取密码失败'
      if (result.message.includes('用户不存在')) {
        recoverError.value = '用户不存在，请检查用户名是否正确'
      }
    }
  } catch (err) {
    recoverError.value = '获取密码失败，请检查网络连接后重试'
  } finally {
    loading.value = false
  }
}

// 修改密码功能
const handleChangePassword = async () => {
  loading.value = true
  changeError.value = ''
  changeSuccess.value = ''

  if (!changeUsername.value.trim()) {
    changeError.value = '请输入用户名'
    loading.value = false
    return
  }

  if (!oldPassword.value.trim()) {
    changeError.value = '请输入原密码'
    loading.value = false
    return
  }

  if (!newPassword.value.trim()) {
    changeError.value = '请输入新密码'
    loading.value = false
    return
  }

  if (newPassword.value === oldPassword.value) {
    changeError.value = '新密码不能与原密码相同'
    loading.value = false
    return
  }

  try {
    const result = await userStore.changePassword(
      changeUsername.value.trim(),
      oldPassword.value.trim(),
      newPassword.value.trim()
    )
    
    if (result.success) {
      changeSuccess.value = '密码修改成功！请使用新密码登录'
      // 清空表单
      oldPassword.value = ''
      newPassword.value = ''
    } else {
      changeError.value = result.message || '密码修改失败'
      if (result.message.includes('用户名或原密码错误')) {
        changeError.value = '用户名或原密码错误，请检查后重试'
      }
    }
  } catch (err) {
    changeError.value = '密码修改失败，请检查网络连接后重试'
  } finally {
    loading.value = false
  }
}
</script>