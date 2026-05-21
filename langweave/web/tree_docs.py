"""Directory-tree API documentation page (Swagger 2 spec)."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.responses import HTMLResponse

TREE_DOCS_HTML = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>LangWeave API 目录</title>
  <style>
    :root {
      --bg: #0f1419;
      --panel: #1a2332;
      --border: #2d3a4d;
      --text: #e6edf3;
      --muted: #8b9cb3;
      --accent: #3b82f6;
      --get: #22c55e;
      --post: #f59e0b;
      --put: #a855f7;
      --delete: #ef4444;
    }
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      font-family: "SF Pro Text", -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      background: var(--bg);
      color: var(--text);
      height: 100vh;
      display: flex;
      flex-direction: column;
    }
    header {
      padding: 12px 20px;
      border-bottom: 1px solid var(--border);
      display: flex;
      align-items: center;
      gap: 16px;
      flex-shrink: 0;
    }
    header h1 { font-size: 1.1rem; font-weight: 600; }
    header .meta { color: var(--muted); font-size: 0.85rem; }
    header a { color: var(--accent); text-decoration: none; font-size: 0.85rem; }
    .layout { display: flex; flex: 1; min-height: 0; }
    aside {
      width: 320px;
      border-right: 1px solid var(--border);
      overflow: auto;
      flex-shrink: 0;
      background: var(--panel);
    }
    .search {
      padding: 10px 12px;
      border-bottom: 1px solid var(--border);
      position: sticky;
      top: 0;
      background: var(--panel);
      z-index: 1;
    }
    .search input {
      width: 100%;
      padding: 8px 10px;
      border: 1px solid var(--border);
      border-radius: 6px;
      background: var(--bg);
      color: var(--text);
      font-size: 0.9rem;
    }
    #tree { padding: 8px 0 24px; font-size: 0.88rem; }
    .folder > .label, .endpoint > .label {
      padding: 6px 12px;
      cursor: pointer;
      display: flex;
      align-items: center;
      gap: 6px;
      user-select: none;
    }
    .folder > .label:hover, .endpoint > .label:hover { background: rgba(59,130,246,0.12); }
    .folder .children { display: none; padding-left: 12px; border-left: 1px solid var(--border); margin-left: 12px; }
    .folder.open > .children { display: block; }
    .chevron { width: 12px; color: var(--muted); transition: transform 0.15s; }
    .folder.open > .label .chevron { transform: rotate(90deg); }
    .method {
      font-size: 0.7rem;
      font-weight: 700;
      padding: 2px 6px;
      border-radius: 4px;
      min-width: 42px;
      text-align: center;
    }
    .method.GET { background: rgba(34,197,94,0.2); color: var(--get); }
    .method.POST { background: rgba(245,158,11,0.2); color: var(--post); }
    .method.PUT { background: rgba(168,85,247,0.2); color: var(--put); }
    .method.DELETE { background: rgba(239,68,68,0.2); color: var(--delete); }
    .endpoint.active > .label { background: rgba(59,130,246,0.2); }
    main {
      flex: 1;
      overflow: auto;
      padding: 24px 28px;
    }
    .empty { color: var(--muted); }
    .detail h2 { font-size: 1.25rem; margin-bottom: 8px; word-break: break-all; }
    .detail .summary { color: var(--muted); margin-bottom: 20px; }
    .detail section { margin-bottom: 24px; }
    .detail h3 { font-size: 0.95rem; margin-bottom: 10px; color: var(--muted); }
    pre {
      background: var(--panel);
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 12px;
      overflow: auto;
      font-size: 0.82rem;
      line-height: 1.5;
    }
    table { width: 100%; border-collapse: collapse; font-size: 0.88rem; }
    th, td { text-align: left; padding: 8px 10px; border-bottom: 1px solid var(--border); }
    th { color: var(--muted); font-weight: 500; }
    .badge { color: var(--accent); font-family: monospace; }
    .try-panel {
      margin-top: 24px;
      padding: 16px;
      background: var(--panel);
      border: 1px solid var(--border);
      border-radius: 10px;
    }
    .try-panel h3 { margin-bottom: 14px; color: var(--text); }
    .field { margin-bottom: 12px; }
    .field label {
      display: block;
      font-size: 0.8rem;
      color: var(--muted);
      margin-bottom: 4px;
    }
    .field input, .field textarea {
      width: 100%;
      padding: 8px 10px;
      border: 1px solid var(--border);
      border-radius: 6px;
      background: var(--bg);
      color: var(--text);
      font-size: 0.88rem;
      font-family: inherit;
    }
    .field textarea { min-height: 120px; font-family: ui-monospace, monospace; resize: vertical; }
    .btn-row { display: flex; gap: 10px; align-items: center; margin-top: 14px; flex-wrap: wrap; }
    button.primary {
      background: var(--accent);
      color: #fff;
      border: none;
      padding: 9px 18px;
      border-radius: 6px;
      font-size: 0.9rem;
      font-weight: 600;
      cursor: pointer;
    }
    button.primary:hover { filter: brightness(1.1); }
    button.primary:disabled { opacity: 0.5; cursor: not-allowed; }
    button.ghost {
      background: transparent;
      color: var(--muted);
      border: 1px solid var(--border);
      padding: 8px 14px;
      border-radius: 6px;
      cursor: pointer;
      font-size: 0.85rem;
    }
    .url-preview {
      font-family: ui-monospace, monospace;
      font-size: 0.82rem;
      color: var(--muted);
      word-break: break-all;
      flex: 1;
      min-width: 200px;
    }
    .response-panel { margin-top: 16px; }
    .response-meta {
      font-size: 0.85rem;
      margin-bottom: 8px;
      display: flex;
      gap: 12px;
      flex-wrap: wrap;
    }
    .status-ok { color: var(--get); }
    .status-err { color: var(--delete); }
    .response-body {
      max-height: 360px;
      overflow: auto;
    }
  </style>
</head>
<body>
  <header>
    <h1>LangWeave API</h1>
    <span class="meta" id="api-version"></span>
    __CLASSIC_LINK__
    <a href="__SPEC_URL__" target="_blank">swagger.json</a>
  </header>
  <div class="layout">
    <aside>
      <div class="search">
        <input type="search" id="filter" placeholder="搜索路径或说明…" />
      </div>
      <nav id="tree"></nav>
    </aside>
    <main id="main">
      <p class="empty">从左侧目录选择接口查看详情</p>
    </main>
  </div>
  <script>
    const SPEC_URL = "__SPEC_URL__";
    const METHODS = ["get", "post", "put", "patch", "delete", "head", "options"];

    function pathToTree(paths) {
      const root = { name: "", children: {}, endpoints: [] };
      for (const [path, item] of Object.entries(paths)) {
        for (const method of METHODS) {
          if (!item[method]) continue;
          const parts = path.split("/").filter(Boolean);
          let node = root;
          for (const part of parts) {
            if (!node.children[part]) {
              node.children[part] = { name: part, children: {}, endpoints: [] };
            }
            node = node.children[part];
          }
          node.endpoints.push({ method: method.toUpperCase(), path, op: item[method] });
        }
      }
      return root;
    }

    function sortKeys(obj) {
      return Object.keys(obj).sort((a, b) => a.localeCompare(b));
    }

    function renderTree(node, container, depth = 0) {
      for (const key of sortKeys(node.children)) {
        const child = node.children[key];
        const folder = document.createElement("div");
        folder.className = "folder" + (depth < 2 ? " open" : "");
        folder.innerHTML = `<div class="label"><span class="chevron">▶</span><span>${key}/</span></div>`;
        const childrenEl = document.createElement("div");
        childrenEl.className = "children";
        renderTree(child, childrenEl, depth + 1);
        child.endpoints
          .sort((a, b) => a.path.localeCompare(b.path) || a.method.localeCompare(b.method))
          .forEach((ep) => {
            const el = document.createElement("div");
            el.className = "endpoint";
            el.dataset.path = ep.path;
            el.dataset.method = ep.method;
            el.innerHTML = `<div class="label"><span class="method ${ep.method}">${ep.method}</span><span>${ep.path.split("/").pop() || ep.path}</span></div>`;
            el.querySelector(".label").onclick = () => selectEndpoint(el, ep);
            childrenEl.appendChild(el);
          });
        folder.querySelector(".label").onclick = () => folder.classList.toggle("open");
        folder.appendChild(childrenEl);
        container.appendChild(folder);
      }
    }

    let currentEl = null;
    let spec = null;
    let currentEp = null;

    function selectEndpoint(el, ep) {
      if (currentEl) currentEl.classList.remove("active");
      currentEl = el;
      el.classList.add("active");
      currentEp = ep;
      renderDetail(ep);
    }

    function resolveSchema(schema) {
      if (!schema) return {};
      if (schema.$ref && spec && spec.definitions) {
        const name = schema.$ref.split("/").pop();
        return spec.definitions[name] || schema;
      }
      return schema;
    }

    function defaultForParam(p) {
      if (p.default !== undefined) return String(p.default);
      if (p.example !== undefined) return String(p.example);
      if (p.name === "agent_name") return "assistant";
      if (p.name === "message") return "你好";
      return "";
    }

    function fieldHtml(p, prefix) {
      const id = prefix + "-" + p.name;
      const val = escapeHtml(defaultForParam(p));
      const req = p.required ? " *" : "";
      const desc = p.description ? ` — ${escapeHtml(p.description)}` : "";
      return `<div class="field">
        <label for="${id}">${escapeHtml(p.name)}${req}${desc}</label>
        <input type="text" id="${id}" data-in="${p.in}" data-name="${escapeHtml(p.name)}" value="${val}" />
      </div>`;
    }

    function renderDetail(ep) {
      const op = ep.op;
      const params = op.parameters || [];
      const bodyParam = params.find((p) => p.in === "body");
      const pathParams = params.filter((p) => p.in === "path");
      const queryParams = params.filter((p) => p.in === "query");
      const hasBody = ["POST", "PUT", "PATCH"].includes(ep.method) && bodyParam;

      let bodyExample = "{}";
      if (bodyParam && bodyParam.schema) {
        bodyExample = JSON.stringify(exampleFromSchema(resolveSchema(bodyParam.schema)), null, 2);
      }

      const pathFields = pathParams.map((p) => fieldHtml(p, "path")).join("");
      const queryFields = queryParams.map((p) => fieldHtml(p, "query")).join("");
      const bodyField = hasBody
        ? `<div class="field"><label for="req-body">请求体 JSON</label>
           <textarea id="req-body">${escapeHtml(bodyExample)}</textarea></div>`
        : "";

      document.getElementById("main").innerHTML = `
        <div class="detail">
          <h2><span class="method ${ep.method}" style="display:inline-block;margin-right:8px;">${ep.method}</span>${ep.path}</h2>
          <p class="summary">${escapeHtml(op.summary || "")}${op.description ? " — " + escapeHtml(op.description) : ""}</p>
          <div class="try-panel">
            <h3>在线调试</h3>
            ${pathFields}
            ${queryFields}
            ${bodyField}
            <div class="btn-row">
              <button type="button" class="primary" id="btn-send">发送请求</button>
              <button type="button" class="ghost" id="btn-reset">重置</button>
              <span class="url-preview" id="url-preview"></span>
            </div>
            <div class="response-panel" id="response-panel" style="display:none">
              <h3>响应结果</h3>
              <div class="response-meta" id="response-meta"></div>
              <pre class="response-body" id="response-body"></pre>
            </div>
          </div>
          ${pathParams.length ? `<section><h3>路径参数说明</h3>${paramTable(pathParams)}</section>` : ""}
          ${queryParams.length ? `<section><h3>查询参数说明</h3>${paramTable(queryParams)}</section>` : ""}
          <section><h3>响应定义</h3><pre>${escapeHtml(JSON.stringify(op.responses || {}, null, 2))}</pre></section>
        </div>`;

      document.getElementById("btn-send").onclick = () => sendRequest(ep);
      document.getElementById("btn-reset").onclick = () => renderDetail(ep);
      document.querySelectorAll(".try-panel input").forEach((inp) => {
        inp.addEventListener("input", () => updateUrlPreview(ep));
      });
      updateUrlPreview(ep);
    }

    function collectValues(prefix) {
      const vals = {};
      document.querySelectorAll(`.try-panel input[data-in="${prefix}"]`).forEach((inp) => {
        vals[inp.dataset.name] = inp.value;
      });
      return vals;
    }

    function buildUrl(ep) {
      const pathVals = collectValues("path");
      const queryVals = collectValues("query");
      let url = ep.path;
      for (const [k, v] of Object.entries(pathVals)) {
        url = url.replace("{" + k + "}", encodeURIComponent(v || ""));
      }
      const qs = new URLSearchParams();
      for (const [k, v] of Object.entries(queryVals)) {
        if (v !== "") qs.append(k, v);
      }
      const q = qs.toString();
      return url + (q ? "?" + q : "");
    }

    function updateUrlPreview(ep) {
      const el = document.getElementById("url-preview");
      if (el) el.textContent = ep.method + " " + buildUrl(ep);
    }

    async function sendRequest(ep) {
      const btn = document.getElementById("btn-send");
      const panel = document.getElementById("response-panel");
      const meta = document.getElementById("response-meta");
      const bodyEl = document.getElementById("response-body");
      const url = buildUrl(ep);
      btn.disabled = true;
      btn.textContent = "请求中…";
      panel.style.display = "block";
      meta.innerHTML = `<span>请求 ${escapeHtml(url)}</span>`;
      bodyEl.textContent = "";

      const opts = { method: ep.method, headers: {} };
      const bodyInput = document.getElementById("req-body");
      if (bodyInput && ["POST", "PUT", "PATCH"].includes(ep.method)) {
        try {
          const raw = bodyInput.value.trim();
          if (raw) {
            JSON.parse(raw);
            opts.headers["Content-Type"] = "application/json";
            opts.body = raw;
          }
        } catch (e) {
          meta.innerHTML = `<span class="status-err">请求体 JSON 无效</span>`;
          bodyEl.textContent = String(e);
          btn.disabled = false;
          btn.textContent = "发送请求";
          return;
        }
      }

      const t0 = performance.now();
      try {
        const res = await fetch(url, opts);
        const elapsed = Math.round(performance.now() - t0);
        const text = await res.text();
        let pretty = text;
        try { pretty = JSON.stringify(JSON.parse(text), null, 2); } catch (_) {}
        const cls = res.ok ? "status-ok" : "status-err";
        meta.innerHTML = `<span class="${cls}">${res.status} ${res.statusText}</span><span>${elapsed} ms</span>`;
        bodyEl.textContent = pretty || "(empty)";
      } catch (err) {
        meta.innerHTML = `<span class="status-err">网络错误</span>`;
        bodyEl.textContent = String(err);
      }
      btn.disabled = false;
      btn.textContent = "发送请求";
    }

    function paramTable(params) {
      if (!params.length) return "";
      const rows = params.map((p) =>
        `<tr><td class="badge">${p.name}</td><td>${p.type || (p.schema && p.schema.type) || "-"}</td><td>${p.required ? "是" : "否"}</td><td>${p.description || ""}</td></tr>`
      ).join("");
      return `<table><thead><tr><th>名称</th><th>类型</th><th>必填</th><th>说明</th></tr></thead><tbody>${rows}</tbody></table>`;
    }

    function exampleFromSchema(schema) {
      schema = resolveSchema(schema);
      if (schema.example) return schema.example;
      if (schema.$ref) return {};
      if (schema.type === "object") {
        const o = {};
        const props = schema.properties || {};
        for (const [k, v] of Object.entries(props)) {
          o[k] = exampleFromSchema(v);
        }
        return o;
      }
      if (schema.type === "array") return [];
      if (schema.type === "integer") return 0;
      if (schema.type === "boolean") return false;
      return "";
    }

    function escapeHtml(s) {
      return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
    }

    function filterTree(q) {
      q = q.trim().toLowerCase();
      document.querySelectorAll(".endpoint").forEach((el) => {
        const text = (el.dataset.path + " " + el.textContent).toLowerCase();
        el.style.display = !q || text.includes(q) ? "" : "none";
      });
      if (q) document.querySelectorAll(".folder").forEach((f) => f.classList.add("open"));
    }

    fetch(SPEC_URL)
      .then((r) => r.json())
      .then((data) => {
        spec = data;
        document.getElementById("api-version").textContent =
          (data.info && data.info.title ? data.info.title + " " : "") +
          (data.swagger || data.openapi || "") +
          (data.info && data.info.version ? " v" + data.info.version : "");
        const tree = pathToTree(data.paths || {});
        const nav = document.getElementById("tree");
        renderTree(tree, nav);
        const first = nav.querySelector(".endpoint");
        if (first) first.querySelector(".label").click();
      })
      .catch((err) => {
        document.getElementById("main").innerHTML =
          `<p class="empty">无法加载 ${SPEC_URL}：${err}</p>`;
      });

    document.getElementById("filter").addEventListener("input", (e) => filterTree(e.target.value));
  </script>
</body>
</html>
"""


def get_tree_docs_html(
    *,
    spec_url: str = "/swagger.json",
    swagger_ui_url: str | None = "/docs/swagger",
) -> str:
    classic = (
        f'<a href="{swagger_ui_url}" target="_blank">经典 Swagger UI</a>'
        if swagger_ui_url
        else ""
    )
    return (
        TREE_DOCS_HTML.replace("__SPEC_URL__", spec_url)
        .replace("__CLASSIC_LINK__", classic)
    )


def mount_tree_docs(
    app: FastAPI,
    *,
    docs_url: str = "/docs",
    spec_url: str = "/swagger.json",
    swagger_ui_url: str = "/docs/swagger",
) -> None:
    """Mount directory-tree documentation at `docs_url`."""

    @app.get(docs_url, include_in_schema=False, tags=["meta"])
    def api_docs_tree() -> HTMLResponse:
        return HTMLResponse(get_tree_docs_html(spec_url=spec_url, swagger_ui_url=swagger_ui_url))
