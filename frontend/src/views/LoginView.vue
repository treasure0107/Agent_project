<template>
  <div class="login-container">
    <div class="login-form">
      <h1 class="login-title">智能医疗助手</h1>
      <h2 class="login-subtitle">登录</h2>

      <el-form :model="loginForm" :rules="rules" ref="loginFormRef" label-width="80px">
        <el-form-item label="账号" prop="username">
          <el-input v-model="loginForm.username" placeholder="用户名或邮箱" />
        </el-form-item>
        <el-form-item label="密码" prop="password">
          <el-input v-model="loginForm.password" type="password" placeholder="请输入密码" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" class="login-button" @click="handleLogin" :loading="loading">
            登录
          </el-button>
          <el-button type="default" class="register-button" @click="goToRegister"> 注册 </el-button>
        </el-form-item>
      </el-form>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import axios from 'axios'

const router = useRouter()
const loginFormRef = ref()
const loading = ref(false)

const backendUrl = import.meta.env.VITE_BACKEND_URL || 'http://localhost:8000'

// 默认演示账号（请先在 Navicat 执行 scripts/seed_demo_user.sql）
const loginForm = reactive({
  username: 'demo',
  password: 'Demo@123456',
})

const rules = {
  username: [{ required: true, message: '请输入用户名或邮箱', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }],
}

const getErrorMessage = (error) => {
  const detail = error.response?.data?.detail
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail)) {
    return detail.map((item) => item.msg || JSON.stringify(item)).join('; ')
  }
  return '登录失败'
}

const handleLogin = async () => {
  if (!loginFormRef.value) return

  try {
    await loginFormRef.value.validate()
    loading.value = true

    const response = await axios.post(`${backendUrl}/api/auth/login`, {
      account: loginForm.username,
      password: loginForm.password,
    })

    localStorage.setItem('token', response.data.access_token)
    localStorage.setItem(
      'user',
      JSON.stringify({
        id: response.data.user.id,
        username: response.data.user.username,
        email: response.data.user.email,
      }),
    )

    ElMessage.success('登录成功')
    router.push('/')
  } catch (error) {
    if (error.response) {
      ElMessage.error(getErrorMessage(error))
    } else {
      ElMessage.error('网络错误，请确认后端已启动且 MySQL 隧道已打开')
    }
  } finally {
    loading.value = false
  }
}

const goToRegister = () => {
  router.push('/register')
}
</script>

<style scoped>
.login-container {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 100vh;
  background: linear-gradient(135deg, #1a202c 0%, #2d3748 100%);
  padding: 20px;
}

.login-form {
  background: rgba(255, 255, 255, 0.1);
  backdrop-filter: blur(10px);
  border-radius: 16px;
  padding: 40px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
  border: 1px solid rgba(255, 255, 255, 0.1);
  width: 100%;
  max-width: 400px;
}

.login-title {
  font-size: 24px;
  font-weight: 700;
  color: #fff;
  text-align: center;
  margin-bottom: 8px;
}

.login-subtitle {
  font-size: 18px;
  color: #a0aec0;
  text-align: center;
  margin-bottom: 32px;
}

.login-button {
  width: 100%;
  margin-bottom: 16px;
  background: linear-gradient(90deg, #3182ce, #4299e1);
  border: none;
  height: 44px;
  font-size: 16px;
  font-weight: 600;
}

.register-button {
  width: 100%;
  background: transparent;
  border: 1px solid #4299e1;
  color: #4299e1;
  height: 44px;
  font-size: 16px;
  font-weight: 600;
  margin: 0 auto 0 0;
}

.el-input__wrapper {
  background: rgba(255, 255, 255, 0.1);
  border: 1px solid rgba(255, 255, 255, 0.2);
  border-radius: 8px;
}

.el-input__inner {
  color: #fff;
}

.el-input__placeholder {
  color: rgba(255, 255, 255, 0.5);
}

.el-form-item__label {
  color: #a0aec0;
}

.el-form-item.is-error .el-input__wrapper {
  border-color: #f56565;
}

.el-form-item__error {
  color: #f56565;
}
</style>
