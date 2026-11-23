// Справочник жанров
const GENRES = {
  chanson: { label: "Шансон", icon: "🎸", folder: "tracks/chanson" },
  disco: { label: "Диско", icon: "★", folder: "tracks/disco" },
  deephouse: { label: "ДипХаус", icon: "⚡", folder: "tracks/deephouse" },
  other: { label: "Разное", icon: "♫", folder: "tracks/other" },
};

// Настройки репозитория GitHub для автообнаружения песен на GitHub Pages
const GITHUB_OWNER = "vlad5-vlad5";
const GITHUB_REPO = "453";
const GITHUB_BRANCH = "main";
const AUDIO_EXT_RE = /\.(mp3|wav|ogg|flac|m4a|aac|opus|webm)$/i;
const IMAGE_EXT_RE = /\.(jpg|jpeg|png|webp|svg|gif)$/i;

// Резервный список треков (если не удалось загрузить tracks.json и /api/tracks)
const FALLBACK_TRACKS = [];

// Необязательно: вставьте сюда ссылку на бесплатную Firebase Realtime Database
// (например: "https://my-music-default-rtdb.europe-west1.firebasedatabase.app"),
// чтобы лайки и комментарии были общими для всех друзей на GitHub Pages.
const FIREBASE_DB_URL = "";

const LS_FAVORITES = "soundwave_favorites_v1";
const LS_PLAYLISTS = "soundwave_playlists_v1";
const LS_LIKES_MAP = "soundwave_likes_map_v1";
const LS_COMMENTS_MAP = "soundwave_comments_map_v1";
const LS_USERNAME = "soundwave_username_v1";
const LS_CLIENT_ID = "soundwave_client_id_v1";

const IS_ADMIN = new URLSearchParams(window.location.search).get("admin") === "1";

function loadJSON(key, fallback) {
  try {
    const raw = localStorage.getItem(key);
    return raw ? JSON.parse(raw) : fallback;
  } catch {
    return fallback;
  }
}

function saveJSON(key, value) {
  try {
    localStorage.setItem(key, JSON.stringify(value));
  } catch {
    // ignore quota errors
  }
}

function getOrCreateClientId() {
  let id = localStorage.getItem(LS_CLIENT_ID);
  if (!id) {
    id = `u-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 8)}`;
    try {
      localStorage.setItem(LS_CLIENT_ID, id);
    } catch {
      // ignore
    }
  }
  return id;
}

const CLIENT_ID = getOrCreateClientId();

// Состояние приложения
const state = {
  serverMode: false,
  tracks: [...FALLBACK_TRACKS],
  genre: "all",
  activePlaylistId: null,
  search: "",
  currentTrackId: null,
  isPlaying: false,
  isShuffle: false,
  isRepeat: false,
  favorites: new Set(loadJSON(LS_FAVORITES, [])),
  likeCounts: loadJSON(LS_LIKES_MAP, {}), // { trackId: number }
  commentsMap: loadJSON(LS_COMMENTS_MAP, {}), // { trackId: [{ id, author, text, createdAt, clientId }] }
  playlists: loadJSON(LS_PLAYLISTS, []), // [{ id, name, trackIds: [] }]
  selectedFiles: [],
  selectedCoverFile: null,
  editingPlaylistId: null,
  playlistModalTrackId: null,
  activeCommentsTrackId: null,
  coverTargetTrackId: null,
};

// DOM-элементы
const audio = document.getElementById("audioPlayer");
const modeBadge = document.getElementById("modeBadge");
const tracksGrid = document.getElementById("tracksGrid");
const emptyState = document.getElementById("emptyState");
const emptyTitle = document.getElementById("emptyTitle");
const emptyDesc = document.getElementById("emptyDesc");
const genreTabs = document.getElementById("genreTabs");
const searchInput = document.getElementById("searchInput");
const resultsLabel = document.getElementById("resultsLabel");
const playAllBtn = document.getElementById("playAllBtn");
const resetFiltersBtn = document.getElementById("resetFiltersBtn");
const rescanBtn = document.getElementById("rescanBtn");
const shareBtn = document.getElementById("shareBtn");

// Плейлисты
const playlistsChips = document.getElementById("playlistsChips");
const newPlaylistBtn = document.getElementById("newPlaylistBtn");
const playlistBanner = document.getElementById("playlistBanner");
const playlistBannerTitle = document.getElementById("playlistBannerTitle");
const playPlaylistBtn = document.getElementById("playPlaylistBtn");
const renamePlaylistBtn = document.getElementById("renamePlaylistBtn");
const deletePlaylistBtn = document.getElementById("deletePlaylistBtn");
const closePlaylistViewBtn = document.getElementById("closePlaylistViewBtn");

// Плеер
const playerCover = document.getElementById("playerCover");
const playerTitle = document.getElementById("playerTitle");
const playerArtist = document.getElementById("playerArtist");
const playerLikeBtn = document.getElementById("playerLikeBtn");
const playerCommentBtn = document.getElementById("playerCommentBtn");
const playPauseBtn = document.getElementById("playPauseBtn");
const prevBtn = document.getElementById("prevBtn");
const nextBtn = document.getElementById("nextBtn");
const shuffleBtn = document.getElementById("shuffleBtn");
const repeatBtn = document.getElementById("repeatBtn");
const progressBar = document.getElementById("progressBar");
const currentTimeEl = document.getElementById("currentTime");
const durationTimeEl = document.getElementById("durationTime");
const volumeBar = document.getElementById("volumeBar");
const muteBtn = document.getElementById("muteBtn");
const visualizerCanvas = document.getElementById("visualizer");

// Модалка загрузки
const uploadModal = document.getElementById("uploadModal");
const openUploadBtn = document.getElementById("openUploadBtn");
const closeUploadBtn = document.getElementById("closeUploadBtn");
const cancelUploadBtn = document.getElementById("cancelUploadBtn");
const uploadForm = document.getElementById("uploadForm");
const dropzone = document.getElementById("dropzone");
const fileInput = document.getElementById("fileInput");
const dropzoneText = document.getElementById("dropzoneText");
const uploadGenre = document.getElementById("uploadGenre");
const uploadTitle = document.getElementById("uploadTitle");
const uploadArtist = document.getElementById("uploadArtist");
const coverInput = document.getElementById("coverInput");
const coverPreviewRow = document.getElementById("coverPreviewRow");
const coverPreviewImg = document.getElementById("coverPreviewImg");
const coverPreviewName = document.getElementById("coverPreviewName");
const clearCoverBtn = document.getElementById("clearCoverBtn");
const submitUploadBtn = document.getElementById("submitUploadBtn");
const publicUploadNotice = document.getElementById("publicUploadNotice");
const githubUploadLink = document.getElementById("githubUploadLink");

// Модалка создания/переименования плейлиста
const playlistModal = document.getElementById("playlistModal");
const playlistModalTitle = document.getElementById("playlistModalTitle");
const closePlaylistModalBtn = document.getElementById("closePlaylistModalBtn");
const cancelPlaylistModalBtn = document.getElementById("cancelPlaylistModalBtn");
const playlistForm = document.getElementById("playlistForm");
const playlistNameInput = document.getElementById("playlistNameInput");
const savePlaylistBtn = document.getElementById("savePlaylistBtn");

