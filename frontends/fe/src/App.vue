<script setup>
import { computed, nextTick, onMounted, ref } from "vue";

import {
  checkHealth,
  getCurrentUser,
  login,
  register,
  setToken,
  sendHeartbeat,
  checkSession,
  onSessionKicked,
  streamChatMessage,
  listAllConversations,
  fetchChatHistoryV2,
  deleteConversationV2,
  updateConversationTitleV2,
} from "./api/client";

// --- Electron detection ---
const isElectron = ref(
  navigator.userAgent.toLowerCase().includes("electron") ||
  typeof window.electronAPI !== "undefined"
);

// --- Desktop version & update check ---
const desktopVersion = ref("");
const updateInfo = ref(null); // { hasUpdate, currentVersion, latestVersion, releaseUrl, releaseNotes } | null
const updateDismissed = ref(false);
const updateChecking = ref(false);

function getElectronAPI() {
  return window.electronAPI || null;
}

async function loadDesktopVersion() {
  const api = getElectronAPI();
  if (!api || typeof api.getAppVersion !== "function") return;
  try {
    desktopVersion.value = await api.getAppVersion();
  } catch {
    // silently fail
  }
}

async function checkDesktopUpdate() {
  const api = getElectronAPI();
  if (!api || typeof api.checkForUpdate !== "function") return;
  updateChecking.value = true;
  try {
    const result = await api.checkForUpdate();
    if (result.hasUpdate) {
      updateInfo.value = result;
    }
  } catch {
    // silently fail
  } finally {
    updateChecking.value = false;
  }
}

function dismissUpdate() {
  updateDismissed.value = true;
}

function openReleaseUrl() {
  const api = getElectronAPI();
  if (api && updateInfo.value?.releaseUrl) {
    api.openReleaseUrl(updateInfo.value.releaseUrl);
  }
}

// Listen for auto-update results pushed from the main process (startup / periodic)
let _unsubscribeUpdate = null;
function setupUpdateListener() {
  const api = getElectronAPI();
  if (!api || typeof api.onUpdateCheckResult !== "function") return;
  _unsubscribeUpdate = api.onUpdateCheckResult((info) => {
    if (info.hasUpdate) {
      updateInfo.value = info;
    }
  });
}

// Periodic update check (every 5 minutes while the app is open)
let _updateTimer = null;
function startPeriodicUpdateCheck() {
  stopPeriodicUpdateCheck();
  _updateTimer = setInterval(checkDesktopUpdate, 5 * 60 * 1000);
}
function stopPeriodicUpdateCheck() {
  if (_updateTimer) {
    clearInterval(_updateTimer);
    _updateTimer = null;
  }
}

// --- Heartbeat (online status) ---
let heartbeatTimer = null;

function startHeartbeat() {
  console.log("[heartbeat] Starting heartbeat...");
  stopHeartbeat();
  sendHeartbeat();
  heartbeatTimer = setInterval(sendHeartbeat, 30000); // every 30s
}

function stopHeartbeat() {
  if (heartbeatTimer) {
    clearInterval(heartbeatTimer);
    heartbeatTimer = null;
  }
}

// --- Session check (single-device login) ---
const kickedMessage = ref("");
let sessionCheckTimer = null;

function startSessionCheck() {
  stopSessionCheck();
  checkSession();
  sessionCheckTimer = setInterval(checkSession, 30000);
}

function stopSessionCheck() {
  if (sessionCheckTimer) {
    clearInterval(sessionCheckTimer);
    sessionCheckTimer = null;
  }
}

function forceLogoutKicked(msg) {
  kickedMessage.value = msg;
  stopHeartbeat();
  stopSessionCheck();
  setToken("");
  authenticated.value = false;
  currentUser.value = null;
  activeConvId.value = null;
  conversations.value = [];
  messages.value = [];
  status.value = msg;
  statusTone.value = "error";
}

onSessionKicked((msg) => {
  forceLogoutKicked(msg);
});

