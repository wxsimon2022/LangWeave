# 搜索引擎提交指南

部署完成后，手动向各大搜索引擎提交站点，加速收录。

> **注意**：Google 和 Bing 已废弃旧的 Ping API，需要登录 Search Console/Webmaster Tools 提交。

---

## 🚀 立即推送（一键提交）

### 百度自动推送
首页已嵌入百度自动推送脚本，每次页面被访问时自动通知百度。访问一次即可触发：

<a href="https://chat.mybfs.cn/" target="_blank">点击访问首页，触发百度自动推送</a>

### RSS 提交（Google / Bing / 百度均支持）

\`\`\`bash
# 直接通过浏览器打开以下链接，提交 sitemap
# Google 现已废弃 ping，以下仅对旧版有用
# https://www.google.com/ping?sitemap=https://chat.mybfs.cn/sitemap.xml
\`\`\`

---

## 1. Google Search Console <sup>推荐</sup>

1. 打开 <a href="https://search.google.com/search-console" target="_blank">Google Search Console</a>
2. 添加资源 → 输入 \`https://chat.mybfs.cn/\`
3. 验证站点所有权（推荐 **DNS 验证**：添加 TXT 记录到域名解析）
4. 验证通过后，在左侧栏 → **Sitemaps** → 输入 \`https://chat.mybfs.cn/sitemap.xml\` → 提交
5. 可选：使用 **URL Inspection** 手动提交首页：\`https://chat.mybfs.cn/\`

## 2. 百度站长平台 <sup>推荐</sup>

1. 打开 <a href="https://ziyuan.baidu.com/site/index" target="_blank">百度资源平台</a>
2. 添加站点 → 输入 \`https://chat.mybfs.cn/\`
3. 验证站点所有权（推荐 **DNS 验证** 或 **文件验证**）
4. 验证通过后 → **普通收录** → **提交 Sitemap** → \`https://chat.mybfs.cn/sitemap.xml\`
5. 首页已嵌入百度自动推送脚本，访问页面即可触发实时推送

### 百度主动推送（高级，需 Token）

如已完成百度站点验证，可通过 API 主动推送 URL：

\`\`\`bash
# 替换 YOUR_TOKEN 为百度站长平台中获取的 token
curl -H "Content-Type: text/plain" \
  -d "https://chat.mybfs.cn/" \
  "http://data.zz.baidu.com/urls?site=https://chat.mybfs.cn&token=YOUR_TOKEN"
\`\`\`

## 3. 必应 Webmaster Tools

方案 A：通过 Google Search Console **数据导入**
- 在 Bing Webmaster Tools 中关联 Google Search Console 账户，自动同步数据

方案 B：手动提交
1. 打开 <a href="https://www.bing.com/webmasters" target="_blank">Bing Webmaster Tools</a>
2. 添加站点 → \`https://chat.mybfs.cn/\`
3. 验证所有权 → 提交 sitemap

## 4. 搜索引擎直接检索

搜索引擎通常会在数周内自动发现新站点。以下方式可加速：

- ✅ 在社交媒体上分享站点链接（Twitter、知乎、小红书等）
- ✅ 在 GitHub 项目 README 中加入站点链接（已完成）
- ✅ 提交到开放目录或导航站

---

## 技术细节

### 已配置的 SEO 增强
- ✅ **robots.txt**：精确控制爬虫访问范围
- ✅ **Sitemap.xml**：包含所有公开页面
- ✅ **结构化数据**：JSON-LD（WebApplication, FAQPage, Organization, BreadcrumbList 等）
- ✅ **Open Graph / Twitter Cards**：社交媒体分享优化
- ✅ **百度自动推送**：页面访问即通知百度
- ✅ **预渲染**：Nginx 对爬虫返回静态 HTML（\`__bot.html\`）
- ✅ **Canonical URL**：防止重复内容
- ✅ **hreflang**：中文站点标记
- ✅ **Gzip**：压缩响应加速爬虫抓取

### Nginx 爬虫处理
Nginx 已配置为对爬虫 User-Agent 返回预渲染静态页面，爬虫可以直接抓取到完整页面内容，无需执行 JavaScript。

支持的爬虫：Googlebot、Baiduspider、Bingbot、Slurp、YandexBot、Sogou、360Spider、facebookexternalhit、Twitterbot 等。

---

## 一键验证

提交后可使用以下工具验证收录情况：

- **Google**：在 Search Console 使用 URL Inspection 输入 \`https://chat.mybfs.cn/\`
- **百度**：在站长平台使用「抓取诊断」工具
- **通用**：在浏览器地址栏输入 \`site:chat.mybfs.cn\` 查看已收录页面
