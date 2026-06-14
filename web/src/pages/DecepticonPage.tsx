import { useCallback, useEffect, useLayoutEffect, useMemo, useState } from "react";
import {
  Activity,
  Database,
  FolderKanban,
  Play,
  RefreshCw,
  Server,
  Shield,
  TerminalSquare,
} from "lucide-react";
import { Badge } from "@nous-research/ui/ui/components/badge";
import { Button } from "@nous-research/ui/ui/components/button";
import { Card, CardContent, CardHeader, CardTitle } from "@nous-research/ui/ui/components/card";
import { Spinner } from "@nous-research/ui/ui/components/spinner";
import { fetchJSON } from "@/lib/api";
import { cn, isoTimeAgo } from "@/lib/utils";
import { usePageHeader } from "@/contexts/usePageHeader";
import { PluginSlot } from "@/plugins";

type StackServiceName = "langgraph" | "sandbox" | "neo4j";
type ServiceTone = "success" | "warning" | "destructive" | "secondary";

interface StackServiceStatus {
  name?: string;
  status?: string;
  state?: string;
  health?: string;
  ports?: string[];
  url?: string;
}

type StackStatusResponse = Partial<Record<StackServiceName, StackServiceStatus>> & {
  services?: StackServiceStatus[];
};

interface Engagement {
  name?: string;
  path?: string;
  status?: string;
  updated_at?: string;
  files?: number;
  summary?: string;
}

interface EngagementsResponse {
  engagements?: Engagement[];
}

interface OpsResponse {
  ok?: boolean;
  run_id?: string;
  status?: string;
  message?: string;
}

const SERVICE_NAMES: StackServiceName[] = ["langgraph", "sandbox", "neo4j"];

const OPS = [
  { kind: "ad", label: "AD", icon: Shield },
  { kind: "c2-sliver", label: "C2 Sliver", icon: TerminalSquare },
  { kind: "reversing", label: "Reversing", icon: Activity },
] as const;

function serviceTone(service: StackServiceStatus | undefined): ServiceTone {
  const value = `${service?.status ?? ""} ${service?.state ?? ""} ${service?.health ?? ""}`.toLowerCase();
  if (!service) return "secondary";
  if (value.includes("healthy") || value.includes("running") || value.includes("up")) {
    return "success";
  }
  if (value.includes("starting") || value.includes("created") || value.includes("paused")) {
    return "warning";
  }
  if (value.includes("error") || value.includes("exited") || value.includes("dead") || value.includes("unhealthy")) {
    return "destructive";
  }
  return "secondary";
}

function serviceLabel(service: StackServiceStatus | undefined) {
  return service?.health ?? service?.status ?? service?.state ?? "unknown";
}

function serviceFromPayload(
  payload: StackStatusResponse | null,
  name: StackServiceName,
): StackServiceStatus | undefined {
  if (!payload) return undefined;
  const direct = payload[name];
  if (direct) return direct;
  return payload.services?.find((service) =>
    (service.name ?? "").toLowerCase().includes(name),
  );
}

function engagementTitle(engagement: Engagement) {
  if (engagement.name) return engagement.name;
  if (!engagement.path) return "engagement";
  return engagement.path.split(/[\\/]/).filter(Boolean).pop() ?? engagement.path;
}

