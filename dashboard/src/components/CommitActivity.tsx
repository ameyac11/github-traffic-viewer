import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, Cell } from "recharts";
import { GitCommitHorizontal, Lock, Loader2 } from "lucide-react";
import type { RepoTraffic } from "@/lib/github-api";
import { commitActivity } from "@/lib/analytics";
import { useIsExporting } from "@/hooks/use-export-state";

function CustomTooltip({ active, payload, label }: any) {
  if (!active || !payload?.length) return null;
  return (
    <div className="glass rounded-lg px-3 py-2 text-xs shadow-xl">
      <p className="mb-1 font-medium text-foreground">{label}</p>
      <p className="text-muted-foreground">
        Commits:{" "}
        <span className="font-semibold text-foreground">{payload[0].value.toLocaleString()}</span>
      </p>
    </div>
  );
}

export function CommitActivity({ repos, isApi = false }: { repos: RepoTraffic[]; isApi?: boolean }) {
  const data = commitActivity(repos);
  const isExporting = useIsExporting();

  return (
    <div className="glass gradient-border animate-slide-up rounded-xl p-5">
      <div
        className="mb-4 flex items-center gap-2"
        title="Total commit count per repository — shows which projects are most actively developed"
      >
        <GitCommitHorizontal className="h-4 w-4 text-primary" />
        <h3 className="text-sm font-semibold">Commit Activity — All Repositories</h3>
      </div>
      {data.length === 0 ? (
        <div className="flex h-[300px] items-center justify-center text-sm text-muted-foreground">
          No data available
        </div>
      ) : !data.some((d) => d.hasData) ? (
        <div className="flex h-[300px] flex-col items-center justify-center gap-3 text-center text-sm text-muted-foreground">
          <div className="flex h-12 w-12 items-center justify-center rounded-full bg-primary/10 ring-1 ring-primary/20">
            {isApi ? (
              <Loader2 className="h-5 w-5 text-primary animate-spin" />
            ) : (
              <Lock className="h-5 w-5 text-primary" />
            )}
          </div>
          <p className="max-w-[280px]">
            {isApi ? (
              "GitHub is computing commit statistics in the background. Please refresh/reload the page in a few seconds."
            ) : (
              "Commit activity requires a Personal Access Token. Switch to Live API mode to unlock."
            )}
          </p>
        </div>
      ) : (
        <ResponsiveContainer width="100%" height={300}>
          <BarChart data={data} margin={{ top: 4, right: 8, left: 8, bottom: 40 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" vertical={false} />
            <XAxis
              dataKey="name"
              angle={-40}
              textAnchor="end"
              tick={{ fill: "var(--muted-foreground)", fontSize: 11 }}
              interval={0}
              height={60}
            />
            <YAxis tick={{ fill: "var(--muted-foreground)", fontSize: 11 }} width={56} tickMargin={4} />
            <Tooltip
              content={<CustomTooltip />}
              cursor={{ fill: "color-mix(in oklab, var(--foreground) 6%, transparent)" }}
            />
            <Bar dataKey="commits" name="Commits" radius={[4, 4, 0, 0]} isAnimationActive={!isExporting}>
              {data.map((_, i) => (
                <Cell key={i} fill="var(--chart-4)" fillOpacity={Math.max(0.4, 1 - i * 0.025)} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      )}
    </div>
  );
}
