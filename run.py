import argparse
from audit_capture.server import serve

parser = argparse.ArgumentParser(description="Run the Audit Capture local demo")
parser.add_argument("--port", type=int, default=8768)
args = parser.parse_args()
if not 1 <= args.port <= 65535:
    parser.error("port must be 1-65535")
serve(args.port)