// Модалка добавления трека в плейлисты
const addToPlaylistModal = document.getElementById("addToPlaylistModal");
const closeAddToPlaylistBtn = document.getElementById("closeAddToPlaylistBtn");
const addToPlaylistTrackName = document.getElementById("addToPlaylistTrackName");
const playlistChecklist = document.getElementById("playlistChecklist");
const quickPlaylistForm = document.getElementById("quickPlaylistForm");
const quickPlaylistInput = document.getElementById("quickPlaylistInput");

// Модалка комментариев
const commentsModal = document.getElementById("commentsModal");
const closeCommentsBtn = document.getElementById("closeCommentsBtn");
const commentsTrackCover = document.getElementById("commentsTrackCover");
const commentsModalTitle = document.getElementById("commentsModalTitle");
const commentsTrackArtist = document.getElementById("commentsTrackArtist");
const commentsLikeBtn = document.getElementById("commentsLikeBtn");
const commentsLikeCount = document.getElementById("commentsLikeCount");
const commentsList = document.getElementById("commentsList");
const commentForm = document.getElementById("commentForm");
const commentAuthorInput = document.getElementById("commentAuthorInput");
const commentTextInput = document.getElementById("commentTextInput");
const commentSubmitBtn = document.getElementById("commentSubmitBtn");

const changeCoverInput = document.getElementById("changeCoverInput");
const toastContainer = document.getElementById("toastContainer");

// Уведомления
function showToast(message) {
  const el = document.createElement("div");
  el.className = "toast";
  el.textContent = message;
  toastContainer.appendChild(el);
  setTimeout(() => {
    el.style.opacity = "0";
    el.style.transition = "opacity 0.25s ease";
    setTimeout(() => el.remove(), 260);
  }, 2600);
}

// Визуализатор эквалайзера (без перехвата аудиопотока Web Audio API, чтобы браузер никогда не глушил звук из-за CORS)
let vizRunning = false;

function initVisualizer() {
  if (vizRunning) return;
  vizRunning = true;
  drawVisualizer();
}

function drawVisualizer() {
  requestAnimationFrame(drawVisualizer);
  const ctx = visualizerCanvas.getContext("2d");
  if (!ctx) return;
  const { width, height } = visualizerCanvas;
  ctx.clearRect(0, 0, width, height);

  const barCount = 16;
  const gap = 3;
  const barWidth = (width - gap * (barCount - 1)) / barCount;
  const t = performance.now() / 160;

  for (let i = 0; i < barCount; i++) {
    let norm = 0.1;
    if (state.isPlaying && !audio.paused) {
      const wave1 = Math.sin(t * 1.15 + i * 0.65);
      const wave2 = Math.cos(t * 0.72 - i * 0.42);
      const wave3 = Math.sin(t * 1.9 + i * 1.15) * 0.35;
      norm = 0.22 + 0.68 * Math.abs((wave1 + wave2 + wave3) / 2.35);
    }
    const barH = Math.max(3, Math.min(height, norm * height));
    const x = i * (barWidth + gap);
    const y = height - barH;

    const grad = ctx.createLinearGradient(0, y, 0, height);
    grad.addColorStop(0, "#38bdf8");
    grad.addColorStop(1, "#7c5cff");
    ctx.fillStyle = grad;
    ctx.beginPath();
    if (typeof ctx.roundRect === "function") {
      ctx.roundRect(x, y, barWidth, barH, 3);
    } else {
      ctx.rect(x, y, barWidth, barH);
    }
    ctx.fill();
  }
}

// Безопасное кодирование путей к аудио и обложкам (кириллица, пробелы, запятые, скобки)
function encodeTrackUrl(url) {
  if (!url) return "";
  if (/^(https?:|blob:|data:)/i.test(url)) return url;
  return url
    .split("/")
    .map((part) => {
      try {
        return encodeURIComponent(decodeURIComponent(part));
      } catch {
        return encodeURIComponent(part);
      }
    })
    .join("/");
}

// Утилиты
function formatTime(seconds) {
  if (!Number.isFinite(seconds) || seconds < 0) return "0:00";
  const mins = Math.floor(seconds / 60);
  const secs = Math.floor(seconds % 60);
  return `${mins}:${secs.toString().padStart(2, "0")}`;
}

function escapeHtml(text) {
  return String(text ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function fileToDataUrl(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result);
    reader.onerror = reject;
    reader.readAsDataURL(file);
  });
}

