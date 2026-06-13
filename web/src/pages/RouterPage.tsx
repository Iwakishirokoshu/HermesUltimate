import { useCallback, useEffect, useLayoutEffect, useMemo, useState } from "react";
import {
  Boxes,
  ExternalLink,
  Globe,
  RefreshCw,
  Router,
  Server,
} from "lucide-react";
import { Badge } from "@nous-research/ui/ui/components/badge";
import { Button } from "@nous-research/ui/ui/components/button";
import { Card, CardContent, CardHeader, CardTitle } from "@nous-research/ui/ui/components/card";
import { Spinner } from "@nous-research/ui/ui/components/spinner";
import { usePageHeader } from "@/contexts/usePageHeader";
import { PluginSlot } from "@/plugins";

const ROUTER_URL = "http://localhost:20128";
const MODELS_URL = `${ROUTER_URL}/v1/models`;

interface RouterModel {
  id: string;
  object?: string;
  owned_by?: string;
  provider?: string;
}

interface RouterModelsResponse {
  data?: RouterModel[];
}

function providerLabel(model: RouterModel) {
  return model.provider ?? model.owned_by ?? model.object ?? "router";
}

export default function RouterPage() {
  const [models, setModels] = useState<RouterModel[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [iframeNonce, setIframeNonce] = useState(0);
  const { setAfterTitle, setEnd } = usePageHeader();

  const groupedModels = useMemo(() => {
    const groups = new Map<string, RouterModel[]>();
    for (const model of models) {
      const provider = providerLabel(model);
      const group = groups.get(provider) ?? [];
      group.push(model);
      groups.set(provider, group);
    }
    return Array.from(groups.entries()).sort(([a], [b]) => a.localeCompare(b));
  }, [models]);

  const loadModels = useCallback(() => {
    setLoading(true);
    setError(null);
    fetch(MODELS_URL)
      .then(async (response) => {
        if (!response.ok) {
          throw new Error(`${response.status}: ${await response.text()}`);
        }
        return (await response.json()) as RouterModelsResponse;
      })
      .then((payload) => setModels(payload.data ?? []))
      .catch((err) => {
        setModels([]);
        setError(String(err));
      })
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    loadModels();
  }, [loadModels]);

  useLayoutEffect(() => {
    setAfterTitle(
      <Badge tone={models.length > 0 ? "success" : "secondary"} className="text-xs">
        {models.length} models
      </Badge>,
    );
    setEnd(
      <div className="flex items-center gap-2">
        <Button
          type="button"
          ghost
          size="icon"
          onClick={loadModels}
          disabled={loading}
          aria-label="Refresh router models"
        >
          {loading ? <Spinner /> : <RefreshCw />}
        </Button>
        <a href={ROUTER_URL} target="_blank" rel="noreferrer">
          <Button type="button" ghost size="icon" aria-label="Open 9router">
            <ExternalLink />
          </Button>
        </a>
      </div>,
    );
    return () => {
      setAfterTitle(null);
      setEnd(null);
    };
  }, [loadModels, loading, models.length, setAfterTitle, setEnd]);

  return (
    <div className="flex min-w-0 max-w-full flex-col gap-4" data-testid="router-page">
      <PluginSlot name="router:top" />

      <div className="grid min-w-0 gap-4 xl:grid-cols-[minmax(0,1fr)_360px]">
        <Card className="min-w-0 overflow-hidden">
          <CardHeader className="px-4 py-3">
            <div className="flex min-w-0 items-center justify-between gap-3">
              <CardTitle className="flex items-center gap-2 text-sm">
                <Router className="h-4 w-4" />
                9router
              </CardTitle>
              <Button
                type="button"
                ghost
                size="icon"
                onClick={() => setIframeNonce((value) => value + 1)}
                aria-label="Reload 9router iframe"
              >
                <RefreshCw />
              </Button>
            </div>
          </CardHeader>
          <CardContent className="p-0">
            <iframe
              key={iframeNonce}
              title="9router UI"
              src={ROUTER_URL}
              className="h-[720px] w-full border-0 border-t border-border bg-black"
            />
          </CardContent>
        </Card>

        <aside className="min-w-0">
          <Card className="min-w-0 overflow-hidden">
            <CardHeader className="px-4 py-3">
              <CardTitle className="flex items-center gap-2 text-sm">
                <Boxes className="h-4 w-4" />
                Models
              </CardTitle>
            </CardHeader>
            <CardContent className="p-0">
              {error && (
                <div className="border-b border-destructive/20 bg-destructive/10 p-3 text-sm text-destructive">
                  {error}
                </div>
              )}

              {loading && models.length === 0 ? (
                <div className="flex min-h-48 items-center justify-center">
                  <Spinner className="text-xl text-primary" />
                </div>
              ) : models.length === 0 ? (
                <div className="px-4 py-8 text-sm text-muted-foreground">
                  No models returned by 9router.
                </div>
              ) : (
                <div className="divide-y divide-border/60">
                  {groupedModels.map(([provider, items]) => (
                    <section key={provider} className="grid gap-2 p-4">
                      <div className="flex items-center justify-between gap-2">
                        <h2 className="flex min-w-0 items-center gap-2 text-xs uppercase tracking-[0.1em] text-text-tertiary">
                          <Server className="h-3.5 w-3.5 shrink-0" />
                          <span className="truncate">{provider}</span>
                        </h2>
                        <Badge tone="secondary" className="shrink-0 text-xs">
                          {items.length}
                        </Badge>
                      </div>
                      <div className="grid gap-1.5">
                        {items.map((model) => (
                          <div
                            key={model.id}
                            className="flex min-w-0 items-center gap-2 border border-border/50 px-2 py-1.5"
                          >
                            <Globe className="h-3.5 w-3.5 shrink-0 text-muted-foreground" />
                            <span className="truncate font-mono text-xs text-text-secondary">
                              {model.id}
                            </span>
                          </div>
                        ))}
                      </div>
                    </section>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </aside>
      </div>

      <PluginSlot name="router:bottom" />
    </div>
  );
}
