import Database from "better-sqlite3";
import { mkdirSync } from "node:fs";
import { dirname } from "node:path";

/**
 * SessionCache — persistent key/value store for session records.
 *
 * Backed by SQLite. Each session is a row keyed by its id, with the
 * serialized payload and an expiry timestamp.
 */
export class SessionCache {
  constructor(dbPath = "./data/sessions.db") {
    mkdirSync(dirname(dbPath), { recursive: true });

    this.db = new Database(dbPath);
    this.db.pragma("journal_mode = WAL");
    this.db.pragma("synchronous = NORMAL");

    this.db.exec(`
      CREATE TABLE IF NOT EXISTS sessions (
        id         TEXT PRIMARY KEY,
        payload    TEXT NOT NULL,
        expires_at INTEGER NOT NULL
      );
      CREATE INDEX IF NOT EXISTS idx_sessions_expiry
        ON sessions (expires_at);
    `);

    this._get = this.db.prepare(
      "SELECT payload, expires_at FROM sessions WHERE id = ?",
    );
    this._set = this.db.prepare(`
      INSERT INTO sessions (id, payload, expires_at)
      VALUES (@id, @payload, @expires_at)
      ON CONFLICT(id) DO UPDATE SET
        payload    = excluded.payload,
        expires_at = excluded.expires_at
    `);
    this._del = this.db.prepare("DELETE FROM sessions WHERE id = ?");
    this._sweep = this.db.prepare("DELETE FROM sessions WHERE expires_at <= ?");
  }

  get(id) {
    const row = this._get.get(id);
    if (!row) return null;
    if (row.expires_at <= Date.now()) {
      this._del.run(id);
      return null;
    }
    return JSON.parse(row.payload);
  }

  set(id, value, ttlMs = 1000 * 60 * 30) {
    this._set.run({
      id,
      payload: JSON.stringify(value),
      expires_at: Date.now() + ttlMs,
    });
  }

  delete(id) {
    this._del.run(id);
  }

  sweepExpired() {
    return this._sweep.run(Date.now()).changes;
  }

  close() {
    this.db.close();
  }
}
