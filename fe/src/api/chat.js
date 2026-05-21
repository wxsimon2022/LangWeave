const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL?.replace(/\/$/, "") || "http://127.0.0.1:8000";

async function request(path, options) {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...(options?.headers || {}),
    },
    ...options,
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

export async function sendEmotionalMessage(message, threadId) {
  const payload = await request("/api/v1/agents/emotional/chat", {
    method: "POST",
    body: JSON.stringify({
      message,
      thread_id: threadId || null,
    }),
  });

  return {
    reply: payload?.data?.content || "",
    threadId: payload?.data?.thread_id || threadId || null,
    raw: payload,
  };
}

export async function checkHealth() {
  return request("/health", {
    method: "GET",
  });
}
