import { useCallback, useEffect, useLayoutEffect, useMemo, useState } from "react";
import {
  CheckCircle2,
  Copy,
  Monitor,
  Play,
  Plus,
  Radio,
  RefreshCw,
  ShieldCheck,
  Square,
} from "lucide-react";
import { Badge } from "@nous-research/ui/ui/components/badge";
import { Button } from "@nous-research/ui/ui/components/button";
import { Card, CardContent, CardHeader, CardTitle } from "@nous-research/ui/ui/components/card";
import { Label } from "@nous-research/ui/ui/components/label";
import { Select, SelectOption } from "@nous-research/ui/ui/components/select";
import { Spinner } from "@nous-research/ui/ui/components/spinner";
import { Switch } from "@nous-research/ui/ui/components/switch";
import { authedFetch, buildWsAuthParam, fetchJSON, HERMES_BASE_PATH } from "@/lib/api";
import { usePageHeader } from "@/contexts/usePageHeader";
import { PluginSlot } from "@/plugins";

interface CloakProfile {
  id: string;
  name: string;
  active?: boolean;
  status?: "running" | "stopped" | string;
  assigned_to?: string;
  path?: string;
  user_data_dir?: string;
  cdp_url?: string | null;
  novnc_url?: string | null;
  proxy?: string | null;
  timezone?: string | null;
  locale?: string | null;
  platform?: string;
  screen_width?: number;
  screen_height?: number;
  fingerprint_seed?: number;
  humanize?: boolean;
  human_preset?: string;
  geoip?: boolean;
  headless?: boolean;
  launch_args?: string[];
  notes?: string | null;
}

interface CloakProfilesResponse {
  profiles?: CloakProfile[];
  active?: string;
  active_profile?: { id?: string; name?: string; cdp_url?: string | null };
  dependencies?: { ok?: boolean; missing?: string[] };
}

interface ReachChannel {
  status?: string;
  name?: string;
  message?: string;
  tier?: number;
  backends?: string[];
  active_backend?: string | null;
}

interface ReachDoctorResponse {
  ok?: boolean;
  source?: string;
  updated_at?: string;
  channels?: Record<string, ReachChannel>;
}

const DEFAULT_CREATE = {
  name: "",
  assigned_to: "manual",
  proxy: "",
  timezone: "",
  locale: "",
  platform: "windows",
  screen_width: "1920",
  screen_height: "1080",
  humanize: true,
  geoip: false,
  launch_args: "",
  notes: "",
};

function normalizeProfiles(payload: CloakProfilesResponse | CloakProfile[]) {
  if (Array.isArray(payload)) {
    return {
      profiles: payload,
      active:
        payload.find((profile) => profile.active)?.id ??
        payload.find((profile) => profile.active)?.name ??
        payload[0]?.id ??
        "",
      dependencies: undefined,
    };
  }
  const profiles = payload.profiles ?? [];
  const active = payload.active_profile?.id ?? payload.active ?? "";
  return {
    profiles,
    active:
      profiles.find((profile) => profile.id === active || profile.name === active)?.id ??
      profiles.find((profile) => profile.active)?.id ??
      profiles[0]?.id ??
      "",
    dependencies: payload.dependencies,
  };
}

function statusTone(status?: string, active?: boolean) {
  if (active) return "success";
  if (status === "running") return "warning";
  return "secondary";
}

function buildProfilePayload(form: typeof DEFAULT_CREATE) {
  return {
    name: form.name.trim(),
    assigned_to: form.assigned_to.trim() || "manual",
    proxy: form.proxy.trim() || null,
    timezone: form.timezone.trim() || null,
    locale: form.locale.trim() || null,
    platform: form.platform,
    screen_width: Number(form.screen_width) || 1920,
    screen_height: Number(form.screen_height) || 1080,
    humanize: form.humanize,
    geoip: form.geoip,
    launch_args: form.launch_args
      .split("\n")
      .map((line) => line.trim())
      .filter(Boolean),
    notes: form.notes.trim() || null,
  };
}

