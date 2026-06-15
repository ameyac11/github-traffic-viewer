import argparse
import sys
import os
import csv

from github_traffic.core import (
    validate_token, 
    get_all_repos, 
    get_repo_traffic, 
    build_row, 
    DEFAULT_CSV
)
from github_traffic.automation import sync_monthly_traffic

# This routes terminal commands to the correct package functions.

def _sep(char="─", width=90):
    print(char * width)

def _row(cols, widths):
    print("  ".join(str(c).ljust(w) for c, w in zip(cols, widths)))

def print_repo(repo: dict, traffic: dict):
    # Pretty-print one repo to terminal
    views   = traffic["views"]
    clones  = traffic["clones"]
    refs    = traffic["referrers"]
    paths   = traffic["paths"]

    lock = "🔒" if repo.get("private") else "🌐"
    _sep("═")
    print(f"  {lock}  {repo['full_name']}")
    _sep("═")

    print("\n  📊  SUMMARY (last 14 days)")
    _sep()
    _row(["Metric", "Total", "Unique"], [35, 15, 15])
    _sep()
    _row(["👁️  Views",  views.get("count", 0),  views.get("uniques", 0)],  [35, 15, 15])
    _row(["📥  Clones", clones.get("count", 0), clones.get("uniques", 0)], [35, 15, 15])

    if refs:
        print("\n  🔗  TOP REFERRERS")
        _sep()
        _row(["Referrer", "Views", "Unique"], [40, 10, 10])
        _sep()
        for r in refs[:5]:
            _row([r.get("referrer", ""), r.get("count", 0), r.get("uniques", 0)], [40, 10, 10])

    if paths:
        print("\n  📄  POPULAR PATHS")
        _sep()
        _row(["Path", "Views", "Unique"], [50, 10, 10])
        _sep()
        for p in paths[:5]:
            _row([p.get("path", ""), p.get("count", 0), p.get("uniques", 0)], [50, 10, 10])

    daily = views.get("views", [])
    if daily:
        print("\n  📅  DAILY VIEWS")
        _sep()
        _row(["Date", "Views", "Unique"], [20, 10, 10])
        _sep()
        for d in daily:
            _row([d.get("timestamp", "")[:10], d.get("count", 0), d.get("uniques", 0)], [20, 10, 10])

    print()

def main():
    parser = argparse.ArgumentParser(description="GitHub Traffic Monitor CLI")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    fetch_parser = subparsers.add_parser("fetch", help="Fetch traffic and save to a CSV")
    fetch_parser.add_argument("-t", "--token", help="GitHub PAT")
    fetch_parser.add_argument("-o", "--output", help="Output CSV filename")

    sync_parser = subparsers.add_parser("sync", help="Append today's traffic to monthly CSVs")
    sync_parser.add_argument("-t", "--token", help="GitHub PAT")
    sync_parser.add_argument("--dir", help="Directory containing monthly CSVs", default="data")

    dashboard_parser = subparsers.add_parser("dashboard", help="Launch the Streamlit dashboard")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    if args.command == "dashboard":
        print("Starting Streamlit Dashboard...")
        dashboard_script = os.path.join(os.path.dirname(__file__), "dashboard.py")
        os.system(f"streamlit run \"{dashboard_script}\"")
        return

    # Both fetch and sync need token
    token = args.token or os.environ.get("GITHUB_TOKEN")
    if not token:
        print("  ❌  No token found.")
        print("      Use --token or set GITHUB_TOKEN environment variable")
        sys.exit(1)

    if args.command == "sync":
        sync_monthly_traffic(token, data_dir=args.dir)
        return

    if args.command == "fetch":
        # Validate before doing any real work
        ok, info, _, _ = validate_token(token)
        if not ok:
            print(f"  ❌  {info}")
            sys.exit(1)
        print(f"\n  ✅  Logged in as: {info}")

        # Fetch and print each repo
        print("\n🚀 Fetching all repositories…\n")
        repos = get_all_repos(token)
        print(f"  Found {len(repos)} repositories.\n")

        all_rows = []
        for repo in repos:
            traffic = get_repo_traffic(token, repo["full_name"])
            print_repo(repo, traffic)
            all_rows.append(build_row(repo, traffic))

        # Save results to CSV
        if all_rows:
            out  = args.output or DEFAULT_CSV
            path = os.path.join(os.getcwd(), out)
            with open(path, "w", newline="", encoding="utf-8") as f:
                cols   = [c for c in all_rows[0].keys() if not c.startswith("_")]
                writer = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
                writer.writeheader()
                writer.writerows(all_rows)
            _sep("═")
            print(f"\n  ✅  Saved → {path}")
            print(f"  📦  {len(all_rows)} repos exported.\n")
        else:
            print("  ⚠️  No data to save.")

if __name__ == "__main__":
    main()
