import { useCallback, useEffect, useLayoutEffect, useState } from "react";
import {
  Bot,
  KeyRound,
  RefreshCw,
  Save,
  ShieldCheck,
  Users,
} from "lucide-react";
import { Badge } from "@nous-research/ui/ui/components/badge";
import { Button } from "@nous-research/ui/ui/components/button";
import { Card, CardContent, CardHeader, CardTitle } from "@nous-research/ui/ui/components/card";
import { Input } from "@nous-research/ui/ui/components/input";
import { Label } from "@nous-research/ui/ui/components/label";
import { Select, SelectOption } from "@nous-research/ui/ui/components/select";
import { Spinner } from "@nous-research/ui/ui/components/spinner";
import { api, fetchJSON } from "@/lib/api";
import type { MessagingPlatform } from "@/lib/api";
import { usePageHeader } from "@/contexts/usePageHeader";
import { PluginSlot } from "@/plugins";

interface GatewayBotInfo {
  id: string;
  name?: string;
  username?: string;
  default_soul?: string;
  allowed_users?: string[];
  token?: string;
  token_masked?: string;
  enabled?: boolean;
  source?: "api" | "platform";
}

interface GatewayBotsResponse {
  bots?: GatewayBotInfo[];
}

const SOUL_OPTIONS = ["default", "red"] as const;

function normalizeBots(payload: GatewayBotsResponse | GatewayBotInfo[]) {
  const raw = Array.isArray(payload) ? payload : (payload.bots ?? []);
  return raw.map((bot, index) => ({
    ...bot,
    id: bot.id || bot.username || bot.name || `bot-${index + 1}`,
    source: "api" as const,
  }));
}

function splitAllowedUsers(value: string | null | undefined) {
  if (!value || value.includes("•") || value.includes("вЂў") || value.includes("*")) {
    return [];
  }
  return value
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
}

function fallbackFromPlatforms(platforms: MessagingPlatform[]): GatewayBotInfo[] {
  const telegram = platforms.find((platform) => platform.id === "telegram");
  if (!telegram) return [];
  const token = telegram.env_vars.find((item) => item.key === "TELEGRAM_BOT_TOKEN");
  const allowed = telegram.env_vars.find((item) => item.key === "TELEGRAM_ALLOWED_USERS");
  return [
    {
      id: "telegram",
      name: telegram.name,
      default_soul: "default",
      allowed_users: splitAllowedUsers(allowed?.redacted_value),
      token_masked: token?.redacted_value ?? (token?.is_set ? "••••••" : "not set"),
      enabled: telegram.enabled,
      source: "platform",
    },
  ];
}

