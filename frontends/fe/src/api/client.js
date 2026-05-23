const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL?.replace(/\/$/, "") || "";

export function getToken() {
  return window.localStorage.getItem("langweave_token") || "";
}

export function setToken(token) {
  if (token) {
    window.localStorage.setItem("langweave_token", token);
    return;
  }
  window.localStorage.removeItem("langweave_token");
}

async function request(path, options = {}) {
  const token = getToken();
  const headers = {
    "Content-Type": "application/json",
    ...(options.headers || {}),
  };

  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }

  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers,
  });

  let payload = null;
  try {
    payload = await response.json();
  } catch {
    payload = null;
  }

  if (!response.ok) {
    const detail =
      payload?.detail ||
      payload?.message ||
      `Request failed with status ${response.status}`;
    throw new Error(detail);
  }

  return payload;
}

export function checkHealth() {
  return request("/health", { method: "GET" });
}

export function login(username, password) {
  return request("/api/v1/auth/login", {
    method: "POST",
    body: JSON.stringify({ username, password }),
  });
}

export function register(username, password) {
  return request("/api/v1/auth/register", {
    method: "POST",
    body: JSON.stringify({ username, password }),
  });
}

export function getCurrentUser() {
  return request("/api/v1/auth/me", {
    method: "GET",
  });
}

// --- Conversations ---

/** List all conversations for the current user. */
export function listConversations() {
  return request("/api/v1/emotional-chat/conversations", { method: "GET" });
}

/**
 * Fetch paginated chat history for a specific conversation.
 *
 * Messages are returned oldest-first.
 * Use offset=0, limit=50 for the most recent 50, etc.
 */
export function fetchChatHistory(conversationId, offset = 0, limit = 50) {
  return request(
    `/api/v1/emotional-chat/history?conversation_id=${conversationId}&offset=${offset}&limit=${limit}`,
    { method: "GET" },
  );
}

export function sendEmotionalMessage(message, conversationId) {
  return request("/api/v1/emotional-chat/messages", {
    method: "POST",
    body: JSON.stringify({ message, conversation_id: conversationId }),
  });
}

export function resetChatHistory(conversationId) {
  return request(
    `/api/v1/emotional-chat/history?conversation_id=${conversationId}`,
    { method: "DELETE" },
  );
}

export function deleteConversation(conversationId) {
  return request(`/api/v1/emotional-chat/conversations/${conversationId}`, {
    method: "DELETE",
  });
}

export async function streamEmotionalMessage(message, conversationId, handlers = {}) {
  const token = getToken();
  const response = await fetch(`${API_BASE_URL}/api/v1/emotional-chat/stream`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify({ message, conversation_id: conversationId }),
  });

  if (!response.ok || !response.body) {
    let detail = `Request failed with status ${response.status}`;
    try {
      const payload = await response.json();
      detail = payload?.detail || payload?.message || detail;
    } catch {
      // Ignore parse errors and keep generic message.
    }
    throw new Error(detail);
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder("utf-8");
  let buffer = "";

  while (true) {
    const { value, done } = await reader.read();
    buffer += decoder.decode(value || new Uint8Array(), { stream: !done });

    const parts = buffer.split("\n\n");
    buffer = parts.pop() || "";

    for (const part of parts) {
      const line = part
        .split("\n")
        .find((item) => item.startsWith("data: "));
      if (!line) {
        continue;
      }
      const parsed = JSON.parse(line.slice(6));
      const event = parsed?.event;
      const payload = parsed?.payload;

      if (event === "chunk") {
        handlers.onChunk?.(payload);
      } else if (event === "done") {
        handlers.onDone?.(payload);
      } else if (event === "error") {
        handlers.onError?.(payload);
      }
    }

    if (done) {
      break;
    }
  }
}

// --- Heartbeat ---

export async function sendHeartbeat() {
  const token = getToken();
  if (!token) return;
  try {
    await request("/api/v1/heartbeat/ping", { method: "POST" });
  } catch {
    // silent — don't spam logs
  }
}
