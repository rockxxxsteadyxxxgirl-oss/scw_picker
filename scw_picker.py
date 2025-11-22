"""Leafletで座標を選び、各サイトを開くボタンを提供するツール。
対象: SCW / ClearOutside / Windy（ECMWF・GFS・JMA MSM・ICON、4分割は別ウィンドウ）/ LightPollutionMap / Stellarium / meteoblue / Ventusky
機能: 地名表示（Nominatim逆ジオ）、お気に入り登録・呼び出し（最大30件、localStorage保存）、ライト/ダーク切替、サイトボタン並び替え保存、Windy 4分割は各枠を最大化/元に戻すボタン付き。
"""

from pathlib import Path
import webbrowser


HTML = """<!DOCTYPE html>
<html lang="ja">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>座標ピッカー</title>
  <link
    rel="stylesheet"
    href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"
    integrity="sha256-p4NxAoJBhIIN+hmNHrzRCf9tD/miZyoHS5obTRR9BMY="
    crossorigin=""
  />
  <style>
    :root {
      --bg: #ffffff;
      --fg: #1f2937;
      --panel-bg: #f7f7f7;
      --accent: #2563eb;
      --border: #d1d5db;
      --card: #ffffff;
    }
    [data-theme="dark"] {
      --bg: #0f172a;
      --fg: #e5e7eb;
      --panel-bg: #111827;
      --accent: #60a5fa;
      --border: #334155;
      --card: #111827;
    }
    * { box-sizing: border-box; }
    body { margin: 0; background: var(--bg); color: var(--fg); font-family: "Segoe UI", "Noto Sans JP", system-ui, -apple-system, sans-serif; }
    h1 { margin: 0; font-size: 20px; }
    .panel { padding: 12px; background: var(--panel-bg); border-top: 1px solid var(--border); }
    .row { display: flex; flex-wrap: wrap; gap: 8px; align-items: center; margin-bottom: 8px; }
    .row:last-child { margin-bottom: 0; }
    #map { width: 100%; height: 60vh; border-bottom: 1px solid var(--border); }
    button { padding: 8px 12px; cursor: pointer; border: none; border-radius: 4px; background: var(--accent); color: #fff; font-weight: 600; }
    button.secondary { background: transparent; color: var(--fg); border: 1px solid var(--border); }
    button:disabled { opacity: 0.6; cursor: not-allowed; }
    input[type="text"] { padding: 6px 8px; border: 1px solid var(--border); border-radius: 4px; background: var(--card); color: var(--fg); }
    code { background: #e5e7eb; color: #111827; padding: 2px 4px; border-radius: 4px; }
    ul { margin: 4px 0 0 18px; padding: 0; line-height: 1.5; }
    .site-buttons { display: flex; flex-wrap: wrap; gap: 6px; }
    .btn-drag.dragging { opacity: 0.6; border: 1px dashed var(--border); }
    .fav-list { display: flex; flex-wrap: wrap; gap: 6px; }
    .fav-item { display: flex; align-items: center; gap: 6px; border: 1px solid var(--border); border-radius: 4px; padding: 4px 6px; background: var(--card); }
    .fav-item.dragging { opacity: 0.6; border-style: dashed; }
    .fav-del { padding: 2px 6px; background: #ef4444; color: #fff; border: none; border-radius: 3px; font-size: 12px; }
    .fav-name { font-size: 12px; color: #6b7280; }
  </style>
</head>
<body>
  <div class="panel" style="padding-bottom:8px;">
    <div class="row" style="margin-bottom:0;">
      <h1>座標ピッカー</h1>
      <button id="theme-toggle" class="secondary" type="button">ダーク/ライト切替</button>
    </div>
  </div>
  <div id="map"></div>
  <div class="panel">
    <div class="row">
      <label>座標 <input id="input-coords" type="text" placeholder="38.13665621942762, 140.44956778749423" style="width:260px;" /></label>
      <button id="jump-btn" class="secondary" type="button">この座標へ移動</button>
    </div>
    <div class="row">選択座標: <code id="coords">未選択</code></div>
    <div class="row">地名: <code id="placename">未取得</code></div>
    <div class="row site-buttons" id="site-buttons">
      <button id="open-scw" class="btn-drag" disabled>SCW</button>
      <button id="open-co" class="btn-drag" disabled>ClearOutside</button>
      <button id="open-windy" class="btn-drag" disabled>Windy(ECMWF)</button>
      <button id="open-windy-gfs" class="btn-drag" disabled>Windy(GFS)</button>
      <button id="open-windy-jma" class="btn-drag" disabled>Windy(JMA MSM)</button>
      <button id="open-windy-icon" class="btn-drag" disabled>Windy(ICON)</button>
      <button id="open-lpm" class="btn-drag" disabled>LightPollutionMap</button>
      <button id="open-stella" class="btn-drag" disabled>Stellarium</button>
      <button id="open-ventusky" class="btn-drag" disabled>Ventusky</button>
      <button id="open-meteoblue" class="btn-drag" disabled>meteoblue</button>
      <button id="open-windy-quad" class="btn-drag" disabled>Windy 4分割</button>
    </div>
    <div class="row">
      <input id="fav-name" type="text" placeholder="お気に入り名（空なら地名か座標）" />
      <button id="fav-save" disabled>お気に入りに追加 (最大30件)</button>
    </div>
    <div class="row">
      <div><strong>お気に入り一覧 (最大30件):</strong></div>
      <div id="fav-list" class="fav-list"></div>
    </div>
    <div class="row" style="display:block;">
      <div><strong>使い方:</strong></div>
      <ul>
        <li>地図をクリック → 座標と地名を取得し、各サイトボタンが有効になります。</li>
        <li>Windy 4分割ボタンは別ウィンドウで4モデルを表示します（ポップアップ許可が必要な場合あり）。</li>
        <li>お気に入りは最大30件。名称未入力なら地名→座標の順で自動設定。ドラッグで並び替え、削除も可能。</li>
        <li>ライト/ダーク切替とサイトボタン並び順はブラウザに保存されます。</li>
      </ul>
    </div>
  </div>

  <script
    src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"
    integrity="sha256-20nQCchB9co0qIjJZRGuk2/Z9VM+kNiyxNV1lvTlZBo="
    crossorigin=""
  ></script>
  <script>
    // 定数
    const DEFAULT_CENTER = { lat: 35.681236, lng: 139.767125 }; // 東京駅
    const DEFAULT_ZOOM = 10;
    const FLY_ZOOM = 13;
    const MAX_FAVS = 30;
    const FAVORITES_KEY = "scw_picker_favorites_v1";
    const SITE_ORDER_KEY = "scw_picker_site_order_v1";
    const THEME_KEY = "scw_picker_theme_v1";
    const DEFAULT_MODEL = "msm78";
    const DEFAULT_ELEMENT = "cp";
    const DEFAULT_ZL = "13";
    const WINDY_BASE = "https://www.windy.com/ja/-雲-clouds";
    const WINDY_LAYER = "clouds";
    // Windy共有リンクの末尾パラメータ。例: https://www.windy.com/ja/-雲-clouds?gfs,clouds,38.285,141.518,10,i:pressure,p:cities,m:eIYaj4Z
    const WINDY_TRAIL = "i:pressure,p:cities,m:eJkaj4e";
    const LPM_STATE = "eyJiYXNlbWFwIjoiTGF5ZXJCaW5nUm9hZCIsIm92ZXJsYXkiOiJ2aWlyc18yMDI0Iiwib3ZlcmxheWNvbG9yIjpmYWxzZSwib3ZlcmxheW9wYWNpdHkiOiI2MCIsImZlYXR1cmVzb3BhY2l0eSI6Ijg1In0=";
    const WINDY_EMBED_BASE = "https://embed.windy.com/embed2.html";

    // マップ
    const map = L.map("map").setView([DEFAULT_CENTER.lat, DEFAULT_CENTER.lng], DEFAULT_ZOOM);
    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
      maxZoom: 18,
      attribution: "© OpenStreetMap contributors",
    }).addTo(map);
    let marker = null;
    let currentLatLng = null;

    // DOM
    const coordsEl = document.getElementById("coords");
    const placeEl = document.getElementById("placename");
    const favNameEl = document.getElementById("fav-name");
    const favSaveBtn = document.getElementById("fav-save");
    const favListEl = document.getElementById("fav-list");
    const themeToggleBtn = document.getElementById("theme-toggle");
    const siteButtons = document.getElementById("site-buttons");
    const inputCoordsEl = document.getElementById("input-coords");
    const jumpBtn = document.getElementById("jump-btn");

    const openScwBtn = document.getElementById("open-scw");
    const openCoBtn = document.getElementById("open-co");
    const openWindyBtn = document.getElementById("open-windy");
    const openWindyGfsBtn = document.getElementById("open-windy-gfs");
    const openWindyJmaBtn = document.getElementById("open-windy-jma");
    const openWindyIconBtn = document.getElementById("open-windy-icon");
    const openLpmBtn = document.getElementById("open-lpm");
    const openStellaBtn = document.getElementById("open-stella");
    const openVentuskyBtn = document.getElementById("open-ventusky");
    const openMeteoblueBtn = document.getElementById("open-meteoblue");
    const openWindyQuadBtn = document.getElementById("open-windy-quad");

    const siteButtonIds = [
      "open-scw",
      "open-co",
      "open-windy",
      "open-windy-gfs",
      "open-windy-jma",
      "open-windy-icon",
      "open-lpm",
      "open-stella",
      "open-ventusky",
      "open-meteoblue",
      "open-windy-quad",
    ];
    let siteOrder = [...siteButtonIds];
    let buttonDragSrcId = null;
    let favDragSrcIndex = null;

    // Windy関連URL
    function windyUrl(lat, lng, product = "") {
      const z = map.getZoom() || DEFAULT_ZOOM;
      const productPrefix = product ? `${product},` : "";
      return `${WINDY_BASE}?${productPrefix}${WINDY_LAYER},${lat.toFixed(3)},${lng.toFixed(3)},${z},${WINDY_TRAIL}`;
    }
    function windyEmbedUrl(lat, lng, product, zoomValue) {
      const base = zoomValue ?? map.getZoom() ?? DEFAULT_ZOOM;
      const z = Math.max(7, Math.min(12, base));
      const model = product || "ecmwf";
      // model パラメータも併記して確実に反映
      return `${WINDY_EMBED_BASE}?lat=${lat}&lon=${lng}&zoom=${z}&level=surface&overlay=clouds&product=${model}&model=${model}&menu=&message=true&marker=true&markerLat=${lat}&markerLon=${lng}&calendar=now`;
    }
    function lpmUrl(lat, lng) {
      const z = (map && typeof map.getZoom === "function") ? map.getZoom() : 10;
      return `https://www.lightpollutionmap.info/#zoom=${z.toFixed(2)}&lat=${lat.toFixed(4)}&lon=${lng.toFixed(4)}&state=${LPM_STATE}`;
    }
    function stellariumUrl(lat, lng) {
      return `https://stellarium-web.org/?lat=${lat.toFixed(4)}&lng=${lng.toFixed(4)}`;
    }
    function meteoblueUrl(lat, lng) {
      const fmt = (v, pos, neg) => `${Math.abs(v).toFixed(3)}${v >= 0 ? pos : neg}`;
      return `https://www.meteoblue.com/en/weather/week/${fmt(lat, "N", "S")}${fmt(lng, "E", "W")}`;
    }
    function ventuskyUrl(lat, lng) {
      return `https://www.ventusky.com/?p=${lat.toFixed(2)};${lng.toFixed(2)};6&l=clouds-total`;
    }

    // 地名取得
    async function updatePlacename(lat, lng) {
      placeEl.textContent = "取得中...";
      try {
        const res = await fetch(
          `https://nominatim.openstreetmap.org/reverse?format=jsonv2&lat=${lat}&lon=${lng}&accept-language=ja`,
          { headers: { "User-Agent": "scw-picker/1.0" } }
        );
        if (!res.ok) throw new Error(`status ${res.status}`);
        const data = await res.json();
        placeEl.textContent = data.display_name || "名前を取得できませんでした";
      } catch (err) {
        placeEl.textContent = "名前を取得できませんでした";
        console.error(err);
      }
    }

    function enableButtons() {
      openScwBtn.disabled = false;
      openCoBtn.disabled = false;
      openWindyBtn.disabled = false;
      openWindyQuadBtn.disabled = false;
      openWindyGfsBtn.disabled = false;
      openWindyJmaBtn.disabled = false;
      openWindyIconBtn.disabled = false;
      openLpmBtn.disabled = false;
      openStellaBtn.disabled = false;
      openVentuskyBtn.disabled = false;
      openMeteoblueBtn.disabled = false;
      favSaveBtn.disabled = false;
    }

    function updateLinks(lat, lng) {
      const params = new URLSearchParams({
        lat: lat.toFixed(6),
        lng: lng.toFixed(6),
        model: DEFAULT_MODEL,
        element: DEFAULT_ELEMENT,
        zl: DEFAULT_ZL,
      });
      const scwUrl = `https://supercweather.com/?${params.toString()}`;
      const coUrl = `https://clearoutside.com/forecast/${lat.toFixed(4)}/${lng.toFixed(4)}`;
      const wUrl = windyUrl(lat, lng);
      const wGfsUrl = windyUrl(lat, lng, "gfs");
      const wJmaUrl = windyUrl(lat, lng, "jmaMsm");
      const wIconUrl = windyUrl(lat, lng, "icon");
      const lpUrl = lpmUrl(lat, lng);
      const stUrl = stellariumUrl(lat, lng);
      const mbUrl = meteoblueUrl(lat, lng);
      const vsUrl = ventuskyUrl(lat, lng);

      coordsEl.textContent = `${lat.toFixed(6)}, ${lng.toFixed(6)}`;
      updatePlacename(lat, lng);
      enableButtons();

      openScwBtn.onclick = () => window.open(scwUrl, "_blank");
      openCoBtn.onclick = () => window.open(coUrl, "_blank");
      openWindyBtn.onclick = () => window.open(wUrl, "_blank");
      openWindyGfsBtn.onclick = () => window.open(wGfsUrl, "_blank");
      openWindyJmaBtn.onclick = () => window.open(wJmaUrl, "_blank");
      openWindyIconBtn.onclick = () => window.open(wIconUrl, "_blank");
      openLpmBtn.onclick = () => window.open(lpUrl, "_blank");
      openStellaBtn.onclick = () => window.open(stUrl, "_blank");
      openMeteoblueBtn.onclick = () => window.open(mbUrl, "_blank");
      openVentuskyBtn.onclick = () => window.open(vsUrl, "_blank");
      openWindyQuadBtn.onclick = () => openWindyQuadWindow(lat, lng);
    }

    function setLocation(lat, lng, { pan = true, scroll = true, zoom = null } = {}) {
      currentLatLng = { lat, lng };
      if (!marker) {
        marker = L.marker([lat, lng]).addTo(map);
      } else {
        marker.setLatLng([lat, lng]);
      }
      if (pan) {
        const targetZoom = zoom != null ? zoom : map.getZoom();
        map.setView([lat, lng], targetZoom);
      }
      updateLinks(lat, lng);
      renderFavorites();
      if (scroll) {
        siteButtons.scrollIntoView({ behavior: "smooth", block: "start" });
      }
    }

    // お気に入り
    function loadFavorites() {
      try {
        const data = localStorage.getItem(FAVORITES_KEY);
        if (!data) return [];
        return JSON.parse(data);
      } catch {
        return [];
      }
    }
    function saveFavorites(list) {
      localStorage.setItem(FAVORITES_KEY, JSON.stringify(list));
    }
    function renderFavorites() {
      const favs = loadFavorites();
      favListEl.innerHTML = "";
      if (favs.length === 0) {
        favListEl.textContent = "なし";
      } else {
        favs.forEach((fav, idx) => {
          const wrap = document.createElement("div");
          wrap.className = "fav-item";
          wrap.draggable = true;
          wrap.dataset.index = idx;
          const btn = document.createElement("button");
          btn.textContent = fav.name;
          btn.onclick = () => {
            setLocation(fav.lat, fav.lng, { pan: true, scroll: true, zoom: map.getZoom() });
          };
          const del = document.createElement("button");
          del.textContent = "削除";
          del.className = "fav-del";
          del.onclick = () => {
            const next = loadFavorites().filter((_, i) => i !== idx);
            saveFavorites(next);
            renderFavorites();
          };
          const nameSpan = document.createElement("span");
          nameSpan.className = "fav-name";
          nameSpan.textContent = `(${fav.lat.toFixed(4)}, ${fav.lng.toFixed(4)})`;
          wrap.appendChild(btn);
          wrap.appendChild(nameSpan);
          wrap.appendChild(del);

          wrap.addEventListener("dragstart", (e) => {
            favDragSrcIndex = idx;
            wrap.classList.add("dragging");
            e.dataTransfer.effectAllowed = "move";
          });
          wrap.addEventListener("dragend", () => {
            wrap.classList.remove("dragging");
            favDragSrcIndex = null;
          });
          wrap.addEventListener("dragover", (e) => {
            e.preventDefault();
            e.dataTransfer.dropEffect = "move";
          });
          wrap.addEventListener("drop", (e) => {
            e.preventDefault();
            const from = favDragSrcIndex;
            const to = idx;
            if (from === null || from === to) return;
            const current = loadFavorites();
            if (from < 0 || from >= current.length || to < 0 || to >= current.length) return;
            const [item] = current.splice(from, 1);
            current.splice(to, 0, item);
            saveFavorites(current);
            renderFavorites();
          });

          favListEl.appendChild(wrap);
        });
      }
      favSaveBtn.disabled = favs.length >= MAX_FAVS || !currentLatLng;
      favSaveBtn.textContent = favs.length >= MAX_FAVS ? "お気に入り上限(30件)" : "お気に入りに追加 (最大30件)";
    }
    function addFavorite() {
      if (!currentLatLng) return;
      const favs = loadFavorites();
      if (favs.length >= MAX_FAVS) {
        alert(`お気に入りは最大 ${MAX_FAVS} 件までです。`);
        renderFavorites();
        return;
      }
      const name =
        favNameEl.value.trim() ||
        placeEl.textContent.trim() ||
        `${currentLatLng.lat.toFixed(4)}, ${currentLatLng.lng.toFixed(4)}`;
      favs.push({ name, lat: currentLatLng.lat, lng: currentLatLng.lng });
      saveFavorites(favs);
      renderFavorites();
      favNameEl.value = "";
    }
    favSaveBtn.onclick = addFavorite;

    // サイト並べ替え
    function loadSiteOrder() {
      try {
        const data = localStorage.getItem(SITE_ORDER_KEY);
        if (!data) return [...siteButtonIds];
        const parsed = JSON.parse(data);
        if (!Array.isArray(parsed)) return [...siteButtonIds];
        const filtered = parsed.filter((id) => siteButtonIds.includes(id));
        const missing = siteButtonIds.filter((id) => !filtered.includes(id));
        return [...filtered, ...missing];
      } catch {
        return [...siteButtonIds];
      }
    }
    function saveSiteOrder(order) {
      localStorage.setItem(SITE_ORDER_KEY, JSON.stringify(order));
    }
    function applySiteOrder(order) {
      order.forEach((id) => {
        const btn = document.getElementById(id);
        if (btn) siteButtons.appendChild(btn);
      });
      siteOrder = order;
    }
    function setupSiteDrag() {
      siteOrder = loadSiteOrder();
      applySiteOrder(siteOrder);
      siteButtonIds.forEach((id) => {
        const btn = document.getElementById(id);
        if (!btn) return;
        btn.draggable = true;
        btn.dataset.id = id;
        btn.addEventListener("dragstart", (e) => {
          buttonDragSrcId = id;
          btn.classList.add("dragging");
          e.dataTransfer.effectAllowed = "move";
        });
        btn.addEventListener("dragend", () => {
          btn.classList.remove("dragging");
          buttonDragSrcId = null;
        });
        btn.addEventListener("dragover", (e) => {
          e.preventDefault();
          e.dataTransfer.dropEffect = "move";
        });
        btn.addEventListener("drop", (e) => {
          e.preventDefault();
          const targetId = id;
          if (!buttonDragSrcId || buttonDragSrcId === targetId) return;
          const current = [...siteOrder];
          const from = current.indexOf(buttonDragSrcId);
          const to = current.indexOf(targetId);
          if (from === -1 || to === -1) return;
          const [item] = current.splice(from, 1);
          current.splice(to, 0, item);
          saveSiteOrder(current);
          applySiteOrder(current);
        });
      });
    }

    // 入力ジャンプ
    function jumpToInput() {
      const raw = (inputCoordsEl?.value || "").trim();
      const parts = raw.split(",").map((s) => s.trim()).filter(Boolean);
      if (parts.length < 2) {
        alert("緯度,経度をカンマ区切りで入力してください（例: 38.13665621942762, 140.44956778749423）。");
        return;
      }
      const latNum = parseFloat(parts[0]);
      const lngNum = parseFloat(parts[1]);
      if (Number.isNaN(latNum) || Number.isNaN(lngNum)) {
        alert("緯度,経度を数値で入力してください。");
        return;
      }
      setLocation(latNum, lngNum, { pan: true, scroll: true, zoom: FLY_ZOOM });
    }
    if (jumpBtn) jumpBtn.onclick = jumpToInput;
    if (inputCoordsEl) {
      inputCoordsEl.addEventListener("keypress", (e) => {
        if (e.key === "Enter") jumpToInput();
      });
    }

    // クリックで位置更新
    map.on("click", (e) => {
      const { lat, lng } = e.latlng;
      setLocation(lat, lng, { pan: false, scroll: true });
    });

    // Windy 4分割
    function openWindyQuadWindow(lat, lng) {
      const zoomValue = Math.max(7, Math.min(12, map.getZoom() || DEFAULT_ZOOM));
      const models = [
        { label: "ECMWF", product: "ecmwf" },
        { label: "GFS", product: "gfs" },
        { label: "ICON", product: "icon" },
        { label: "JMA MSM", product: "jmaMsm" },
      ];
    const doc = `<!DOCTYPE html>
<html lang="ja">
<head>
  <meta charset="UTF-8" />
  <title>Windy 4分割</title>
  <style>
    body { margin:0; background:#0f172a; color:#e5e7eb; font-family:system-ui,-apple-system,sans-serif; }
    .grid { display:grid; grid-template-columns:repeat(2, minmax(0, 1fr)); grid-auto-rows:50vh; gap:6px; padding:6px; box-sizing:border-box; height:100vh; }
    .grid.maximized { grid-template-columns:1fr; grid-auto-rows:1fr; }
    .card { border:1px solid #334155; border-radius:6px; overflow:hidden; display:flex; flex-direction:column; }
    .card header { padding:6px 10px; background:#111827; border-bottom:1px solid #334155; font-weight:600; display:flex; align-items:center; justify-content:space-between; gap:8px; }
    .actions { display:flex; gap:6px; }
    .actions button { background:#2563eb; color:#fff; border:0; border-radius:4px; padding:4px 8px; cursor:pointer; }
    .url { font-size:12px; color:#cbd5e1; padding:4px 10px; background:#0b1220; border-bottom:1px solid #1f2937; word-break: break-all; }
    iframe { flex:1; border:0; width:100%; height:100%; }
  </style>
</head>
<body>
  <div class="grid" id="grid">
    ${models
      .map(
        (m, i) => {
          const url = windyEmbedUrl(lat, lng, m.product);
          return `
      <div class="card" data-idx="${i}">
        <header>
          <span>${m.label}</span>
          <div class="actions">
            <button onclick="maximize(${i})">最大化</button>
            <button onclick="restore()">元に戻す</button>
          </div>
        </header>
        <div class="url">model: ${m.product} / ${url}</div>
        <iframe src="${url}" loading="lazy"></iframe>
      </div>`;
        }
      )
      .join("")}
  </div>
  <script>
    const grid = document.getElementById("grid");
    const cards = Array.from(grid.querySelectorAll(".card"));
    function maximize(idx) {
      cards.forEach((c, i) => { c.style.display = i === idx ? "flex" : "none"; });
      grid.classList.add("maximized");
    }
    function restore() {
      cards.forEach((c) => (c.style.display = "flex"));
      grid.classList.remove("maximized");
    }
  <\\/script>
</body>
</html>`;
      const w = window.open("", "_blank");
      if (!w) {
        alert("ポップアップがブロックされました。許可してください。");
        return;
      }
      w.document.write(doc);
      w.document.close();
    }

    // テーマ切替
    function applyTheme(theme) {
      document.documentElement.setAttribute("data-theme", theme);
      localStorage.setItem(THEME_KEY, theme);
      themeToggleBtn.textContent = theme === "dark" ? "ライトにする" : "ダークにする";
    }
    (function initTheme() {
      const saved = localStorage.getItem(THEME_KEY);
      if (saved === "dark" || saved === "light") {
        applyTheme(saved);
      } else {
        const prefersDark = window.matchMedia("(prefers-color-scheme: dark)").matches;
        applyTheme(prefersDark ? "dark" : "light");
      }
    })();
    themeToggleBtn.onclick = () => {
      const current = document.documentElement.getAttribute("data-theme") === "dark" ? "dark" : "light";
      applyTheme(current === "dark" ? "light" : "dark");
    };

    // 初期セット
    setupSiteDrag();
    renderFavorites();
  </script>
</body>
</html>
"""

HTML_PATH = Path(__file__).resolve().with_suffix(".html")


def main() -> None:
    HTML_PATH.write_text(HTML, encoding="utf-8")
    webbrowser.open(HTML_PATH.as_uri())
    print("ブラウザが開かない場合は次のファイルを直接開いてください:")
    print(HTML_PATH)


if __name__ == "__main__":
    main()
