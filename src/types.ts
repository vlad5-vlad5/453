export interface Channel {
  id: string;
  name: string;
  group: string;
  logo?: string;
  url: string;
  /** Код страны (ISO) из атрибута tvg-country или group-title */
  countryCode?: string;
  /** Название страны на русском */
  countryName?: string;
  /** Флаг страны (emoji) */
  countryFlag?: string;
  tvgId?: string;
  tvgName?: string;
}