#!/usr/bin/env node
/**
 * add-country.mjs — добавляет название страны рядом с названием канала
 * в M3U-плейлисте:  «Название канала (Россия)»
 *
 * Использование:
 *   node scripts/add-country.mjs вход.m3u [выход.m3u] [--flag]
 *
 *   без выходного файла результат пишется в <вход>_со_странами.m3u
 *   --flag  — добавить флаг: «Название (🇷🇺 Россия)»
 *
 * Вся логика — в scripts/core-logic.js (общая с сайтом и standalone-HTML).
 * Идемпотентно; EPG не ломается (tvg-id не меняется).
 */
import { readFileSync, writeFileSync } from 'node:fs';
import path from 'node:path';
import { createRequire } from 'node:module';
import { fileURLToPath } from 'node:url';

const require = createRequire(import.meta.url);
const { processPlaylist } = require('./core-logic.cjs');

const root = path.join(path.dirname(fileURLToPath(import.meta.url)), '..');
const data = JSON.parse(
  readFileSync(path.join(root, 'shared', 'countries.json'), 'utf8')
);

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

const input = readFileSync(inputPath, 'utf8');
const { text, stats } = processPlaylist(input, data, { withFlag });
writeFileSync(outputPath, text, 'utf8');

console.log(`Каналов всего:            ${stats.total}`);
console.log(`Страна добавлена:         ${stats.added}`);
console.log(`Уже была (без изменений): ${stats.unchanged}`);
console.log(`Страна не распознана:     ${stats.unknown}`);
console.log(`Готово → ${outputPath}`);
