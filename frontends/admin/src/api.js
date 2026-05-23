const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL?.replace(/\/$/, "") || "";

function getToken() {
  return window.localStorage.getItem("langweave_admin_token") || "";
}

function setToken(token) {
  if (token) {
    window.localStorage.setItem("langweave_admin_token", token);
    return;
  }
  window.localStorage.removeItem("langweave_admin_token");
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

// --- Auth ---

export function login(username, password) {
  return request("/api/v1/auth/login", {
    method: "POST",
    body: JSON.stringify({ username, password }),
  });
}

export function getCurrentUser() {
  return request("/api/v1/auth/me", { method: "GET" });
}

export { setToken, getToken };

// --- Admin ---

export function adminListUsers() {
  return request("/api/v1/admin/users", { method: "GET" });
}

export function adminDeleteUser(userId) {
  return request(`/api/v1/admin/users/${userId}`, { method: "DELETE" });
}

export function adminUpdatePassword(userId, newPassword) {
  return request(`/api/v1/admin/users/${userId}/password`, {
    method: "PUT",
    body: JSON.stringify({ new_password: newPassword }),
  });
}
