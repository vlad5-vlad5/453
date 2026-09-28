import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import Hls from 'hls.js';
import type { Channel } from './types';
import { parseM3U } from './m3uParser';
import { COUNTRIES } from './countries';
import { processPlaylist } from '../scripts/core-logic.cjs';
import countriesData from '../shared/countries.json';

const STORAGE_KEY = 'iptv-playlist-url';

/** Имя файла для скачивания результата */
function outputName(name: string): string {
  return name.replace(/(\.m3u8?)?$/i, (m) => `_со_странами${m || '.m3u'}`);
}

/**
 * Загрузка текста плейлиста: напрямую, а при CORS/HTTP-ограничениях —
 * через публичный прокси (частые M3U-хосты не отдают CORS-заголовки).
 */
async function fetchPlaylistText(url: string): Promise<string> {
  const direct = async () => {
    const res = await fetch(url);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return res.text();
  };
  const viaProxy = async () => {
    const res = await fetch(
      `https://api.allorigins.win/raw?url=${encodeURIComponent(url)}`
    );
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return res.text();
  };

  // Страница на https не может тянуть http-плейлисты напрямую (mixed content)
  const isMixed =
    window.location.protocol === 'https:' && /^http:\/\//i.test(url);
  if (isMixed) return viaProxy();

  try {
    return await direct();
  } catch {
    return viaProxy();
  }
}

function loadFromStorage(): string {
  try {
    return localStorage.getItem(STORAGE_KEY) ?? '';
  } catch {
    return '';
  }
}

