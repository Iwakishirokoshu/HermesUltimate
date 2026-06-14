import {
  useCallback,
  useEffect,
  useLayoutEffect,
  useMemo,
  useState,
} from "react";
import {
  CheckCircle2,
  FileCode2,
  RefreshCw,
  Save,
  Sparkles,
} from "lucide-react";
import { Badge } from "@nous-research/ui/ui/components/badge";
import { Button } from "@nous-research/ui/ui/components/button";
import { Card, CardContent, CardHeader, CardTitle } from "@nous-research/ui/ui/components/card";
import { Input } from "@nous-research/ui/ui/components/input";
import { Label } from "@nous-research/ui/ui/components/label";
import { Spinner } from "@nous-research/ui/ui/components/spinner";
import { buildWsUrl, fetchJSON } from "@/lib/api";
import { cn } from "@/lib/utils";
import { usePageHeader } from "@/contexts/usePageHeader";
import { PluginSlot } from "@/plugins";

interface SoulRecord {
  name: string;
  backend?: string;
  soul_md?: string;
  allowed_toolsets?: string[];
  langgraph_url?: string | null;
  vault_load?: Record<string, unknown> | null;
  yaml?: string;
  raw_yaml?: string;
  active?: boolean;
  active_chat_ids?: string[];
}

interface ActiveSoulRecord {
  chat_id: string;
  soul_name?: string;
  name?: string;
  updated_at?: string;
}

interface SoulsResponse {
  souls?: SoulRecord[];
  active?: Record<string, string> | ActiveSoulRecord[];
  active_soul?: string;
  active_chat_id?: string;
  chat_id?: string;
}

type WsState = "connecting" | "live" | "offline";

const DEFAULT_CHAT_ID = "default";

function encodeSoulName(name: string) {
  return encodeURIComponent(name);
}

function soulYaml(soul: SoulRecord | undefined) {
  if (!soul) return "";
  if (typeof soul.yaml === "string") return soul.yaml;
  if (typeof soul.raw_yaml === "string") return soul.raw_yaml;

  return [
    `name: ${soul.name}`,
    `backend: ${soul.backend ?? "hermes"}`,
    `soul_md: ${soul.soul_md ?? `souls/${soul.name}/SOUL.md`}`,
    "allowed_toolsets:",
    ...(soul.allowed_toolsets ?? []).map((toolset) => `  - ${toolset}`),
  ].join("\n");
}

function resolveActiveSoul(
  payload: SoulsResponse | null,
  chatId: string,
): string | null {
  if (!payload) return null;
  const active = payload.active;

  if (Array.isArray(active)) {
    const row = active.find((item) => item.chat_id === chatId);
    return row?.soul_name ?? row?.name ?? null;
  }

  if (active && typeof active === "object") {
    return active[chatId] ?? null;
  }

  if (!payload.active_soul) return null;
  if (!payload.active_chat_id && !payload.chat_id) return payload.active_soul;
  return payload.active_chat_id === chatId || payload.chat_id === chatId
    ? payload.active_soul
    : null;
}

function formatToolsets(toolsets: string[] | undefined) {
  if (!toolsets?.length) return "none";
  return toolsets.join(", ");
}