function cleanFileTitle(filename) {
  return filename
    .replace(/\.[^/.]+$/, "")
    .replace(/[-_]+/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}

function isTrackInAnyPlaylist(trackId) {
  return state.playlists.some((pl) => pl.trackIds.includes(trackId));
}

function parseTrackFilename(filename) {
  const stem = filename.replace(/\.[^/.]+$/, "");
  if (stem.includes(" - ")) {
    const [artist, ...rest] = stem.split(" - ");
    return {
      artist: artist.trim() || "Моя коллекция",
      title: rest.join(" - ").trim() || stem,
    };
  }
  const cleaned = cleanFileTitle(filename);
  return {
    artist: "Моя коллекция",
    title: cleaned ? cleaned.charAt(0).toUpperCase() + cleaned.slice(1) : stem,
  };
}

// Дополнительная проверка новых файлов напрямую из папок на GitHub (чтобы новые песни появлялись сразу)
async function mergeNewTracksFromGitHub() {
  const genreKeys = Object.keys(GENRES);
  const existingIds = new Set(state.tracks.map((t) => t.id));
  let added = 0;

  await Promise.all(
    genreKeys.map(async (genre) => {
      try {
        const apiUrl = `https://api.github.com/repos/${GITHUB_OWNER}/${GITHUB_REPO}/contents/music_website/tracks/${genre}?ref=${GITHUB_BRANCH}`;
        const res = await fetch(apiUrl, { headers: { Accept: "application/vnd.github.v3+json" } });
        if (!res.ok) return;
        const items = await res.json();
        if (!Array.isArray(items)) return;

        const coverByStem = new Map();
        for (const item of items) {
          if (item.type === "file" && IMAGE_EXT_RE.test(item.name)) {
            const stem = item.name.replace(/\.[^/.]+$/, "").toLowerCase();
            coverByStem.set(stem, item.download_url || `tracks/${genre}/${encodeURIComponent(item.name)}`);
          }
        }

        for (const item of items) {
          if (item.type !== "file" || !AUDIO_EXT_RE.test(item.name)) continue;
          const relId = `tracks/${genre}/${item.name}`;
          if (existingIds.has(relId)) continue;

          const { artist, title } = parseTrackFilename(item.name);
          const stem = item.name.replace(/\.[^/.]+$/, "").toLowerCase();
          state.tracks.unshift({
            id: relId,
            title,
            artist,
            genre,
            src: `tracks/${genre}/${encodeURIComponent(item.name)}`,
            fallbackSrc: item.download_url || null,
            cover: coverByStem.get(stem) || null,
            duration: "--:--",
          });
          existingIds.add(relId);
          added++;
        }
      } catch {
        // Тихий пропуск, если API недоступен или достигнут лимит
      }
    })
  );

  if (added > 0) {
    renderAll();
  }
}

function encodeFirebaseKey(trackId) {
  return trackId.replace(/[.#$/[\]]/g, "_");
}

function getLikeCount(trackId) {
  const stored = Number(state.likeCounts[trackId] || 0);
  const minForSelf = state.favorites.has(trackId) ? 1 : 0;
  return Math.max(stored, minForSelf);
}

function getTrackComments(trackId) {
  const arr = state.commentsMap[trackId];
  return Array.isArray(arr) ? arr : [];
}

function syncOwnerControls() {
  const showOwner = state.serverMode || IS_ADMIN;
  openUploadBtn.classList.toggle("hidden", !showOwner);
}

async function loadSocialData() {
  if (state.serverMode) {
    try {
      const res = await fetch("/api/social", { cache: "no-store" });
      if (res.ok) {
        const data = await res.json();
        state.likeCounts = data.likes || {};
        state.commentsMap = data.comments || {};
        saveJSON(LS_LIKES_MAP, state.likeCounts);
        saveJSON(LS_COMMENTS_MAP, state.commentsMap);
        renderTracks();
        if (state.activeCommentsTrackId) renderCommentsModal();
      }
    } catch {
      // Используем локальные данные
    }
    return;
  }

  const fbBase = FIREBASE_DB_URL.replace(/\/+$/, "");
  if (!fbBase) return;

  try {
    const res = await fetch(`${fbBase}/social.json`, { cache: "no-store" });
    if (!res.ok) return;
    const data = await res.json();
    if (!data) return;

    const likes = {};
    const comments = {};
    for (const track of state.tracks) {
      const key = encodeFirebaseKey(track.id);
      if (data.likes && typeof data.likes[key] === "number") {
        likes[track.id] = data.likes[key];
      }
      if (data.comments && data.comments[key]) {
        const rawObj = data.comments[key];
        const list = Array.isArray(rawObj) ? rawObj.filter(Boolean) : Object.values(rawObj);
        comments[track.id] = list.sort((a, b) => (b.createdAt || 0) - (a.createdAt || 0));
      }
    }
    state.likeCounts = { ...state.likeCounts, ...likes };
    state.commentsMap = { ...state.commentsMap, ...comments };
    saveJSON(LS_LIKES_MAP, state.likeCounts);
    saveJSON(LS_COMMENTS_MAP, state.commentsMap);
    renderTracks();
    if (state.activeCommentsTrackId) renderCommentsModal();
  } catch {
    // Тихий fallback на localStorage
  }
}

// Загрузка треков: сначала локальный сервер /api/tracks, затем tracks/tracks.json + GitHub
async function loadTracksFromServer(notify = false) {
  rescanBtn.classList.add("is-spinning");
  try {
    const res = await fetch("/api/tracks", { cache: "no-store" });
    if (!res.ok) throw new Error("API unavailable");
    const data = await res.json();
    if (Array.isArray(data.tracks)) {
      state.serverMode = true;
      state.tracks = data.tracks;
      modeBadge.textContent = "Коллекция музыки по жанрам";
      rescanBtn.classList.remove("hidden");
      syncOwnerControls();
      await loadSocialData();
      if (notify) {
        showToast(`Список обновлён · треков: ${data.tracks.length}`);
      }
      renderAll();
      return;
    }
  } catch {
    state.serverMode = false;
    modeBadge.textContent = "Коллекция музыки по жанрам";
    rescanBtn.classList.remove("hidden");
    syncOwnerControls();

    // Пробуем загрузить автоматически сгенерированный tracks/tracks.json
    try {
      const idxRes = await fetch(`tracks/tracks.json?t=${Date.now()}`, { cache: "no-store" });
      if (idxRes.ok) {
        const idxData = await idxRes.json();
        if (Array.isArray(idxData.tracks)) {
          state.tracks = idxData.tracks;
        }
      }
    } catch {
      // Оставляем FALLBACK_TRACKS
    }

    renderAll();
    await mergeNewTracksFromGitHub();
    await loadSocialData();

    if (notify) {
      showToast(`Список обновлён · треков: ${state.tracks.length}`);
    }
    return;
  } finally {
    setTimeout(() => rescanBtn.classList.remove("is-spinning"), 350);
  }
  renderAll();
}

shareBtn?.addEventListener("click", async () => {
  const url = window.location.href;
  try {
    if (navigator.share) {
      await navigator.share({ title: document.title, url });
      return;
    }
    await navigator.clipboard.writeText(url);
    showToast("Ссылка скопирована — отправьте её друзьям!");
  } catch {
    showToast("Скопируйте ссылку из адресной строки браузера");
  }
});

// Сохранение лайков, комментариев и плейлистов
function persistFavorites() {
  saveJSON(LS_FAVORITES, Array.from(state.favorites));
}

function persistPlaylists() {
  saveJSON(LS_PLAYLISTS, state.playlists);
}

async function toggleFavorite(trackId) {
  if (!trackId) return;
  const alreadyLiked = state.favorites.has(trackId);
  const prevCount = getLikeCount(trackId);
  const delta = alreadyLiked ? -1 : 1;

  if (alreadyLiked) {
    state.favorites.delete(trackId);
    showToast("Лайк убран");
  } else {
    state.favorites.add(trackId);
    showToast("Понравилось ♥");
  }

  const nextCount = Math.max(0, prevCount + delta);
  state.likeCounts[trackId] = nextCount;
  persistFavorites();
  saveJSON(LS_LIKES_MAP, state.likeCounts);
  updatePlayerUI();
  renderAll();
  if (state.activeCommentsTrackId === trackId) renderCommentsModal();

  if (state.serverMode) {
    try {
      const res = await fetch("/api/like", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ trackId, delta }),
      });
      if (res.ok) {
        const data = await res.json();
        state.likeCounts[trackId] = data.likes;
        saveJSON(LS_LIKES_MAP, state.likeCounts);
        renderTracks();
        if (state.activeCommentsTrackId === trackId) renderCommentsModal();
      }
    } catch {
      // Локальное состояние уже обновлено
    }
  } else if (FIREBASE_DB_URL) {
    const fbBase = FIREBASE_DB_URL.replace(/\/+$/, "");
    const key = encodeFirebaseKey(trackId);
    try {
      await fetch(`${fbBase}/social/likes/${key}.json`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(nextCount),
      });
    } catch {
      // ignore
    }
  }
}

// Фильтрация треков
function getFilteredTracks() {
  const q = state.search.trim().toLowerCase();
  const activePlaylist = state.activePlaylistId
    ? state.playlists.find((p) => p.id === state.activePlaylistId)
    : null;

  return state.tracks.filter((track) => {
    if (activePlaylist && !activePlaylist.trackIds.includes(track.id)) {
      return false;
    }
    if (!activePlaylist) {
      if (state.genre === "favorites" && !state.favorites.has(track.id)) {
        return false;
      }
      if (state.genre !== "all" && state.genre !== "favorites" && track.genre !== state.genre) {
        return false;
      }
    }
    if (!q) return true;
    const genreName = (GENRES[track.genre]?.label || "").toLowerCase();
    return (
      track.title.toLowerCase().includes(q) ||
      track.artist.toLowerCase().includes(q) ||
      genreName.includes(q)
    );
  });
}

