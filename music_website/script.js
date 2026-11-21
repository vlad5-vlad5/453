// Справочник жанров
const GENRES = {
  electronic: { label: "Электроника", icon: "⚡", folder: "tracks/electronic" },
  ambient: { label: "Эмбиент", icon: "✦", folder: "tracks/ambient" },
  rock: { label: "Рок", icon: "🎸", folder: "tracks/rock" },
  pop: { label: "Поп", icon: "★", folder: "tracks/pop" },
};

// Резервный список треков (если сайт открыт статически без server.py)
const FALLBACK_TRACKS = [
  {
    id: "tracks/electronic/neon-pulse.wav",
    title: "Neon Pulse",
    artist: "SynthLab",
    genre: "electronic",
    src: "tracks/electronic/neon-pulse.wav",
    cover: "tracks/electronic/neon-pulse.svg",
    duration: "0:08",
  },
  {
    id: "tracks/ambient/northern-lights.wav",
    title: "Northern Lights",
    artist: "Aurora Drift",
    genre: "ambient",
    src: "tracks/ambient/northern-lights.wav",
    cover: "tracks/ambient/northern-lights.svg",
    duration: "0:09",
  },
  {
    id: "tracks/rock/electric-horizon.wav",
    title: "Electric Horizon",
    artist: "Voltage Drive",
    genre: "rock",
    src: "tracks/rock/electric-horizon.wav",
    cover: "tracks/rock/electric-horizon.svg",
    duration: "0:08",
  },
  {
    id: "tracks/pop/summer-skyline.wav",
    title: "Summer Skyline",
    artist: "Brightline",
    genre: "pop",
    src: "tracks/pop/summer-skyline.wav",
    cover: "tracks/pop/summer-skyline.svg",
    duration: "0:08",
  },
];

const LS_FAVORITES = "soundwave_favorites_v1";
const LS_PLAYLISTS = "soundwave_playlists_v1";

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
  playlists: loadJSON(LS_PLAYLISTS, []), // [{ id, name, trackIds: [] }]
  selectedFiles: [],
  selectedCoverFile: null,
  editingPlaylistId: null,
  playlistModalTrackId: null,
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

// Web Audio визуализатор
let audioCtx = null;
let analyser = null;
let dataArray = null;

function initVisualizer() {
  if (audioCtx) return;
  try {
    const AudioContextClass = window.AudioContext || window.webkitAudioContext;
    if (!AudioContextClass) return;
    audioCtx = new AudioContextClass();
    const source = audioCtx.createMediaElementSource(audio);
    analyser = audioCtx.createAnalyser();
    analyser.fftSize = 64;
    source.connect(analyser);
    analyser.connect(audioCtx.destination);
    dataArray = new Uint8Array(analyser.frequencyBinCount);
    drawVisualizer();
  } catch {
    // Визуализатор необязателен
  }
}

