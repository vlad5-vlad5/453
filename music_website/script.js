// Справочник жанров
const GENRES = {
  chanson: { label: "Шансон", icon: "🎸", folder: "tracks/chanson" },
  disco: { label: "Диско", icon: "★", folder: "tracks/disco" },
  deephouse: { label: "ДипХаус", icon: "⚡", folder: "tracks/deephouse" },
  ruspop: { label: "Русская Поп-музыка", icon: "🎤", folder: "tracks/ruspop" },
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

// Общая база Firebase Realtime Database: лайки и комментарии видны всем друзьям
// на GitHub Pages. Правила доступа открывают только ветку /social.
const FIREBASE_DB_URL = "https://moya-novaya-muzyka-default-rtdb.firebaseio.com";

const LS_FAVORITES = "soundwave_favorites_v1";
const LS_PLAYLISTS = "soundwave_playlists_v1";
const LS_LIKES_MAP = "soundwave_likes_map_v1";
const LS_COMMENTS_MAP = "soundwave_comments_map_v1";
const LS_USERNAME = "soundwave_username_v1";
const LS_CLIENT_ID = "soundwave_client_id_v1";
const LS_EQ = "soundwave_eq_v1";

const EQ_PRESETS = {
  flat: { bassBoost: false, surround: false, bass: 0, mid: 0, treble: 0 },
  bass: { bassBoost: true, surround: false, bass: 7, mid: 0, treble: 2 },
  surround: { bassBoost: false, surround: true, bass: 3, mid: 1, treble: 3 },
  club: { bassBoost: true, surround: true, bass: 6.5, mid: -1, treble: 4 },
  vocal: { bassBoost: false, surround: false, bass: 2, mid: 3.5, treble: 2.5 },
};

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
  search: "", // поиск убран из интерфейса, поле оставлено для совместимости
  currentTrackId: null,
  isPlaying: false,
  isShuffle: false,
  isRepeat: false,
  favorites: new Set(loadJSON(LS_FAVORITES, [])),
  likeCounts: loadJSON(LS_LIKES_MAP, {}), // { trackId: number }
  commentsMap: loadJSON(LS_COMMENTS_MAP, {}), // { trackId: [{ id, author, text, createdAt, clientId }] }
  selectedFiles: [],
  selectedCoverFile: null,
  activeCommentsTrackId: null,
  coverTargetTrackId: null,
  eq: {
    bassBoost: false,
    surround: false,
    bass: 0,
    mid: 0,
    treble: 0,
    preset: "flat",
    ...loadJSON(LS_EQ, {}),
  },
};

// DOM-элементы
const audio = document.getElementById("audioPlayer");
const modeBadge = document.getElementById("modeBadge");
const tracksGrid = document.getElementById("tracksGrid");
const emptyState = document.getElementById("emptyState");
const emptyTitle = document.getElementById("emptyTitle");
const emptyDesc = document.getElementById("emptyDesc");
const genreTabs = document.getElementById("genreMenu"); // меню жанров
const genreMenuBtn = document.getElementById("genreMenuBtn");
const genreMenu = document.getElementById("genreMenu");
const genreCurrentLabel = document.getElementById("genreCurrentLabel");
const genreHint = document.getElementById("genreHint");
const resetFiltersBtn = document.getElementById("resetFiltersBtn");
const rescanBtn = document.getElementById("rescanBtn");
const shareBtn = document.getElementById("shareBtn");

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

// Удаление трека (только владельцу)
const deleteTrackModal = document.getElementById("deleteTrackModal");
const deleteTrackName = document.getElementById("deleteTrackName");
const deleteProgress = document.getElementById("deleteProgress");
const confirmDeleteTrackBtn = document.getElementById("confirmDeleteTrackBtn");
const cancelDeleteTrackBtn = document.getElementById("cancelDeleteTrackBtn");
const cancelDeleteTrackBtn2 = document.getElementById("cancelDeleteTrackBtn2");

// Панель владельца (статистика лайков и комментариев)
const ownerStatsBtn = document.getElementById("ownerStatsBtn");
const ownerPanel = document.getElementById("ownerPanel");
const closeOwnerPanelBtn = document.getElementById("closeOwnerPanelBtn");
const ownerList = document.getElementById("ownerList");
const ownerSyncStatus = document.getElementById("ownerSyncStatus");
const ownerRefreshBtn = document.getElementById("ownerRefreshBtn");
const ownerTracksCount = document.getElementById("ownerTracksCount");
const ownerLikesCount = document.getElementById("ownerLikesCount");
const ownerCommentsCount = document.getElementById("ownerCommentsCount");
const ownerLikedTracksCount = document.getElementById("ownerLikedTracksCount");
const ownerTokenInput = document.getElementById("ownerTokenInput");
const ownerTokenSaveBtn = document.getElementById("ownerTokenSaveBtn");
const ownerTokenClearBtn = document.getElementById("ownerTokenClearBtn");
const ownerTokenHint = document.getElementById("ownerTokenHint");
const ownerTokenCheckBtn = document.getElementById("ownerTokenCheckBtn");
const ownerTokenStatus = document.getElementById("ownerTokenStatus");

// Модалка настроек звука (Бас-буст / 3D / Эквалайзер)
const openEqBtn = document.getElementById("openEqBtn");
const eqModal = document.getElementById("eqModal");
const closeEqBtn = document.getElementById("closeEqBtn");
const doneEqBtn = document.getElementById("doneEqBtn");
const resetEqBtn = document.getElementById("resetEqBtn");
const bassBoostToggle = document.getElementById("bassBoostToggle");
const surroundToggle = document.getElementById("surroundToggle");
const eqPresetsEl = document.getElementById("eqPresets");
const eqBassSlider = document.getElementById("eqBassSlider");
const eqMidSlider = document.getElementById("eqMidSlider");
const eqTrebleSlider = document.getElementById("eqTrebleSlider");
const eqVolumeSlider = document.getElementById("eqVolumeSlider");
const eqBassVal = document.getElementById("eqBassVal");
const eqMidVal = document.getElementById("eqMidVal");
const eqTrebleVal = document.getElementById("eqTrebleVal");
const eqVolumeVal = document.getElementById("eqVolumeVal");

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

// --- Аудиодвижок: Бас-буст, Объёмный звук 3D, 3-полосный эквалайзер и лимитер ---
let audioEngine = null;
let vizRunning = false;

function isEqActive() {
  const { bassBoost, surround, bass, mid, treble } = state.eq;
  return Boolean(bassBoost || surround || bass !== 0 || mid !== 0 || treble !== 0);
}

function createStudioImpulse(ctx, durationSec = 0.42) {
  const rate = ctx.sampleRate;
  const length = Math.floor(rate * durationSec);
  const preDelay = Math.floor(rate * 0.012);
  const impulse = ctx.createBuffer(2, length, rate);

  for (let ch = 0; ch < 2; ch++) {
    const data = impulse.getChannelData(ch);
    let lp = 0;
    for (let i = preDelay; i < length; i++) {
      const progress = (i - preDelay) / (length - preDelay);
      const decay = Math.pow(1 - progress, 3.2);
      const noise = Math.random() * 2 - 1;
      // Мягкий ФНЧ для тёплого студийного объёма без металлического звона
      lp = lp * 0.72 + noise * 0.28;
      data[i] = lp * decay * 0.55;
    }
  }
  return impulse;
}

function ensureAudioEngine() {
  if (audioEngine) {
    if (audioEngine.ctx.state === "suspended") {
      audioEngine.ctx.resume().catch(() => {});
    }
    return audioEngine;
  }

  try {
    const AudioCtx = window.AudioContext || window.webkitAudioContext;
    if (!AudioCtx) return null;

    const ctx = new AudioCtx();
    const source = ctx.createMediaElementSource(audio);

    // 1. Отдельный фильтр для Бас-буста (68 Гц)
    const subBassBoost = ctx.createBiquadFilter();
    subBassBoost.type = "lowshelf";
    subBassBoost.frequency.value = 68;
    subBassBoost.gain.value = 0;

    // 2. 3-полосный музыкальный эквалайзер
    const bassFilter = ctx.createBiquadFilter();
    bassFilter.type = "lowshelf";
    bassFilter.frequency.value = 90;
    bassFilter.gain.value = 0;

    const midFilter = ctx.createBiquadFilter();
    midFilter.type = "peaking";
    midFilter.frequency.value = 1200;
    midFilter.Q.value = 1.0;
    midFilter.gain.value = 0;

    const trebleFilter = ctx.createBiquadFilter();
    trebleFilter.type = "highshelf";
    trebleFilter.frequency.value = 6500;
    trebleFilter.gain.value = 0;

    // 3. Прямой (сухой) сигнал
    const dryGain = ctx.createGain();
    dryGain.gain.value = 1.0;

    // 4. Объёмный звук 3D: расширение стереобазы (M/S) + студийное пространство
    const splitter = ctx.createChannelSplitter(2);
    const merger = ctx.createChannelMerger(2);
    const invRToL = ctx.createGain();
    const invLToR = ctx.createGain();
    invRToL.gain.value = -0.38;
    invLToR.gain.value = -0.38;

    const surroundWidthGain = ctx.createGain();
    surroundWidthGain.gain.value = 0;

    const convolver = ctx.createConvolver();
    convolver.buffer = createStudioImpulse(ctx, 0.42);
    const surroundReverbGain = ctx.createGain();
    surroundReverbGain.gain.value = 0;

    // 5. Мягкий лимитер, чтобы усиленный бас никогда не хрипел
    const compressor = ctx.createDynamicsCompressor();
    compressor.threshold.value = -4;
    compressor.knee.value = 12;
    compressor.ratio.value = 4;
    compressor.attack.value = 0.005;
    compressor.release.value = 0.15;

    const analyser = ctx.createAnalyser();
    analyser.fftSize = 256;
    analyser.smoothingTimeConstant = 0.45;
    const dataArray = new Uint8Array(analyser.frequencyBinCount);
    const timeDataArray = new Uint8Array(analyser.fftSize);

    // Отдельный «быстрый» анализатор для сценического светового движка:
    // меньше сглаживания и выше разрешение — атаки барабанов ловятся чётко
    const beatAnalyser = ctx.createAnalyser();
    beatAnalyser.fftSize = 512;
    beatAnalyser.smoothingTimeConstant = 0.35;
    const beatData = new Uint8Array(beatAnalyser.frequencyBinCount);

    // Коммутация цепочки
    source.connect(subBassBoost);
    subBassBoost.connect(bassFilter);
    bassFilter.connect(midFilter);
    midFilter.connect(trebleFilter);

    // Сухой путь
    trebleFilter.connect(dryGain);
    dryGain.connect(compressor);

    // Стерео-расширение (L - 0.38*R, R - 0.38*L)
    trebleFilter.connect(splitter);
    splitter.connect(merger, 0, 0);
    splitter.connect(invRToL, 1);
    invRToL.connect(merger, 0, 0);

    splitter.connect(merger, 1, 1);
    splitter.connect(invLToR, 0);
    invLToR.connect(merger, 0, 1);

    merger.connect(surroundWidthGain);
    surroundWidthGain.connect(compressor);

    // Мягкий объёмный ревербератор
    trebleFilter.connect(convolver);
    convolver.connect(surroundReverbGain);
    surroundReverbGain.connect(compressor);

    // Выход
    compressor.connect(analyser);
    analyser.connect(ctx.destination);
    // Параллельная ветка только для анализа ударов (в колонки не идёт)
    compressor.connect(beatAnalyser);

    audioEngine = {
      ctx,
      subBassBoost,
      bassFilter,
      midFilter,
      trebleFilter,
      dryGain,
      surroundWidthGain,
      surroundReverbGain,
      analyser,
      dataArray,
      timeDataArray,
      beatAnalyser,
      beatData,
      compressor,
    };

    if (ctx.state === "suspended") {
      ctx.resume().catch(() => {});
    }
    return audioEngine;
  } catch (err) {
    console.warn("Эквалайзер недоступен, используется стандартное воспроизведение:", err);
    return null;
  }
}

// Анализатор спектра нужен постоянно для цветомузыки, даже когда эквалайзер выключен.
// Цепочка при этом полностью прозрачна: Bass Boost / EQ / 3D стоят в нуле, сухой сигнал = 1.0,
// поэтому звук звучит ровно так же, как через нативный <audio>.
function ensureSpectrumAnalyser() {
  if (!audioEngine) {
    ensureAudioEngine();
  }
  if (!audioEngine) return null;

  if (audioEngine.ctx.state === "suspended") {
    audioEngine.ctx.resume().catch(() => {});
  }

  // Пока эквалайзер не включён — гарантируем нейтральные усиления (звук не тронут)
  if (!isEqActive()) {
    const now = audioEngine.ctx.currentTime;
    audioEngine.subBassBoost.gain.setTargetAtTime(0, now, 0.02);
    audioEngine.bassFilter.gain.setTargetAtTime(0, now, 0.02);
    audioEngine.midFilter.gain.setTargetAtTime(0, now, 0.02);
    audioEngine.trebleFilter.gain.setTargetAtTime(0, now, 0.02);
    audioEngine.dryGain.gain.setTargetAtTime(1.0, now, 0.02);
    audioEngine.surroundWidthGain.gain.setTargetAtTime(0, now, 0.02);
    audioEngine.surroundReverbGain.gain.setTargetAtTime(0, now, 0.02);
    // Лимитер в режиме «звук как есть» полностью прозрачен
    if (audioEngine.compressor) {
      audioEngine.compressor.threshold.setTargetAtTime(0, now, 0.02);
      audioEngine.compressor.ratio.setTargetAtTime(1, now, 0.02);
      audioEngine.compressor.knee.setTargetAtTime(0, now, 0.02);
    }
  }
  return audioEngine;
}

function applyEqSettings(initIfNeeded = false) {
  const { bassBoost, surround, bass, mid, treble } = state.eq;
  const active = isEqActive();

  if (active && (initIfNeeded || audioEngine)) {
    ensureAudioEngine();
  }

  if (audioEngine) {
    const now = audioEngine.ctx.currentTime;
    audioEngine.subBassBoost.gain.setTargetAtTime(bassBoost ? 6.5 : 0, now, 0.03);
    audioEngine.bassFilter.gain.setTargetAtTime(Number(bass) || 0, now, 0.03);
    audioEngine.midFilter.gain.setTargetAtTime(Number(mid) || 0, now, 0.03);
    audioEngine.trebleFilter.gain.setTargetAtTime(Number(treble) || 0, now, 0.03);

    audioEngine.dryGain.gain.setTargetAtTime(surround ? 0.88 : 1.0, now, 0.04);
    audioEngine.surroundWidthGain.gain.setTargetAtTime(surround ? 0.32 : 0, now, 0.04);
    audioEngine.surroundReverbGain.gain.setTargetAtTime(surround ? 0.24 : 0, now, 0.04);

    // Лимитер жёстко работает только при включённом эквалайзере,
    // иначе он полностью прозрачен и не подкрашивает звук
    if (audioEngine.compressor) {
      audioEngine.compressor.threshold.setTargetAtTime(active ? -4 : 0, now, 0.03);
      audioEngine.compressor.knee.setTargetAtTime(active ? 12 : 0, now, 0.03);
      audioEngine.compressor.ratio.setTargetAtTime(active ? 4 : 1, now, 0.03);
    }
  }

  saveJSON(LS_EQ, state.eq);
  syncEqUI();
}

