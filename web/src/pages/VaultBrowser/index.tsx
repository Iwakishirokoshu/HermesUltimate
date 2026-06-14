import { useCallback, useEffect, useMemo, useState } from "react";
import type { FormEvent } from "react";
import {
  Archive,
  ChevronRight,
  FileText,
  Folder,
  FolderOpen,
  RefreshCw,
  Search,
} from "lucide-react";
import { Badge } from "@nous-research/ui/ui/components/badge";
import { Button } from "@nous-research/ui/ui/components/button";
import { Card, CardContent, CardHeader, CardTitle } from "@nous-research/ui/ui/components/card";
import { Spinner } from "@nous-research/ui/ui/components/spinner";
import { fetchJSON } from "@/lib/api";
import { cn, isoTimeAgo } from "@/lib/utils";

interface VaultEntry {
  name?: string;
  path?: string;
  type?: "file" | "directory" | string;
  size?: number | null;
  updated_at?: string;
  summary?: string;
}

interface VaultTreeResponse {
  folder?: string;
  root?: string;
  entries?: VaultEntry[];
}

interface VaultReadResponse extends VaultEntry {
  content?: string;
}

interface VaultSearchResponse {
  query?: string;
  results?: VaultSearchResult[];
}

type VaultSearchResult = VaultEntry & { snippet?: string };

export interface VaultBrowserProps {
  className?: string;
}

function entryTitle(entry: VaultEntry) {
  if (entry.name) return entry.name;
  if (!entry.path) return "entry";
  return entry.path.split(/[\\/]/).filter(Boolean).pop() ?? entry.path;
}

function parentFolder(path: string) {
  const parts = path.split("/").filter(Boolean);
  parts.pop();
  return parts.join("/");
}

function formatSize(size?: number | null) {
  if (!size) return "";
  if (size < 1024) return `${size} B`;
  if (size < 1024 * 1024) return `${Math.round(size / 102.4) / 10} KB`;
  return `${Math.round(size / 1024 / 102.4) / 10} MB`;
}

function Breadcrumbs({
  folder,
  onOpen,
}: {
  folder: string;
  onOpen: (folder: string) => void;
}) {
  const parts = folder.split("/").filter(Boolean);
  return (
    <div className="flex min-w-0 flex-wrap items-center gap-1 text-xs text-text-tertiary">
      <button
        type="button"
        className="hover:text-midground"
        onClick={() => onOpen("")}
      >
        Vault
      </button>
      {parts.map((part, index) => {
        const next = parts.slice(0, index + 1).join("/");
        return (
          <span key={next} className="flex min-w-0 items-center gap-1">
            <ChevronRight className="h-3 w-3 shrink-0" />
            <button
              type="button"
              className="max-w-40 truncate hover:text-midground"
              onClick={() => onOpen(next)}
            >
              {part}
            </button>
          </span>
        );
      })}
    </div>
  );
}

