/*
 * Service worker «НейроДозы» с ручным выпуском обновлений.
 *
 * Главная идея: код можно заливать когда угодно, но гости увидят его только
 * после того, как владелец поменяет номер в music_website/release.json.
 *
 *   release.json  = {"release": "2026-12-26"}
 *
 * Как это работает:
 * 1. Оболочка (HTML, CSS, JS, иконки) отдаётся ИЗ КЭША — гость всегда видит
 *    ту версию, которую выпустили, а не то, что случайно задеплоено.
 * 2. Приложение периодически спрашивает service worker: «не вышло ли нового?».
 *    SW читает release.json из сети и сравнивает с тем, что показывает.
 * 3. Если номер другой — SW скачивает новую оболочку в отдельный кэш и
 *    сообщает странице «обновление готово». Старая версия продолжает работать.
 * 4. Страница применяет обновление в безопасный момент (пауза, конец трека
 *    или по кнопке) и перезагружается.
 *
 * Так правки не рвут музыку и не появляются у гостей раньше времени.
 *
 * ВАЖНО: release.json — единственный переключатель. Меняя index.html,
 * style.css или script.js, НЕ трогайте номер, пока не готовы выпустить.
 */

const RELEASE_URL = "./release.json";
const SHELL_PREFIX = "neurodoza-shell-";
const META_CACHE = "neurodoza-meta";
const MARKER_URL = "./.current-release";

// Минимальная оболочка: без неё приложение не запустится
const SHELL_ASSETS = [
  "./",
  "./index.html",
  "./style.css",
  "./script.js",
  "./manifest.json",
  "./favicon.ico",
  "./favicon-32.png",
  "./icon-192.png",
  "./icon-512.png",
  "./icon-512-maskable.png",
  "./apple-touch-icon.png",
];

// Не кэшируем: музыка, обложки и всё, что меняется от устройства к устройству
const NEVER_CACHE = /\/tracks\/|\.(mp3|m4a|wav|ogg|flac|aac|opus|webm|jpg|jpeg|png|webp)$/i;

// Номер версии, которую сейчас видят гости, и та, что уже скачана и ждёт
let currentRelease = null;
let pendingRelease = null;
let stagingPromise = null;

// --- Служебный маркер: какой релиз сейчас активен -------------------------

async function readMarker() {
  try {
    const meta = await caches.open(META_CACHE);
    const res = await meta.match(MARKER_URL);
    if (!res) return null;
    const text = (await res.text()).trim();
    return text || null;
  } catch {
    return null;
  }
}

async function writeMarker(release) {
  const meta = await caches.open(META_CACHE);
  await meta.put(
    MARKER_URL,
    new Response(release, { headers: { "Content-Type": "text/plain" } })
  );
}

// Какой номер опубликован на сайте прямо сейчас
async function fetchDeployedRelease() {
  try {
    const res = await fetch(new Request(RELEASE_URL, { cache: "no-store" }));
    if (!res || !res.ok) return null;
    const data = await res.json();
    const value = data && data.release;
    if (value === undefined || value === null) return null;
    return String(value).trim() || null;
  } catch {
    return null;
  }
}

async function shellCacheName() {
  if (!currentRelease) currentRelease = await readMarker();
  return SHELL_PREFIX + (currentRelease || "bootstrap");
}

// Скачиваем оболочку в кэш конкретного релиза
async function seedCache(release) {
  const name = SHELL_PREFIX + release;
  if (await caches.has(name)) return name;
  const cache = await caches.open(name);
  await Promise.all(
    SHELL_ASSETS.map((url) =>
      // Один недоступный файл не должен ломать установку целиком
      cache.add(new Request(url, { cache: "reload" })).catch(() => null)
    )
  );
  return name;
}

async function notifyAll(message) {
  try {
    const windows = await self.clients.matchAll({ type: "window", includeUncontrolled: true });
    windows.forEach((client) => client.postMessage(message));
  } catch {
    // нет окон — некому сообщать
  }
}

// --- Установка и активация ------------------------------------------------

