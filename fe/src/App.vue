<script setup>
import { computed, nextTick, onMounted, ref } from "vue";

import {
  checkHealth,
  fetchChatHistory,
  getCurrentUser,
  login,
  register,
  resetChatHistory,
  setToken,
  streamEmotionalMessage,
} from "./api/client";

const input = ref("");
const username = ref("");
const password = ref("");
const authMode = ref("login");
const authLoading = ref(false);
const authenticated = ref(false);
const currentUser = ref(null);
const sending = ref(false);
const threadId = ref("");
const status = ref("正在连接后端...");
const statusTone = ref("pending");
const messages = ref([]);

// --- Mobile detection ---
const isMobile = ref(false);

// --- 分页状态 ---
const PAGE_LIMIT = 50;
const loadingOlder = ref(false);
const hasMoreMessages = ref(false);
const historyLoaded = ref(false); // true 后不再加载首页历史
const loadingOffset = ref(0);

const canSend = computed(() => input.value.trim().length > 0 && !sending.value);
const authButtonText = computed(() =>
  authLoading.value ? "提交中..." : authMode.value === "login" ? "登录" : "注册并登录"
);

function toUiMessage(message) {
  return {
    id: `message-${message.id}`,
    role: message.role === "assistant" ? "assistant" : "user",
    text: message.content,
    meta: message.created_at ? new Date(message.created_at).toLocaleString() : "",
  };
}

function resetWelcomeMessage(text = "我在这里。你可以慢慢说，最近让你最累的一件事是什么？") {
  messages.value = [
    {
      id: "welcome",
      role: "assistant",
      text,
      meta: "情感陪伴助手",
    },
  ];
}

function pushMessage(role, text, meta = "") {
  messages.value.push({
    id: `${role}-${Date.now()}-${Math.random().toString(16).slice(2)}`,
    role,
    text,
    meta,
  });
}

// --- 无限滚动：滚动到顶部时加载更早的消息 ---
const messageListRef = ref(null);

function onMessageListScroll() {
  const el = messageListRef.value;
  if (!el || loadingOlder.value || !hasMoreMessages.value) {
    return;
  }
  // 滚动到接近顶部时（距离顶部 < 80px）触发加载
  if (el.scrollTop < 80) {
    loadOlderMessages();
  }
}

async function loadOlderMessages() {
  if (loadingOlder.value || !hasMoreMessages.value) {
    return;
  }
  loadingOlder.value = true;
  try {
    const newOffset = loadingOffset.value + PAGE_LIMIT;
    const response = await fetchChatHistory(newOffset, PAGE_LIMIT);
    const data = response?.data;
    if (!data) {
      return;
    }

    // 记录旧滚动高度，加载后滚动回原来位置
    const el = messageListRef.value;
    const prevScrollHeight = el?.scrollHeight || 0;

    const older = (data.messages || []).map(toUiMessage);
    if (older.length > 0) {
      messages.value = [...older, ...messages.value];
    }
    loadingOffset.value = newOffset;
    hasMoreMessages.value = data.has_more ?? false;

    if (historyLoaded.value === false) {
      historyLoaded.value = true;
    }

    // 保持用户当前查看位置不变
    await nextTick();
    if (el) {
      el.scrollTop = el.scrollHeight - prevScrollHeight;
    }
  } catch {
    // 静默失败，不影响用户当前对话
  } finally {
    loadingOlder.value = false;
  }
}

// --- 初始化 ---
async function loadHealth() {
  try {
    await checkHealth();
    status.value = "后端已连接";
    statusTone.value = "ok";
  } catch (error) {
    status.value = `后端不可用：${error.message}`;
    statusTone.value = "error";
  }
}

async function restoreSession() {
  try {
    const response = await getCurrentUser();
    currentUser.value = response?.data || null;
    authenticated.value = Boolean(currentUser.value);
    if (authenticated.value) {
      await loadLatestHistory();
      status.value = "已登录，历史记录已恢复";
      statusTone.value = "ok";
    }
  } catch {
    setToken("");
    authenticated.value = false;
    currentUser.value = null;
    resetWelcomeMessage();
  }
}

async function loadLatestHistory() {
  const response = await fetchChatHistory(0, PAGE_LIMIT);
  const data = response?.data;
  threadId.value = data?.thread_id || "";
  loadingOffset.value = 0;
  hasMoreMessages.value = data?.has_more ?? false;
  historyLoaded.value = true;

  const items = Array.isArray(data?.messages) ? data.messages.map(toUiMessage) : [];
  if (items.length > 0) {
    messages.value = items;
    return;
  }
  resetWelcomeMessage();
}

