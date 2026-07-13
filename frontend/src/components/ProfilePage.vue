<script setup>
import { ref, reactive, nextTick, onMounted } from 'vue'
import { user, t, convs } from '../store.js'
import { put } from '../api.js'

const emit = defineEmits(['close'])

const pf = reactive({
  nickname: '', real_name: '', gender: '', birthday: '',
  bio: '', ai_address: '', avatar: '', avatar_color: ''
})

const oldPw = ref('')
const newPw = ref('')
const confirmPw = ref('')
const profileMsg = ref('')
const profileMsgOk = ref(false)
const fileInput = ref(null)

const presets = ['🐱','🐶','🦊','🐼','🦁','🐸','🐧','🦉','🐯','🐰','🐻','🐲']
const colors = ['#5b57d2','#e54d4d','#1a7f37','#f59e0b','#0ea5e9','#ec4899','#8b5cf6','#14b8a6']

function syncPf() {
  pf.nickname = user.value.nickname || ''
  pf.real_name = user.value.real_name || ''
  pf.gender = user.value.gender || ''
  pf.birthday = user.value.birthday || ''
  pf.bio = user.value.bio || ''
  pf.ai_address = user.value.ai_address || ''
  pf.avatar = user.value.avatar || ''
  pf.avatar_color = user.value.avatar_color || ''
}

function isImgAvatar(v) {
  return v && v.startsWith('data:')
}

function avBgStyle(color) {
  return { background: color }
}

function pickAvatarFile() {
  fileInput.value?.click()
}

function onAvatarFile(e) {
  const file = e.target.files?.[0]
  if (!file) return
  if (file.size > 200 * 1024) {
    profileMsg.value = t('avatarTooBig')
    profileMsgOk.value = false
    return
  }
  const reader = new FileReader()
  reader.onload = () => {
    setAvatar(reader.result)
  }
  reader.readAsDataURL(file)
  e.target.value = ''
}

async function setAvatar(v) {
  pf.avatar = v
  profileMsg.value = ''
  profileMsgOk.value = false
  const d = await put('/auth/profile', { avatar: v })
  if (d) {
    user.value.avatar = v
    profileMsg.value = t('saved')
    profileMsgOk.value = true
  } else {
    profileMsg.value = 'Save failed'
    profileMsgOk.value = false
  }
}

async function setAvatarColor(v) {
  pf.avatar_color = v
  profileMsg.value = ''
  profileMsgOk.value = false
  const d = await put('/auth/profile', { avatar_color: v })
  if (d) {
    user.value.avatar_color = v
    profileMsg.value = t('saved')
    profileMsgOk.value = true
  } else {
    profileMsg.value = 'Save failed'
    profileMsgOk.value = false
  }
}

async function removeAvatar() {
  pf.avatar = ''
  pf.avatar_color = ''
  profileMsg.value = ''
  profileMsgOk.value = false
  const d = await put('/auth/profile', { avatar: '', avatar_color: '' })
  if (d) {
    user.value.avatar = ''
    user.value.avatar_color = ''
    profileMsg.value = t('saved')
    profileMsgOk.value = true
  } else {
    profileMsg.value = 'Save failed'
    profileMsgOk.value = false
  }
}

async function saveProfileField(fields) {
  profileMsg.value = ''
  profileMsgOk.value = false
  const d = await put('/auth/profile', fields)
  if (d) {
    Object.assign(user.value, fields)
    profileMsg.value = t('saved')
    profileMsgOk.value = true
  } else {
    profileMsg.value = 'Save failed'
    profileMsgOk.value = false
  }
}

function saveProfileText() {
  saveProfileField({
    nickname: pf.nickname,
    real_name: pf.real_name,
    gender: pf.gender,
    birthday: pf.birthday,
    bio: pf.bio,
    ai_address: pf.ai_address
  })
}