function formatDb(v) {
  const num = Number(v) || 0;
  return `${num > 0 ? "+" : ""}${num} дБ`;
}

function syncEqUI() {
  const { bassBoost, surround, bass, mid, treble, preset } = state.eq;
  const active = isEqActive();

  if (openEqBtn) {
    openEqBtn.classList.toggle("active", active);
  }
  if (bassBoostToggle) {
    bassBoostToggle.classList.toggle("active", Boolean(bassBoost));
    bassBoostToggle.setAttribute("aria-pressed", String(Boolean(bassBoost)));
  }
  if (surroundToggle) {
    surroundToggle.classList.toggle("active", Boolean(surround));
    surroundToggle.setAttribute("aria-pressed", String(Boolean(surround)));
  }
  if (eqBassSlider) {
    eqBassSlider.value = String(bass);
    eqBassVal.textContent = formatDb(bass);
  }
  if (eqMidSlider) {
    eqMidSlider.value = String(mid);
    eqMidVal.textContent = formatDb(mid);
  }
  if (eqTrebleSlider) {
    eqTrebleSlider.value = String(treble);
    eqTrebleVal.textContent = formatDb(treble);
  }
  if (eqPresetsEl) {
    eqPresetsEl.querySelectorAll(".eq-preset-btn").forEach((btn) => {
      btn.classList.toggle("active", btn.getAttribute("data-preset") === preset);
    });
  }
  if (eqVolumeSlider && eqVolumeVal) {
    const vol = audio.muted ? 0 : audio.volume;
    eqVolumeSlider.value = String(vol);
    eqVolumeVal.textContent = `${Math.round(vol * 100)}%`;
  }
}

// Индикация плеера: Цветомузыка (неподвижные разноцветные лампочки) + Ползунки + классический Winamp
const LS_VIZ_MODE = "my_new_music_viz_mode_v4";
const VIZ_MODES = ["bulbs", "faders", "winamp", "osc"];
const BULB_COUNT = 8;
const FADER_BANDS = 10;
const SPECTRUM_BANDS = 16;

// Палитра 8 неподвижных разноцветных лампочек цветомузыки (от баса к высоким)
const BULB_PALETTE = [
  [255, 42, 66],   // красная (глубокий бас)
  [255, 132, 24],  // оранжевая (верхний бас)
  [255, 224, 28],  // жёлтая (нижняя середина)
  [56, 255, 98],   // ярко-зелёная (ритм / середина)
  [0, 240, 214],   // бирюзовая (вокал)
  [42, 162, 255],  // голубая (верхняя середина)
  [108, 102, 255], // сине-индиго (высокие)
  [232, 60, 255],  // фиолетово-розовая (тарелки)
];

// Точная классическая 16-цветная палитра Winamp (снизу вверх: ярко-зелёный -> жёлтый -> оранжевый -> красный)
const WINAMP_SPECTRUM_COLORS = [
  "#188408",
  "#1ca010",
  "#24bc16",
  "#2ed61d",
  "#47e214",
  "#7be80e",
  "#b4ee0a",
  "#e2f208",
  "#f7e408",
  "#f7c608",
  "#f7a408",
  "#f78208",
  "#f25e08",
  "#eb3b08",
  "#e21b08",
  "#d60000",
];

// Классические оттенки осциллографа Winamp (центр -> пик)
const WINAMP_OSC_COLORS = ["#31ef24", "#7bff68", "#c4ffba", "#ffffff"];

const savedVizMode = localStorage.getItem(LS_VIZ_MODE);
const vizState = {
  mode: VIZ_MODES.includes(savedVizMode) ? savedVizMode : "bulbs",
  levels: new Float32Array(SPECTRUM_BANDS),
  peaks: new Float32Array(SPECTRUM_BANDS),
  peakHold: new Float32Array(SPECTRUM_BANDS),
  peakVel: new Float32Array(SPECTRUM_BANDS),
  faderLevels: new Float32Array(FADER_BANDS),
  faderFlash: new Float32Array(FADER_BANDS),
  faderArmed: new Uint8Array(FADER_BANDS).fill(1),
  faderLastFlash: new Float32Array(FADER_BANDS),
  faderPeak: new Float32Array(FADER_BANDS).fill(0.35),
  faderPrevLevel: new Float32Array(FADER_BANDS),
  faderHighSince: new Float32Array(FADER_BANDS),
  faderCeilHold: new Float32Array(FADER_BANDS),
  lastFaderTime: 0,
  bulbFlash: new Float32Array(BULB_COUNT),
  bulbGlow: new Float32Array(BULB_COUNT),
  lastBulbTime: 0,
  lastFrameTime: 0,
};

// ============================================================================
// Адаптивное качество графики: слабые телефоны не должны тормозить
// Уровень 2 — полное качество, 1 — облегчённое, 0 — минимальное (только при просадке)
// ============================================================================
const LS_VIZ_QUALITY = "soundwave_viz_quality_v2";

const IS_MOBILE =
  /Android|iPhone|iPad|iPod|Mobile|Opera Mini|IEMobile/i.test(navigator.userAgent) ||
  (navigator.maxTouchPoints > 1 && window.matchMedia("(max-width: 1024px)").matches);

function initialVizQuality() {
  if (IS_MOBILE) return 1;
  // Слабый десктоп: мало ядер или немного памяти
  const cores = navigator.hardwareConcurrency || 4;
  const mem = navigator.deviceMemory || 8;
  if (cores <= 4 || mem <= 4) return 1;
  return 2;
}

let vizQuality = (() => {
  const saved = Number(localStorage.getItem(LS_VIZ_QUALITY));
  if (saved === 0 || saved === 1 || saved === 2) return Math.min(saved, initialVizQuality());
  return initialVizQuality();
})();

function saveVizQuality() {
  try {
    localStorage.setItem(LS_VIZ_QUALITY, String(vizQuality));
  } catch {
    // ignore
  }
}

// Авто-просадка: если FPS стабильно ниже 32, снижаем качество на ступень
const perfMonitor = { frames: 0, acc: 0, lastDrop: 0 };

function trackPerformance(dt) {
  perfMonitor.frames++;
  perfMonitor.acc += dt;
  if (perfMonitor.acc < 1.6) return;

  const fps = perfMonitor.frames / perfMonitor.acc;
  perfMonitor.frames = 0;
  perfMonitor.acc = 0;

  if (fps < 32 && vizQuality > 0) {
    const now = performance.now();
    if (now - perfMonitor.lastDrop > 5000) {
      perfMonitor.lastDrop = now;
      vizQuality -= 1;
      saveVizQuality();
    }
  }
}

const spectrumWrapEl = document.getElementById("spectrumWrap");
spectrumWrapEl?.addEventListener("click", () => {
  const idx = VIZ_MODES.indexOf(vizState.mode);
  vizState.mode = VIZ_MODES[(idx + 1) % VIZ_MODES.length];
  try {
    localStorage.setItem(LS_VIZ_MODE, vizState.mode);
  } catch {
    // ignore
  }
  const labels = {
    bulbs: "Индикатор: Цветомузыка (лампочки)",
    faders: "Индикатор: Ползунки",
    winamp: "Индикатор: Winamp Спектр",
    osc: "Индикатор: Winamp Осциллограф",
  };
  showToast(labels[vizState.mode] || "Индикатор");
});

// Логарифмическое распределение полос по бинам FFT (от глубокого баса 60 Гц к высоким 14 кГц)
function buildLogBandRanges(binCount, bands) {
  const ranges = [];
  const minBin = 1;
  const maxBin = Math.max(minBin + bands, Math.min(binCount - 1, 96));
  for (let i = 0; i < bands; i++) {
    const start = Math.floor(minBin * Math.pow(maxBin / minBin, i / bands));
    const end = Math.max(
      start + 1,
      Math.floor(minBin * Math.pow(maxBin / minBin, (i + 1) / bands))
    );
    ranges.push([start, Math.min(binCount, end)]);
  }
  return ranges;
}

const LOG_BAND_RANGES = buildLogBandRanges(128, SPECTRUM_BANDS);
const FADER_LOG_RANGES = buildLogBandRanges(128, FADER_BANDS);

// ============================================================================
// Сценический световой движок («как у артиста на сцене»)
// Лампочки больше не привязаны к полосам эквалайзера: движок ловит удары
// барабанов и раскладывает их в концертные световые паттерны, сменяющиеся
// каждый такт (4 удара бочки).
// ============================================================================

// Диапазоны бинов быстрого анализатора (fftSize 512, бин ≈ 86–94 Гц):
// 0–2 ≈ 0–260 Гц, 2–6 ≈ 170–560 Гц, 8–40 ≈ 0.7–3.7 кГц, 55–175 ≈ 4.7–15 кГц
const STAGE_BANDS = [
  [0, 3],     // 0: бочка (kick) — самый низ
  [3, 7],     // 1: низкий бас / томы
  [8, 40],    // 2: снейр, хлопки, вокал
  [55, 175],  // 3: хэт, тарелки
];

// Концертные световые схемы, сменяющиеся каждый такт
const STAGE_PATTERNS = ["all", "sweep", "odd-even", "wave"];

const stageState = {
  prevLevel: new Float32Array(4),
  fluxAvg: new Float32Array(4),
  lastHit: new Float32Array(4),
  lastBulb: new Float32Array(BULB_COUNT),
  kickCount: 0,
  hatCount: 0,
  pattern: 0,
  beatInterval: 0.55, // оценка периода бочки (109 BPM по умолчанию)
  nextBeat: 0,        // момент следующей восьмой доли такта
  clockStep: 0,       // номер восьмой доли
  lastKick: 0,
  detectedKicks: 0,
  syntheticKicks: 0,
  energy: 0,
};

const STAGE_COOLDOWN = [0.09, 0.09, 0.085, 0.07];

// Детектор атаки по спектральному потоку: важна не громкость, а ПРИРОСТ энергии
// относительно предыдущего кадра. Именно так ловят удар барабана — и не «привыкают»
// к плотному басовитому мастерингу, из-за которого старый детектор молчал.
function stageFlux(bandIndex, level, dt, t) {
  const i = bandIndex;
  const prev = stageState.prevLevel[i];
  const rise = Math.max(0, level - prev);
  stageState.prevLevel[i] = level;

  const mean = stageState.fluxAvg[i];
  stageState.fluxAvg[i] = mean + (rise - mean) * Math.min(1, dt * 2.2);

  // Адаптивный порог: заметно выше «обычного» шума, но не выше самой атаки
  const threshold = Math.max(0.014, mean * 1.25 + 0.008);
  if (rise > threshold && t - stageState.lastHit[i] > STAGE_COOLDOWN[i]) {
    stageState.lastHit[i] = t;
    return Math.min(1, 0.45 + level * 0.65);
  }
  return 0;
}

function stageBandLevel(range) {
  const bins = audioEngine.beatData;
  let peak = 0;
  let sum = 0;
  let count = 0;
  for (let b = range[0]; b < range[1]; b++) {
    const val = bins[b] || 0;
    if (val > peak) peak = val;
    sum += val;
    count++;
  }
  const avg = count ? sum / count : 0;
  // Лёгкая компрессия динамики: тихие удары тоже добивают до видимого уровня
  const raw = (peak * 0.7 + avg * 0.3) / 255;
  return Math.min(1, Math.pow(raw, 0.72) * 1.05);
}

// Зажечь лампочку короткой фотовспышкой (force — даже если только что горела)
function stageFireBulb(index, strength, t, force = false) {
  if (index < 0 || index >= BULB_COUNT) return;
  if (!force && t - stageState.lastBulb[index] < 0.055) return;
  stageState.lastBulb[index] = t;
  vizState.bulbFlash[index] = Math.max(vizState.bulbFlash[index], Math.min(1, strength));
  vizState.bulbGlow[index] = 1;
}

// Раскладка удара бочки по концертному паттерну.
// Паттерн меняется раз в такт (8 восьмых), а не на каждый удар — так шоу
// выглядит осмысленно, как у настоящего световика.
function stageKick(t, power) {
  const step = stageState.kickCount++;
  const bar = Math.floor(stageState.clockStep / 8);
  const pattern = STAGE_PATTERNS[bar % STAGE_PATTERNS.length];
  stageState.pattern = pattern;
  stageState.barIndex = bar;
  const strength = 1;
  const head = (step * 2) % BULB_COUNT;

  if (pattern === "all") {
    for (let i = 0; i < BULB_COUNT; i++) stageFireBulb(i, 1, t, true);
  } else if (pattern === "sweep") {
    stageFireBulb(head, 1, t, true);
    stageFireBulb((head + 1) % BULB_COUNT, 1, t, true);
  } else if (pattern === "odd-even") {
    const parity = step % 2;
    for (let i = parity; i < BULB_COUNT; i += 2) stageFireBulb(i, 1, t, true);
  } else {
    stageFireBulb(head, 1, t, true);
    stageFireBulb((head + 3) % BULB_COUNT, 1, t);
    stageFireBulb((head + 5) % BULB_COUNT, 1, t);
  }

  // Первые две лампочки всегда отмечают саму бочку — как низкие стробоскопы на сцене
  stageFireBulb(0, 1, t, true);
  if (pattern !== "sweep") stageFireBulb(1, 1, t);
}

function stageSnare(t, power) {
  const strength = 1;
  const bar = (stageState.barIndex || 0) % STAGE_PATTERNS.length;
  if (bar === 1) {
    // в «перебежке» снейр бьёт по краям
    stageFireBulb(0, strength, t);
    stageFireBulb(BULB_COUNT - 1, strength, t);
  } else if (bar === 2) {
    stageFireBulb(2, strength, t);
    stageFireBulb(5, strength, t);
  } else {
    stageFireBulb(3, strength, t);
    stageFireBulb(4, strength, t, true);
  }
}

function stageHat(t, power) {
  const idx = stageState.hatCount++ % BULB_COUNT;
  stageFireBulb(idx, 1, t);
}

// Часы сцены: каждый тик — восьмая доля такта 4/4 (сильная доля = бочка).
// Движок никогда не «замолкает»: даже если детектор что-то пропустил,
// лампочки продолжают бить в такт, а пойманные удары лишь поджигают свет ярче.
function stageClockTick(t, power) {
  const step = stageState.clockStep++;
  stageState.lastClockTick = t;
  const beatInBar = step % 8;
  // Классическая сетка 4/4: бочка на 1 и 3, снейр на 2 и 4, хэт на слабых долях
  if (beatInBar === 0 || beatInBar === 4) {
    stageState.syntheticKicks++;
    stageKick(t, Math.max(0.62, power));
  } else if (beatInBar === 2 || beatInBar === 6) {
    stageSnare(t, Math.max(0.58, power * 0.9));
  } else {
    stageHat(t, Math.max(0.5, power * 0.8));
  }
}