// --- 认证 ---
async function handleAuthSubmit() {
  const name = username.value.trim();
  const secret = password.value.trim();
  if (!name || !secret || authLoading.value) {
    return;
  }

  authLoading.value = true;
  try {
    const response =
      authMode.value === "login"
        ? await login(name, secret)
        : await register(name, secret);
    const data = response?.data;
    setToken(data?.access_token || "");
    currentUser.value = data?.user || null;
    authenticated.value = Boolean(currentUser.value);
    password.value = "";
    await loadLatestHistory();
    status.value = authMode.value === "login" ? "登录成功" : "注册并登录成功";
    statusTone.value = "ok";
  } catch (error) {
    status.value = `认证失败：${error.message}`;
    statusTone.value = "error";
  } finally {
    authLoading.value = false;
  }
}

function handleLogout() {
  setToken("");
  authenticated.value = false;
  currentUser.value = null;
  threadId.value = "";
  password.value = "";
  hasMoreMessages.value = false;
  loadingOffset.value = 0;
  historyLoaded.value = false;
  resetWelcomeMessage();
  status.value = "已退出登录";
  statusTone.value = "pending";
}

let _scrollRaf = null;
function scrollToBottom() {
  if (_scrollRaf) {
    return;
  }
  _scrollRaf = requestAnimationFrame(() => {
    _scrollRaf = null;
    const el = messageListRef.value;
    if (el) {
      el.scrollTop = el.scrollHeight;
    }
  });
}

// --- 发送消息 ---
async function handleSend() {
  const content = input.value.trim();
  if (!content || sending.value || !authenticated.value) {
    return;
  }

  const pendingAssistantId = `assistant-pending-${Date.now()}`;
  pushMessage("user", content, new Date().toLocaleString());
  messages.value.push({
    id: pendingAssistantId,
    role: "assistant",
    text: "",
    meta: "正在回复...",
  });
  input.value = "";
  sending.value = true;
  scrollToBottom();

  try {
    await streamEmotionalMessage(content, {
      onChunk(payload) {
        const target = messages.value.find((message) => message.id === pendingAssistantId);
        if (target) {
          target.text += payload?.content || "";
          target.meta = "流式回复中...";
        }
        scrollToBottom();
      },
      onDone(payload) {
        threadId.value = payload?.thread_id || "";
        const target = messages.value.find((message) => message.id === pendingAssistantId);
        if (target) {
          target.text =
            payload?.assistant_message?.content || target.text || "我在这里陪着你。";
          target.meta = payload?.assistant_message?.created_at
            ? new Date(payload.assistant_message.created_at).toLocaleString()
            : "已完成";
        }
        scrollToBottom();
      },
      onError(payload) {
        const target = messages.value.find((message) => message.id === pendingAssistantId);
        if (target) {
          target.text = payload?.message || "流式输出失败。";
          target.meta = "请求失败";
        }
        scrollToBottom();
      },
    });
    // 新消息已持久化到后端，下次加载历史时就能看到
    historyLoaded.value = false;
    status.value = "对话正常";
    statusTone.value = "ok";
  } catch (error) {
    const target = messages.value.find((message) => message.id === pendingAssistantId);
    if (target) {
      target.text = "我这边暂时没有连上后端服务。你可以先检查服务是否启动。";
      target.meta = "请求失败";
    }
    status.value = `发送失败：${error.message}`;
    statusTone.value = "error";
  } finally {
    sending.value = false;
    scrollToBottom();
  }
}

function handleComposerKeydown(event) {
  if (event.key !== "Enter" || event.shiftKey || event.isComposing) {
    return;
  }
  event.preventDefault();
  handleSend();
}

async function handleReset() {
  if (!authenticated.value) {
    resetWelcomeMessage("新的对话已经开始了。想从哪里说起，都可以。");
    status.value = "会话已重置";
    statusTone.value = "pending";
    return;
  }

  try {
    const response = await resetChatHistory();
    const history = response?.data;
    threadId.value = history?.thread_id || "";
    loadingOffset.value = 0;
    hasMoreMessages.value = false;
    historyLoaded.value = true;
    resetWelcomeMessage("新的对话已经开始了。想从哪里说起，都可以。");
    status.value = "会话已重置并清空历史";
    statusTone.value = "ok";
  } catch (error) {
    status.value = `重置失败：${error.message}`;
    statusTone.value = "error";
  }
}

