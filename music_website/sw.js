/*
 * Service worker «НейроДозы».
 *
 * Задачи:
 * 1. Оболочка приложения (HTML, CSS, JS, иконки) открывается мгновенно и без сети.
 * 2. Новая версия сайта подхватывается сама при следующем запуске — иначе
 *    установленное приложение месяцами показывало бы старый код.
 * 3. Музыка и обложки в кэш не кладутся: файлы большие, а слушать их всё
 *    равно можно только с интернетом.
 *
 * ВАЖНО: при изменении index.html/style.css/script.js меняйте CACHE_VERSION,
 * иначе у установленных приложений останется старая копия.
 */

const CACHE_VERSION = "neurodoza-v20261226";
const SHELL_CACHE = `${CACHE_VERSION}-shell`;

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

// Не кэшируем: музыка, обложки треков и всё, что меняется от устройства к устройству
const NEVER_CACHE = /\/tracks\/|\.(mp3|m4a|wav|ogg|flac|aac|opus|webm|jpg|jpeg|png|webp)$/i;

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches
      .open(SHELL_CACHE)
      .then((cache) =>
        // addAll падает целиком, если один файл недоступен — добавляем по одному
        Promise.all(
          SHELL_ASSETS.map((url) =>
            cache.add(new Request(url, { cache: "reload" })).catch(() => null)
          )
        )
      )
      // ВАЖНО: здесь намеренно НЕТ skipWaiting(). Если он есть, новая версия
      // сразу вытесняет старую, у всех открытых страниц меняется контроллер
      // и — если их перезагрузить — у гостя обрывается песня на середине.
      // Вместо этого новая версия ждёт (waiting), пока страница не решит:
      // «сейчас safe обновиться». Решение принимает script.js.
  );
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches
      .keys()
      .then((keys) =>
        Promise.all(
          keys
            .filter((key) => key !== SHELL_CACHE)
            .map((key) => caches.delete(key))
        )
      )
      .then(async () => {
        // claim() берёт под контроль страницы без контроллера — это первый
        // запуск, там обновлять нечего и рвать нечего. Если же страницы уже
        // под старой версией, оставляем их в покое: они сами решат, когда
        // переключаться (иначе гарантирован обрыв музыки).
        const windows = await self.clients.matchAll({ type: "window" });
        const uncontrolled = windows.filter((client) => !client.controller);
        if (uncontrolled.length > 0) {
          await self.clients.claim();
        }
      })
  );
});

// Оболочка: сначала сеть (чтобы обновления приходили сразу), при обрыве — кэш.
// Сеть отдаёт страницу быстрее, чем кто-то успевает заметить; офлайн — из кэша.
async function networkFirst(request) {
  const cache = await caches.open(SHELL_CACHE);
  try {
    const response = await fetch(request);
    if (response && response.ok) {
      cache.put(request, response.clone()).catch(() => {});
    }
    return response;
  } catch (err) {
    const cached = await cache.match(request, { ignoreSearch: true });
    if (cached) return cached;
    // Последний шанс: главная страница из кэша вместо ошибки сети
    const shell = await cache.match("./index.html", { ignoreSearch: true });
    if (shell) return shell;
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

  // Музыка и картинки — мимо кэша
  if (NEVER_CACHE.test(url.pathname)) return;

  event.respondWith(networkFirst(request));
});

// Сообщение от страницы: «переключайся на новую версию».
// Страница присылает его только тогда, когда безопасно: пауза, конец трека,
// или гость сам нажал «Обновить».
self.addEventListener("message", (event) => {
  if (event.data === "SKIP_WAITING") {
    self.skipWaiting();
  }
});
