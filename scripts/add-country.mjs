#!/usr/bin/env node
/**
 * add-country.mjs — добавляет название страны рядом с названием канала
 * в M3U-плейлисте:  «Название канала (Россия)»
 *
 * Страна определяется по (в порядке приоритета):
 *   1. атрибутам tvg-country / country в строке #EXTINF
 *   2. суффиксу tvg-id (формат iptv-org: «BBCOne.uk» → .uk → Великобритания)
 *   3. названию группы group-title («Россия», «Ukraine», «News» → спец.метки)
 *
 * Использование:
 *   node scripts/add-country.mjs вход.m3u [выход.m3u] [--flag]
 *
 *   без выходного файла результат пишется в <вход>_со_странами.m3u
 *   --flag  — добавить флаг: «Название (🇷🇺 Россия)»
 *
 * Скрипт идемпотентен: повторный запуск не дублирует страну.
 * EPG не ломается — привязка идёт по tvg-id, он не изменяется.
 */
import { readFileSync, writeFileSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const root = path.join(path.dirname(fileURLToPath(import.meta.url)), '..');
const data = JSON.parse(
  readFileSync(path.join(root, 'shared', 'countries.json'), 'utf8')
);
const { countries, groupToCountry, special } = data;

const withFlag = process.argv.includes('--flag');
const args = process.argv.slice(2).filter((a) => !a.startsWith('--'));

if (args.length < 1) {
  console.error('Использование: node scripts/add-country.mjs вход.m3u [выход.m3u] [--flag]');
  process.exit(1);
}

const inputPath = args[0];
const outputPath =
  args[1] ??
  inputPath.replace(/(\.m3u8?)?$/i, (m) => `_со_странами${m || '.m3u'}`);

/** Коды, отличающиеся от ISO (iptv-org пишет .uk, не .gb) */
const CODE_ALIASES = { UK: 'GB', EL: 'GR' };

/** Группы-категории, которые НЕ являются странами */
const NOT_COUNTRY = new Set([
  'KIDS', 'MUSIC', 'CINEMA', 'SPORT', 'NEWS', 'DOC', 'ENT',
  'INT', 'WORLD', 'EUR', 'AFR', 'ASIA', 'LATAM',
]);

/** ISO-код → «🇷🇺 Россия» / «Россия» */
function countryByCode(code) {
  if (!code) return null;
  let first = code.split(/[,\s]+/)[0]?.trim().toUpperCase();
  if (!first) return null;
  first = CODE_ALIASES[first] ?? first;
  return countries[first] ?? null;
}

/** Название группы → страна (категории вроде «News» игнорируются) */
// Сначала — точное совпадение, затем самые длинные ключи,
// чтобы «Ukraine» не сматчивалось на короткий «uk» (→ GB)
const GROUP_ENTRIES = Object.entries(groupToCountry).sort(
  (a, b) => b[0].length - a[0].length
);

function countryByGroup(group) {
  if (!group) return null;
  const key = group.trim().toLowerCase();
  const direct = groupToCountry[key];
  if (direct) return resolveMapped(direct);
  for (const [k, v] of GROUP_ENTRIES) {
    if (key.includes(k)) return resolveMapped(v);
  }
  return null;
}

function resolveMapped(code) {
  if (NOT_COUNTRY.has(code)) return null;
  return special[code] ?? countries[code] ?? null;
}

/** tvg-id вида «BBCOne.uk» → «Великобритания» */
function countryByTvgId(tvgId) {
  if (!tvgId) return null;
  const m = /\.([A-Za-z]{2})$/.exec(tvgId.trim());
  if (!m) return null;
  return countryByCode(m[1]);
}

/** Разделитель между атрибутами и названием (запятая вне кавычек) */
function splitAttrsTitle(s) {
  let inQuotes = false;
  for (let i = 0; i < s.length; i++) {
    const ch = s[i];
    if (ch === '"') inQuotes = !inQuotes;
    else if (ch === ',' && !inQuotes) return i;
  }
  return -1;
}

/** Строка #EXTINF уже содержит нашу приписку? */
function alreadyHasCountry(title, info) {
  if (!info) return false;
  const suffix = ` (${info.name})`;
  if (title.endsWith(suffix)) return true;
  return title.endsWith(` (${info.flag} ${info.name})`);
}

function parseAttrs(attrStr) {
  const attrs = {};
  const re = /([\w-]+)="([^"]*)"/g;
  let m;
  while ((m = re.exec(attrStr)) !== null) attrs[m[1].toLowerCase()] = m[2];
  return attrs;
}

function processLine(line) {
  if (!line.startsWith('#EXTINF')) return { line, changed: false, skipped: false };

  const body = line.slice('#EXTINF'.length);
  const cut = splitAttrsTitle(body);
  const attrStr = cut >= 0 ? body.slice(0, cut) : body;
  let title = cut >= 0 ? body.slice(cut + 1) : '';
  const attrs = parseAttrs(attrStr);

  const info =
    countryByCode(attrs['tvg-country'] || attrs['country'] || attrs['tvg-country-code']) ??
    countryByTvgId(attrs['tvg-id']) ??
    countryByGroup(attrs['group-title']);

  if (!info) return { line, changed: false, skipped: true };
  if (alreadyHasCountry(title, info)) return { line, changed: false, skipped: false };

  const suffix = withFlag ? ` (${info.flag} ${info.name})` : ` (${info.name})`;
  title = title.trimEnd();
  const rebuilt = `#EXTINF${attrStr},${title}${suffix}`;
  return { line: rebuilt, changed: true, skipped: false };
}

const content = readFileSync(inputPath, 'utf8');
const lines = content.split(/\r?\n/);
let changed = 0;
let skipped = 0;

const out = lines.map((raw) => {
  if (!raw.startsWith('#EXTINF')) return raw;
  const res = processLine(raw);
  if (res.changed) changed++;
  if (res.skipped) skipped++;
  return res.line;
});

writeFileSync(outputPath, out.join('\n'), 'utf8');

const total = lines.filter((l) => l.startsWith('#EXTINF')).length;
console.log(`Каналов всего:            ${total}`);
console.log(`Страна добавлена:         ${changed}`);
console.log(`Уже была (без изменений): ${total - changed - skipped}`);
console.log(`Страна не распознана:     ${skipped}`);
console.log(`Готово → ${outputPath}`);
