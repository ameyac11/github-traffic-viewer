import { useEffect, useMemo, useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { LogOut, Loader2, AlertCircle, ExternalLink, FileSpreadsheet, Link as LinkIcon, Database } from "lucide-react";
import { toast } from "sonner";
import {
  fetchTraffic,
  downloadCsv,
  MAIN_REPO_URL,
  AUTOMATION_REPO_URL,
  type AuthResult,
  type RepoTraffic,
} from "@/lib/github-api";
import { scaleByRange, trendingRepos, repoTopics, type RangeKey } from "@/lib/analytics";
import { DEMO_DATA } from "@/lib/demo-data";
import { MetricsGrid } from "./MetricsGrid";
import { TrafficCharts } from "./TrafficCharts";
import { RepoTable } from "./RepoTable";
import { CloneLeaderboard } from "./CloneLeaderboard";
import { DashboardToolbar, type ViewMode } from "./DashboardToolbar";
import { SpikeBanner } from "./SpikeBanner";
import { LifetimeHero } from "./LifetimeHero";
import { GlobalReferrers } from "./GlobalReferrers";
import { TrafficHeatmap } from "./TrafficHeatmap";
import { ExportHistory } from "./ExportHistory";
import { ExportOverlay } from "./ExportOverlay";
import { KeyboardHelp } from "./KeyboardHelp";
import { CumulativeGrowth } from "./CumulativeGrowth";
import { Wordmark } from "./Wordmark";
import { TopNavPills } from "./TopNavPills";
import { loadRepoFilter, saveRepoFilter } from "./RepoFilter";
import { IssuesPrsCard } from "./IssuesPrsCard";
import { LanguageDistribution } from "./LanguageDistribution";
import { CommitActivity } from "./CommitActivity";
import { ExportModal } from "./ExportModal";
import { CardModal, type CardProfile } from "./CardModal";
import { WeeklyDigestCard } from "./WeeklyDigestCard";
import { BestDayCard } from "./BestDayCard";
import { BestTimeCard } from "./BestTimeCard";
import { HnRedditBanner } from "./HnRedditBanner";

const VIEW_MODE_KEY = "gitlytics-view-mode";
const HN_DISMISS_KEY = "gitlytics-hn-dismissed";

const DEFAULT_AVATAR = "/gitlytics-logo.png";

type Source =
  | { mode: "api"; auth: AuthResult; token: string }
  | { mode: "csv"; data: RepoTraffic[] };

function buildCardProfile(source: Source): CardProfile {
  if (source.mode === "api") {
    return {
      name: source.auth.name || source.auth.username,
      username: source.auth.username,
      avatar_url: source.auth.avatar_url || DEFAULT_AVATAR,
      bio: (source.auth as any).bio || undefined,
      location: (source.auth as any).location || undefined,
      followers: (source.auth as any).followers ?? 0,
      following: (source.auth as any).following ?? 0,
    };
  }
  // CSV / Demo: derive owner from first repo "owner/repo"
  const first = source.data[0]?.repository ?? "gitlytics/repo";
  const owner = first.split("/")[0] || "gitlytics";
  const isDemo = source.data === DEMO_DATA || (source.data && source.data.length > 0 && source.data[0]?.repository === "ameyac11/gitlytics");

  if (isDemo) {
    return {
      name: "Gitlytics",
      username: "gitlytics",
      avatar_url: "/gitlytics-logo.png",
      bio: "Demo profile — exploring Gitlytics with sample data.",
      location: "San Francisco",
      followers: 12480,
      following: 9,
    };
  }

  return {
    name: owner === "ameyac11" ? "Ameya Chopade" : owner === "octocat" ? "Gitlytics" : owner,
    username: owner === "octocat" ? "gitlytics" : owner,
    avatar_url: owner === "octocat" ? "/gitlytics-logo.png" : `https://github.com/${owner}.png`,
    bio: owner === "ameyac11" ? "Building Gitlytics · Developer" : "Demo profile — exploring Gitlytics with sample data.",
    location: owner === "ameyac11" ? "India" : "San Francisco",
    followers: owner === "ameyac11" ? 1420 : 12480,
    following: owner === "ameyac11" ? 82 : 9,
  };
}

export function DashboardView({
  source,
  onLogout,
}: {
  source: Source;
  onLogout: () => void;
}) {
  const isApi = source.mode === "api";

  const query = useQuery({
    queryKey: ["traffic", isApi ? (source as any).auth.username : "csv"],
    queryFn: () => fetchTraffic((source as any).token),
    staleTime: 60_000,
    enabled: isApi,
  });

  const owner = useMemo(() => {
    if (isApi) return (source as any).auth.username;
    const first = (source as any).data[0]?.repository ?? "gitlytics/repo";
    return first.split("/")[0] || "gitlytics";
  }, [source, isApi]);

  const isDemo = !isApi && (source.data === DEMO_DATA || (source.data && source.data.length > 0 && source.data[0]?.repository === "ameyac11/gitlytics"));
  const showFetchProfile = !isApi && !isDemo && owner !== "octocat";

  const profileQuery = useQuery({
    queryKey: ["github-profile", owner],
    queryFn: async () => {
      const res = await fetch(`https://api.github.com/users/${owner}`);
      if (!res.ok) throw new Error("Failed to fetch public profile");
      return res.json();
    },
    enabled: showFetchProfile,
    staleTime: 5 * 60_000,
  });

  const rawData: RepoTraffic[] = isApi ? (query.data ?? []) : (source as any).data;
  const isLoading = isApi && query.isLoading;
  const isError = isApi && query.isError;
  const cardProfile = useMemo(() => {
    const base = buildCardProfile(source);
    if (!isApi && profileQuery.data) {
      return {
        name: profileQuery.data.name || profileQuery.data.login,
        username: profileQuery.data.login,
        avatar_url: profileQuery.data.avatar_url,
        bio: profileQuery.data.bio || undefined,
        location: profileQuery.data.location || undefined,
        followers: profileQuery.data.followers || 0,
        following: profileQuery.data.following || 0,
      };
    }
    return base;
  }, [source, isApi, profileQuery.data]);

  const [search, setSearch] = useState("");
  const [topN, setTopN] = useState(10);
  const [range, setRange] = useState<RangeKey>("14D");
  const [customFrom, setCustomFrom] = useState("");
  const [customTo, setCustomTo] = useState("");
  const [bannerDismissed, setBannerDismissed] = useState(false);
  const [hnDismissed, setHnDismissed] = useState(false);
  const [showExport, setShowExport] = useState(false);
  const [showCard, setShowCard] = useState(false);
  const [viewMode, setViewModeState] = useState<ViewMode>("basic");
  const [topicFilter, setTopicFilter] = useState<string | null>(null);
  const [selectedRepos, setSelectedRepos] = useState<string[]>([]);
  const [exportMode, setExportMode] = useState<"png" | "pdf">("png");
  const searchRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    try {
      const v = localStorage.getItem(VIEW_MODE_KEY);
      if (v === "basic" || v === "advanced") setViewModeState(v);
      if (localStorage.getItem(HN_DISMISS_KEY) === "1") setHnDismissed(true);
      setSelectedRepos(loadRepoFilter());
    } catch {
      /* ignore */
    }
  }, []);

  function setViewMode(v: ViewMode) {
    setViewModeState(v);
    try {
      localStorage.setItem(VIEW_MODE_KEY, v);
    } catch {
      /* ignore */
    }
  }

  function dismissHn() {
    setHnDismissed(true);
    try {
      localStorage.setItem(HN_DISMISS_KEY, "1");
    } catch {
      /* ignore */
    }
  }

  function copyLink() {
    try {
      navigator.clipboard.writeText(window.location.href);
      toast.success("Link copied", { duration: 3000 });
    } catch {
      toast.error("Copy failed");
    }
  }

  const advanced = viewMode === "advanced";

  const data = useMemo(() => scaleByRange(rawData, range), [rawData, range]);

  const filtered = useMemo(() => {
    const byName = data.filter((r) => r.repository.toLowerCase().includes(search.toLowerCase()));
    const byTopic = topicFilter
      ? byName.filter((r) => (r.topics ?? []).includes(topicFilter))
      : byName;
    if (selectedRepos.length === 0) return byTopic;
    const set = new Set(selectedRepos);
    return byTopic.filter((r) => set.has(r.repository));
  }, [data, search, topicFilter, selectedRepos]);

  const allRepoNames = useMemo(() => data.map((r) => r.repository), [data]);
  const repoLabel =
    selectedRepos.length === 0 || selectedRepos.length === allRepoNames.length
      ? "All repos"
      : selectedRepos.length === 1
        ? selectedRepos[0]
        : `${selectedRepos.length} repos`;

  function applyRepos(next: string[]) {
    setSelectedRepos(next);
    saveRepoFilter(next);
  }

  async function runWithRepos(repos: string[], fn: () => Promise<void>) {
    const prev = selectedRepos;
    setSelectedRepos(repos);
    // wait for React to commit + charts to re-render
    await new Promise((r) => setTimeout(r, 700));
    try {
      await fn();
    } finally {
      setSelectedRepos(prev);
    }
  }

  function resetFilters() {
    setSearch("");
    setTopN(10);
    setRange("14D");
    setTopicFilter(null);
    setSelectedRepos([]);
    saveRepoFilter([]);
    toast.success("Filters reset", { duration: 2000 });
  }

  // Keyboard shortcuts
  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      const tag = (e.target as HTMLElement)?.tagName;
      const inField = tag === "INPUT" || tag === "TEXTAREA";
      if (e.key === "Escape") {
        setShowExport(false);
        setShowCard(false);
        return;
      }
      if (inField) return;
      if (e.key === "e" || e.key === "E") {
        e.preventDefault();
        setShowExport(true);
      } else if (e.key === "b" || e.key === "B") {
        e.preventDefault();
        setViewMode(viewMode === "basic" ? "advanced" : "basic");
      } else if (e.key === "r" || e.key === "R") {
        e.preventDefault();
        resetFilters();
      } else if (e.key === "/") {
        e.preventDefault();
        searchRef.current?.focus();
      }
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [viewMode]);

  const trending = useMemo(() => trendingRepos(data), [data]);

  return (
    <div className="min-h-screen">
      <header className="glass sticky top-0 z-10 border-b border-border">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-4 py-3 sm:px-6">
          <div className="flex items-center gap-2.5">
            <img
              src="/gitlytics-logo.png"
              alt="Gitlytics logo"
              className="h-9 w-9 object-contain"
            />
            <div className="leading-tight">
              <p className="text-sm font-semibold"><Wordmark /></p>
              <div className="flex flex-wrap items-center gap-x-3 gap-y-0.5 text-xs text-muted-foreground">
                <a
                  href={MAIN_REPO_URL}
                  target="_blank"
                  rel="noreferrer"
                  className="flex items-center gap-1 hover:text-primary"
                >
                  dashboard
                  <ExternalLink className="h-3 w-3" />
                </a>
                <a
                  href={AUTOMATION_REPO_URL}
                  target="_blank"
                  rel="noreferrer"
                  className="flex items-center gap-1 hover:text-primary"
                >
                  automation
                  <ExternalLink className="h-3 w-3" />
                </a>
              </div>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <div className="flex items-center gap-2.5 border-r border-border/50 pr-3">
              <img
                src={cardProfile.avatar_url}
                alt={cardProfile.name}
                crossOrigin="anonymous"
                onError={(e) => {
                  (e.currentTarget as HTMLImageElement).src = DEFAULT_AVATAR;
                }}
                className="h-8 w-8 rounded-full ring-1 ring-primary/40"
              />
              <div className="hidden text-right leading-tight sm:block">
                <p className="text-sm font-medium">
                  {cardProfile.name}
                </p>
                <p className="text-xs text-muted-foreground">
                  @{cardProfile.username}
                </p>
              </div>
            </div>

            {isApi ? (
              <span className="hidden items-center gap-1.5 rounded-lg bg-orange-500/10 px-2.5 py-1 text-xs font-medium text-orange-500 ring-1 ring-orange-500/25 sm:flex">
                <Database className="h-3.5 w-3.5" />
                Live API
              </span>
            ) : source.mode === "csv" && (source.data === DEMO_DATA || (source.data && source.data.length > 0 && source.data[0]?.repository === "ameyac11/gitlytics")) ? (
              <span className="hidden items-center gap-1.5 rounded-lg bg-foreground/10 px-2.5 py-1 text-xs font-medium text-foreground ring-1 ring-foreground/25 sm:flex">
                <FileSpreadsheet className="h-3.5 w-3.5" />
                Demo
              </span>
            ) : (
              <span className="hidden items-center gap-1.5 rounded-lg bg-green-500/10 px-2.5 py-1 text-xs font-medium text-green-500 ring-1 ring-green-500/25 sm:flex">
                <FileSpreadsheet className="h-3.5 w-3.5" />
                CSV Mode
              </span>
            )}

            <div className="ml-2 flex items-center gap-2.5">
              <TopNavPills className="hidden md:flex" />
              <button
                onClick={onLogout}
                className="flex items-center gap-1.5 rounded-lg border border-input bg-background/40 px-3 py-1.5 text-xs font-medium transition-all hover:scale-[1.02] hover:bg-destructive/15 hover:text-destructive"
              >
                <LogOut className="h-3.5 w-3.5" />
                <span className="hidden sm:inline">Reset</span>
              </button>
            </div>
          </div>
        </div>
      </header>

      <main id="dashboard-root" className="mx-auto max-w-7xl space-y-6 px-4 py-6 sm:px-6">
        {isLoading && (
          <div className="flex flex-col items-center justify-center gap-3 py-32 text-muted-foreground">
            <Loader2 className="h-7 w-7 animate-spin text-primary" />
            <p className="text-sm">Loading your traffic data…</p>
          </div>
        )}

        {isError && (
          <div className="glass mx-auto flex max-w-md flex-col items-center gap-3 rounded-xl p-8 text-center">
            <AlertCircle className="h-8 w-8 text-destructive" />
            <p className="text-sm text-muted-foreground">
              {query.error instanceof Error ? query.error.message : "Failed to load data."}
            </p>
            <button
              onClick={() => query.refetch()}
              className="rounded-lg bg-primary px-4 py-2 text-sm font-semibold text-primary-foreground transition-transform hover:scale-[1.02]"
            >
              Try again
            </button>
          </div>
        )}

        {!isLoading && !isError && data.length > 0 && (
          <>
            {advanced && !hnDismissed && <HnRedditBanner repos={data} onDismiss={dismissHn} />}
            {!bannerDismissed && trending.length > 0 && (
              <SpikeBanner repos={trending} onDismiss={() => setBannerDismissed(true)} />
            )}
            <DashboardToolbar
              query={search}
              setQuery={setSearch}
              searchRef={searchRef}
              topN={topN}
              setTopN={setTopN}
              maxN={Math.min(30, filtered.length)}
              range={range}
              setRange={setRange}
              customFrom={customFrom}
              setCustomFrom={setCustomFrom}
              customTo={customTo}
              setCustomTo={setCustomTo}
              onDownload={() => downloadCsv(filtered, repoLabel)}
              onExportPng={() => { setExportMode("png"); setShowExport(true); }}
              onExportPdf={() => { setExportMode("pdf"); setShowExport(true); }}
              onCreateCard={() => setShowCard(true)}
              onReload={() => query.refetch()}
              reloading={isApi && query.isFetching}
              canReload={isApi}
              viewMode={viewMode}
              setViewMode={setViewMode}
              topic={topicFilter}
              onClearTopic={() => setTopicFilter(null)}
              allRepos={allRepoNames}
              selectedRepos={selectedRepos}
              onSelectedReposChange={applyRepos}
            />
            {advanced && (
              <div id="section-weekly-digest">
                <WeeklyDigestCard repos={filtered} />
              </div>
            )}
            <div id="section-hero">
              <LifetimeHero repos={filtered} />
            </div>
            {advanced && (
              <div id="section-best-day">
                <BestDayCard repos={filtered} />
              </div>
            )}
            {advanced && (
              <div id="section-issues-prs">
                <IssuesPrsCard repos={filtered} />
              </div>
            )}
            <div id="section-stat-cards">
              <MetricsGrid repos={filtered} />
            </div>
            <div id="section-top10-charts">
              <TrafficCharts repos={filtered} topN={topN} />
            </div>
            {advanced && (
              <div id="section-referrer-aggregation">
                <GlobalReferrers repos={filtered} advanced />
              </div>
            )}
            {advanced && (
              <div id="section-heatmap" className="space-y-3">
                <TrafficHeatmap repos={filtered} />
                <BestTimeCard repos={filtered} />
              </div>
            )}
            {advanced && (
              <div id="section-languages">
                <LanguageDistribution repos={filtered} />
              </div>
            )}
            {advanced && (
              <div id="section-commits">
                <CommitActivity repos={filtered} isApi={isApi} />
              </div>
            )}
            {advanced && (
              <div id="section-cumulative-growth">
                <CumulativeGrowth repos={filtered} />
              </div>
            )}
            <div id="section-most-cloned">
              <CloneLeaderboard repos={filtered} />
            </div>
            <div id="section-all-repos">
              <RepoTable
                repos={filtered}
                advanced={advanced}
                onTopic={(t) => setTopicFilter(t)}
              />
            </div>
            <div id="section-export-history">
              <ExportHistory />
            </div>
          </>
        )}

        {showExport && (
          <ExportModal
            onClose={() => setShowExport(false)}
            mode={exportMode}
            allRepos={allRepoNames}
            defaultRepos={selectedRepos.length === 0 ? allRepoNames : selectedRepos}
            runWithRepos={runWithRepos}
            profile={cardProfile}
          />
        )}
        {showCard && (
          <CardModal
            profile={cardProfile}
            repos={filtered}
            onClose={() => setShowCard(false)}
          />
        )}


        {!isLoading && !isError && data.length === 0 && (
          <div className="glass mx-auto max-w-md rounded-xl p-10 text-center text-muted-foreground">
            No repository traffic data available.
          </div>
        )}
      </main>
      <ExportOverlay />
      <KeyboardHelp />
    </div>
  );
}
