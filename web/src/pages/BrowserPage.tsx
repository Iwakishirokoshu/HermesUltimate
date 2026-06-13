import { useCallback, useEffect, useLayoutEffect, useMemo, useRef, useState } from "react";
import {
  Eye,
  EyeOff,
  FileUp,
  Radio,
  Monitor,
  RefreshCw,
  ShieldCheck,
} from "lucide-react";
import { Badge } from "@nous-research/ui/ui/components/badge";
import { Button } from "@nous-research/ui/ui/components/button";
import { Card, CardContent, CardHeader, CardTitle } from "@nous-research/ui/ui/components/card";
import { Label } from "@nous-research/ui/ui/components/label";
import { Select, SelectOption } from "@nous-research/ui/ui/components/select";
import { Spinner } from "@nous-research/ui/ui/components/spinner";
import { authedFetch, fetchJSON } from "@/lib/api";
import { usePageHeader } from "@/contexts/usePageHeader";
import { PluginSlot } from "@/plugins";

const NOVNC_BASE_URL = "http://localhost:6080/vnc.html";

interface CloakProfile {
  name: string;
  active?: boolean;
  path?: string;
}

interface CloakProfilesResponse {
  profiles?: CloakProfile[];
  active?: string;
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

function vncPassword() {
  const typedWindow = window as typeof window & {
    __HERMES_VNC_PASSWORD__?: string;
  };
  return typedWindow.__HERMES_VNC_PASSWORD__ ?? import.meta.env.VITE_VNC_PASSWORD ?? "";
}

function normalizeProfiles(payload: CloakProfilesResponse | CloakProfile[]) {
  if (Array.isArray(payload)) {
    return {
      profiles: payload,
      active: payload.find((profile) => profile.active)?.name ?? payload[0]?.name ?? "",
    };
  }
  const profiles = payload.profiles ?? [];
  return {
    profiles,
    active: payload.active ?? profiles.find((profile) => profile.active)?.name ?? profiles[0]?.name ?? "",
  };
}

export default function BrowserPage() {
  const [viewOnly, setViewOnly] = useState(true);
  const [iframeNonce, setIframeNonce] = useState(0);
  const [profiles, setProfiles] = useState<CloakProfile[]>([]);
  const [activeProfile, setActiveProfile] = useState("");
  const [profilesLoading, setProfilesLoading] = useState(true);
  const [reachChannels, setReachChannels] = useState<Record<string, ReachChannel>>({});
  const [reachLoading, setReachLoading] = useState(true);
  const [savingProfile, setSavingProfile] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const fileRef = useRef<HTMLInputElement | null>(null);
  const { setAfterTitle, setEnd } = usePageHeader();

  const iframeUrl = useMemo(() => {
    const params = new URLSearchParams({
      autoconnect: "true",
      password: vncPassword(),
      view_only: viewOnly ? "1" : "0",
      hermes_reload: String(iframeNonce),
    });
    return `${NOVNC_BASE_URL}?${params.toString()}`;
  }, [iframeNonce, viewOnly]);

  const loadProfiles = useCallback(() => {
    setProfilesLoading(true);
    setError(null);
    fetchJSON<CloakProfilesResponse | CloakProfile[]>("/api/cloak/profiles")
      .then((payload) => {
        const normalized = normalizeProfiles(payload);
        setProfiles(normalized.profiles);
        setActiveProfile((current) =>
          current && normalized.profiles.some((profile) => profile.name === current)
            ? current
            : normalized.active,
        );
      })
      .catch((err) => {
        setProfiles([]);
        setError(String(err));
      })
      .finally(() => setProfilesLoading(false));
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

  useLayoutEffect(() => {
    setAfterTitle(
      <Badge tone={viewOnly ? "secondary" : "warning"} className="text-xs">
        {viewOnly ? "read-only" : "control"}
      </Badge>,
    );
    setEnd(
      <Button
        type="button"
        ghost
        size="icon"
        onClick={() => setIframeNonce((value) => value + 1)}
        aria-label="Reload noVNC"
      >
        <RefreshCw />
      </Button>,
    );
    return () => {
      setAfterTitle(null);
      setEnd(null);
    };
  }, [setAfterTitle, setEnd, viewOnly]);

  const selectProfile = async (name: string) => {
    setActiveProfile(name);
    if (!name) return;
    setSavingProfile(true);
    setError(null);
    setNotice(null);
    try {
      await fetchJSON<{ ok: boolean }>("/api/cloak/profile/active", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name }),
      });
      setNotice(`Profile active: ${name}`);
      setIframeNonce((value) => value + 1);
    } catch (err) {
      setError(String(err));
    } finally {
      setSavingProfile(false);
    }
  };

