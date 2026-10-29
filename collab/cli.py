"""Run a non-mutating reconciliation on explicitly supplied local files."""
import argparse
import json
import logging
from pathlib import Path
from .reconcile import reconcile


def main() -> None:
    p = argparse.ArgumentParser(description="Offline, synthetic identity reconciliation (dry-run)")
    p.add_argument("--directory", required=True, type=Path)
    p.add_argument("--messaging", required=True, type=Path)
    p.add_argument("--output", type=Path)
    p.add_argument("--log-level", choices=("DEBUG", "INFO", "WARNING"), default="INFO")
    args = p.parse_args()
    logging.basicConfig(level=args.log_level, format="%(levelname)s %(message)s")
    try:
        directory = json.loads(args.directory.read_text(encoding="utf-8"))
        messaging = json.loads(args.messaging.read_text(encoding="utf-8"))
        result = reconcile(directory, messaging)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        p.error(str(exc))
    payload = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload, encoding="utf-8")
        logging.info("Dry-run report created at %s with %s findings", args.output, result["summary"]["findings"])
    else:
        print(payload)


if __name__ == "__main__":
    main()
