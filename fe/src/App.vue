<script setup>
import { computed, onMounted, ref } from "vue";

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
      await loadHistory();
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

async function loadHistory() {
  const response = await fetchChatHistory();
  const history = response?.data;
  threadId.value = history?.thread_id || "";
  const items = Array.isArray(history?.messages) ? history.messages.map(toUiMessage) : [];
  if (items.length > 0) {
    messages.value = items;
    return;
  }
  resetWelcomeMessage();
}

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
    await loadHistory();
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
  resetWelcomeMessage();
  status.value = "已退出登录";
  statusTone.value = "pending";
}

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
    resetWelcomeMessage("新的对话已经开始了。想从哪里说起，都可以。");
    status.value = "会话已重置并清空历史";
    statusTone.value = "ok";
  } catch (error) {
    status.value = `重置失败：${error.message}`;
    statusTone.value = "error";
  }
}

onMounted(() => {
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
              登录后会自动保存聊天记录，下次打开页面会恢复同一账号的历史消息。
            </p>
          </div>
          <button class="ghost-button" type="button" @click="handleReset">新对话</button>
        </header>

        <div class="message-list">
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
            rows="4"
            placeholder="比如：最近总觉得很焦虑，晚上也睡不好。"
            @keydown="handleComposerKeydown"
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
