/**
 * core-logic.js — ядро обработки M3U: добавление названия страны
 * в имя канала. Работает и в Node (require), и в браузере (<script>).
 *
 * processPlaylist(text, data, { withFlag }) -> { text, stats }
 *   data = { countries, groupToCountry, special }  (shared/countries.json)
 *   stats = { total, added, unchanged, unknown }
 *
 * Страна определяется по (в порядке приоритета):
 *   1. tvg-country / country / tvg-country-code
 *   2. суффиксу tvg-id («BBCOne.uk» → Великобритания), алиас UK→GB
 *   3. group-title (самые длинные ключи первыми, категории не берём)
 */
(function (root, factory) {
  const api = factory();
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  else root.AddCountry = api;
})(typeof self !== 'undefined' ? self : this, function () {
  'use strict';

  const CODE_ALIASES = { UK: 'GB', EL: 'GR' };

  /** Группы-категории, которые НЕ являются странами */
  const NOT_COUNTRY = new Set([
    'KIDS', 'MUSIC', 'CINEMA', 'SPORT', 'NEWS', 'DOC', 'ENT',
    'INT', 'WORLD', 'EUR', 'AFR', 'ASIA', 'LATAM',
  ]);

  function splitAttrsTitle(s) {
    let inQuotes = false;
    for (let i = 0; i < s.length; i++) {
      const ch = s[i];
      if (ch === '"') inQuotes = !inQuotes;
      else if (ch === ',' && !inQuotes) return i;
    }
    return -1;
  }

  function parseAttrs(attrStr) {
    const attrs = {};
    const re = /([\w-]+)="([^"]*)"/g;
    let m;
    while ((m = re.exec(attrStr)) !== null) attrs[m[1].toLowerCase()] = m[2];
    return attrs;
  }

  function makeHelpers(data) {
    const { countries, groupToCountry, special } = data;

    const groupEntries = Object.entries(groupToCountry).sort(
      (a, b) => b[0].length - a[0].length
    );

    function byCode(code) {
      if (!code) return null;
      let first = code.split(/[,\s]+/)[0];
      if (!first) return null;
      first = CODE_ALIASES[first.trim().toUpperCase()] ?? first.trim().toUpperCase();
      return countries[first] ?? null;
    }

    function resolveMapped(code) {
      if (NOT_COUNTRY.has(code)) return null;
      return special[code] ?? countries[code] ?? null;
    }

    function byGroup(group) {
      if (!group) return null;
      const key = group.trim().toLowerCase();
      const direct = groupToCountry[key];
      if (direct) return resolveMapped(direct);
      for (const [k, v] of groupEntries) {
        if (key.includes(k)) return resolveMapped(v);
      }
      return null;
    }

    function byTvgId(tvgId) {
      if (!tvgId) return null;
      const m = /\.([A-Za-z]{2})$/.exec(String(tvgId).trim());
      if (!m) return null;
      return byCode(m[1]);
    }

    function findCountry(attrs) {
      return (
        byCode(attrs['tvg-country'] || attrs['country'] || attrs['tvg-country-code']) ??
        byTvgId(attrs['tvg-id']) ??
        byGroup(attrs['group-title'])
      );
    }

    return { findCountry };
  }

  function alreadyHas(title, info) {
    if (!info) return false;
    return (
      title.endsWith(' (' + info.name + ')') ||
      title.endsWith(' (' + info.flag + ' ' + info.name + ')')
    );
  }

  /**
   * Возвращает новый текст плейлиста со страной в именах каналов.
   * Идемпотентно: уже обработанные строки не меняются.
   */
  function processPlaylist(text, data, opts) {
    const withFlag = !!(opts && opts.withFlag);
    const { findCountry } = makeHelpers(data);
    const lines = text.split(/\r?\n/);
    let total = 0;
    let added = 0;
    let unknown = 0;

    const out = lines.map(function (raw) {
      if (!raw.startsWith('#EXTINF')) return raw;
      total++;
      const body = raw.slice('#EXTINF'.length);
      const cut = splitAttrsTitle(body);
      const attrStr = cut >= 0 ? body.slice(0, cut) : body;
      let title = cut >= 0 ? body.slice(cut + 1) : '';
      const attrs = parseAttrs(attrStr);
      const info = findCountry(attrs);
      if (!info) {
        unknown++;
        return raw;
      }
      if (alreadyHas(title, info)) {
        return raw;
      }
      const suffix = withFlag ? ' (' + info.flag + ' ' + info.name + ')' : ' (' + info.name + ')';
      title = title.replace(/\s+$/, '');
      added++;
      return '#EXTINF' + attrStr + ',' + title + suffix;
    });

    return {
      text: out.join('\n'),
      stats: { total: total, added: added, unchanged: total - added - unknown, unknown: unknown },
    };
  }

  return { processPlaylist: processPlaylist, splitAttrsTitle: splitAttrsTitle, parseAttrs: parseAttrs };
});
