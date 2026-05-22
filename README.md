# KV-TTLv0.9

A hybrid, concurrent, in-memory key-value database with active TTL and AOF persistence.

## Architecture
* **Core (Go)**: TCP server (port `9000`), thread-safe store, active TTL cleaner, and AOF logging.
* **Gateway (Node.js)**: Rate-limited HTTP proxy (port `8000`) forwarding client requests.
* **Admin CLI (Python)**: Direct TCP terminal shell.

## Setup & Run
1. Install node packages: `cd gateway && npm install`
2. Compile core: `cd go_core && go build`
3. Launch cluster: `python main.py`

## API Gateway (Port 8000)
* **Set Key** (`POST /set`): `{"key": "name", "value": "Alice", "ttl": 10}`
* **Get Key** (`GET /get/:key`)
* **Delete Key** (`DELETE /delete/:key`)

## Direct CLI (Port 9000)
Run `python client.py` to use raw database commands:
* `SET <key> <ttl_seconds> <value>` (0 = no expiry)
* `GET <key>`
* `DEL <key>`