export default function VaultBrowser({ className }: VaultBrowserProps) {
  const [folder, setFolder] = useState("");
  const [root, setRoot] = useState("");
  const [entries, setEntries] = useState<VaultEntry[]>([]);
  const [selectedPath, setSelectedPath] = useState("");
  const [selectedFile, setSelectedFile] = useState<VaultReadResponse | null>(null);
  const [query, setQuery] = useState("");
  const [searchResults, setSearchResults] = useState<VaultSearchResult[]>([]);
  const [loadingTree, setLoadingTree] = useState(true);
  const [loadingFile, setLoadingFile] = useState(false);
  const [searching, setSearching] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const directories = useMemo(
    () => entries.filter((entry) => entry.type === "directory"),
    [entries],
  );
  const files = useMemo(
    () => entries.filter((entry) => entry.type !== "directory"),
    [entries],
  );

  const loadTree = useCallback((nextFolder: string) => {
    setLoadingTree(true);
    setError(null);
    fetchJSON<VaultTreeResponse>(
      `/api/vault/tree?folder=${encodeURIComponent(nextFolder)}`,
    )
      .then((payload) => {
        setFolder(payload.folder ?? nextFolder);
        setRoot(payload.root ?? "");
        setEntries(payload.entries ?? []);
      })
      .catch((err) => {
        setEntries([]);
        setError(String(err));
      })
      .finally(() => setLoadingTree(false));
  }, []);

  const loadFile = useCallback((path: string) => {
    setLoadingFile(true);
    setError(null);
    setSelectedPath(path);
    fetchJSON<VaultReadResponse>(`/api/vault/read?path=${encodeURIComponent(path)}`)
      .then((payload) => setSelectedFile(payload))
      .catch((err) => {
        setSelectedFile(null);
        setError(String(err));
      })
      .finally(() => setLoadingFile(false));
  }, []);

  useEffect(() => {
    loadTree("");
  }, [loadTree]);

  const openEntry = (entry: VaultEntry) => {
    const path = entry.path ?? "";
    if (!path) return;
    if (entry.type === "directory") {
      setSearchResults([]);
      loadTree(path);
      return;
    }
    loadFile(path);
  };

  const runSearch = (event?: FormEvent<HTMLFormElement>) => {
    event?.preventDefault();
    const nextQuery = query.trim();
    if (!nextQuery) {
      setSearchResults([]);
      return;
    }
    setSearching(true);
    setError(null);
    fetchJSON<VaultSearchResponse>("/api/vault/search", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query: nextQuery, top_k: 25 }),
    })
      .then((payload) => setSearchResults(payload.results ?? []))
      .catch((err) => {
        setSearchResults([]);
        setError(String(err));
      })
      .finally(() => setSearching(false));
  };

  const clearSearch = () => {
    setQuery("");
    setSearchResults([]);
  };

  return (
    <Card className={cn("flex min-h-0 min-w-0 flex-col overflow-hidden", className)}>
      <CardHeader className="px-4 py-3">
        <div className="flex min-w-0 flex-col gap-3 xl:flex-row xl:items-center xl:justify-between">
          <div className="flex min-w-0 flex-col gap-1">
            <div className="flex min-w-0 items-center gap-2">
              <CardTitle className="flex items-center gap-2 text-sm">
                <Archive className="h-4 w-4" />
                Vault Browser
              </CardTitle>
              {root && (
                <Badge tone="secondary" className="max-w-72 truncate text-xs">
                  {root}
                </Badge>
              )}
            </div>
            <Breadcrumbs folder={folder} onOpen={loadTree} />
          </div>

          <form
            className="flex min-w-0 flex-wrap items-center gap-2"
            onSubmit={runSearch}
          >
            <div className="flex min-w-0 items-center gap-2 border border-border bg-background-base px-2 py-1.5">
              <Search className="h-3.5 w-3.5 shrink-0 text-text-tertiary" />
              <input
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                className="min-w-48 bg-transparent text-sm outline-none placeholder:text-text-tertiary"
                placeholder="Search vault..."
              />
            </div>
            <Button type="submit" size="sm" disabled={searching}>
              {searching ? <Spinner /> : "Search"}
            </Button>
            {searchResults.length > 0 && (
              <Button type="button" size="sm" outlined onClick={clearSearch}>
                List
              </Button>
            )}
            <Button
              type="button"
              ghost
              size="icon"
              onClick={() => loadTree(folder)}
              disabled={loadingTree}
              aria-label="Refresh vault"
            >
              {loadingTree ? <Spinner /> : <RefreshCw />}
            </Button>
          </form>
        </div>
      </CardHeader>

      <CardContent className="min-h-0 flex-1 p-0">
        {error && (
          <div className="border-t border-destructive/20 bg-destructive/10 px-4 py-2 text-sm text-destructive">
            {error}
          </div>
        )}

        <div className="grid min-h-[620px] min-w-0 lg:grid-cols-[340px_minmax(0,1fr)]">
          <aside className="min-h-0 border-t border-border lg:border-r">
            <div className="flex items-center justify-between border-b border-border px-3 py-2">
              <span className="text-xs uppercase text-text-tertiary">
                {searchResults.length > 0 ? "Search results" : "Entries"}
              </span>
              <Badge tone="secondary" className="text-xs">
                {searchResults.length > 0 ? searchResults.length : entries.length}
              </Badge>
            </div>

            <div className="max-h-[620px] overflow-y-auto">
              {loadingTree && entries.length === 0 ? (
                <div className="flex min-h-48 items-center justify-center">
                  <Spinner className="text-xl text-primary" />
                </div>
              ) : searchResults.length > 0 ? (
                <div className="divide-y divide-border/60">
                  {searchResults.map((entry) => (
                    <button
                      key={entry.path}
                      type="button"
                      className={cn(
                        "grid w-full gap-1 px-3 py-2 text-left hover:bg-surface-hover",
                        selectedPath === entry.path && "bg-surface-hover",
                      )}
                      onClick={() => entry.path && loadFile(entry.path)}
                    >
                      <span className="flex min-w-0 items-center gap-2 text-sm text-midground">
                        <FileText className="h-4 w-4 shrink-0 text-primary" />
                        <span className="truncate">{entryTitle(entry)}</span>
                      </span>
                      <span className="truncate font-mono text-xs text-text-tertiary">
                        {entry.path}
                      </span>
                      {entry.snippet && (
                        <span className="line-clamp-2 text-xs leading-5 text-text-secondary">
                          {entry.snippet}
                        </span>
                      )}
                    </button>
                  ))}
                </div>
              ) : entries.length === 0 ? (
                <div className="px-4 py-8 text-sm text-muted-foreground">
                  This vault folder is empty.
                </div>
              ) : (
                <div className="divide-y divide-border/60">
                  {folder && (
                    <button
                      type="button"
                      className="flex w-full items-center gap-2 px-3 py-2 text-left text-sm text-text-secondary hover:bg-surface-hover"
                      onClick={() => loadTree(parentFolder(folder))}
                    >
                      <FolderOpen className="h-4 w-4 shrink-0" />
                      ..
                    </button>
                  )}
                  {[...directories, ...files].map((entry) => (
                    <button
                      key={entry.path ?? entry.name}
                      type="button"
                      className={cn(
                        "grid w-full gap-1 px-3 py-2 text-left hover:bg-surface-hover",
                        selectedPath === entry.path && "bg-surface-hover",
                      )}
                      onClick={() => openEntry(entry)}
                    >
                      <span className="flex min-w-0 items-center gap-2 text-sm text-midground">
                        {entry.type === "directory" ? (
                          <Folder className="h-4 w-4 shrink-0 text-warning" />
                        ) : (
                          <FileText className="h-4 w-4 shrink-0 text-primary" />
                        )}
                        <span className="truncate">{entryTitle(entry)}</span>
                      </span>
                      <span className="flex min-w-0 items-center gap-2 text-xs text-text-tertiary">
                        {entry.updated_at && <span>{isoTimeAgo(entry.updated_at)}</span>}
                        {entry.size != null && <span>{formatSize(entry.size)}</span>}
                      </span>
                      {entry.summary && (
                        <span className="line-clamp-2 text-xs leading-5 text-text-secondary">
                          {entry.summary}
                        </span>
                      )}
                    </button>
                  ))}
                </div>
              )}
            </div>
          </aside>

          <section className="min-h-0 border-t border-border bg-background-base">
            {loadingFile ? (
              <div className="flex min-h-[620px] items-center justify-center">
                <Spinner className="text-xl text-primary" />
              </div>
            ) : selectedFile ? (
              <div className="flex min-h-[620px] min-w-0 flex-col">
                <header className="border-b border-border px-4 py-3">
                  <div className="flex min-w-0 flex-col gap-1">
                    <h2 className="truncate text-sm font-medium text-midground">
                      {entryTitle(selectedFile)}
                    </h2>
                    <p className="truncate font-mono text-xs text-text-tertiary">
                      {selectedFile.path}
                    </p>
                  </div>
                </header>
                <pre className="min-h-0 flex-1 overflow-auto whitespace-pre-wrap break-words p-4 font-mono text-sm leading-6 text-text-secondary">
                  {selectedFile.content || ""}
                </pre>
              </div>
            ) : (
              <div className="flex min-h-[620px] items-center justify-center px-6 text-center text-sm text-muted-foreground">
                Select a vault file to preview it here.
              </div>
            )}
          </section>
        </div>
      </CardContent>
    </Card>
  );
}
