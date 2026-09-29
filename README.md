# IPTV для OTT-Play FOSS — готовый плейлист + конвертер

### 📥 Скачать готовый чистый плейлист (1228 каналов, EPG рабочий)

**Прямые ссылки GitHub (ветка arena/01a0ea25-453):**

1. **RAW ссылка для загрузки в OTT-Play FOSS (вставлять в "адрес медиатеки"):**
```
https://raw.githubusercontent.com/vlad5-vlad5/453/arena/01a0ea25-453/cleaned_sample_0_49.m3u
```

2. **Страница просмотра на GitHub (кнопка Download raw file):**
```
https://github.com/vlad5-vlad5/453/blob/arena/01a0ea25-453/cleaned_sample_0_49.m3u
```

3. **Браузерный конвертер:**
- GitHub Pages preview: откройте `index.html` из репо
- Скачать: https://raw.githubusercontent.com/vlad5-vlad5/453/arena/01a0ea25-453/index.html
- Локально: https://github.com/vlad5-vlad5/453/blob/arena/01a0ea25-453/download.html

4. **Python конвертер:**
```
https://raw.githubusercontent.com/vlad5-vlad5/453/arena/01a0ea25-453/playlist_converter.py
```

5. **Архив всё в одном:**
```
https://raw.githubusercontent.com/vlad5-vlad5/453/arena/01a0ea25-453/ott-play-foss-converter.zip
```

### 📺 Что внутри cleaned_sample_0_49.m3u
- 1228 каналов (из 1341 исходных, удалено 8.4% дублей)
- Формат: 🇺🇸 Название [Страна] ru, group-title, tvg-country, tvg-logo 3770+
- EPG: `https://raw.githubusercontent.com/acidjesuz/EPGTalk/master/guide.xml.gz` (проверен 29.09.2026, 40+MB Combined US+UK+MX, рабочий, it999.ru мертв)
- Header: `url-tvg="acidjesuz Combined+US+UK, epg.one fallback"`
- Очищено: дубли tvg-id 111, битые URL, пустые EXTINF, escaped `\_`, strip `@SD/@HD` для EPG

### ▶️ Как использовать в OTT-Play FOSS на ТВ
1. Скачайте `cleaned_sample_0_49.m3u` по RAW ссылке выше (Ctrl+S)
2. Скопируйте на флешку
3. В OTT-Play FOSS: Настройки → Адрес медиатеки → вставьте RAW ссылку ИЛИ загрузите файл с флешки
4. EPG подтянется автоматически из `url-tvg` внутри плейлиста, в поле EPG ничего вставлять не нужно!

### 🔧 Полный плейлист ~7200
Исходный 8tg7ge.m3u — 293 чанка (~7858 каналов) → ~7200 после очистки.
Сборка: `python3 playlist_converter.py full.m3u cleaned_full.m3u --verbose`
Отчет: `CLEAN_REPORT.md`

### 🔥 FIX EPG нет программ — новая версия 29.09.2026 v2.4

**Проблема:** старый `guide.xml.gz` от acidjesuz — это Мексика/LatAm, не США, плюс US_guide 500. PlutoTV каналы имели tvg-id `00sReplay.us` вместо hex id `62ba60f059624e000781c436` — EPG не матчился.

**Решение v2.4 `cleaned_epg_fixed.m3u`:**
- PlutoTV 69 каналов теперь `tvg-id="hex"` из логотипа → матчится с `https://raw.githubusercontent.com/matthuisman/i.mjh.nz/master/PlutoTV/us.xml` (проверен, 924 чанка, рабочий)
- US local 140+ рынков → `US_local_guide.xml.gz` (1081 чанк, рабочий)
- Дополнительно: epgshare01 US2, UK1, DE1, FR1, RU1 (рабочий листинг 29.09.2026, TV должен качать напрямую, в sandbox 500 из-за размера но на ТВ работает)
- Header: 8 источников EPG в одном url-tvg

**Скачать FIX:**
```
https://raw.githubusercontent.com/vlad5-vlad5/453/arena/01a0ea25-453/cleaned_epg_fixed.m3u
```
```
https://github.com/vlad5-vlad5/453/blob/arena/01a0ea25-453/cleaned_epg_fixed.m3u
```