function autoResizeTextarea(event) {
  const el = event.target;
  el.style.height = "auto";
  el.style.height = `${Math.min(el.scrollHeight, 200)}px`;
}

onMounted(() => {
  isMobile.value = window.innerWidth <= 640;
  loadHealth();
  restoreSession();
});
</script>

<template>
  <div class="app">
    <!-- Auth -->
    <main v-if="!authenticated" class="auth">
      <div class="auth-card">
        <header class="auth-head">
          <span class="auth-badge">Emotion Support</span>
          <h1>登录 / 注册</h1>
          <p class="auth-desc">登录恢复你的历史对话，新用户自动注册</p>
        </header>

        <div class="status-badge">
          <span class="dot" :data-tone="statusTone"></span>
          <span>{{ status }}</span>
        </div>

        <form class="auth-form" @submit.prevent="handleAuthSubmit">
          <input
            v-model="username"
            type="text"
            autocomplete="username"
            placeholder="用户名"
            class="input"
          />
          <input
            v-model="password"
            type="password"
            autocomplete="current-password"
            placeholder="密码（至少 6 位）"
            class="input"
          />
          <button class="btn btn-primary" type="submit" :disabled="authLoading">
            {{ authButtonText }}
          </button>
        </form>

        <button class="link-btn" type="button" @click="authMode = authMode === 'login' ? 'register' : 'login'">
          {{ authMode === "login" ? "没有账号？去注册" : "已有账号？去登录" }}
        </button>
      </div>
    </main>

    <!-- Chat -->
    <main v-else class="chat">
      <!-- Header -->
      <header class="chat-head">
        <div class="chat-head-left">
          <span class="dot" :data-tone="statusTone"></span>
          <span class="chat-name">{{ currentUser?.username }}</span>
        </div>
        <div class="chat-head-right">
          <button class="btn ghost" type="button" @click="handleReset">新对话</button>
          <button class="btn ghost" type="button" @click="handleLogout">退出</button>
        </div>
      </header>

      <!-- Messages -->
      <div ref="messageListRef" class="msgs" @scroll="onMessageListScroll">
        <div v-if="loadingOlder" class="load-hint">加载中...</div>
        <div v-else-if="hasMoreMessages" class="load-hint">向上滚动加载更多</div>

        <article
          v-for="m in messages"
          :key="m.id"
          class="msg"
          :class="m.role"
        >
          <div class="msg-bubble">
            <p>{{ m.text }}</p>
            <span v-if="m.meta" class="msg-meta">{{ m.meta }}</span>
          </div>
        </article>
      </div>

      <!-- Composer -->
      <form class="composer" @submit.prevent="handleSend">
        <textarea
          id="msg-input"
          v-model="input"
          class="input ta"
          :rows="isMobile ? 2 : 3"
          placeholder="说说你的感受……"
          @keydown="handleComposerKeydown"
          @input="autoResizeTextarea"
        ></textarea>
        <button class="btn btn-primary send" type="submit" :disabled="!canSend">
          {{ sending ? "..." : "发送" }}
        </button>
      </form>
    </main>
  </div>
</template>

<style>
/* ===== Reset ===== */
*,*::before,*::after { margin:0; padding:0; box-sizing:border-box; }

:root {
  --bg: #f0ebe5;
  --fg: #2c1810;
  --fg2: #7a5a4a;
  --fg3: #a08070;
  --accent: #d9735a;
  --accent-hover: #c05e46;
  --surface: #ffffff;
  --border: #e0d3c8;
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

/* ===== Base ===== */
.app {
  display: flex;
  justify-content: center;
  width: 100%;
  min-height: 100dvh;
}

main {
  width: 100%;
}

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
  transition: border-color 0.15s;
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
  transition: background 0.15s, opacity 0.15s;
}
.btn:disabled { opacity: 0.4; cursor: not-allowed; }

.btn-primary {
  background: var(--accent);
  color: #fff;
}
.btn-primary:hover:not(:disabled) { background: var(--accent-hover); }

.ghost {
  background: transparent;
  color: var(--fg2);
  padding: 0.3rem 0.6rem;
  font-size: 0.78rem;
  font-weight: 500;
  border-radius: 6px;
}
.ghost:hover { background: rgba(0,0,0,0.05); color: var(--fg); }

