<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { NButton, NInput, NCard } from 'naive-ui'
import { useAuthStore } from '../stores/auth'

const router = useRouter()
const auth = useAuthStore()

const email = ref('')
const password = ref('')
const error = ref('')
const loading = ref(false)

async function handleLogin() {
  error.value = ''
  loading.value = true
  try {
    await auth.login(email.value, password.value)
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
        <p class="text-sm text-slate-400 mt-1">简历熔炉 · 登录</p>
      </div>

      <div class="space-y-4">
        <n-input v-model:value="email" placeholder="邮箱" size="large" />
        <n-input v-model:value="password" type="password" placeholder="密码" size="large" @keyup.enter="handleLogin" />
        <div v-if="error" class="text-sm text-red-500 text-center">{{ error }}</div>
        <n-button type="primary" block size="large" :loading="loading" @click="handleLogin">登录</n-button>
      </div>

      <div class="text-center mt-4">
        <router-link to="/register" class="text-sm text-blue-500 hover:text-blue-600">还没有账号？注册</router-link>
      </div>
    </n-card>
  </div>
</template>
