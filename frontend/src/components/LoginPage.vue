<template>
  <div class="login-page">
    <div class="login-card">
      <div style="display:flex;justify-content:center;margin-bottom:.5rem">
        <svg viewBox="0 0 40 40" width="48" height="48" fill="none">
          <rect width="40" height="40" rx="10" style="fill:var(--accent)" />
          <path d="M9 29V12l11 12 11-12v17" stroke="#fff" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" />
          <circle cx="30" cy="9" r="2" fill="#fff" opacity="0.5" />
        </svg>
      </div>
      <h1>MeiKen AI</h1>
      <div class="sub">
        {{ loginMode === 'reset' ? t('resetSub') : loginMode === 'forgot' ? t('forgotSub') : (loginMode === 'login' ? t('loginSub') : t('regSub')) }}
      </div>

      <div v-if="loginMode === 'forgot'">
        <div class="field">
          <label>{{ t('email') }}</label>
          <input v-model="authEmail" type="text" placeholder="you@email.com" />
        </div>
        <button class="btn primary" @click="doForgot" :disabled="authBusy || !authEmail">
          {{ authBusy ? '…' : t('sendLink') }}
        </button>
        <div class="err" v-if="authErr" :style="{ color: forgotOk ? '#1a7f37' : '' }">{{ authErr }}</div>
        <div v-if="forgotLink" style="margin-top:.5rem;padding:.5rem;background:var(--code-bg);border:1px solid var(--border);border-radius:8px;font-size:12px;word-break:break-all;color:var(--text-secondary)">
          <div style="font-weight:600;color:var(--text);margin-bottom:.3rem">开发模式 — 点击链接重置</div>
          <a :href="forgotLink" style="color:var(--accent)">{{ forgotLink }}</a>
        </div>
      </div>

      <div v-if="loginMode === 'reset'">
        <div class="field">
          <label>{{ t('newPassword') }}</label>
          <input v-model="authPw" type="password" placeholder="·······" />
        </div>
        <div class="field">
          <label>{{ t('confirmPassword') }}</label>
          <input v-model="authPw2" type="password" placeholder="·······" />
        </div>
        <button class="btn primary" @click="doReset" :disabled="authBusy || !authPw || authPw !== authPw2">
          {{ authBusy ? '…' : t('reset') }}
        </button>
      </div>

      <div v-if="loginMode !== 'forgot' && loginMode !== 'reset'">
        <div class="field">
          <label>{{ loginMode === 'login' ? t('emailOrNick') : t('email') }}</label>
          <input v-model="authEmail" type="text" :placeholder="loginMode === 'login' ? t('emailOrNickPh') : 'you@email.com'" />
        </div>
        <div class="field">
          <label>{{ t('password') }}</label>
          <input v-model="authPw" type="password" placeholder="·······" />
        </div>
        <div v-if="loginMode === 'register'" class="field">
          <label>{{ t('nickname') }}</label>
          <input v-model="authNick" type="text" :placeholder="t('nicknamePh')" />
        </div>
        <button class="btn primary" @click="doAuth" :disabled="authBusy">
          {{ authBusy ? '…' : (loginMode === 'login' ? t('login') : t('register')) }}
        </button>
      </div>

      <div class="err" v-if="authErr && loginMode !== 'forgot'">{{ authErr }}</div>

      <div class="switch">
        <div v-if="loginMode === 'forgot' || loginMode === 'reset'">
          <a @click="switchTo('login')">{{ t('back') }}</a>
        </div>
        <div v-else>
          {{ loginMode === 'login' ? t('noAccount') : t('hasAccount') }}
          <a @click="loginMode = loginMode === 'login' ? 'register' : 'login'; authErr = ''">
            {{ loginMode === 'login' ? t('goRegister') : t('goLogin') }}
          </a>
          <span v-if="loginMode === 'login'" style="margin:0 6px;color:var(--text-muted)">|</span>
          <a v-if="loginMode === 'login'" @click="switchTo('forgot')">{{ t('forgotPassword') }}</a>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { authed, user, t, loadConvs } from '../store.js'

const isLocal = window.location.hostname === '127.0.0.1' || window.location.hostname === 'localhost'
const API = import.meta.env.DEV
  ? '/api'
  : (isLocal ? 'http://127.0.0.1:8000/api' : window.location.origin + '/api')

