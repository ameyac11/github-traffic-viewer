import { useEffect, useMemo, useState } from "react";
import {
  LogOut, Link as LinkIcon, Lock, ExternalLink, Star, GitFork, Package,
  Users, MapPin, Calendar, Globe, Award, Loader2, User,
} from "lucide-react";
import { toast } from "sonner";
import type { PublicProfile, PublicRepo } from "@/lib/github-public";
import { publicReposToTraffic } from "@/lib/github-public";
import { repoLanguage, LANG_TINT } from "@/lib/analytics";
import { LanguagePill } from "./LanguagePill";
import { TopicTags } from "./TopicTags";
import {
  LaunchReadinessCard, ReadmeQualityCard, StarForkRatioCard,
} from "./DeepDiveAdvanced";
import { DashboardToolbar, type ViewMode } from "./DashboardToolbar";
import { CardModal, type CardProfile } from "./CardModal";
import { ExportModal } from "./ExportModal";
import { CommitActivity } from "./CommitActivity";
import { LanguageDistribution } from "./LanguageDistribution";
import { ExportHistory } from "./ExportHistory";
import { ExportOverlay } from "./ExportOverlay";
import { KeyboardHelp } from "./KeyboardHelp";
import { Wordmark } from "./Wordmark";
import { TopNavPills } from "./TopNavPills";
import { loadRepoFilter, saveRepoFilter } from "./RepoFilter";

const VIEW_MODE_KEY = "gitlytics-view-mode";

