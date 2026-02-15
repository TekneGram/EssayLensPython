from __future__ import annotations

import unittest

from cli.parser import parse_shell_command


class CliParserTests(unittest.TestCase):
    def test_parse_topic_sentence_with_at_file(self) -> None:
        cmd = parse_shell_command('/topic-sentence @Assessment/in/sample.docx')
        self.assertEqual(cmd.name, "topic-sentence")
        self.assertEqual(cmd.args["file"], "Assessment/in/sample.docx")

    def test_parse_topic_sentence_with_quoted_path(self) -> None:
        cmd = parse_shell_command('/topic-sentence @"Assessment/in/my essay.docx"')
        self.assertEqual(cmd.name, "topic-sentence")
        self.assertEqual(cmd.args["file"], "Assessment/in/my essay.docx")

    def test_parse_metadata_with_at_file(self) -> None:
        cmd = parse_shell_command('/metadata @Assessment/in/sample.docx')
        self.assertEqual(cmd.name, "metadata")
        self.assertEqual(cmd.args["file"], "Assessment/in/sample.docx")

    def test_parse_prompt_test_with_at_file(self) -> None:
        cmd = parse_shell_command('/prompt-test @Assessment/in/sample.docx')
        self.assertEqual(cmd.name, "prompt-test")
        self.assertEqual(cmd.args["file"], "Assessment/in/sample.docx")

    def test_parse_llm_commands(self) -> None:
        self.assertEqual(parse_shell_command('/llm-list').name, 'llm-list')
        self.assertEqual(parse_shell_command('/llm-status').name, 'llm-status')
        self.assertEqual(parse_shell_command('/llm-start qwen3_4b_q8').args['model_key'], 'qwen3_4b_q8')
        self.assertEqual(parse_shell_command('/llm-switch qwen3_8b_q8').args['model_key'], 'qwen3_8b_q8')

    def test_reject_missing_at_file(self) -> None:
        with self.assertRaisesRegex(ValueError, "@file"):
            parse_shell_command('/topic-sentence Assessment/in/sample.docx')

    def test_reject_unknown_command(self) -> None:
        with self.assertRaisesRegex(ValueError, "Unknown command"):
            parse_shell_command('/bogus')

    def test_reject_metadata_extra_args(self) -> None:
        with self.assertRaisesRegex(ValueError, "only one @file"):
            parse_shell_command("/metadata @a.docx extra")

    def test_reject_prompt_test_extra_args(self) -> None:
        with self.assertRaisesRegex(ValueError, "only one @file"):
            parse_shell_command("/prompt-test @a.docx extra")


if __name__ == "__main__":
    unittest.main()