// --- Tiny Markdown renderer ---
const mdRenderer = (() => {
  const esc = (s) =>
    s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");

  function renderLine(text) {
    let html = esc(text);
    html = html.replace(/`([^`]+)`/g, "<code>$1</code>");
    html = html.replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");
    html = html.replace(/(?<!_)__(.+?)__(?!_)/g, "<strong>$1</strong>");
    html = html.replace(/\*(.+?)\*/g, "<em>$1</em>");
    html = html.replace(/(?<!_)_(.+?)_(?!_)/g, "<em>$1</em>");
    html = html.replace(/~~(.+?)~~/g, "<del>$1</del>");
    html = html.replace(
      /https?:\/\/[^\s<]+/g,
      '<a href="$&" target="_blank" rel="noopener">$&</a>'
    );
    return html;
  }

  return function render(md) {
    if (!md) return "";
    const lines = md.split("\n");
    let html = "";
    let inCodeBlock = false;
    let codeBuf = [];

    for (let i = 0; i < lines.length; i++) {
      const line = lines[i];

      if (/^```/.test(line)) {
        if (inCodeBlock) {
          html += `<pre><code>${esc(codeBuf.join("\n"))}</code></pre>`;
          codeBuf = [];
          inCodeBlock = false;
          continue;
        } else {
          inCodeBlock = true;
          continue;
        }
      }

      if (inCodeBlock) {
        codeBuf.push(line);
        continue;
      }

      if (/^---+\s*$/.test(line) || /^\*\*\*+\s*$/.test(line)) {
        html += "<hr>";
        continue;
      }

      const hMatch = line.match(/^(#{1,4})\s+(.+)/);
      if (hMatch) {
        const tag = "h" + Math.min(hMatch[1].length + 2, 4);
        html += `<${tag}>${renderLine(hMatch[2])}</${tag}>`;
        continue;
      }

      if (/^\s*[-*+]\s+/.test(line)) {
        html += `<li>${renderLine(line.replace(/^\s*[-*+]\s+/, ""))}</li>`;
        continue;
      }

      if (/^\s*\d+\.\s+/.test(line)) {
        html += `<li>${renderLine(line.replace(/^\s*\d+\.\s+/, ""))}</li>`;
        continue;
      }

      if (/^\s*>\s?/.test(line)) {
        html += `<blockquote><p>${renderLine(line.replace(/^\s*>\s?/, ""))}</p></blockquote>`;
        continue;
      }

      if (line.trim()) {
        html += `<p>${renderLine(line)}</p>`;
      } else {
        html += "<br>";
      }
    }

    if (inCodeBlock && codeBuf.length) {
      html += `<pre><code>${esc(codeBuf.join("\n"))}</code></pre>`;
    }

    html = html.replace(
      /(?:<li>.*?<\/li>\s*)+/g,
      (match) => `<ul>${match}</ul>`
    );

    return html;
  };
})();

// ============================
// State
// ============================

const input = ref("");
const username = ref("");
const password = ref("");
const authMode = ref("login");
const authLoading = ref(false);
const authenticated = ref(false);
const currentUser = ref(null);
const sending = ref(false);
const status = ref("正在连接后端...");
const statusTone = ref("pending");
const messages = ref([]);
const isMobile = ref(false);

// --- Conversation management ---
const conversations = ref([]);           // list from the backend
const activeConvId = ref(null);          // currently loaded conversation id
const sidePanelOpen = ref(false);        // toggle conversation list

// --- Pagination ---
const PAGE_LIMIT = 50;
const loadingOlder = ref(false);
const hasMoreMessages = ref(false);
const historyLoaded = ref(false);
const loadingOffset = ref(0);

// ============================
// Computed
// ============================

const canSend = computed(() => input.value.trim().length > 0 && !sending.value);
const authButtonText = computed(() =>
  authLoading.value ? "提交中..." : authMode.value === "login" ? "登录" : "注册并登录"
);

// ============================
// Message helpers
// ============================

function toUiMessage(message) {
  return {
    id: `message-${message.id}`,
    role: message.role === "assistant" ? "assistant" : "user",
    text: message.content,
    meta: message.created_at ? new Date(message.created_at).toLocaleString() : "",
  };
}

function pushMessage(role, text, meta = "") {
  messages.value.push({
    id: `${role}-${Date.now()}-${Math.random().toString(16).slice(2)}`,
    role,
    text,
    meta,
  });
}

// ============================
// Infinite scroll
// ============================

const messageListRef = ref(null);

function onMessageListScroll() {
  const el = messageListRef.value;
  if (!el || loadingOlder.value || !hasMoreMessages.value) return;
  if (el.scrollTop < 80) {
    loadOlderMessages();
  }
}

async function loadOlderMessages() {
  if (loadingOlder.value || !hasMoreMessages.value || !activeConvId.value) return;
  loadingOlder.value = true;
  try {
    const newOffset = loadingOffset.value + PAGE_LIMIT;
    const response = await fetchChatHistoryV2(activeConvId.value, newOffset, PAGE_LIMIT);
    const data = response?.data;
    if (!data) return;

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

    await nextTick();
    if (el) {
      el.scrollTop = el.scrollHeight - prevScrollHeight;
    }
  } catch {
    // silent
  } finally {
    loadingOlder.value = false;
  }
}

// ============================
// Init
// ============================

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
      await refreshConversationList();
      startHeartbeat();
      startSessionCheck();
      // Load the most recent conversation
      if (conversations.value.length > 0) {
        await loadConversation(conversations.value[0].id);
      } else {
        await startNewConversation();
      }
      status.value = "已登录，历史记录已恢复";
      statusTone.value = "ok";
    }
  } catch {
    setToken("");
    authenticated.value = false;
    currentUser.value = null;
  }
}

// ============================
// Conversation management
// ============================

async function refreshConversationList() {
  try {
    const response = await listAllConversations();
    conversations.value = response?.data?.conversations || [];
  } catch {
    // silent
  }
}

