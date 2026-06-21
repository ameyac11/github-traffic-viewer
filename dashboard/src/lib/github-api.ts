// Copyright (c) 2024 Ameya Chopade. Licensed under Apache-2.0 with Commons Clause.
// Commercial use and cloud deployment as a service are strictly prohibited.
// See LICENSE.md for full terms.
export const API_BASE = "http://localhost:8000";
import { exportFilename, appendHistory } from "./export-history";

export const MAIN_REPO_URL = "https://github.com/ameyac11/gitlytics";

export const AUTOMATION_REPO_URL =
  "https://github.com/ameyac11/gitlytics-github-traffic-automation";

export interface AuthResult {
  authenticated: boolean;
  username: string;
  name: string;
  avatar_url: string;
}

export interface DailyPoint {
  timestamp: string;
  count: number;
  uniques: number;
}

export interface ReferrerPoint {
  referrer: string;
  count: number;
  uniques: number;
}

export interface PathPoint {
  path: string;
  title: string;
  count: number;
  uniques: number;
}

export interface RepoTraffic {
  repository: string;
  is_private: boolean;
  stars: number;
  forks: number;
  views: number;
  unique_visitors: number;
  clones: number;
  unique_cloners: number;
  top_referrer?: string;
  top_referrer_views?: number;
  top_path?: string;
  top_path_views?: number;
  fetched_at?: string;
  // Repo metadata — available in Live API and Username modes
  language?: string | null;
  topics?: string[];
  watchers_count?: number;
  open_issues_count?: number;
  pushed_at?: string | null;
  created_at?: string | null;
  // Deep stats — only available for top 20 repos in Live API mode
  total_commits?: number | null;
  open_prs?: number | null;
  total_releases?: number | null;
  last_release_at?: string | null;
  has_readme?: boolean | null;
  has_license?: boolean | null;
  has_contributing?: boolean | null;
  has_code_of_conduct?: boolean | null;
  _daily_views?: DailyPoint[];
  _daily_clones?: DailyPoint[];
  _referrers?: ReferrerPoint[];
  _paths?: PathPoint[];
}

export interface BackendConfig {
  has_token: boolean;
  has_data_dir: boolean;
}

export async function getBackendConfig(): Promise<BackendConfig> {
  const res = await fetch(`${API_BASE}/api/config`);
  if (!res.ok) throw new Error("Failed to fetch backend config.");
  return res.json() as Promise<BackendConfig>;
}

export async function authenticate(token: string): Promise<AuthResult> {
  const res = await fetch(`${API_BASE}/api/auth`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ token }),
  });
  if (!res.ok) {
    throw new Error(
      `Authentication failed (${res.status}). Check your token and that the backend is running.`,
    );
  }
  const data = (await res.json()) as AuthResult;
  if (!data.authenticated) throw new Error("Invalid GitHub token.");
  return data;
}

export async function fetchTraffic(token: string): Promise<RepoTraffic[]> {
  const res = await fetch(`${API_BASE}/api/traffic`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ token }),
  });
  if (!res.ok) {
    throw new Error(`Failed to load traffic data (${res.status}).`);
  }
  return (await res.json()) as RepoTraffic[];
}

export async function uploadCsv(file: File): Promise<RepoTraffic[]> {
  const form = new FormData();
  form.append("file", file);
  const res = await fetch(`${API_BASE}/api/upload-csv`, {
    method: "POST",
    body: form,
  });
  if (!res.ok) {
    throw new Error(`Failed to process CSV (${res.status}). Make sure the file format is correct.`);
  }
  return (await res.json()) as RepoTraffic[];
}

/**
 * Fixed canonical CSV schema. Every export uses exactly these columns.
 */
const CSV_COLUMNS = [
  "date",
  "repository",
  "is_private",
  "views",
  "unique_visitors",
  "clones",
  "unique_cloners",
  "stars",
  "forks",
  "top_referrer",
  "top_referrer_views",
  "top_referrer_uniques",
  "top_path",
  "top_path_views",
  "top_path_uniques",
  "_raw_referrers",
  "_raw_paths",
] as const;

function csvDate(r: RepoTraffic): string {
  if (r["fetched_at"]) return String(r["fetched_at"]).slice(0, 10);
  return new Date().toISOString().slice(0, 10);
}

export async function downloadCsv(
  repos: RepoTraffic[],
  repoLabel = "All repos",
) {
  const filename = exportFilename("csv");
  const escape = (v: unknown) => {
    const s = v === undefined || v === null ? "" : String(v);
    return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
  };
  const header = CSV_COLUMNS.join(",");
  const rows = repos.map((r) => {
    const topRef = r._referrers?.[0];
    const topPath = r._paths?.[0];
    const map: Record<(typeof CSV_COLUMNS)[number], unknown> = {
      date: csvDate(r),
      repository: r.repository,
      is_private: r.is_private ? "true" : "false",
      views: r["views"] ?? "",
      unique_visitors: r["unique_visitors"] ?? "",
      clones: r["clones"] ?? "",
      unique_cloners: r["unique_cloners"] ?? "",
      stars: r.stars ?? "",
      forks: r.forks ?? "",
      top_referrer: r["top_referrer"] ?? topRef?.referrer ?? "",
      top_referrer_views: r["top_referrer_views"] ?? topRef?.count ?? "",
      top_referrer_uniques: topRef?.uniques ?? "",
      top_path: r["top_path"] ?? topPath?.path ?? "",
      top_path_views: r["top_path_views"] ?? topPath?.count ?? "",
      top_path_uniques: topPath?.uniques ?? "",
      _raw_referrers: r._referrers ? JSON.stringify(r._referrers) : "",
      _raw_paths: r._paths ? JSON.stringify(r._paths) : "",
    };
    return CSV_COLUMNS.map((c) => escape(map[c])).join(",");
  });
  const csv = [header, ...rows].join("\n");
  const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
  appendHistory({ action: "Download CSV", repos: repoLabel, filename });
}