function drawVisualizer() {
  requestAnimationFrame(drawVisualizer);
  const ctx = visualizerCanvas.getContext("2d");
  const { width, height } = visualizerCanvas;
  ctx.clearRect(0, 0, width, height);

  const barCount = 16;
  const gap = 3;
  const barWidth = (width - gap * (barCount - 1)) / barCount;

  if (analyser && dataArray && state.isPlaying) {
    analyser.getByteFrequencyData(dataArray);
  }

  for (let i = 0; i < barCount; i++) {
    let norm = 0.08;
    if (state.isPlaying && dataArray) {
      norm = Math.max(0.12, (dataArray[i] || 0) / 255);
    }
    const barH = Math.max(3, norm * height);
    const x = i * (barWidth + gap);
    const y = height - barH;

    const grad = ctx.createLinearGradient(0, y, 0, height);
    grad.addColorStop(0, "#38bdf8");
    grad.addColorStop(1, "#7c5cff");
    ctx.fillStyle = grad;
    ctx.beginPath();
    ctx.roundRect(x, y, barWidth, barH, 3);
    ctx.fill();
  }
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

// Загрузка треков через серверное автосканирование /api/tracks
async function loadTracksFromServer(notify = false) {
  rescanBtn.classList.add("is-spinning");
  try {
    const res = await fetch("/api/tracks", { cache: "no-store" });
    if (!res.ok) throw new Error("API unavailable");
    const data = await res.json();
    if (Array.isArray(data.tracks)) {
      state.serverMode = true;
      state.tracks = data.tracks;
      modeBadge.textContent = "Автосканирование папок tracks/ активно";
      rescanBtn.classList.remove("hidden");
      if (notify) {
        showToast(`Папки просканированы · найдено треков: ${data.tracks.length}`);
      }
      renderAll();
      return;
    }
  } catch {
    state.serverMode = false;
    modeBadge.textContent = "Коллекция музыки по жанрам";
    rescanBtn.classList.add("hidden");
    if (notify) {
      showToast("Список треков обновлён");
    }
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

// Сохранение лайков и плейлистов
function persistFavorites() {
  saveJSON(LS_FAVORITES, Array.from(state.favorites));
}

function persistPlaylists() {
  saveJSON(LS_PLAYLISTS, state.playlists);
}

function toggleFavorite(trackId) {
  if (!trackId) return;
  if (state.favorites.has(trackId)) {
    state.favorites.delete(trackId);
    showToast("Убрано из избранного");
  } else {
    state.favorites.add(trackId);
    showToast("Добавлено в избранное ♥");
  }
  persistFavorites();
  updatePlayerUI();
  renderAll();
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
    electronic: 0,
    ambient: 0,
    rock: 0,
    pop: 0,
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
      emptyTitle.textContent = "Треки не найдены";
      emptyDesc.textContent = "Попробуйте выбрать другой жанр, очистить поиск или добавить свой аудиофайл.";
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
      const inPlaylist = isTrackInAnyPlaylist(track.id);

      const cardClass = [
        "track-card",
        isCurrent ? "is-playing" : "",
        isCurrent && !state.isPlaying ? "is-paused" : "",
      ]
        .filter(Boolean)
        .join(" ");

      const coverHtml = track.cover
        ? `<img class="cover-img" src="${escapeHtml(track.cover)}" alt="Обложка ${escapeHtml(track.title)}" loading="lazy" />`
        : `<span class="cover-symbol" aria-hidden="true">${genreInfo.icon}</span>`;

      return `
        <article class="${cardClass}" data-id="${escapeHtml(track.id)}">
          <div class="track-cover cover-${escapeHtml(track.genre)}" data-action="toggle" data-id="${escapeHtml(track.id)}">
            ${coverHtml}
            <span class="track-genre-badge">${escapeHtml(genreInfo.label)}</span>

            <div class="cover-top-actions">
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
            </div>

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
            <button
              type="button"
              class="like-btn ${isLiked ? "liked" : ""}"
              data-action="like"
              data-id="${escapeHtml(track.id)}"
              title="${isLiked ? "Убрать из избранного" : "В избранное"}"
              aria-label="${isLiked ? "Убрать из избранного" : "Добавить в избранное"}"
            >
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z" />
              </svg>
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

              <a
                class="download-link"
                href="${escapeHtml(track.src)}"
                download="${escapeHtml(track.title)}"
                title="Скачать трек"
                aria-label="Скачать ${escapeHtml(track.title)}"
              >
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                  <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                  <polyline points="7 10 12 15 17 10" />
                  <line x1="12" y1="15" x2="12" y2="3" />
                </svg>
              </a>
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
    ? `<img src="${escapeHtml(track.cover)}" alt="" />`
    : `<span>${genreInfo.icon}</span>`;

  playerLikeBtn.classList.toggle("liked", state.favorites.has(track.id));
}

// Воспроизведение
function playTrack(trackId) {
  const track = state.tracks.find((t) => t.id === trackId);
  if (!track) return;

  initVisualizer();
  if (audioCtx && audioCtx.state === "suspended") {
    audioCtx.resume();
  }

  if (state.currentTrackId !== trackId) {
    state.currentTrackId = trackId;
    audio.src = track.src;
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
  if (e.target.closest(".download-link")) return;

  const actionEl = e.target.closest("[data-action]");
  if (!actionEl) return;

  const action = actionEl.getAttribute("data-action");
  const id = actionEl.getAttribute("data-id");
  if (!id) return;

  if (action === "like") {
    e.stopPropagation();
    toggleFavorite(id);
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

// --- Кнопки плеера ---
playerLikeBtn.addEventListener("click", () => {
  if (state.currentTrackId) toggleFavorite(state.currentTrackId);
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
function openUploadModal() {
  uploadModal.classList.remove("hidden");
  if (GENRES[state.genre]) {
    uploadGenre.value = state.genre;
  }
}

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
