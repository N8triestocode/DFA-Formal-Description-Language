#File shared among all members
import unittest
from pathlib import Path

from pipeline import pipeliner_run


FORMAT1_DFA = (Path(__file__).parent / "tests" / "format1.txt").read_text(encoding="utf-8")
VALID_DFA = """M = ({q0}, {a}, δ, q0, {q0})
δ(q0,a)=q0"""


INCOMPLETE_DFA = """M = ({q0, q1}, {a}, δ, q0, {q1})
δ(q0,a)=q1"""



class TestPipeline(unittest.TestCase):
    def test_returns_program_when_format1_semantics_are_valid(self):
        program, errors = pipeliner_run(FORMAT1_DFA)

        self.assertIsNotNone(program)
        self.assertIsNone(errors)

    def test_returns_program_when_semantics_are_valid(self):
        program, errors = pipeliner_run(VALID_DFA)

        self.assertIsNotNone(program)
        self.assertIsNone(errors)

    def test_returns_semantic_errors_for_invalid_program(self):
        program, errors = pipeliner_run(INCOMPLETE_DFA)

        self.assertIsNone(program)
        self.assertTrue(errors)
        self.assertTrue(any("Missing transition" in error[0] for error in errors))

    def test_returns_parse_errors_without_running_semantics(self):
        program, errors = pipeliner_run("not a DFA")

        self.assertIsNone(program)
        self.assertTrue(errors)
        self.assertIn("Expected", errors[0][0])


if __name__ == "__main__":
    unittest.main(verbosity=2)
  