// Полный проход сценического движка за кадр
function updateStageEngine(dt, t, playing, useFft) {
  if (!playing) {
    stageState.kickCount = 0;
    stageState.hatCount = 0;
    stageState.clockStep = 0;
    stageState.nextBeat = 0;
    stageState.energy = 0;
    stageState.detectedKicks = 0;
    stageState.syntheticKicks = 0;
    stageState.beatInterval = 0.55;
    for (let i = 0; i < 4; i++) {
      stageState.prevLevel[i] = 0;
      stageState.fluxAvg[i] = 0;
      stageState.lastHit[i] = 0;
    }
    stageState.lastKick = 0;
    return;
  }

  // Всегда идёт тактовый ход сцены (восьмые доли).
  // Темп подстраивается под пойманную бочку, но не может «встать».
  const eighth = Math.max(0.185, Math.min(0.42, stageState.beatInterval / 2));
  if (!stageState.nextBeat) {
    stageState.nextBeat = t + eighth;
  }
  let guard = 0;
  while (t >= stageState.nextBeat && guard++ < 4) {
    stageClockTick(stageState.nextBeat, 0.7);
    stageState.nextBeat += eighth;
  }

  if (!useFft) return;

  const kickPower = stageFlux(0, stageBandLevel(STAGE_BANDS[0]), dt, t);
  const bassPower = stageFlux(1, stageBandLevel(STAGE_BANDS[1]), dt, t);
  const snarePower = stageFlux(2, stageBandLevel(STAGE_BANDS[2]), dt, t);
  const hatPower = stageFlux(3, stageBandLevel(STAGE_BANDS[3]), dt, t);

  stageState.energy =
    stageState.energy * 0.9 + ((audioEngine.beatData[0] || 0) / 255) * 0.1;

  if (kickPower) {
    // Живая бочка: уточняем темп и поджигаем свет поверх тактового хода
    if (
      stageState.lastKick &&
      t - stageState.lastKick > 0.22 &&
      t - stageState.lastKick < 1.4
    ) {
      const period = t - stageState.lastKick;
      stageState.beatInterval += (period - stageState.beatInterval) * 0.22;
      stageState.nextBeat = t + Math.max(0.185, Math.min(0.42, stageState.beatInterval / 2));
    }
    stageState.lastKick = t;
    stageState.detectedKicks++;
    // Не дублируем свет, если тактовый ход только что ударил по этому же удару
    const recentClock = t - (stageState.lastClockTick || 0) < 0.07;
    if (!recentClock) stageKick(t, kickPower);
  } else if (bassPower && bassPower > 0.3) {
    // Сильные басовые ноты без бочки тоже подсвечивают низ
    stageFireBulb(0, 0.7, t);
    stageFireBulb(1, 0.58, t);
  }

  if (snarePower) stageSnare(t, snarePower);
  if (hatPower) stageHat(t, hatPower);
}

function drawBulbsVisualizer(ctx, width, height, playing, t) {
  // Тёмный матовый корпус панели цветомузыки
  ctx.fillStyle = "#0b0e13";
  ctx.fillRect(0, 0, width, height);

  const dt = vizState.lastBulbTime
    ? Math.min(0.05, Math.max(0.004, t - vizState.lastBulbTime))
    : 0.016;
  vizState.lastBulbTime = t;

  // Короткая резкая вспышка как на фотоаппарате (~70–90 мс) + очень короткое послесвечение,
  // после которого лампа гаснет в полную темноту
  const flashDecay = Math.exp(-dt * 34);
  const glowDecay = Math.exp(-dt * 17);

  let useFft = false;
  if (playing && audioEngine?.beatAnalyser) {
    audioEngine.beatAnalyser.getByteFrequencyData(audioEngine.beatData);
    for (let k = 0; k < 60; k++) {
      if ((audioEngine.beatData[k] || 0) > 2) {
        useFft = true;
        break;
      }
    }
  }

  // Страховка: если браузер «усыпил» аудиоконтекст, возвращаем его к жизни,
  // чтобы звук и цветомузыка не пропадали после свёрнутой вкладки или блокировки экрана
  if (playing && audioEngine && audioEngine.ctx.state !== "running") {
    audioEngine.ctx.resume().catch(() => {});
  }

  // Сценический движок сам зажигает лампочки по ударам барабанов и паттернам
  updateStageEngine(dt, t, playing, useFft);

  const slotW = width / BULB_COUNT;
  const cy = height / 2;
  // Миниатюрные лампочки (в 4 раза меньше прежних) с ярким ореолом вспышки
  const r = Math.max(1.8, Math.min(slotW * 0.09, height * 0.085));

  for (let i = 0; i < BULB_COUNT; i++) {
    // Чуть выше порог обнуления — лампа гарантированно уходит в абсолютно тёмное состояние
    vizState.bulbFlash[i] *= flashDecay;
    vizState.bulbGlow[i] *= glowDecay;
    if (vizState.bulbFlash[i] < 0.06) vizState.bulbFlash[i] = 0;
    if (vizState.bulbGlow[i] < 0.05) vizState.bulbGlow[i] = 0;

    const flash = vizState.bulbFlash[i];
    const glow = vizState.bulbGlow[i];
    const [cr, cg, cb] = BULB_PALETTE[i];
    const cx = i * slotW + slotW / 2;

    // Кривая яркости: в покое лампа полностью потушена, при ударе — ослепительная вспышка.
    // flash^0.62 вытягивает середину вверх, поэтому вспышка «щёлкает» ярко, а не вязнет в полутонах.
    // Максимально «выкрученная» кривая: почти любой удар выходит на 85–100% яркости
    const punch = Math.pow(flash, 0.32);
    const afterglow = glow * 0.6;

    // 1. Мощный цветной ореол вспышки — аддитивное свечение, как настоящий прожектор
    if (punch > 0.01 || afterglow > 0.01) {
      const haloR = r * (1.7 + punch * 4.2 + afterglow * 1.1);
      const haloGrad = ctx.createRadialGradient(cx, cy, r * 0.12, cx, cy, haloR);
      haloGrad.addColorStop(0, `rgba(255, 255, 255, ${Math.min(1, 0.35 + punch * 0.9)})`);
      haloGrad.addColorStop(0.22, `rgba(255, 255, 255, ${Math.min(1, punch * 0.85)})`);
      haloGrad.addColorStop(0.42, `rgba(${cr}, ${cg}, ${cb}, ${Math.min(1, punch * 0.95 + afterglow * 0.45)})`);
      haloGrad.addColorStop(0.72, `rgba(${cr}, ${cg}, ${cb}, ${Math.min(0.7, punch * 0.55 + afterglow * 0.25)})`);
      haloGrad.addColorStop(1, `rgba(${cr}, ${cg}, ${cb}, 0)`);
      ctx.save();
      ctx.globalCompositeOperation = "lighter";
      ctx.fillStyle = haloGrad;
      ctx.beginPath();
      ctx.arc(cx, cy, haloR, 0, Math.PI * 2);
      ctx.fill();
      ctx.restore();
    }

    // 2. Тонкий тёмный ободок цоколя (неподвижное гнездо лампочки, виден всегда)
    ctx.beginPath();
    ctx.arc(cx, cy, r + 0.7, 0, Math.PI * 2);
    ctx.fillStyle = "#12161d";
    ctx.fill();
    ctx.lineWidth = 0.6;
    ctx.strokeStyle = punch > 0.12
      ? `rgba(${cr}, ${cg}, ${cb}, ${Math.min(1, 0.5 + punch * 0.5)})`
      : "rgba(255, 255, 255, 0.10)";
    ctx.stroke();

    // 3. Стеклянная линза: в покое — почти чёрное стекло, при вспышке — раскалённая до белого
    ctx.save();
    if (punch > 0.02 || afterglow > 0.02) {
      // Размытие теней — самая дорогая операция 2D-канваса: на телефонах не используем вовсе
      if (vizQuality >= 2) {
        ctx.shadowColor = punch > 0.3
          ? `rgba(255, 255, 255, ${Math.min(1, 0.7 + punch * 0.3)})`
          : `rgba(${cr}, ${cg}, ${cb}, ${Math.min(1, 0.5 + afterglow * 0.5)})`;
        ctx.shadowBlur = 3 + punch * 26 + afterglow * 5;
      }
      // Вспышка светится аддитивно — свет складывается и выглядит по-настоящему ярко
      ctx.globalCompositeOperation = "lighter";
    }

    const bodyGrad = ctx.createRadialGradient(
      cx - r * 0.24,
      cy - r * 0.24,
      r * 0.06,
      cx,
      cy,
      r
    );
    // В покое — приглушённое ЦВЕТНОЕ стекло, при ударе — чистое белое каление на полной яркости
    const coreMix = Math.min(1, Math.pow(punch, 0.55));
    const rr = Math.round(cr * 0.34 + (255 - cr * 0.34) * coreMix);
    const rg = Math.round(cg * 0.34 + (255 - cg * 0.34) * coreMix);
    const rb = Math.round(cb * 0.34 + (255 - cb * 0.34) * coreMix);
    // В покое лампа погашена, при вспышке сразу выходит на 100%
    const centerAlpha = Math.min(1, 0.09 + punch * 1.6 + afterglow * 0.35);
    const midAlpha = Math.min(1, 0.055 + punch * 1.5 + afterglow * 0.4);
    const rimAlpha = Math.min(1, 0.035 + punch * 1.1 + afterglow * 0.25);

    bodyGrad.addColorStop(0, `rgba(${rr}, ${rg}, ${rb}, ${centerAlpha})`);
    bodyGrad.addColorStop(0.55, `rgba(${cr}, ${cg}, ${cb}, ${midAlpha})`);
    bodyGrad.addColorStop(1, `rgba(${Math.round(cr * 0.35)}, ${Math.round(cg * 0.35)}, ${Math.round(cb * 0.35)}, ${rimAlpha})`);

    ctx.fillStyle = bodyGrad;
    ctx.beginPath();
    ctx.arc(cx, cy, r, 0, Math.PI * 2);
    ctx.fill();

    // Белое раскалённое ядро по центру — «пересвет» как у настоящей фотовспышки
    if (punch > 0.08) {
      const coreR = r * (0.32 + punch * 0.4);
      const coreGrad = ctx.createRadialGradient(cx, cy, 0, cx, cy, coreR);
      coreGrad.addColorStop(0, `rgba(255, 255, 255, ${Math.min(1, punch * 1.2)})`);
      coreGrad.addColorStop(0.55, `rgba(255, 255, 255, ${Math.min(0.9, punch * 0.8)})`);
      coreGrad.addColorStop(1, "rgba(255, 255, 255, 0)");
      ctx.fillStyle = coreGrad;
      ctx.beginPath();
      ctx.arc(cx, cy, coreR, 0, Math.PI * 2);
      ctx.fill();
    }
    ctx.restore();

    // 4. Стеклянный блик сверху-слева (проявляется только на вспышке)
    if (punch > 0.05) {
      ctx.save();
      ctx.globalCompositeOperation = "lighter";
      ctx.fillStyle = `rgba(255, 255, 255, ${Math.min(1, 0.2 + punch * 0.8)})`;
      ctx.beginPath();
      ctx.arc(cx - r * 0.32, cy - r * 0.32, Math.max(0.55, r * 0.26), 0, Math.PI * 2);
      ctx.fill();
      ctx.restore();
    }

    // 5. Короткий резкий 4-лучевой блик фотовспышки (тоже аддитивно — лучи «прожигают» кадр)
    if (punch > 0.15 && vizQuality === 0) {
      // Экономный вариант: простой крест без градиентов
      ctx.save();
      ctx.globalCompositeOperation = "lighter";
      ctx.fillStyle = `rgba(255, 255, 255, ${Math.min(1, punch * 0.9)})`;
      const rayH0 = r * (1.6 + punch * 3.2);
      const rayV0 = r * (1.3 + punch * 2.8);
      ctx.fillRect(cx - rayH0, cy - 0.5, rayH0 * 2, 1);
      ctx.fillRect(cx - 0.5, cy - rayV0, 1, rayV0 * 2);
      ctx.restore();
    } else if (punch > 0.15) {
      const rayH = r * (1.8 + punch * 4.2);
      const rayV = r * (1.5 + punch * 3.6);
      ctx.save();
      ctx.globalCompositeOperation = "lighter";
      const hGrad = ctx.createLinearGradient(cx - rayH, cy, cx + rayH, cy);
      hGrad.addColorStop(0, "rgba(255, 255, 255, 0)");
      hGrad.addColorStop(0.5, `rgba(255, 255, 255, ${Math.min(1, punch * 1.35)})`);
      hGrad.addColorStop(1, "rgba(255, 255, 255, 0)");
      ctx.fillStyle = hGrad;
      ctx.fillRect(cx - rayH, cy - 0.75, rayH * 2, 1.5);

      const vGrad = ctx.createLinearGradient(cx, cy - rayV, cx, cy + rayV);
      vGrad.addColorStop(0, "rgba(255, 255, 255, 0)");
      vGrad.addColorStop(0.5, `rgba(255, 255, 255, ${Math.min(1, punch * 1.25)})`);
      vGrad.addColorStop(1, "rgba(255, 255, 255, 0)");
      ctx.fillStyle = vGrad;
      ctx.fillRect(cx - 0.75, cy - rayV, 1.5, rayV * 2);
      ctx.restore();
    }
  }
}

function fillPillRect(ctx, x, y, w, h, r) {
  const rad = Math.min(r, w / 2, h / 2);
  ctx.beginPath();
  if (typeof ctx.roundRect === "function") {
    ctx.roundRect(x, y, w, h, rad);
  } else {
    ctx.moveTo(x + rad, y);
    ctx.lineTo(x + w - rad, y);
    ctx.quadraticCurveTo(x + w, y, x + w, y + rad);
    ctx.lineTo(x + w, y + h - rad);
    ctx.quadraticCurveTo(x + w, y + h, x + w - rad, y + h);
    ctx.lineTo(x + rad, y + h);
    ctx.quadraticCurveTo(x, y + h, x, y + h - rad);
    ctx.lineTo(x, y + rad);
    ctx.quadraticCurveTo(x, y, x + rad, y);
  }
  ctx.fill();
}

