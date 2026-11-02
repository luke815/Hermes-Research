"""List every USDT-margined perp that ever traded on Binance.

Reads the public archive bucket listing, which includes delisted symbols,
and follows the pagination marker to the end. Saves incrementally.
"""

import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

OUT = Path("/opt/data/workspace/regime-tester/data/binance_symbols.txt")
BASE = "https://s3-ap-northeast-1.amazonaws.com/data.binance.vision"
NS = {"s3": "http://s3.amazonaws.com/doc/2006-03-01/"}


def page(marker: str) -> tuple[list[str], str | None]:
    url = f"{BASE}?prefix=data/futures/um/daily/klines/&delimiter=/&max-keys=1000"
    if marker:
        url += f"&marker={marker}"
    with urllib.request.urlopen(url, timeout=60) as response:
        root = ET.fromstring(response.read())
    symbols = []
    for prefix in root.findall("s3:CommonPrefixes/s3:Prefix", NS):
        name = prefix.text.strip("/").split("/")[-1]
        if name.endswith("USDT"):
            symbols.append(name)
    truncated = root.findtext("s3:IsTruncated", default="false", namespaces=NS) == "true"
    next_marker = root.findtext("s3:NextMarker", default=None, namespaces=NS) if truncated else None
    return symbols, next_marker


def main() -> None:
    seen = set(OUT.read_text().split()) if OUT.exists() else set()
    marker = ""
    while True:
        symbols, marker = page(marker)
        new = [s for s in symbols if s not in seen]
        seen.update(new)
        OUT.write_text("\n".join(sorted(seen)) + "\n")
        print(f"{len(seen)} symbols", flush=True)
        if marker is None:
            break
    print(f"done: {len(seen)} USDT perps ever listed", flush=True)


if __name__ == "__main__":
    main()
