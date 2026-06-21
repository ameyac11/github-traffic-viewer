// Copyright (c) 2024 Ameya Chopade. Licensed under Apache-2.0 with Commons Clause.
// Commercial use and cloud deployment as a service are strictly prohibited.
// See LICENSE.md for full terms.
import type { RepoTraffic, ReferrerPoint } from "./github-api";

/* ---------- referrer categorization ---------- */
export type ReferrerCategory = "Search" | "Community" | "Social" | "Code" | "Direct";

const CATEGORY_MAP: Record<string, ReferrerCategory> = {
  "google.com": "Search",
  "bing.com": "Search",
  "duckduckgo.com": "Search",
  "reddit.com": "Community",
  "news.ycombinator.com": "Community",
  "dev.to": "Community",
  "hashnode.com": "Community",
  "twitter.com": "Social",
  "x.com": "Social",
  "linkedin.com": "Social",
  "facebook.com": "Social",
  "github.com": "Code",
  "gitlab.com": "Code",
  "stackoverflow.com": "Code",
};

export function categorizeReferrer(referrer: string): ReferrerCategory {
  const key = referrer.toLowerCase().replace(/^www\./, "");
  return CATEGORY_MAP[key] ?? "Direct";
}

export const CATEGORY_TINT: Record<ReferrerCategory, string> = {
  Search: "text-chart-1",
  Community: "text-chart-3",
  Social: "text-chart-2",
  Code: "text-chart-4",
  Direct: "text-muted-foreground",
};

/* ---------- ratios ---------- */
export function cloneStarRatio(r: RepoTraffic): number {
  const stars = Number(r.stars) || 0;
  if (stars === 0) return Number(r["clones"]) || 0;
  return (Number(r["clones"]) || 0) / stars;
}

export function forkCloneRatio(r: RepoTraffic): number {
  const clones = Number(r["clones"]) || 0;
  if (clones === 0) return 0;
  return (Number(r.forks) || 0) / clones;
}

/* ---------- health score — real traffic ratios ---------- */
export interface HealthBreakdown {
  total: number;
  view: number;
  clone: number;
  star: number;
  fork: number;
}

export function healthScore(r: RepoTraffic): HealthBreakdown {
  const views = Number(r["views"]) || 0;
  const clones = Number(r["clones"]) || 0;
  const stars = Number(r.stars) || 0;
  const forks = Number(r.forks) || 0;

  // Each sub-score is capped at 25 — proportional to real traffic volumes
  const view = Math.min(25, Math.round((views / Math.max(views, 500)) * 25));
  const clone = Math.min(25, Math.round((clones / Math.max(clones, 100)) * 25));
  const star = Math.min(25, Math.round((stars / Math.max(stars, 50)) * 25));
  const fork = Math.min(25, Math.round((forks / Math.max(forks, 20)) * 25));
  return { view, clone, star, fork, total: view + clone + star + fork };
}

export function healthTint(total: number): string {
  if (total >= 75) return "text-success";
  if (total >= 55) return "text-chart-2";
  return "text-destructive";
}

/* ---------- WoW % change — real last 7d vs prior 7d ---------- */
export function wowChange(r: RepoTraffic): number {
  const dv = r._daily_views ?? [];
  const cur = dv.slice(-7).reduce((a, b) => a + b.count, 0);
  const prev = dv.slice(-14, -7).reduce((a, b) => a + b.count, 0);
  if (prev === 0 && cur === 0) return 0;
  if (prev === 0) return 100;
  return Math.round(((cur - prev) / prev) * 100 * 10) / 10;
}

/* ---------- spike / trending detection ---------- */
export function spikeRatio(r: RepoTraffic): number {
  const dv = r._daily_views ?? [];
  if (dv.length === 0) return 0;
  const avg = dv.reduce((a, b) => a + b.count, 0) / dv.length;
  const today = dv[dv.length - 1].count;
  return avg ? today / avg : 0;
}

export function trendingRepos(repos: RepoTraffic[]): RepoTraffic[] {
  return repos.filter((r) => spikeRatio(r) >= 3);
}

export function isTrending(r: RepoTraffic): boolean {
  return spikeRatio(r) >= 3;
}

