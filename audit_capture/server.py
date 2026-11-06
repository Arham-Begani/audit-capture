"""Loopback-only local demo. No telemetry, outbound networking, or disk writes."""
from functools import partial
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
from urllib.parse import urlparse
from .core import CONDITIONS, POLICIES, PROFILES, from_dict, generate, run, to_dict
from .import_scores import replay_evidence
from .json_io import loads as strict_loads
from . import __version__

ROOT = Path(__file__).resolve().parents[1]
STATIC = {"/": ("web/index.html", "text/html"), "/app.js": ("web/app.js", "text/javascript"),
          "/style.css": ("web/style.css", "text/css"),
          "/signal.css": ("web/signal.css", "text/css"),
          "/motion.js": ("web/motion.js", "text/javascript"),
          "/fonts/manrope-latin.woff2": ("web/fonts/manrope-latin.woff2", "font/woff2"),
          "/fonts/space-grotesk-latin.woff2": ("web/fonts/space-grotesk-latin.woff2", "font/woff2")}


def unpack_document(data):
    """Parse original uploaded bytes before JS can collapse duplicate keys."""
    if set(data) != {'document', 'fallback_config'} or not isinstance(data['document'], str):
        raise ValueError('Expected a document and fallback_config')
    if len(data['document'].encode('utf-8')) > 128000:
        raise ValueError('Document exceeds 128 KB')
    document = strict_loads(data['document'])
    if not isinstance(document, dict):
        raise ValueError('Expected a scenario object')
    if 'replay_config' in document:
        config = document['replay_config']
    elif isinstance(document.get('result'), dict):
        previous = document['result']
        config = {'policy': previous.get('policy'), 'budget': previous.get('budget'),
                  'audit_seed': previous.get('audit_seed'), 'hard_block': previous.get('hard_block_threshold')}
    else:
        config = data['fallback_config']
    if not isinstance(config, dict) or set(config) != {'policy', 'budget', 'audit_seed', 'hard_block'}:
        raise ValueError('Invalid replay configuration')
    result = {'scenario': document.get('scenario', document), **config}
    for key in ('provenance', 'scenario_sha256', 'original_scenario_sha256'):
        if key in document:
            result[key] = document[key]
    return result


class Handler(BaseHTTPRequestHandler):
    def setup(self):
        super().setup()
        self.connection.settimeout(5)

    def valid_host(self):
        return self.headers.get('Host') in (f'127.0.0.1:{self.server.server_port}',
                                             f'localhost:{self.server.server_port}')

    def log_message(self, *args):
        pass

    def send(self, status, body, content_type="application/json"):
        if not isinstance(body, bytes):
            body = json.dumps(body, allow_nan=False).encode()
        self.send_response(status)
        self.send_header("Content-Type", content_type + "; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if not self.valid_host():
            return self.send(403, {'error': 'Host is not allowed'})
        path = urlparse(self.path).path
        if path in STATIC:
            filename, mime = STATIC[path]
            self.send(200, (ROOT / filename).read_bytes(), mime)
        elif path == '/favicon.ico':
            self.send(204, b'', 'image/x-icon')
        elif path == "/api/meta":
            self.send(200, {"conditions": CONDITIONS, "policies": POLICIES, "profiles": PROFILES,
                            "evidence_type": "constructed_synthetic", "version": __version__})
        elif path == "/api/results":
            results = ROOT / "results/summary.json"
            if results.exists():
                self.send(200, results.read_bytes())
            else:
                self.send(404, {"error": "Run python -m audit_capture.evaluate first."})
        else:
            self.send(404, {"error": "Not found"})

    def do_POST(self):
        if not self.valid_host():
            return self.send(403, {'error': 'Host is not allowed'})
        if self.path not in ("/api/run", "/api/import"):
            return self.send(404, {"error": "Not found"})
        # Prevent cross-origin requests from unrelated websites to localhost.
        origin = self.headers.get("Origin")
        if origin and origin not in (f"http://127.0.0.1:{self.server.server_port}", f"http://localhost:{self.server.server_port}"):
            return self.send(403, {"error": "Origin is not allowed"})
        try:
            if self.headers.get_content_type() != 'application/json' or self.headers.get('Transfer-Encoding'):
                raise ValueError('Use a JSON body with Content-Length')
            length = int(self.headers.get("Content-Length", "0"))
            maximum = 256512 if self.path == '/api/import' else 128000
            if not 1 <= length <= maximum:
                raise ValueError(f'Request must contain 1-{maximum} bytes')
            data = strict_loads(self.rfile.read(length))
            if not isinstance(data, dict):
                raise ValueError("Request must be an object")
            if self.path == "/api/import":
                if 'document' in data:
                    data = unpack_document(data)
                if set(data) - {'scenario', 'policy', 'budget', 'audit_seed', 'hard_block',
                               'provenance', 'provenance_status', 'scenario_sha256', 'original_scenario_sha256'}:
                    raise ValueError('Unknown import fields')
                scenario = from_dict(data["scenario"])
            else:
                if set(data) - {"seed", "condition", "profile", "policy", "budget", "audit_seed", "single_actor", "mandatory", "hard_block"}:
                    raise ValueError("Unknown request fields")
                for flag in ("single_actor", "mandatory"):
                    if flag in data and type(data[flag]) is not bool:
                        raise ValueError(f"{flag} must be boolean")
                scenario = generate(data.get("seed", 42), data.get("condition", "selected_decoys"),
                                    data.get("profile", "overlap"), single_actor=data.get("single_actor", False),
                                    mandatory=data.get("mandatory", False))
            policy, budget, audit_seed = data.get("policy", "top_risk"), data.get("budget", 2), data.get("audit_seed", 42)
            result = run(scenario, policy, budget, audit_seed, data.get("hard_block"))
            comparisons = [run(scenario, p, budget, audit_seed, data.get("hard_block")) for p in POLICIES]
            evidence = replay_evidence(data, scenario)
            self.send(200, {"scenario": to_dict(scenario), "result": result, "comparisons": comparisons,
                            'replay_config': {'policy': policy, 'budget': budget, 'audit_seed': audit_seed,
                                              'hard_block': data.get('hard_block')}, **evidence})
        except (ValueError, TypeError, KeyError, OverflowError, RecursionError, TimeoutError) as exc:
            self.send(400, {"error": str(exc)[:240]})


def serve(port=8768):
    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    print(f"Audit Capture running at http://127.0.0.1:{server.server_port}", flush=True)
    print("Synthetic scores and actions. Press Ctrl+C to stop.", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
