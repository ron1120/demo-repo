from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from .diagnose import MODES, diagnose_run, diagnose_text, prepare
from .evaluate import evaluate, format_report
from .models import Diagnosis
from .slack import build_message, post


def load_known_flaky(path: str | None) -> tuple[str, ...]:
    if not path:
        return ()
    lines = Path(path).read_text(encoding="utf-8").splitlines()
    return tuple(line.strip() for line in lines if line.strip() and not line.startswith("#"))


def format_diagnosis(d: Diagnosis) -> str:
    lines = [f"Category:  {d.category}  (confidence: {d.confidence}, via {d.source})", f"Summary:   {d.summary}"]
    if d.evidence:
        lines.append("Evidence:")
        lines += [f"  - {e}" for e in d.evidence]
    lines.append(f"Next step: {d.next_step}")
    if d.redactions:
        lines.append(f"({d.redactions} secret-like values were redacted before analysis)")
    return "\n".join(lines)


def cmd_diagnose(args) -> int:
    known = load_known_flaky(args.known_flaky)
    if args.log_file:
        text = Path(args.log_file).read_text(encoding="utf-8", errors="replace")
        d = diagnose_text(text, mode=args.mode, known_flaky=known)
    elif args.repo and args.run_id:
        d, _ = diagnose_run(args.repo, args.run_id, mode=args.mode, known_flaky=known)
    else:
        print("error: give --log-file, or --repo and --run-id", file=sys.stderr)
        return 2
    print(json.dumps(d.to_dict(), indent=2) if args.json else format_diagnosis(d))
    return 0


def cmd_notify(args) -> int:
    known = load_known_flaky(args.known_flaky)
    d, meta = diagnose_run(args.repo, args.run_id, mode=args.mode, known_flaky=known)
    payload = build_message(d, meta, f"https://github.com/{args.repo}/actions/runs/{args.run_id}")
    webhook = os.environ.get("SLACK_WEBHOOK_URL")
    if args.dry_run or not webhook:
        if not args.dry_run:
            print("warning: SLACK_WEBHOOK_URL is not set; printing instead of posting", file=sys.stderr)
        print(json.dumps(payload, indent=2))
        return 0
    post(webhook, payload)
    print(f"Posted diagnosis for run {args.run_id} to Slack ({d.category}, {d.confidence})")
    return 0


def cmd_download(args) -> int:
    from .github import GitHubClient

    _, log_text = GitHubClient().fetch_failure(args.repo, args.run_id)
    text, count = prepare(log_text)
    Path(args.out).write_text(text, encoding="utf-8")
    print(f"Wrote {args.out} ({count} secret-like values redacted)")
    return 0


def cmd_build_dataset(args) -> int:
    from .dataset import build_dataset
    from .github import GitHubClient

    added = build_dataset(GitHubClient(), args.repo, Path(args.out), workflow=args.workflow)
    print(f"Added {len(added)} labelled runs to {args.out}/labels.json")
    return 0


def cmd_eval(args) -> int:
    result = evaluate(Path(args.labels), mode=args.mode, known_flaky=load_known_flaky(args.known_flaky))
    print(json.dumps(result, indent=2) if args.json else format_report(result))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="triage", description="Diagnose failed GitHub Actions runs.")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("diagnose", help="Diagnose one failed run (from GitHub) or a saved log file.")
    p.add_argument("--repo", help="owner/name")
    p.add_argument("--run-id", type=int)
    p.add_argument("--log-file")
    p.add_argument("--mode", choices=MODES, default="hybrid")
    p.add_argument("--known-flaky", help="File with one known-flaky test id (or substring) per line.")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_diagnose)

    p = sub.add_parser("notify", help="Diagnose a failed run and post the result to Slack (SLACK_WEBHOOK_URL).")
    p.add_argument("--repo", required=True)
    p.add_argument("--run-id", type=int, required=True)
    p.add_argument("--mode", choices=MODES, default="hybrid")
    p.add_argument("--known-flaky")
    p.add_argument("--dry-run", action="store_true", help="Print the Slack payload instead of posting it.")
    p.set_defaults(func=cmd_notify)

    p = sub.add_parser("download", help="Save the redacted log of a failed run to a file.")
    p.add_argument("--repo", required=True)
    p.add_argument("--run-id", type=int, required=True)
    p.add_argument("--out", required=True)
    p.set_defaults(func=cmd_download)

    p = sub.add_parser("build-dataset", help="Download and auto-label the demo repo's failed runs.")
    p.add_argument("--repo", required=True)
    p.add_argument("--out", default="samples")
    p.add_argument("--workflow", default="ci.yml")
    p.set_defaults(func=cmd_build_dataset)

    p = sub.add_parser("eval", help="Score the classifier against a labelled set.")
    p.add_argument("--labels", default="samples/labels.json")
    p.add_argument("--mode", choices=MODES, default="hybrid")
    p.add_argument("--known-flaky")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_eval)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)
