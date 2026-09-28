#!/usr/bin/env node
/**
 * make-standalone.mjs — генерирует автономный add-country.html
 * (работает двойным кликом, без сервера и без Node).
 *
 * Запуск: node scripts/make-standalone.mjs
 */
import { readFileSync, writeFileSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const root = path.join(path.dirname(fileURLToPath(import.meta.url)), '..');
const data = readFileSync(path.join(root, 'shared', 'countries.json'), 'utf8').trim();
const core = readFileSync(path.join(root, 'scripts', 'core-logic.cjs'), 'utf8').trim();

const GLUE = `
(function () {
  var DATA = __DATA__;
  var fileInput = document.getElementById('fileInput');
  var dropZone = document.getElementById('dropZone');
  var statusEl = document.getElementById('status');
  var statsEl = document.getElementById('stats');
  var previewEl = document.getElementById('preview');
  var dlBtn = document.getElementById('dl');
  var dlFlagBtn = document.getElementById('dlFlag');
  var pasteArea = document.getElementById('paste');
  var pasteBtn = document.getElementById('pasteBtn');
  var currentText = null;
  var currentName = 'playlist.m3u';

  function fmt(stats) {
    return 'Каналов: ' + stats.total + ' · добавлено: ' + stats.added +
      ' · уже было: ' + stats.unchanged + ' · без страны: ' + stats.unknown;
  }

  function preview(text) {
    var lines = text.split(/\\r?\\n/).filter(function (l) { return l.indexOf('#EXTINF') === 0; });
    var sample = lines.slice(0, 6).map(function (l) {
      var i = l.lastIndexOf(',');
      return i >= 0 ? l.slice(i + 1) : l;
    });
    previewEl.textContent = sample.join('\\n');
  }

  function process(text, name) {
    currentText = text.replace(/^\\uFEFF/, '');
    if (name) currentName = name;
    var res = AddCountry.processPlaylist(currentText, DATA, { withFlag: false });
    statsEl.textContent = fmt(res.stats);
    preview(res.text);
    dlBtn.disabled = false;
    dlFlagBtn.disabled = false;
    statusEl.textContent = 'Готово! Нажмите «Скачать результат».';
    statusEl.className = 'status ok';
  }

  function download(withFlag) {
    if (!currentText) return;
    var res = AddCountry.processPlaylist(currentText, DATA, { withFlag: withFlag });
    var blob = new Blob(['\\uFEFF' + res.text], { type: 'audio/x-mpegurl' });
    var url = URL.createObjectURL(blob);
    var a = document.createElement('a');
    a.href = url;
    a.download = currentName.replace(/(\\.m3u8?)?$/i, function (m) { return '_со_странами' + (m || '.m3u'); });
    document.body.appendChild(a);
    a.click();
    a.remove();
    setTimeout(function () { URL.revokeObjectURL(url); }, 5000);
    statusEl.textContent = 'Файл сохранён: ' + a.download;
    statusEl.className = 'status ok';
  }

  fileInput.addEventListener('change', function () {
    var f = fileInput.files && fileInput.files[0];
    if (!f) return;
    statusEl.textContent = 'Читаю ' + f.name + '…';
    statusEl.className = 'status';
    var r = new FileReader();
    r.onload = function () { process(String(r.result), f.name); };
    r.onerror = function () {
      statusEl.textContent = 'Не удалось прочитать файл';
      statusEl.className = 'status err';
    };
    r.readAsText(f, 'utf-8');
  });

  ['dragover', 'drop'].forEach(function (ev) {
    document.addEventListener(ev, function (e) {
      e.preventDefault();
      if (ev === 'dragover') { dropZone.classList.add('hot'); return; }
      dropZone.classList.remove('hot');
      var f = e.dataTransfer && e.dataTransfer.files && e.dataTransfer.files[0];
      if (f) {
        statusEl.textContent = 'Читаю ' + f.name + '…';
        var r = new FileReader();
        r.onload = function () { process(String(r.result), f.name); };
        r.readAsText(f, 'utf-8');
      }
    });
  });

  dlBtn.addEventListener('click', function () { download(false); });
  dlFlagBtn.addEventListener('click', function () { download(true); });

  pasteBtn.addEventListener('click', function () {
    var t = pasteArea.value.trim();
    if (!t) {
      statusEl.textContent = 'Вставьте текст плейлиста в поле выше';
      statusEl.className = 'status err';
      return;
    }
    process(t, 'playlist.m3u');
  });
})();
`;

const html = `<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Добавить страну в M3U-плейлист</title>
<style>
  :root { color-scheme: dark; }
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    font-family: 'Segoe UI', Roboto, Arial, sans-serif;
    background: #0b0f17; color: #eaf0fa;
    min-height: 100vh; padding: 32px 18px;
    display: flex; justify-content: center;
  }
  .wrap { width: min(760px, 100%); }
  h1 { font-size: 26px; margin-bottom: 8px; }
  .sub { color: #94a3b8; font-size: 15px; line-height: 1.55; margin-bottom: 22px; }
  .sub b { color: #cdd9ee; }
  #dropZone {
    border: 2px dashed #2c3852; border-radius: 14px;
    padding: 34px 20px; text-align: center; cursor: pointer;
    background: #121826; font-size: 17px; color: #94a3b8;
    transition: border-color .15s, background .15s;
  }
  #dropZone:hover, #dropZone.hot { border-color: #ffd54a; color: #eaf0fa; background: #1a2235; }
  #dropZone .big { font-size: 40px; display: block; margin-bottom: 10px; }
  #dropZone input { display: none; }
  .status { margin-top: 16px; font-size: 15px; font-weight: 600; color: #3ea6ff; min-height: 22px; }
  .status.ok { color: #6bdc8c; }
  .status.err { color: #ff7b7b; }
  .stats { margin-top: 6px; font-size: 14px; color: #94a3b8; }
  .actions { display: flex; gap: 12px; margin-top: 18px; flex-wrap: wrap; }
  button {
    font: inherit; font-weight: 700; font-size: 15px;
    padding: 12px 20px; border-radius: 10px; cursor: pointer;
    background: #3ea6ff; color: #06121f; border: none;
  }
  button.secondary { background: #1a2235; color: #eaf0fa; border: 2px solid #2c3852; }
  button:disabled { opacity: .4; cursor: not-allowed; }
  button:not(:disabled):hover { filter: brightness(1.1); }
  .label { display: block; font-size: 14px; font-weight: 700; color: #cdd9ee; margin: 26px 0 8px; }
  #preview {
    background: #0d1320; border: 1px solid #232c42; border-radius: 10px;
    padding: 14px; font-family: Consolas, monospace; font-size: 13px;
    white-space: pre-wrap; word-break: break-all; color: #b9c6dc;
    min-height: 60px; line-height: 1.6;
  }
  textarea {
    width: 100%; min-height: 120px; font-family: Consolas, monospace; font-size: 13px;
    background: #121826; color: #eaf0fa; border: 2px solid #2c3852;
    border-radius: 10px; padding: 12px; resize: vertical;
  }
  textarea:focus { outline: none; border-color: #ffd54a; }
  .note { margin-top: 26px; font-size: 13px; color: #5d6b85; line-height: 1.6; }
</style>
</head>
<body>
<div class="wrap">
  <h1>🏳️ Добавить страну в M3U-плейлист</h1>
  <div class="sub">
    Загрузите ваш <b>.m3u</b> файл — название страны будет дописано рядом с именем каждого канала:
    «BBC One <b>(Великобритания)</b>». Работает офлайн, файлы никуда не отправляются.
    EPG не ломается — привязка идёт по tvg-id, он не меняется.
  </div>

  <label id="dropZone" for="fileInput">
    <span class="big">📂</span>
    Нажмите, чтобы выбрать M3U-файл,<br>или перетащите его сюда
    <input id="fileInput" type="file" accept=".m3u,.m3u8,text/plain">
  </label>

  <div id="status" class="status"></div>
  <div id="stats" class="stats"></div>

  <div class="actions">
    <button id="dl" disabled>💾 Скачать результат</button>
    <button id="dlFlag" class="secondary" disabled>🚩 Скачать с флагом</button>
  </div>

  <span class="label">Как будет выглядеть (первые каналы):</span>
  <pre id="preview">— загрузите файл —</pre>

  <span class="label">Или вставьте текст плейлиста:</span>
  <textarea id="paste" placeholder="#EXTM3U&#10;#EXTINF:-1 tvg-id=&quot;BBCOne.uk&quot;,BBC One&#10;http://…"></textarea>
  <div class="actions"><button id="pasteBtn" class="secondary">Обработать вставленный текст</button></div>

  <div class="note">
    Страна определяется по атрибуту tvg-country, затем по коду в конце tvg-id
    (формат iptv-org, например .ru), затем по названию группы (group-title).
    Скрипт идемпотентен: повторная обработка не портит результат.
  </div>
</div>
<script>
${core}
</script>
<script>
${GLUE.replace('__DATA__', () => data)}
</script>
</body>
</html>
`;

writeFileSync(path.join(root, 'add-country.html'), html, 'utf8');
// копия в public/ — чтобы файл попал в сборку Vite и на GitHub Pages
writeFileSync(path.join(root, 'public', 'add-country.html'), html, 'utf8');
console.log('Готово → add-country.html и public/add-country.html (' + html.length + ' байт)');
