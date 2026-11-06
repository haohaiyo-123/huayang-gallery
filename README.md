# 花漾画廊 — 部署到 Render（免费、无需信用卡）

把画廊部署到 Render，手机随时访问，不依赖家里电脑。

> 注：Hugging Face Spaces 自 2026 年 7 月起 Docker/Gradio Spaces 已改为付费（仅 Static 免费），本方案改用 Render。

## 步骤

1. 打开 https://dashboard.render.com → 用 GitHub 账号登录（无需信用卡）
2. **New +** → **Web Service**
3. 授权 GitHub 后选择本仓库 `huayang-gallery`（若列表没有，点 "Configure account" 授权）
4. 配置页：
   - **Region**: Singapore（离国内最近）
   - **Instance Type**: **Free**（0.1 CPU / 512MB）
   - 其余保持默认（`render.yaml` 已填好）
5. 点 **Deploy Web Service**，构建约 3~5 分钟
6. 部署完成后得到公网地址：`https://huayang-gallery.onrender.com`（以后缀实际为准）
7. 手机浏览器打开 → 分享 → **添加到主屏幕** = 独立 App

## 免费层特性（重要）

- **15 分钟无访问自动休眠**，下次访问需约 1 分钟唤醒——第一次打开转圈是正常现象，不是坏了
- 每月 750 实例小时（一个服务跑满整月没问题）
- 免费带宽 5GB/月（小画廊绰绰有余）

## 技术说明

- `yeitu.com` 的 DNS（含 Ali DoH）被污染指向失效源站 120.26.198.174，站点实际存活于 Cloudflare 之后
- 服务内置 CF 边缘 IP 候选池（约 20 个 IP），并行健康检查（5s 超时），结果缓存 600s，自动失败转移
- 用 `curl --resolve` 钉住健康边缘 IP 直连抓取（Dockerfile 已安装 curl）
- 图片走 jiutuvip CDN（无防盗链），出站经 `/proxy` 代理并带 Referer 兜底
- PWA：手机「添加到主屏幕」后全屏独立运行（manifest + service worker 已内置）

## 本地开发

```bash
pip install -r requirements.txt
python app.py          # 默认 0.0.0.0:8899，可用 PORT 环境变量覆盖
```
