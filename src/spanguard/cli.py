"""CLI: `spanguard guard TEXT`, `spanguard up`, `spanguard eval`, `spanguard report`."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="spanguard")
    sub = ap.add_subparsers(dest="cmd", required=True)

    g = sub.add_parser("guard", help="guard one text (stdin or arg)")
    g.add_argument("text", nargs="?")
    g.add_argument("--mode", default=None)
    g.add_argument("--json", action="store_true")

    up = sub.add_parser("up", help="run the gateway + demo UI")
    up.add_argument("--host", default=None)
    up.add_argument("--port", type=int, default=None)

    ev = sub.add_parser("eval", help="run the eval harness over fixture sets")
    ev.add_argument("--detectors", default="rules")
    ev.add_argument("--out", default=None)

    sub.add_parser("report", help="regenerate README benchmark blocks + charts")
    tools_p = sub.add_parser("tools", help="tool-definition scanning (rug-pull detection)")
    tools_sub = tools_p.add_subparsers(dest="tools_cmd", required=True)
    tp_scan = tools_sub.add_parser("scan", help="scan a request body JSON for poisoned tool descriptions")
    tp_scan.add_argument("file", help="request body JSON file (or - for stdin)")
    tp_pin = tools_sub.add_parser("pin", help="pin trusted tool descriptions (write hash file)")
    tp_pin.add_argument("file", help="request body JSON file with the trusted tools array")
    tp_pin.add_argument("--out", default="spanguard-tool-pins.json")
    args = ap.parse_args(argv)

    if args.cmd == "guard":
        from .config import Settings
        from .detect.pipeline import Guard

        s = Settings.from_env()
        guard = Guard(mode=args.mode or s.mode, model_id=s.model_id)
        text = args.text if args.text is not None else sys.stdin.read()
        result = guard.guard(text)
        if args.json:
            print(json.dumps(result.as_dict(), indent=2, ensure_ascii=False))
        else:
            print(result.cleaned)
        return 0

    if args.cmd == "up":
        import uvicorn

        from .config import Settings
        from .gateway.app import app as fast_app

        s = Settings.from_env()
        uvicorn.run(fast_app, host=args.host or s.host, port=args.port or s.port)
        return 0

    if args.cmd == "eval":
        from .eval.cli import run_eval

        run_eval(detectors=args.detectors, out=args.out)
        return 0

    if args.cmd == "tools":
        import sys as _sys

        from .detect.toolscan import scan_tool_defs, write_pins

        if args.file == "-":
            raw = _sys.stdin.read()
        else:
            raw = Path(args.file).read_text(encoding="utf-8")
        body = json.loads(raw)
        if args.tools_cmd == "pin":
            n = write_pins(body, args.out)
            print(f"pinned {n} tool descriptions -> {args.out}")
            return 0
        findings = scan_tool_defs(body)
        print(json.dumps(findings, indent=2, ensure_ascii=False))
        return 1 if findings else 0

    if args.cmd == "report":
        from .eval.report import main as report_main

        report_main()
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
