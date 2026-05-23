<script setup>
import { computed, onMounted, ref } from "vue";
import { adminDeleteUser, adminListConversations, adminGetConversationMessages, adminListUsers, adminUpdatePassword, getCurrentUser, login, setToken } from "./api.js";

// ===== Auth state =====
const username = ref("");
const password = ref("");
const authLoading = ref(false);
const authenticated = ref(false);
const currentUser = ref(null);
const authError = ref("");

// ===== Admin state =====
const users = ref([]);
const loading = ref(false);
const adminError = ref("");

// ===== Password modal =====
const showPasswordModal = ref(false);
const passwordTargetUser = ref(null);
const newPassword = ref("");
const passwordLoading = ref(false);
const passwordError = ref("");

// ===== Chat history views =====
const chatViewUser = ref(null);          // user whose conversations we are browsing
const conversations = ref([]);
const convLoading = ref(false);
const convError = ref("");
const chatMessages = ref([]);
const chatTitle = ref("");
const msgLoading = ref(false);

// ===== Auth =====
const canLogin = computed(() => username.value.trim().length >= 3 && password.value.trim().length >= 6);

async function handleLogin() {
  const name = username.value.trim();
  const secret = password.value.trim();
  if (!canLogin.value || authLoading.value) return;
  authLoading.value = true;
  authError.value = "";
  try {
    const resp = await login(name, secret);
    setToken(resp?.data?.access_token || "");
    currentUser.value = resp?.data?.user || null;
    authenticated.value = true;
    password.value = "";
    await loadUsers();
  } catch (error) {
    authError.value = error.message;
  } finally {
    authLoading.value = false;
  }
}

function handleLogout() {
  setToken("");
  authenticated.value = false;
  currentUser.value = null;
  users.value = [];
}

// ===== Admin =====
async function loadUsers() {
  loading.value = true;
  adminError.value = "";
  try {
    const resp = await adminListUsers();
    users.value = resp?.data?.users || [];
  } catch (error) {
    adminError.value = error.message;
  } finally {
    loading.value = false;
  }
}

async function handleDeleteUser(userId) {
  const user = users.value.find((u) => u.id === userId);
  if (!user) return;
  if (!confirm(`确定删除用户"${user.username}"（ID: ${userId}）？此操作不可恢复。`)) return;
  try {
    await adminDeleteUser(userId);
    users.value = users.value.filter((u) => u.id !== userId);
  } catch (error) {
    adminError.value = error.message;
  }
}

function openPasswordModal(user) {
  passwordTargetUser.value = user;
  newPassword.value = "";
  passwordError.value = "";
  passwordLoading.value = false;
  showPasswordModal.value = true;
}

function closePasswordModal() {
  showPasswordModal.value = false;
  passwordTargetUser.value = null;
  newPassword.value = "";
  passwordError.value = "";
}

async function handleUpdatePassword() {
  if (!passwordTargetUser.value || newPassword.value.trim().length < 6 || passwordLoading.value) return;
  passwordLoading.value = true;
  passwordError.value = "";
  try {
    await adminUpdatePassword(passwordTargetUser.value.id, newPassword.value.trim());
    closePasswordModal();
    adminError.value = `密码已更新`;
  } catch (error) {
    passwordError.value = error.message;
  } finally {
    passwordLoading.value = false;
  }
}

// ===== Chat history =====
function openChatView(user) {
  chatViewUser.value = user;
  conversations.value = [];
  chatMessages.value = [];
  chatTitle.value = "";
  convError.value = "";
  loadConversations(user.id);
}

function closeChatView() {
  chatViewUser.value = null;
  conversations.value = [];
  chatMessages.value = [];
  chatTitle.value = "";
  convError.value = "";
}

async function loadConversations(userId) {
  convLoading.value = true;
  convError.value = "";
  try {
    const resp = await adminListConversations(userId);
    conversations.value = resp?.data?.conversations || [];
  } catch (error) {
    convError.value = error.message;
  } finally {
    convLoading.value = false;
  }
}

async function openConversation(conv) {
  if (!chatViewUser.value) return;
  msgLoading.value = true;
  chatTitle.value = conv.title;
  chatMessages.value = [];
  try {
    const resp = await adminGetConversationMessages(chatViewUser.value.id, conv.id);
    chatMessages.value = resp?.data?.messages || [];
  } catch (error) {
    convError.value = error.message;
  } finally {
    msgLoading.value = false;
  }
}

function backToConversations() {
  chatMessages.value = [];
  chatTitle.value = "";
}

function formatDate(dateStr) {
  const d = new Date(dateStr);
  return d.toLocaleString();
}