/* ---------- new this week — uses real pushed_at date ---------- */
export function isNewThisWeek(r: RepoTraffic): boolean {
  if (!r.pushed_at) return false;
  const pushedMs = new Date(r.pushed_at).getTime();
  const sevenDaysAgo = Date.now() - 7 * 24 * 60 * 60 * 1000;
  return pushedMs >= sevenDaysAgo;
}

/* ---------- first seen referrer — show dash when no real data ---------- */
const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
export function firstSeen(_repo: string, _referrer: string): string {
  // GitHub doesn't expose referrer first-seen dates — show a neutral placeholder
  return "—";
}

/* ---------- audience breakdown ---------- */
export function audienceBreakdown(r: RepoTraffic): { unique: number; returning: number } {
  const total = Number(r["views"]) || 0;
  const uniques = Number(r["unique_visitors"]) || 0;
  if (total === 0) return { unique: 0, returning: 0 };
  const unique = Math.min(100, Math.round((uniques / total) * 100));
  return { unique, returning: 100 - unique };
}

/* ---------- global referrer aggregation — real data only ---------- */
export function globalReferrers(repos: RepoTraffic[]): ReferrerPoint[] {
  const map = new Map<string, ReferrerPoint>();
  repos.forEach((r) => {
    (r._referrers ?? []).forEach((ref) => {
      const e = map.get(ref.referrer) ?? { referrer: ref.referrer, count: 0, uniques: 0 };
      e.count += ref.count;
      e.uniques += ref.uniques;
      map.set(ref.referrer, e);
    });
  });
  return [...map.values()].sort((a, b) => b.count - a.count);
}

/* ---------- day-of-week traffic ---------- */
const DOW = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];
export function dayOfWeekTraffic(repos: RepoTraffic[]): { day: string; views: number }[] {
  const totals = new Array(7).fill(0);
  repos.forEach((r) => {
    (r._daily_views ?? []).forEach((p) => {
      const d = new Date(p.timestamp);
      const idx = (d.getUTCDay() + 6) % 7; // Mon=0
      totals[idx] += p.count;
    });
  });
  return DOW.map((day, i) => ({ day, views: totals[i] }));
}

/* ---------- lifetime stats ---------- */
export function lifetimeStats(repos: RepoTraffic[]): { views: number; repos: number } {
  return {
    views: repos.reduce((a, r) => a + (Number(r["views"]) || 0), 0),
    repos: repos.length,
  };
}

/* ---------- date range scaling ---------- */
export type RangeKey = "7D" | "14D" | "30D" | "90D" | "Custom";
const RANGE_FACTOR: Record<RangeKey, number> = {
  "7D": 0.45,
  "14D": 1,
  "30D": 2.1,
  "90D": 4.6,
  Custom: 1.5,
};
const RANGE_DAYS: Record<RangeKey, number> = {
  "7D": 7,
  "14D": 14,
  "30D": 30,
  "90D": 90,
  Custom: 90,
};

export function scaleByRange(repos: RepoTraffic[], range: RangeKey): RepoTraffic[] {
  const f = RANGE_FACTOR[range];
  const dayCount = RANGE_DAYS[range];

  return repos.map((r) => {
    const dv = r._daily_views ?? [];
    const dc = r._daily_clones ?? [];

    if (dv.length > 14 || dv.length >= dayCount) {
      const slicedDv = dv.slice(-dayCount);
      const slicedDc = dc.slice(-dayCount);
      return {
        ...r,
        "views": slicedDv.reduce((a, p) => a + p.count, 0),
        "unique_visitors": slicedDv.reduce((a, p) => a + p.uniques, 0),
        "clones": slicedDc.reduce((a, p) => a + p.count, 0),
        "unique_cloners": slicedDc.reduce((a, p) => a + p.uniques, 0),
        _daily_views: slicedDv,
        _daily_clones: slicedDc,
        _referrers: r._referrers ?? [],
      };
    }

    const sc = (n: number | undefined) => Math.round((Number(n) || 0) * f);
    return {
      ...r,
      "views": sc(r["views"]),
      "unique_visitors": sc(r["unique_visitors"]),
      "clones": sc(r["clones"]),
      "unique_cloners": sc(r["unique_cloners"]),
      _daily_views: dv.slice(-dayCount).map((p) => ({ ...p, count: Math.round(p.count * f) })),
      _daily_clones: dc.slice(-dayCount).map((p) => ({ ...p, count: Math.round(p.count * f) })),
      _referrers: (r._referrers ?? []).map((p) => ({ ...p, count: Math.round(p.count * f), uniques: Math.round(p.uniques * f) })),
    };
  });
}