self.addEventListener("install", (event) => {
  event.waitUntil(
    (async () => {
      // ВАЖНО: здесь намеренно НЕТ skipWaiting(). Если он есть, новая версия
      // сразу вытесняет старую, у открытых страниц меняется контроллер
      // и — если их перезагрузить — у гостя обрывается песня на середине.
      const marker = await readMarker();
      if (marker) {
        // Кэш уже есть — не перетираем его свежим деплоем.
        // Именно поэтому залитый код не виден, пока не поднят release.json.
        currentRelease = marker;
        return;
      }
      // Самый первый запуск: берём то, что сейчас опубликовано
      const release = (await fetchDeployedRelease()) || "bootstrap";
      await seedCache(release);
      await writeMarker(release);
      currentRelease = release;
    })()
  );
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    (async () => {
      currentRelease = currentRelease || (await readMarker());
      const keep = await shellCacheName();

      // Чистим всё лишнее: старые оболочки прошлых выпусков
      const keys = await caches.keys();
      await Promise.all(
        keys
          .filter((key) => key !== META_CACHE && key !== keep)
          .map((key) => caches.delete(key).catch(() => false))
      );

      // claim() нужен только страницам без контроллера (самый первый запуск).
      // Страницы под старой версией не трогаем: они сами решат, когда
      // переключаться, иначе гарантирован обрыв музыки.
      const windows = await self.clients.matchAll({ type: "window" });
      const uncontrolled = windows.filter((client) => !client.controller);
      if (uncontrolled.length > 0) {
        await self.clients.claim();
      }
    })()
  );
});

// --- Отдача файлов: сначала кэш, сеть — только как добавка ----------------

async function cacheFirst(request) {
  const name = await shellCacheName();
  const cache = await caches.open(name);
  const cached = await cache.match(request, { ignoreSearch: true });
  if (cached) return cached;

  // Нет в кэше (например, новая картинка) — берём из сети и докладываем
  try {
    const response = await fetch(request);
    if (response && response.ok) {
      cache.put(request, response.clone()).catch(() => {});
    }
    return response;
  } catch (err) {
    // Для переходов по страницам отдаём сохранённую главную
    if (request.mode === "navigate") {
      const shell = await cache.match("./index.html", { ignoreSearch: true });
      if (shell) return shell;
    }
    throw err;
  }
}

self.addEventListener("fetch", (event) => {
  const { request } = event;
  if (request.method !== "GET") return;

  const url = new URL(request.url);

  // Чужие домены (GitHub API, Firebase) не трогаем вовсе
  if (url.origin !== self.location.origin) return;

  // API локального сервера — всегда живой запрос
  if (url.pathname.includes("/api/")) return;

  // release.json — это сигнал о выпуске, его всегда читаем из сети свежим
  if (url.pathname.endsWith("/release.json")) return;

  // Музыка и картинки — мимо кэша
  if (NEVER_CACHE.test(url.pathname)) return;

  event.respondWith(cacheFirst(request));
});

// --- Проверка и применение релиза ----------------------------------------

async function checkRelease() {
  const deployed = await fetchDeployedRelease();
  if (!currentRelease) currentRelease = await readMarker();

  // deployed — что опубликовано на сайте; current — что показываем гостю.
  // Расхождение видно только владельцу (?admin=1) как подсказка.
  if (!deployed) {
    return { current: currentRelease, available: pendingRelease, offline: true };
  }
  if (deployed === currentRelease) {
    return { current: currentRelease, available: null, deployed };
  }
  if (pendingRelease === deployed) {
    return { current: currentRelease, available: pendingRelease, deployed };
  }

  // Новая версия: скачиваем её в отдельный кэш, старую не трогаем
  if (!stagingPromise) {
    stagingPromise = (async () => {
      await seedCache(deployed);
      pendingRelease = deployed;
      await notifyAll({ type: "UPDATE_READY", release: deployed });
    })()
      .catch(() => {})
      .finally(() => {
        stagingPromise = null;
      });
  }
  await stagingPromise;

  return { current: currentRelease, available: pendingRelease, deployed };
}

async function applyRelease() {
  if (!pendingRelease) return { applied: false };
  const previous = currentRelease;
  currentRelease = pendingRelease;
  pendingRelease = null;
  await writeMarker(currentRelease);

  // Старую оболочку убираем, чтобы не занимала место
  if (previous && previous !== currentRelease) {
    await caches.delete(SHELL_PREFIX + previous).catch(() => false);
  }
  return { applied: true, release: currentRelease };
}

self.addEventListener("message", (event) => {
  const data = event.data;
  const reply = (message) => {
    try {
      if (event.source && event.source.postMessage) event.source.postMessage(message);
    } catch {
      // источник мог закрыться
    }
  };

  // Просьба переключиться на новую версию service worker
  if (data === "SKIP_WAITING") {
    self.skipWaiting();
    return;
  }

  const type = data && typeof data === "object" ? data.type : null;

  if (type === "CHECK_RELEASE") {
    event.waitUntil(
      checkRelease().then((status) => reply({ type: "RELEASE_STATUS", ...status }))
    );
    return;
  }

  if (type === "APPLY_RELEASE") {
    event.waitUntil(
      applyRelease().then((result) => {
        if (result.applied) notifyAll({ type: "RELEASE_APPLIED", release: result.release });
        reply({ type: "RELEASE_APPLIED", ...result });
      })
    );
  }
});