// ===== Init =====
async function restoreSession() {
  try {
    const resp = await getCurrentUser();
    currentUser.value = resp?.data || null;
    authenticated.value = Boolean(currentUser.value);
    if (authenticated.value) {
      await loadUsers();
    }
  } catch {
    setToken("");
    authenticated.value = false;
    currentUser.value = null;
  }
}

onMounted(restoreSession);
</script>

<template>
  <div class="app">
    <!-- Login -->
    <main v-if="!authenticated" class="login-page">
      <div class="login-card">
        <div class="login-icon">🔧</div>
        <h1 class="login-title">管理后台</h1>
        <p class="login-subtitle">LangWeave 用户管理系统</p>

        <div v-if="authError" class="msg-bar error">{{ authError }}</div>

        <form class="login-form" @submit.prevent="handleLogin">
          <div class="field">
            <input
              v-model="username"
              type="text"
              autocomplete="username"
              placeholder="管理员用户名"
              class="input"
            />
          </div>
          <div class="field">
            <input
              v-model="password"
              type="password"
              autocomplete="current-password"
              placeholder="密码"
              class="input"
            />
          </div>
          <button class="btn btn-primary btn-block" type="submit" :disabled="!canLogin || authLoading">
            {{ authLoading ? "登录中..." : "登录" }}
          </button>
        </form>
      </div>
    </main>

    <!-- Admin Dashboard -->
    <main v-else class="admin-page">
      <header class="admin-header">
        <div class="admin-header-left">
          <span class="admin-header-title">用户管理</span>
        </div>
        <div class="admin-header-right">
          <span class="admin-user">{{ currentUser?.username }}</span>
          <button class="btn ghost" type="button" @click="handleLogout">退出</button>
        </div>
      </header>

      <div class="admin-content">
        <div v-if="loading" class="load-hint">加载中...</div>

        <div v-else-if="adminError" class="msg-bar error">{{ adminError }}</div>

        <table v-else-if="users.length > 0" class="user-table">
          <thead>
            <tr>
              <th>ID</th>
              <th>用户名</th>
              <th>对话数</th>
              <th>注册时间</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="u in users" :key="u.id">
              <td>{{ u.id }}</td>
              <td>{{ u.username }}</td>
              <td>{{ u.conversation_count }}</td>
              <td>{{ formatDate(u.created_at) }}</td>
              <td>
                <button
                  class="btn ghost"
                  type="button"
                  @click="openChatView(u)"
                  title="查看聊天记录"
                >
                  聊天
                </button>
                <button
                  class="btn ghost"
                  type="button"
                  @click="openPasswordModal(u)"
                  title="修改密码"
                >
                  改密
                </button>
                <button
                  class="btn ghost danger"
                  type="button"
                  :disabled="u.id === currentUser?.id"
                  :title="u.id === currentUser?.id ? '不能删除自己' : '删除用户'"
                  @click="handleDeleteUser(u.id)"
                >
                  {{ u.id === currentUser?.id ? "当前账号" : "删除" }}
                </button>
              </td>
            </tr>
          </tbody>
        </table>

        <div v-else class="load-hint">暂无注册用户</div>
      </div>

      <!-- Password Modal -->
      <Teleport to="body">
        <div v-if="showPasswordModal" class="modal-overlay" @click.self="closePasswordModal">
          <div class="modal-card">
            <h3 class="modal-title">修改密码</h3>
            <p class="modal-desc">用户：{{ passwordTargetUser?.username }}</p>

            <div v-if="passwordError" class="msg-bar error">{{ passwordError }}</div>

            <form class="modal-form" @submit.prevent="handleUpdatePassword">
              <div class="field">
                <input
                  v-model="newPassword"
                  type="password"
                  autocomplete="new-password"
                  placeholder="新密码（至少6位）"
                  class="input"
                />
              </div>
              <div class="modal-actions">
                <button class="btn ghost" type="button" @click="closePasswordModal">取消</button>
                <button
                  class="btn btn-primary"
                  type="submit"
                  :disabled="newPassword.trim().length < 6 || passwordLoading"
                >
                  {{ passwordLoading ? "提交中..." : "确认修改" }}
                </button>
              </div>
            </form>
          </div>
        </div>
      </Teleport>

      <!-- Chat History View -->
      <Teleport to="body">
        <div v-if="chatViewUser" class="modal-overlay" @click.self="closeChatView">
          <div class="modal-card chat-card">
            <!-- Header -->
            <div class="chat-header">
              <button class="btn ghost" type="button" @click="closeChatView">← 返回</button>
              <span class="chat-header-title">
                {{ chatTitle || chatViewUser?.username + ' 的对话' }}
              </span>
              <span></span>
            </div>

            <!-- Messages view -->
            <div v-if="chatMessages.length > 0" class="chat-messages">
              <div class="chat-msg-bar">
                <button class="btn ghost" type="button" @click="backToConversations">← 所有对话</button>
                <span class="chat-msg-title">{{ chatTitle }}</span>
              </div>
              <div class="chat-msg-list">
                <div
                  v-for="m in chatMessages"
                  :key="m.id"
                  class="msg-bubble-wrap"
                  :class="m.role"
                >
                  <div class="msg-bubble">
                    {{ m.content }}
                  </div>
                  <span class="msg-time">{{ formatDate(m.created_at) }}</span>
                </div>
              </div>
            </div>

            <!-- Conversations list -->
            <div v-else class="chat-conv-list">
              <div v-if="convLoading" class="load-hint">加载中...</div>
              <div v-else-if="convError" class="msg-bar error">{{ convError }}</div>
              <div v-else-if="conversations.length === 0" class="load-hint">暂无对话</div>
              <div
                v-for="conv in conversations"
                :key="conv.id"
                class="chat-conv-item"
                @click="openConversation(conv)"
              >
                <div class="chat-conv-title">{{ conv.title }}</div>
                <div class="chat-conv-meta">
                  {{ conv.message_count }} 条消息 · {{ formatDate(conv.updated_at) }}
                </div>
              </div>
            </div>
          </div>
        </div>
      </Teleport>
    </main>
  </div>