async function changePassword() {
  profileMsg.value = ''
  profileMsgOk.value = false
  if (!oldPw.value || !newPw.value || !confirmPw.value) {
    profileMsg.value = 'Please fill all fields'
    return
  }
  if (newPw.value !== confirmPw.value) {
    profileMsg.value = t('pwMismatch') || 'Passwords do not match'
    return
  }
  const d = await put('/auth/password', {
    old_password: oldPw.value,
    new_password: newPw.value
  })
  if (d) {
    profileMsg.value = t('pwChanged') || 'Password changed'
    profileMsgOk.value = true
    oldPw.value = ''
    newPw.value = ''
    confirmPw.value = ''
  } else {
    profileMsg.value = 'Save failed'
    profileMsgOk.value = false
  }
}

onMounted(() => {
  syncPf()
})
</script>

<template>
  <div class="top-bar">
    <button class="btn" @click="$emit('close')" title="Back" style="padding:.35rem .5rem;width:34px;height:34px">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="18" height="18" stroke-linecap="round" stroke-linejoin="round"><polyline points="15 18 9 12 15 6"/></svg>
    </button>
    <span style="font-size:16px;font-weight:600;margin-left:8px">{{ t('profileTitle') }}</span>
    <div style="flex:1"></div>
    <button class="btn primary" @click="saveProfileText">{{ t('save') || 'Save' }}</button>
  </div>

  <div class="profile-page">
    <div class="profile-inner">

      <div class="profile-hero">
        <div class="avatar-lg" @click="pickAvatarFile">
          <img v-if="isImgAvatar(pf.avatar)" :src="pf.avatar" alt="avatar" />
          <span v-else-if="pf.avatar" style="font-size:42px">{{ pf.avatar }}</span>
          <span v-else style="font-size:42px">{{ (pf.nickname || pf.email || 'U')[0].toUpperCase() }}</span>
          <div class="av-overlay">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="22" height="22" stroke-linecap="round" stroke-linejoin="round"><path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z"/><circle cx="12" cy="13" r="4"/></svg>
          </div>
        </div>
        <input ref="fileInput" type="file" accept="image/*" style="display:none" @change="onAvatarFile" />
        <div class="avatar-hint">{{ t('avatarHint') }}</div>
        <div class="avatar-sub-actions">
          <button class="btn" @click="pickAvatarFile" style="font-size:12px;padding:.3rem .6rem">{{ t('uploadImg') }}</button>
          <button class="btn" @click="removeAvatar" v-if="pf.avatar" style="font-size:12px;padding:.3rem .6rem">{{ t('removeAvatar') }}</button>
        </div>
      </div>

      <div class="profile-card">
        <div class="profile-card-title">{{ t('avatarStyle') }}</div>
        <div class="preset-grid">
          <button
            v-for="p in presets" :key="p"
            class="preset-item"
            :class="{ active: pf.avatar === p && !pf.avatar_color }"
            @click="setAvatar(p)"
          >{{ p }}</button>
        </div>
        <div class="color-grid">
          <button
            v-for="c in colors" :key="c"
            class="color-dot"
            :class="{ active: pf.avatar_color === c }"
            :style="avBgStyle(c)"
            @click="setAvatarColor(c)"
          >
            <svg v-if="pf.avatar_color === c" viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="3" width="14" height="14" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>
          </button>
        </div>
      </div>

      <div class="profile-card">
        <div class="profile-card-title">{{ t('basicInfo') || 'Basic Info' }}</div>
        <div class="profile-field">
          <label>{{ t('nickname') || 'Nickname' }}</label>
          <input class="profile-input" v-model="pf.nickname" maxlength="30" />
        </div>
        <div class="profile-field">
          <label>{{ t('realName') || 'Real Name' }}</label>
          <input class="profile-input" v-model="pf.real_name" maxlength="30" />
        </div>
        <div class="profile-field">
          <label>{{ t('gender') || 'Gender' }}</label>
          <div class="gender-pills">
            <button class="gender-pill" :class="{ active: pf.gender === 'male' }" @click="pf.gender = 'male'">{{ t('genderMale') }}</button>
            <button class="gender-pill" :class="{ active: pf.gender === 'female' }" @click="pf.gender = 'female'">{{ t('genderFemale') }}</button>
            <button class="gender-pill" :class="{ active: pf.gender === 'other' }" @click="pf.gender = 'other'">{{ t('genderOther') }}</button>
            <button class="gender-pill" :class="{ active: pf.gender === 'private' || !pf.gender }" @click="pf.gender = 'private'">{{ t('genderPrivate') }}</button>
          </div>
        </div>
        <div class="profile-field">
          <label>{{ t('birthday') || 'Birthday' }}</label>
          <input class="profile-input" type="date" v-model="pf.birthday" />
        </div>
      </div>

      <div class="profile-card">
        <div class="profile-card-title">{{ t('personalization') || 'Personalization' }}</div>
        <div class="profile-field">
          <label>{{ t('bio') || 'Bio' }} <span class="char-count">{{ (pf.bio || '').length }}/100</span></label>
          <textarea class="profile-input" v-model="pf.bio" maxlength="100" rows="3" style="resize:vertical;min-height:72px"></textarea>
        </div>
        <div class="profile-field">
          <label>{{ t('aiAddress') || 'AI Address' }} <span class="char-count">{{ (pf.ai_address || '').length }}/30</span></label>
          <input class="profile-input" v-model="pf.ai_address" maxlength="30" />
        </div>
      </div>

      <div class="profile-card">
        <div class="profile-card-title">{{ t('accountInfo') || 'Account Info' }}</div>
        <div class="info-list">
          <div class="info-line">
            <span class="info-label">{{ t('email') || 'Email' }}</span>
            <span class="info-value">{{ user.email }}</span>
          </div>
          <div class="info-line">
            <span class="info-label">{{ t('role') || 'Role' }}</span>
            <span class="info-value"><span class="tag" :class="{ admin: user.role === 'admin' }">{{ user.role || 'user' }}</span></span>
          </div>
          <div class="info-line">
            <span class="info-label">{{ t('createdAt') || 'Created' }}</span>
            <span class="info-value">{{ user.created_at?.slice(0, 10) }}</span>
          </div>
          <div class="info-line">
            <span class="info-label">{{ t('chatCount') || 'Chats' }}</span>
            <span class="info-value">{{ convs.length }}</span>
          </div>
        </div>
      </div>

      <div class="profile-card">
        <div class="profile-card-title">{{ t('changePassword') || 'Change Password' }}</div>
        <div class="profile-field">
          <label>{{ t('oldPassword') || 'Old Password' }}</label>
          <input class="profile-input" type="password" v-model="oldPw" placeholder="·······" />
        </div>
        <div class="profile-field">
          <label>{{ t('newPassword') || 'New Password' }}</label>
          <input class="profile-input" type="password" v-model="newPw" placeholder="·······" />
        </div>
        <div class="profile-field">
          <label>{{ t('confirmPassword') || 'Confirm Password' }}</label>
          <input class="profile-input" type="password" v-model="confirmPw" placeholder="·······" />
        </div>
        <button class="btn primary wide" @click="changePassword">{{ t('changePassword') || 'Change Password' }}</button>
      </div>

      <div class="profile-actions">
        <div class="profile-msg" v-if="profileMsg" :style="{ color: profileMsgOk ? '#1a7f37' : 'var(--danger)' }">{{ profileMsg }}</div>
      </div>

    </div>
  </div>
