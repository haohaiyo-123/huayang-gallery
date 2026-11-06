# 花漾画廊 — 部署到 Hugging Face Spaces

把画廊部署到 HF Spaces（免费、无需信用卡），手机随时访问，不依赖家里电脑。

## 步骤

1. 注册/登录 https://huggingface.co
2. 右上角头像 → **New Space**
   - Space name: `huayang-gallery`
   - License: 随意（如 mit）
   - SDK 选 **Docker** → Blank 模板
   - 可见性建议 **Public**（Private 的话 Pro 才能匿名访问，Public 免费最方便）
3. 上传本目录的 3 个文件到 Space（网页上 Files → Add file → Upload files）：
   - `Dockerfile`
   - `requirements.txt`
   - `app.py`
   - `templates/index.html`（注意保持 templates 目录结构，用 Upload files 时把文件拖进会自动建目录吗？——不会，用一次 commit：可以先 Add file → Create a new file，路径填 `templates/index.html`，再把 index.html 内容粘进去）
4. 等待自动构建（2~5 分钟），状态变 Running
5. 得到网址：`https://你的用户名-huayang-gallery.hf.space`
6. 手机浏览器打开该网址 → 分享 → 添加到主屏幕 = 一个独立 App

## 说明

- 免费额度：CPU Basic 免费、无时间限制；闲置约 48h 后会休眠，访问时会自动唤醒（首次慢 20~30 秒）
- 服务内部已含 CF 边缘 IP 池直连逻辑（机房 DNS 同样解析到失效源站，脚本用 curl --resolve 绕过）
- 图片通过 `/proxy` 代理出站，HF 免费流量对这种小画廊完全够用
