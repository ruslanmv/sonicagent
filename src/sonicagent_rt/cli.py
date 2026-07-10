"""Command-line entry point."""
import argparse
import uvicorn

def main() -> None:
    parser = argparse.ArgumentParser(prog="SonicAgent")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--reload", action="store_true")
    args = parser.parse_args()
    uvicorn.run("sonicagent_rt.app:app", host=args.host, port=args.port, reload=args.reload)