  const uploadCookies = async () => {
    const file = fileRef.current?.files?.[0];
    if (!file) {
      setError("Select a cookies file.");
      return;
    }

    const form = new FormData();
    form.set("file", file);
    if (activeProfile) form.set("profile", activeProfile);

    setUploading(true);
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
      setNotice("Cookies imported");
      if (fileRef.current) fileRef.current.value = "";
      setIframeNonce((value) => value + 1);
    } catch (err) {
      setError(String(err));
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="flex min-w-0 max-w-full flex-col gap-4" data-testid="browser-page">
      <PluginSlot name="browser:top" />

      <div className="grid min-w-0 gap-4 xl:grid-cols-[minmax(0,1fr)_360px]">
        <Card className="min-w-0 overflow-hidden">
          <CardHeader className="px-4 py-3">
            <div className="flex min-w-0 flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
              <CardTitle className="flex items-center gap-2 text-sm">
                <Monitor className="h-4 w-4" />
                Cloak Browser
              </CardTitle>
              <div className="flex flex-wrap gap-2">
                <Button
                  type="button"
                  size="sm"
                  outlined={!viewOnly}
                  prefix={<EyeOff className="h-3.5 w-3.5" />}
                  onClick={() => setViewOnly(true)}
                  disabled={viewOnly}
                >
                  Release
                </Button>
                <Button
                  type="button"
                  size="sm"
                  outlined={viewOnly}
                  prefix={<Eye className="h-3.5 w-3.5" />}
                  onClick={() => setViewOnly(false)}
                  disabled={!viewOnly}
                >
                  Take control
                </Button>
              </div>
            </div>
          </CardHeader>
          <CardContent className="p-0">
            <iframe
              key={`${iframeNonce}:${viewOnly ? "view" : "control"}`}
              title="noVNC Cloak Browser"
              src={iframeUrl}
              className="h-[720px] w-full border-0 border-t border-border bg-black"
            />
          </CardContent>
        </Card>

        <aside className="grid h-fit min-w-0 gap-4">
          <Card className="min-w-0 overflow-hidden">
            <CardHeader className="px-4 py-3">
              <CardTitle className="flex items-center gap-2 text-sm">
                <ShieldCheck className="h-4 w-4" />
                Profile
              </CardTitle>
            </CardHeader>
            <CardContent className="grid gap-3 px-4 pb-4">
              <div className="grid gap-2">
                <Label htmlFor="cloak-profile">Active profile</Label>
                <Select
                  id="cloak-profile"
                  value={activeProfile}
                  disabled={profilesLoading || savingProfile || profiles.length === 0}
                  onValueChange={selectProfile}
                >
                  <SelectOption value="">
                    {profilesLoading ? "Loading profiles" : "Select profile"}
                  </SelectOption>
                  {profiles.map((profile) => (
                    <SelectOption key={profile.name} value={profile.name}>
                      {profile.name}
                    </SelectOption>
                  ))}
                </Select>
              </div>
              <Button
                type="button"
                size="sm"
                outlined
                onClick={loadProfiles}
                disabled={profilesLoading}
                prefix={profilesLoading ? <Spinner /> : <RefreshCw className="h-3.5 w-3.5" />}
              >
                Refresh
              </Button>
            </CardContent>
          </Card>

          <Card className="min-w-0 overflow-hidden">
            <CardHeader className="px-4 py-3">
              <CardTitle className="flex items-center gap-2 text-sm">
                <FileUp className="h-4 w-4" />
                Import cookies
              </CardTitle>
            </CardHeader>
            <CardContent className="grid gap-3 px-4 pb-4">
              <input
                ref={fileRef}
                type="file"
                accept=".json,.txt,.cookies"
                disabled={uploading}
                className="flex h-10 w-full border border-input bg-transparent px-3 py-2 text-sm shadow-sm file:mr-3 file:border-0 file:bg-transparent file:text-sm file:text-midground placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-60"
              />
              <Button
                type="button"
                size="sm"
                onClick={uploadCookies}
                disabled={uploading}
                prefix={uploading ? <Spinner /> : <FileUp className="h-3.5 w-3.5" />}
              >
                Import
              </Button>
            </CardContent>
          </Card>

          <ReachChannelsCard
            channels={reachChannels}
            loading={reachLoading}
            onRefresh={loadReachChannels}
          />
        </aside>
      </div>

      {error && (
        <div className="border border-destructive/20 bg-destructive/10 p-3 text-sm text-destructive">
          {error}
        </div>
      )}

      {notice && (
        <div className="border border-success/20 bg-success/10 p-3 text-sm text-success">
          {notice}
        </div>
      )}

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
          <Button
            type="button"
            ghost
            size="icon"
            onClick={onRefresh}
            disabled={loading}
            aria-label="Refresh Reach channels"
          >
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
          <div className="px-4 py-6 text-sm text-muted-foreground">
            No Reach channels returned.
          </div>
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
                        <div className="truncate font-medium text-midground">
                          {id}
                        </div>
                        <div className="truncate text-text-tertiary">
                          {channel.name ?? id}
                        </div>
                      </td>
                      <td className="px-3 py-2">
                        <Badge tone={tone} className="text-xs">
                          {channel.status ?? "unknown"}
                        </Badge>
                      </td>
                      <td className="max-w-36 px-3 py-2 text-text-secondary">
                        <span className="block truncate">
                          {channel.active_backend ?? channel.backends?.[0] ?? "-"}
                        </span>
                      </td>
                      <td className="px-3 py-2 text-text-secondary">
                        {channel.tier ?? "-"}
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
  );
}