// Обновление счётчиков
function updateCounts() {
  const existingIds = new Set(state.tracks.map((t) => t.id));
  const counts = {
    all: state.tracks.length,
    favorites: Array.from(state.favorites).filter((id) => existingIds.has(id)).length,
    chanson: 0,
    disco: 0,
    deephouse: 0,
    other: 0,
  };
  for (const t of state.tracks) {
    if (counts[t.genre] !== undefined) counts[t.genre]++;
  }
  document.querySelectorAll("[data-count]").forEach((el) => {
    const key = el.getAttribute("data-count");
    el.textContent = counts[key] ?? 0;
  });
}

// Отрисовка панели плейлистов
function renderPlaylistsBar() {
  const existingIds = new Set(state.tracks.map((t) => t.id));

  if (state.playlists.length === 0) {
    playlistsChips.innerHTML = `<span class="playlists-empty-hint">Пока нет плейлистов — создайте свой</span>`;
  } else {
    playlistsChips.innerHTML = state.playlists
      .map((pl) => {
        const count = pl.trackIds.filter((id) => existingIds.has(id)).length;
        const active = pl.id === state.activePlaylistId;
        return `
          <button type="button" class="playlist-chip ${active ? "active" : ""}" data-playlist-id="${escapeHtml(pl.id)}">
            <span>${escapeHtml(pl.name)}</span>
            <span class="chip-count">${count}</span>
          </button>
        `;
      })
      .join("");
  }

  const activePl = state.playlists.find((p) => p.id === state.activePlaylistId);
  if (activePl) {
    playlistBanner.classList.remove("hidden");
    playlistBannerTitle.textContent = activePl.name;
  } else {
    playlistBanner.classList.add("hidden");
  }

  // Подсветка вкладок жанров
  genreTabs.querySelectorAll(".genre-tab").forEach((tab) => {
    const active = !state.activePlaylistId && tab.getAttribute("data-genre") === state.genre;
    tab.classList.toggle("active", active);
    tab.setAttribute("aria-selected", String(active));
  });
}

// Отрисовка сетки треков
function renderTracks() {
  updateCounts();
  const list = getFilteredTracks();
  resultsLabel.textContent = `Показано треков: ${list.length}`;

  if (list.length === 0) {
    tracksGrid.innerHTML = "";
    emptyState.classList.remove("hidden");
    if (state.activePlaylistId) {
      emptyTitle.textContent = "В этом плейлисте пока пусто";
      emptyDesc.textContent = "Нажмите кнопку «+» на карточке любого трека, чтобы добавить его сюда.";
    } else if (state.genre === "favorites") {
      emptyTitle.textContent = "В избранном пока нет треков";
      emptyDesc.textContent = "Нажмите на сердечко ♥ на любой карточке, чтобы добавить трек в избранное.";
    } else {
      emptyTitle.textContent = "Пока нет треков";
      emptyDesc.textContent = "Выберите другой жанр, очистите поиск или загляните позже — музыка скоро появится.";
    }
    return;
  }

  emptyState.classList.add("hidden");

  tracksGrid.innerHTML = list
    .map((track) => {
      const genreInfo = GENRES[track.genre] || { label: track.genre, icon: "♪" };
      const isCurrent = track.id === state.currentTrackId;
      const isPlayingCurrent = isCurrent && state.isPlaying;
      const isLiked = state.favorites.has(track.id);
      const likeCount = getLikeCount(track.id);
      const commentCount = getTrackComments(track.id).length;
      const inPlaylist = isTrackInAnyPlaylist(track.id);
      const showOwner = state.serverMode || IS_ADMIN;

      const cardClass = [
        "track-card",
        isCurrent ? "is-playing" : "",
        isCurrent && !state.isPlaying ? "is-paused" : "",
      ]
        .filter(Boolean)
        .join(" ");

      const coverHtml = track.cover
        ? `<img class="cover-img" src="${escapeHtml(encodeTrackUrl(track.cover))}" alt="Обложка ${escapeHtml(track.title)}" loading="lazy" />`
        : `<span class="cover-symbol" aria-hidden="true">${genreInfo.icon}</span>`;

      const coverEditHtml = showOwner
        ? `<div class="cover-top-actions">
              <button
                type="button"
                class="cover-mini-btn"
                data-action="cover"
                data-id="${escapeHtml(track.id)}"
                title="Изменить обложку"
                aria-label="Изменить обложку для ${escapeHtml(track.title)}"
              >
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                  <rect x="3" y="3" width="18" height="18" rx="2" ry="2" />
                  <circle cx="8.5" cy="8.5" r="1.5" />
                  <polyline points="21 15 16 10 5 21" />
                </svg>
              </button>
            </div>`
        : "";

      return `
        <article class="${cardClass}" data-id="${escapeHtml(track.id)}">
          <div class="track-cover cover-${escapeHtml(track.genre)}" data-action="toggle" data-id="${escapeHtml(track.id)}">
            ${coverHtml}
            <span class="track-genre-badge">${escapeHtml(genreInfo.label)}</span>
            ${coverEditHtml}

            <div class="eq-bars" aria-hidden="true">
              <span></span><span></span><span></span><span></span>
            </div>

            <button
              type="button"
              class="cover-play-overlay"
              data-action="toggle"
              data-id="${escapeHtml(track.id)}"
              aria-label="${isPlayingCurrent ? "Пауза" : "Воспроизвести"} ${escapeHtml(track.title)}"
            >
              ${
                isPlayingCurrent
                  ? `<svg viewBox="0 0 24 24" fill="currentColor"><rect x="6" y="4" width="4" height="16" rx="1"/><rect x="14" y="4" width="4" height="16" rx="1"/></svg>`
                  : `<svg viewBox="0 0 24 24" fill="currentColor"><polygon points="7 4 20 12 7 20 7 4"/></svg>`
              }
            </button>
          </div>

          <div class="track-head-row">
            <div class="track-info">
              <h3 class="track-title" title="${escapeHtml(track.title)}">${escapeHtml(track.title)}</h3>
              <p class="track-artist" title="${escapeHtml(track.artist)}">${escapeHtml(track.artist)}</p>
            </div>
          </div>

          <div class="card-social-bar">
            <button
              type="button"
              class="social-pill like-pill ${isLiked ? "liked" : ""}"
              data-action="like"
              data-id="${escapeHtml(track.id)}"
              title="${isLiked ? "Убрать лайк" : "Поставить лайк"}"
              aria-label="${isLiked ? "Убрать лайк" : "Поставить лайк"}"
            >
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z" />
              </svg>
              <span>${likeCount}</span>
            </button>

            <button
              type="button"
              class="social-pill comment-pill ${commentCount > 0 ? "has-comments" : ""}"
              data-action="comments"
              data-id="${escapeHtml(track.id)}"
              title="Комментарии к треку"
              aria-label="Открыть комментарии (${commentCount})"
            >
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <path d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z" />
              </svg>
              <span>${commentCount}</span>
            </button>
          </div>

          <div class="track-footer">
            <span class="track-duration">${escapeHtml(track.duration || "--:--")}</span>
            <div class="track-actions">
              <button
                type="button"
                class="card-action-btn ${inPlaylist ? "in-playlist" : ""}"
                data-action="playlist"
                data-id="${escapeHtml(track.id)}"
                title="Добавить в плейлист"
                aria-label="Добавить ${escapeHtml(track.title)} в плейлист"
              >
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
                  <line x1="12" y1="5" x2="12" y2="19" />
                  <line x1="5" y1="12" x2="19" y2="12" />
                </svg>
              </button>
            </div>
          </div>
        </article>
      `;
    })
    .join("");
}