export default function App() {
  const [channels, setChannels] = useState<Channel[]>([]);
  const [search, setSearch] = useState('');
  const [activeGroup, setActiveGroup] = useState('all');
  const [focusIndex, setFocusIndex] = useState(0);
  const [current, setCurrent] = useState<Channel | null>(null);
  const [playing, setPlaying] = useState(false);
  const [error, setError] = useState('');
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [urlInput, setUrlInput] = useState(loadFromStorage);
  const [loadingPlaylist, setLoadingPlaylist] = useState(false);
  const [status, setStatus] = useState('');
  const [zapVisible, setZapVisible] = useState(false);
  const [rawPlaylist, setRawPlaylist] = useState<string | null>(null);
  const [sourceName, setSourceName] = useState('playlist.m3u');
  const [downloadNote, setDownloadNote] = useState('');

  const listRef = useRef<HTMLUListElement>(null);
  const zapTimer = useRef<number>();

  const groups = useMemo(() => {
    const set = new Set<string>();
    for (const c of channels) if (c.group) set.add(c.group);
    return [...set].sort((a, b) => a.localeCompare(b, 'ru'));
  }, [channels]);

  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase();
    return channels.filter((c) => {
      if (activeGroup !== 'all' && c.group !== activeGroup) return false;
      if (!q) return true;
      return (
        c.name.toLowerCase().includes(q) ||
        (c.countryName ?? '').toLowerCase().includes(q) ||
        (c.group ?? '').toLowerCase().includes(q)
      );
    });
  }, [channels, search, activeGroup]);

  useEffect(() => {
    if (focusIndex >= filtered.length) setFocusIndex(Math.max(0, filtered.length - 1));
  }, [filtered.length, focusIndex]);

  // Прокрутка списка к сфокусированному элементу
  useEffect(() => {
    const el = listRef.current?.children[focusIndex] as HTMLElement | undefined;
    el?.scrollIntoView({ block: 'nearest' });
  }, [focusIndex]);

  const showZap = useCallback(() => {
    setZapVisible(true);
    window.clearTimeout(zapTimer.current);
    zapTimer.current = window.setTimeout(() => setZapVisible(false), 4000);
  }, []);

  const selectChannel = useCallback(
    (ch: Channel) => {
      setCurrent(ch);
      setPlaying(true);
      setError('');
      showZap();
    },
    [showZap]
  );

  /** Следующий/предыдущий канал (перемотка каналов) */
  const zap = useCallback(
    (dir: 1 | -1) => {
      if (!filtered.length) return;
      const idx = current ? filtered.findIndex((c) => c.id === current.id) : -1;
      const next = idx >= 0 ? idx + dir : dir === 1 ? 0 : filtered.length - 1;
      const wrapped = (next + filtered.length) % filtered.length;
      setFocusIndex(wrapped);
      selectChannel(filtered[wrapped]);
    },
    [filtered, current, selectChannel]
  );

  /** Загрузка плейлиста по URL */
  const loadUrl = useCallback(async (rawUrl?: string) => {
    const url = (rawUrl ?? '').trim();
    if (!url) {
      setStatus('');
      return;
    }
    setLoadingPlaylist(true);
    setStatus('Загрузка плейлиста…');
    setError('');
    try {
      const text = (await fetchPlaylistText(url)).replace(/^\uFEFF/, '');
      const parsed = parseM3U(text);
      if (!parsed.length) throw new Error('в файле не найдено ни одного канала');
      setChannels(parsed);
      setRawPlaylist(text);
      setSourceName('playlist.m3u');
      setFocusIndex(0);
      setCurrent(null);
      setPlaying(false);
      localStorage.setItem(STORAGE_KEY, url);
      setStatus(`Загружено каналов: ${parsed.length}`);
      setSettingsOpen(false);
    } catch (e) {
      setStatus('');
      setError(`Не удалось загрузить плейлист: ${e instanceof Error ? e.message : e}`);
    } finally {
      setLoadingPlaylist(false);
    }
  }, []);

  /** Загрузка плейлиста из локального файла */
  const loadFile = useCallback(async (file: File) => {
    setLoadingPlaylist(true);
    setStatus(`Читаю ${file.name}…`);
    setError('');
    try {
      const text = (await file.text()).replace(/^\uFEFF/, '');
      const parsed = parseM3U(text);
      if (!parsed.length) throw new Error('в файле не найдено ни одного канала');
      setChannels(parsed);
      setRawPlaylist(text);
      setSourceName(file.name);
      setFocusIndex(0);
      setCurrent(null);
      setPlaying(false);
      setStatus(`Загружено каналов: ${parsed.length}`);
      setSettingsOpen(false);
    } catch (e) {
      setStatus('');
      setError(`Не удалось прочитать файл: ${e instanceof Error ? e.message : e}`);
    } finally {
      setLoadingPlaylist(false);
    }
  }, []);

  /** Скачать M3U с названиями стран в именах каналов */
  const downloadPlaylist = useCallback(
    (withFlag: boolean) => {
      if (!rawPlaylist) return;
      const { text, stats } = processPlaylist(rawPlaylist, countriesData, { withFlag });
      const blob = new Blob(['\uFEFF' + text], { type: 'audio/x-mpegurl' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = outputName(sourceName);
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.setTimeout(() => URL.revokeObjectURL(url), 5000);
      const note = `Сохранено: ${a.download} — страна добавлена у ${stats.added} из ${stats.total} каналов`;
      setDownloadNote(note);
      setStatus(note);
      window.setTimeout(() => setDownloadNote(''), 6000);
    },
    [rawPlaylist, sourceName]
  );

  // Автозагрузка сохранённого URL при старте
  useEffect(() => {
    const saved = loadFromStorage();
    if (saved) void loadUrl(saved);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  /** Навигация с пульта / клавиатуры */
  useEffect(() => {
    const onKeyDown = (e: KeyboardEvent) => {
      const target = e.target as HTMLElement | null;
      const inInput =
        target &&
        (target.tagName === 'INPUT' || target.tagName === 'TEXTAREA' || target.isContentEditable);

      if (settingsOpen) {
        if (e.key === 'Escape' || e.key === 'Backspace') {
          if (!inInput || e.key === 'Escape') {
            e.preventDefault();
            setSettingsOpen(false);
          }
        }
        return;
      }

      switch (e.key) {
        case 'ArrowDown':
        case 'ArrowUp': {
          if (inInput) return;
          e.preventDefault();
          const dir = e.key === 'ArrowDown' ? 1 : -1;
          // Если ничего не играет — листаем список; во время просмотра перематываем каналы
          if (playing && current) {
            zap(dir as 1 | -1);
          } else {
            setFocusIndex((i) => Math.min(Math.max(0, i + dir), Math.max(0, filtered.length - 1)));
          }
          break;
        }
        case 'ArrowRight':
          if (!inInput && playing) {
            e.preventDefault();
            zap(1);
          }
          break;
        case 'ArrowLeft':
          if (!inInput && playing) {
            e.preventDefault();
            zap(-1);
          }
          break;
        case 'PageDown': // Channel+
          e.preventDefault();
          zap(1);
          break;
        case 'PageUp': // Channel-
          e.preventDefault();
          zap(-1);
          break;
        case 'Enter':
        case ' ': {
          if (inInput) return;
          e.preventDefault();
          const ch = filtered[focusIndex];
          if (ch) selectChannel(ch);
          break;
        }
        case 'Backspace':
        case 'Escape': {
          if (inInput && e.key === 'Backspace') return;
          e.preventDefault();
          if (playing) {
            setPlaying(false);
          } else {
            setFocusIndex(0);
          }
          break;
        }
        case 'm':
        case 'M':
        case 'ь':
        case 'Ь': {
          if (inInput) return;
          const v = document.querySelector('video');
          if (v) v.muted = !v.muted;
          break;
        }
        default:
          break;
      }
    };

    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, [filtered, focusIndex, playing, current, zap, selectChannel, settingsOpen]);

  const currentIndex = current ? filtered.findIndex((c) => c.id === current.id) : -1;
  const channelNumber = currentIndex >= 0 ? currentIndex + 1 : 0;

  return (
    <div className="app">
      <aside className="sidebar">
        <div className="sidebar-header">
          <div className="logo">
            <span className="tv-icon">📺</span>
            <span>Мировое ТВ</span>
          </div>
          <input
            className="search-input"
            type="search"
            placeholder="🔍 Канал или страна…"
            value={search}
            onChange={(e) => {
              setSearch(e.target.value);
              setFocusIndex(0);
            }}
          />
        </div>

        <div className="groups-row">
          <button
            className={`group-chip ${activeGroup === 'all' ? 'active' : ''}`}
            onClick={() => setActiveGroup('all')}
          >
            Все ({channels.length})
          </button>
          {groups.map((g) => (
            <button
              key={g}
              className={`group-chip ${activeGroup === g ? 'active' : ''}`}
              onClick={() => setActiveGroup(g)}
            >
              {g}
            </button>
          ))}
        </div>

        <ul className="channel-list" ref={listRef}>
          {filtered.length === 0 && (
            <div className="empty-state">
              {channels.length === 0 ? (
                <>
                  Плейлист пуст.
                  <br />
                  Нажмите «Плейлист», чтобы загрузить M3U файл или ссылку.
                </>
              ) : (
                'Ничего не найдено. Попробуйте другой запрос.'
              )}
            </div>
          )}
          {filtered.map((ch, i) => (
            <li
              key={ch.id}
              className={[
                'channel-item',
                current?.id === ch.id ? 'active' : '',
                i === focusIndex ? 'focused' : '',
              ]
                .filter(Boolean)
                .join(' ')}
              onClick={() => {
                setFocusIndex(i);
                selectChannel(ch);
              }}
            >
              {ch.logo ? (
                <img
                  className="channel-logo"
                  src={ch.logo}
                  alt=""
                  loading="lazy"
                  onError={(e) => {
                    (e.target as HTMLImageElement).style.display = 'none';
                  }}
                />
              ) : (
                <div className="channel-logo placeholder">📺</div>
              )}
              <div className="channel-info">
                <div className="channel-name">{ch.name}</div>
                {ch.countryName ? (
                  <div className="channel-country">
                    <span className="flag">{ch.countryFlag}</span>
                    <span className="country-name">{ch.countryName}</span>
                  </div>
                ) : (
                  <div className="channel-country no-country">страна не указана</div>
                )}
              </div>
            </li>
          ))}
        </ul>
      </aside>

      <main className="player-area">
        <div className="video-wrap">
          <VideoPlayer
            channel={current}
            playing={playing}
            onError={setError}
            onPlaying={() => setError('')}
          />

          {!playing && !current && (
            <div className="center-hint">
              <div className="big-icon">🎬</div>
              <div>
                {channels.length > 0
                  ? 'Выберите канал и нажмите OK'
                  : 'Загрузите плейлист, чтобы смотреть ТВ'}
              </div>
            </div>
          )}

          {playing && current && (zapVisible || error) && (
            <div className="zap-overlay">
              <div className="zap-number">
                Канал {channelNumber > 0 ? channelNumber : ''} {current.group ? `· ${current.group}` : ''}
              </div>
              <div className="zap-name">{current.name}</div>
              <div className="zap-country">
                <span className="flag">{current.countryFlag ?? '🏳️'}</span>
                <span>{current.countryName ?? 'Страна не указана'}</span>
              </div>
            </div>
          )}

          {error && <div className="error-banner">⚠️ {error}</div>}
        </div>

        <div className="controls">
          <button className="ctrl-btn primary" onClick={() => zap(-1)}>
            ⬆︎ Канал −
          </button>
          <button className="ctrl-btn primary" onClick={() => zap(1)}>
            Канал + ⬇︎
          </button>
          <button
            className="ctrl-btn"
            onClick={() => {
              setPlaying(false);
              setCurrent(null);
            }}
          >
            ⏹ Стоп
          </button>
          <button className="ctrl-btn" onClick={() => setSettingsOpen(true)}>
            📋 Плейлист
          </button>
          <button
            className="ctrl-btn"
            disabled={!rawPlaylist}
            onClick={() => downloadPlaylist(false)}
            title="Скачать M3U с названием страны рядом с именем каждого канала"
          >
            💾 Со странами
          </button>
          <button
            className="ctrl-btn"
            disabled={!rawPlaylist}
            onClick={() => downloadPlaylist(true)}
            title="То же самое, но с флагом страны"
          >
            🚩 С флагом
          </button>
          <div className="spacer" />
          {downloadNote ? (
            <div className="hint download-note">{downloadNote}</div>
          ) : (
            <div className="hint">
              <b>↑↓</b> каналы <b>OK</b> смотреть <b>Esc</b> назад <b>M</b> звук
            </div>
          )}
        </div>
      </main>

      {settingsOpen && (
        <div className="modal-backdrop" onClick={() => setSettingsOpen(false)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <h2>Плейлист</h2>
            <div className="sub">
              Загрузите M3U/M3U8 плейлист — по ссылке или из файла. Рядом с каждым каналом будет
              название его страны (из атрибута tvg-country или группы).
            </div>

            <label className="field-label" htmlFor="url-input">
              Ссылка на плейлист (URL)
            </label>
            <input
              id="url-input"
              className="field-input"
              placeholder="https://example.com/playlist.m3u"
              value={urlInput}
              onChange={(e) => setUrlInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter') void loadUrl(urlInput);
              }}
            />

            <label className="file-drop">
              <input
                type="file"
                accept=".m3u,.m3u8,application/x-mpegURL"
                onChange={(e) => {
                  const f = e.target.files?.[0];
                  if (f) void loadFile(f);
                }}
              />
              📂 Или нажмите, чтобы выбрать локальный .m3u файл
            </label>

            {status && <div className="status-line">{status}</div>}
            {error && <div className="status-line error">{error}</div>}

            <div className="modal-actions">
              <button
                className="ctrl-btn primary"
                disabled={loadingPlaylist}
                onClick={() => void loadUrl(urlInput)}
              >
                {loadingPlaylist ? 'Загрузка…' : 'Загрузить по ссылке'}
              </button>
              <button className="ctrl-btn" onClick={() => setSettingsOpen(false)}>
                Закрыть
              </button>
            </div>

            <label className="field-label">Доступные страны в справочнике</label>
            <div className="sub">
              {Object.values(COUNTRIES).length} стран — от {COUNTRIES['RU'].flag}{' '}
              {COUNTRIES['RU'].name} до {COUNTRIES['US'].flag} {COUNTRIES['US'].name}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

/** Видеоплеер с поддержкой HLS (hls.js) и нативных mp4/m3u8 */
function VideoPlayer({
  channel,
  playing,
  onError,
  onPlaying,
}: {
  channel: Channel | null;
  playing: boolean;
  onError: (msg: string) => void;
  onPlaying: () => void;
}) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const hlsRef = useRef<Hls | null>(null);

  useEffect(() => {
    const video = videoRef.current;
    if (!video || !channel || !playing) return;

    const url = channel.url;
    const isHls = /\.m3u8($|\?)/i.test(url) || url.includes('m3u8');

    const cleanup = () => {
      hlsRef.current?.destroy();
      hlsRef.current = null;
      video.removeAttribute('src');
      video.load();
    };
    cleanup();

    const onErr = () => onError(`Не удалось воспроизвести «${channel.name}»`);

    if (isHls && Hls.isSupported()) {
      const hls = new Hls({ enableWorker: true, lowLatencyMode: false });
      hlsRef.current = hls;
      hls.on(Hls.Events.ERROR, (_e, data) => {
        if (data.fatal) {
          onErr();
          hls.destroy();
          hlsRef.current = null;
        }
      });
      hls.on(Hls.Events.MANIFEST_PARSED, () => {
        video.play().catch(() => undefined);
      });
      hls.loadSource(url);
      hls.attachMedia(video);
    } else {
      video.src = url;
      video.addEventListener('error', onErr);
      video.play().catch(() => undefined);
    }

    const handlePlaying = () => onPlaying();
    video.addEventListener('playing', handlePlaying);

    return () => {
      video.removeEventListener('error', onErr);
      video.removeEventListener('playing', handlePlaying);
      cleanup();
    };
  }, [channel, playing, onError, onPlaying]);

  return <video ref={videoRef} playsInline controls={false} />;
}