async function loadConversation(convId) {
  activeConvId.value = convId;
  sidePanelOpen.value = false;
  loadingOffset.value = 0;
  hasMoreMessages.value = false;
  historyLoaded.value = false;

  const response = await fetchChatHistoryV2(convId, 0, PAGE_LIMIT);
  const data = response?.data;
  loadingOffset.value = 0;
  hasMoreMessages.value = data?.has_more ?? false;
  historyLoaded.value = true;

  const items = Array.isArray(data?.messages) ? data.messages.map(toUiMessage) : [];
  if (items.length > 0) {
    messages.value = items;
  } else {
    // fresh conversation — show welcome
    messages.value = [];
  }
  scrollToBottom();
}

async function startNewConversation() {
  // Create a new conversation by loading with null conv id — service will create one
  activeConvId.value = null;
  sidePanelOpen.value = false;
  messages.value = [];
  loadingOffset.value = 0;
  hasMoreMessages.value = false;
  historyLoaded.value = true;
  scrollToBottom();
}

async function handleDeleteConversation(convId) {
  if (!confirm("确定删除这个对话？")) return;
  try {
    await deleteConversationV2(convId);
    await refreshConversationList();
    if (activeConvId.value === convId) {
      if (conversations.value.length > 0) {
        await loadConversation(conversations.value[0].id);
      } else {
        await startNewConversation();
      }
    }
  } catch {
    // silent
  }
}

// --- Inline rename ---
const renamingConvId = ref(null);
const renamingTitle = ref("");

function startRename(conv) {
  renamingConvId.value = conv.id;
  renamingTitle.value = conv.title;
  // Focus the input on next tick
  nextTick(() => {
    const input = document.querySelector(".rename-input");
    if (input) {
      input.focus();
      input.select();
    }
  });
}

function cancelRename() {
  renamingConvId.value = null;
  renamingTitle.value = "";
}

async function submitRename() {
  const convId = renamingConvId.value;
  const title = renamingTitle.value.trim();
  cancelRename();
  if (!convId || !title) return;
  // Optimistic update
  const conv = conversations.value.find((c) => c.id === convId);
  if (conv) {
    const oldTitle = conv.title;
    conv.title = title;
    try {
      await updateConversationTitleV2(convId, title);
    } catch {
      conv.title = oldTitle; // rollback on failure
    }
  }
}

// ============================
// Auth
// ============================

async function handleAuthSubmit() {
  const name = username.value.trim();
  const secret = password.value.trim();
  if (!name || !secret || authLoading.value) return;

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
    startHeartbeat();
    await refreshConversationList();
    if (conversations.value.length > 0) {
      await loadConversation(conversations.value[0].id);
    } else {
      await startNewConversation();
    }
    status.value = authMode.value === "login" ? "登录成功" : "注册并登录成功";
    statusTone.value = "ok";
    startSessionCheck();
  } catch (error) {
    status.value = `认证失败：${error.message}`;
    statusTone.value = "error";
  } finally {
    authLoading.value = false;
  }
}

function handleLogout() {
  stopHeartbeat();
  stopSessionCheck();
  setToken("");
  authenticated.value = false;
  currentUser.value = null;
  activeConvId.value = null;
  conversations.value = [];
  messages.value = [];
  status.value = "已退出登录";
  statusTone.value = "pending";
}

// ============================
// Scroll
// ============================

let _scrollRaf = null;
function scrollToBottom() {
  if (_scrollRaf) return;
  _scrollRaf = requestAnimationFrame(() => {
    _scrollRaf = null;
    const el = messageListRef.value;
    if (el) {
      el.scrollTop = el.scrollHeight;
    }
  });
}

// ============================
// Send
// ============================

