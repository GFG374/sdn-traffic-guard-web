<template>
  <header class="bg-white h-16 shadow-sm flex items-center justify-between px-6 sticky top-0 z-20">
    <div class="flex items-center">
      <button 
        class="mr-4 text-gray-600 hover:text-blue-600 transition-colors duration-300"
        @click="$emit('toggleSidebar')"
      >
        <i class="fas fa-bars text-xl"></i>
      </button>
      <div class="relative">
        <span class="absolute inset-y-0 left-0 flex items-center pl-3">
          <i class="fas fa-search text-gray-600"></i>
        </span>
        <input 
          type="text" 
          placeholder="搜索..." 
          class="pl-10 pr-4 py-2 rounded-lg border border-gray-300 focus:outline-none focus:ring-2 focus:ring-blue-500/30 focus:border-blue-500 transition-colors duration-300 w-64"
        >
      </div>
    </div>
    
    <div class="flex items-center space-x-6">
      <button class="relative text-gray-600 hover:text-blue-600 transition-colors duration-300">
        <i class="fas fa-bell text-xl"></i>
        <span class="absolute -top-1 -right-1 w-4 h-4 bg-red-500 rounded-full text-white text-xs flex items-center justify-center">3</span>
      </button>
      
      <!-- 设置按钮和下拉菜单 -->
      <div class="relative">
        <button 
          @click="toggleSettingsMenu"
          class="relative text-gray-600 hover:text-blue-600 transition-colors duration-300"
        >
          <i class="fas fa-cog text-xl"></i>
        </button>
        
        <!-- 设置下拉菜单 -->
        <div 
          v-if="showSettingsMenu"
          class="absolute right-0 mt-2 w-64 bg-white rounded-lg shadow-lg border border-gray-200 z-50"
        >
          <!-- 用户信息 -->
          <div class="p-4 border-b border-gray-200">
            <div class="flex items-center space-x-3">
              <div v-if="!user?.avatar || user.avatar.startsWith('bg-')" 
                :class="[
                  'w-14 h-14 rounded-full flex items-center justify-center text-white font-bold text-xl',
                  user?.avatar || 'bg-gradient-to-r from-indigo-500 to-purple-600'
                ]"
              >
                {{ user?.username?.charAt(0).toUpperCase() || 'U' }}
              </div>
              <img v-else 
                :src="user.avatar.startsWith('http') || user.avatar.startsWith('data:') ? user.avatar : 'http://localhost:8001' + user.avatar" 
                alt="用户头像" 
                class="w-14 h-14 rounded-full object-cover border-2 border-gray-300"
                @error="handleImageError"
              />
              <div>
                <p class="font-medium text-gray-900">{{ user?.username || '用户' }}</p>
                <p class="text-sm text-gray-600">{{ user?.email || '' }}</p>
              </div>
            </div>
          </div>
          
          <!-- 设置选项 -->
          <div class="py-2">
            <button 
              @click="openChangeAvatar"
              class="w-full px-4 py-2 text-left text-sm text-gray-700 hover:bg-gray-50 flex items-center"
            >
              <i class="fas fa-user-circle mr-3 text-gray-400"></i>
              修改头像
            </button>
            
            <button 
              @click="openChangePassword"
              class="w-full px-4 py-2 text-left text-sm text-gray-700 hover:bg-gray-50 flex items-center"
            >
              <i class="fas fa-key mr-3 text-gray-400"></i>
              修改密码
            </button>
            
            <button 
              @click="openAccountDetails"
              class="w-full px-4 py-2 text-left text-sm text-gray-700 hover:bg-gray-50 flex items-center"
            >
              <i class="fas fa-user-cog mr-3 text-gray-400"></i>
              账号详情
            </button>
            
            <div class="border-t border-gray-200 my-2"></div>
            
            <button 
              @click="handleLogout"
              class="w-full px-4 py-2 text-left text-sm text-red-600 hover:bg-red-50 flex items-center"
            >
              <i class="fas fa-sign-out-alt mr-3"></i>
              退出登录
            </button>
          </div>
        </div>
      </div>
      
      <div class="flex items-center space-x-2">
        <div v-if="!user?.avatar || user.avatar.startsWith('bg-')" 
          :class="[
            'w-10 h-10 rounded-full flex items-center justify-center text-white font-bold',
            user?.avatar || 'bg-gradient-to-r from-indigo-500 to-purple-600'
          ]"
        >
          {{ user?.username?.charAt(0).toUpperCase() || 'U' }}
        </div>
        <img v-else 
          :src="user.avatar.startsWith('http') || user.avatar.startsWith('data:') ? user.avatar : 'http://localhost:8001' + user.avatar" 
          alt="用户头像" 
          class="w-10 h-10 rounded-full object-cover border-2 border-gray-300"
          @error="handleImageError"
        >
        <span class="text-sm font-medium text-gray-700">{{ user?.username || '用户' }}</span>
      </div>
    </div>
    
    <!-- 修改头像弹窗 -->
    <ChangeAvatarModal 
      v-if="showChangeAvatarModal" 
      @close="showChangeAvatarModal = false"
      @avatar-updated="handleAvatarUpdated"
    />
  </header>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue';
import { useRouter } from 'vue-router';
import { useUserStore } from '../../stores/user';
import ChangeAvatarModal from './ChangeAvatarModal.vue';

// 定义 emits
defineEmits<{
  toggleSidebar: []
}>();

const router = useRouter();
const userStore = useUserStore();

// 状态管理
const showSettingsMenu = ref(false);
const showChangeAvatarModal = ref(false);

// 获取用户信息
const user = userStore.user;

// 切换设置菜单
const toggleSettingsMenu = () => {
  showSettingsMenu.value = !showSettingsMenu.value;
};

// 点击外部关闭菜单
const handleClickOutside = (event: Event) => {
  const target = event.target as HTMLElement;
  if (!target.closest('.relative')) {
    showSettingsMenu.value = false;
  }
};

// 打开修改头像
const openChangeAvatar = () => {
  showSettingsMenu.value = false;
  showChangeAvatarModal.value = true;
};

// 打开修改密码
const openChangePassword = () => {
  showSettingsMenu.value = false;
  router.push('/change-password');
};

// 打开账号详情
const openAccountDetails = () => {
  showSettingsMenu.value = false;
  router.push('/account-details');
};

// 退出登录
const handleLogout = () => {
  showSettingsMenu.value = false;
  userStore.logout();
  router.push('/login');
};

// 处理图片加载错误
const handleImageError = (event: Event) => {
  const img = event.target as HTMLImageElement;
  img.style.display = 'none';
  // 强制刷新用户数据
  userStore.getUserInfo();
};

// 头像更新处理
const handleAvatarUpdated = () => {
  // 可以在这里添加头像更新后的处理逻辑
  console.log('头像已更新');
};

// 生命周期钩子
onMounted(() => {
  document.addEventListener('click', handleClickOutside);
});

onUnmounted(() => {
  document.removeEventListener('click', handleClickOutside);
});
</script>

<style scoped>
/* 顶部导航栏样式已通过Tailwind工具类实现 */
</style>