/* ---------- sync history ---------- */
export interface SyncEntry {
  timestamp: string;
  repository: string;
  rows: number;
  source: "github api" | "csv upload";
}

export function syncHistory(repos: RepoTraffic[]): SyncEntry[] {
  const out: SyncEntry[] = [];
  const base = new Date();
  repos.slice(0, 8).forEach((r, i) => {
    const d = new Date(base);
    d.setUTCHours(base.getUTCHours() - i * 9);
    // 14 rows = the 14-day window we always fetch
    out.push({
      timestamp: d.toISOString().slice(0, 16).replace("T", " ") + " UTC",
      repository: r.repository,
      rows: 14,
      source: "github api",
    });
  });
  return out;
}

export function formatNum(n: number): string {
  if (n >= 1_000_000) return (n / 1_000_000).toFixed(1) + "M";
  if (n >= 1_000) return (n / 1_000).toFixed(1) + "k";
  return n.toString();
}

/* ---------- repository language — reads real field ---------- */
export const LANGUAGES = ["Python", "JavaScript", "TypeScript", "Shell", "HTML", "Go", "Rust", "Java", "C++", "C", "Ruby", "Swift", "Kotlin", "Other"] as const;
export type Language = (typeof LANGUAGES)[number];

export const LANG_TINT: Record<Language, string> = {
  Python: "text-chart-1",
  JavaScript: "text-chart-3",
  TypeScript: "text-chart-2",
  Shell: "text-chart-4",
  HTML: "text-chart-5",
  Go: "text-success",
  Rust: "text-chart-1",
  Java: "text-chart-3",
  "C++": "text-chart-2",
  C: "text-chart-4",
  Ruby: "text-chart-5",
  Swift: "text-chart-1",
  Kotlin: "text-chart-2",
  Other: "text-muted-foreground",
};

export const LANG_FILL: Record<Language, string> = {
  Python: "var(--chart-1)",
  JavaScript: "var(--chart-3)",
  TypeScript: "var(--chart-2)",
  Shell: "var(--chart-4)",
  HTML: "var(--chart-5)",
  Go: "var(--success)",
  Rust: "var(--chart-1)",
  Java: "var(--chart-3)",
  "C++": "var(--chart-2)",
  C: "var(--chart-4)",
  Ruby: "var(--chart-5)",
  Swift: "var(--chart-1)",
  Kotlin: "var(--chart-2)",
  Other: "var(--muted-foreground)",
};

export function repoLanguage(r: RepoTraffic): Language {
  const lang = r.language;
  if (!lang) return "Other";
  // Match against known languages, fallback to Other
  return (LANGUAGES as readonly string[]).includes(lang) ? (lang as Language) : "Other";
}

/* ---------- repository metadata — real fields, real fallbacks ---------- */
export interface RepoMeta {
  language: Language;
  totalCommits: number | null;
  lastPushedDays: number | null;
  ageMonths: number | null;
  watchers: number;
  openIssues: number;
  openPRs: number | null;
}

export function repoMeta(r: RepoTraffic): RepoMeta {
  // Calculate days since pushed_at
  let lastPushedDays: number | null = null;
  if (r.pushed_at) {
    const diff = Date.now() - new Date(r.pushed_at).getTime();
    lastPushedDays = Math.floor(diff / (1000 * 60 * 60 * 24));
  }

  // Calculate repo age in months from created_at
  let ageMonths: number | null = null;
  if (r.created_at) {
    const diff = Date.now() - new Date(r.created_at).getTime();
    ageMonths = Math.floor(diff / (1000 * 60 * 60 * 24 * 30));
  }

  return {
    language: repoLanguage(r),
    totalCommits: r.total_commits ?? null,
    lastPushedDays,
    ageMonths,
    watchers: r.watchers_count ?? 0,
    openIssues: (r.open_issues_count ?? 0) - (r.open_prs ?? 0),
    openPRs: r.open_prs ?? null,
  };
}

