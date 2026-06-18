import { createServer } from "node:http";
import { SessionManager } from "./sessions.js";

const sessions = new SessionManager();

// Reap expired sessions on a fixed interval so the table doesn't grow forever.
const REAP_INTERVAL_MS = 1000 * 60 * 5;
setInterval(() => sessions.reapExpired(), REAP_INTERVAL_MS).unref();

function json(res, status, body) {
  const payload = JSON.stringify(body);
  res.writeHead(status, {
    "content-type": "application/json",
    "content-length": Buffer.byteLength(payload),
  });
  res.end(payload);
}

const server = createServer((req, res) => {
  const url = new URL(req.url, "http://localhost");

  // POST /sessions { userId } -> issue a session
  if (req.method === "POST" && url.pathname === "/sessions") {
    let raw = "";
    req.on("data", (c) => (raw += c));
    req.on("end", () => {
      try {
        const { userId } = JSON.parse(raw || "{}");
        if (!userId) return json(res, 400, { error: "userId required" });
        return json(res, 201, sessions.create(userId));
      } catch {
        return json(res, 400, { error: "invalid body" });
      }
    });
    return;
  }

  // GET /sessions/:id -> validate
  const match = url.pathname.match(/^\/sessions\/([^/]+)$/);
  if (match) {
    const id = match[1];
    if (req.method === "GET") {
      const record = sessions.validate(id);
      return record
        ? json(res, 200, { id, ...record })
        : json(res, 404, { error: "not found or expired" });
    }
    if (req.method === "DELETE") {
      sessions.revoke(id);
      return json(res, 204, {});
    }
  }

  json(res, 404, { error: "not found" });
});

const PORT = process.env.PORT || 8787;
server.listen(PORT, () => {
  console.log(`session-service listening on :${PORT}`);
});
