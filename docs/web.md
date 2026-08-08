# SnipContext Web Server

Run a local web API for browsing and managing snippets. This is useful for integrations, remote access on a trusted network, or programmatic automation.

## Usage

```bash
sc serve --host 127.0.0.1 --port 8000
```

After startup, open the auto-generated docs:

- Swagger UI: `http://127.0.0.1:8000/docs`
- ReDoc: `http://127.0.0.1:8000/redoc`

## Configuration

| Flag | Default | Description |
|------|---------|-------------|
| `--host` | `127.0.0.1` | Bind address |
| `--port` | `8000` | Bind port |

Optional install:

```bash
pip install snipcontext[web]
```

## API Endpoints

- `GET /` — API metadata and docs pointer
- `GET /health` — health check
- `GET /snippets` — list snippets
- `POST /snippets` — create snippet
- `GET /snippets/{id}` — get snippet
- `PUT /snippets/{id}` — update snippet
- `DELETE /snippets/{id}` — delete snippet
- Agent/router endpoints from `agent_card`

## Notes

- The web server reads from the active SnipContext storage/config.
- For remote access, bind to a trusted interface and use transport-level security as needed.
- Start the server from the CLI with `sc serve`, not `sc web`.
