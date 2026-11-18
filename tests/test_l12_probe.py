"""The v2 probe sends full timestamps and never writes the key."""

import unittest

import scripts.l12_probe as probe


class L12Probe(unittest.TestCase):
    def test_the_window_uses_full_timestamps(self):
        start, end = probe.window("2026-11-18")
        self.assertTrue(start.endswith("T00:00:00Z"))
        self.assertTrue(end.endswith("T00:00:00Z"))
        url = probe.url_for(start, end)
        self.assertNotIn("start=2026-11-18&", url)
        self.assertIn("start=2026-11-11T00:00:00Z", url)

    def test_the_payload_does_not_carry_the_key(self):
        seen = {}

        class FakeResponse:
            status = 200

            def read(self):
                return b'{"ok": true}'

            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

        def fake_urlopen(req, timeout):
            seen["headers"] = dict(req.header_items())
            return FakeResponse()

        probe.urllib.request.urlopen = fake_urlopen
        status, body = probe.probe("Mozilla/5.0", probe.url_for(*probe.window("2026-11-18")),
                                   "SECRET-KEY-VALUE")
        self.assertEqual(status, 200)
        self.assertNotIn("SECRET-KEY-VALUE", body)
        self.assertEqual(seen["headers"]["X-api-key"], "SECRET-KEY-VALUE")


if __name__ == "__main__":
    unittest.main()
