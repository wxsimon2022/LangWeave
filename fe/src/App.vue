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

  try {
    await streamEmotionalMessage(content, {
      onChunk(payload) {
        const target = messages.value.find((message) => message.id === pendingAssistantId);
        if (target) {
          target.text += payload?.content || "";
          target.meta = "流式回复中...";
        }
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
      },
      onError(payload) {
        const target = messages.value.find((message) => message.id === pendingAssistantId);
        if (target) {
          target.text = payload?.message || "流式输出失败。";
          target.meta = "请求失败";
        }
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
  <div class="page-shell">
    <div class="background-orb orb-left"></div>
    <div class="background-orb orb-right"></div>

    <main v-if="!authenticated" class="auth-screen">
      <section class="auth-hero">
        <p class="eyebrow">Emotion Support Console</p>
        <h1>把登录和倾诉分开。</h1>
        <p class="hero-copy">
          先完成登录，再进入专注聊天的空间。这样页面更干净，状态也更清楚。
        </p>

        <div class="status-row">
          <span class="status-dot" :data-tone="statusTone"></span>
          <span class="status-text">{{ status }}</span>
        </div>
      </section>

      <section class="auth-panel">
        <div class="auth-panel-header">
          <p class="auth-kicker">{{ authMode === "login" ? "Sign In" : "Create Account" }}</p>
          <h2>{{ authMode === "login" ? "登录继续聊天" : "注册新账号" }}</h2>
          <p class="auth-description">
            登录后会自动恢复你自己的历史消息，并继续上一次情感对话。
          </p>
        </div>

        <form class="auth-form" @submit.prevent="handleAuthSubmit">
          <input
            v-model="username"
            class="auth-input"
            type="text"
            autocomplete="username"
            placeholder="用户名"
          />
          <input
            v-model="password"
            class="auth-input"
            type="password"
            autocomplete="current-password"
            placeholder="密码，至少 6 位"
          />
          <button class="send-button block-button" type="submit" :disabled="authLoading">
            {{ authButtonText }}
          </button>
        </form>

        <button
          class="switch-auth"
          type="button"
          @click="authMode = authMode === 'login' ? 'register' : 'login'"
        >
          {{ authMode === "login" ? "没有账号？去注册" : "已有账号？去登录" }}
        </button>
      </section>
    </main>

    <main v-else class="chat-screen">
      <section class="hero-panel">
        <p class="eyebrow">Emotion Support Console</p>
        <h1>情感聊天助手</h1>
        <p class="hero-copy">
          这是一个偏陪伴型的对话界面。它不会催你给答案，也不会急着下判断，只负责先把你的话接住。
        </p>

        <div class="status-row">
          <span class="status-dot" :data-tone="statusTone"></span>
          <span class="status-text">{{ status }}</span>
        </div>

        <div class="thread-card">
          <span class="thread-label">当前会话</span>
          <strong>{{ threadId || "未建立" }}</strong>
        </div>

        <div class="account-card">
          <span class="thread-label">当前用户</span>
          <strong>{{ currentUser?.username }}</strong>
          <button class="ghost-button block-button" type="button" @click="handleLogout">
            退出登录
          </button>
        </div>
      </section>

      <section class="chat-panel">
        <header class="chat-header">
          <div>
            <p class="chat-title">对话窗口</p>
            <p class="chat-subtitle">
              登录后会自动保存聊天记录。滚动到顶部可加载更多历史消息。
            </p>
          </div>
          <button class="ghost-button" type="button" @click="handleReset">新对话</button>
        </header>

        <div
          ref="messageListRef"
          class="message-list"
          @scroll="onMessageListScroll"
        >
          <div v-if="loadingOlder" class="load-more-hint">加载更早的消息...</div>
          <div v-else-if="hasMoreMessages" class="load-more-hint">
            向上滚动加载更多历史消息
          </div>

          <article
            v-for="message in messages"
            :key="message.id"
            class="message-item"
            :data-role="message.role"
          >
            <div class="message-badge">
              {{ message.role === "assistant" ? "陪伴助手" : "你" }}
            </div>
            <div class="message-bubble">
              <p>{{ message.text }}</p>
              <span v-if="message.meta" class="message-meta">{{ message.meta }}</span>
            </div>
          </article>
        </div>

        <form class="composer" @submit.prevent="handleSend">
          <label class="composer-label" for="message">
            想说什么就写下来，不需要组织得很完整。
          </label>
          <textarea
            id="message"
            v-model="input"
            class="composer-input"
            :rows="isMobile ? 2 : 4"
            placeholder="比如：最近总觉得很焦虑，晚上也睡不好。"
            @keydown="handleComposerKeydown"
            @input="autoResizeTextarea"
          ></textarea>

          <div class="composer-actions">
            <p class="composer-tip">
              前端调用接口：`/api/v1/auth/*`、`/api/v1/emotional-chat/*`
            </p>
            <button class="send-button" type="submit" :disabled="!canSend">
              {{ sending ? "发送中..." : "发送" }}
            </button>
          </div>
        </form>
      </section>
    </main>
  </div>
</template>

<style>
/* ===== Reset & Base ===== */
*,
*::before,
*::after {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

:root {
  --bg-start: #fef3ed;
  --bg-end: #f9e8e0;
  --text-primary: #2c1810;
  --text-secondary: #7a5a4a;
  --text-muted: #a08070;
  --accent: #d9735a;
  --accent-hover: #c05e46;
  --accent-soft: #f5ddd5;
  --surface: #ffffffdd;
  --surface-hover: #ffffff;
  --border: #e6d3c8;
  --shadow-sm: 0 1px 3px rgba(0, 0, 0, 0.06);
  --shadow-md: 0 4px 20px rgba(0, 0, 0, 0.08);
  --radius-sm: 8px;
  --radius-md: 12px;
  --radius-lg: 20px;
  --font-sans: "Inter", -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto,
    sans-serif;
  --font-mono: "JetBrains Mono", "Fira Code", monospace;
}

html {
  font-size: 16px;
  -webkit-font-smoothing: antialiased;
}

body {
  font-family: var(--font-sans);
  background: linear-gradient(145deg, var(--bg-start), var(--bg-end));
  color: var(--text-primary);
  min-height: 100dvh;
}

/* ===== Layout ===== */
.page-shell {
  display: flex;
  min-height: 100dvh;
  position: relative;
  overflow: hidden;
}

.background-orb {
  position: fixed;
  border-radius: 50%;
  filter: blur(120px);
  opacity: 0.35;
  pointer-events: none;
  z-index: 0;
}

.orb-left {
  width: 500px;
  height: 500px;
  background: #e8b4a0;
  top: -120px;
  left: -150px;
}

.orb-right {
  width: 400px;
  height: 400px;
  background: #d9b8a8;
  bottom: -100px;
  right: -100px;
}

/* ===== Auth Screen ===== */
.auth-screen {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: center;
  gap: 3rem;
  width: 100%;
  padding: 2rem;
  z-index: 1;
}

.auth-hero {
  flex: 0 1 380px;
}

.eyebrow {
  font-size: 0.75rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: var(--accent);
  margin-bottom: 0.75rem;
}

.auth-hero h1 {
  font-size: 2rem;
  font-weight: 650;
  line-height: 1.25;
  margin-bottom: 1rem;
  color: var(--text-primary);
}

.hero-copy {
  font-size: 0.95rem;
  line-height: 1.6;
  color: var(--text-secondary);
  margin-bottom: 1.5rem;
  max-width: 36ch;
}

.status-row {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.status-dot {
  display: inline-block;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #bbb;
  transition: background 0.3s;
}

.status-dot[data-tone="ok"] {
  background: #44b37f;
}

.status-dot[data-tone="error"] {
  background: #e06050;
}

.status-dot[data-tone="pending"] {
  background: #d9a040;
}

.status-text {
  font-size: 0.85rem;
  color: var(--text-muted);
}

/* ===== Auth Panel ===== */
.auth-panel {
  flex: 0 1 380px;
  background: var(--surface);
  backdrop-filter: blur(16px);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  padding: 2.25rem;
  box-shadow: var(--shadow-md);
}

.auth-panel-header {
  margin-bottom: 1.75rem;
}

.auth-kicker {
  font-size: 0.7rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: var(--accent);
  margin-bottom: 0.4rem;
}

.auth-panel-header h2 {
  font-size: 1.3rem;
  font-weight: 600;
  margin-bottom: 0.5rem;
}

.auth-description {
  font-size: 0.85rem;
  color: var(--text-secondary);
  line-height: 1.5;
}

.auth-form {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  margin-bottom: 1rem;
}

.auth-input {
  padding: 0.75rem 1rem;
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  font-size: 0.95rem;
  background: #fff;
  transition: border-color 0.2s, box-shadow 0.2s;
  outline: none;
}

.auth-input:focus {
  border-color: var(--accent);
  box-shadow: 0 0 0 3px var(--accent-soft);
}

.switch-auth {
  background: none;
  border: none;
  font-size: 0.85rem;
  color: var(--accent);
  cursor: pointer;
  text-decoration: underline;
  text-underline-offset: 3px;
}

.switch-auth:hover {
  color: var(--accent-hover);
}

/* ===== Chat Screen ===== */
.chat-screen {
  display: flex;
  gap: 1.5rem;
  width: 100%;
  max-width: 1200px;
  margin: 0 auto;
  padding: 1.5rem;
  z-index: 1;
}

/* ===== Hero Panel (left sidebar) ===== */
.hero-panel {
  flex: 0 0 280px;
  position: sticky;
  top: 1.5rem;
  align-self: start;
}

.hero-panel h1 {
  font-size: 1.4rem;
  font-weight: 650;
  margin-bottom: 0.75rem;
}

.hero-panel .hero-copy {
  font-size: 0.85rem;
  margin-bottom: 1.25rem;
}

/* ===== Card ===== */
.thread-card,
.account-card {
  background: var(--surface);
  backdrop-filter: blur(12px);
  border-radius: var(--radius-md);
  padding: 0.75rem 1rem;
  margin-top: 0.75rem;
  border: 1px solid var(--border);
  display: flex;
  align-items: center;
  gap: 0.5rem;
  flex-wrap: wrap;
  font-size: 0.8rem;
}

.thread-label {
  color: var(--text-muted);
  font-weight: 500;
}

.thread-card strong,
.account-card strong {
  font-weight: 600;
  font-size: 0.85rem;
  word-break: break-all;
  max-width: 100%;
}

/* ===== Chat Panel (right column) ===== */
.chat-panel {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: calc(100dvh - 3rem);
  max-width: 700px;
}

.chat-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 1rem;
}

.chat-title {
  font-weight: 650;
  font-size: 1rem;
}

.chat-subtitle {
  font-size: 0.8rem;
  color: var(--text-muted);
  margin-top: 0.2rem;
}

/* ===== Message List ===== */
.message-list {
  flex: 1;
  overflow-y: auto;
  max-height: 60vh;
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  padding: 0.5rem 0.25rem 0.5rem 0;
  scroll-behavior: smooth;
  margin-bottom: 1rem;
}

.load-more-hint {
  text-align: center;
  font-size: 0.75rem;
  color: var(--text-muted);
  padding: 0.5rem 0;
  user-select: none;
}

.message-item {
  display: flex;
  flex-direction: column;
  max-width: 85%;
}

.message-item[data-role="user"] {
  align-self: flex-end;
  align-items: flex-end;
}

.message-item[data-role="assistant"] {
  align-self: flex-start;
  align-items: flex-start;
}

.message-badge {
  font-size: 0.7rem;
  font-weight: 600;
  color: var(--text-muted);
  margin-bottom: 0.25rem;
  padding: 0 0.25rem;
}

.message-bubble {
  background: var(--surface);
  backdrop-filter: blur(12px);
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  padding: 0.75rem 1rem;
  box-shadow: var(--shadow-sm);
  line-height: 1.6;
  font-size: 0.92rem;
}

.message-item[data-role="user"] .message-bubble {
  background: var(--accent);
  border-color: var(--accent);
  color: #fff;
  border-bottom-right-radius: 4px;
}

.message-item[data-role="assistant"] .message-bubble {
  border-bottom-left-radius: 4px;
}

.message-meta {
  display: block;
  font-size: 0.68rem;
  color: var(--text-muted);
  margin-top: 0.35rem;
}

.message-item[data-role="user"] .message-meta {
  color: rgba(255, 255, 255, 0.7);
}

/* ===== Composer ===== */
.composer {
  background: var(--surface);
  backdrop-filter: blur(12px);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  padding: 1rem 1.25rem;
  box-shadow: var(--shadow-md);
}

.composer-label {
  display: block;
  font-size: 0.75rem;
  font-weight: 500;
  color: var(--text-muted);
  margin-bottom: 0.5rem;
}

.composer-input {
  width: 100%;
  border: none;
  resize: none;
  font-family: var(--font-sans);
  font-size: 0.92rem;
  line-height: 1.6;
  background: transparent;
  outline: none;
  color: var(--text-primary);
}

.composer-input::placeholder {
  color: var(--text-muted);
}

.composer-actions {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 0.75rem;
}

.composer-tip {
  font-size: 0.7rem;
  color: var(--text-muted);
  font-family: var(--font-mono);
}

/* ===== Buttons ===== */
.send-button {
  background: var(--accent);
  color: #fff;
  border: none;
  border-radius: var(--radius-sm);
  padding: 0.6rem 1.5rem;
  font-size: 0.88rem;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.2s, transform 0.1s;
}

.send-button:hover:not(:disabled) {
  background: var(--accent-hover);
}

.send-button:active:not(:disabled) {
  transform: scale(0.97);
}

.send-button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.block-button {
  width: 100%;
  text-align: center;
}

.ghost-button {
  background: transparent;
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  padding: 0.45rem 1rem;
  font-size: 0.8rem;
  font-weight: 500;
  color: var(--text-secondary);
  cursor: pointer;
  transition: background 0.2s;
}

.ghost-button:hover {
  background: var(--accent-soft);
}

/* ===== Responsive: Tablet ===== */
@media (max-width: 960px) {
  .chat-screen {
    flex-direction: column;
    padding: 1rem;
  }

  .hero-panel {
    flex: none;
    position: static;
  }

  .chat-panel {
    min-height: auto;
  }
}

/* ===== Responsive: Mobile ===== */
@media (max-width: 640px) {
  /* ---------- Base ---------- */
  html {
    font-size: 15px;
  }

  .page-shell {
    min-height: 100dvh;
    padding-bottom: env(safe-area-inset-bottom, 0px);
  }

  /* ---------- Auth Screen ---------- */
  .auth-screen {
    flex-direction: column;
    padding: 0;
    gap: 0;
  }

  .auth-hero {
    flex: none;
    padding: 2rem 1.25rem 1rem;
    width: 100%;
  }

  .auth-hero h1 {
    font-size: 1.4rem;
  }

  .auth-panel {
    flex: none;
    width: 100%;
    border-radius: var(--radius-lg) var(--radius-lg) 0 0;
    padding: 1.5rem 1.25rem;
    padding-bottom: calc(1.5rem + env(safe-area-inset-bottom, 0px));
  }

  /* ---------- Chat Screen ---------- */
  .chat-screen {
    flex-direction: column;
    padding: 0;
    gap: 0;
  }

  /* Collapsible status bar instead of sidebar */
  .hero-panel {
    flex: none;
    position: static;
    padding: 0.75rem 1rem;
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 0.5rem;
    background: var(--surface);
    backdrop-filter: blur(12px);
    border-bottom: 1px solid var(--border);
  }

  .hero-panel .eyebrow {
    display: none;
  }

  .hero-panel h1 {
    font-size: 0.95rem;
    margin-bottom: 0;
    margin-right: auto;
  }

  .hero-panel .hero-copy {
    display: none;
  }

  .hero-panel .status-row {
    order: 10;
    width: 100%;
  }

  .hero-panel .status-text {
    font-size: 0.72rem;
  }

  .thread-card,
  .account-card {
    margin-top: 0;
    padding: 0.3rem 0.6rem;
    font-size: 0.72rem;
    width: auto;
  }

  .account-card {
    display: flex;
    align-items: center;
    gap: 0.4rem;
  }

  .account-card .ghost-button {
    padding: 0.2rem 0.6rem;
    font-size: 0.7rem;
  }

  /* ---------- Chat Panel ---------- */
  .chat-panel {
    display: flex;
    flex-direction: column;
    min-height: 0;
    flex: 1;
    padding: 0.75rem 0.75rem 0;
    overflow: hidden;
  }

  .chat-header {
    margin-bottom: 0.5rem;
  }

  .chat-title {
    font-size: 0.85rem;
  }

  .chat-subtitle {
    display: none;
  }

  .chat-header .ghost-button {
    padding: 0.35rem 0.75rem;
    font-size: 0.75rem;
  }

  /* ---------- Message List ---------- */
  .message-list {
    flex: 1;
    max-height: none;
    min-height: 0;
    padding: 0.25rem 0;
    margin-bottom: 0.5rem;
    overscroll-behavior: contain;
    -webkit-overflow-scrolling: touch;
  }

  .message-item {
    max-width: 92%;
  }

  .message-bubble {
    padding: 0.6rem 0.85rem;
    font-size: 0.88rem;
  }

  .message-meta {
    font-size: 0.62rem;
  }

  /* ---------- Composer ---------- */
  .composer {
    border-radius: var(--radius-md) var(--radius-md) 0 0;
    padding: 0.75rem 0.85rem;
    padding-bottom: calc(0.75rem + env(safe-area-inset-bottom, 0px));
    margin: 0 -0.75rem;
    border-left: none;
    border-right: none;
    border-bottom: none;
  }

  .composer-label {
    font-size: 0.7rem;
    margin-bottom: 0.35rem;
  }

  .composer-input {
    font-size: 0.88rem;
    min-height: 2.5rem;
  }

  .composer-actions {
    margin-top: 0.5rem;
  }

  .composer-tip {
    display: none;
  }

  .send-button {
    padding: 0.55rem 1.25rem;
    font-size: 0.85rem;
  }
}

/* ===== Touch-safe tweaks for very small screens ===== */
@media (max-width: 400px) {
  .hero-panel h1 {
    font-size: 0.85rem;
  }

  .thread-card strong,
  .account-card strong {
    font-size: 0.72rem;
    max-width: 100px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .message-item {
    max-width: 98%;
  }

  .message-bubble {
    padding: 0.5rem 0.7rem;
    font-size: 0.85rem;
  }
}
</style>
