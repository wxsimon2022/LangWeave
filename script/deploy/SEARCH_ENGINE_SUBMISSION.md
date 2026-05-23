# 搜索引擎提交指南

部署完成后，手动向各大搜索引擎提交站点，加速收录。

## 1. 百度 (Baidu)

- **提交入口**: https://ziyuan.baidu.com/site/index
- 需要验证站点所有权（推荐 DNS 验证或文件验证）
- 提交链接: `https://chat.mybfs.cn/`
- 提交 sitemap: `https://chat.mybfs.cn/sitemap.xml`

## 2. Google

- **提交入口**: https://search.google.com/search-console
- 需要验证站点所有权（推荐 DNS 验证）
- 提交 sitemap: `https://chat.mybfs.cn/sitemap.xml`

## 3. 必应 (Bing)

- **提交入口**: https://www.bing.com/webmasters
- 可通过 Google Search Console 数据导入
- 或手动提交 sitemap

## 非必做的加速方式

在页面 `<head>` 中已添加以下标签，爬虫会自动发现：

```html
<link rel="canonical" href="https://chat.mybfs.cn/" />
<link rel="sitemap" type="application/xml" href="/sitemap.xml" />
```

## Nginx 爬虫处理

Nginx 已配置为对爬虫 User-Agent 返回预渲染静态页面 `__bot.html`，
爬虫可以直接抓取到完整页面内容，无需执行 JavaScript。

支持的爬虫：Googlebot、Baiduspider、Bingbot、Slurp、YandexBot、Sogou、360Spider、facebookexternalhit、Twitterbot 等。