function drawFaderVisualizer(ctx, width, height, playing, t) {
  // Глубокий тёмно-графитовый фон, как на референсе
  ctx.fillStyle = "#0d1114";
  ctx.fillRect(0, 0, width, height);

  const dt = vizState.lastFaderTime
    ? Math.min(0.05, Math.max(0.004, t - vizState.lastFaderTime))
    : 0.016;
  vizState.lastFaderTime = t;

  if (!playing) {
    for (let i = 0; i < FADER_BANDS; i++) {
      vizState.faderPeak[i] = 0.3;
      vizState.faderHighSince[i] = 0;
      vizState.faderCeilHold[i] = 0;
    }
  }
  // Мгновенное затухание фотовспышки (~80–100 мс, не зависит от герцовки экрана)
  const flashDecay = Math.exp(-dt * 30);

  const bands = FADER_BANDS;
  const slotW = width / bands;
  const trackW = Math.max(3, Math.min(4.2, slotW * 0.22));
  const knobW = Math.max(8, Math.min(12, slotW * 0.62));
  const knobH = Math.max(4, Math.min(5.2, height * 0.145));
  const padTop = 3;
  const padBottom = 2;
  const trackH = Math.max(10, height - padTop - padBottom);

  let useFft = false;
  if (playing && audioEngine?.analyser) {
    audioEngine.analyser.getByteFrequencyData(audioEngine.dataArray);
    for (let k = 1; k < 48; k++) {
      if (audioEngine.dataArray[k] > 2) {
        useFft = true;
        break;
      }
    }
  }

  // Тонкие вертикальные разделители между 10 каналами
  ctx.fillStyle = "rgba(255, 255, 255, 0.05)";
  for (let i = 1; i < bands; i++) {
    ctx.fillRect(Math.round(i * slotW), 0, 1, height);
  }

  for (let i = 0; i < bands; i++) {
    let target = 0.06;
    if (playing) {
      if (useFft) {
        const [start, end] = FADER_LOG_RANGES[i];
        let peakBin = 0;
        let sumBin = 0;
        let count = 0;
        for (let b = start; b < end; b++) {
          const val = audioEngine.dataArray[b] || 0;
          if (val > peakBin) peakBin = val;
          sumBin += val;
          count++;
        }
        const avg = count ? sumBin / count : 0;
        const raw = (peakBin * 0.62 + avg * 0.38) / 255;
        const tilt = 0.94 + (i / bands) * 0.38;
        const boosted = Math.min(1, raw * tilt);

        // Опорный уровень («средняя громкость» полосы) с МЕДЛЕННЫМ догоном: 1.6 с.
        // Так он отслеживает общую громкость трека, но не подстраивается под каждый удар —
        // поэтому динамика не стирается даже на очень энергичной музыке.
        const peakRef = vizState.faderPeak[i];
        const follow = Math.min(1, dt * 0.62);
        vizState.faderPeak[i] = Math.max(0.08, peakRef + (boosted - peakRef) * follow);

        // ВАЖНО: не делим на опорный уровень (это и было причиной «ползунки залипли вверху»).
        // Считаем ОТКЛОНЕНИЕ от среднего — оно сохраняет движение на любой громкости.
        const ref = Math.max(0.08, vizState.faderPeak[i]);
        const dev = (boosted - ref) / ref;

        // Низкая чувствительность: качание вокруг 52% с мягким ограничением краёв
        target = Math.min(0.9, Math.max(0.05, 0.52 + dev * 0.9));
      } else {
        const kick = Math.pow(0.5 + 0.5 * Math.sin(t * 7.6), 1.7) * Math.max(0, 1 - i / 3.8);
        const mid = Math.pow(0.5 + 0.5 * Math.sin(t * 3.9 + i * 0.72), 1.4) * 0.85;
        const wave = (0.5 + 0.5 * Math.sin(t * 2.6 - i * 0.92) * Math.cos(t * 1.8 + i * 0.44)) * 0.8;
        const high = (0.5 + 0.5 * Math.sin(t * 9.8 + i * 1.85)) * 0.55 * (i / bands);
        target = Math.min(0.9, Math.max(0.05, 0.24 + (kick * 0.85 + mid * 0.7 + wave * 0.62 + high) * 0.62));
      }
    }

    // Успокоение: если полоса держится у потолка дольше 1.2 с, плавно опускаем её
    // рабочий потолок — ползунок не может «застрять» наверху даже на самом энергичном треке
    const ceil = vizState.faderCeilHold[i];
    if (target > 0.72) {
      vizState.faderCeilHold[i] = Math.min(0.26, ceil + dt * 0.2);
    } else {
      vizState.faderCeilHold[i] = Math.max(0, ceil - dt * 0.4);
    }
    target = Math.max(0.05, target - vizState.faderCeilHold[i]);

    // Живая физика моторизованного фейдера: подъём чуть мягче, спуск заметно быстрее,
    // поэтому после каждого удара ползунок реально опускается, а не липнет наверху
    const prev = vizState.faderLevels[i];
    const next = target > prev
      ? prev + (target - prev) * 0.6
      : prev + (target - prev) * 0.42;
    vizState.faderLevels[i] = next;

    const level = Math.max(0, Math.min(1, next));

    // Короткая резкая вспышка как на фотоаппарате: срабатывает однократно при ударе о верхний пик
    vizState.faderFlash[i] *= flashDecay;
    if (vizState.faderFlash[i] < 0.02) vizState.faderFlash[i] = 0;

    // Вспышка ловит РЕЗКИЙ РЫВОК вверх (удар), а не факт «стоять у потолка».
    // Плюс страховка: если ползунок держится наверху дольше 0,4 с, готовность
    // восстанавливается сама — вспышки не могут заклинить на громком треке.
    const prevLevel = vizState.faderPrevLevel[i];
    const jump = level - prevLevel;
    vizState.faderPrevLevel[i] = level;

    if (!playing || level < 0.42) {
      vizState.faderArmed[i] = 1;
      vizState.faderHighSince[i] = 0;
    } else if (level >= 0.55) {
      if (vizState.faderHighSince[i] === 0) vizState.faderHighSince[i] = t;
      if (t - vizState.faderHighSince[i] > 0.4) vizState.faderArmed[i] = 1;
    } else {
      vizState.faderHighSince[i] = 0;
    }

    if (
      playing &&
      ((jump > 0.085 && level > 0.44) || (level >= 0.85 && vizState.faderArmed[i])) &&
      t - vizState.faderLastFlash[i] > 0.16
    ) {
      vizState.faderFlash[i] = 1.0;
      vizState.faderLastFlash[i] = t;
      vizState.faderArmed[i] = 0;
      vizState.faderHighSince[i] = t;
    }
    const flash = vizState.faderFlash[i];

    const cx = i * slotW + slotW / 2;
    const trackX = cx - trackW / 2;

    // 1. Тёмно-серая вертикальная направляющая (прорезь)
    ctx.fillStyle = "#363c42";
    fillPillRect(ctx, trackX, padTop, trackW, trackH, trackW / 2);

    // 2. Положение зелёной капсулы и высота белой полосы
    const usableTravel = Math.max(4, trackH - knobH);
    const knobY = padTop + usableTravel * (1 - level);
    const whiteTop = knobY + knobH * 0.5;
    const whiteH = Math.max(trackW, padTop + trackH - whiteTop);

    // 3. Ярко-белый скруглённый столбик снизу до ползунка
    ctx.fillStyle = "#ffffff";
    fillPillRect(ctx, trackX, whiteTop, trackW, whiteH, trackW / 2);

    // 4. Плавное свечение при подъёме + короткий ослепительный ореол фотовспышки
    const knobX = cx - knobW / 2;
    const knobCenterY = knobY + knobH / 2;
    if (level > 0.48 && flash < 0.1) {
      const climbGlow = Math.min(0.45, (level - 0.48) * 0.85);
      const climbR = knobW * 0.9;
      const climbGrad = ctx.createRadialGradient(cx, knobCenterY, 0.5, cx, knobCenterY, climbR);
      climbGrad.addColorStop(0, `rgba(110, 255, 130, ${climbGlow})`);
      climbGrad.addColorStop(1, "rgba(71, 248, 104, 0)");
      ctx.fillStyle = climbGrad;
      ctx.beginPath();
      ctx.arc(cx, knobCenterY, climbR, 0, Math.PI * 2);
      ctx.fill();
    }

    if (flash > 0.03) {
      const flashR = knobW * (1.15 + flash * 1.1);
      const flashGrad = ctx.createRadialGradient(cx, knobCenterY, 0.5, cx, knobCenterY, flashR);
      flashGrad.addColorStop(0, `rgba(255, 255, 255, ${Math.min(1, flash * 1.05)})`);
      flashGrad.addColorStop(0.32, `rgba(215, 255, 222, ${flash * 0.85})`);
      flashGrad.addColorStop(0.65, `rgba(80, 255, 115, ${flash * 0.42})`);
      flashGrad.addColorStop(1, "rgba(80, 255, 115, 0)");
      ctx.fillStyle = flashGrad;
      ctx.beginPath();
      ctx.arc(cx, knobCenterY, flashR, 0, Math.PI * 2);
      ctx.fill();
    }

    // 5. Зелёная овальная капсула-ползунок: чем выше, тем ярче; на вспышке — белое ослепление
    const hue = Math.round(136 - level * 14);
    const sat = Math.round(56 + level * 44);
    const light = Math.min(99, Math.round(31 + level * 29 + flash * 45));

    ctx.save();
    if (flash > 0.05) {
      ctx.shadowColor = `rgba(255, 255, 255, ${Math.min(1, 0.7 + flash * 0.3)})`;
      ctx.shadowBlur = 8 + flash * 18;
    } else if (level > 0.35) {
      ctx.shadowColor = `rgba(71, 245, 98, ${0.28 + level * 0.52})`;
      ctx.shadowBlur = 2 + level * 7;
    }
    ctx.fillStyle = flash > 0.55 ? "#ffffff" : `hsl(${hue}, ${sat}%, ${light}%)`;
    fillPillRect(ctx, knobX, knobY, knobW, knobH, knobH / 2);

    // Верхний блик на капсуле
    ctx.shadowBlur = 0;
    ctx.fillStyle = `rgba(255, 255, 255, ${Math.min(1, 0.16 + level * 0.24 + flash * 0.6)})`;
    fillPillRect(ctx, knobX + 1.2, knobY + 0.7, Math.max(2, knobW - 2.4), Math.max(1, knobH * 0.34), knobH / 2);

    // Резкий крестообразный блик фотовспышки (длится доли секунды)
    if (flash > 0.14) {
      const rayH = knobW * (1.05 + flash * 0.85);
      const rayV = knobH * (1.2 + flash * 1.6);
      const hGrad = ctx.createLinearGradient(cx - rayH, knobCenterY, cx + rayH, knobCenterY);
      hGrad.addColorStop(0, "rgba(255, 255, 255, 0)");
      hGrad.addColorStop(0.5, `rgba(255, 255, 255, ${Math.min(1, flash * 1.1)})`);
      hGrad.addColorStop(1, "rgba(255, 255, 255, 0)");
      ctx.fillStyle = hGrad;
      ctx.fillRect(cx - rayH, knobCenterY - 0.75, rayH * 2, 1.5);

      const vGrad = ctx.createLinearGradient(cx, knobCenterY - rayV, cx, knobCenterY + rayV);
      vGrad.addColorStop(0, "rgba(255, 255, 255, 0)");
      vGrad.addColorStop(0.5, `rgba(255, 255, 255, ${Math.min(1, flash * 1.0)})`);
      vGrad.addColorStop(1, "rgba(255, 255, 255, 0)");
      ctx.fillStyle = vGrad;
      ctx.fillRect(cx - 0.75, knobCenterY - rayV, 1.5, rayV * 2);
    }
    ctx.restore();
  }
}

function initVisualizer() {
  if (vizRunning) return;
  vizRunning = true;
  drawVisualizer();
}

function drawWinampGrid(ctx, width, height) {
  // Классический чёрный экранчик Winamp с фирменной пиксельной сеткой
  ctx.fillStyle = "#000000";
  ctx.fillRect(0, 0, width, height);

  ctx.fillStyle = "#181a28";
  for (let y = 2; y < height; y += 4) {
    for (let x = 2; x < width; x += 4) {
      ctx.fillRect(x, y, 1, 1);
    }
  }
}

function getWinampBarColor(rowRatio, mode) {
  if (mode === "neon") {
    if (rowRatio >= 0.82) return "#fb7185";
    if (rowRatio >= 0.56) return "#a855f7";
    return "#22d3ee";
  }
  const idx = Math.max(
    0,
    Math.min(WINAMP_SPECTRUM_COLORS.length - 1, Math.floor(rowRatio * WINAMP_SPECTRUM_COLORS.length))
  );
  return WINAMP_SPECTRUM_COLORS[idx];
}

function drawWinampOscilloscope(ctx, width, height, playing, t) {
  let hasRealWave = false;
  let waveData = null;

  if (playing && audioEngine?.analyser && audioEngine.timeDataArray) {
    audioEngine.analyser.getByteTimeDomainData(audioEngine.timeDataArray);
    waveData = audioEngine.timeDataArray;
    for (let i = 0; i < waveData.length; i++) {
      if (Math.abs(waveData[i] - 128) > 2) {
        hasRealWave = true;
        break;
      }
    }
  }

  const midY = Math.floor(height / 2);
  const steps = Math.max(36, Math.floor(width / 2));

  // Центральная тонкая линия покоя
  if (!playing) {
    ctx.fillStyle = "#22a81c";
    ctx.fillRect(0, midY, width, 1);
    return;
  }

  let prevY = midY;
  for (let i = 0; i < steps; i++) {
    let sample = 0;
    if (hasRealWave && waveData) {
      const idx = Math.floor((i / steps) * waveData.length);
      sample = (waveData[idx] - 128) / 128;
      sample = Math.max(-1, Math.min(1, sample * 1.45));
    } else {
      const p = i / steps;
      const env = Math.sin(p * Math.PI);
      sample =
        (Math.sin(t * 14 + p * 18) * 0.45 +
          Math.sin(t * 27 - p * 31) * 0.3 +
          Math.cos(t * 9 + p * 8) * 0.25) *
        env;
    }

    const x = Math.round((i / (steps - 1)) * (width - 2));
    const y = Math.round(midY + sample * (height * 0.44));
    const amp = Math.min(1, Math.abs(sample) * 1.25);
    const colorIdx = Math.min(
      WINAMP_OSC_COLORS.length - 1,
      Math.floor(amp * WINAMP_OSC_COLORS.length)
    );
    ctx.fillStyle = WINAMP_OSC_COLORS[colorIdx];

    // Классический пиксельный штрих Winamp без размытия
    const topY = Math.min(prevY, y);
    const spanH = Math.max(2, Math.abs(y - prevY) + 1);
    ctx.fillRect(x, topY, 2, spanH);
    prevY = y;
  }
}

