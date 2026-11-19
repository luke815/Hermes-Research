"""The stall line the digest quotes is read from the response, not the prompt.

The prompt restates the instruction and contains the words, so a reader that
searches the whole file would pass on a digest that never printed the line.
"""

import os
import unittest

from scripts.l0_check import digest_response_line


class DigestLine(unittest.TestCase):
    def test_reads_the_line_from_the_response_only(self):
        text = (
            "The digest ends with the line top backlog item A5, 1 runs\n"
            "## Response\n"
            "top backlog item A5, 28 runs\n"
        )
        self.assertEqual(digest_response_line(text), "top backlog item A5, 28 runs")

    def test_a_prompt_mention_is_not_the_line(self):
        text = "quote the line top backlog item A5, 1 runs\n## Response\nnothing here\n"
        self.assertEqual(digest_response_line(text), "")


if __name__ == "__main__":
    unittest.main()
