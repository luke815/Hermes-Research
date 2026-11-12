"""Show the confirmation sentence now in the backlog. Reads only."""

from pathlib import Path

PATH = Path(__file__).resolve().parents[1] / "research" / "backlog.md"


def main():
    text = PATH.read_text()
    marker = "tsi|z_90|below|5|ret_1|eth|none|daily"
    if marker not in text:
        raise SystemExit("missing")
    start = text.index(marker) - 40
    print(text[start:start + 320].replace("\n", " "))


if __name__ == "__main__":
    main()