function drawVisualizer() {
  requestAnimationFrame(drawVisualizer);
  if (document.hidden || !visualizerCanvas) return;

  const rect = visualizerCanvas.getBoundingClientRect();
  if (rect.width < 20 || rect.height < 10) return;

  // DPR ограничен по уровню качества: на телефоне рисуем в 1.5x, а не в 3x
  const dprCap = vizQuality >= 2 ? 2 : vizQuality === 1 ? 1.5 : 1;
  const dpr = Math.min(window.devicePixelRatio || 1, dprCap);
  const targetW = Math.round(rect.width * dpr);
  const targetH = Math.round(rect.height * dpr);
  if (visualizerCanvas.width !== targetW || visualizerCanvas.height !== targetH) {
    visualizerCanvas.width = targetW;
    visualizerCanvas.height = targetH;
  }

  const ctx = visualizerCanvas.getContext("2d");
  if (!ctx) return;

  const width = rect.width;
  const height = rect.height;
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);

  const playing = state.isPlaying && !audio.paused;
  const t = performance.now() / 1000;

  // Авто-мониторинг FPS и ограничение частоты кадров на слабых устройствах
  if (vizState.lastFrameTime) {
    const frameDt = Math.min(0.2, t - vizState.lastFrameTime);
    trackPerformance(frameDt);
    if (vizQuality <= 1) {
      const minGap = vizQuality === 0 ? 1 / 30 : 1 / 45;
      if (frameDt < minGap) return;
    }
  }
  vizState.lastFrameTime = t;

  // Режим 1 (по умолчанию): Цветомузыка — 8 неподвижных разноцветных лампочек с короткими фотовспышками
  if (vizState.mode === "bulbs") {
    drawBulbsVisualizer(ctx, width, height, playing, t);
    return;
  }

  // Режим 2: Ползунки — белые столбики с ярко-зелёными овальными капсулами
  if (vizState.mode === "faders") {
    drawFaderVisualizer(ctx, width, height, playing, t);
    return;
  }

  drawWinampGrid(ctx, width, height);

  // Режим 3: Классический осциллограф Winamp
  if (vizState.mode === "osc") {
    drawWinampOscilloscope(ctx, width, height, playing, t);
    return;
  }

  // Режим 1 и 3: Классический спектр Winamp (тонкие чёткие столбики + падающие серые пики)
  const bands = SPECTRUM_BANDS;
  const padX = 2;
  const usableW = Math.max(20, width - padX * 2);
  const slotWidth = usableW / bands;
  const barWidth = Math.max(2, Math.min(3.5, Math.floor(slotWidth * 0.48)));
  const rows = Math.max(12, Math.floor(height / 2.2));
  const rowStep = height / rows;

  let useFft = false;
  if (playing && audioEngine?.analyser) {
    audioEngine.analyser.getByteFrequencyData(audioEngine.dataArray);
    for (let k = 1; k < 48; k++) {
      if (audioEngine.dataArray[k] > 2) {
        useFft = true;
        break;
      }
    }
  }

  for (let i = 0; i < bands; i++) {
    let target = 0;
    if (playing) {
      if (useFft) {
        const [start, end] = LOG_BAND_RANGES[i];
        let peakBin = 0;
        let sumBin = 0;
        let count = 0;
        for (let b = start; b < end; b++) {
          const val = audioEngine.dataArray[b] || 0;
          if (val > peakBin) peakBin = val;
          sumBin += val;
          count++;
        }
        const avg = count ? sumBin / count : 0;
        const raw = (peakBin * 0.62 + avg * 0.38) / 255;
        const tilt = 0.94 + (i / bands) * 0.38;
        target = Math.min(1, Math.pow(raw * tilt, 1.05));
      } else {
        const kick = Math.pow(0.5 + 0.5 * Math.sin(t * 7.8), 3.0) * Math.max(0, 1 - i / 5);
        const snare = Math.pow(0.5 + 0.5 * Math.sin(t * 3.9 + 1.5), 4) * Math.exp(-Math.pow((i - 7) / 3.4, 2));
        const melody = (0.45 + 0.45 * Math.sin(t * 2.7 + i * 0.55) * Math.cos(t * 1.4 - i * 0.3)) * 0.66;
        const sparkle = (0.5 + 0.5 * Math.sin(t * 11.5 + i * 1.9)) * 0.34 * (i / bands);
        target = Math.min(0.98, Math.max(0.08, kick * 0.85 + snare * 0.66 + melody * 0.52 + sparkle));
      }
    }

    // Фирменная живая динамика Winamp: мгновенный рывок вверх, характерный линейный спад вниз
    const prev = vizState.levels[i];
    const next = target > prev
      ? target
      : Math.max(0, prev - 0.042);
    vizState.levels[i] = next < 0.01 ? 0 : next;

    // Фирменная физика падающей серой точки Peak Hold из Winamp
    if (vizState.levels[i] >= vizState.peaks[i]) {
      vizState.peaks[i] = vizState.levels[i];
      vizState.peakHold[i] = 14;
      vizState.peakVel[i] = 0;
    } else if (vizState.peakHold[i] > 0) {
      vizState.peakHold[i] -= 1;
    } else {
      vizState.peakVel[i] += 0.0018;
      vizState.peaks[i] = Math.max(0, vizState.peaks[i] - vizState.peakVel[i]);
    }

    const x = Math.round(padX + i * slotWidth + (slotWidth - barWidth) / 2);
    const activeRows = Math.round(vizState.levels[i] * rows);

    // Отрисовка столбика по строкам классической палитрой Winamp (1px зазор между пиксельными полосками)
    for (let r = 0; r < activeRows; r++) {
      const y = Math.round(height - (r + 1) * rowStep);
      const segH = Math.max(1, Math.round(rowStep - 0.7));
      const ratio = r / Math.max(1, rows - 1);
      ctx.fillStyle = getWinampBarColor(ratio, vizState.mode);
      ctx.fillRect(x, y, barWidth, segH);
    }

    // Фирменная светло-серая падающая риска Winamp над каждым столбиком
    if (vizState.peaks[i] > 0.03) {
      const peakRow = Math.min(rows - 1, Math.floor(vizState.peaks[i] * rows));
      const py = Math.round(height - (peakRow + 1) * rowStep);
      ctx.fillStyle = vizState.mode === "neon" ? "#f8fafc" : "#b8bec8";
      ctx.fillRect(x, py, barWidth, Math.max(1.5, Math.round(rowStep * 0.8)));
    }
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
    .replace(/\[[^\]]*\]/g, "")
    .replace(/[_]+/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}

function isTrackInAnyPlaylist(trackId) {
  return state.playlists.some((pl) => pl.trackIds.includes(trackId));
}

