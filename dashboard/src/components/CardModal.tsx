import { useMemo, useState } from "react";
import { createPortal } from "react-dom";
import { X, ImageDown, Star, GitFork, Package, Users } from "lucide-react";
import { runCardExport } from "@/lib/exports";
import { repoLanguage, LANG_TINT } from "@/lib/analytics";
import type { RepoTraffic } from "@/lib/github-api";
import { Wordmark } from "./Wordmark";

export interface CardProfile {
  name: string;
  username: string;
  avatar_url: string;
  bio?: string;
  location?: string;
  followers?: number;
  following?: number;
}

export function CardModal({
  profile,
  repos,
  onClose,
}: {
  profile: CardProfile;
  repos: RepoTraffic[];
  onClose: () => void;
}) {
  const [opts, setOpts] = useState({
    profile: true,
    stats: true,
    languages: true,
    popular: true,
    followers: false,
  });
  const [busy, setBusy] = useState(false);

  const { totalStars, totalForks, repoCount, topLangs, popular, langShares } = useMemo(() => {
    const totalStars = repos.reduce((a, r) => a + (Number(r.stars) || 0), 0);
    const totalForks = repos.reduce((a, r) => a + (Number(r.forks) || 0), 0);
    const repoCount = repos.length;
    const langCounts = new Map<string, number>();
    for (const r of repos) {
      const l = repoLanguage(r);
      langCounts.set(l, (langCounts.get(l) || 0) + 1);
    }
    const topLangs = [...langCounts.entries()]
      .sort((a, b) => b[1] - a[1])
      .slice(0, 3)
      .map(([l]) => l);
    const popular = [...repos].sort((a, b) => (Number(b.stars) || 0) - (Number(a.stars) || 0))[0];

    const totalLangsCount = [...langCounts.values()].reduce((a, b) => a + b, 0);
    const langShares = [...langCounts.entries()]
      .sort((a, b) => b[1] - a[1])
      .slice(0, 3)
      .map(([name, count]) => ({
        name,
        percentage: totalLangsCount > 0 ? Math.round((count / totalLangsCount) * 100) : 0,
      }));

    return { totalStars, totalForks, repoCount, topLangs, popular, langShares };
  }, [repos]);

  async function download() {
    setBusy(true);
    try {
      await runCardExport(profile.username);
      onClose();
    } catch {
      /* toast handled */
    } finally {
      setBusy(false);
    }
  }

  const toggle = (k: keyof typeof opts) => setOpts((o) => ({ ...o, [k]: !o[k] }));

  return createPortal(
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-background/95 p-4 backdrop-blur-md"
      onClick={() => !busy && onClose()}
    >
      <div
        className="glass animate-slide-up w-full max-w-4xl overflow-hidden rounded-xl border border-border"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between border-b border-border p-4">
          <div>
            <h3 className="text-sm font-semibold">Create Developer Card</h3>
            <p className="mt-0.5 text-xs text-muted-foreground">
              Shareable image for X and LinkedIn
            </p>
          </div>
          <button
            onClick={() => !busy && onClose()}
            aria-label="Close"
            className="rounded-lg p-1 text-muted-foreground transition-colors hover:bg-foreground/5 hover:text-foreground"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        <div className="grid gap-5 p-5 md:grid-cols-[1fr_240px]">
          {/* Preview */}
          <div className="flex items-center justify-center rounded-lg border border-border/60 bg-background/30 p-4">
            <DeveloperCard profile={profile} opts={opts} totalStars={totalStars} totalForks={totalForks} repoCount={repoCount} topLangs={topLangs} popular={popular} langShares={langShares} />
          </div>

          {/* Toggles */}
          <div className="space-y-2 text-sm">
            <p className="text-xs uppercase tracking-wide text-muted-foreground">Include</p>
            {([
              ["profile", "Profile info"],
              ["stats", "Stats"],
              ["languages", "Top languages"],
              ["popular", "Most popular repo"],
              ["followers", "Followers / following"],
            ] as const).map(([k, label]) => (
              <label
                key={k}
                className="flex cursor-pointer items-center gap-2.5 rounded-lg border border-border/60 bg-background/30 px-3 py-2 transition-colors hover:bg-foreground/5"
              >
                <input
                  type="checkbox"
                  checked={opts[k]}
                  onChange={() => toggle(k)}
                  className="h-4 w-4 cursor-pointer accent-primary"
                />
                {label}
              </label>
            ))}
            <label className="flex items-center gap-2.5 rounded-lg border border-border/60 bg-background/30 px-3 py-2 opacity-70">
              <input type="checkbox" checked readOnly className="h-4 w-4 accent-primary" />
              Gitlytics branding
            </label>
            <button
              onClick={download}
              disabled={busy}
              className="mt-3 flex w-full items-center justify-center gap-1.5 rounded-lg bg-primary px-4 py-2.5 text-sm font-semibold text-primary-foreground transition-transform hover:scale-[1.01] disabled:opacity-50"
            >
              <ImageDown className="h-4 w-4" />
              {busy ? "Generating…" : "Download Card"}
            </button>
          </div>
        </div>
      </div>
    </div>,
    document.body,
  );
} function DeveloperCard({
  profile,
  opts,
  totalStars,
  totalForks,
  repoCount,
  topLangs,
  popular,
  langShares,
}: {
  profile: CardProfile;
  opts: { profile: boolean; stats: boolean; languages: boolean; popular: boolean; followers: boolean };
  totalStars: number;
  totalForks: number;
  repoCount: number;
  topLangs: string[];
  popular?: RepoTraffic;
  langShares: { name: string; percentage: number }[];
}) {
  return (
    <div
      id="developer-card"
      className="relative w-[480px] rounded-2xl border border-border/80 p-6 shadow-2xl bg-[#141312] overflow-hidden"
    >
      {/* Decorative Glow */}
      <div className="absolute -right-20 -top-20 h-40 w-40 rounded-full bg-primary/10 pointer-events-none" />
      <div className="absolute -left-20 -bottom-20 h-40 w-40 rounded-full bg-chart-2/10 pointer-events-none" />

      {/* Header Branding */}
      <div className="relative z-10 mb-5 flex items-center gap-2">
        <img src="/gitlytics-logo.png" alt="" className="h-5 w-5 object-contain" />
        <Wordmark className="text-xs font-bold tracking-wider uppercase opacity-90" />
      </div>

      {/* Profile Section */}
      {opts.profile && (
        <div className="relative z-10 mb-5 flex items-center gap-4">
          <img
            src={profile.avatar_url}
            alt=""
            crossOrigin="anonymous"
            onError={(e) => {
              (e.currentTarget as HTMLImageElement).src = "/octocat.png";
            }}
            className="h-16 w-16 rounded-full border-2 border-primary/50 p-0.5 bg-surface/40 object-cover shadow-lg shadow-primary/5"
          />
          <div className="leading-tight">
            <p className="text-lg font-bold tracking-tight text-foreground">
              {profile.name || profile.username}
            </p>
            <p className="text-xs font-semibold text-primary">@{profile.username}</p>
            {(profile.bio || profile.location) && (
              <p className="mt-1 text-xs text-muted-foreground line-clamp-2 max-w-[340px]">
                {[profile.bio, profile.location].filter(Boolean).join(" · ")}
              </p>
            )}
          </div>
        </div>
      )}

      {/* Stats Cards Grid */}
      {opts.stats && (
        <div className={`relative z-10 mb-5 grid gap-2.5 text-xs ${opts.followers ? "grid-cols-4" : "grid-cols-3"}`}>
          <Stat icon={<Star className="h-4 w-4" />} label="Stars" value={totalStars} colorClass="text-chart-2" />
          <Stat icon={<GitFork className="h-4 w-4" />} label="Forks" value={totalForks} colorClass="text-chart-4" />
          <Stat icon={<Package className="h-4 w-4" />} label="Repos" value={repoCount} colorClass="text-chart-3" />
          {opts.followers && (
            <Stat icon={<Users className="h-4 w-4" />} label="Followers" value={profile.followers ?? 0} colorClass="text-primary" />
          )}
        </div>
      )}

      {/* Top Languages */}
      {opts.languages && langShares.length > 0 && (
        <div className="relative z-10 mb-5">
          <p className="mb-2 text-[10px] uppercase tracking-wider text-muted-foreground/80 font-bold">
            Top Languages
          </p>
          {/* Segmented Progress Bar */}
          <div className="mb-3 h-2 w-full rounded-full bg-foreground/5 overflow-hidden flex">
            {langShares.map((lang, idx) => {
              const bgColors = ["bg-primary", "bg-chart-2", "bg-chart-3", "bg-chart-4"];
              const colorClass = bgColors[idx % bgColors.length];
              return (
                <div
                  key={lang.name}
                  style={{ width: `${lang.percentage}%` }}
                  className={`${colorClass} h-full`}
                />
              );
            })}
          </div>

          {/* Language Legends */}
          <div className="flex flex-wrap gap-x-4 gap-y-1.5">
            {langShares.map((lang, idx) => {
              const dotColors = ["bg-primary", "bg-chart-2", "bg-chart-3", "bg-chart-4"];
              const dotColorClass = dotColors[idx % dotColors.length];
              return (
                <div key={lang.name} className="flex items-center gap-1.5 text-xs">
                  <span className={`h-2 w-2 rounded-full ${dotColorClass}`} />
                  <span className="font-semibold text-foreground">{lang.name}</span>
                  <span className="text-muted-foreground font-medium">{lang.percentage}%</span>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Most Popular Repo */}
      {opts.popular && popular && (
        <div className="relative z-10 mb-5 rounded-xl border border-border/50 bg-foreground/[0.01] p-3.5 hover:bg-foreground/[0.02] transition-colors group">
          <p className="mb-1.5 text-[10px] uppercase tracking-wider text-muted-foreground/80 font-bold">
            Most Popular Project
          </p>
          <p className="truncate text-sm font-bold text-foreground group-hover:text-primary transition-colors">
            {popular.repository}
          </p>
          <div className="mt-2 flex items-center gap-3 text-xs text-muted-foreground font-semibold">
            <span className="flex items-center gap-1">
              <Star className="h-3.5 w-3.5 text-chart-2 fill-chart-2/10" /> {popular.stars}
            </span>
            <span className="flex items-center gap-1">
              <GitFork className="h-3.5 w-3.5 text-chart-4" /> {popular.forks}
            </span>
            <span className="h-1.5 w-1.5 rounded-full bg-primary" />
            <span>{repoLanguage(popular)}</span>
          </div>
        </div>
      )}

      {/* Footer */}
      <p className="relative z-10 mt-1 text-center text-[10px] tracking-wide text-muted-foreground/80">
        <Wordmark className="font-bold inline" /> · gitlytics.dev
      </p>
    </div>
  );
}

function Stat({
  icon,
  label,
  value,
  colorClass = "text-primary",
}: {
  icon: React.ReactNode;
  label: string;
  value: number;
  colorClass?: string;
}) {
  return (
    <div className="flex flex-col rounded-xl border border-border/50 bg-foreground/[0.02] p-2.5 transition-all hover:bg-foreground/[0.04] relative overflow-hidden group">
      <div className="flex items-center justify-between text-muted-foreground">
        <span className="text-[9px] font-bold uppercase tracking-wider text-muted-foreground/75">{label}</span>
        <span className={`transition-transform group-hover:scale-110 ${colorClass}`}>{icon}</span>
      </div>
      <span className="text-base font-bold tracking-tight tabular-nums text-foreground mt-1.5">
        {value.toLocaleString()}
      </span>
    </div>
  );
}