</template>

<style>
/* ===== Reset ===== */
*,*::before,*::after { margin:0; padding:0; box-sizing:border-box; }

:root {
  --bg: #f5f2ef;
  --fg: #1e1a18;
  --fg2: #6a5a4e;
  --fg3: #a89484;
  --accent: #d9735a;
  --accent-hover: #c05e46;
  --accent-soft: #f5ddd5;
  --surface: #fff;
  --border: #e0d6ce;
  --radius: 10px;
  --font: "Inter", -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
}

html { font-size: 16px; -webkit-font-smoothing: antialiased; }

body {
  font-family: var(--font);
  background: var(--bg);
  color: var(--fg);
  min-height: 100dvh;
}

.app { min-height: 100dvh; }

/* ===== Shared ===== */
.input {
  display: block;
  width: 100%;
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 0.7rem 0.85rem;
  font-family: var(--font);
  font-size: 0.9rem;
  background: var(--surface);
  outline: none;
  transition: border-color 0.2s;
}
.input:focus { border-color: var(--accent); }
.input::placeholder { color: var(--fg3); }

.btn {
  border: none;
  border-radius: var(--radius);
  padding: 0.6rem 1.2rem;
  font-family: var(--font);
  font-size: 0.88rem;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.2s, opacity 0.15s;
}
.btn:disabled { opacity: 0.4; cursor: not-allowed; }

.btn-primary {
  background: var(--accent);
  color: #fff;
}
.btn-primary:hover:not(:disabled) { background: var(--accent-hover); }

.btn-block { width: 100%; }

.ghost {
  background: transparent;
  color: var(--fg2);
  padding: 0.25rem 0.55rem;
  font-size: 0.78rem;
  font-weight: 500;
  border-radius: 6px;
}
.ghost:hover:not(:disabled) { background: var(--accent-soft); color: var(--accent-hover); }

.field { margin-bottom: 0.6rem; }

.msg-bar {
  padding: 0.5rem 0.75rem;
  border-radius: 8px;
  font-size: 0.82rem;
  margin-bottom: 0.75rem;
}
.msg-bar.error {
  background: #fef0f0;
  color: #d06050;
}

.load-hint {
  text-align: center;
  font-size: 0.78rem;
  color: var(--fg3);
  padding: 2rem 0;
}

/* ===== Login ===== */
.login-page {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 100dvh;
  padding: 1.5rem;
}

.login-card {
  width: 100%;
  max-width: 360px;
  background: var(--surface);
  border-radius: 20px;
  padding: 2.5rem 2rem 2rem;
  text-align: center;
  box-shadow: 0 8px 40px rgba(0,0,0,0.06);
}

.login-icon { font-size: 2.5rem; margin-bottom: 0.5rem; }
.login-title { font-size: 1.25rem; font-weight: 650; margin-bottom: 0.25rem; }
.login-subtitle { font-size: 0.82rem; color: var(--fg2); margin-bottom: 1.25rem; }
.login-form { text-align: left; }

/* ===== Admin Dashboard ===== */
.admin-page {
  display: flex;
  flex-direction: column;
  min-height: 100dvh;
  max-width: 800px;
  margin: 0 auto;
  padding: 0 1rem;
}

.admin-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-shrink: 0;
  padding: 0.9rem 0;
  border-bottom: 1px solid var(--border);
}

.admin-header-title {
  font-size: 1.05rem;
  font-weight: 650;
}

