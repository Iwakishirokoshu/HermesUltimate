import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { MonitorDot } from "lucide-react";
import { buildWsUrl } from "@/lib/api";
import { cn } from "@/lib/utils";

type CloakActivityState = "idle" | "active" | "stale" | "error";

interface ActivitySidebarIndicatorProps {
  collapsed?: boolean;
  onNavigate?: () => void;
}

function normalizeActivity(value: unknown): CloakActivityState {
  if (typeof value === "string") {
    const lowered = value.toLowerCase();
    if (lowered === "active") return "active";
    if (lowered === "stale") return "stale";
    if (lowered === "error") return "error";
    return "idle";
  }

  if (value && typeof value === "object") {
    const record = value as Record<string, unknown>;
    return normalizeActivity(record.state ?? record.status ?? record.activity);
  }

  return "idle";
}

function stateDotClass(state: CloakActivityState) {
  if (state === "active") return "bg-warning";
  if (state === "stale" || state === "error") return "bg-destructive";
  return "bg-muted-foreground";
}

export default function ActivitySidebarIndicator({
  collapsed = false,
  onNavigate,
}: ActivitySidebarIndicatorProps) {
  const navigate = useNavigate();
  const [state, setState] = useState<CloakActivityState>("idle");

  useEffect(() => {
    let socket: WebSocket | null = null;
    let cancelled = false;

    buildWsUrl("/api/ws/cloak-activity")
      .then((url) => {
        if (cancelled) return;
        socket = new WebSocket(url);
        socket.onopen = () => setState("idle");
        socket.onmessage = (event) => {
          try {
            setState(normalizeActivity(JSON.parse(event.data)));
          } catch {
            setState(normalizeActivity(event.data));
          }
        };
        socket.onerror = () => setState("error");
        socket.onclose = () => setState((current) =>
          current === "active" ? "stale" : current,
        );
      })
      .catch(() => setState("error"));

    return () => {
      cancelled = true;
      socket?.close();
    };
  }, []);

  const label = useMemo(() => `Cloak ${state}`, [state]);

  return (
    <button
      type="button"
      aria-label={label}
      onClick={() => {
        navigate("/browser");
        onNavigate?.();
      }}
      className={cn(
        "group/cloak relative flex w-full items-center gap-3",
        "px-5 py-2.5",
        "font-mondwest text-display text-xs tracking-[0.1em]",
        "whitespace-nowrap text-text-secondary transition-colors",
        "hover:text-midground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-midground",
        collapsed && "lg:justify-center lg:px-0",
      )}
    >
      <span className="relative flex h-3.5 w-3.5 shrink-0 items-center justify-center">
        <MonitorDot className="h-3.5 w-3.5" />
        <span
          aria-hidden
          className={cn(
            "absolute -right-0.5 -top-0.5 h-1.5 w-1.5 rounded-full ring-1 ring-background-base",
            stateDotClass(state),
            state === "active" && "animate-pulse",
          )}
        />
      </span>
      <span
        className={cn(
          "truncate uppercase transition-opacity duration-300",
          collapsed ? "lg:hidden" : "lg:block",
        )}
      >
        Cloak {state}
      </span>
      <span
        aria-hidden
        className="absolute inset-y-0.5 left-1.5 right-1.5 bg-midground opacity-0 pointer-events-none transition-opacity duration-200 group-hover/cloak:opacity-5"
      />
    </button>
  );
}