async function handleSend() {
  const content = input.value.trim();
  if (!content || sending.value || !authenticated.value) return;

  const pendingAssistantId = `assistant-pending-${Date.now()}`;
  pushMessage("user", content, new Date().toLocaleString());
  messages.value.push({
    id: pendingAssistantId,
    role: "assistant",
    text: "",
    meta: "思考中",
  });
  input.value = "";
  sending.value = true;
  scrollToBottom();

  try {
    await streamChatMessage(content, activeConvId.value, {
      onIntent(payload) {
        const target = messages.value.find((m) => m.id === pendingAssistantId);
        if (target) {
          const agentLabel = payload?.target_agent === "emotional" ? "情感陪伴" : "AI 助手";
          target.meta = `识别意图: ${payload?.intent || "unknown"} → ${agentLabel}`;
          target.text = "";
        }
      },
      onChunk(payload) {
        const target = messages.value.find((m) => m.id === pendingAssistantId);
        if (target) {
          target.text += payload?.content || "";
          target.meta = "回复中";
        }
        scrollToBottom();
      },
      onDone(payload) {
        const target = messages.value.find((m) => m.id === pendingAssistantId);
        if (target) {
          target.text =
            payload?.assistant_message?.content || target.text || "我在这里陪着你。";
          target.meta = payload?.assistant_message?.created_at
            ? new Date(payload.assistant_message.created_at).toLocaleString()
            : "已完成";
        }
        // Update conversation id from the response
        if (payload?.conversation_id) {
          activeConvId.value = payload.conversation_id;
        }
        // Refresh the conversation list to get the new title
        refreshConversationList();
        historyLoaded.value = false;
        status.value = "对话正常";
        statusTone.value = "ok";
        scrollToBottom();
      },
      onError(payload) {
        const target = messages.value.find((m) => m.id === pendingAssistantId);
        if (target) {
          target.text = payload?.message || "流式输出失败。";
          target.meta = "请求失败";
        }
        scrollToBottom();
      },
    });
  } catch (error) {
    const target = messages.value.find((m) => m.id === pendingAssistantId);
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
  if (event.key !== "Enter" || event.shiftKey || event.isComposing) return;
  event.preventDefault();
  handleSend();
}

function autoResizeTextarea(event) {
  const el = event.target;
  el.style.height = "auto";
  el.style.height = `${Math.min(el.scrollHeight, 200)}px`;
}

onMounted(() => {
  console.log("[app] Mounted, starting initialization...");
  isMobile.value = window.innerWidth <= 640;
  loadHealth();
  restoreSession();
  loadDesktopVersion();
  setupUpdateListener();
  checkDesktopUpdate();
  startPeriodicUpdateCheck();
});
</script>

<template>
  <div class="app" :class="{ 'electron-fullscreen': isElectron }">
    <!-- Desktop update notification -->
    <div v-if="updateInfo && !updateDismissed" class="update-banner">
      <div class="update-banner-content">
        <span class="update-icon">📦</span>
        <span>
          <strong>发现新版本 {{ updateInfo.latestVersion }}</strong>
          （当前 {{ updateInfo.currentVersion }}）
        </span>
        <button class="update-btn" @click="openReleaseUrl">查看详情</button>
        <button class="update-close" @click="dismissUpdate" title="忽略">✕</button>
      </div>
      <div v-if="updateInfo.releaseNotes" class="update-release-notes">
        <pre>{{ updateInfo.releaseNotes }}</pre>
      </div>
    </div>

    <!-- Auth -->
    <main v-if="!authenticated" class="auth">
      <div class="auth-card">
        <div v-if="kickedMessage" class="kicked-banner">{{ kickedMessage }}</div>
        <div class="auth-icon">💬</div>
        <h1 class="auth-title">情感陪伴</h1>
        <p class="auth-subtitle">登录后自动恢复你的历史对话</p>

        <div class="auth-status">
          <span class="dot" :data-tone="statusTone"></span>
          <span>{{ status }}</span>
        </div>

        <form class="auth-form" @submit.prevent="handleAuthSubmit">
          <div class="field">
            <input
              v-model="username"
              type="text"
              autocomplete="username"
              placeholder="用户名"
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
          <button class="btn btn-primary btn-block" type="submit" :disabled="authLoading">
            {{ authButtonText }}
          </button>
        </form>

        <button class="link-btn" type="button" @click="authMode = authMode === 'login' ? 'register' : 'login'">
          {{ authMode === "login" ? "没有账号？去注册" : "已有账号？去登录" }}
        </button>
      </div>
    </main>

    <!-- Chat -->
    <main v-else class="chat-layout">
      <!-- Overlay for mobile sidebar -->
      <div
        v-if="sidePanelOpen && isMobile"
        class="overlay"
        @click="sidePanelOpen = false"
      ></div>

      <!-- Conversation sidebar -->
      <aside class="side" :class="{ open: sidePanelOpen }">
        <div class="side-head">
          <span class="side-title">历史对话</span>
          <button class="btn ghost" type="button" @click="startNewConversation">新对话</button>
        </div>
        <div class="side-list">
          <div
            v-for="conv in conversations"
            :key="conv.id"
            class="side-item"
            :class="{ active: conv.id === activeConvId }"
            @click="loadConversation(conv.id)"
          >
            <div
              v-if="renamingConvId === conv.id"
              class="side-item-title"
              @click.stop
            >
              <input
                class="rename-input"
                v-model="renamingTitle"
                @keydown.enter.prevent="submitRename"
                @keydown.escape.prevent="cancelRename"
                @blur="submitRename"
                @click.stop
              />
            </div>
            <div
              v-else
              class="side-item-title"
              @dblclick.stop="startRename(conv)"
              :title="conv.title"
            >
              {{ conv.title }}
              <button
                class="side-rename"
                type="button"
                title="重命名"
                @click.stop="startRename(conv)"
              >✎</button>
            </div>
            <div class="side-item-meta">{{ conv.message_count }} 条消息</div>
            <button
              class="side-del"
              type="button"
              title="删除"
              @click.stop="handleDeleteConversation(conv.id)"
            >×</button>
          </div>
          <div v-if="conversations.length === 0" class="side-empty">暂无历史对话</div>
        </div>
      </aside>

      <!-- Main chat area -->
      <div class="chat">
        <header class="chat-head">
          <div class="chat-head-left">
            <button class="btn ghost menu-btn" type="button" @click="sidePanelOpen = !sidePanelOpen">
              ☰
            </button>
            <span class="dot" :data-tone="statusTone"></span>
            <span class="chat-name">{{ currentUser?.username }}</span>
          </div>
          <div class="chat-head-right">
            <button class="btn ghost" type="button" @click="startNewConversation">新对话</button>
            <span v-if="desktopVersion" class="version-in-head">
              <span class="version-badge">v{{ desktopVersion }}</span>
              <button
                v-if="!updateChecking"
                class="version-check-btn"
                type="button"
                title="检查更新"
                @click="checkDesktopUpdate"
              >↻</button>
              <span v-else class="version-checking">↻</span>
            </span>
            <button class="btn ghost" type="button" @click="handleLogout">退出</button>
          </div>
        </header>

        <div ref="messageListRef" class="msgs" @scroll="onMessageListScroll">
          <div v-if="loadingOlder" class="load-hint">加载中...</div>
          <div v-else-if="hasMoreMessages" class="load-hint">向上滚动加载更多</div>

          <div v-if="!activeConvId && messages.length === 0" class="empty-state">
            <p>点击"新对话"开始聊天</p>
          </div>

          <div
            v-for="m in messages"
            :key="m.id"
            class="msg"
            :class="[m.role, { pending: m.role === 'assistant' && !m.text }]"
          >
            <div class="msg-bubble">
              <div v-if="m.role === 'assistant' && !m.text" class="thinking">
                <span class="dot-pulse"></span>
                <span class="dot-pulse"></span>
                <span class="dot-pulse"></span>
              </div>
              <div v-else v-html="mdRenderer(m.text)"></div>
            </div>
            <span v-if="m.meta" class="msg-meta">{{ m.meta }}</span>
          </div>
        </div>

        <form class="composer" @submit.prevent="handleSend">
          <textarea
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
      </div>

      <!-- Desktop version badge & manual update check (hidden in Electron, shown in browser) -->
      <div v-if="desktopVersion && !isElectron" class="desktop-version">
        <span>
          LangWeave Desktop v{{ desktopVersion }}
          <button
            v-if="!updateChecking"
            class="version-check-btn"
            type="button"
            title="检查更新"
            @click="checkDesktopUpdate"
          >检查更新</button>
          <span v-else class="version-checking">检查中…</span>
        </span>
      </div>
    </main>
  </div>
</template>

<style>
/* ===== Reset ===== */
*,*::before,*::after { margin:0; padding:0; box-sizing:border-box; }

:root {
  --bg: #efe7e0;
  --fg: #2c1810;
  --fg2: #7a5a4a;
  --fg3: #b09080;
  --accent: #d9735a;
  --accent-hover: #c05e46;
  --accent-soft: #f5ddd5;
  --surface: #fff;
  --border: #e6d9d0;
  --shadow-sm: 0 1px 2px rgba(0,0,0,0.04);
  --shadow-md: 0 4px 12px rgba(0,0,0,0.06);
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

/* ===== Desktop Update Banner ===== */
.update-banner {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  z-index: 9999;
  background: #2c1810;
  color: #fff;
  padding: 0.6rem 1rem;
  font-size: 0.85rem;
  display: flex;
  justify-content: center;
  animation: slideDown 0.3s ease;
}
@keyframes slideDown {
  from { transform: translateY(-100%); opacity: 0; }
  to { transform: translateY(0); opacity: 1; }
}
.update-banner-content {
  display: flex;
  align-items: center;
  gap: 0.6rem;
  flex-wrap: wrap;
  justify-content: center;
}
.update-icon { font-size: 1.1rem; }
.update-btn {
  background: var(--accent);
  color: #fff;
  border: none;
  border-radius: 6px;
  padding: 0.35rem 0.8rem;
  font-size: 0.82rem;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.2s;
}
.update-btn:hover { background: var(--accent-hover); }
.update-close {
  background: transparent;
  color: #fff;
  border: none;
  font-size: 1rem;
  cursor: pointer;
  opacity: 0.6;
  padding: 0.1rem 0.3rem;
  line-height: 1;
}
.update-close:hover { opacity: 1; }

/* ===== Layout ===== */
.app {
  display: flex;
  justify-content: center;
  min-height: 100dvh;
  background:
    radial-gradient(ellipse 600px 400px at 10% 0%, rgba(217,115,90,0.10) 0%, transparent 70%),
    radial-gradient(ellipse 500px 500px at 90% 100%, rgba(160,128,112,0.08) 0%, transparent 70%);
}

main { width: 100%; }

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
.ghost:hover { background: var(--accent-soft); color: var(--accent-hover); }

.link-btn {
  background: none;
  border: none;
  font-size: 0.82rem;
  color: var(--accent);
  cursor: pointer;
  padding: 0.25rem 0;
  transition: opacity 0.15s;
}
.link-btn:hover { opacity: 0.75; }

.dot {
  display: inline-block;
  width: 7px; height: 7px;
  border-radius: 50%;
  background: #bbb;
  transition: background 0.3s;
  flex-shrink: 0;
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
  max-width: 360px;
  background: var(--surface);
  border-radius: 20px;
  padding: 2.5rem 2rem 2rem;
  text-align: center;
  box-shadow: 0 8px 40px rgba(0,0,0,0.06);
}

.auth-icon {
  font-size: 2.5rem;
  margin-bottom: 0.75rem;
  line-height: 1;
}

.auth-title {
  font-size: 1.35rem;
  font-weight: 650;
  margin-bottom: 0.3rem;
}

.auth-subtitle {
  font-size: 0.82rem;
  color: var(--fg2);
  margin-bottom: 1.25rem;
}

.auth-status {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.4rem;
  font-size: 0.78rem;
  color: var(--fg2);
  margin-bottom: 1.25rem;
}

.auth-form {
  display: flex;
  flex-direction: column;
  gap: 0.6rem;
  margin-bottom: 0.75rem;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

/* ===== Chat Layout ===== */
.chat-layout {
  display: flex;
  width: 100%;
  height: 100dvh;
  max-width: 900px;
  margin: 0 auto;
  position: relative;
}

/* --- Overlay for mobile --- */
.overlay {
  position: fixed;
  inset: 0;
  background: rgba(0,0,0,0.3);
  z-index: 9;
}

/* --- Sidebar --- */
.side {
  width: 260px;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  border-right: 1px solid var(--border);
  background: var(--surface);
  z-index: 10;
  overflow: hidden;
}

.side-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-shrink: 0;
  padding: 0.7rem 0.75rem;
  border-bottom: 1px solid var(--border);
}

.side-title {
  font-size: 0.85rem;
  font-weight: 600;
}

.side-list {
  flex: 1;
  overflow-y: auto;
  padding: 0.35rem 0;
}

.side-item {
  display: flex;
  flex-direction: column;
  padding: 0.55rem 0.75rem;
  cursor: pointer;
  border-left: 3px solid transparent;
  transition: background 0.15s;
  position: relative;
}
.side-item:hover { background: var(--accent-soft); }
.side-item.active {
  background: var(--accent-soft);
  border-left-color: var(--accent);
}

.side-item-title {
  font-size: 0.82rem;
  font-weight: 500;
  color: var(--fg);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  padding-right: 1.2rem;
  display: flex;
  align-items: center;
  gap: 0.2rem;
}

.side-rename {
  background: none;
  border: none;
  font-size: 0.7rem;
  color: var(--fg3);
  cursor: pointer;
  padding: 0 0.15rem;
  line-height: 1;
  border-radius: 3px;
  opacity: 0;
  transition: opacity 0.15s, background 0.15s;
  flex-shrink: 0;
}
.side-item:hover .side-rename { opacity: 0.5; }
.side-rename:hover { opacity: 1 !important; background: rgba(0,0,0,0.05); }

.rename-input {
  width: 100%;
  border: 1px solid var(--accent);
  border-radius: 4px;
  padding: 0.15rem 0.3rem;
  font-family: var(--font);
  font-size: 0.82rem;
  font-weight: 500;
  outline: none;
  background: var(--surface);
  color: var(--fg);
}

.side-item-meta {
  font-size: 0.68rem;
  color: var(--fg3);
  margin-top: 0.1rem;
}

.side-del {
  position: absolute;
  top: 0.35rem;
  right: 0.35rem;
  background: none;
  border: none;
  font-size: 1rem;
  color: var(--fg3);
  cursor: pointer;
  padding: 0.1rem 0.3rem;
  border-radius: 4px;
  line-height: 1;
  opacity: 0;
  transition: opacity 0.15s, background 0.15s;
}
.side-item:hover .side-del { opacity: 0.6; }
.side-del:hover { background: rgba(0,0,0,0.06); opacity: 1 !important; }

.side-empty {
  text-align: center;
  font-size: 0.78rem;
  color: var(--fg3);
  padding: 2rem 0;
}

/* --- Main Chat --- */
.chat {
  flex: 1;
  display: flex;
  flex-direction: column;
  height: 100dvh;
  min-width: 0;
  background: var(--surface);
}

/* --- Menu button (mobile) --- */
.menu-btn {
  display: none;
  font-size: 1.1rem;
  padding: 0.15rem 0.35rem;
  line-height: 1;
}

/* --- Header --- */
.chat-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-shrink: 0;
  padding: 0.75rem 1rem;
}

.chat-head-left {
  display: flex;
  align-items: center;
  gap: 0.45rem;
}

.chat-name {
  font-size: 0.88rem;
  font-weight: 600;
}

.chat-head-right {
  display: flex;
  align-items: center;
  gap: 0.15rem;
}

/* --- Version in head (Electron) --- */
.version-in-head {
  display: inline-flex;
  align-items: center;
  gap: 0.2rem;
  margin: 0 0.3rem;
  user-select: none;
}
.version-badge {
  font-size: 0.68rem;
  color: var(--fg3);
  background: rgba(0,0,0,0.04);
  padding: 0.1rem 0.35rem;
  border-radius: 4px;
  line-height: 1.4;
}

/* --- Messages --- */
.msgs {
  flex: 1;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 0.6rem;
  padding: 0.75rem 1rem;
  scroll-behavior: smooth;
}

.msgs::-webkit-scrollbar { width: 4px; }
.msgs::-webkit-scrollbar-thumb { background: var(--border); border-radius: 4px; }

.load-hint {
  text-align: center;
  font-size: 0.68rem;
  color: var(--fg3);
  padding: 0.5rem 0;
  user-select: none;
}

.msg {
  display: flex;
  flex-direction: column;
  max-width: 78%;
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
  padding: 0.6rem 0.95rem;
  border-radius: 1.2rem;
  line-height: 1.55;
  font-size: 0.9rem;
  max-width: 100%;
  word-wrap: break-word;
  overflow-wrap: break-word;
}

/* --- MD content inside bubbles --- */
.msg-bubble p {
  margin: 0.2em 0;
}
.msg-bubble p:first-child { margin-top: 0; }
.msg-bubble p:last-child { margin-bottom: 0; }
.msg-bubble ul, .msg-bubble ol {
  margin: 0.3em 0;
  padding-left: 1.3em;
}
.msg-bubble li { margin: 0.15em 0; }
.msg-bubble code {
  font-family: "SF Mono", "JetBrains Mono", "Fira Code", monospace;
  font-size: 0.82em;
  padding: 0.1em 0.35em;
  border-radius: 4px;
  background: rgba(0,0,0,0.06);
}
.msg.user .msg-bubble code {
  background: rgba(255,255,255,0.2);
}
.msg-bubble pre {
  margin: 0.4em 0;
  padding: 0.6em 0.8em;
  border-radius: 8px;
  background: rgba(0,0,0,0.04);
  overflow-x: auto;
}
.msg.user .msg-bubble pre {
  background: rgba(0,0,0,0.15);
}
.msg-bubble pre code {
  background: none;
  padding: 0;
  font-size: 0.82em;
}
.msg-bubble blockquote {
  margin: 0.4em 0;
  padding: 0.2em 0.6em;
  border-left: 3px solid var(--accent);
  opacity: 0.85;
}
.msg-bubble a {
  color: inherit;
  text-decoration: underline;
  text-underline-offset: 2px;
  opacity: 0.9;
}
.msg.user .msg-bubble a { opacity: 0.85; }
.msg-bubble a:hover { opacity: 1; }
.msg-bubble hr {
  border: none;
  border-top: 1px solid var(--border);
  margin: 0.5em 0;
}
.msg-bubble strong { font-weight: 650; }
.msg-bubble em { font-style: italic; }
.msg-bubble del { text-decoration: line-through; opacity: 0.7; }
.msg-bubble h3 {
  font-size: 1.05em;
  font-weight: 650;
  margin: 0.4em 0 0.2em;
}
.msg-bubble h4 {
  font-size: 0.95em;
  font-weight: 600;
  margin: 0.3em 0 0.15em;
}

.msg.user .msg-bubble {
  background: var(--accent);
  color: #fff;
  border-bottom-right-radius: 0.3rem;
}

.msg.assistant .msg-bubble {
  background: #f7f2ed;
  color: var(--fg);
  border-bottom-left-radius: 0.3rem;
}

.msg-meta {
  font-size: 0.58rem;
  color: var(--fg3);
  margin-top: 0.2rem;
  padding: 0 0.2rem;
}

.msg.user .msg-meta { color: var(--fg3); }

/* --- Thinking animation (3 bouncing dots) --- */
.thinking {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 0.15rem 0;
  min-height: 1.2em;
}
.dot-pulse {
  display: inline-block;
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: var(--fg3);
  animation: pulse 1.4s ease-in-out infinite both;
}
.dot-pulse:nth-child(1) { animation-delay: 0s; }
.dot-pulse:nth-child(2) { animation-delay: 0.2s; }
.dot-pulse:nth-child(3) { animation-delay: 0.4s; }

@keyframes pulse {
  0%, 80%, 100% { transform: scale(0.6); opacity: 0.4; }
  40% { transform: scale(1); opacity: 1; }
}

/* --- Empty state --- */
.empty-state {
  display: flex;
  align-items: center;
  justify-content: center;
  flex: 1;
  font-size: 0.88rem;
  color: var(--fg3);
}
.empty-state p { padding: 2rem; }

/* --- Composer --- */
.composer {
  flex-shrink: 0;
  display: flex;
  align-items: flex-end;
  gap: 0.5rem;
  padding: 0.75rem 1rem;
  padding-bottom: calc(0.75rem + env(safe-area-inset-bottom, 0px));
  border-top: 1px solid var(--border);
}

.composer .ta {
  flex: 1;
  border-radius: 1.25rem;
  resize: none;
  padding: 0.55rem 0.85rem;
  font-size: 0.88rem;
  line-height: 1.5;
  max-height: 120px;
}

.composer .send {
  flex-shrink: 0;
  border-radius: 2rem;
  padding: 0.5rem 1.1rem;
  font-size: 0.82rem;
}

/* ===== Mobile ===== */
@media (max-width: 640px) {
  html { font-size: 15px; }

  /* --- Auth --- */
  .auth { padding: 1rem; }
  .auth-card {
    max-width: 100%;
    border-radius: 16px;
    padding: 2rem 1.5rem 1.5rem;
  }
  .auth-icon { font-size: 2rem; }
  .auth-title { font-size: 1.2rem; }
  .auth-status { font-size: 0.75rem; }
  .auth-form { gap: 0.5rem; }
  .auth .input {
    padding: 0.75rem 0.85rem;
    font-size: 16px; /* prevent iOS zoom on focus */
  }

  /* --- Chat --- */
  .chat-layout { max-width: 100%; }

  .chat {
    max-width: 100%;
    box-shadow: none;
    min-height: 100dvh;
  }

  .chat-head {
    padding: 0.5rem 0.65rem;
    padding-top: calc(0.5rem + env(safe-area-inset-top, 0px));
  }
  .chat-name { font-size: 0.85rem; }
  .chat-head-right { gap: 0; }
  .chat-head-right .ghost {
    padding: 0.35rem 0.5rem;
    font-size: 0.75rem;
  }

  /* --- Sidebar on mobile --- */
  .menu-btn { display: inline-flex; }

  .side {
    position: fixed;
    top: 0;
    left: 0;
    bottom: 0;
    width: 280px;
    transform: translateX(-100%);
    transition: transform 0.25s ease;
    box-shadow: 2px 0 12px rgba(0,0,0,0.1);
  }
  .side.open { transform: translateX(0); }

  .msgs {
    flex: 1;
    padding: 0.6rem 0.65rem;
    gap: 0.5rem;
    -webkit-overflow-scrolling: touch;
    overscroll-behavior: contain;
    touch-action: pan-y;
  }

  .msg { max-width: 88%; }

  .msg-bubble {
    padding: 0.55rem 0.8rem;
    font-size: 0.88rem;
    border-radius: 1rem;
  }

  .msg-meta { font-size: 0.55rem; }

  .composer {
    padding: 0.5rem 0.65rem;
    padding-bottom: calc(0.5rem + env(safe-area-inset-bottom, 0px));
    gap: 0.4rem;
  }

  .composer .ta {
    padding: 0.45rem 0.75rem;
    font-size: 16px; /* prevent iOS zoom */
    max-height: 100px;
  }

  .composer .send {
    padding: 0.5rem 0.9rem;
    font-size: 0.8rem;
  }
}

@media (max-width: 400px) {
  .msg { max-width: 95%; }
  .auth-card { padding: 1.5rem 1.25rem 1.25rem; }
  .chat-head { padding: 0.4rem 0.5rem; }
  .msgs { padding: 0.4rem 0.5rem; }
  .composer { padding: 0.4rem 0.5rem; gap: 0.35rem; }
}

/* ===== Desktop version badge ===== */
.desktop-version {
  text-align: center;
  padding: 0.35rem 0 0.5rem;
  font-size: 0.65rem;
  color: var(--fg3);
  user-select: none;
  cursor: default;
}
.desktop-version span {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
}
.version-check-btn {
  background: transparent;
  border: 1px solid var(--border);
  border-radius: 4px;
  padding: 0.1rem 0.4rem;
  font-size: 0.6rem;
  color: var(--fg2);
  cursor: pointer;
  transition: background 0.15s, border-color 0.15s;
  line-height: 1.5;
}
.version-check-btn:hover {
  background: var(--accent-soft);
  border-color: var(--accent);
  color: var(--accent-hover);
}
.version-checking {
  font-size: 0.6rem;
  color: var(--accent);
}

/* ===== Update release notes ===== */
.update-release-notes {
  max-height: 120px;
  overflow-y: auto;
  margin-top: 0.35rem;
  padding: 0.4rem 0.6rem;
  background: rgba(0,0,0,0.04);
  border-radius: 6px;
  font-size: 0.75rem;
  line-height: 1.4;
  color: var(--fg2);
}
.update-release-notes pre {
  font-family: inherit;
  white-space: pre-wrap;
  word-break: break-word;
}

/* ===== Kicked banner ===== */
.kicked-banner {
  background: #fef0f0;
  color: #d06050;
  border: 1px solid #f5c6c6;
  border-radius: 8px;
  padding: 0.6rem 0.85rem;
  margin-bottom: 1rem;
  font-size: 0.82rem;
  font-weight: 500;
  text-align: center;
}

/* ===== Electron fullscreen override ===== */
.electron-fullscreen {
  --radius: 0;
}
.electron-fullscreen .app {
  min-height: 100vh;
}
.electron-fullscreen .chat-layout {
  max-width: none;
  height: 100vh;
  box-shadow: none;
}
.electron-fullscreen .auth-card {
  max-width: 400px;
}
.electron-fullscreen .msgs {
  padding: 0.75rem 1.5rem;
}
.electron-fullscreen .composer {
  padding: 0.75rem 1.5rem;
}
.electron-fullscreen .chat-head {
  padding: 0.6rem 1.5rem;
}
.electron-fullscreen .side {
  width: 280px;
}
</style>