const loginMode = ref('login')
const authEmail = ref('')
const authPw = ref('')
const authPw2 = ref('')
const authNick = ref('')
const authBusy = ref(false)
const authErr = ref('')
const forgotOk = ref(false)
const forgotLink = ref('')
const resetToken = ref('')

function switchTo(mode) {
  loginMode.value = mode
  authErr.value = ''
  forgotOk.value = false
  forgotLink.value = ''
  if (mode === 'forgot') authEmail.value = ''
}

async function doAuth() {
  authErr.value = ''
  authBusy.value = true
  forgotOk.value = false
  forgotLink.value = ''
  const endpoint = loginMode.value === 'login' ? '/auth/login' : '/auth/register'
  const body = { email: authEmail.value, password: authPw.value }
  if (loginMode.value === 'register') body.nickname = authNick.value
  try {
    const r = await fetch(API + endpoint, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include',
      body: JSON.stringify(body)
    })
    const d = await r.json()
    if (!r.ok) { authErr.value = d.detail || 'Error'; authBusy.value = false; return }
    user.value = d.user
    authed.value = true
    await loadConvs()
    authBusy.value = false
  } catch (e) { authErr.value = 'Connection error: ' + e.message; authBusy.value = false }
}

async function doForgot() {
  authErr.value = ''
  forgotOk.value = false
  forgotLink.value = ''
  authBusy.value = true
  try {
    const r = await fetch(API + '/auth/forgot-password', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email: authEmail.value })
    })
    const d = await r.json()
    if (!r.ok) { authErr.value = d.detail || 'Error' }
    else { forgotOk.value = true; if (d.link) forgotLink.value = d.link; else authErr.value = 'Reset link sent — check your inbox' }
  } catch (e) { authErr.value = e.message }
  authBusy.value = false
}

async function doReset() {
  authErr.value = ''
  authBusy.value = true
  try {
    const r = await fetch(API + '/auth/reset-password', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ token: resetToken.value, password: authPw.value })
    })
    if (!r.ok) { const d = await r.json(); authErr.value = d.detail || 'Error' }
    else {
      authErr.value = 'Password reset — please login'
      loginMode.value = 'login'
      authPw.value = ''
      authPw2.value = ''
      resetToken.value = ''
      window.location.hash = ''
    }
  } catch (e) { authErr.value = e.message }
  authBusy.value = false
}

onMounted(() => {
  const hash = window.location.hash
  if (hash.startsWith('#reset')) {
    const params = new URLSearchParams(hash.slice(hash.indexOf('?')))
    resetToken.value = params.get('token') || ''
    loginMode.value = 'reset'
  }
})
</script>

<style scoped>
.login-page {
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100vh;
  background: var(--bg);
  padding: 2rem;
}

.login-card {
  width: 100%;
  max-width: 400px;
  padding: 2.5rem 2rem;
  border-radius: var(--radius-lg);
  background: var(--surface);
  border: 1px solid var(--border);
  box-shadow: var(--shadow-lg);
  animation: fadeSlide .4s var(--spring);
}
@keyframes fadeSlide { from { opacity: 0; transform: translateY(36px); } to { opacity: 1; transform: translateY(0); } }

.login-card h1 {
  text-align: center;
  font-size: 22px;
  font-weight: 700;
  margin-bottom: .3rem;
  letter-spacing: -.3px;
}

.sub {
  text-align: center;
  color: var(--text-secondary);
  font-size: 13.5px;
  margin-bottom: 1.5rem;
}

.field {
  margin-bottom: 1rem;
}

.field label {
  display: block;
  font-size: 12.5px;
  font-weight: 600;
  color: var(--text-secondary);
  margin-bottom: .3rem;
}

.field input {
  width: 100%;
  padding: .65rem .85rem;
  border-radius: 9px;
  border: 1.5px solid var(--border-strong);
  background: var(--bg);
  color: var(--text);
  font-size: 14px;
  font-family: var(--font);
  outline: none;
  transition: border-color .2s;
}

.field input:focus {
  border-color: var(--accent);
}

.btn.primary {
  width: 100%;
  margin-top: .5rem;
}

.err {
  color: var(--danger);
  font-size: 12.5px;
  text-align: center;
  margin-top: .5rem;
}

.switch {
  text-align: center;
  margin-top: 1rem;
  font-size: 13px;
  color: var(--text-secondary);
}

.switch a {
  color: var(--accent);
  cursor: pointer;
  font-weight: 550;
}

.switch span {
  margin: 0 6px;
  color: var(--text-muted);
}
</style>