function renderAll() {
  renderPlaylistsBar();
  renderTracks();
}

// Обновление нижнего плеера
function updatePlayerUI() {
  const track = state.tracks.find((t) => t.id === state.currentTrackId);
  const iconPlay = playPauseBtn.querySelector(".icon-play");
  const iconPause = playPauseBtn.querySelector(".icon-pause");

  iconPlay.classList.toggle("hidden", state.isPlaying);
  iconPause.classList.toggle("hidden", !state.isPlaying);

  if (!track) {
    playerLikeBtn.classList.remove("liked");
    return;
  }

  const genreInfo = GENRES[track.genre] || { label: track.genre, icon: "♪" };
  playerTitle.textContent = track.title;
  playerArtist.textContent = `${track.artist} · ${genreInfo.label}`;
  playerCover.className = `player-cover cover-${track.genre}`;
  playerCover.innerHTML = track.cover
    ? `<img src="${escapeHtml(encodeTrackUrl(track.cover))}" alt="" />`
    : `<span>${genreInfo.icon}</span>`;

  playerLikeBtn.classList.toggle("liked", state.favorites.has(track.id));
}

// Воспроизведение
function playTrack(trackId) {
  const track = state.tracks.find((t) => t.id === trackId);
  if (!track) return;

  initVisualizer();

  if (state.currentTrackId !== trackId) {
    state.currentTrackId = trackId;
    audio.dataset.fallbackUsed = "0";
    audio.src = encodeTrackUrl(track.src);
    audio.currentTime = 0;
  }

  audio
    .play()
    .then(() => {
      state.isPlaying = true;
      updatePlayerUI();
      renderTracks();
    })
    .catch((err) => {
      // Если основной файл ещё не опубликован на GitHub Pages, пробуем запасную ссылку raw.githubusercontent.com
      if (track.fallbackSrc && audio.dataset.fallbackUsed !== "1") {
        audio.dataset.fallbackUsed = "1";
        audio.src = track.fallbackSrc;
        audio
          .play()
          .then(() => {
            state.isPlaying = true;
            updatePlayerUI();
            renderTracks();
          })
          .catch((err2) => {
            console.error("Ошибка воспроизведения:", err2);
            showToast("Не удалось воспроизвести файл");
          });
        return;
      }
      console.error("Ошибка воспроизведения:", err);
      showToast("Не удалось воспроизвести файл");
    });
}

function toggleTrack(trackId) {
  if (state.currentTrackId === trackId) {
    if (state.isPlaying) {
      audio.pause();
      state.isPlaying = false;
      updatePlayerUI();
      renderTracks();
    } else {
      playTrack(trackId);
    }
  } else {
    playTrack(trackId);
  }
}

function stepTrack(direction) {
  const list = getFilteredTracks();
  const pool = list.length > 0 ? list : state.tracks;
  if (pool.length === 0) return;

  if (state.isShuffle && pool.length > 1) {
    const others = pool.filter((t) => t.id !== state.currentTrackId);
    const randomTrack = others[Math.floor(Math.random() * others.length)];
    playTrack(randomTrack.id);
    return;
  }

  const idx = pool.findIndex((t) => t.id === state.currentTrackId);
  const nextIdx = idx === -1 ? 0 : (idx + direction + pool.length) % pool.length;
  playTrack(pool[nextIdx].id);
}

// --- События фильтров и карточек ---
genreTabs.addEventListener("click", (e) => {
  const btn = e.target.closest(".genre-tab");
  if (!btn) return;
  const genre = btn.getAttribute("data-genre");
  if (!genre) return;

  state.activePlaylistId = null;
  state.genre = genre;
  renderAll();
});

searchInput.addEventListener("input", (e) => {
  state.search = e.target.value;
  renderTracks();
});

resetFiltersBtn.addEventListener("click", () => {
  state.activePlaylistId = null;
  state.genre = "all";
  state.search = "";
  searchInput.value = "";
  renderAll();
});

rescanBtn.addEventListener("click", () => loadTracksFromServer(true));

playAllBtn.addEventListener("click", () => {
  const list = getFilteredTracks();
  if (list.length > 0) playTrack(list[0].id);
});

tracksGrid.addEventListener("click", (e) => {
  const actionEl = e.target.closest("[data-action]");
  if (!actionEl) return;

  const action = actionEl.getAttribute("data-action");
  const id = actionEl.getAttribute("data-id");
  if (!id) return;

  if (action === "like") {
    e.stopPropagation();
    toggleFavorite(id);
  } else if (action === "comments") {
    e.stopPropagation();
    openCommentsModal(id);
  } else if (action === "playlist") {
    e.stopPropagation();
    openAddToPlaylistModal(id);
  } else if (action === "cover") {
    e.stopPropagation();
    state.coverTargetTrackId = id;
    changeCoverInput.value = "";
    changeCoverInput.click();
  } else if (action === "toggle") {
    toggleTrack(id);
  }
});

// Смена обложки любого трека
changeCoverInput.addEventListener("change", async (e) => {
  const file = e.target.files?.[0];
  const trackId = state.coverTargetTrackId;
  if (!file || !trackId) return;

  const track = state.tracks.find((t) => t.id === trackId);
  if (!track) return;

  try {
    const dataUrl = await fileToDataUrl(file);
    if (state.serverMode && !track.src.startsWith("blob:")) {
      const res = await fetch("/api/cover", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          trackId: track.id,
          coverFilename: file.name,
          coverBase64: dataUrl,
        }),
      });
      if (!res.ok) throw new Error("Не удалось сохранить обложку");
      const json = await res.json();
      track.cover = `${json.cover}?v=${Date.now()}`;
      showToast("Обложка сохранена в папке tracks/");
    } else {
      track.cover = dataUrl;
      showToast("Обложка обновлена");
    }
    updatePlayerUI();
    renderTracks();
  } catch (err) {
    console.error(err);
    showToast("Ошибка при обновлении обложки");
  } finally {
    state.coverTargetTrackId = null;
  }
});

// --- Плейлисты ---
playlistsChips.addEventListener("click", (e) => {
  const chip = e.target.closest(".playlist-chip");
  if (!chip) return;
  const plId = chip.getAttribute("data-playlist-id");
  state.activePlaylistId = state.activePlaylistId === plId ? null : plId;
  renderAll();
});

