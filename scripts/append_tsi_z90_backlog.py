"""Append the TSI 90-bar attempt to the confirmation line in the backlog."""

from pathlib import Path

PATH = Path(__file__).resolve().parents[1] / "research" / "backlog.md"
NEEDLE = "results/2026-11-12_confirm_tsi.json."
INSERT = (
    "results/2026-11-12_confirm_tsi.json. "
    "Forty-seventh attempt 2026-11-12: tsi|z_90|below|5|ret_1|eth|none|daily rejected. "
    "Validation t-stat 0.9047 against bar 3.0502, independent n 41, sign kept. "
    "Test spread 0.0535 percent, t-stat 0.0527, independent n 22, sign kept. Closed. "
    "results/2026-11-12_confirm_tsi_z90.json."
)


def main():
    text = PATH.read_text()
    if "tsi|z_90|below|5|ret_1|eth|none|daily" in text:
        raise SystemExit("attempt already recorded")
    if text.count(NEEDLE) != 1:
        raise SystemExit(f"needle count {text.count(NEEDLE)}")
    PATH.write_text(text.replace(NEEDLE, INSERT, 1))
    print("updated")


if __name__ == "__main__":
    main()