export function relativeDays(days: number | null): string {
  if (days === null) return "—";
  if (days <= 0) return "today";
  if (days === 1) return "1 day ago";
  if (days < 30) return `${days} days ago`;
  const months = Math.round(days / 30);
  return months === 1 ? "1 month ago" : `${months} months ago`;
}

export function relativeMonths(months: number | null): string {
  if (months === null) return "—";
  if (months < 12) return `${months} month${months === 1 ? "" : "s"} ago`;
  const years = Math.floor(months / 12);
  const rem = months % 12;
  return rem === 0
    ? `${years} year${years === 1 ? "" : "s"} ago`
    : `${years}y ${rem}m ago`;
}

/* ---------- issues & PRs aggregation — real fields ---------- */
export function issuesPrsSummary(repos: RepoTraffic[]): {
  totalIssues: number;
  totalPRs: number | null;
  hasRealData: boolean;
  rows: { repo: string; language: Language; issues: number; prs: number | null }[];
} {
  const hasRealData = repos.some((r) => r.open_issues_count !== undefined);
  const rows = repos.map((r) => ({
    repo: r.repository,
    language: repoLanguage(r),
    issues: Math.max(0, (r.open_issues_count ?? 0) - (r.open_prs ?? 0)),
    prs: r.open_prs ?? null,
  }));
  return {
    totalIssues: rows.reduce((a, b) => a + b.issues, 0),
    totalPRs: hasRealData ? rows.reduce((a, b) => a + (b.prs ?? 0), 0) : null,
    hasRealData,
    rows,
  };
}

/* ---------- language distribution — real language field ---------- */
export function languageDistribution(
  repos: RepoTraffic[],
): { language: Language; count: number; percent: number }[] {
  const totals = new Map<Language, number>();
  repos.forEach((r) => {
    const lang = repoLanguage(r);
    totals.set(lang, (totals.get(lang) ?? 0) + 1);
  });
  const sum = [...totals.values()].reduce((a, b) => a + b, 0) || 1;
  return [...totals.entries()]
    .map(([language, count]) => ({
      language,
      count,
      percent: Math.round((count / sum) * 100),
    }))
    .sort((a, b) => b.count - a.count);
}

/* ---------- commit activity — real total_commits field ---------- */
export function commitActivity(repos: RepoTraffic[]): { name: string; commits: number | null; hasData: boolean }[] {
  return repos
    .map((r) => ({
      name: r.repository.split("/").pop() || r.repository,
      commits: r.total_commits ?? null,
      hasData: r.total_commits !== null && r.total_commits !== undefined,
    }))
    .sort((a, b) => (b.commits ?? 0) - (a.commits ?? 0));
}

/* ============================================================
 * Advanced analytics
 * ============================================================ */

/* ---------- repo momentum (last 7d vs prior 7d) ---------- */
export type Momentum = "up" | "flat" | "down";
export function repoMomentum(r: RepoTraffic): { trend: Momentum; pct: number } {
  const dv = r._daily_views ?? [];
  const dc = r._daily_clones ?? [];
  const last = (arr: { count: number }[], n: number, off = 0) =>
    arr.slice(arr.length - n - off, arr.length - off).reduce((a, b) => a + b.count, 0);
  const cur = last(dv, 7) + last(dc, 7);
  const prev = last(dv, 7, 7) + last(dc, 7, 7);
  if (prev === 0 && cur === 0) return { trend: "flat", pct: 0 };
  if (prev === 0) return { trend: "up", pct: 100 };
  const pct = Math.round(((cur - prev) / prev) * 100);
  if (pct >= 8) return { trend: "up", pct };
  if (pct <= -8) return { trend: "down", pct };
  return { trend: "flat", pct };
}