.admin-header-right {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.admin-user {
  font-size: 0.85rem;
  color: var(--fg2);
}

.admin-content {
  flex: 1;
  padding: 1rem 0;
}

.user-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.85rem;
}

.user-table th {
  text-align: left;
  padding: 0.6rem 0.4rem;
  font-weight: 600;
  color: var(--fg2);
  border-bottom: 1px solid var(--border);
  font-size: 0.78rem;
  white-space: nowrap;
}

.user-table td {
  padding: 0.6rem 0.4rem;
  border-bottom: 1px solid var(--border);
  vertical-align: middle;
}

.user-table tr:last-child td { border-bottom: none; }
.user-table tr:hover td { background: rgba(0,0,0,0.02); }

.user-table .danger { color: #d55; }
.user-table .danger:hover:not(:disabled) { background: rgba(200,60,60,0.08); color: #c33; }

/* ===== Modal ===== */
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0,0,0,0.35);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  padding: 1rem;
}

.modal-card {
  width: 100%;
  max-width: 380px;
  background: var(--surface);
  border-radius: 18px;
  padding: 2rem 1.75rem 1.75rem;
  box-shadow: 0 12px 48px rgba(0,0,0,0.12);
}

.modal-title {
  font-size: 1.1rem;
  font-weight: 650;
  margin-bottom: 0.3rem;
}

.modal-desc {
  font-size: 0.82rem;
  color: var(--fg2);
  margin-bottom: 1rem;
}

.modal-form .field { margin-bottom: 1rem; }

.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 0.5rem;
}

/* ===== Chat History ===== */
.chat-card {
  max-width: 600px;
  max-height: 80vh;
  display: flex;
  flex-direction: column;
  padding: 1rem 0;
}

.chat-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-shrink: 0;
  padding: 0 1.25rem 0.75rem;
  border-bottom: 1px solid var(--border);
}

.chat-header-title {
  font-size: 0.95rem;
  font-weight: 600;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  margin: 0 0.5rem;
}

.chat-conv-list {
  flex: 1;
  overflow-y: auto;
  padding: 0.5rem 0;
}

.chat-conv-item {
  padding: 0.7rem 1.25rem;
  cursor: pointer;
  transition: background 0.15s;
}
.chat-conv-item:hover { background: rgba(0,0,0,0.03); }

.chat-conv-title {
  font-size: 0.9rem;
  font-weight: 550;
  margin-bottom: 0.2rem;
}

.chat-conv-meta {
  font-size: 0.75rem;
  color: var(--fg3);
}

.chat-messages {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.chat-msg-bar {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  flex-shrink: 0;
  padding: 0 1.25rem 0.5rem;
  border-bottom: 1px solid var(--border);
}

.chat-msg-title {
  font-size: 0.85rem;
  font-weight: 550;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.chat-msg-list {
  flex: 1;
  overflow-y: auto;
  padding: 0.75rem 1.25rem;
  display: flex;
  flex-direction: column;
  gap: 0.6rem;
}

.msg-bubble-wrap {
  display: flex;
  flex-direction: column;
  max-width: 78%;
}

.msg-bubble-wrap.user {
  align-self: flex-end;
  align-items: flex-end;
}

.msg-bubble-wrap.assistant {
  align-self: flex-start;
  align-items: flex-start;
}

.msg-bubble {
  padding: 0.6rem 0.95rem;
  border-radius: 1.2rem;
  line-height: 1.55;
  font-size: 0.88rem;
  max-width: 100%;
  word-wrap: break-word;
  overflow-wrap: break-word;
  white-space: pre-wrap;
}

.msg-bubble-wrap.user .msg-bubble {
  background: var(--accent);
  color: #fff;
  border-bottom-right-radius: 0.3rem;
}

.msg-bubble-wrap.assistant .msg-bubble {
  background: #f7f2ed;
  color: var(--fg);
  border-bottom-left-radius: 0.3rem;
}

.msg-time {
  font-size: 0.58rem;
  color: var(--fg3);
  margin-top: 0.2rem;
  padding: 0 0.2rem;
}

/* ===== Mobile ===== */
@media (max-width: 640px) {
  html { font-size: 15px; }
  .login-page { padding: 1rem; }
  .login-card {
    max-width: 100%;
    border-radius: 16px;
    padding: 2rem 1.5rem 1.5rem;
  }
  .admin-page { padding: 0 0.65rem; }
  .admin-header { padding: 0.6rem 0; }
  .admin-content { padding: 0.6rem 0; }
  .user-table th, .user-table td { padding: 0.45rem 0.3rem; font-size: 0.8rem; }
  .user-table .ghost { font-size: 0.72rem; padding: 0.2rem 0.4rem; }
}
</style>
