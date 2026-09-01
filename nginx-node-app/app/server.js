// CRUD API for tallies (attachable to reminders via reminderId).
// Node stdlib only — no npm deps. Data persists to a JSON file on a volume.
const http = require('http');
const fs = require('fs');
const path = require('path');
const crypto = require('crypto');
const os = require('os');

const port = process.env.PORT || 3000;
const dataDir = process.env.DATA_DIR || path.join(__dirname, 'data');
const dataFile = path.join(dataDir, 'tallies.json');

// ---- persistence -----------------------------------------------------------

let tallies = new Map();

function loadStore() {
  try {
    const raw = JSON.parse(fs.readFileSync(dataFile, 'utf8'));
    tallies = new Map(raw.map((t) => [t.id, t]));
  } catch {
    tallies = new Map(); // first run, or unreadable file
  }
}

function saveStore() {
  fs.mkdirSync(dataDir, { recursive: true });
  const tmp = dataFile + '.tmp';
  fs.writeFileSync(tmp, JSON.stringify([...tallies.values()], null, 2));
  fs.renameSync(tmp, dataFile); // atomic swap so a crash can't corrupt the file
}

// ---- helpers ---------------------------------------------------------------

function sendJson(res, status, body) {
  res.writeHead(status, { 'Content-Type': 'application/json' });
  res.end(JSON.stringify(body, null, 2));
}

function readBody(req) {
  return new Promise((resolve, reject) => {
    let data = '';
    req.on('data', (chunk) => {
      data += chunk;
      if (data.length > 1e6) {
        reject(new Error('payload too large'));
        req.destroy();
      }
    });
    req.on('end', () => {
      if (!data) return resolve({});
      try {
        resolve(JSON.parse(data));
      } catch {
        reject(new Error('invalid JSON body'));
      }
    });
    req.on('error', reject);
  });
}

// ---- routes ----------------------------------------------------------------
//
// GET    /api/tallies                 list all (?reminderId=... to filter)
// POST   /api/tallies                 create { name, count?, reminderId? }
// GET    /api/tallies/:id             read one
// PATCH  /api/tallies/:id             update name / count / reminderId
// DELETE /api/tallies/:id             remove
// POST   /api/tallies/:id/increment   count += 1 (or body { by: n })

async function handleTallies(req, res, segments, query) {
  const [id, action] = segments;

  if (!id) {
    if (req.method === 'GET') {
      let list = [...tallies.values()];
      if (query.has('reminderId')) {
        list = list.filter((t) => t.reminderId === query.get('reminderId'));
      }
      return sendJson(res, 200, list);
    }
    if (req.method === 'POST') {
      const body = await readBody(req);
      if (!body.name || typeof body.name !== 'string') {
        return sendJson(res, 400, { error: 'name (string) is required' });
      }
      const now = new Date().toISOString();
      const tally = {
        id: crypto.randomUUID(),
        name: body.name,
        count: Number.isInteger(body.count) ? body.count : 0,
        reminderId: typeof body.reminderId === 'string' ? body.reminderId : null,
        createdAt: now,
        updatedAt: now,
      };
      tallies.set(tally.id, tally);
      saveStore();
      return sendJson(res, 201, tally);
    }
    return sendJson(res, 405, { error: 'method not allowed' });
  }

  const tally = tallies.get(id);
  if (!tally) return sendJson(res, 404, { error: 'tally not found' });

  if (action === 'increment' && req.method === 'POST') {
    const body = await readBody(req);
    const by = Number.isInteger(body.by) ? body.by : 1;
    tally.count += by;
    tally.updatedAt = new Date().toISOString();
    saveStore();
    return sendJson(res, 200, tally);
  }
  if (action) return sendJson(res, 404, { error: 'unknown action' });

  switch (req.method) {
    case 'GET':
      return sendJson(res, 200, tally);
    case 'PATCH':
    case 'PUT': {
      const body = await readBody(req);
      if (body.name !== undefined) {
        if (typeof body.name !== 'string' || !body.name) {
          return sendJson(res, 400, { error: 'name must be a non-empty string' });
        }
        tally.name = body.name;
      }
      if (body.count !== undefined) {
        if (!Number.isInteger(body.count)) {
          return sendJson(res, 400, { error: 'count must be an integer' });
        }
        tally.count = body.count;
      }
      if (body.reminderId !== undefined) {
        if (body.reminderId !== null && typeof body.reminderId !== 'string') {
          return sendJson(res, 400, { error: 'reminderId must be a string or null' });
        }
        tally.reminderId = body.reminderId;
      }
      tally.updatedAt = new Date().toISOString();
      saveStore();
      return sendJson(res, 200, tally);
    }
    case 'DELETE':
      tallies.delete(id);
      saveStore();
      return sendJson(res, 204, {});
    default:
      return sendJson(res, 405, { error: 'method not allowed' });
  }
}

// ---- server ----------------------------------------------------------------

const server = http.createServer(async (req, res) => {
  const url = new URL(req.url, `http://${req.headers.host || 'localhost'}`);
  const segments = url.pathname.split('/').filter(Boolean);

  try {
    if (url.pathname === '/health') {
      return sendJson(res, 200, { status: 'ok', tallies: tallies.size });
    }
    if (segments[0] === 'api' && segments[1] === 'tallies') {
      return await handleTallies(req, res, segments.slice(2), url.searchParams);
    }
    if (url.pathname === '/') {
      return sendJson(res, 200, {
        message: 'Tally CRUD API (behind nginx)',
        hostname: os.hostname(),
        endpoints: [
          'GET    /api/tallies?reminderId=...',
          'POST   /api/tallies',
          'GET    /api/tallies/:id',
          'PATCH  /api/tallies/:id',
          'DELETE /api/tallies/:id',
          'POST   /api/tallies/:id/increment',
        ],
      });
    }
    return sendJson(res, 404, { error: 'not found' });
  } catch (err) {
    const status = /JSON|payload/.test(err.message) ? 400 : 500;
    return sendJson(res, status, { error: err.message });
  }
});

loadStore();
server.listen(port, () => {
  console.log(`Tally API listening on port ${port}, data file: ${dataFile}`);
});

// Let `docker stop` / compose down terminate the container promptly.
process.on('SIGTERM', () => server.close(() => process.exit(0)));
process.on('SIGINT', () => server.close(() => process.exit(0)));
