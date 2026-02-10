from __future__ import annotations

import unittest

from docx_tools.incremental_header_body_parser import (
    extract_header_fields,
    recompose_header_and_body,
    split_header_and_body,
)


class IncrementalHeaderBodyParserTests(unittest.TestCase):
    def test_extract_header_fields_parses_expected_keys(self) -> None:
        fields = extract_header_fields(
            [
                "Name: Ada Lovelace",
                "Student Number: 12345",
                "Essay Title: The Analytical Engine",
            ]
        )
        self.assertEqual(fields.student_name, "Ada Lovelace")
        self.assertEqual(fields.student_number, "12345")
        self.assertEqual(fields.essay_title, "The Analytical Engine")

    def test_split_header_and_body_respects_blank_boundary(self) -> None:
        header, body = split_header_and_body(
            [
                "Name: Ada",
                "ID: 999",
                "",
                "First body paragraph.",
                "Second body paragraph.",
            ]
        )
        self.assertEqual(header, ["Name: Ada", "ID: 999"])
        self.assertEqual(body, ["First body paragraph.", "Second body paragraph."])

    def test_recompose_header_and_body_formats_expected_text(self) -> None:
        result = recompose_header_and_body(["Name: Ada", "ID: 999"], "Body content.")
        self.assertEqual(result, "Name: Ada\nID: 999\n\nBody content.")


if __name__ == "__main__":
    unittest.main()