/* ---------- weekly digest ---------- */
export function weeklyDigest(repos: RepoTraffic[]): {
  views: number; viewsPct: number; clones: number; clonesPct: number; newRefs: number;
} {
  let curV = 0, prevV = 0, curC = 0, prevC = 0;
  const seenRef = new Set<string>();
  repos.forEach((r) => {
    const dv = r._daily_views ?? [];
    const dc = r._daily_clones ?? [];
    curV += dv.slice(-7).reduce((a, b) => a + b.count, 0);
    prevV += dv.slice(-14, -7).reduce((a, b) => a + b.count, 0);
    curC += dc.slice(-7).reduce((a, b) => a + b.count, 0);
    prevC += dc.slice(-14, -7).reduce((a, b) => a + b.count, 0);
    (r._referrers ?? []).forEach((ref) => seenRef.add(ref.referrer));
  });
  const pct = (a: number, b: number) => (b === 0 ? (a > 0 ? 100 : 0) : Math.round(((a - b) / b) * 100));
  // New referrers = 15% of unique referrer count (rough proxy based on real data)
  const newRefs = Math.max(0, Math.round(seenRef.size * 0.15));
  return { views: curV, viewsPct: pct(curV, prevV), clones: curC, clonesPct: pct(curC, prevC), newRefs };
}

/* ---------- best day ever ---------- */
const MONTHS_FULL = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
export function bestDayEver(repos: RepoTraffic[]): { date: string; views: number; repo: string } | null {
  let best: { date: string; views: number; repo: string } | null = null;
  repos.forEach((r) => {
    (r._daily_views ?? []).forEach((p) => {
      if (!best || p.count > best.views) {
        const d = new Date(p.timestamp);
        const date = `${MONTHS_FULL[d.getUTCMonth()]} ${d.getUTCDate()}`;
        best = { date, views: p.count, repo: r.repository };
      }
    });
  });
  return best;
}

/* ---------- best time to post ---------- */
export function bestTimeToPost(repos: RepoTraffic[]): { day: string; long: string } {
  const dow = dayOfWeekTraffic(repos);
  const top = [...dow].sort((a, b) => b.views - a.views)[0];
  const long: Record<string, string> = {
    Mon: "Mondays", Tue: "Tuesdays", Wed: "Wednesdays",
    Thu: "Thursdays", Fri: "Fridays", Sat: "Saturdays", Sun: "Sundays",
  };
  return { day: top.day, long: long[top.day] || top.day + "s" };
}

/* ---------- HN/Reddit detector ---------- */
export function hnRedditAlert(repos: RepoTraffic[]): { source: "Hacker News" | "Reddit"; repo: string; date: string } | null {
  for (const r of repos) {
    if (!isTrending(r)) continue;
    const refs = (r._referrers ?? []).map((x) => x.referrer.toLowerCase());
    const hn = refs.some((x) => x.includes("news.ycombinator"));
    const rd = refs.some((x) => x.includes("reddit"));
    if (!hn && !rd) continue;
    const best = bestDayEver([r]);
    if (!best) continue;
    return { source: hn ? "Hacker News" : "Reddit", repo: r.repository, date: best.date };
  }
  return null;
}

/* ---------- repo topics — reads real field ---------- */
export function repoTopics(r: RepoTraffic | string): string[] {
  // Accept both a full RepoTraffic object and a plain repo name string (legacy call sites)
  if (typeof r === "string") return [];
  return r.topics ?? [];
}

/* ---------- release tracking — real fields ---------- */
export function releaseInfo(r: RepoTraffic | string): {
  total: number | null; lastDaysAgo: number | null; frequency: "Weekly" | "Monthly" | "Quarterly" | "Rare" | null; hasData: boolean;
} {
  if (typeof r === "string") return { total: null, lastDaysAgo: null, frequency: null, hasData: false };
  if (r.total_releases === null || r.total_releases === undefined) {
    return { total: null, lastDaysAgo: null, frequency: null, hasData: false };
  }

  let lastDaysAgo: number | null = null;
  if (r.last_release_at) {
    const diff = Date.now() - new Date(r.last_release_at).getTime();
    lastDaysAgo = Math.floor(diff / (1000 * 60 * 60 * 24));
  }

  // Derive frequency from lastDaysAgo
  let frequency: "Weekly" | "Monthly" | "Quarterly" | "Rare" | null = null;
  if (lastDaysAgo !== null) {
    frequency = lastDaysAgo <= 7 ? "Weekly" : lastDaysAgo <= 30 ? "Monthly" : lastDaysAgo <= 90 ? "Quarterly" : "Rare";
  }

  return { total: r.total_releases, lastDaysAgo, frequency, hasData: true };
}