export default function SoulsPage() {
  const [chatId, setChatId] = useState(DEFAULT_CHAT_ID);
  const [payload, setPayload] = useState<SoulsResponse | null>(null);
  const [selected, setSelected] = useState<string | null>(null);
  const [yamlText, setYamlText] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [wsState, setWsState] = useState<WsState>("connecting");
  const { setAfterTitle, setEnd } = usePageHeader();

  const souls = useMemo(() => payload?.souls ?? [], [payload]);
  const activeSoul = useMemo(
    () => resolveActiveSoul(payload, chatId),
    [payload, chatId],
  );
  const selectedSoul = useMemo(
    () => souls.find((soul) => soul.name === selected),
    [selected, souls],
  );

  const loadSouls = useCallback(() => {
    setLoading(true);
    setError(null);
    fetchJSON<SoulsResponse>("/api/souls")
      .then((nextPayload) => {
        const nextSouls = nextPayload.souls ?? [];
        setPayload(nextPayload);
        setSelected((current) => {
          if (current && nextSouls.some((soul) => soul.name === current)) {
            return current;
          }
          return nextSouls[0]?.name ?? null;
        });
      })
      .catch((err) => setError(String(err)))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    loadSouls();
  }, [loadSouls]);

  useEffect(() => {
    setYamlText(soulYaml(selectedSoul));
  }, [selectedSoul]);

  useEffect(() => {
    let socket: WebSocket | null = null;
    let closed = false;

    setWsState("connecting");
    buildWsUrl("/api/ws/souls")
      .then((url) => {
        if (closed) return;
        socket = new WebSocket(url);
        socket.onopen = () => setWsState("live");
        socket.onmessage = () => loadSouls();
        socket.onerror = () => setWsState("offline");
        socket.onclose = () => setWsState("offline");
      })
      .catch(() => setWsState("offline"));

    return () => {
      closed = true;
      socket?.close();
    };
  }, [loadSouls]);

  useLayoutEffect(() => {
    setAfterTitle(
      <span className="flex items-center gap-2">
        <Badge tone={wsState === "live" ? "success" : "secondary"} className="text-xs">
          <span
            className={cn(
              "mr-1 inline-block h-1.5 w-1.5 rounded-full bg-current",
              wsState === "live" && "animate-pulse",
            )}
          />
          {wsState}
        </Badge>
        {activeSoul && (
          <Badge tone="secondary" className="text-xs">
            {chatId}: {activeSoul}
          </Badge>
        )}
      </span>,
    );
    setEnd(
      <Button
        type="button"
        ghost
        size="icon"
        onClick={loadSouls}
        disabled={loading}
        aria-label="Refresh souls"
      >
        {loading ? <Spinner /> : <RefreshCw />}
      </Button>,
    );
    return () => {
      setAfterTitle(null);
      setEnd(null);
    };
  }, [activeSoul, chatId, loadSouls, loading, setAfterTitle, setEnd, wsState]);

  const handleSave = async () => {
    if (!selectedSoul) return;
    setSaving(true);
    setError(null);
    setNotice(null);
    try {
      await fetchJSON<{ ok: boolean }>(`/api/souls/${encodeSoulName(selectedSoul.name)}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ yaml: yamlText }),
      });
      setNotice(`Saved ${selectedSoul.name}`);
      loadSouls();
    } catch (err) {
      setError(String(err));
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="flex min-w-0 max-w-full flex-col gap-4" data-testid="souls-page">
      <PluginSlot name="souls:top" />

      <div className="grid min-w-0 gap-4 xl:grid-cols-[minmax(0,1fr)_minmax(360px,0.85fr)]">
        <Card className="min-w-0 overflow-hidden">
          <CardHeader className="px-4 py-3">
            <div className="flex min-w-0 flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
              <CardTitle className="flex items-center gap-2 text-sm">
                <Sparkles className="h-4 w-4" />
                Souls
              </CardTitle>
              <div className="flex min-w-0 items-center gap-2">
                <Label htmlFor="souls-chat-id" className="shrink-0 text-xs">
                  chat_id
                </Label>
                <Input
                  id="souls-chat-id"
                  value={chatId}
                  onChange={(event) => setChatId(event.target.value || DEFAULT_CHAT_ID)}
                  className="h-8 w-44"
                />
              </div>
            </div>
          </CardHeader>

          <CardContent className="p-0">
            {error && (
              <div className="border-b border-destructive/20 bg-destructive/10 p-3 text-sm text-destructive">
                {error}
              </div>
            )}

            {notice && (
              <div className="border-b border-success/20 bg-success/10 p-3 text-sm text-success">
                {notice}
              </div>
            )}

            {loading && souls.length === 0 ? (
              <div className="flex min-h-56 items-center justify-center">
                <Spinner className="text-xl text-primary" />
              </div>
            ) : souls.length === 0 ? (
              <div className="px-4 py-10 text-center text-sm text-muted-foreground">
                No souls returned by /api/souls.
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full min-w-[760px] text-left text-sm">
                  <thead className="border-b border-border text-xs uppercase tracking-[0.08em] text-text-tertiary">
                    <tr>
                      <th className="px-4 py-2 font-normal">Name</th>
                      <th className="px-4 py-2 font-normal">Backend</th>
                      <th className="px-4 py-2 font-normal">Tools</th>
                      <th className="px-4 py-2 font-normal">SOUL.md</th>
                      <th className="px-4 py-2 font-normal">Active</th>
                    </tr>
                  </thead>
                  <tbody>
                    {souls.map((soul) => {
                      const active =
                        soul.active ||
                        soul.name === activeSoul ||
                        soul.active_chat_ids?.includes(chatId);
                      return (
                        <tr
                          key={soul.name}
                          className={cn(
                            "border-b border-border/60 transition-colors hover:bg-muted/20",
                            selected === soul.name && "bg-muted/30",
                          )}
                        >
                          <td className="px-4 py-3">
                            <button
                              type="button"
                              className="flex items-center gap-2 text-left font-medium text-midground"
                              onClick={() => setSelected(soul.name)}
                            >
                              {soul.name}
                            </button>
                          </td>
                          <td className="px-4 py-3 text-text-secondary">
                            {soul.backend ?? "hermes"}
                          </td>
                          <td className="px-4 py-3 text-text-secondary">
                            {formatToolsets(soul.allowed_toolsets)}
                          </td>
                          <td className="px-4 py-3 font-mono text-xs text-text-secondary">
                            {soul.soul_md ?? "-"}
                          </td>
                          <td className="px-4 py-3">
                            {active ? (
                              <Badge tone="success" className="text-xs">
                                <CheckCircle2 className="mr-1 h-3 w-3" />
                                active
                              </Badge>
                            ) : (
                              <span className="text-xs text-text-tertiary">idle</span>
                            )}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </CardContent>
        </Card>

        <Card className="min-w-0 overflow-hidden">
          <CardHeader className="px-4 py-3">
            <div className="flex min-w-0 items-center justify-between gap-3">
              <CardTitle className="flex min-w-0 items-center gap-2 text-sm">
                <FileCode2 className="h-4 w-4 shrink-0" />
                <span className="truncate">
                  {selectedSoul ? `${selectedSoul.name}.yaml` : "soul.yaml"}
                </span>
              </CardTitle>
              <Button
                type="button"
                size="sm"
                onClick={handleSave}
                disabled={!selectedSoul || saving}
                prefix={saving ? <Spinner /> : <Save className="h-3.5 w-3.5" />}
              >
                {saving ? "Saving" : "Save"}
              </Button>
            </div>
          </CardHeader>
          <CardContent className="p-0">
            <textarea
              className="flex min-h-[520px] w-full resize-y border-t border-border bg-transparent px-4 py-3 font-mono text-sm leading-relaxed placeholder:text-muted-foreground focus-visible:outline-none"
              value={yamlText}
              onChange={(event) => setYamlText(event.target.value)}
              spellCheck={false}
              disabled={!selectedSoul}
              placeholder="Select a soul."
            />
          </CardContent>
        </Card>
      </div>

      <PluginSlot name="souls:bottom" />
    </div>
  );
}