</template>

<style scoped>
.top-bar {
  display: flex;
  align-items: center;
  padding: 8px 12px;
  border-bottom: 1px solid var(--border-strong);
  background: var(--surface);
  flex-shrink: 0;
}

.profile-page {
  flex: 1;
  overflow-y: auto;
  padding: 24px 16px;
}

.profile-inner {
  max-width: 560px;
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  gap: 20px;
  padding-bottom: 40px;
}

.profile-hero {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
  padding: 24px 0 12px;
}

.avatar-lg {
  width: 96px;
  height: 96px;
  border-radius: 50%;
  background: var(--accent-soft);
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
  cursor: pointer;
  overflow: hidden;
  transition: box-shadow .2s var(--ease);
  border: 2px solid var(--border);
}

.avatar-lg:hover {
  box-shadow: 0 0 0 4px var(--accent-soft);
}

.avatar-lg img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.av-overlay {
  position: absolute;
  inset: 0;
  background: rgba(0, 0, 0, 0.4);
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  opacity: 0;
  transition: opacity .2s var(--ease);
  border-radius: 50%;
}

.avatar-lg:hover .av-overlay {
  opacity: 1;
}

.avatar-hint {
  font-size: 12px;
  color: var(--text-muted);
}

.avatar-sub-actions {
  display: flex;
  gap: 8px;
}