function parseTrackFilename(filename) {
  const cleanedStem = cleanFileTitle(filename) || filename.replace(/\.[^/.]+$/, "");
  if (cleanedStem.includes(" - ")) {
    const [artist, ...rest] = cleanedStem.split(" - ");
    return {
      artist: artist.trim() || "Моя коллекция",
      title: rest.join(" - ").trim() || cleanedStem,
    };
  }
  return {
    artist: "Моя коллекция",
    title: cleanedStem ? cleanedStem.charAt(0).toUpperCase() + cleanedStem.slice(1) : filename,
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
  // Панель владельца доступна только владельцу (server.py или ?admin=1)
  ownerStatsBtn?.classList.toggle("hidden", !showOwner);
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

  if (!getFirebaseBase()) return;

  try {
    const data = await fetchFirebaseSocial();
    if (!data) return;
    applyFirebaseSocial(data, true);
  } catch {
    // Тихий fallback на localStorage
  }
}

function getFirebaseBase() {
  return (FIREBASE_DB_URL || "").replace(/\/+$/, "");
}

// Читаем общие лайки и комментарии из Firebase
async function fetchFirebaseSocial() {
  const fbBase = getFirebaseBase();
  if (!fbBase) return null;
  const res = await fetch(`${fbBase}/social.json?t=${Date.now()}`, { cache: "no-store" });
  if (!res.ok) return null;
  const data = await res.json();
  return data && typeof data === "object" ? data : {};
}

// Счётчик лайков: теперь это СПИСОК тех, кто лайкнул (лайки не теряются при совпадении)
function countLikeList(raw) {
  if (raw == null) return 0;
  if (typeof raw === "number") return Math.max(0, Math.round(raw));
  if (Array.isArray(raw)) return raw.filter(Boolean).length;
  if (typeof raw === "object") return Object.keys(raw).length;
  return 0;
}

function hasOwnLike(raw) {
  if (!raw) return false;
  if (Array.isArray(raw)) return raw.includes(CLIENT_ID);
  if (typeof raw === "object") return Object.prototype.hasOwnProperty.call(raw, CLIENT_ID);
  return false;
}

// Применяем данные из Firebase к локальному состоянию и перерисовываем интерфейс
function applyFirebaseSocial(data, rerender) {
  const likes = {};
  const comments = {};
  let myLikesChanged = false;

  for (const track of state.tracks) {
    const key = encodeFirebaseKey(track.id);

    const rawLikes = data.likes ? data.likes[key] : null;
    likes[track.id] = countLikeList(rawLikes);
    const mine = hasOwnLike(rawLikes);
    if (mine && !state.favorites.has(track.id)) {
      state.favorites.add(track.id);
      myLikesChanged = true;
    } else if (!mine && rawLikes != null && state.favorites.has(track.id)) {
      state.favorites.delete(track.id);
      myLikesChanged = true;
    }

    if (data.comments && data.comments[key]) {
      const rawObj = data.comments[key];
      const list = Array.isArray(rawObj) ? rawObj.filter(Boolean) : Object.values(rawObj);
      comments[track.id] = list
        .filter((c) => c && typeof c === "object")
        .sort((a, b) => (b.createdAt || 0) - (a.createdAt || 0));
    }
  }

  state.likeCounts = likes;
  state.commentsMap = comments;
  saveJSON(LS_LIKES_MAP, state.likeCounts);
  saveJSON(LS_COMMENTS_MAP, state.commentsMap);
  if (myLikesChanged) persistFavorites();

  if (rerender) {
    renderAll();
    if (state.activeCommentsTrackId) renderCommentsModal();
  }
}

// Тихая синхронизация каждые 20 секунд: новые лайки и комментарии друзей
// появляются без перезагрузки страницы
let socialSyncTimer = null;

function startSocialSync() {
  if (!getFirebaseBase() || state.serverMode) return;
  if (socialSyncTimer) return;

  const tick = async () => {
    if (document.hidden) return;
    try {
      const data = await fetchFirebaseSocial();
      if (data) applyFirebaseSocial(data, true);
      // Если панель владельца открыта — обновляем и её
      if (typeof ownerPanelOpen !== "undefined" && ownerPanelOpen) renderOwnerPanel();
    } catch {
      // сеть недоступна — просто ждём следующего раза
    }
  };

  socialSyncTimer = setInterval(tick, 20000);
  document.addEventListener("visibilitychange", () => {
    if (!document.hidden) tick();
  });
}


// ============================================================================
// Панель владельца: статистика лайков и комментариев по каждому треку
// Открывается только по ссылке с ?admin=1 (или на локальном server.py)
// ============================================================================

let ownerPanelOpen = false;
let ownerActiveTab = "likes";
let ownerSocialCache = null;

function formatOwnerDate(ts) {
  if (!ts) return "";
  try {
    return new Date(ts).toLocaleString("ru-RU", {
      day: "2-digit",
      month: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return "";
  }
}

function renderOwnerStats() {
  const tracks = state.tracks;
  let totalLikes = 0;
  let totalComments = 0;
  let likedTracks = 0;

  for (const track of tracks) {
    const likes = getLikeCount(track.id);
    const comments = getTrackComments(track.id).length;
    totalLikes += likes;
    totalComments += comments;
    if (likes > 0) likedTracks += 1;
  }

  if (ownerTracksCount) ownerTracksCount.textContent = String(tracks.length);
  if (ownerLikesCount) ownerLikesCount.textContent = String(totalLikes);
  if (ownerCommentsCount) ownerCommentsCount.textContent = String(totalComments);
  if (ownerLikedTracksCount) ownerLikedTracksCount.textContent = String(likedTracks);
}

function ownerTrackRow(track) {
  const cover = track.cover
    ? `<img src="${escapeHtml(track.cover)}" alt="" loading="lazy" />`
    : "♪";
  const genre = GENRES[track.genre]?.label || "Разное";
  return `
    <div class="owner-row-cover">${cover}</div>
    <div class="owner-row-body">
      <div class="owner-row-title">${escapeHtml(track.title)}</div>
      <div class="owner-row-sub">${escapeHtml(track.artist || "Неизвестный исполнитель")} · ${escapeHtml(genre)}</div>
    </div>
  `;
}

function renderOwnerPanel() {
  renderOwnerStats();
  if (!ownerList) return;

  const tracks = state.tracks;

  if (!tracks.length) {
    ownerList.innerHTML = `<div class="owner-empty">Треки пока не загружены.</div>`;
    return;
  }

  if (ownerActiveTab === "likes") {
    const rows = tracks
      .map((track) => ({ track, likes: getLikeCount(track.id) }))
      .sort((a, b) => b.likes - a.likes || a.track.title.localeCompare(b.track.title, "ru"));

    const active = rows.filter((r) => r.likes > 0);

    if (!active.length) {
      ownerList.innerHTML = `<div class="owner-empty">Лайков пока нет. Как только друг нажмёт ♥, трек появится здесь.</div>`;
      return;
    }

    ownerList.innerHTML = active
      .map(
        ({ track, likes }) => `
        <div class="owner-row">
          ${ownerTrackRow(track)}
          <div class="owner-row-badges">
            <span class="owner-badge is-likes">♥ ${likes}</span>
          </div>
        </div>`
      )
      .join("");
    return;
  }

  // Вкладка «Комментарии»: последние комментарии по всем трекам
  const feed = [];
  for (const track of tracks) {
    for (const comment of getTrackComments(track.id)) {
      feed.push({ track, comment });
    }
  }
  feed.sort((a, b) => (b.comment.createdAt || 0) - (a.comment.createdAt || 0));

  if (!feed.length) {
    ownerList.innerHTML = `<div class="owner-empty">Комментариев пока нет.</div>`;
    return;
  }

  ownerList.innerHTML = feed
    .slice(0, 100)
    .map(
      ({ track, comment }) => `
      <div class="owner-row">
        ${ownerTrackRow(track)}
        <div class="owner-row-body">
          <div class="owner-row-title">${escapeHtml(comment.author || "Гость")}</div>
          <div class="owner-row-sub">${escapeHtml(track.title)} · ${escapeHtml(formatOwnerDate(comment.createdAt))}</div>
          <div class="owner-comment-text">${escapeHtml(comment.text || "")}</div>
        </div>
      </div>`
    )
    .join("");
}

function setOwnerSyncStatus(text, kind = "") {
  if (!ownerSyncStatus) return;
  ownerSyncStatus.textContent = text;
  ownerSyncStatus.classList.toggle("is-warn", kind === "warn");
  ownerSyncStatus.classList.toggle("is-ok", kind === "ok");
}

async function refreshOwnerPanel() {
  setOwnerSyncStatus("Обновляем данные из общей базы…");
  renderOwnerPanel();

  if (state.serverMode) {
    await loadSocialData();
    renderOwnerPanel();
    setOwnerSyncStatus("Данные с локального сервера обновлены.", "ok");
    return;
  }

  if (!getFirebaseBase()) {
    setOwnerSyncStatus(
      "Общая база не подключена — видны только лайки и комментарии этого браузера.",
      "warn"
    );
    return;
  }

  try {
    const data = await fetchFirebaseSocial();
    if (!data) throw new Error("no data");
    ownerSocialCache = data;
    applyFirebaseSocial(data, false);
    renderOwnerPanel();
    setOwnerSyncStatus(`Данные из общей базы обновлены · ${new Date().toLocaleTimeString("ru-RU")}`, "ok");
  } catch {
    setOwnerSyncStatus(
      "Не удалось связаться с общей базой. Проверьте подключение к интернету и правила Firebase.",
      "warn"
    );
    renderOwnerPanel();
  }
}

function openOwnerPanel() {
  if (!ownerPanel) return;
  ownerPanelOpen = true;
  ownerPanel.classList.remove("hidden");
  renderOwnerPanel();
  refreshOwnerPanel();
}

function closeOwnerPanel() {
  if (!ownerPanel) return;
  ownerPanelOpen = false;
  ownerPanel.classList.add("hidden");
}

ownerStatsBtn?.addEventListener("click", openOwnerPanel);
closeOwnerPanelBtn?.addEventListener("click", closeOwnerPanel);
ownerPanel?.addEventListener("click", (e) => {
  if (e.target === ownerPanel) closeOwnerPanel();
});
ownerRefreshBtn?.addEventListener("click", () => refreshOwnerPanel());

document.querySelectorAll(".owner-tab").forEach((tab) => {
  tab.addEventListener("click", () => {
    ownerActiveTab = tab.dataset.ownerTab === "comments" ? "comments" : "likes";
    document.querySelectorAll(".owner-tab").forEach((t) => {
      const active = t === tab;
      t.classList.toggle("active", active);
      t.setAttribute("aria-selected", String(active));
    });
    renderOwnerPanel();
  });
});

document.addEventListener("keydown", (e) => {
  if (e.key === "Escape" && ownerPanelOpen) closeOwnerPanel();
});


// ============================================================================
// Удаление трека владельцем
// Локальный server.py — удаляет файл с диска.
// GitHub Pages — удаляет .mp3, обложку и запись в tracks.json через GitHub API
// с личным токеном, который хранится только в этом браузере (localStorage).
// ============================================================================

const LS_GH_TOKEN = "soundwave_gh_token_v1";

let pendingDeleteTrackId = null;
let deletingInFlight = false;

function getGithubToken() {
  try {
    return localStorage.getItem(LS_GH_TOKEN) || "";
  } catch {
    return "";
  }
}

function setGithubToken(token) {
  try {
    if (token) localStorage.setItem(LS_GH_TOKEN, token);
    else localStorage.removeItem(LS_GH_TOKEN);
  } catch {
    // приватный режим — токен проживёт только до перезагрузки
  }
}

function syncOwnerTokenUI() {
  const token = getGithubToken();
  if (ownerTokenStatus && !token) ownerTokenStatus.textContent = "";
  if (ownerTokenInput) {
    ownerTokenInput.value = token ? "•".repeat(Math.min(24, token.length)) : "";
  }
  document.querySelector(".owner-token")?.classList.toggle("is-saved", Boolean(token));
  if (ownerTokenHint) {
    ownerTokenHint.innerHTML = token
      ? "Токен сохранён в этом браузере — кнопки удаления работают. Чтобы стереть, нажмите «Забыть»."
      : `Токен нужен только для удаления песен на GitHub Pages. Создать:
         <a href="https://github.com/settings/tokens/new?scopes=repo&description=НейроДвиж" target="_blank" rel="noopener">Settings → Developer settings → Tokens (classic)</a>,
         галочка <code>repo</code>. Токен не сохраняется в коде сайта.`;
  }
}

ownerTokenSaveBtn?.addEventListener("click", () => {
  const raw = ownerTokenInput?.value.trim() || "";
  // Если в поле маскировка, значит токен уже сохранён — не перезаписываем
  if (raw && !raw.startsWith("•")) {
    setGithubToken(raw);
    showToast("Токен GitHub сохранён");
  } else if (!raw) {
    showToast("Вставьте токен в поле");
    return;
  }
  syncOwnerTokenUI();
});

ownerTokenClearBtn?.addEventListener("click", () => {
  setGithubToken("");
  syncOwnerTokenUI();
  if (ownerTokenStatus) ownerTokenStatus.textContent = "";
  showToast("Токен удалён из браузера");
});

// Проверка токена: показывает, может ли он читать и удалять файлы в репозитории
function setTokenStatus(text, kind) {
  if (!ownerTokenStatus) return;
  ownerTokenStatus.textContent = text;
  ownerTokenStatus.dataset.state = kind || "";
}

ownerTokenCheckBtn?.addEventListener("click", async () => {
  const token = getGithubToken();
  if (!token) {
    setTokenStatus("Сначала вставьте токен и нажмите «Сохранить».", "error");
    return;
  }

  const originalLabel = ownerTokenCheckBtn.textContent;
  ownerTokenCheckBtn.disabled = true;
  ownerTokenCheckBtn.textContent = "Проверяем…";
  setTokenStatus("Соединяемся с GitHub…", "pending");

  try {
    const userRes = await fetch(`${GH_API}/user`, { headers: ghHeaders(), cache: "no-store" });
    if (userRes.status === 401) {
      setTokenStatus("Токен недействителен: истёк или скопирован с ошибкой. Создайте новый.", "error");
      return;
    }
    if (!userRes.ok) {
      setTokenStatus(`GitHub ответил ошибкой ${userRes.status}. Попробуйте позже.`, "error");
      return;
    }
    const user = await userRes.json();

    // Проверяем доступ именно к этому репозиторию
    const repoRes = await fetch(
      `${GH_API}/repos/${GITHUB_OWNER}/${GITHUB_REPO}`,
      { headers: ghHeaders(), cache: "no-store" }
    );
    if (repoRes.status === 404) {
      setTokenStatus("Токен не видит репозиторий — проверьте, что у него есть право «repo».", "error");
      return;
    }
    if (!repoRes.ok) {
      setTokenStatus(`Нет доступа к репозиторию (${repoRes.status}).`, "error");
      return;
    }
    const repo = await repoRes.json();

    const canWrite = Boolean(repo.permissions?.push || repo.permissions?.admin);
    if (!canWrite) {
      setTokenStatus(
        "Токен читает репозиторий, но удалять файлы не может. Нужен доступ с записью (Contents: Read and write).",
        "error"
      );
      return;
    }

    setTokenStatus(`Всё в порядке. Токен действует: ${user.login}. Удаление песен работает.`, "ok");
    showToast("Токен работает — можно удалять песни");
  } catch (err) {
    setTokenStatus(`Не удалось проверить токен: ${err?.message || "нет связи с GitHub"}.`, "error");
  } finally {
    ownerTokenCheckBtn.disabled = false;
    ownerTokenCheckBtn.textContent = originalLabel;
  }
});

// --- GitHub API: получить/удалить файл по пути в репозитории ---
const GH_API = "https://api.github.com";

function ghHeaders() {
  return {
    Accept: "application/vnd.github.v3+json",
    Authorization: `Bearer ${getGithubToken()}`,
  };
}

// Путь к файлу в репозитории. Часть треков приходит из автоскана GitHub уже
// закодированной (%D0%91...), часть — обычным текстом. Поэтому сначала
// раскодируем путь, а затем кодируем ровно один раз: иначе получается двойное
// кодирование (%2525) и GitHub отвечает 404 — файл «не удаляется».
function normalizeRepoPath(path) {
  let s = String(path || "").replace(/\\/g, "/").replace(/^\.?\//, "");
  for (let i = 0; i < 3; i++) {
    if (!/%[0-9A-Fa-f]{2}/.test(s)) break;
    try {
      const decoded = decodeURIComponent(s);
      if (decoded === s) break;
      s = decoded;
    } catch {
      break;
    }
  }
  return s;
}

// Полный путь внутри репозитория: music_website/tracks/<жанр>/<файл>
function repoPathForWrite(value) {
  const raw = String(value || "");
  if (!raw || /^https?:/i.test(raw) || /^data:|^blob:/i.test(raw)) return "";
  const rel = normalizeRepoPath(raw);
  if (!rel) return "";
  return rel.startsWith("music_website/") ? rel : `music_website/${rel}`;
}

function encodeRepoPath(path) {
  return normalizeRepoPath(path)
    .split("/")
    .filter(Boolean)
    .map(encodeURIComponent)
    .join("/");
}

function ghContentsUrl(path) {
  return `${GH_API}/repos/${GITHUB_OWNER}/${GITHUB_REPO}/contents/${encodeRepoPath(path)}`;
}

// Список файлов в папке репозитория (null — если получить не удалось)
async function ghListDir(dirPath) {
  const res = await fetch(`${ghContentsUrl(dirPath)}?ref=${GITHUB_BRANCH}`, {
    headers: ghHeaders(),
    cache: "no-store",
  });
  if (res.status === 401 || res.status === 403) {
    const err = new Error(`GitHub ${res.status}`);
    err.status = res.status;
    throw err;
  }
  if (!res.ok) return null;
  const data = await res.json().catch(() => null);
  return Array.isArray(data) ? data : null;
}

async function ghGetFile(path) {
  const res = await fetch(`${ghContentsUrl(path)}?ref=${GITHUB_BRANCH}`, {
    headers: ghHeaders(),
    cache: "no-store",
  });
  if (res.status === 404) return null;
  if (!res.ok) {
    const err = new Error(`GitHub ${res.status}`);
    err.status = res.status;
    throw err;
  }
  return res.json();
}

// Ищем файл в папке по имени без учёта регистра и формы юникода (NFC/NFD).
// Так удаление работает даже если имя на GitHub записано чуть иначе.
async function ghResolveFile(path) {
  const normalized = normalizeRepoPath(path);
  const parts = normalized.split("/").filter(Boolean);
  const name = parts.pop() || "";
  const dirPath = parts.join("/");

  let direct = null;
  try {
    direct = await ghGetFile(normalized);
  } catch (err) {
    // Плохой токен или нет прав — сообщаем сразу, не маскируем под «файла нет»
    if (err?.status === 401 || err?.status === 403) throw err;
    direct = null;
  }
  if (direct && direct.sha) {
    return { path: normalized, sha: direct.sha, name, certain: true };
  }

  const listing = await ghListDir(dirPath);
  if (!listing) {
    return { path: normalized, sha: null, name, certain: false };
  }

  const target = name.normalize("NFC").toLowerCase();
  const hit = listing.find(
    (item) =>
      item.type === "file" &&
      String(item.name).normalize("NFC").toLowerCase() === target
  );
  if (hit) {
    return { path: `${dirPath}/${hit.name}`, sha: hit.sha, name: hit.name, certain: true };
  }
  return { path: normalized, sha: null, name, certain: true };
}

// Возвращает { deleted, certain }: certain=false — не смогли проверить наличие файла
async function ghDeleteFile(path, message) {
  const resolved = await ghResolveFile(path);
  if (!resolved.sha) {
    return { deleted: false, certain: resolved.certain, path: resolved.path };
  }

  const res = await fetch(ghContentsUrl(resolved.path), {
    method: "DELETE",
    headers: { ...ghHeaders(), "Content-Type": "application/json" },
    body: JSON.stringify({ message, sha: resolved.sha, branch: GITHUB_BRANCH }),
  });

  if (res.ok) {
    return { deleted: true, certain: true, path: resolved.path };
  }
  if (res.status === 404) {
    // Файл исчез между чтением и удалением — считаем удалённым
    return { deleted: true, certain: true, path: resolved.path };
  }
  const err = new Error(`Не удалось удалить ${path} (${res.status})`);
  err.status = res.status;
  throw err;
}

const TRACKS_INDEX_PATH = "music_website/tracks/tracks.json";

// Ключ для сравнения записей: без префикса music_website/, раскодированный, в нижнем регистре
function trackPathKey(value) {
  const key = normalizeRepoPath(value)
    .replace(/^music_website\//, "")
    .trim()
    .toLowerCase();
  return key.normalize ? key.normalize("NFC") : key;
}

function decodeGithubContent(content) {
  const binary = atob(String(content).replace(/\s/g, ""));
  try {
    return decodeURIComponent(escape(binary));
  } catch {
    return binary;
  }
}

function encodeGithubContent(text) {
  return btoa(unescape(encodeURIComponent(text)));
}

async function ghDeleteTrackFromIndex(track) {
  const targets = new Set(
    [track.id, track.src, track.fallbackSrc]
      .filter(Boolean)
      .map((v) => trackPathKey(v))
  );

  for (let attempt = 0; attempt < 2; attempt++) {
    const info = await ghGetFile(TRACKS_INDEX_PATH);
    if (!info || !info.content) return false;

    let json;
    try {
      json = JSON.parse(decodeGithubContent(info.content));
    } catch {
      return false;
    }
    if (!Array.isArray(json.tracks)) return false;

    const before = json.tracks.length;
    json.tracks = json.tracks.filter((t) => {
      const keys = [t.id, t.src].filter(Boolean).map((v) => trackPathKey(v));
      return !keys.some((k) => targets.has(k));
    });
    if (json.tracks.length === before) return false;

    const content = encodeGithubContent(JSON.stringify({ tracks: json.tracks }, null, 2) + "\n");

    const res = await fetch(ghContentsUrl(TRACKS_INDEX_PATH), {
      method: "PUT",
      headers: { ...ghHeaders(), "Content-Type": "application/json" },
      body: JSON.stringify({
        message: `Remove "${track.title}" from tracks index`,
        content,
        sha: info.sha,
        branch: GITHUB_BRANCH,
      }),
    });

    if (res.ok) return true;
    // 409 — файл успели изменить. Перечитываем sha и пробуем ещё раз.
    if (res.status === 409 && attempt === 0) continue;
    return false;
  }
  return false;
}

function setDeleteProgress(text) {
  if (deleteProgress) deleteProgress.textContent = text || "";
}

function openDeleteTrackModal(trackId) {
  const track = state.tracks.find((t) => t.id === trackId);
  if (!track || !deleteTrackModal) return;

  pendingDeleteTrackId = trackId;
  if (deleteTrackName) deleteTrackName.textContent = `${track.title} — ${track.artist || "без исполнителя"}`;
  setDeleteProgress("");
  deleteTrackModal.classList.remove("hidden");
  confirmDeleteTrackBtn.disabled = false;
  syncOwnerTokenUI();

  // Предупреждаем, если удалять на GitHub нечем
  if (!state.serverMode && !getGithubToken()) {
    setDeleteProgress("Нужен токен GitHub — введите его в панели владельца (кнопка с диаграммой в шапке).");
  }
}

function closeDeleteTrackModal() {
  pendingDeleteTrackId = null;
  if (deletingInFlight) return;
  deleteTrackModal?.classList.add("hidden");
  setDeleteProgress("");
}

cancelDeleteTrackBtn?.addEventListener("click", closeDeleteTrackModal);
cancelDeleteTrackBtn2?.addEventListener("click", closeDeleteTrackModal);
deleteTrackModal?.addEventListener("click", (e) => {
  if (e.target === deleteTrackModal) closeDeleteTrackModal();
});

async function deleteTrackEverywhere(track) {
  if (state.serverMode) {
    // Локальный сервер: просим удалить файл с диска
    const res = await fetch("/api/delete-track", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ trackId: track.id }),
    });
    if (!res.ok) {
      const msg = await res.json().catch(() => ({}));
      throw new Error(msg.error || "Не удалось удалить файл на сервере");
    }
    return;
  }

  if (!getGithubToken()) {
    const err = new Error("Нет токена GitHub — введите его в панели владельца.");
    err.code = "NO_TOKEN";
    throw err;
  }

  const relSrc = repoPathForWrite(track.src || track.id);

  setDeleteProgress("Удаляем файл песни…");
  const fileResult = await ghDeleteFile(relSrc, `Delete track "${track.title}"`);

  if (!fileResult.deleted && fileResult.certain) {
    setDeleteProgress("Файла на GitHub уже нет — чистим список…");
  }

  // Обложка: удаляем только локальный файл внутри папки треков
  const coverRel = repoPathForWrite(track.cover);
  if (coverRel && /^music_website\/tracks\//.test(coverRel)) {
    try {
      setDeleteProgress("Удаляем обложку…");
      await ghDeleteFile(coverRel, `Delete cover for "${track.title}"`);
    } catch {
      // обложка могла быть внешней или уже удалённой — это не критично
    }
  }

  setDeleteProgress("Убираем песню из общего списка…");
  try {
    await ghDeleteTrackFromIndex(track);
  } catch {
    // запись могла уже отсутствовать (треки автоскана в tracks.json не попадают)
  }

  // Финальная проверка: файл должен исчезнуть из папки жанра
  if (fileResult.certain) {
    setDeleteProgress("Проверяем результат…");
    const check = await ghResolveFile(relSrc);
    if (check.sha) {
      const err = new Error("Файл остался на GitHub — удаление не применилось.");
      err.code = "STILL_THERE";
      throw err;
    }
  } else {
    // Проверить не смогли (сеть/лимит API) — не врём пользователю про «Готово»
    const err = new Error("Не удалось проверить результат удаления.");
    err.code = "UNVERIFIED";
    throw err;
  }
}

confirmDeleteTrackBtn?.addEventListener("click", async () => {
  if (deletingInFlight) return;
  const track = state.tracks.find((t) => t.id === pendingDeleteTrackId);
  if (!track) return;

  if (!state.serverMode && !getGithubToken()) {
    setDeleteProgress("Сначала вставьте токен GitHub в панели владельца и нажмите «Сохранить».");
    return;
  }

  const confirmed = window.confirm(
    `Удалить «${track.title}»?\n\nФайл будет удалён безвозвратно (восстановить можно только в истории GitHub).`
  );
  if (!confirmed) return;

  deletingInFlight = true;
  confirmDeleteTrackBtn.disabled = true;
  setDeleteProgress("Удаляем…");

  try {
    await deleteTrackEverywhere(track);

    // Останавливаем воспроизведение, если удаляли текущий трек
    if (state.currentTrackId === track.id) {
      try {
        audio.pause();
      } catch {
        // ignore
      }
      state.currentTrackId = null;
      state.isPlaying = false;
      audio.removeAttribute("src");
    }

    state.tracks = state.tracks.filter((t) => t.id !== track.id);
    state.favorites.delete(track.id);
    persistFavorites();
    renderAll();
    updatePlayerUI?.();

    setDeleteProgress("Готово! Песня удалена.");
    showToast(`«${track.title}» удалена`);
    deletingInFlight = false;
    setTimeout(() => {
      deleteTrackModal?.classList.add("hidden");
      setDeleteProgress("");
    }, 900);
  } catch (err) {
    deletingInFlight = false;
    confirmDeleteTrackBtn.disabled = false;

    const status = err?.status;
    if (err?.code === "NO_TOKEN") {
      setDeleteProgress("Нужен токен GitHub — вставьте его в панели владельца.");
    } else if (err?.code === "STILL_THERE") {
      setDeleteProgress(
        "GitHub принял запрос, но файл всё ещё на месте. Обновите страницу (Ctrl+F5) и проверьте, что токен с правом «repo» и создан вами."
      );
    } else if (err?.code === "UNVERIFIED") {
      setDeleteProgress(
        "Команда на удаление отправлена, но проверить результат не удалось (сеть или лимит GitHub). Обновите страницу через минуту."
      );
    } else if (status === 401) {
      setDeleteProgress("Токен не принят: он истёк или скопирован с ошибкой. Создайте новый с правом «repo».");
    } else if (status === 403) {
      setDeleteProgress("У токена нет права удалять файлы. Нужен доступ «repo» (Contents: Read and write).");
    } else if (status === 404) {
      setDeleteProgress("Файл не найден в GitHub — возможно, он уже удалён. Обновите страницу.");
    } else if (status === 409) {
      setDeleteProgress("Файл только что изменился на GitHub. Нажмите «Удалить» ещё раз.");
    } else {
      setDeleteProgress(`Ошибка: ${err?.message || "не удалось удалить"}`);
    }
    showToast("Не удалось удалить песню");
  }
});

document.addEventListener("keydown", (e) => {
  if (e.key === "Escape" && pendingDeleteTrackId) closeDeleteTrackModal();
});

syncOwnerTokenUI();

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

// Кнопка «На весь экран»
const fullscreenBtn = document.getElementById("fullscreenBtn");

function isFullscreenActive() {
  return Boolean(document.fullscreenElement || document.webkitFullscreenElement);
}

function syncFullscreenBtn() {
  if (!fullscreenBtn) return;
  const active = isFullscreenActive();
  fullscreenBtn.classList.toggle("active", active);
  fullscreenBtn.title = active ? "Выйти из полноэкранного режима" : "На весь экран";
  fullscreenBtn.setAttribute(
    "aria-label",
    active ? "Выйти из полноэкранного режима" : "Развернуть на весь экран"
  );
  fullscreenBtn.querySelector(".icon-fs-enter")?.classList.toggle("hidden", active);
  fullscreenBtn.querySelector(".icon-fs-exit")?.classList.toggle("hidden", !active);
}

fullscreenBtn?.addEventListener("click", async () => {
  try {
    if (isFullscreenActive()) {
      const exitFn = document.exitFullscreen || document.webkitExitFullscreen;
      if (exitFn) await exitFn.call(document);
    } else {
      const el = document.documentElement;
      const reqFn = el.requestFullscreen || el.webkitRequestFullscreen;
      if (reqFn) {
        await reqFn.call(el);
      } else {
        showToast("На iPhone: нажмите «Поделиться» → «На экран Домой» для полного экрана");
      }
    }
  } catch {
    showToast("На iPhone: нажмите «Поделиться» → «На экран Домой» для полного экрана");
  } finally {
    syncFullscreenBtn();
  }
});

document.addEventListener("fullscreenchange", syncFullscreenBtn);
document.addEventListener("webkitfullscreenchange", syncFullscreenBtn);
syncFullscreenBtn();

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
  } else if (getFirebaseBase()) {
    // Ставим/снимаем СВОЙ лайк в общем списке — чужие лайки при этом не затираются
    const fbBase = getFirebaseBase();
    const key = encodeFirebaseKey(trackId);
    const path = `${fbBase}/social/likes/${key}/${CLIENT_ID}.json`;
    try {
      await fetch(path, {
        method: alreadyLiked ? "DELETE" : "PUT",
        headers: { "Content-Type": "application/json" },
        body: alreadyLiked ? undefined : JSON.stringify(Date.now()),
      });
      const data = await fetchFirebaseSocial();
      if (data) applyFirebaseSocial(data, true);
    } catch {
      // локальное состояние уже обновлено
    }
  }
}