export default function BotsPage() {
  const [bots, setBots] = useState<GatewayBotInfo[]>([]);
  const [fallbackBots, setFallbackBots] = useState<GatewayBotInfo[]>([]);
  const [loading, setLoading] = useState(true);
  const [savingId, setSavingId] = useState<string | null>(null);
  const [allowedDrafts, setAllowedDrafts] = useState<Record<string, string>>({});
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const { setAfterTitle, setEnd } = usePageHeader();

  const displayedBots = bots.length > 0 ? bots : fallbackBots;

  const load = useCallback(() => {
    setLoading(true);
    setError(null);
    setNotice(null);
    return Promise.allSettled([
      fetchJSON<GatewayBotsResponse | GatewayBotInfo[]>("/api/gateway/bots"),
      api.getMessagingPlatforms(),
    ])
      .then(([botsResult, platformsResult]) => {
        if (botsResult.status === "fulfilled") {
          setBots(normalizeBots(botsResult.value));
        } else {
          setBots([]);
          setError(String(botsResult.reason));
        }

        if (platformsResult.status === "fulfilled") {
          setFallbackBots(fallbackFromPlatforms(platformsResult.value.platforms));
        }
      })
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  useLayoutEffect(() => {
    setAfterTitle(
      <Badge tone={displayedBots.length > 0 ? "success" : "secondary"} className="text-xs">
        {displayedBots.length} bots
      </Badge>,
    );
    setEnd(
      <Button
        type="button"
        ghost
        size="icon"
        onClick={() => void load()}
        disabled={loading}
        aria-label="Refresh bots"
      >
        {loading ? <Spinner /> : <RefreshCw />}
      </Button>,
    );
    return () => {
      setAfterTitle(null);
      setEnd(null);
    };
  }, [displayedBots.length, load, loading, setAfterTitle, setEnd]);

  const updateBot = async (
    bot: GatewayBotInfo,
    changes: { default_soul?: string; allowed_users?: string[] },
  ) => {
    setSavingId(bot.id);
    setError(null);
    setNotice(null);
    setBots((prev) =>
      prev.map((item) => (item.id === bot.id ? { ...item, ...changes } : item)),
    );
    try {
      await fetchJSON<{ ok: boolean }>(
        `/api/gateway/bots/${encodeURIComponent(bot.id)}`,
        {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(changes),
        },
      );
      setNotice(`Saved ${bot.name ?? bot.id}`);
      await load();
    } catch (err) {
      setError(String(err));
    } finally {
      setSavingId(null);
    }
  };

  const saveAllowedUsers = (bot: GatewayBotInfo) => {
    const raw = allowedDrafts[bot.id] ?? (bot.allowed_users ?? []).join(", ");
    const allowedUsers = raw
      .split(",")
      .map((value) => value.trim())
      .filter(Boolean);
    void updateBot(bot, { allowed_users: allowedUsers });
  };

  return (
    <div className="flex min-w-0 max-w-full flex-col gap-4" data-testid="bots-page">
      <PluginSlot name="bots:top" />

      {error && (
        <div className="border border-warning/30 bg-warning/10 p-3 text-sm text-warning">
          {error}
        </div>
      )}

      {notice && (
        <div className="border border-success/20 bg-success/10 p-3 text-sm text-success">
          {notice}
        </div>
      )}

      {loading && displayedBots.length === 0 ? (
        <div className="flex items-center justify-center py-24">
          <Spinner className="text-2xl text-primary" />
        </div>
      ) : displayedBots.length === 0 ? (
        <Card>
          <CardContent className="py-12 text-center text-sm text-muted-foreground">
            No bots returned.
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-4 xl:grid-cols-2">
          {displayedBots.map((bot) => {
            const token = bot.token_masked ?? bot.token ?? "not set";
            const allowedUsers = bot.allowed_users ?? [];
            const draft = allowedDrafts[bot.id] ?? allowedUsers.join(", ");
            const busy = savingId === bot.id;
            return (
              <Card key={bot.id} className="min-w-0 overflow-hidden">
                <CardHeader className="px-4 py-3">
                  <div className="flex min-w-0 items-start justify-between gap-3">
                    <CardTitle className="flex min-w-0 items-center gap-2 text-sm">
                      <Bot className="h-4 w-4 shrink-0" />
                      <span className="truncate">
                        {bot.username ? `@${bot.username}` : bot.name ?? bot.id}
                      </span>
                    </CardTitle>
                    <div className="flex shrink-0 gap-2">
                      <Badge tone={bot.enabled === false ? "secondary" : "success"}>
                        {bot.enabled === false ? "disabled" : "enabled"}
                      </Badge>
                      {bot.source === "platform" && <Badge tone="outline">platform</Badge>}
                    </div>
                  </div>
                </CardHeader>
                <CardContent className="grid gap-4 px-4 pb-4">
                  <div className="grid gap-2">
                    <Label htmlFor={`bots-soul-${bot.id}`}>default_soul</Label>
                    <Select
                      id={`bots-soul-${bot.id}`}
                      value={bot.default_soul ?? "default"}
                      disabled={busy}
                      onValueChange={(value) => updateBot(bot, { default_soul: value })}
                    >
                      {SOUL_OPTIONS.map((soul) => (
                        <SelectOption key={soul} value={soul}>
                          {soul}
                        </SelectOption>
                      ))}
                    </Select>
                  </div>

                  <div className="grid gap-2">
                    <Label className="flex items-center gap-2">
                      <Users className="h-3.5 w-3.5" />
                      allowed_users
                    </Label>
                    <div className="flex flex-wrap gap-2">
                      {allowedUsers.length > 0 ? (
                        allowedUsers.map((user) => (
                          <span
                            key={user}
                            className="border border-border px-2 py-1 font-courier text-xs text-text-secondary"
                          >
                            {user}
                          </span>
                        ))
                      ) : (
                        <span className="text-xs text-muted-foreground">none</span>
                      )}
                    </div>
                    <div className="flex flex-col gap-2 sm:flex-row">
                      <Input
                        value={draft}
                        onChange={(event) =>
                          setAllowedDrafts((prev) => ({
                            ...prev,
                            [bot.id]: event.target.value,
                          }))
                        }
                        placeholder="comma-separated Telegram user IDs"
                        className="font-courier"
                      />
                      <Button
                        type="button"
                        size="sm"
                        outlined
                        disabled={busy}
                        onClick={() => saveAllowedUsers(bot)}
                        prefix={busy ? <Spinner /> : <Save className="h-4 w-4" />}
                      >
                        Save
                      </Button>
                    </div>
                  </div>

                  <div className="flex min-w-0 items-center gap-2 text-xs text-muted-foreground">
                    <KeyRound className="h-3.5 w-3.5 shrink-0" />
                    <span className="truncate font-courier">{token}</span>
                  </div>

                  <div className="flex items-center gap-2 text-xs text-muted-foreground">
                    <ShieldCheck className="h-3.5 w-3.5" />
                    <span>{bot.id}</span>
                  </div>
                </CardContent>
              </Card>
            );
          })}
        </div>
      )}

      <PluginSlot name="bots:bottom" />
    </div>
  );
}
