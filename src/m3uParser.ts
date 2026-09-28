import type { Channel } from './types';
import { countryFromCode, countryFromGroup } from './countries';

/**
 * Парсер M3U / M3U8 плейлистов.
 * Извлекает name, url, tvg-logo, tvg-country, group-title и т.д.
 */
export function parseM3U(content: string): Channel[] {
  const channels: Channel[] = [];
  const lines = content.split(/\r?\n/);

  let pendingAttrs: Record<string, string> | null = null;
  let pendingName = '';
  let id = 0;

  for (const raw of lines) {
    const line = raw.trim();
    if (!line) continue;

    if (line.startsWith('#EXTINF')) {
      pendingAttrs = {};
      // Формат: #EXTINF:-1 tvg-id="x" tvg-name="y" tvg-logo="z" group-title="g",Название канала
      const attrsPart = line.slice('#EXTINF'.length);
      const commaIdx = findTitleSeparator(attrsPart);
      const attrStr = commaIdx >= 0 ? attrsPart.slice(0, commaIdx) : attrsPart;
      pendingName = commaIdx >= 0 ? attrsPart.slice(commaIdx + 1).trim() : '';

      const attrRe = /([\w-]+)="([^"]*)"/g;
      let m: RegExpExecArray | null;
      while ((m = attrRe.exec(attrStr)) !== null) {
        pendingAttrs[m[1].toLowerCase()] = m[2];
      }
      continue;
    }

    if (line.startsWith('#')) continue; // прочие директивы (#EXTVLCOPT, #EXTGRP и т.п.)

    // Строка с URL
    if (pendingAttrs) {
      const attrs = pendingAttrs;
      const group = attrs['group-title'] || '';
      const code = attrs['tvg-country'] || attrs['country'] || attrs['tvg-country-code'];
      const info = countryFromCode(code) ?? countryFromGroup(group);

      const name = pendingName || attrs['tvg-name'] || line;
      channels.push({
        id: String(id++),
        name,
        group,
        logo: attrs['tvg-logo'] || attrs['logo'] || undefined,
        url: line,
        countryCode: undefined,
        countryName: info?.name,
        countryFlag: info?.flag,
        tvgId: attrs['tvg-id'],
        tvgName: attrs['tvg-name'],
      });
      pendingAttrs = null;
      pendingName = '';
    }
  }

  return channels;
}

/**
 * Находит разделитель между атрибутами и названием канала.
 * Названия могут содержать запятые, поэтому ищем последнюю запятую
 * после закрывающей кавычки атрибутов (или первую запятую, если атрибутов нет).
 */
function findTitleSeparator(s: string): number {
  let inQuotes = false;
  let lastQuoteEnd = -1;
  for (let i = 0; i < s.length; i++) {
    const ch = s[i];
    if (ch === '"') {
      inQuotes = !inQuotes;
      if (!inQuotes) lastQuoteEnd = i;
    } else if (ch === ',' && !inQuotes) {
      return i;
    }
  }
  void lastQuoteEnd;
  return -1;
}
