import { useMemo, useState } from "react";
import {
  Archive,
  CalendarDays,
  ExternalLink,
  Network,
  RefreshCw,
  Search,
} from "lucide-react";
import { Badge } from "@nous-research/ui/ui/components/badge";
import { Button } from "@nous-research/ui/ui/components/button";
import { Card, CardContent, CardHeader, CardTitle } from "@nous-research/ui/ui/components/card";
import { cn } from "@/lib/utils";

const DEFAULT_CURATOR_URL = "http://localhost:8090";

const CURATOR_ROUTES = [
  { path: "/", label: "List", icon: Archive },
  { path: "/calendar", label: "Calendar", icon: CalendarDays },
  { path: "/search", label: "Search", icon: Search },
  { path: "/graph", label: "Graph", icon: Network },
] as const;

export interface VaultBrowserProps {
  baseUrl?: string;
  className?: string;
}

function joinUrl(baseUrl: string, path: string) {
  const base = baseUrl.replace(/\/+$/, "");
  return `${base}${path}`;
}

export default function VaultBrowser({
  baseUrl = DEFAULT_CURATOR_URL,
  className,
}: VaultBrowserProps) {
  const [route, setRoute] = useState<(typeof CURATOR_ROUTES)[number]["path"]>("/");
  const [nonce, setNonce] = useState(0);
  const iframeUrl = useMemo(
    () => `${joinUrl(baseUrl, route)}?hermes_reload=${nonce}`,
    [baseUrl, nonce, route],
  );

  return (
    <Card className={cn("min-w-0 overflow-hidden", className)}>
      <CardHeader className="px-4 py-3">
        <div className="flex min-w-0 flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex min-w-0 items-center gap-2">
            <CardTitle className="flex items-center gap-2 text-sm">
              <Archive className="h-4 w-4" />
              Vault Browser
            </CardTitle>
            <Badge tone="secondary" className="truncate text-xs">
              {baseUrl}
            </Badge>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            {CURATOR_ROUTES.map(({ path, label, icon: Icon }) => (
              <Button
                key={path}
                type="button"
                size="sm"
                outlined={route !== path}
                prefix={<Icon className="h-3.5 w-3.5" />}
                onClick={() => setRoute(path)}
              >
                {label}
              </Button>
            ))}
            <Button
              type="button"
              ghost
              size="icon"
              onClick={() => setNonce((value) => value + 1)}
              aria-label="Refresh Vault Browser"
            >
              <RefreshCw />
            </Button>
            <a href={joinUrl(baseUrl, route)} target="_blank" rel="noreferrer">
              <Button type="button" ghost size="icon" aria-label="Open Vault Browser">
                <ExternalLink />
              </Button>
            </a>
          </div>
        </div>
      </CardHeader>
      <CardContent className="p-0">
        <iframe
          title="Vault Browser"
          src={iframeUrl}
          className="h-[680px] w-full border-0 border-t border-border bg-black"
        />
      </CardContent>
    </Card>
  );
}
