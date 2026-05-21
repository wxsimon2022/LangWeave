<script setup>
import { computed, onMounted, ref } from "vue";

import { checkHealth, sendEmotionalMessage } from "./api/chat";

const input = ref("");
const sending = ref(false);
const threadId = ref("");
const status = ref("正在连接后端...");
const statusTone = ref("pending");
const messages = ref([
  {
    id: "welcome",
    role: "assistant",
    text: "我在这里。你可以慢慢说，最近让你最累的一件事是什么？",
    meta: "情感陪伴助手",
  },
]);

const canSend = computed(() => input.value.trim().length > 0 && !sending.value);

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

async function handleSend() {
  const content = input.value.trim();
  if (!content || sending.value) {
    return;
  }

  pushMessage("user", content, threadId.value ? `会话 ${threadId.value}` : "新会话");
  input.value = "";
  sending.value = true;

  try {
    const result = await sendEmotionalMessage(content, threadId.value || null);
    threadId.value = result.threadId || "";
    pushMessage(
      "assistant",
      result.reply || "我听见你了，如果你愿意，可以再多说一点。",
      threadId.value ? `thread_id: ${threadId.value}` : "已回复"
    );
    status.value = "对话正常";
    statusTone.value = "ok";
  } catch (error) {
    pushMessage("assistant", "我这边暂时没有连上后端服务。你可以先检查服务是否启动。", "请求失败");
    status.value = `发送失败：${error.message}`;
    statusTone.value = "error";
  } finally {
    sending.value = false;
  }
}

function handleReset() {
  threadId.value = "";
  input.value = "";
  messages.value = [
    {
      id: "welcome",
      role: "assistant",
      text: "新的对话已经开始了。想从哪里说起，都可以。",
      meta: "情感陪伴助手",
    },
  ];
  status.value = "会话已重置";
  statusTone.value = "pending";
}

onMounted(() => {
  loadHealth();
});
</script>

<template>
  <div class="page-shell">
    <div class="background-orb orb-left"></div>
    <div class="background-orb orb-right"></div>

    <main class="app-frame">
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
      </section>

      <section class="chat-panel">
        <header class="chat-header">
          <div>
            <p class="chat-title">对话窗口</p>
            <p class="chat-subtitle">建议直接说情绪、压力、关系困扰或最近让你难受的事。</p>
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
          ></textarea>

          <div class="composer-actions">
            <p class="composer-tip">
              前端调用接口：`POST /api/v1/agents/emotional/chat`
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