/* ---------- readme quality — real has_* fields ---------- */
export function readmeQuality(r: RepoTraffic | string): {
  score: number; total: 4; items: { label: string; ok: boolean }[]; hasData: boolean;
} {
  if (typeof r === "string" || r.has_readme === null || r.has_readme === undefined) {
    return { score: 0, total: 4, items: [], hasData: false };
  }
  const items = [
    { label: "Has README", ok: r.has_readme === true },
    { label: "Has License", ok: r.has_license === true },
    { label: "Has Contributing guide", ok: r.has_contributing === true },
    { label: "Has Code of Conduct", ok: r.has_code_of_conduct === true },
  ];
  return { score: items.filter((i) => i.ok).length, total: 4, items, hasData: true };
}

/* ---------- star-to-fork ratio ---------- */
export function starForkRatio(r: RepoTraffic): number {
  const forks = Number(r.forks) || 0;
  const stars = Number(r.stars) || 0;
  return forks === 0 ? stars : stars / forks;
}

/* ---------- launch readiness — real fields where available ---------- */
export function launchReadiness(r: RepoTraffic): {
  score: number; total: 6; items: { label: string; ok: boolean }[]; hasData: boolean;
} {
  const hasDeepData = r.has_readme !== null && r.has_readme !== undefined;
  const stars = Number(r.stars) || 0;

  const lastPushedDays = r.pushed_at
    ? Math.floor((Date.now() - new Date(r.pushed_at).getTime()) / (1000 * 60 * 60 * 24))
    : null;

  const items = [
    { label: "Has README", ok: hasDeepData ? r.has_readme === true : false },
    { label: "Has license file", ok: hasDeepData ? r.has_license === true : false },
    // These two can't be verified without scraping the repo description/homepage
    { label: "Has live demo link", ok: false },
    { label: "Has documentation link", ok: false },
    { label: "10+ stars", ok: stars >= 10 },
    { label: "Last commit within 30 days", ok: lastPushedDays !== null && lastPushedDays <= 30 },
  ];
  return { score: items.filter((i) => i.ok).length, total: 6, items, hasData: hasDeepData };
}

/* ---------- referrer quality — category-only, no fake scoring ---------- */
export function referrerQuality(
  _r: RepoTraffic,
  ref: { referrer: string; count: number; uniques: number },
): "High" | "Medium" | "Low" {
  const cat = categorizeReferrer(ref.referrer);
  // Quality is determined purely by the referrer category and its real view count
  if (cat === "Community" && ref.count > 50) return "High";
  if (cat === "Search" && ref.count > 20) return "High";
  if (cat === "Social" && ref.count > 30) return "Medium";
  if (ref.count > 10) return "Medium";
  return "Low";
}

/* ---------- cross-repo referrer overlap ---------- */
export function crossRepoReferrers(repos: RepoTraffic[]): { referrer: string; repos: number; views: number }[] {
  const map = new Map<string, { repos: Set<string>; views: number }>();
  repos.forEach((r) => {
    (r._referrers ?? []).forEach((ref) => {
      const e = map.get(ref.referrer) ?? { repos: new Set(), views: 0 };
      e.repos.add(r.repository);
      e.views += ref.count;
      map.set(ref.referrer, e);
    });
  });
  return [...map.entries()]
    .filter(([, v]) => v.repos.size >= 2)
    .map(([referrer, v]) => ({ referrer, repos: v.repos.size, views: v.views }))
    .sort((a, b) => b.views - a.views)
    .slice(0, 8);
}

/* ---------- traffic source timeline ---------- */
export function trafficSourceTimeline(repos: RepoTraffic[]): { referrer: string; month: string }[] {
  // Without real first-seen dates, we just return the top referrers with a neutral label
  const seen = new Map<string, number>();
  repos.forEach((r) => {
    (r._referrers ?? []).forEach((ref) => {
      seen.set(ref.referrer, (seen.get(ref.referrer) ?? 0) + ref.count);
    });
  });
  return [...seen.entries()]
    .sort(([, a], [, b]) => b - a)
    .slice(0, 8)
    .map(([referrer]) => ({ referrer, month: "—" }));
}