// Фильтрация треков
function getFilteredTracks() {
  const q = state.search.trim().toLowerCase();

  return state.tracks.filter((track) => {
    if (state.genre === "favorites" && !state.favorites.has(track.id)) {
      return false;
    }
    // "all" — все песни, жанровые вкладки — только совпадающие
    if (state.genre !== "favorites" && state.genre !== "all" && track.genre !== state.genre) {
      return false;
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
    ruspop: 0,
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

// Подсветка активной вкладки жанра
// Названия для меню жанров (включая «Все песни»)
const GENRE_VIEW_LABELS = {
  all: "Все песни",
  favorites: "Избранное",
};

function genreViewLabel(key) {
  return GENRE_VIEW_LABELS[key] || GENRES[key]?.label || "Все песни";
}

function syncGenreTabs() {
  genreTabs?.querySelectorAll(".genre-option").forEach((option) => {
    const active = option.getAttribute("data-genre") === state.genre;
    option.classList.toggle("active", active);
    option.setAttribute("aria-selected", String(active));
  });

  if (genreCurrentLabel) genreCurrentLabel.textContent = genreViewLabel(state.genre);

  // Точка у кнопки повторяет цвет выбранного жанра
  const toggleDot = genreMenuBtn?.querySelector(".genre-toggle-dot");
  if (toggleDot) {
    toggleDot.className = `genre-dot dot-${state.genre}`;
  }
}

// Отрисовка списка треков
function renderTracks() {
  updateCounts();
  const list = getFilteredTracks();

  if (list.length === 0) {
    tracksGrid.innerHTML = "";
    emptyState.classList.remove("hidden");
    if (state.genre === "favorites") {
      emptyTitle.textContent = "В избранном пока нет треков";
      emptyDesc.textContent = "Нажмите на сердечко ♥ на любой карточке, чтобы добавить трек в избранное.";
    } else {
      emptyTitle.textContent = "Пока нет треков";
      emptyDesc.textContent = "Выберите другой жанр или загляните позже — музыка скоро появится.";
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

      const deleteTrackHtml = showOwner
        ? `<button
              type="button"
              class="track-delete-btn"
              data-action="delete"
              data-id="${escapeHtml(track.id)}"
              title="Удалить песню"
              aria-label="Удалить ${escapeHtml(track.title)}"
            >
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <polyline points="3 6 5 6 21 6" />
                <path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6" />
                <path d="M10 11v6M14 11v6" />
                <path d="M9 6V4a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v2" />
              </svg>
            </button>`
        : "";

      return `
        <article class="${cardClass}" data-id="${escapeHtml(track.id)}">
          ${deleteTrackHtml}
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

          <div class="track-head-row" data-action="toggle" data-id="${escapeHtml(track.id)}">
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
          </div>
        </article>
      `;
    })
    .join("");
}

function syncBackgroundMood() {
  const playingTrack = state.isPlaying
    ? state.tracks.find((t) => t.id === state.currentTrackId)
    : null;
  const theme = playingTrack ? playingTrack.genre : state.genre;
  if (theme) {
    document.body.dataset.theme = theme;
  } else {
    delete document.body.dataset.theme;
  }
  document.body.classList.toggle("music-playing", Boolean(state.isPlaying));
}

function renderAll() {
  syncGenreTabs();
  renderTracks();
  syncBackgroundMood();
}

// Обновление нижнего плеера
function updatePlayerUI() {
  const track = state.tracks.find((t) => t.id === state.currentTrackId);
  const iconPlay = playPauseBtn.querySelector(".icon-play");
  const iconPause = playPauseBtn.querySelector(".icon-pause");

  iconPlay.classList.toggle("hidden", state.isPlaying);
  iconPause.classList.toggle("hidden", !state.isPlaying);
  syncBackgroundMood();

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

// Быстрое обновление только активной карточки без перерисовки всего списка (убирает тормоза при переключении)
const ICON_PLAY_SVG = `<svg viewBox="0 0 24 24" fill="currentColor"><polygon points="7 4 20 12 7 20 7 4"/></svg>`;
const ICON_PAUSE_SVG = `<svg viewBox="0 0 24 24" fill="currentColor"><rect x="6" y="4" width="4" height="16" rx="1"/><rect x="14" y="4" width="4" height="16" rx="1"/></svg>`;

function syncPlayingCardUI() {
  const cards = tracksGrid.querySelectorAll(".track-card");
  cards.forEach((card) => {
    const id = card.getAttribute("data-id");
    const isCurrent = id === state.currentTrackId;
    const isPlayingCurrent = isCurrent && state.isPlaying;
    const isPausedCurrent = isCurrent && !state.isPlaying;

    card.classList.toggle("is-playing", isPlayingCurrent);
    card.classList.toggle("is-paused", isPausedCurrent);

    const playBtn = card.querySelector(".cover-play-overlay");
    if (playBtn) {
      const wantPause = isPlayingCurrent;
      if (playBtn.dataset.iconState !== (wantPause ? "pause" : "play")) {
        playBtn.dataset.iconState = wantPause ? "pause" : "play";
        playBtn.innerHTML = wantPause ? ICON_PAUSE_SVG : ICON_PLAY_SVG;
      }
    }

    if (isCurrent) {
      const track = state.tracks.find((t) => t.id === id);
      const durEl = card.querySelector(".track-duration");
      if (track && durEl && track.duration && durEl.textContent !== track.duration) {
        durEl.textContent = track.duration;
      }
    }
  });
}

// Фоновая предзагрузка следующей песни для мгновенного автопереключения без пауз
let preloadAudio = null;
let preloadedTrackId = null;

function getNextTrackInQueue(direction = 1) {
  const list = getFilteredTracks();
  const pool = list.length > 0 ? list : state.tracks;
  if (pool.length === 0) return null;

  if (state.isShuffle && pool.length > 1) {
    const others = pool.filter((t) => t.id !== state.currentTrackId);
    return others[Math.floor(Math.random() * others.length)] || pool[0];
  }

  const idx = pool.findIndex((t) => t.id === state.currentTrackId);
  const nextIdx = idx === -1 ? 0 : (idx + direction + pool.length) % pool.length;
  return pool[nextIdx] || null;
}

function preloadNextTrack() {
  if (state.isRepeat || state.isShuffle) return;
  const next = getNextTrackInQueue(1);
  if (!next || next.id === state.currentTrackId || next.id === preloadedTrackId) return;
  preloadedTrackId = next.id;

  try {
    if (!preloadAudio) {
      preloadAudio = new Audio();
      preloadAudio.crossOrigin = "anonymous";
      preloadAudio.preload = "auto";
      preloadAudio.muted = true;
    }
    preloadAudio.src = encodeTrackUrl(next.src);
    preloadAudio.load();
  } catch {
    // ignore
  }
}

// Интеграция с MediaSession (кнопки на экране блокировки + стабильное автопереключение в фоне на телефоне)
function updateMediaSession(track) {
  if (!("mediaSession" in navigator) || !track) return;
  try {
    const genreInfo = GENRES[track.genre] || { label: track.genre };
    const artwork = track.cover
      ? [{ src: new URL(encodeTrackUrl(track.cover), window.location.href).href, sizes: "512x512" }]
      : [];
    navigator.mediaSession.metadata = new MediaMetadata({
      title: track.title,
      artist: `${track.artist} · ${genreInfo.label}`,
      album: "НейроДвиж",
      artwork,
    });
    navigator.mediaSession.playbackState = state.isPlaying ? "playing" : "paused";
  } catch {
    // ignore
  }
}

function initMediaSessionHandlers() {
  if (!("mediaSession" in navigator)) return;
  const bind = (action, fn) => {
    try {
      navigator.mediaSession.setActionHandler(action, fn);
    } catch {
      // ignore unsupported action
    }
  };
  bind("play", () => {
    if (state.currentTrackId) playTrack(state.currentTrackId);
  });
  bind("pause", () => {
    audio.pause();
  });
  bind("previoustrack", () => stepTrack(-1));
  bind("nexttrack", () => stepTrack(1));
  bind("seekto", (details) => {
    if (details?.seekTime != null && Number.isFinite(audio.duration)) {
      audio.currentTime = Math.max(0, Math.min(audio.duration, details.seekTime));
    }
  });
}

// Воспроизведение (чистый нативный <audio> по умолчанию, AudioContext — только при включённом EQ/Бас/3D)
let playSeq = 0;

function playTrack(trackId) {
  const track = state.tracks.find((t) => t.id === trackId);
  if (!track) return;

  const seq = ++playSeq;
  initVisualizer();

  // Анализатор подключаем всегда (это не меняет звук, пока эквалайзер выключен)
  ensureSpectrumAnalyser();
  if (isEqActive()) {
    applyEqSettings(true);
  }

  const isSwitching = state.currentTrackId !== trackId;
  if (isSwitching) {
    state.currentTrackId = trackId;
    audio.dataset.fallbackUsed = "0";
    audio.src = encodeTrackUrl(track.src);
    audio.currentTime = 0;
    progressBar.value = "0";
    progressBar.style.background = "";
    currentTimeEl.textContent = "0:00";
    durationTimeEl.textContent = track.duration && track.duration !== "--:--" ? track.duration : "0:00";
    updatePlayerUI();
    syncPlayingCardUI();
  }

  const startPlayback = () => {
    const playPromise = audio.play();
    if (!playPromise) return;
    playPromise
      .then(() => {
        if (seq !== playSeq) return;
        state.isPlaying = true;
        updatePlayerUI();
        syncPlayingCardUI();
        updateMediaSession(track);
        // Запускаем тихую предзагрузку следующей песни через 1.5 сек
        setTimeout(() => {
          if (seq === playSeq && state.isPlaying) preloadNextTrack();
        }, 1500);
      })
      .catch((err) => {
        if (seq !== playSeq) return;
        if (err && err.name === "AbortError") return;
        // Если основной файл ещё не опубликован на GitHub Pages, пробуем запасную ссылку raw.githubusercontent.com
        if (track.fallbackSrc && audio.dataset.fallbackUsed !== "1") {
          audio.dataset.fallbackUsed = "1";
          audio.src = track.fallbackSrc;
          audio
            .play()
            .then(() => {
              if (seq !== playSeq) return;
              state.isPlaying = true;
              updatePlayerUI();
              syncPlayingCardUI();
              updateMediaSession(track);
            })
            .catch((err2) => {
              if (seq !== playSeq || err2?.name === "AbortError") return;
              console.error("Ошибка воспроизведения:", err2);
              showToast("Не удалось воспроизвести файл");
            });
          return;
        }
        console.error("Ошибка воспроизведения:", err);
        showToast("Не удалось воспроизвести файл");
      });
  };

  startPlayback();
}

function toggleTrack(trackId) {
  if (state.currentTrackId === trackId) {
    if (state.isPlaying) {
      audio.pause();
      state.isPlaying = false;
      updatePlayerUI();
      syncPlayingCardUI();
    } else {
      playTrack(trackId);
    }
  } else {
    playTrack(trackId);
  }
}

function stepTrack(direction) {
  const next = getNextTrackInQueue(direction);
  if (next) playTrack(next.id);
}

// --- События фильтров и карточек ---
// --- Меню жанров ---
const LS_GENRE_HINT_SEEN = "neurodvizh_genre_hint_seen_v1";

function hideGenreHint() {
  if (!genreHint) return;
  genreHint.classList.add("is-hidden");
  document.getElementById("genreHintHand")?.classList.add("is-hidden");
  try {
    localStorage.setItem(LS_GENRE_HINT_SEEN, "1");
  } catch {
    // приватный режим — подсказка вернётся после перезагрузки
  }
}

function restoreGenreHint() {
  if (!genreHint) return;
  let seen = false;
  try {
    seen = localStorage.getItem(LS_GENRE_HINT_SEEN) === "1";
  } catch {
    seen = false;
  }
  genreHint.classList.toggle("is-hidden", seen);
  document.getElementById("genreHintHand")?.classList.toggle("is-hidden", seen);
}

function setGenreMenuOpen(open) {
  if (!genreMenu || !genreMenuBtn) return;
  genreMenu.classList.toggle("hidden", !open);
  genreMenuBtn.setAttribute("aria-expanded", String(open));
}

function isGenreMenuOpen() {
  return genreMenu ? !genreMenu.classList.contains("hidden") : false;
}

genreMenuBtn?.addEventListener("click", (e) => {
  e.stopPropagation();
  setGenreMenuOpen(!isGenreMenuOpen());
});

// Клик вне меню закрывает его
document.addEventListener("click", (e) => {
  if (!isGenreMenuOpen()) return;
  if (e.target.closest(".genre-dropdown")) return;
  setGenreMenuOpen(false);
});

document.addEventListener("keydown", (e) => {
  if (e.key === "Escape" && isGenreMenuOpen()) setGenreMenuOpen(false);
});

restoreGenreHint();

genreTabs.addEventListener("click", (e) => {
  const btn = e.target.closest(".genre-option");
  if (!btn) return;
  const genre = btn.getAttribute("data-genre");
  if (!genre) return;

  if (genre === state.genre && !isGenreMenuOpen()) return;

  state.genre = genre;
  setGenreMenuOpen(false);
  hideGenreHint();
  renderAll();
});

resetFiltersBtn.addEventListener("click", () => {
  state.genre = "all";
  state.search = "";
  renderAll();
});

rescanBtn.addEventListener("click", () => loadTracksFromServer(true));

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
  } else if (action === "cover") {
    e.stopPropagation();
    state.coverTargetTrackId = id;
    changeCoverInput.value = "";
    changeCoverInput.click();
  } else if (action === "delete") {
    e.stopPropagation();
    openDeleteTrackModal(id);
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
  } else if (getFirebaseBase()) {
    const fbBase = getFirebaseBase();
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
  } else if (getFirebaseBase()) {
    const fbBase = getFirebaseBase();
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

  // Подтягиваем свежий список из общей базы, чтобы комментарий точно сохранился
  if (!state.serverMode && getFirebaseBase()) {
    try {
      const data = await fetchFirebaseSocial();
      if (data) applyFirebaseSocial(data, true);
    } catch {
      // локальная копия уже показана
    }
  }
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
    syncPlayingCardUI();
  }
});

audio.addEventListener("play", () => {
  state.isPlaying = true;
  // Анализатор для цветомузыки подключаем всегда (звук при выключенном EQ не меняется)
  ensureSpectrumAnalyser();
  updatePlayerUI();
  syncPlayingCardUI();
  const track = state.tracks.find((t) => t.id === state.currentTrackId);
  if (track) updateMediaSession(track);
});

audio.addEventListener("pause", () => {
  if (!audio.ended) {
    state.isPlaying = false;
    updatePlayerUI();
    syncPlayingCardUI();
    if ("mediaSession" in navigator) {
      try {
        navigator.mediaSession.playbackState = "paused";
      } catch {
        // ignore
      }
    }
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
  if (audioEngine?.ctx?.state === "suspended") {
    audioEngine.ctx.resume().catch(() => {});
  }
  if (state.isRepeat) {
    audio.currentTime = 0;
    audio.play().catch(() => {});
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

function setAppVolume(val) {
  const clamped = Math.max(0, Math.min(1, Number(val)));
  audio.volume = clamped;
  audio.muted = clamped === 0;
  volumeBar.value = String(clamped);
  if (eqVolumeSlider && eqVolumeVal) {
    eqVolumeSlider.value = String(clamped);
    eqVolumeVal.textContent = `${Math.round(clamped * 100)}%`;
  }
  syncVolumeIcons();
}

volumeBar.addEventListener("input", () => setAppVolume(volumeBar.value));

muteBtn.addEventListener("click", () => {
  audio.muted = !audio.muted;
  syncVolumeIcons();
  syncEqUI();
});

// --- Модалка настроек звука (Бас-буст, Объёмный звук 3D, Эквалайзер) ---
function openEqModal() {
  syncEqUI();
  eqModal.classList.remove("hidden");
}

function closeEqModal() {
  eqModal.classList.add("hidden");
}

openEqBtn?.addEventListener("click", openEqModal);
closeEqBtn?.addEventListener("click", closeEqModal);
doneEqBtn?.addEventListener("click", closeEqModal);
eqModal?.addEventListener("click", (e) => {
  if (e.target === eqModal) closeEqModal();
});

bassBoostToggle?.addEventListener("click", () => {
  state.eq.bassBoost = !state.eq.bassBoost;
  state.eq.preset = "custom";
  applyEqSettings(true);
  showToast(state.eq.bassBoost ? "Бас-буст включён" : "Бас-буст выключен");
});

surroundToggle?.addEventListener("click", () => {
  state.eq.surround = !state.eq.surround;
  state.eq.preset = "custom";
  applyEqSettings(true);
  showToast(state.eq.surround ? "Объёмный звук 3D включён" : "Объёмный звук 3D выключен");
});

eqPresetsEl?.addEventListener("click", (e) => {
  const btn = e.target.closest(".eq-preset-btn");
  if (!btn) return;
  const key = btn.getAttribute("data-preset");
  const preset = EQ_PRESETS[key];
  if (!preset) return;

  state.eq = { ...preset, preset: key };
  applyEqSettings(key !== "flat");
  showToast(`Режим звука: ${btn.textContent.trim()}`);
});

eqBassSlider?.addEventListener("input", () => {
  state.eq.bass = Number(eqBassSlider.value);
  state.eq.preset = "custom";
  applyEqSettings(true);
});

eqMidSlider?.addEventListener("input", () => {
  state.eq.mid = Number(eqMidSlider.value);
  state.eq.preset = "custom";
  applyEqSettings(true);
});

eqTrebleSlider?.addEventListener("input", () => {
  state.eq.treble = Number(eqTrebleSlider.value);
  state.eq.preset = "custom";
  applyEqSettings(true);
});

eqVolumeSlider?.addEventListener("input", () => setAppVolume(eqVolumeSlider.value));

resetEqBtn?.addEventListener("click", () => {
  state.eq = { ...EQ_PRESETS.flat, preset: "flat" };
  setAppVolume(1);
  applyEqSettings(false);
  showToast("Настройки звука сброшены");
});

syncEqUI();

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

// Живой падающий снег поверх чёрно-белого фона (без тумана)
function initSnowfall() {
  const canvas = document.getElementById("snowCanvas");
  if (!canvas) return;
  if (window.matchMedia?.("(prefers-reduced-motion: reduce)")?.matches) return;

  const ctx = canvas.getContext("2d");
  if (!ctx) return;

  let width = 0;
  let height = 0;
  let flakes = [];
  let windTime = 0;

  function resize() {
    // На телефонах снег рисуем в пониженном разрешении и меньшим числом частиц —
    // полноэкранный канвас самый прожорливый по пикселям
    const snowDprCap = vizQuality >= 2 ? 2 : vizQuality === 1 ? 1.25 : 1;
    const dpr = Math.min(window.devicePixelRatio || 1, snowDprCap);
    width = window.innerWidth;
    height = window.innerHeight;
    canvas.width = Math.floor(width * dpr);
    canvas.height = Math.floor(height * dpr);
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);

    const narrow = width < 700;
    const targetCount =
      vizQuality >= 2 ? (narrow ? 52 : 95) : vizQuality === 1 ? (narrow ? 32 : 60) : narrow ? 18 : 34;
    while (flakes.length < targetCount) flakes.push(spawnFlake(true));
    if (flakes.length > targetCount) flakes.length = targetCount;
  }

  function spawnFlake(randomY = false) {
    // 3 слоя глубины: дальний мелкий, средний, ближний крупный
    const depth = Math.random();
    const isCrystal = depth > 0.84;
    const radius = isCrystal
      ? 3.2 + Math.random() * 2.4
      : 1.0 + depth * 2.4;

    return {
      x: Math.random() * (width || window.innerWidth),
      y: randomY ? Math.random() * (height || window.innerHeight) : -14 - Math.random() * 24,
      r: radius,
      vy: 0.45 + depth * 1.35,
      swayAmp: 0.25 + depth * 0.75,
      swayFreq: 0.008 + Math.random() * 0.016,
      phase: Math.random() * Math.PI * 2,
      alpha: 0.35 + depth * 0.55,
      crystal: isCrystal,
      angle: Math.random() * Math.PI * 2,
      spin: (Math.random() - 0.5) * 0.018,
    };
  }

  function drawCrystal(x, y, r, angle, alpha) {
    ctx.save();
    ctx.translate(x, y);
    ctx.rotate(angle);
    ctx.strokeStyle = `rgba(255, 255, 255, ${alpha})`;
    ctx.lineWidth = 1;
    ctx.lineCap = "round";

    for (let i = 0; i < 3; i++) {
      ctx.beginPath();
      ctx.moveTo(-r, 0);
      ctx.lineTo(r, 0);
      ctx.stroke();

      // Маленькие веточки на концах лучей
      const b = r * 0.58;
      const tip = r * 0.3;
      ctx.beginPath();
      ctx.moveTo(b, 0);
      ctx.lineTo(b + tip * 0.7, -tip * 0.7);
      ctx.moveTo(b, 0);
      ctx.lineTo(b + tip * 0.7, tip * 0.7);
      ctx.moveTo(-b, 0);
      ctx.lineTo(-b - tip * 0.7, -tip * 0.7);
      ctx.moveTo(-b, 0);
      ctx.lineTo(-b - tip * 0.7, tip * 0.7);
      ctx.stroke();

      ctx.rotate(Math.PI / 3);
    }
    ctx.restore();
  }

  resize();
  window.addEventListener("resize", resize);

  let lastFrame = 0;
  function tick(now) {
    requestAnimationFrame(tick);
    if (document.hidden) return;
    const minInterval = width < 700 ? 32 : 22;
    if (now - lastFrame < minInterval) return;
    const dt = Math.min(2.2, (now - lastFrame) / 16.67 || 1);
    lastFrame = now;

    ctx.clearRect(0, 0, width, height);
    windTime += 0.004 * dt;
    const breeze = Math.sin(windTime) * 0.35;
    const speedBoost = (state.isPlaying ? 1.15 : 1) * dt;

    for (const f of flakes) {
      f.phase += f.swayFreq * speedBoost;
      f.y += f.vy * speedBoost;
      f.x += (breeze + Math.sin(f.phase) * f.swayAmp) * speedBoost;
      if (f.crystal) f.angle += f.spin * dt;

      if (f.y > height + 16) {
        Object.assign(f, spawnFlake(false));
      } else if (f.x < -16) {
        f.x = width + 14;
      } else if (f.x > width + 16) {
        f.x = -14;
      }

      if (f.crystal) {
        drawCrystal(f.x, f.y, f.r, f.angle, f.alpha);
      } else {
        ctx.fillStyle = `rgba(255, 255, 255, ${f.alpha})`;
        ctx.beginPath();
        ctx.arc(f.x, f.y, f.r, 0, Math.PI * 2);
        ctx.fill();
      }
    }
  }

  requestAnimationFrame(tick);
}

// Старт приложения
initMediaSessionHandlers();
initSnowfall();
initVisualizer();
loadTracksFromServer(false);
startSocialSync();
