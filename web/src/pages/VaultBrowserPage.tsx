import { useCallback, useEffect, useLayoutEffect, useMemo, useState } from "react";
import {
  Archive,
  Database,
  FileText,
  HeartPulse,
  RefreshCw,
  ShieldCheck,
  Snowflake,
} from "lucide-react";
import { Badge } from "@nous-research/ui/ui/components/badge";
import { Button } from "@nous-research/ui/ui/components/button";
import { Card, CardContent, CardHeader, CardTitle } from "@nous-research/ui/ui/components/card";
import { Spinner } from "@nous-research/ui/ui/components/spinner";
import { fetchJSON } from "@/lib/api";
import { cn, isoTimeAgo } from "@/lib/utils";
import { usePageHeader } from "@/contexts/usePageHeader";
import { PluginSlot } from "@/plugins";
import VaultBrowser from "@/pages/VaultBrowser";

type VaultTab = "browser" | "engagements" | "health";

interface VaultTreeEntry {
  name?: string;
  path?: string;
  type?: "file" | "directory" | string;
  size?: number;
  updated_at?: string;
  summary?: string;
}

interface VaultTreeResponse {
  folder?: string;
  entries?: VaultTreeEntry[];
}

interface VaultHealthResponse {
  hit_rate?: number;
  dead_pages?: VaultTreeEntry[] | number;
  duplicates?: Array<{
    path?: string;
    paths?: string[];
    canonical?: string;
  }> | number;
  checked_at?: string;
  pages?: number;
}

const TABS: Array<{ id: VaultTab; label: string; icon: typeof Archive }> = [
  { id: "browser", label: "Browser", icon: Database },
  { id: "engagements", label: "Engagements", icon: Archive },
  { id: "health", label: "Health", icon: HeartPulse },
];

function entryTitle(entry: VaultTreeEntry) {
  if (entry.name) return entry.name;
  if (!entry.path) return "entry";
  return entry.path.split(/[\\/]/).filter(Boolean).pop() ?? entry.path;
}

function normalizeDeadPages(value: VaultHealthResponse["dead_pages"]) {
  if (Array.isArray(value)) return value;
  return [];
}

function normalizeDuplicates(value: VaultHealthResponse["duplicates"]) {
  if (Array.isArray(value)) return value;
  return [];
}

function countValue(value: unknown) {
  if (Array.isArray(value)) return value.length;
  if (typeof value === "number") return value;
  return 0;
}