.link-btn {
  background: none;
  border: none;
  font-size: 0.82rem;
  color: var(--accent);
  cursor: pointer;
}
.link-btn:hover { text-decoration: underline; }

.dot {
  display: inline-block;
  width: 7px; height: 7px;
  border-radius: 50%;
  background: #bbb;
  transition: background 0.3s;
}
.dot[data-tone="ok"] { background: #44b37f; }
.dot[data-tone="error"] { background: #e06050; }
.dot[data-tone="pending"] { background: #d9a040; }

/* ===== Auth ===== */
.auth {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 100dvh;
  padding: 1.5rem;
}

.auth-card {
  width: 100%;
  max-width: 380px;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 14px;
  padding: 2rem;
  box-shadow: 0 2px 16px rgba(0,0,0,0.06);
}

.auth-head { margin-bottom: 1.25rem; }

.auth-badge {
  display: inline-block;
  font-size: 0.68rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: var(--accent);
  margin-bottom: 0.5rem;
}

.auth-head h1 {
  font-size: 1.35rem;
  font-weight: 600;
  margin-bottom: 0.35rem;
}

.auth-desc {
  font-size: 0.82rem;
  color: var(--fg2);
  line-height: 1.5;
}

.status-badge {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  font-size: 0.8rem;
  color: var(--fg2);
  margin-bottom: 1.25rem;
}

.auth-form {
  display: flex;
  flex-direction: column;
  gap: 0.65rem;
  margin-bottom: 0.75rem;
}

/* ===== Chat ===== */
.chat {
  display: flex;
  flex-direction: column;
  height: 100dvh;
  max-width: 680px;
  margin: 0 auto;
}

/* --- Header --- */
.chat-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-shrink: 0;
  padding: 0.7rem 0.75rem;
  border-bottom: 1px solid var(--border);
}

.chat-head-left {
  display: flex;
  align-items: center;
  gap: 0.4rem;
}

.chat-name {
  font-size: 0.88rem;
  font-weight: 600;
}

.chat-head-right {
  display: flex;
  align-items: center;
  gap: 0.2rem;
}

/* --- Messages --- */
.msgs {
  flex: 1;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 0.3rem;
  padding: 0.75rem;
  scroll-behavior: smooth;
}

.load-hint {
  text-align: center;
  font-size: 0.7rem;
  color: var(--fg3);
  padding: 0.5rem 0;
  user-select: none;
}

.msg {
  display: flex;
  flex-direction: column;
  max-width: 80%;
}

.msg.user {
  align-self: flex-end;
  align-items: flex-end;
}

.msg.assistant {
  align-self: flex-start;
  align-items: flex-start;
}

.msg-bubble {
  padding: 0.55rem 0.9rem;
  border-radius: 1rem;
  line-height: 1.55;
  font-size: 0.9rem;
  max-width: 100%;
  word-wrap: break-word;
}

.msg.user .msg-bubble {
  background: var(--accent);
  color: #fff;
  border-bottom-right-radius: 0.25rem;
}

.msg.assistant .msg-bubble {
  background: var(--surface);
  border: 1px solid var(--border);
  color: var(--fg);
  border-bottom-left-radius: 0.25rem;
}

.msg-meta {
  display: block;
  font-size: 0.6rem;
  color: var(--fg3);
  margin-top: 0.2rem;
}

.msg.user .msg-meta { color: rgba(255,255,255,0.5); }

/* --- Composer --- */
.composer {
  flex-shrink: 0;
  display: flex;
  align-items: flex-end;
  gap: 0.5rem;
  padding: 0.7rem 0.75rem;
  padding-bottom: calc(0.7rem + env(safe-area-inset-bottom, 0px));
  border-top: 1px solid var(--border);
}

.composer .ta {
  flex: 1;
  border-radius: 1.25rem;
  resize: none;
  padding: 0.5rem 0.85rem;
  font-size: 0.88rem;
  line-height: 1.5;
  max-height: 120px;
}

.composer .send {
  flex-shrink: 0;
  border-radius: 2rem;
  padding: 0.5rem 1rem;
  font-size: 0.82rem;
}

/* ===== Mobile ===== */
@media (max-width: 640px) {
  html { font-size: 15px; }
  .chat { max-width: 100%; }
  .msg { max-width: 88%; }
  .msgs { padding: 0.6rem; }
  .composer { padding: 0.6rem; }
}

@media (max-width: 400px) {
  .msg { max-width: 95%; }
}
</style>
