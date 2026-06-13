<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { NButton, NInput, NCard } from 'naive-ui'
import { useAuthStore } from '../stores/auth'

const router = useRouter()
const auth = useAuthStore()

const username = ref('')
const email = ref('')
const password = ref('')
const confirmPassword = ref('')
const error = ref('')
const loading = ref(false)

async function handleRegister() {
  error.value = ''
  if (password.value !== confirmPassword.value) {
    error.value = '两次密码不一致'
    return
  }
  loading.value = true
  try {
    await auth.register(username.value, email.value, password.value)
    router.push('/info')
  } catch (e: any) {
    error.value = e.message
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="min-h-screen flex items-center justify-center px-4" style="background: linear-gradient(135deg, #eff6ff 0%, #dbeafe 50%, #f8fafc 100%)">
    <n-card class="w-full max-w-sm" style="border-radius:16px;box-shadow:0 4px 24px rgba(0,0,0,0.06)">
      <div class="text-center mb-6">
        <div class="text-3xl mb-2">🔥</div>
        <h1 class="text-xl font-extrabold" style="color:#1e40af">Resume <span style="color:#3b82f6">Forge</span></h1>
        <p class="text-sm text-slate-400 mt-1">创建账号</p>
      </div>

      <div class="space-y-4">
        <n-input v-model:value="username" placeholder="用户名" size="large" />
        <n-input v-model:value="email" placeholder="邮箱" size="large" />
        <n-input v-model:value="password" type="password" placeholder="密码" size="large" />
        <n-input v-model:value="confirmPassword" type="password" placeholder="确认密码" size="large" @keyup.enter="handleRegister" />
        <div v-if="error" class="text-sm text-red-500 text-center">{{ error }}</div>
        <n-button type="primary" block size="large" :loading="loading" @click="handleRegister">注册</n-button>
      </div>

      <div class="text-center mt-4">
        <router-link to="/login" class="text-sm text-blue-500 hover:text-blue-600">已有账号？登录</router-link>
      </div>
    </n-card>
  </div>
</template>
