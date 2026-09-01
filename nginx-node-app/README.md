# nginx + Node.js Tally CRUD Stack

A two-service Docker Compose stack: an nginx reverse proxy in front of a
Node.js CRUD API for **tallies** — counters that can be attached to reminders
via a `reminderId` field. Data persists to a named volume as JSON.

```
client ──:8080──> nginx ──:3000──> node tally API ──> tally-data volume
                  (proxy)          (internal only)     (JSON store)
```

## Layout

```
nginx-node-app/
├── docker-compose.yml      # the stack: two services, one network, one volume
├── app/
│   ├── Dockerfile          # node:20-alpine, non-root, healthcheck
│   ├── package.json
│   └── server.js           # stdlib-only CRUD API on :3000
└── nginx/
    ├── Dockerfile          # nginx:1.27-alpine with config baked in
    └── default.conf        # reverse-proxy config -> app:3000
```

## Run locally

```sh
cd nginx-node-app
docker compose up --build
```

## Run as a stack on Dockhand

The compose file is written to work in stack managers (Dockhand, Dockge,
Portainer):

- **Relative build contexts** (`./app`, `./nginx`): create the stack from this
  repository (subpath `nginx-node-app/`) or copy this directory into the
  stack's folder so Dockhand can build both images.
- **No `container_name`, no bind mounts, no host paths** — the stack manager
  controls naming and placement; state lives in the named volume `tally-data`.
- **Single published port**: `8080 -> nginx:80`. Change the host side in
  `docker-compose.yml` if 8080 is taken on your Docker host.
- Both services use `restart: unless-stopped`, so the stack comes back up
  with the host.

## API

| Method | Path | Description |
|--------|------|-------------|
| GET    | `/api/tallies` | List tallies (`?reminderId=...` to filter) |
| POST   | `/api/tallies` | Create — body `{ "name": "...", "count": 0, "reminderId": "..." }` |
| GET    | `/api/tallies/:id` | Read one |
| PATCH  | `/api/tallies/:id` | Update `name`, `count`, and/or `reminderId` |
| DELETE | `/api/tallies/:id` | Delete |
| POST   | `/api/tallies/:id/increment` | Bump count by 1, or body `{ "by": n }` |
| GET    | `/health` | Health/readiness check |

`name` is required on create; `count` defaults to 0 and `reminderId` to
`null`. Attach a tally to a reminder by setting `reminderId` on create or via
PATCH, then fetch a reminder's tallies with `GET /api/tallies?reminderId=...`.

Example session:

```sh
# create a tally attached to a reminder
curl -s -X POST localhost:8080/api/tallies \
  -H 'Content-Type: application/json' \
  -d '{"name":"glasses of water","reminderId":"reminder-42"}'

# bump it
curl -s -X POST localhost:8080/api/tallies/<id>/increment

# all tallies for that reminder
curl -s 'localhost:8080/api/tallies?reminderId=reminder-42'
```

## Notes

- The node service is not published on the host; nginx is the only entry
  point. Uncomment the `ports` block on `app` in `docker-compose.yml` to reach
  it directly at `localhost:3000` while debugging.
- The app has no npm dependencies (Node stdlib only), so builds are fast and
  fully offline after the base image is pulled.
- Storage is a JSON file on the `tally-data` volume, written atomically —
  fine for a single-instance stack; swap in a database service if the tally
  or reminder model grows.
- nginx forwards `Host`, `X-Real-IP`, `X-Forwarded-For`, and
  `X-Forwarded-Proto`, and supports websocket upgrades.