export function UsernameView({
  profile,
  repos,
  onLogout,
}: {
  profile: PublicProfile;
  repos: PublicRepo[];
  onLogout: () => void;
}) {
  const [viewMode, setViewModeState] = useState<ViewMode>("basic");
  const [showExport, setShowExport] = useState(false);
  const [showCard, setShowCard] = useState(false);
  const [exportMode, setExportMode] = useState<"png" | "pdf">("png");
  const [exportRepoFilter, setExportRepoFilter] = useState<string[] | null>(null);
  const [selectedRepos, setSelectedRepos] = useState<string[]>([]);

  useEffect(() => {
    try {
      const v = localStorage.getItem(VIEW_MODE_KEY);
      if (v === "basic" || v === "advanced") setViewModeState(v);
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

  const advanced = viewMode === "advanced";

  const trafficShape = useMemo(() => publicReposToTraffic(repos), [repos]);
  const allRepoNames = useMemo(() => trafficShape.map((r) => r.repository), [trafficShape]);
  const visibleRepos = useMemo(() => {
    const active =
      exportRepoFilter && exportRepoFilter.length > 0
        ? exportRepoFilter
        : selectedRepos.length > 0
          ? selectedRepos
          : null;
    if (!active) return repos;
    const set = new Set(active);
    return repos.filter((r) => set.has(r.full_name));
  }, [repos, exportRepoFilter, selectedRepos]);
  const visibleTraffic = useMemo(() => {
    const active =
      exportRepoFilter && exportRepoFilter.length > 0
        ? exportRepoFilter
        : selectedRepos.length > 0
          ? selectedRepos
          : null;
    if (!active) return trafficShape;
    const set = new Set(active);
    return trafficShape.filter((r) => set.has(r.repository));
  }, [trafficShape, exportRepoFilter, selectedRepos]);

  function applyRepos(next: string[]) {
    setSelectedRepos(next);
    saveRepoFilter(next);
  }
  const totalStars = visibleRepos.reduce((a, r) => a + r.stargazers_count, 0);
  const totalForks = visibleRepos.reduce((a, r) => a + r.forks_count, 0);
  const popular = [...visibleRepos].sort((a, b) => b.stargazers_count - a.stargazers_count)[0];
  const langSet = new Set(visibleRepos.map((r) => r.language).filter(Boolean));
  const devScore = Math.min(
    100,
    Math.round(totalStars * 0.25 + totalForks * 0.4 + visibleRepos.length * 0.6 + langSet.size * 3),
  );

  const createdYear = profile.created_at ? new Date(profile.created_at).getFullYear() : "—";

  function copyLink() {
    try {
      navigator.clipboard.writeText(window.location.href);
      toast.success("Link copied", { duration: 3000 });
    } catch {
      toast.error("Copy failed");
    }
  }

  const cardProfile: CardProfile = {
    name: profile.name || profile.login,
    username: profile.login,
    avatar_url: profile.avatar_url,
    bio: profile.bio || undefined,
    location: profile.location || undefined,
    followers: profile.followers,
    following: profile.following,
  };

  return (
    <div className="min-h-screen">
      <header className="glass sticky top-0 z-10 border-b border-border">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-4 py-3 sm:px-6">
          <div className="flex items-center gap-2.5">
            <img src="/gitlytics-logo.png" alt="Gitlytics logo" className="h-9 w-9 object-contain" />
            <div className="leading-tight">
              <p className="text-sm font-semibold"><Wordmark /></p>
              <p className="text-xs text-muted-foreground">Username mode</p>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <div className="flex items-center gap-2.5 border-r border-border/50 pr-3">
              <img
                src={profile.avatar_url}
                alt=""
                crossOrigin="anonymous"
                onError={(e) => {
                  (e.currentTarget as HTMLImageElement).src = "/octocat.png";
                }}
                className="h-8 w-8 rounded-full ring-1 ring-primary/40"
              />
              <div className="hidden text-right leading-tight sm:block">
                <p className="text-sm font-medium">{profile.name || profile.login}</p>
                <p className="text-xs text-muted-foreground">@{profile.login}</p>
              </div>
            </div>

            <span className="hidden items-center gap-1.5 rounded-lg bg-red-500/10 px-2.5 py-1 text-xs font-medium text-red-500 ring-1 ring-red-500/25 sm:flex">
              <User className="h-3.5 w-3.5" />
              Username Mode
            </span>
            
            <div className="ml-2 flex items-center gap-2.5">
              <TopNavPills className="hidden md:flex" />
              <button
                onClick={copyLink}
                className="flex items-center gap-1.5 rounded-lg border border-input bg-background/40 px-3 py-1.5 text-xs font-medium transition-all hover:scale-[1.02] hover:bg-foreground/5"
              >
                <LinkIcon className="h-3.5 w-3.5" />
                <span className="hidden sm:inline">Copy Link</span>
              </button>
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
        {/* Filter / toolbar */}
        <DashboardToolbar
          query=""
          setQuery={() => {}}
          topN={10}
          setTopN={() => {}}
          maxN={10}
          range="14D"
          setRange={() => {}}
          customFrom=""
          setCustomFrom={() => {}}
          customTo=""
          setCustomTo={() => {}}
          onDownload={() => {}}
          onExportPng={() => { setExportMode("png"); setShowExport(true); }}
          onExportPdf={() => { setExportMode("pdf"); setShowExport(true); }}
          onCreateCard={() => setShowCard(true)}
          onReload={() => {}}
          reloading={false}
          canReload={false}
          viewMode={viewMode}
          setViewMode={setViewMode}
          showCsv={false}
          allRepos={allRepoNames}
          selectedRepos={selectedRepos}
          onSelectedReposChange={applyRepos}
        />

        {/* Section 1 — Profile */}
        <div id="section-hero" className="glass gradient-border animate-slide-up flex flex-col gap-4 rounded-xl p-5 sm:flex-row sm:items-start">
          <img
            src={profile.avatar_url}
            alt=""
            crossOrigin="anonymous"
            onError={(e) => {
              (e.currentTarget as HTMLImageElement).src = "/octocat.png";
            }}
            className="h-20 w-20 rounded-xl ring-1 ring-primary/40 sm:h-24 sm:w-24"
          />
          <div className="flex-1 space-y-2">
            <div>
              <h2 className="text-xl font-semibold text-primary">{profile.name || profile.login}</h2>
              <p className="text-sm text-muted-foreground">@{profile.login}</p>
            </div>
            {profile.bio && <p className="text-sm">{profile.bio}</p>}
            <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-muted-foreground">
              {profile.location && (
                <span className="flex items-center gap-1"><MapPin className="h-3 w-3" />{profile.location}</span>
              )}
              {profile.blog && (
                <a href={profile.blog.startsWith("http") ? profile.blog : `https://${profile.blog}`} target="_blank" rel="noreferrer" className="flex items-center gap-1 hover:text-primary">
                  <Globe className="h-3 w-3" />{profile.blog}<ExternalLink className="h-3 w-3" />
                </a>
              )}
              {profile.twitter_username && (
                <a href={`https://x.com/${profile.twitter_username}`} target="_blank" rel="noreferrer" className="flex items-center gap-1 hover:text-primary">
                  @{profile.twitter_username}<ExternalLink className="h-3 w-3" />
                </a>
              )}
              <span className="flex items-center gap-1"><Calendar className="h-3 w-3" />Member since {createdYear}</span>
            </div>
            <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs">
              <span><span className="font-semibold text-foreground">{profile.followers.toLocaleString()}</span> <span className="text-muted-foreground">followers</span></span>
              <span><span className="font-semibold text-foreground">{profile.following.toLocaleString()}</span> <span className="text-muted-foreground">following</span></span>
              <span><span className="font-semibold text-foreground">{profile.public_repos.toLocaleString()}</span> <span className="text-muted-foreground">public repos</span></span>
            </div>
          </div>
        </div>

        {/* Section 2 — Stat cards */}
        <div id="section-stat-cards" className="grid grid-cols-2 gap-4 sm:grid-cols-4">
          <StatCard label="Public Repos" value={visibleRepos.length} icon={Package} />
          <StatCard label="Total Stars" value={totalStars} icon={Star} />
          <StatCard label="Total Forks" value={totalForks} icon={GitFork} />
          <StatCard label="Developer Score" value={devScore} icon={Award} suffix="/100" />
        </div>

        {/* Section 3 — Most starred */}
        {popular && (
          <div className="glass gradient-border animate-slide-up rounded-xl p-5">
            <p className="mb-2 text-[10px] uppercase tracking-wide text-muted-foreground">Most Popular Project</p>
            <div className="flex flex-wrap items-center gap-2">
              <a href={popular.html_url} target="_blank" rel="noreferrer" className="text-lg font-semibold text-primary hover:underline">
                {popular.full_name}
              </a>
              <LanguagePill repo={popular.full_name} />
            </div>
            {popular.description && <p className="mt-1.5 text-sm text-muted-foreground">{popular.description}</p>}
            <div className="mt-3 flex flex-wrap items-center gap-3 text-xs text-muted-foreground">
              <span><span className="font-semibold text-foreground">{popular.stargazers_count.toLocaleString()}</span> ★</span>
              <span><span className="font-semibold text-foreground">{popular.forks_count.toLocaleString()}</span> 🍴</span>
              {popular.language && <span>{popular.language}</span>}
              <span>Last pushed {new Date(popular.pushed_at).toLocaleDateString()}</span>
            </div>
          </div>
        )}

        {advanced && (
          <>
            <div id="section-languages">
              <LanguageDistribution repos={visibleTraffic} />
            </div>
            <div id="section-commits">
              <CommitActivity repos={visibleTraffic} />
            </div>
          </>
        )}

        {/* Section 7 — All repos table */}
        <div id="section-all-repos" className="glass gradient-border animate-slide-up rounded-xl">
          <div className="border-b border-border p-4">
            <h3 className="text-sm font-semibold">All Public Repositories</h3>
            <p className="mt-0.5 text-xs text-muted-foreground">Click a row to expand</p>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border text-left text-xs text-muted-foreground">
                  <th className="px-4 py-3 font-medium">Repository</th>
                  <th className="px-4 py-3 text-right font-medium">Stars</th>
                  <th className="px-4 py-3 text-right font-medium">Forks</th>
                  <th className="px-4 py-3 text-right font-medium">Language</th>
                  <th className="hidden px-4 py-3 text-right font-medium lg:table-cell">Last Pushed</th>
                  <th className="hidden px-4 py-3 text-right font-medium lg:table-cell">Issues</th>
                </tr>
              </thead>
              <tbody>
                {visibleRepos.map((r) => (
                  <UserRepoRow key={r.full_name} repo={r} traffic={trafficShape.find((t) => t.repository === r.full_name)!} advanced={advanced} />
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Section 8 — Locked traffic */}
        <div className="glass gradient-border animate-slide-up flex flex-col gap-3 rounded-xl p-5 sm:flex-row sm:items-center">
          <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-lg bg-primary/15 ring-1 ring-primary/30">
            <Lock className="h-5 w-5 text-primary" />
          </div>
          <p className="flex-1 text-sm text-muted-foreground">
            Views, clones, referrers and visitor data require connecting with a Personal Access Token.
            Switch to Live API mode to unlock traffic analytics.
          </p>
          <button
            onClick={onLogout}
            className="rounded-lg bg-primary px-4 py-2 text-sm font-semibold text-primary-foreground transition-transform hover:scale-[1.02]"
          >
            Connect with PAT
          </button>
        </div>

        {showExport && (
          <ExportModal
            onClose={() => setShowExport(false)}
            mode={exportMode}
            allRepos={allRepoNames}
            defaultRepos={allRepoNames}
            runWithRepos={async (selected, fn) => {
              const apply = selected.length === 0 ? null : selected;
              setExportRepoFilter(apply);
              await new Promise((r) => setTimeout(r, 700));
              try {
                await fn();
              } finally {
                setExportRepoFilter(null);
              }
            }}
            profile={cardProfile}
          />
        )}
        {showCard && (
          <CardModal profile={cardProfile} repos={trafficShape} onClose={() => setShowCard(false)} />
        )}

        <div id="section-export-history">
          <ExportHistory />
        </div>
      </main>
      <ExportOverlay />
      <KeyboardHelp />
    </div>
  );
}

function StatCard({ label, value, icon: Icon, suffix }: { label: string; value: number; icon: typeof Star; suffix?: string }) {
  return (
    <div className="glass gradient-border animate-slide-up rounded-xl p-4">
      <div className="mb-3 flex items-center justify-between">
        <span className="text-xs font-medium text-muted-foreground">{label}</span>
        <Icon className="h-4 w-4 text-primary" />
      </div>
      <p className="text-2xl font-semibold tracking-tight">
        {value.toLocaleString()}
        {suffix && <span className="text-sm text-muted-foreground">{suffix}</span>}
      </p>
    </div>
  );
}

function UserRepoRow({
  repo, traffic, advanced,
}: { repo: PublicRepo; traffic: ReturnType<typeof publicReposToTraffic>[number]; advanced: boolean }) {
  const [open, setOpen] = useState(false);
  const [forceOpen, setForceOpen] = useState(false);
  useEffect(() => {
    const expand = () => setForceOpen(true);
    const restore = () => setForceOpen(false);
    window.addEventListener("gitlytics-export-expand", expand);
    window.addEventListener("gitlytics-export-restore", restore);
    return () => {
      window.removeEventListener("gitlytics-export-expand", expand);
      window.removeEventListener("gitlytics-export-restore", restore);
    };
  }, []);
  const isOpen = open || forceOpen;
  return (
    <>
      <tr onClick={() => setOpen((o) => !o)} className="cursor-pointer border-b border-border/60 transition-colors last:border-0 hover:bg-foreground/[0.03]">
        <td className="px-4 py-3">
          <div className="flex flex-wrap items-center gap-2">
            <a href={repo.html_url} target="_blank" rel="noreferrer" onClick={(e) => e.stopPropagation()} className="font-medium hover:text-primary">
              {repo.full_name}
            </a>
            <LanguagePill repo={repo.full_name} />
          </div>
        </td>
        <td className="px-4 py-3 text-right tabular-nums text-muted-foreground">{repo.stargazers_count.toLocaleString()}</td>
        <td className="px-4 py-3 text-right tabular-nums text-muted-foreground">{repo.forks_count.toLocaleString()}</td>
        <td className="px-4 py-3 text-right text-muted-foreground">{repo.language || "—"}</td>
        <td className="hidden px-4 py-3 text-right text-muted-foreground lg:table-cell">{new Date(repo.pushed_at).toLocaleDateString()}</td>
        <td className="hidden px-4 py-3 text-right tabular-nums text-muted-foreground lg:table-cell">{repo.open_issues_count}</td>
      </tr>
      {isOpen && (
        <tr className="border-b border-border/60 bg-background/30">
          <td colSpan={6} className="px-4 py-5">
            <div className="animate-slide-up space-y-4">
              {repo.description && <p className="text-sm text-muted-foreground">{repo.description}</p>}
              {repo.topics?.length > 0 ? (
                <div className="rounded-lg border border-border/60 bg-background/30 p-3">
                  <p className="mb-1.5 text-[11px] font-medium text-muted-foreground">Topics</p>
                  <div className="flex flex-wrap gap-1.5">
                    {repo.topics.map((t) => (
                      <span key={t} className="inline-flex items-center rounded-md bg-foreground/5 px-2 py-0.5 text-[11px] font-medium ring-1 ring-border">{t}</span>
                    ))}
                  </div>
                </div>
              ) : (
                <TopicTags repo={repo.full_name} />
              )}
              <div className="grid grid-cols-2 gap-3 lg:grid-cols-3">
                <ReadmeQualityCard repo={traffic} />
                <StarForkRatioCard repo={traffic} />
                <div className="rounded-lg border border-border/60 bg-background/30 p-3 text-xs text-muted-foreground" title="Traffic data requires Live API mode with PAT">
                  <div className="flex items-center gap-1.5 font-semibold text-foreground"><Lock className="h-3.5 w-3.5 text-primary" /> Traffic locked</div>
                  <p className="mt-1">Switch to Live API to unlock views, clones and referrers.</p>
                </div>
              </div>
              {advanced && <LaunchReadinessCard repo={traffic} />}
            </div>
          </td>
        </tr>
      )}
    </>
  );
}
