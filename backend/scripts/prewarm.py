"""Pre-warm the Apify LinkedIn cache for known demo recipients.

Run BEFORE the demo so live invocation hits cache (~50ms instead of 30s).

Usage:
  cd backend
  ../.venv/bin/python scripts/prewarm.py https://linkedin.com/in/foo https://linkedin.com/in/bar
  # or
  ../.venv/bin/python scripts/prewarm.py demo_recipients.txt
"""
from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.services import apify as apify_svc  # noqa: E402


def collect_urls(args: list[str]) -> list[str]:
    urls: list[str] = []
    for a in args:
        if a.startswith("http"):
            urls.append(a.strip())
            continue
        p = Path(a)
        if p.exists():
            for line in p.read_text().splitlines():
                line = line.strip()
                if line and not line.startswith("#"):
                    urls.append(line)
    return urls


async def main():
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        sys.exit(1)
    urls = collect_urls(args)
    if not urls:
        print("No URLs provided.")
        sys.exit(1)
    print(f"Pre-warming {len(urls)} profiles…")
    res = await apify_svc.prewarm_cache(urls)
    print(json.dumps(res, indent=2))
    print(
        f"Cache hits: {len(res['hit'])} | live scrapes: {len(res['live'])} | failed: {len(res['failed'])}"
    )


if __name__ == "__main__":
    asyncio.run(main())