playPlaylistBtn.addEventListener("click", () => {
  const list = getFilteredTracks();
  if (list.length > 0) playTrack(list[0].id);
  else showToast("В плейлисте нет треков");
});

closePlaylistViewBtn.addEventListener("click", () => {
  state.activePlaylistId = null;
  renderAll();
});

deletePlaylistBtn.addEventListener("click", () => {
  if (!state.activePlaylistId) return;
  const pl = state.playlists.find((p) => p.id === state.activePlaylistId);
  if (!pl) return;
  state.playlists = state.playlists.filter((p) => p.id !== state.activePlaylistId);
  state.activePlaylistId = null;
  persistPlaylists();
  showToast(`Плейлист «${pl.name}» удалён`);
  renderAll();
});

function openPlaylistModal(editId = null) {
  state.editingPlaylistId = editId;
  if (editId) {
    const pl = state.playlists.find((p) => p.id === editId);
    playlistModalTitle.textContent = "Переименовать плейлист";
    savePlaylistBtn.textContent = "Сохранить";
    playlistNameInput.value = pl ? pl.name : "";
  } else {
    playlistModalTitle.textContent = "Новый плейлист";
    savePlaylistBtn.textContent = "Создать";
    playlistNameInput.value = "";
  }
  playlistModal.classList.remove("hidden");
  setTimeout(() => playlistNameInput.focus(), 40);
}

function closePlaylistModal() {
  playlistModal.classList.add("hidden");
  state.editingPlaylistId = null;
}

newPlaylistBtn.addEventListener("click", () => openPlaylistModal(null));
renamePlaylistBtn.addEventListener("click", () => {
  if (state.activePlaylistId) openPlaylistModal(state.activePlaylistId);
});
closePlaylistModalBtn.addEventListener("click", closePlaylistModal);
cancelPlaylistModalBtn.addEventListener("click", closePlaylistModal);
playlistModal.addEventListener("click", (e) => {
  if (e.target === playlistModal) closePlaylistModal();
});

playlistForm.addEventListener("submit", (e) => {
  e.preventDefault();
  const name = playlistNameInput.value.trim();
  if (!name) return;

  if (state.editingPlaylistId) {
    const pl = state.playlists.find((p) => p.id === state.editingPlaylistId);
    if (pl) {
      pl.name = name;
      showToast(`Плейлист переименован в «${name}»`);
    }
  } else {
    const newPl = { id: `pl-${Date.now()}`, name, trackIds: [] };
    state.playlists.push(newPl);
    state.activePlaylistId = newPl.id;
    showToast(`Плейлист «${name}» создан`);
  }
  persistPlaylists();
  closePlaylistModal();
  renderAll();
});

// Модалка «Добавить трек в плейлисты»
function renderPlaylistChecklist() {
  const trackId = state.playlistModalTrackId;
  if (!trackId) return;

  if (state.playlists.length === 0) {
    playlistChecklist.innerHTML = `<p class="playlists-empty-hint">Создайте свой первый плейлист ниже</p>`;
    return;
  }

  playlistChecklist.innerHTML = state.playlists
    .map((pl) => {
      const checked = pl.trackIds.includes(trackId);
      return `
        <label class="playlist-check-item">
          <span class="playlist-check-left">
            <input type="checkbox" data-pl-id="${escapeHtml(pl.id)}" ${checked ? "checked" : ""} />
            <span class="playlist-check-name">${escapeHtml(pl.name)}</span>
          </span>
          <span class="playlist-check-count">${pl.trackIds.length}</span>
        </label>
      `;
    })
    .join("");
}

function openAddToPlaylistModal(trackId) {
  const track = state.tracks.find((t) => t.id === trackId);
  if (!track) return;
  state.playlistModalTrackId = trackId;
  addToPlaylistTrackName.textContent = `${track.title} — ${track.artist}`;
  quickPlaylistInput.value = "";
  renderPlaylistChecklist();
  addToPlaylistModal.classList.remove("hidden");
}

function closeAddToPlaylistModal() {
  addToPlaylistModal.classList.add("hidden");
  state.playlistModalTrackId = null;
}

closeAddToPlaylistBtn.addEventListener("click", closeAddToPlaylistModal);
addToPlaylistModal.addEventListener("click", (e) => {
  if (e.target === addToPlaylistModal) closeAddToPlaylistModal();
});

playlistChecklist.addEventListener("change", (e) => {
  const checkbox = e.target.closest("input[type='checkbox']");
  if (!checkbox || !state.playlistModalTrackId) return;
  const plId = checkbox.getAttribute("data-pl-id");
  const pl = state.playlists.find((p) => p.id === plId);
  if (!pl) return;

  if (checkbox.checked) {
    if (!pl.trackIds.includes(state.playlistModalTrackId)) {
      pl.trackIds.push(state.playlistModalTrackId);
    }
    showToast(`Добавлено в «${pl.name}»`);
  } else {
    pl.trackIds = pl.trackIds.filter((id) => id !== state.playlistModalTrackId);
    showToast(`Убрано из «${pl.name}»`);
  }
  persistPlaylists();
  renderPlaylistChecklist();
  renderAll();
});

quickPlaylistForm.addEventListener("submit", (e) => {
  e.preventDefault();
  const name = quickPlaylistInput.value.trim();
  if (!name || !state.playlistModalTrackId) return;

  const newPl = {
    id: `pl-${Date.now()}`,
    name,
    trackIds: [state.playlistModalTrackId],
  };
  state.playlists.push(newPl);
  persistPlaylists();
  quickPlaylistInput.value = "";
  showToast(`Создан плейлист «${name}» и трек добавлен`);
  renderPlaylistChecklist();
  renderAll();
});