export default function BrowserPage() {
  const [profiles, setProfiles] = useState<CloakProfile[]>([]);
  const [selectedProfileId, setSelectedProfileId] = useState("");
  const [viewerUrl, setViewerUrl] = useState("");
  const [viewOnly, setViewOnly] = useState(false);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [dependencies, setDependencies] = useState<CloakProfilesResponse["dependencies"]>(undefined);
  const [createOpen, setCreateOpen] = useState(false);
  const [createForm, setCreateForm] = useState(DEFAULT_CREATE);
  const [reachChannels, setReachChannels] = useState<Record<string, ReachChannel>>({});
  const [reachLoading, setReachLoading] = useState(true);
  const { setAfterTitle, setEnd } = usePageHeader();

  const selectedProfile = useMemo(
    () => profiles.find((profile) => profile.id === selectedProfileId) ?? profiles[0],
    [profiles, selectedProfileId],
  );

  const runningCount = profiles.filter((profile) => profile.status === "running").length;

  const loadProfiles = useCallback(() => {
    setLoading(true);
    setError(null);
    fetchJSON<CloakProfilesResponse | CloakProfile[]>("/api/cloak/profiles")
      .then((payload) => {
        const normalized = normalizeProfiles(payload);
        setProfiles(normalized.profiles);
        setDependencies(normalized.dependencies);
        setSelectedProfileId((current) =>
          current && normalized.profiles.some((profile) => profile.id === current)
            ? current
            : normalized.active,
        );
      })
      .catch((err) => {
        setProfiles([]);
        setError(String(err));
      })
      .finally(() => setLoading(false));
  }, []);

  const loadReachChannels = useCallback(() => {
    setReachLoading(true);
    fetchJSON<ReachDoctorResponse>("/api/reach/doctor")
      .then((payload) => setReachChannels(payload.channels ?? {}))
      .catch((err) => setError(String(err)))
      .finally(() => setReachLoading(false));
  }, []);

  useEffect(() => {
    loadProfiles();
    loadReachChannels();
  }, [loadProfiles, loadReachChannels]);

  useEffect(() => {
    let cancelled = false;
    async function resolveViewer() {
      if (!selectedProfile || selectedProfile.status !== "running" || !selectedProfile.novnc_url) {
        setViewerUrl("");
        return;
      }
      const [authName, authValue] = await buildWsAuthParam();
      const wsPath = `${HERMES_BASE_PATH}/api/cloak/profiles/${encodeURIComponent(
        selectedProfile.id,
      )}/vnc-ws`
        .replace(/^\/+/, "")
        .replace(/\/{2,}/g, "/");
      const wsParams = new URLSearchParams({ [authName]: authValue });
      const params = new URLSearchParams({
        autoconnect: "true",
        resize: "remote",
        reconnect: "true",
        view_only: viewOnly ? "1" : "0",
        path: `${wsPath}?${wsParams.toString()}`,
      });
      const url = `${HERMES_BASE_PATH}${selectedProfile.novnc_url}?${params.toString()}`;
      if (!cancelled) setViewerUrl(url);
    }
    resolveViewer().catch((err) => {
      if (!cancelled) setError(String(err));
    });
    return () => {
      cancelled = true;
    };
  }, [selectedProfile, viewOnly]);

  useLayoutEffect(() => {
    setAfterTitle(
      <Badge tone={runningCount > 0 ? "success" : "secondary"} className="text-xs">
        {runningCount} running
      </Badge>,
    );
    setEnd(
      <Button
        type="button"
        ghost
        size="icon"
        onClick={loadProfiles}
        disabled={loading}
        aria-label="Refresh Cloak profiles"
      >
        {loading ? <Spinner /> : <RefreshCw />}
      </Button>,
    );
    return () => {
      setAfterTitle(null);
      setEnd(null);
    };
  }, [loadProfiles, loading, runningCount, setAfterTitle, setEnd]);

  const action = async (profile: CloakProfile, verb: "launch" | "stop" | "activate") => {
    setBusy(`${verb}:${profile.id}`);
    setError(null);
    setNotice(null);
    try {
      const payload = await fetchJSON<{ ok: boolean; profile?: CloakProfile }>(
        `/api/cloak/profiles/${encodeURIComponent(profile.id)}/${verb}`,
        { method: "POST" },
      );
      setNotice(
        verb === "activate"
          ? `${profile.name} is now the Hermes Cloak profile`
          : `${profile.name}: ${verb}`,
      );
      if (payload.profile) {
        setSelectedProfileId(payload.profile.id);
      }
      loadProfiles();
    } catch (err) {
      setError(String(err));
    } finally {
      setBusy(null);
    }
  };

  const createProfile = async () => {
    const payload = buildProfilePayload(createForm);
    if (!payload.name) {
      setError("Profile name is required.");
      return;
    }
    setBusy("create");
    setError(null);
    setNotice(null);
    try {
      const response = await fetchJSON<{ ok: boolean; profile: CloakProfile }>("/api/cloak/profiles", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      setCreateForm(DEFAULT_CREATE);
      setCreateOpen(false);
      setSelectedProfileId(response.profile.id);
      setNotice(`Profile created: ${response.profile.name}`);
      loadProfiles();
    } catch (err) {
      setError(String(err));
    } finally {
      setBusy(null);
    }
  };

  const uploadCookies = async (file: File | null) => {
    if (!file || !selectedProfile) return;
    const form = new FormData();
    form.set("file", file);
    form.set("profile", selectedProfile.name);
    setBusy("cookies");
    setError(null);
    setNotice(null);
    try {
      const response = await authedFetch("/api/cloak/cookies/import", {
        method: "POST",
        body: form,
      });
      if (!response.ok) {
        throw new Error(`${response.status}: ${await response.text()}`);
      }
      setNotice("Cookies imported into active CDP session");
    } catch (err) {
      setError(String(err));
    } finally {
      setBusy(null);
    }
  };

  const copyCdp = async () => {
    if (!selectedProfile?.cdp_url) return;
    await navigator.clipboard?.writeText(selectedProfile.cdp_url);
    setNotice("CDP URL copied");
  };

  return (
    <div className="flex min-h-0 min-w-0 max-w-full flex-1 flex-col gap-3" data-testid="browser-page">
      <PluginSlot name="browser:top" />

      {dependencies && !dependencies.ok && (
        <div className="border border-warning/30 bg-warning/10 px-3 py-2 text-sm text-warning">
          Missing native Cloak dependencies: {(dependencies.missing ?? []).join(", ")}
        </div>
      )}

      <div className="grid min-h-0 min-w-0 flex-1 gap-3 xl:grid-cols-[300px_minmax(0,1fr)_360px]">
        <aside className="flex min-h-0 min-w-0 flex-col overflow-hidden border border-border bg-background-base">
          <div className="flex items-center justify-between gap-2 border-b border-border px-3 py-2">
            <div className="flex min-w-0 items-center gap-2">
              <ShieldCheck className="h-4 w-4 shrink-0" />
              <span className="truncate text-sm font-medium">Cloak profiles</span>
            </div>
            <Button type="button" ghost size="icon" onClick={() => setCreateOpen((value) => !value)} aria-label="Create profile">
              <Plus />
            </Button>
          </div>

          {createOpen && (
            <div className="grid gap-2 border-b border-border p-3 text-xs">
              <label className="grid gap-1">
                <span className="text-text-tertiary">Name</span>
                <input
                  value={createForm.name}
                  onChange={(event) => setCreateForm((form) => ({ ...form, name: event.target.value }))}
                  className="h-8 border border-input bg-transparent px-2 text-sm"
                  placeholder="acc-main-01"
                />
              </label>
              <div className="grid grid-cols-2 gap-2">
                <label className="grid gap-1">
                  <span className="text-text-tertiary">Width</span>
                  <input
                    value={createForm.screen_width}
                    onChange={(event) => setCreateForm((form) => ({ ...form, screen_width: event.target.value }))}
                    className="h-8 border border-input bg-transparent px-2"
                  />
                </label>
                <label className="grid gap-1">
                  <span className="text-text-tertiary">Height</span>
                  <input
                    value={createForm.screen_height}
                    onChange={(event) => setCreateForm((form) => ({ ...form, screen_height: event.target.value }))}
                    className="h-8 border border-input bg-transparent px-2"
                  />
                </label>
              </div>
              <label className="grid gap-1">
                <span className="text-text-tertiary">Proxy</span>
                <input
                  value={createForm.proxy}
                  onChange={(event) => setCreateForm((form) => ({ ...form, proxy: event.target.value }))}
                  className="h-8 border border-input bg-transparent px-2"
                  placeholder="socks5://user:pass@host:1080"
                />
              </label>
              <div className="grid grid-cols-2 gap-2">
                <label className="grid gap-1">
                  <span className="text-text-tertiary">Locale</span>
                  <input
                    value={createForm.locale}
                    onChange={(event) => setCreateForm((form) => ({ ...form, locale: event.target.value }))}
                    className="h-8 border border-input bg-transparent px-2"
                    placeholder="en-US"
                  />
                </label>
                <label className="grid gap-1">
                  <span className="text-text-tertiary">Timezone</span>
                  <input
                    value={createForm.timezone}
                    onChange={(event) => setCreateForm((form) => ({ ...form, timezone: event.target.value }))}
                    className="h-8 border border-input bg-transparent px-2"
                    placeholder="Europe/Kiev"
                  />
                </label>
              </div>
              <label className="grid gap-1">
                <span className="text-text-tertiary">Extra args</span>
                <textarea
                  value={createForm.launch_args}
                  onChange={(event) => setCreateForm((form) => ({ ...form, launch_args: event.target.value }))}
                  className="min-h-16 resize-y border border-input bg-transparent px-2 py-1"
                  placeholder="--fingerprint-noise=false"
                />
              </label>
              <div className="flex items-center justify-between gap-2">
                <Label className="text-xs">Humanize</Label>
                <Switch
                  checked={createForm.humanize}
                  onCheckedChange={(checked) => setCreateForm((form) => ({ ...form, humanize: checked }))}
                />
              </div>
              <div className="flex items-center justify-between gap-2">
                <Label className="text-xs">GeoIP</Label>
                <Switch
                  checked={createForm.geoip}
                  onCheckedChange={(checked) => setCreateForm((form) => ({ ...form, geoip: checked }))}
                />
              </div>
              <Button type="button" size="sm" onClick={createProfile} disabled={busy === "create"} prefix={busy === "create" ? <Spinner /> : <Plus className="h-3.5 w-3.5" />}>
                Create profile
              </Button>
            </div>
          )}

          <div className="min-h-0 flex-1 overflow-y-auto">
            {loading && profiles.length === 0 ? (
              <div className="flex min-h-32 items-center justify-center">
                <Spinner className="text-xl text-primary" />
              </div>
            ) : profiles.length === 0 ? (
              <div className="p-4 text-sm text-muted-foreground">No Cloak profiles yet.</div>
            ) : (
              profiles.map((profile) => (
                <button
                  key={profile.id}
                  type="button"
                  onClick={() => setSelectedProfileId(profile.id)}
                  className={`grid w-full gap-1 border-b border-border/60 px-3 py-3 text-left hover:bg-midground/5 ${
                    selectedProfile?.id === profile.id ? "bg-midground/10" : ""
                  }`}
                >
                  <div className="flex min-w-0 items-center justify-between gap-2">
                    <span className="truncate text-sm font-medium text-midground">{profile.name}</span>
                    <Badge tone={statusTone(profile.status, profile.active)} className="shrink-0 text-xs">
                      {profile.active ? "active" : profile.status ?? "stopped"}
                    </Badge>
                  </div>
                  <div className="truncate text-xs text-text-tertiary">
                    seed {profile.fingerprint_seed} / {profile.screen_width}x{profile.screen_height}
                  </div>
                </button>
              ))
            )}
          </div>
        </aside>

        <main className="flex min-h-0 min-w-0 flex-col overflow-hidden border border-border bg-black">
          <div className="flex min-w-0 items-center justify-between gap-3 border-b border-border bg-background-base px-3 py-2">
            <div className="flex min-w-0 items-center gap-2">
              <Monitor className="h-4 w-4 shrink-0" />
              <span className="truncate text-sm font-medium">
                {selectedProfile ? selectedProfile.name : "Cloak workspace"}
              </span>
              {selectedProfile?.cdp_url && (
                <Badge tone="secondary" className="hidden text-xs md:inline-flex">
                  {selectedProfile.cdp_url.replace("http://", "")}
                </Badge>
              )}
            </div>
            <div className="flex shrink-0 items-center gap-2">
              <Button type="button" ghost size="icon" onClick={() => setViewOnly((value) => !value)} aria-label="Toggle VNC control">
                {viewOnly ? <ShieldCheck /> : <Monitor />}
              </Button>
              <Button type="button" ghost size="icon" onClick={loadProfiles} aria-label="Reload profiles">
                <RefreshCw />
              </Button>
            </div>
          </div>

          {viewerUrl ? (
            <iframe
              key={viewerUrl}
              title="Cloak profile desktop"
              src={viewerUrl}
              className="min-h-[680px] w-full flex-1 border-0 bg-black"
            />
          ) : (
            <div className="flex min-h-[680px] flex-1 items-center justify-center bg-black text-sm text-text-tertiary">
              {selectedProfile ? "Launch this profile to open its desktop." : "Select or create a Cloak profile."}
            </div>
          )}
        </main>

        <aside className="grid min-h-0 min-w-0 content-start gap-3 overflow-y-auto">
          <Card className="min-w-0 overflow-hidden">
            <CardHeader className="px-4 py-3">
              <CardTitle className="flex items-center gap-2 text-sm">
                <ShieldCheck className="h-4 w-4" />
                Selected profile
              </CardTitle>
            </CardHeader>
            <CardContent className="grid gap-3 px-4 pb-4">
              <div className="grid gap-2">
                <Label htmlFor="cloak-profile">Profile</Label>
                <Select id="cloak-profile" value={selectedProfileId} disabled={loading || profiles.length === 0} onValueChange={setSelectedProfileId}>
                  <SelectOption value="">{loading ? "Loading profiles" : "Select profile"}</SelectOption>
                  {profiles.map((profile) => (
                    <SelectOption key={profile.id} value={profile.id}>
                      {profile.name}
                    </SelectOption>
                  ))}
                </Select>
              </div>

              {selectedProfile && (
                <>
                  <div className="grid gap-1 text-xs text-text-secondary">
                    <div className="flex items-center justify-between gap-2">
                      <span>Status</span>
                      <Badge tone={statusTone(selectedProfile.status, selectedProfile.active)} className="text-xs">
                        {selectedProfile.active ? "active" : selectedProfile.status ?? "stopped"}
                      </Badge>
                    </div>
                    <div className="flex items-center justify-between gap-2">
                      <span>Humanize</span>
                      <span>{selectedProfile.humanize ? "on" : "off"}</span>
                    </div>
                    <div className="flex items-center justify-between gap-2">
                      <span>GeoIP</span>
                      <span>{selectedProfile.geoip ? "on" : "off"}</span>
                    </div>
                    <div className="flex items-center justify-between gap-2">
                      <span>Assigned</span>
                      <span className="truncate">{selectedProfile.assigned_to ?? "manual"}</span>
                    </div>
                  </div>

                  <div className="grid grid-cols-2 gap-2">
                    {selectedProfile.status === "running" ? (
                      <Button type="button" size="sm" outlined onClick={() => action(selectedProfile, "stop")} disabled={busy === `stop:${selectedProfile.id}`} prefix={busy === `stop:${selectedProfile.id}` ? <Spinner /> : <Square className="h-3.5 w-3.5" />}>
                        Stop
                      </Button>
                    ) : (
                      <Button type="button" size="sm" onClick={() => action(selectedProfile, "launch")} disabled={busy === `launch:${selectedProfile.id}`} prefix={busy === `launch:${selectedProfile.id}` ? <Spinner /> : <Play className="h-3.5 w-3.5" />}>
                        Launch
                      </Button>
                    )}
                    <Button type="button" size="sm" outlined onClick={() => action(selectedProfile, "activate")} disabled={busy === `activate:${selectedProfile.id}`} prefix={busy === `activate:${selectedProfile.id}` ? <Spinner /> : <CheckCircle2 className="h-3.5 w-3.5" />}>
                      Use
                    </Button>
                  </div>

                  <Button type="button" size="sm" outlined onClick={copyCdp} disabled={!selectedProfile.cdp_url} prefix={<Copy className="h-3.5 w-3.5" />}>
                    Copy CDP URL
                  </Button>

                  <label className="grid gap-2">
                    <span className="text-xs text-text-tertiary">Import cookies</span>
                    <input
                      type="file"
                      accept=".json,.txt,.cookies"
                      disabled={busy === "cookies"}
                      onChange={(event) => uploadCookies(event.target.files?.[0] ?? null)}
                      className="flex h-10 w-full border border-input bg-transparent px-3 py-2 text-sm file:mr-3 file:border-0 file:bg-transparent file:text-sm file:text-midground"
                    />
                  </label>
                </>
              )}
            </CardContent>
          </Card>

          <ReachChannelsCard channels={reachChannels} loading={reachLoading} onRefresh={loadReachChannels} />
        </aside>
      </div>

      {error && <div className="border border-destructive/20 bg-destructive/10 p-3 text-sm text-destructive">{error}</div>}
      {notice && <div className="border border-success/20 bg-success/10 p-3 text-sm text-success">{notice}</div>}

      <PluginSlot name="browser:bottom" />
    </div>
  );
}

function ReachChannelsCard({
  channels,
  loading,
  onRefresh,
}: {
  channels: Record<string, ReachChannel>;
  loading: boolean;
  onRefresh: () => void;
}) {
  const rows = Object.entries(channels).sort(([a], [b]) => a.localeCompare(b));

  return (
    <Card className="min-w-0 overflow-hidden">
      <CardHeader className="px-4 py-3">
        <div className="flex min-w-0 items-center justify-between gap-3">
          <CardTitle className="flex items-center gap-2 text-sm">
            <Radio className="h-4 w-4" />
            Reach Channels
          </CardTitle>
          <Button type="button" ghost size="icon" onClick={onRefresh} disabled={loading} aria-label="Refresh Reach channels">
            {loading ? <Spinner /> : <RefreshCw />}
          </Button>
        </div>
      </CardHeader>
      <CardContent className="p-0">
        {loading && rows.length === 0 ? (
          <div className="flex min-h-36 items-center justify-center">
            <Spinner className="text-xl text-primary" />
          </div>
        ) : rows.length === 0 ? (
          <div className="px-4 py-6 text-sm text-muted-foreground">No Reach channels returned.</div>
        ) : (
          <div className="max-h-[420px] overflow-auto">
            <table className="w-full min-w-[440px] text-left text-xs">
              <thead className="sticky top-0 border-b border-border bg-background-base text-text-tertiary">
                <tr>
                  <th className="px-3 py-2 font-normal">Channel</th>
                  <th className="px-3 py-2 font-normal">Status</th>
                  <th className="px-3 py-2 font-normal">Backend</th>
                  <th className="px-3 py-2 font-normal">Tier</th>
                </tr>
              </thead>
              <tbody>
                {rows.map(([id, channel]) => {
                  const tone =
                    channel.status === "ok"
                      ? "success"
                      : channel.status === "warn"
                        ? "warning"
                        : channel.status === "off"
                          ? "secondary"
                          : "destructive";
                  return (
                    <tr key={id} className="border-b border-border/60">
                      <td className="max-w-40 px-3 py-2">
                        <div className="truncate font-medium text-midground">{id}</div>
                        <div className="truncate text-text-tertiary">{channel.name ?? id}</div>
                      </td>
                      <td className="px-3 py-2">
                        <Badge tone={tone} className="text-xs">
                          {channel.status ?? "unknown"}
                        </Badge>
                      </td>
                      <td className="max-w-36 px-3 py-2 text-text-secondary">
                        <span className="block truncate">{channel.active_backend ?? channel.backends?.[0] ?? "-"}</span>
                      </td>
                      <td className="px-3 py-2 text-text-secondary">{channel.tier ?? "-"}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
