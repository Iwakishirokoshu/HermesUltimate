#!/usr/bin/env bash
set -euo pipefail

CONTAINER="${NINEROUTER_CONTAINER:-hermes-9router}"
DB_PATH="${NINEROUTER_DB_PATH:-}"

if ! command -v docker >/dev/null 2>&1; then
  echo "[9router-auth] docker is not installed or not on PATH" >&2
  exit 1
fi

if ! docker inspect "$CONTAINER" >/dev/null 2>&1; then
  echo "[9router-auth] container not found: $CONTAINER" >&2
  exit 1
fi

if [ "$(docker inspect -f '{{.State.Running}}' "$CONTAINER")" != "true" ]; then
  echo "[9router-auth] container is not running: $CONTAINER" >&2
  exit 1
fi

repair_data_permissions() {
  docker exec -u root "$CONTAINER" sh -lc '
    data_dir="${DATA_DIR:-/app/data}"
    mkdir -p "$data_dir/db"
    if id node >/dev/null 2>&1; then
      chown -R node:node "$data_dir"
      chmod -R u+rwX,g+rwX "$data_dir"
    else
      chmod -R a+rwX "$data_dir"
    fi
  '
}

repair_data_permissions

docker exec -i "$CONTAINER" node - "$DB_PATH" <<'NODE'
const fs = require("fs");
const os = require("os");
const path = require("path");

const requestedPath = process.argv[2] || "";
const candidates = [
  requestedPath,
  process.env.DATA_DIR ? path.join(process.env.DATA_DIR, "db", "data.sqlite") : "",
  "/data/db/data.sqlite",
  "/app/data/db/data.sqlite",
  path.join(os.homedir(), ".9router", "db", "data.sqlite"),
].filter(Boolean);

let Database;
try {
  Database = require("better-sqlite3");
} catch (err) {
  console.error(`[9router-auth] better-sqlite3 is unavailable: ${err.message}`);
  process.exit(1);
}

const dbPath = candidates.find((candidate) => fs.existsSync(candidate)) || candidates[0];
if (!dbPath) {
  console.error("[9router-auth] could not determine SQLite database path");
  process.exit(1);
}

fs.mkdirSync(path.dirname(dbPath), { recursive: true });
const db = new Database(dbPath);
db.exec("CREATE TABLE IF NOT EXISTS settings (id INTEGER PRIMARY KEY CHECK (id = 1), data TEXT NOT NULL)");

const row = db.prepare("SELECT data FROM settings WHERE id = 1").get();
let data = {};

if (row && row.data) {
  try {
    data = JSON.parse(row.data);
  } catch (err) {
    console.error(`[9router-auth] invalid settings JSON: ${err.message}`);
    process.exit(1);
  }
}

data.requireLogin = false;
data.authMode = data.authMode || "password";
delete data.password;

db.prepare(
  "INSERT INTO settings(id, data) VALUES(1, ?) ON CONFLICT(id) DO UPDATE SET data = excluded.data",
).run(JSON.stringify(data));

console.log(JSON.stringify({ ok: true, requireLogin: data.requireLogin, hasPassword: Boolean(data.password) }));
NODE

repair_data_permissions

echo "[9router-auth] password login disabled for $CONTAINER"

if [ "${NINEROUTER_RESTART_AFTER_AUTH:-1}" != "0" ]; then
  docker restart "$CONTAINER" >/dev/null
  echo "[9router-auth] restarted $CONTAINER"
fi