// --- Комментарии к треку ---
function formatCommentDate(ts) {
  if (!ts) return "";
  const diffSec = Math.floor((Date.now() - ts) / 1000);
  if (diffSec < 60) return "только что";
  if (diffSec < 3600) return `${Math.floor(diffSec / 60)} мин назад`;
  if (diffSec < 86400) return `${Math.floor(diffSec / 3600)} ч назад`;
  return new Date(ts).toLocaleString("ru-RU", {
    day: "numeric",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function renderCommentsModal() {
  const trackId = state.activeCommentsTrackId;
  if (!trackId) return;
  const track = state.tracks.find((t) => t.id === trackId);
  if (!track) return;

  const genreInfo = GENRES[track.genre] || { label: track.genre, icon: "♪" };
  commentsModalTitle.textContent = track.title;
  commentsTrackArtist.textContent = `${track.artist} · ${genreInfo.label}`;
  commentsTrackCover.className = `comments-track-cover cover-${track.genre}`;
  commentsTrackCover.innerHTML = track.cover
    ? `<img src="${escapeHtml(track.cover)}" alt="" />`
    : `<span>${genreInfo.icon}</span>`;

  const liked = state.favorites.has(trackId);
  commentsLikeBtn.classList.toggle("liked", liked);
  commentsLikeCount.textContent = String(getLikeCount(trackId));

  const items = getTrackComments(trackId);
  if (items.length === 0) {
    commentsList.innerHTML = `<div class="comments-empty">Пока нет комментариев — станьте первым!</div>`;
    return;
  }

  commentsList.innerHTML = items
    .map((c) => {
      const initial = (c.author || "Г").trim().charAt(0).toUpperCase() || "Г";
      const canDelete = !c.clientId || c.clientId === CLIENT_ID;
      return `
        <div class="comment-item" data-comment-id="${escapeHtml(c.id)}">
          <div class="comment-avatar" aria-hidden="true">${escapeHtml(initial)}</div>
          <div class="comment-body">
            <div class="comment-meta-row">
              <span class="comment-author">${escapeHtml(c.author || "Гость")}</span>
              <div class="comment-right-meta">
                <span class="comment-date">${escapeHtml(formatCommentDate(c.createdAt))}</span>
                ${
                  canDelete
                    ? `<button type="button" class="comment-delete-btn" data-delete-comment="${escapeHtml(c.id)}" title="Удалить комментарий">Удалить</button>`
                    : ""
                }
              </div>
            </div>
            <p class="comment-text">${escapeHtml(c.text)}</p>
          </div>
        </div>
      `;
    })
    .join("");
}

function openCommentsModal(trackId) {
  state.activeCommentsTrackId = trackId;
  const savedName = localStorage.getItem(LS_USERNAME) || "";
  if (savedName && !commentAuthorInput.value.trim()) {
    commentAuthorInput.value = savedName;
  }
  commentTextInput.value = "";
  renderCommentsModal();
  commentsModal.classList.remove("hidden");
  setTimeout(() => {
    (commentAuthorInput.value.trim() ? commentTextInput : commentAuthorInput).focus();
  }, 40);
}

function closeCommentsModal() {
  commentsModal.classList.add("hidden");
  state.activeCommentsTrackId = null;
}

closeCommentsBtn.addEventListener("click", closeCommentsModal);
commentsModal.addEventListener("click", (e) => {
  if (e.target === commentsModal) closeCommentsModal();
});

commentsLikeBtn.addEventListener("click", () => {
  if (state.activeCommentsTrackId) toggleFavorite(state.activeCommentsTrackId);
});

commentsList.addEventListener("click", async (e) => {
  const btn = e.target.closest("[data-delete-comment]");
  if (!btn || !state.activeCommentsTrackId) return;
  const commentId = btn.getAttribute("data-delete-comment");
  const trackId = state.activeCommentsTrackId;

  state.commentsMap[trackId] = getTrackComments(trackId).filter((c) => c.id !== commentId);
  saveJSON(LS_COMMENTS_MAP, state.commentsMap);
  renderCommentsModal();
  renderTracks();
  showToast("Комментарий удалён");

  if (state.serverMode) {
    try {
      await fetch("/api/comments/delete", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ trackId, commentId, clientId: CLIENT_ID }),
      });
    } catch {
      // ignore
    }
  } else if (FIREBASE_DB_URL) {
    const fbBase = FIREBASE_DB_URL.replace(/\/+$/, "");
    const key = encodeFirebaseKey(trackId);
    try {
      await fetch(`${fbBase}/social/comments/${key}/${encodeURIComponent(commentId)}.json`, {
        method: "DELETE",
      });
    } catch {
      // ignore
    }
  }
});

commentForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  const trackId = state.activeCommentsTrackId;
  if (!trackId) return;

  const author = commentAuthorInput.value.trim() || "Гость";
  const text = commentTextInput.value.trim();
  if (!text) return;

  try {
    localStorage.setItem(LS_USERNAME, author);
  } catch {
    // ignore
  }

  let newComment = {
    id: `c-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 6)}`,
    author,
    text,
    createdAt: Date.now(),
    clientId: CLIENT_ID,
  };

  commentSubmitBtn.disabled = true;

  if (state.serverMode) {
    try {
      const res = await fetch("/api/comments", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ trackId, author, text, clientId: CLIENT_ID }),
      });
      if (res.ok) {
        const data = await res.json();
        if (data.comment) newComment = data.comment;
      }
    } catch {
      // Сохраняем локально
    }
  } else if (FIREBASE_DB_URL) {
    const fbBase = FIREBASE_DB_URL.replace(/\/+$/, "");
    const key = encodeFirebaseKey(trackId);
    try {
      await fetch(`${fbBase}/social/comments/${key}/${encodeURIComponent(newComment.id)}.json`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(newComment),
      });
    } catch {
      // ignore
    }
  }

  const list = getTrackComments(trackId);
  state.commentsMap[trackId] = [newComment, ...list];
  saveJSON(LS_COMMENTS_MAP, state.commentsMap);

  commentTextInput.value = "";
  commentSubmitBtn.disabled = false;
  renderCommentsModal();
  renderTracks();
  showToast("Комментарий добавлен");
});

// --- Кнопки плеера ---
playerLikeBtn.addEventListener("click", () => {
  if (state.currentTrackId) toggleFavorite(state.currentTrackId);
});

playerCommentBtn.addEventListener("click", () => {
  if (state.currentTrackId) openCommentsModal(state.currentTrackId);
  else showToast("Сначала выберите трек");
});

playPauseBtn.addEventListener("click", () => {
  if (!state.currentTrackId) {
    const list = getFilteredTracks();
    const first = list[0] || state.tracks[0];
    if (first) playTrack(first.id);
    return;
  }
  toggleTrack(state.currentTrackId);
});

prevBtn.addEventListener("click", () => stepTrack(-1));
nextBtn.addEventListener("click", () => stepTrack(1));

shuffleBtn.addEventListener("click", () => {
  state.isShuffle = !state.isShuffle;
  shuffleBtn.classList.toggle("active", state.isShuffle);
});

repeatBtn.addEventListener("click", () => {
  state.isRepeat = !state.isRepeat;
  repeatBtn.classList.toggle("active", state.isRepeat);
});

audio.volume = Number(volumeBar.value);

audio.addEventListener("loadedmetadata", () => {
  durationTimeEl.textContent = formatTime(audio.duration);
  const track = state.tracks.find((t) => t.id === state.currentTrackId);
  if (track && Number.isFinite(audio.duration)) {
    track.duration = formatTime(audio.duration);
    renderTracks();
  }
});

audio.addEventListener("timeupdate", () => {
  if (!Number.isFinite(audio.duration) || audio.duration <= 0) return;
  const percent = (audio.currentTime / audio.duration) * 100;
  progressBar.value = String(percent);
  progressBar.style.background = `linear-gradient(90deg, #7c5cff ${percent}%, rgba(255,255,255,0.14) ${percent}%)`;
  currentTimeEl.textContent = formatTime(audio.currentTime);
});

audio.addEventListener("ended", () => {
  if (state.isRepeat) {
    audio.currentTime = 0;
    audio.play();
  } else {
    stepTrack(1);
  }
});

audio.addEventListener("error", () => {
  const track = state.tracks.find((t) => t.id === state.currentTrackId);
  if (track?.fallbackSrc && audio.dataset.fallbackUsed !== "1") {
    audio.dataset.fallbackUsed = "1";
    audio.src = track.fallbackSrc;
    audio.play().catch(() => {});
  }
});

