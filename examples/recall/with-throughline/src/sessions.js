import { randomUUID } from "node:crypto";
import { SessionCache } from "./cache.js";

/**
 * SessionManager — issues, validates, and revokes sessions on top of the
 * SessionCache. Knows nothing about the storage backend beyond the cache API.
 */
export class SessionManager {
  constructor(cache = new SessionCache()) {
    this.cache = cache;
  }

  create(userId, { ttlMs } = {}) {
    const id = randomUUID();
    const record = {
      userId,
      createdAt: Date.now(),
      lastSeen: Date.now(),
    };
    this.cache.set(id, record, ttlMs);
    return { id, ...record };
  }

  validate(id) {
    const record = this.cache.get(id);
    if (!record) return null;
    record.lastSeen = Date.now();
    this.cache.set(id, record);
    return record;
  }

  revoke(id) {
    this.cache.delete(id);
  }

  reapExpired() {
    return this.cache.sweepExpired();
  }
}
