export interface CountryInfo {
  name: string;
  flag: string;
}

export interface CountriesData {
  countries: Record<string, CountryInfo>;
  groupToCountry: Record<string, string>;
  special: Record<string, CountryInfo>;
}

export interface ProcessStats {
  total: number;
  added: number;
  unchanged: number;
  unknown: number;
}

export declare function processPlaylist(
  text: string,
  data: CountriesData,
  opts?: { withFlag?: boolean }
): { text: string; stats: ProcessStats };

export declare function splitAttrsTitle(s: string): number;
export declare function parseAttrs(attrStr: string): Record<string, string>;