export default function VaultBrowserPage() {
  const [tab, setTab] = useState<VaultTab>("browser");
  const [engagements, setEngagements] = useState<VaultTreeEntry[]>([]);
  const [health, setHealth] = useState<VaultHealthResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [actionPath, setActionPath] = useState<string | null>(null);
  const { setAfterTitle, setEnd } = usePageHeader();

  const deadPages = useMemo(
    () => normalizeDeadPages(health?.dead_pages),
    [health],
  );
  const duplicates = useMemo(
    () => normalizeDuplicates(health?.duplicates),
    [health],
  );

  const load = useCallback(() => {
    setLoading(true);
    setError(null);
    Promise.allSettled([
      fetchJSON<VaultTreeResponse>("/api/vault/tree?folder=Engagements"),
      fetchJSON<VaultHealthResponse>("/api/vault/health"),
    ])
      .then(([treeResult, healthResult]) => {
        if (treeResult.status === "fulfilled") {
          setEngagements(treeResult.value.entries ?? []);
        } else {
          setError(String(treeResult.reason));
        }

        if (healthResult.status === "fulfilled") {
          setHealth(healthResult.value);
        } else if (treeResult.status === "fulfilled") {
          setError(String(healthResult.reason));
        }
      })
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  useLayoutEffect(() => {
    setAfterTitle(
      <Badge tone="secondary" className="text-xs">
        {tab}
      </Badge>,
    );
    setEnd(
      <Button
        type="button"
        ghost
        size="icon"
        onClick={load}
        disabled={loading}
        aria-label="Refresh Vault"
      >
        {loading ? <Spinner /> : <RefreshCw />}
      </Button>,
    );
    return () => {
      setAfterTitle(null);
      setEnd(null);
    };
  }, [load, loading, setAfterTitle, setEnd, tab]);

  const runVaultAction = async (path: string, tier: "Hot" | "Cold") => {
    setActionPath(path);
    setError(null);
    try {
      await fetchJSON<{ ok: boolean }>("/api/vault/promote", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ path, tier }),
      });
      load();
    } catch (err) {
      setError(String(err));
    } finally {
      setActionPath(null);
    }
  };

  return (
    <div className="flex min-w-0 max-w-full flex-col gap-4" data-testid="vault-browser-page">
      <PluginSlot name="vault:top" />

      <div
        role="tablist"
        aria-label="Vault"
        className="flex min-w-0 flex-wrap items-center gap-2"
      >
        {TABS.map(({ id, label, icon: Icon }) => (
          <Button
            key={id}
            type="button"
            size="sm"
            outlined={tab !== id}
            prefix={<Icon className="h-3.5 w-3.5" />}
            onClick={() => setTab(id)}
            aria-selected={tab === id}
            role="tab"
          >
            {label}
          </Button>
        ))}
      </div>

      {error && (
        <div className="border border-destructive/20 bg-destructive/10 p-3 text-sm text-destructive">
          {error}
        </div>
      )}

      {tab === "browser" && <VaultBrowser />}

      {tab === "engagements" && (
        <Card className="min-w-0 overflow-hidden">
          <CardHeader className="px-4 py-3">
            <CardTitle className="flex items-center gap-2 text-sm">
              <Archive className="h-4 w-4" />
              Engagements
            </CardTitle>
          </CardHeader>
          <CardContent className="p-0">
            {loading && engagements.length === 0 ? (
              <div className="flex min-h-56 items-center justify-center">
                <Spinner className="text-xl text-primary" />
              </div>
            ) : engagements.length === 0 ? (
              <div className="px-4 py-8 text-sm text-muted-foreground">
                No entries returned for Engagements.
              </div>
            ) : (
              <div className="divide-y divide-border/60">
                {engagements.map((entry, index) => (
                  <article
                    key={`${entry.path ?? entry.name ?? "engagement"}-${index}`}
                    className="flex min-w-0 flex-col gap-3 px-4 py-3 sm:flex-row sm:items-center sm:justify-between"
                  >
                    <div className="min-w-0">
                      <h2 className="truncate text-sm font-medium text-midground">
                        {entryTitle(entry)}
                      </h2>
                      <p className="truncate font-mono text-xs text-text-tertiary">
                        {entry.path ?? "Engagements"}
                      </p>
                      {entry.summary && (
                        <p className="mt-1 line-clamp-2 text-xs leading-5 text-text-secondary">
                          {entry.summary}
                        </p>
                      )}
                    </div>
                    <div className="flex shrink-0 items-center gap-2">
                      {entry.updated_at && (
                        <span className="text-xs text-text-tertiary">
                          {isoTimeAgo(entry.updated_at)}
                        </span>
                      )}
                      <Badge tone="secondary" className="text-xs">
                        {entry.type ?? "entry"}
                      </Badge>
                    </div>
                  </article>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {tab === "health" && (
        <div className="grid min-w-0 gap-4 xl:grid-cols-[minmax(0,0.65fr)_minmax(420px,1fr)]">
          <section className="grid min-w-0 gap-3 sm:grid-cols-3 xl:grid-cols-1">
            <HealthMetric
              icon={ShieldCheck}
              label="Hit rate"
              value={
                typeof health?.hit_rate === "number"
                  ? `${Math.round(health.hit_rate * 100)}%`
                  : "n/a"
              }
            />
            <HealthMetric
              icon={FileText}
              label="Dead pages"
              value={String(countValue(health?.dead_pages))}
            />
            <HealthMetric
              icon={Archive}
              label="Duplicates"
              value={String(countValue(health?.duplicates))}
            />
          </section>

          <Card className="min-w-0 overflow-hidden">
            <CardHeader className="px-4 py-3">
              <CardTitle className="flex items-center gap-2 text-sm">
                <HeartPulse className="h-4 w-4" />
                Health
              </CardTitle>
            </CardHeader>
            <CardContent className="grid gap-4 px-4 pb-4">
              {health?.checked_at && (
                <p className="text-xs text-text-tertiary">
                  Checked {isoTimeAgo(health.checked_at)}
                </p>
              )}

              <HealthList
                title="Dead pages"
                entries={deadPages}
                empty="No dead pages reported."
                actionPath={actionPath}
                onArchive={(path) => runVaultAction(path, "Cold")}
                onPromote={(path) => runVaultAction(path, "Hot")}
              />

              <div className="grid gap-2">
                <h3 className="font-mondwest text-display text-xs uppercase tracking-[0.12em] text-text-tertiary">
                  Duplicates
                </h3>
                {duplicates.length === 0 ? (
                  <p className="text-sm text-muted-foreground">
                    No duplicates reported.
                  </p>
                ) : (
                  <div className="grid gap-2">
                    {duplicates.map((dupe, index) => {
                      const paths = dupe.paths ?? (dupe.path ? [dupe.path] : []);
                      return (
                        <div
                          key={`${dupe.canonical ?? dupe.path ?? "duplicate"}-${index}`}
                          className="grid gap-2 border border-border/60 p-3"
                        >
                          <div className="flex items-center justify-between gap-3">
                            <span className="truncate text-sm text-midground">
                              {dupe.canonical ?? paths[0] ?? "duplicate"}
                            </span>
                            <Badge tone="warning" className="text-xs">
                              {paths.length}
                            </Badge>
                          </div>
                          {paths.map((path) => (
                            <div
                              key={path}
                              className="flex min-w-0 items-center justify-between gap-2"
                            >
                              <span className="truncate font-mono text-xs text-text-secondary">
                                {path}
                              </span>
                              <Button
                                type="button"
                                size="sm"
                                outlined
                                disabled={actionPath === path}
                                prefix={
                                  actionPath === path ? (
                                    <Spinner />
                                  ) : (
                                    <Snowflake className="h-3.5 w-3.5" />
                                  )
                                }
                                onClick={() => runVaultAction(path, "Cold")}
                              >
                                Archive
                              </Button>
                            </div>
                          ))}
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      <PluginSlot name="vault:bottom" />
    </div>
  );
}

function HealthMetric({
  icon: Icon,
  label,
  value,
}: {
  icon: typeof ShieldCheck;
  label: string;
  value: string;
}) {
  return (
    <Card className="min-w-0 overflow-hidden">
      <CardContent className="flex items-center justify-between gap-3 p-4">
        <div className="min-w-0">
          <p className="text-xs text-text-tertiary">{label}</p>
          <p className="mt-1 truncate font-mondwest text-display text-xl text-midground">
            {value}
          </p>
        </div>
        <Icon className="h-5 w-5 shrink-0 text-muted-foreground" />
      </CardContent>
    </Card>
  );
}

function HealthList({
  actionPath,
  empty,
  entries,
  onArchive,
  onPromote,
  title,
}: {
  actionPath: string | null;
  empty: string;
  entries: VaultTreeEntry[];
  onArchive: (path: string) => void;
  onPromote: (path: string) => void;
  title: string;
}) {
  return (
    <div className="grid gap-2">
      <h3 className="font-mondwest text-display text-xs uppercase tracking-[0.12em] text-text-tertiary">
        {title}
      </h3>
      {entries.length === 0 ? (
        <p className="text-sm text-muted-foreground">{empty}</p>
      ) : (
        <div className="grid gap-2">
          {entries.map((entry) => {
            const path = entry.path ?? entry.name ?? "";
            const busy = actionPath === path;
            return (
              <div
                key={path}
                className={cn(
                  "flex min-w-0 flex-col gap-2 border border-border/60 p-3",
                  "sm:flex-row sm:items-center sm:justify-between",
                )}
              >
                <div className="min-w-0">
                  <p className="truncate text-sm text-midground">
                    {entryTitle(entry)}
                  </p>
                  <p className="truncate font-mono text-xs text-text-tertiary">
                    {path}
                  </p>
                </div>
                <div className="flex shrink-0 gap-2">
                  <Button
                    type="button"
                    size="sm"
                    outlined
                    disabled={!path || busy}
                    prefix={busy ? <Spinner /> : <ShieldCheck className="h-3.5 w-3.5" />}
                    onClick={() => onPromote(path)}
                  >
                    Promote
                  </Button>
                  <Button
                    type="button"
                    size="sm"
                    outlined
                    disabled={!path || busy}
                    prefix={busy ? <Spinner /> : <Snowflake className="h-3.5 w-3.5" />}
                    onClick={() => onArchive(path)}
                  >
                    Archive
                  </Button>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