export default function DecepticonPage() {
  const [stack, setStack] = useState<StackStatusResponse | null>(null);
  const [engagements, setEngagements] = useState<Engagement[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [runningKind, setRunningKind] = useState<string | null>(null);
  const [opsNotice, setOpsNotice] = useState<string | null>(null);
  const { setAfterTitle, setEnd } = usePageHeader();

  const services = useMemo(
    () =>
      SERVICE_NAMES.map((name) => ({
        name,
        service: serviceFromPayload(stack, name),
      })),
    [stack],
  );
  const neo4jBrowserUrl =
    serviceFromPayload(stack, "neo4j")?.url ?? "http://127.0.0.1:7474/browser/";

  const load = useCallback(() => {
    setLoading(true);
    setError(null);
    Promise.allSettled([
      fetchJSON<StackStatusResponse>("/api/stack/status"),
      fetchJSON<EngagementsResponse>("/api/decepticon/engagements"),
    ])
      .then(([stackResult, engagementsResult]) => {
        if (stackResult.status === "fulfilled") {
          setStack(stackResult.value);
        } else {
          setError(String(stackResult.reason));
        }

        if (engagementsResult.status === "fulfilled") {
          setEngagements(engagementsResult.value.engagements ?? []);
        } else if (stackResult.status === "fulfilled") {
          setError(String(engagementsResult.reason));
        }
      })
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  useLayoutEffect(() => {
    const healthyCount = services.filter(({ service }) => serviceTone(service) === "success").length;
    setAfterTitle(
      <Badge tone={healthyCount === services.length ? "success" : "secondary"} className="text-xs">
        {healthyCount}/{services.length} services
      </Badge>,
    );
    setEnd(
      <Button
        type="button"
        ghost
        size="icon"
        onClick={load}
        disabled={loading}
        aria-label="Refresh Decepticon"
      >
        {loading ? <Spinner /> : <RefreshCw />}
      </Button>,
    );
    return () => {
      setAfterTitle(null);
      setEnd(null);
    };
  }, [load, loading, services, setAfterTitle, setEnd]);

  const startOps = async (kind: string) => {
    setRunningKind(kind);
    setError(null);
    setOpsNotice(null);
    try {
      const response = await fetchJSON<OpsResponse>("/api/decepticon/ops", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ kind }),
      });
      setOpsNotice(response.message ?? response.run_id ?? response.status ?? `${kind} started`);
      load();
    } catch (err) {
      setError(String(err));
    } finally {
      setRunningKind(null);
    }
  };

  return (
    <div className="flex min-w-0 max-w-full flex-col gap-4" data-testid="decepticon-page">
      <PluginSlot name="decepticon:top" />

      <section className="grid min-w-0 gap-3 lg:grid-cols-3">
        {services.map(({ name, service }) => {
          const tone = serviceTone(service);
          return (
            <Card key={name} className="min-w-0 overflow-hidden">
              <CardContent className="flex items-start justify-between gap-3 p-4">
                <div className="min-w-0">
                  <div className="flex items-center gap-2">
                    <Server className="h-4 w-4 text-muted-foreground" />
                    <h2 className="font-mondwest text-display text-sm uppercase tracking-[0.12em] text-midground">
                      {name}
                    </h2>
                  </div>
                  <p className="mt-2 truncate text-xs text-text-secondary">
                    {service?.url ?? service?.ports?.join(", ") ?? "no endpoint"}
                  </p>
                </div>
                <Badge tone={tone} className="shrink-0 text-xs">
                  {serviceLabel(service)}
                </Badge>
              </CardContent>
            </Card>
          );
        })}
      </section>

      <Card className="min-w-0 overflow-hidden">
        <CardHeader className="px-4 py-3">
          <div className="flex min-w-0 flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <CardTitle className="flex items-center gap-2 text-sm">
              <Play className="h-4 w-4" />
              Start ops
            </CardTitle>
            {opsNotice && (
              <Badge tone="success" className="w-fit max-w-full truncate text-xs">
                {opsNotice}
              </Badge>
            )}
          </div>
        </CardHeader>
        <CardContent className="flex flex-wrap gap-2 px-4 pb-4">
          {OPS.map(({ kind, label, icon: Icon }) => (
            <Button
              key={kind}
              type="button"
              size="sm"
              onClick={() => startOps(kind)}
              disabled={runningKind !== null}
              prefix={runningKind === kind ? <Spinner /> : <Icon className="h-3.5 w-3.5" />}
            >
              {label}
            </Button>
          ))}
        </CardContent>
      </Card>

      {error && (
        <div className="border border-destructive/20 bg-destructive/10 p-3 text-sm text-destructive">
          {error}
        </div>
      )}

      <div className="grid min-w-0 gap-4 xl:grid-cols-[minmax(0,0.8fr)_minmax(520px,1.2fr)]">
        <Card className="min-w-0 overflow-hidden">
          <CardHeader className="px-4 py-3">
            <CardTitle className="flex items-center gap-2 text-sm">
              <FolderKanban className="h-4 w-4" />
              Engagements
            </CardTitle>
          </CardHeader>
          <CardContent className="p-0">
            {loading && engagements.length === 0 ? (
              <div className="flex min-h-48 items-center justify-center">
                <Spinner className="text-xl text-primary" />
              </div>
            ) : engagements.length === 0 ? (
              <div className="px-4 py-8 text-sm text-muted-foreground">
                No engagements returned by /api/decepticon/engagements.
              </div>
            ) : (
              <div className="divide-y divide-border/60">
                {engagements.map((engagement, index) => (
                  <article
                    key={`${engagement.path ?? engagement.name ?? "engagement"}-${index}`}
                    className="grid gap-2 px-4 py-3"
                  >
                    <div className="flex min-w-0 items-start justify-between gap-3">
                      <div className="min-w-0">
                        <h3 className="truncate text-sm font-medium text-midground">
                          {engagementTitle(engagement)}
                        </h3>
                        <p className="truncate font-mono text-xs text-text-tertiary">
                          {engagement.path ?? "~/HermesVault/Engagements"}
                        </p>
                      </div>
                      <Badge tone="secondary" className="shrink-0 text-xs">
                        {engagement.status ?? `${engagement.files ?? 0} files`}
                      </Badge>
                    </div>
                    {engagement.summary && (
                      <p className="line-clamp-2 text-xs leading-5 text-text-secondary">
                        {engagement.summary}
                      </p>
                    )}
                    {engagement.updated_at && (
                      <span className="text-xs text-text-tertiary">
                        {isoTimeAgo(engagement.updated_at)}
                      </span>
                    )}
                  </article>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        <Card className="min-w-0 overflow-hidden">
          <CardHeader className="px-4 py-3">
            <CardTitle className="flex items-center gap-2 text-sm">
              <Database className="h-4 w-4" />
              Neo4j
            </CardTitle>
          </CardHeader>
          <CardContent className="p-0">
            <iframe
              title="Neo4j browser"
              src={neo4jBrowserUrl}
              className={cn(
                "h-[620px] w-full border-0 bg-black",
                "border-t border-border",
              )}
            />
          </CardContent>
        </Card>
      </div>

      <PluginSlot name="decepticon:bottom" />
    </div>
  );
}