progressBar.addEventListener("input", () => {
  if (!Number.isFinite(audio.duration) || audio.duration <= 0) return;
  audio.currentTime = (Number(progressBar.value) / 100) * audio.duration;
});

function syncVolumeIcons() {
  const muted = audio.muted || audio.volume === 0;
  muteBtn.querySelector(".icon-vol").classList.toggle("hidden", muted);
  muteBtn.querySelector(".icon-mute").classList.toggle("hidden", !muted);
}

volumeBar.addEventListener("input", () => {
  audio.volume = Number(volumeBar.value);
  audio.muted = audio.volume === 0;
  syncVolumeIcons();
});

muteBtn.addEventListener("click", () => {
  audio.muted = !audio.muted;
  syncVolumeIcons();
});

// Горячие клавиши
document.addEventListener("keydown", (e) => {
  const tag = document.activeElement?.tagName;
  if (tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT") return;

  if (e.code === "Space") {
    e.preventDefault();
    playPauseBtn.click();
  } else if (e.code === "ArrowRight" && Number.isFinite(audio.duration)) {
    audio.currentTime = Math.min(audio.duration, audio.currentTime + 5);
  } else if (e.code === "ArrowLeft" && Number.isFinite(audio.duration)) {
    audio.currentTime = Math.max(0, audio.currentTime - 5);
  }
});

// --- Модальное окно загрузки трека и обложки ---
function syncGithubUploadLink() {
  if (!githubUploadLink) return;
  const genre = uploadGenre.value || "chanson";
  githubUploadLink.href = `https://github.com/${GITHUB_OWNER}/${GITHUB_REPO}/upload/${GITHUB_BRANCH}/music_website/tracks/${genre}`;
  const label = GENRES[genre]?.label || genre;
  githubUploadLink.textContent = `Загрузить в «${label}» для всех друзей`;
}

function openUploadModal() {
  uploadModal.classList.remove("hidden");
  if (GENRES[state.genre]) {
    uploadGenre.value = state.genre;
  }
  syncGithubUploadLink();
  if (publicUploadNotice) {
    publicUploadNotice.classList.toggle("hidden", state.serverMode);
  }
}

uploadGenre.addEventListener("change", syncGithubUploadLink);

function clearCoverSelection() {
  state.selectedCoverFile = null;
  coverInput.value = "";
  coverPreviewRow.classList.add("hidden");
  coverPreviewImg.removeAttribute("src");
}

function closeUploadModal() {
  uploadModal.classList.add("hidden");
  state.selectedFiles = [];
  fileInput.value = "";
  uploadTitle.value = "";
  uploadArtist.value = "";
  clearCoverSelection();
  dropzoneText.innerHTML = 'Перетащите аудиофайлы сюда или <span>выберите на устройстве</span>';
  submitUploadBtn.disabled = true;
  submitUploadBtn.textContent = "Загрузить";
}

function handleSelectedFiles(fileList) {
  const files = Array.from(fileList).filter(
    (f) => f.type.startsWith("audio/") || /\.(mp3|wav|ogg|flac|m4a|aac|opus)$/i.test(f.name)
  );
  if (files.length === 0) return;

  state.selectedFiles = files;
  dropzoneText.innerHTML =
    files.length === 1
      ? `Выбран файл: <strong>${escapeHtml(files[0].name)}</strong>`
      : `Выбрано файлов: <strong>${files.length}</strong>`;
  if (files.length === 1 && !uploadTitle.value.trim()) {
    uploadTitle.value = cleanFileTitle(files[0].name);
  }
  submitUploadBtn.disabled = false;
}

openUploadBtn.addEventListener("click", openUploadModal);
closeUploadBtn.addEventListener("click", closeUploadModal);
cancelUploadBtn.addEventListener("click", closeUploadModal);
uploadModal.addEventListener("click", (e) => {
  if (e.target === uploadModal) closeUploadModal();
});

fileInput.addEventListener("change", (e) => handleSelectedFiles(e.target.files));

dropzone.addEventListener("dragover", (e) => {
  e.preventDefault();
  dropzone.classList.add("drag-over");
});

dropzone.addEventListener("dragleave", () => dropzone.classList.remove("drag-over"));

dropzone.addEventListener("drop", (e) => {
  e.preventDefault();
  dropzone.classList.remove("drag-over");
  handleSelectedFiles(e.dataTransfer.files);
});

coverInput.addEventListener("change", async (e) => {
  const file = e.target.files?.[0];
  if (!file) {
    clearCoverSelection();
    return;
  }
  state.selectedCoverFile = file;
  coverPreviewImg.src = await fileToDataUrl(file);
  coverPreviewName.textContent = file.name;
  coverPreviewRow.classList.remove("hidden");
});

clearCoverBtn.addEventListener("click", clearCoverSelection);

uploadForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  if (state.selectedFiles.length === 0) return;

  const genre = uploadGenre.value;
  const customArtist = uploadArtist.value.trim();
  const customTitle = state.selectedFiles.length === 1 ? uploadTitle.value.trim() : "";

  submitUploadBtn.disabled = true;
  submitUploadBtn.textContent = "Загрузка...";

  let coverDataUrl = null;
  let coverFilename = null;
  if (state.selectedCoverFile) {
    coverDataUrl = await fileToDataUrl(state.selectedCoverFile);
    coverFilename = state.selectedCoverFile.name;
  }

  let firstAddedId = null;

  try {
    if (state.serverMode) {
      for (const file of state.selectedFiles) {
        const audioBase64 = await fileToDataUrl(file);
        const res = await fetch("/api/upload", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            genre,
            title: customTitle || cleanFileTitle(file.name),
            artist: customArtist,
            filename: file.name,
            audioBase64,
            coverFilename,
            coverBase64: coverDataUrl,
          }),
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.error || "Ошибка загрузки");
        if (!firstAddedId && data.track) firstAddedId = data.track.id;
      }
      await loadTracksFromServer(false);
      showToast(`Сохранено в tracks/${genre}/`);
    } else {
      state.selectedFiles.forEach((file, idx) => {
        const id = `local-${Date.now()}-${idx}`;
        if (!firstAddedId) firstAddedId = id;
        const objectUrl = URL.createObjectURL(file);
        const track = {
          id,
          title: customTitle || cleanFileTitle(file.name) || file.name,
          artist: customArtist || "Локальный трек",
          genre,
          src: objectUrl,
          cover: coverDataUrl,
          duration: "--:--",
        };
        state.tracks.unshift(track);
        const probe = new Audio(objectUrl);
        probe.addEventListener("loadedmetadata", () => {
          track.duration = formatTime(probe.duration);
          renderTracks();
        });
      });
      renderAll();
      showToast("Трек добавлен в плеер");
    }

    closeUploadModal();
    if (firstAddedId) playTrack(firstAddedId);
  } catch (err) {
    console.error(err);
    showToast(err.message || "Не удалось загрузить файл");
    submitUploadBtn.disabled = false;
    submitUploadBtn.textContent = "Загрузить";
  }
});

// Старт приложения
loadTracksFromServer(false);