.profile-card {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  padding: 20px;
}

.profile-card-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-secondary);
  text-transform: uppercase;
  letter-spacing: .5px;
  margin-bottom: 16px;
}

.profile-field {
  margin-bottom: 14px;
}

.profile-field:last-child {
  margin-bottom: 0;
}

.profile-field label {
  display: block;
  font-size: 12.5px;
  font-weight: 500;
  color: var(--text-secondary);
  margin-bottom: 6px;
}

.char-count {
  font-weight: 400;
  color: var(--text-muted);
  margin-left: 6px;
}

.profile-input {
  width: 100%;
  padding: .6rem .75rem;
  border: 1px solid var(--border-strong);
  border-radius: 8px;
  font-size: 13.5px;
  font-family: var(--font);
  background: var(--bg);
  color: var(--text);
  outline: none;
  box-sizing: border-box;
  transition: border-color .2s var(--ease), box-shadow .2s var(--ease);
}

.profile-input:focus {
  border-color: var(--accent);
  box-shadow: 0 0 0 3px var(--accent-soft);
}

.gender-pills {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.gender-pill {
  padding: 6px 16px;
  border: 1px solid var(--border-strong);
  border-radius: 20px;
  background: var(--bg);
  color: var(--text-secondary);
  font-size: 13px;
  font-family: var(--font);
  cursor: pointer;
  transition: all .2s var(--ease);
}

.gender-pill:hover {
  border-color: var(--accent);
  color: var(--accent);
}

.gender-pill.active {
  background: var(--accent);
  color: #fff;
  border-color: var(--accent);
}

.preset-grid {
  display: grid;
  grid-template-columns: repeat(6, 1fr);
  gap: 8px;
  margin-bottom: 16px;
}

.preset-item {
  width: 100%;
  aspect-ratio: 1;
  border: 2px solid var(--border);
  border-radius: var(--radius);
  background: var(--bg);
  font-size: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all .2s var(--ease);
  font-family: var(--font);
}

.preset-item:hover {
  border-color: var(--accent);
  background: var(--accent-soft);
}

.preset-item.active {
  border-color: var(--accent);
  background: var(--accent-soft);
}

.color-grid {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}

.color-dot {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  border: 3px solid transparent;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all .2s var(--ease);
  padding: 0;
}

.color-dot:hover {
  transform: scale(1.15);
}

.color-dot.active {
  border-color: var(--text);
  transform: scale(1.1);
}

.info-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.info-line {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 4px 0;
}

.info-label {
  font-size: 13px;
  color: var(--text-secondary);
}

.info-value {
  font-size: 13px;
  color: var(--text);
  font-weight: 500;
}

.tag {
  display: inline-block;
  padding: 2px 10px;
  border-radius: 12px;
  font-size: 11.5px;
  font-weight: 600;
  background: var(--accent-soft);
  color: var(--accent);
  text-transform: uppercase;
  letter-spacing: .3px;
}

.tag.admin {
  background: var(--danger-soft);
  color: var(--danger);
}

.profile-actions {
  display: flex;
  justify-content: center;
}

.profile-msg {
  font-size: 13px;
  text-align: center;
  padding: 8px 16px;
  border-radius: 8px;
  background: var(--bg);
}

@media (max-width: 768px) {
  .preset-grid { grid-template-columns: repeat(4, 1fr); }
  .profile-page { padding: 16px 8px; }
  .profile-card { padding: 14px; }
  .profile-hero { padding: 16px 0 8px; }
  .avatar-lg { width: 80px; height: 80px; }
}
</style>
