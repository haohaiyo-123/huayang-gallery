#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""亿图花漾 画廊 — 本地 DNS 被污染指向失效源站，通过 curl --resolve
钉住 Cloudflare 边缘 IP 直连（DoH 自动刷新），图片 CDN jiutuvip 可直链。"""
import os
import re
import subprocess
import time
from urllib.parse import urljoin, quote

import requests
from flask import Flask, Response, jsonify, render_template, request

_base = os.path.dirname(os.path.abspath(__file__))
_tpl = "gallery_templates" if os.path.isdir(os.path.join(_base, "gallery_templates")) else "templates"
app = Flask(__name__, template_folder=os.path.join(_base, _tpl))

@app.get("/")
def index():
    try:
        return render_template("index.html")
    except Exception:
        return "<h3>template missing</h3>", 200

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"

# ---------- DNS over HTTPS：解析 yeitu.com 的真实 Cloudflare IP ----------
# 本地 DNS 指向失效源站(120.26.198.174)，且常用 CF 边缘 IP 时通时断。
# 策略：维护一个候选 CF 边缘 IP 池，动态健康检查，轮换使用。
_edge_cache = {"ips": [], "ts": 0}
CF_CANDIDATES = ["104.16.0.1", "104.17.0.1", "104.18.0.1", "104.19.0.1", "104.20.0.1",
                 "104.21.64.137", "104.22.0.1", "104.24.0.1", "104.25.0.1", "104.26.0.1",
                 "104.27.0.1", "108.162.192.1", "141.101.90.1", "162.158.0.1",
                 "172.64.0.1", "172.65.0.1", "172.66.0.1", "172.67.151.52",
                 "173.245.48.1", "188.114.96.1"]

def _probe_ip(ip):
    r = subprocess.run(["curl", "-s", "-o", "/dev/null", "-w", "%{http_code}",
                        "--resolve", f"www.yeitu.com:443:{ip}", "-A", UA,
                        "https://www.yeitu.com/", "-m", "5"], capture_output=True, text=True)
    return r.stdout.strip() == "200"

def yeitu_ips():
    if _edge_cache["ips"] and time.time() - _edge_cache["ts"] < 600:
        return _edge_cache["ips"]
    from concurrent.futures import ThreadPoolExecutor
    ok = []
    # 并行探测，最多收集 4 个可用边缘
    with ThreadPoolExecutor(max_workers=10) as ex:
        for ip, alive in zip(CF_CANDIDATES, ex.map(_probe_ip, CF_CANDIDATES)):
            if alive:
                ok.append(ip)
            if len(ok) >= 4:
                break
    if not ok:
        ok = ["104.16.0.1"]  # last resort
    _edge_cache.update(ips=ok, ts=time.time())
    return ok

def fetch(url, referer=None, timeout=20):
    """用 curl --resolve 钉住 CF 边缘 IP 抓 HTML，失败自动换 IP 重试。"""
    ips = yeitu_ips()
    last = None
    for ip in ips[:3]:
        cmd = ["curl", "-s", "--resolve", f"www.yeitu.com:443:{ip}", "--resolve", f"yeitu.com:443:{ip}",
               "-A", UA, "-m", str(timeout), "--compressed"]
        if referer:
            cmd += ["-H", f"Referer: {referer}"]
        cmd.append(url)
        r = subprocess.run(cmd, capture_output=True)
        if r.returncode == 0 and r.stdout:
            return r.stdout.decode("utf-8", "replace")
        last = r
    # 所有 IP 都失败 → 刷新边缘池再试一次
    _edge_cache.update(ips=[], ts=0)
    ips = yeitu_ips()
    cmd = ["curl", "-s", "--resolve", f"www.yeitu.com:443:{ips[0]}", "-A", UA, "-m", str(timeout), "--compressed"]
    if referer:
        cmd += ["-H", f"Referer: {referer}"]
    cmd.append(url)
    r = subprocess.run(cmd, capture_output=True)
    return r.stdout.decode("utf-8", "replace")

# ---------- 亿图花漾抓取 ----------

def src_yetu(page):
    """亿图花漾 yeitu.com/tag/huayang"""
    # tag 分页对非法 page 返回空，page=1 用裸 URL
    url = f"https://www.yeitu.com/tag/huayang/?&page={page}" if page > 1 else "https://www.yeitu.com/tag/huayang/"
    html = fetch(url, referer="https://www.yeitu.com/")
    albums, seen = [], set()
    for m in re.finditer(r'href="(https?://www\.yeitu\.com/meinv/xinggan/\d{8}_\d+\.html)"', html):
        if m.group(1) not in seen:
            seen.add(m.group(1)); albums.append(m.group(1))
    from concurrent.futures import ThreadPoolExecutor

    def crawl_album(album):
        out = []
        title = None
        try:
            nxt = album
            hops = 0
            while nxt and hops < 15:
                hops += 1
                page_html = fetch(nxt, referer="https://www.yeitu.com/")
                if hops == 1:
                    tm = re.search(r'<h1[^>]*>([^<]+)</h1>', page_html)
                    if tm: title = tm.group(1).strip()
                for m in re.finditer(r'<img[^>]+src="(https?://[^"]*jiutuvip[^"]+)"', page_html):
                    u = m.group(1)
                    if u not in out:
                        out.append(u)  # jiutuvip CDN 无防盗链
                nm = re.search(r'<a[^>]+href="([^"]+)"[^>]*>\s*下一页', page_html)
                nxt = urljoin("https://www.yeitu.com/", nm.group(1)) if nm else None
        except Exception:
            pass
        return out, title

    albums_out, titles = [], []
    with ThreadPoolExecutor(max_workers=6) as ex:
        for part, title in ex.map(crawl_album, albums[:12]):
            if part:
                albums_out.append(part)
                titles.append(title or f"图集 {len(albums_out)}")
    return albums_out, titles

SOURCES = {"yetu": ("亿图花漾", src_yetu, 21)}

# ---------- API ----------

@app.get("/api/sources")
def api_sources():
    return jsonify([{"id": k, "name": v[0], "max_page": v[2]} for k, v in SOURCES.items()])

@app.get("/api/images")
def api_images():
    sid = request.args.get("source", "yetu")
    page = int(request.args.get("page", 1))
    if sid not in SOURCES:
        return jsonify({"error": "unknown source"}), 404
    name, fn, _ = SOURCES[sid]
    try:
        albums, titles = fn(page)
    except Exception as e:
        return jsonify({"error": str(e), "albums": []})
    return jsonify({"source": sid, "name": name, "page": page,
                    "albums": [{"title": t, "images": a} for t, a in zip(titles, albums)]})

_PROXY_CACHE = {}

@app.get("/proxy")
def proxy():
    url = request.args.get("url", "")
    if not url.startswith(("http://", "https://")):
        return "bad url", 400
    if url in _PROXY_CACHE:
        data, ctype = _PROXY_CACHE[url]
        return Response(data, mimetype=ctype, headers={"Cache-Control": "public, max-age=86400"})
    try:
        r = requests.get(url, headers={"User-Agent": UA, "Referer": "https://www.yeitu.com/"}, timeout=25,
                         stream=True)
        data = r.content
        ctype = r.headers.get("Content-Type", "image/jpeg")
        if len(_PROXY_CACHE) > 300:
            _PROXY_CACHE.pop(next(iter(_PROXY_CACHE)))
        _PROXY_CACHE[url] = (data, ctype)
        return Response(data, mimetype=ctype, headers={"Cache-Control": "public, max-age=86400"})
    except Exception as e:
        return f"proxy error: {e}", 502

@app.after_request
def cors(resp):
    resp.headers["Access-Control-Allow-Origin"] = "*"
    return resp

@app.get("/sw.js")
def sw_js():
    return Response("""const C='imgcache-v1';
self.addEventListener('install', e => self.skipWaiting());
self.addEventListener('activate', e => e.waitUntil(clients.claim()));
self.addEventListener('fetch', e => {
  const u = new URL(e.request.url);
  if (u.pathname === '/proxy' && e.request.method === 'GET') {
    e.respondWith(caches.open(C).then(async c => {
      const hit = await c.match(e.request);
      if (hit) return hit;
      const resp = await fetch(e.request);
      if (resp.ok) c.put(e.request, resp.clone());
      return resp;
    }));
  }
});""", mimetype="application/javascript")

@app.get("/manifest.json")
def manifest():
    return jsonify({
        "name": "花漾画廊", "short_name": "花漾",
        "start_url": "/", "display": "standalone",
        "background_color": "#0f1115", "theme_color": "#0f1115",
        "icons": []
    })

def _warmup():
    try:
        yeitu_ips()
    except Exception:
        pass

if __name__ == "__main__":
    import threading
    import os
    threading.Thread(target=_warmup, daemon=True).start()
    port = int(os.environ.get("PORT", 8899))
    app.run(host="0.0.0.0", port=port, debug=False, threaded=True)
