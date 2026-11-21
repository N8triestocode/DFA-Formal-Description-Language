"""Tests for parser.py. Run with: python -m unittest discover -s tests -p test_parser.py -v"""

import unittest

from lexer import get_tokens
from parser import Parser, ParseError, Name, Transition, parse


def P(text):
    """Build a Parser over `text` (lexical errors ignored; tests use clean input)."""
    tokens, _ = get_tokens(text)
    return Parser(tokens, text)


FORMAT1 = """M = (Q, Σ, δ, q0, F)
Q = {q1, q2, q3, q4, Trap}
Σ = {a, b, c}
δ = Q × Σ → Q
q0 = q1
F = {q4}

δ a b c
q1 q2 q3 Trap
q2 q4 Trap q2
q3 Trap q4 q3
q4 Trap Trap Trap
Trap Trap Trap Trap
"""

FORMAT2 = """M = ({q1, q2, q3, q4, Trap}, {a, b, c}, δ, q1, {q4})
δ(q1,a)=q2 δ(q1,b)=q3 δ(q1,c)=Trap δ(q2,a)=q4 δ(q2,b)=Trap δ(q2,c)=q2
δ(q3,a)=Trap δ(q3,b)=q4 δ(q3,c)=q3
δ(q4,a)=Trap δ(q4,b)=Trap δ(q4,c)=Trap δ(Trap,a)=Trap δ(Trap,b)=Trap δ(Trap,c)=Trap
"""


# ----------------------------------------------------------------------------
# Building blocks
# ----------------------------------------------------------------------------

class TestBuildingBlocks(unittest.TestCase):
    def test_idenlist_single(self):
        self.assertEqual(P("a").parse_idenlist(), ["a"])

    def test_idenlist_many(self):
        self.assertEqual(P("q1, q2 ,Trap").parse_idenlist(), ["q1", "q2", "Trap"])

    def test_idenlist_stops_at_non_comma(self):
        p = P("a, b }")
        self.assertEqual(p.parse_idenlist(), ["a", "b"])
        self.assertEqual(p.peek().type, "RBRACE")

    def test_idenlist_trailing_comma_is_error(self):
        with self.assertRaises(ParseError):
            P("a, }").parse_idenlist()

    def test_idenlist_empty_is_error(self):
        with self.assertRaises(ParseError):
            P("}").parse_idenlist()

    def test_names_carry_positions(self):
        names = P("{a, b}").parse_set()
        self.assertIsInstance(names[1], Name)
        self.assertEqual((names[0].line, names[0].column), (1, 2))
        self.assertEqual((names[1].line, names[1].column), (1, 5))

    def test_set_empty(self):
        self.assertEqual(P("{}").parse_set(), [])

    def test_set_empty_with_spaces(self):
        self.assertEqual(P("{ }").parse_set(), [])

    def test_set_one_and_many(self):
        self.assertEqual(P("{a}").parse_set(), ["a"])
        self.assertEqual(P("{q1, q2, Trap}").parse_set(), ["q1", "q2", "Trap"])

    def test_set_single_digit_names(self):
        self.assertEqual(P("{0, 1}").parse_set(), ["0", "1"])

    def test_set_consumes_closing_brace(self):
        p = P("{a} , b")
        p.parse_set()
        self.assertEqual(p.peek().type, "COMMA")

    def test_set_missing_close(self):
        with self.assertRaises(ParseError) as cm:
            P("{a, b").parse_set()
        self.assertIn("'}'", cm.exception.message)

    def test_set_missing_open(self):
        with self.assertRaises(ParseError) as cm:
            P("a, b}").parse_set()
        self.assertIn("'{'", cm.exception.message)

    def test_set_trailing_comma(self):
        with self.assertRaises(ParseError):
            P("{a,}").parse_set()

    def test_set_missing_comma(self):
        with self.assertRaises(ParseError):
            P("{a b}").parse_set()


# ----------------------------------------------------------------------------
# Format 1 pieces
# ----------------------------------------------------------------------------

class TestFormat1Pieces(unittest.TestCase):
    def test_statedef(self):
        p = P("Q = {q1, q2}")
        self.assertEqual(p.parse_statedef(), ("Q", ["q1", "q2"]))
        self.assertEqual(p.peek().type, "NWLINE")   # stops BEFORE the newline

    def test_statedef_empty_set(self):
        self.assertEqual(P("Q = {}").parse_statedef(), ("Q", []))

    def test_statedef_missing_equals(self):
        with self.assertRaises(ParseError):
            P("Q {q1}").parse_statedef()

    def test_sigmadef_symbol_and_words(self):
        self.assertEqual(P("Σ = {a, b}").parse_sigmadef(), ["a", "b"])
        self.assertEqual(P("sigma = {a}").parse_sigmadef(), ["a"])
        self.assertEqual(P("SIGMA = {}").parse_sigmadef(), [])

    def test_sigmadef_wrong_keyword(self):
        with self.assertRaises(ParseError):
            P("Q = {a}").parse_sigmadef()

    def test_tranfunc_unicode(self):
        p = P("δ = Q × Σ → Q")
        self.assertEqual(p.parse_tranfunc(), ("Q", "Q"))
        self.assertEqual(p.peek().type, "NWLINE")

    def test_tranfunc_ascii(self):
        self.assertEqual(P("delta = S * sigma -> T").parse_tranfunc(), ("S", "T"))

    def test_tranfunc_missing_arrow(self):
        with self.assertRaises(ParseError) as cm:
            P("δ = Q × Σ Q").parse_tranfunc()
        self.assertIn("->", cm.exception.message)

    def test_tranfunc_missing_sigma(self):
        with self.assertRaises(ParseError):
            P("δ = Q × → Q").parse_tranfunc()

    def test_startdef(self):
        self.assertEqual(P("q0 = q1").parse_startdef(), ("q0", "q1"))

    def test_startdef_set_instead_of_name(self):
        with self.assertRaises(ParseError):
            P("q0 = {q1}").parse_startdef()

    def test_finaldef(self):
        self.assertEqual(P("F = {q4}").parse_finaldef(), ("F", ["q4"]))
        self.assertEqual(P("F = {}").parse_finaldef(), ("F", []))

    def test_tableheader(self):
        p = P("δ a b c\nq1 q2 q3 q4\n")
        self.assertEqual(p.parse_tableheader(), ["a", "b", "c"])
        self.assertEqual(p.peek().type, "IDEN")      # NWLINE was consumed

    def test_tableheader_needs_a_symbol(self):
        with self.assertRaises(ParseError):
            P("δ\n").parse_tableheader()

    def test_tableheader_needs_newline_or_more(self):
        with self.assertRaises(ParseError):
            P("δ a b )").parse_tableheader()

    def test_tablerow(self):
        p = P("q1 q2 q3 Trap\nq2 a\n")
        self.assertEqual(p.parse_tablerow(), ("q1", ["q2", "q3", "Trap"]))
        self.assertEqual(p.peek().value, "q2")       # NWLINE consumed

    def test_tablerow_state_only(self):
        self.assertEqual(P("q1\n").parse_tablerow(), ("q1", []))

    def test_tablerow_bad_token(self):
        with self.assertRaises(ParseError):
            P("q1 q2 , q3\n").parse_tablerow()

    def test_table(self):
        header, rows = P("δ a b\nq1 q1 q2\nq2 q2 q1\n").parse_table()
        self.assertEqual(header, ["a", "b"])
        self.assertEqual(rows, [("q1", ["q1", "q2"]), ("q2", ["q2", "q1"])])

    def test_table_header_only(self):
        header, rows = P("δ a\n").parse_table()
        self.assertEqual((header, rows), (["a"], []))

    def test_table_requires_header(self):
        with self.assertRaises(ParseError):
            P("q1 q2\n").parse_table()

    def test_table_stops_at_eof(self):
        p = P("δ a\nq1 q1\n")
        p.parse_table()
        self.assertEqual(p.peek().type, "EOF")


# ----------------------------------------------------------------------------
# Format 2 pieces
# ----------------------------------------------------------------------------

class TestFormat2Pieces(unittest.TestCase):
    def test_inlinetran(self):
        p = P("δ(q1,a)=q2\n")
        tr = p.parse_inlinetran()
        self.assertEqual((tr.state, tr.symbol, tr.target), ("q1", "a", "q2"))
        self.assertEqual(tr.position, (1, 1))
        self.assertEqual(p.peek().type, "EOF")       # optional NWLINE consumed

    def test_inlinetran_unpacks_as_tuple(self):
        self.assertEqual(P("δ(q1,a)=q2").parse_inlinetran()[:3], ("q1", "a", "q2"))

    def test_inlinetran_without_newline_followed_by_another(self):
        p = P("δ(q1,a)=q2 δ(q1,b)=q3")
        p.parse_inlinetran()
        self.assertEqual(p.peek().type, "DELTA")

    def test_inlinetran_words(self):
        tr = P("delta(q1, a) = q2").parse_inlinetran()
        self.assertEqual((tr.state, tr.symbol, tr.target), ("q1", "a", "q2"))

    def test_inlinetran_missing_equals(self):
        with self.assertRaises(ParseError):
            P("δ(q1,a) q2").parse_inlinetran()

    def test_inlinetran_missing_rparen(self):
        with self.assertRaises(ParseError) as cm:
            P("δ(q1,a=q2").parse_inlinetran()
        self.assertIn("')'", cm.exception.message)

    def test_inlinetran_missing_target(self):
        with self.assertRaises(ParseError):
            P("δ(q1,a)=\n").parse_inlinetran()


# ----------------------------------------------------------------------------
# Whole programs
# ----------------------------------------------------------------------------

class TestFormat1Program(unittest.TestCase):
    def test_sample_program(self):
        res = parse(FORMAT1)
        self.assertTrue(res.ok, res.errors)
        prog = res.program
        self.assertEqual(prog.format, 1)
        self.assertEqual(prog.name, "M")
        self.assertEqual((prog.states_ref, prog.start_ref, prog.finals_ref),
                         ("Q", "q0", "F"))
        self.assertEqual(prog.states, ["q1", "q2", "q3", "q4", "Trap"])
        self.assertEqual(prog.states_name, "Q")
        self.assertEqual(prog.alphabet, ["a", "b", "c"])
        self.assertEqual((prog.delta_domain, prog.delta_codomain), ("Q", "Q"))
        self.assertEqual((prog.start_name, prog.start), ("q0", "q1"))
        self.assertEqual((prog.finals_name, prog.finals), ("F", ["q4"]))
        self.assertEqual(prog.table_header, ["a", "b", "c"])
        self.assertEqual(len(prog.table_rows), 5)
        self.assertEqual(prog.table_rows[0], ("q1", ["q2", "q3", "Trap"]))
        self.assertEqual(prog.table_rows[4], ("Trap", ["Trap", "Trap", "Trap"]))

    def test_ascii_only(self):
        text = ("M = (Q, sigma, delta, q0, F)\nQ = {q1}\nsigma = {a}\n"
                "delta = Q * sigma -> Q\nq0 = q1\nF = {q1}\ndelta a\nq1 q1\n")
        res = parse(text)
        self.assertTrue(res.ok, res.errors)
        self.assertEqual(res.program.table_rows, [("q1", ["q1"])])

    def test_empty_Q_and_sigma_are_legal_syntax(self):
        text = ("M = (Q, Σ, δ, q0, F)\nQ = {}\nΣ = {}\nδ = Q × Σ → Q\n"
                "q0 = q1\nF = {}\nδ a\n")
        res = parse(text)
        self.assertTrue(res.ok, res.errors)
        self.assertEqual((res.program.states, res.program.alphabet), ([], []))

    def test_comments_blank_lines_and_leading_newlines(self):
        text = "\n\n! my DFA\n" + FORMAT1.replace("Q = {", "! states\nQ = {", 1)
        text = text.replace("\n", "\n\n", 3)
        res = parse(text)
        self.assertTrue(res.ok, res.errors)

    def test_crlf_and_no_final_newline(self):
        text = FORMAT1.rstrip("\n").replace("\n", "\r\n")
        res = parse(text)
        self.assertTrue(res.ok, res.errors)
        self.assertEqual(len(res.program.table_rows), 5)

    def test_missing_table(self):
        text = FORMAT1.split("δ a b c")[0]
        res = parse(text)
        self.assertFalse(res.ok)
        self.assertIn("end of file", res.syntax_errors[0][0])

    def test_error_reports_correct_line_and_column(self):
        text = "M = (Q, Σ, δ, q0, F)\nQ = {q1}\nΣ {a}\n"
        res = parse(text)
        self.assertFalse(res.ok)
        message, line, col = res.syntax_errors[0]
        self.assertEqual((line, col), (3, 3))
        self.assertIn("'='", message)
        self.assertIn("line 3, column 3", message)

    def test_missing_closing_brace(self):
        text = "M = (Q, Σ, δ, q0, F)\nQ = {q1, q2\nΣ = {a}\n"
        res = parse(text)
        self.assertFalse(res.ok)
        message, line, col = res.syntax_errors[0]
        self.assertEqual(line, 2)
        self.assertIn("'}'", message)

    def test_tuple_line_wrong_order(self):
        res = parse("M = (Q, δ, Σ, q0, F)\n")
        self.assertFalse(res.ok)
        self.assertIn("Σ", res.syntax_errors[0][0])

    def test_junk_after_table(self):
        res = parse(FORMAT1 + "}\n")
        self.assertFalse(res.ok)
        self.assertIn("end of file", res.syntax_errors[0][0])
        self.assertEqual(res.syntax_errors[0][1], 14)


class TestFormat2Program(unittest.TestCase):
    def test_sample_program(self):
        res = parse(FORMAT2)
        self.assertTrue(res.ok, res.errors)
        prog = res.program
        self.assertEqual(prog.format, 2)
        self.assertEqual(prog.name, "M")
        self.assertEqual(prog.states, ["q1", "q2", "q3", "q4", "Trap"])
        self.assertEqual(prog.alphabet, ["a", "b", "c"])
        self.assertEqual(prog.start, "q1")
        self.assertEqual(prog.finals, ["q4"])
        self.assertEqual(len(prog.transitions), 15)
        self.assertEqual(prog.transitions[0][:3], ("q1", "a", "q2"))
        self.assertEqual(prog.transitions[0].position, (2, 1))
        self.assertEqual(prog.transitions[-1][:3], ("Trap", "c", "Trap"))
        self.assertEqual(prog.states_ref, None)

    def test_one_per_line(self):
        text = "M = ({q1}, {a}, δ, q1, {q1})\nδ(q1,a)=q1\n"
        res = parse(text)
        self.assertTrue(res.ok, res.errors)
        self.assertEqual(len(res.program.transitions), 1)

    def test_no_final_newline_and_comment(self):
        text = "M = ({q1}, {a}, δ, q1, {q1})\nδ(q1,a)=q1 ! self loop"
        res = parse(text)
        self.assertTrue(res.ok, res.errors)

    def test_empty_sets_are_legal_syntax(self):
        res = parse("M = ({}, {}, δ, q1, {})\nδ(q1,a)=q1\n")
        self.assertTrue(res.ok, res.errors)

    def test_needs_at_least_one_transition(self):
        res = parse("M = ({q1}, {a}, δ, q1, {q1})\n")
        self.assertFalse(res.ok)
        self.assertIn("'δ'", res.syntax_errors[0][0])

    def test_missing_rparen(self):
        first = "M = ({q1}, {a}, δ, q1, {q1}"
        res = parse(first + "\nδ(q1,a)=q1\n")
        self.assertFalse(res.ok)
        message, line, col = res.syntax_errors[0]
        self.assertEqual((line, col), (1, len(first) + 1))
        self.assertIn("')'", message)

    def test_unclosed_set_in_tuple(self):
        res = parse("M = ({q1, {a}, δ, q1, {q1})\nδ(q1,a)=q1\n")
        self.assertFalse(res.ok)
        self.assertEqual(res.syntax_errors[0][1], 1)

    def test_extra_closing_paren(self):
        res = parse("M = ({q1}, {a}, δ, q1, {q1}))\nδ(q1,a)=q1\n")
        self.assertFalse(res.ok)

    def test_junk_after_transitions(self):
        res = parse("M = ({q1}, {a}, δ, q1, {q1})\nδ(q1,a)=q1\n}\n")
        self.assertFalse(res.ok)
        message, line, col = res.syntax_errors[0]
        self.assertEqual((line, col), (3, 1))
        self.assertIn("end of file", message)

    def test_bad_transition_reports_its_line(self):
        text = "M = ({q1}, {a}, δ, q1, {q1})\nδ(q1,a)=q1\nδ(q1 a)=q1\n"
        res = parse(text)
        self.assertFalse(res.ok)
        self.assertEqual(res.syntax_errors[0][1], 3)


# ----------------------------------------------------------------------------
# Top level, wrapper, lexical errors
# ----------------------------------------------------------------------------

class TestProgramHeader(unittest.TestCase):
    def test_empty_input(self):
        res = parse("")
        self.assertFalse(res.ok)
        self.assertIn("name", res.syntax_errors[0][0])
        self.assertEqual(res.syntax_errors[0][1:], (1, 1))

    def test_must_start_with_identifier(self):
        res = parse("= ({q1}, {a}, δ, q1, {q1})\n")
        self.assertFalse(res.ok)
        self.assertEqual(res.syntax_errors[0][1:], (1, 1))

    def test_missing_equals(self):
        res = parse("M ({q1}, {a}, δ, q1, {q1})\n")
        self.assertFalse(res.ok)
        self.assertIn("'='", res.syntax_errors[0][0])

    def test_missing_lparen(self):
        res = parse("M = {q1}, {a}, δ, q1, {q1})\n")
        self.assertFalse(res.ok)
        self.assertIn("'('", res.syntax_errors[0][0])

    def test_bad_token_after_lparen(self):
        res = parse("M = (, {a})\n")
        self.assertFalse(res.ok)
        self.assertIn("after '('", res.syntax_errors[0][0])

    def test_format_chosen_by_next_token(self):
        self.assertEqual(parse(FORMAT1).program.format, 1)
        self.assertEqual(parse(FORMAT2).program.format, 2)

    def test_parse_program_directly(self):
        prog = P(FORMAT2).parse_program()
        self.assertEqual(prog.format, 2)

    def test_parse_program_raises_parse_error(self):
        with self.assertRaises(ParseError) as cm:
            P("M = (").parse_program()
        self.assertEqual(cm.exception.line, 1)
        self.assertIsInstance(cm.exception.column, int)


class TestWrapper(unittest.TestCase):
    ERR = "M = ({q1}, {a}, δ, q1, {q1})\nδ(q1,ε)=q1\n"

    def test_lexical_errors_stop_by_default(self):
        res = parse(self.ERR)
        self.assertFalse(res.ok)
        self.assertIsNone(res.program)
        self.assertEqual(len(res.lexical_errors), 1)
        self.assertEqual(res.syntax_errors, [])
        message, line, col = res.lexical_errors[0]
        self.assertIn("ε", message)
        self.assertEqual((line, col), (2, 6))

    def test_parse_anyway_reports_both(self):
        res = parse(self.ERR, parse_anyway=True)
        self.assertFalse(res.ok)
        self.assertEqual(len(res.lexical_errors), 1)
        self.assertEqual(len(res.syntax_errors), 1)
        self.assertEqual(len(res.errors), 2)

    def test_parse_anyway_with_recoverable_char(self):
        # '@' is skipped by the lexer and the rest still parses; ok stays False
        res = parse("M = ({q1}, {a}, δ, q1, {q1})\nδ(q1,a)=q1 @\n", parse_anyway=True)
        self.assertIsNotNone(res.program)
        self.assertFalse(res.ok)

    def test_lexical_errors_do_not_leak_between_calls(self):
        parse(self.ERR)
        self.assertTrue(parse(FORMAT2).ok)
        self.assertEqual(parse(FORMAT2).errors, [])

    def test_never_raises(self):
        for text in ["", "\n\n", "M", "M =", "M = (", "{", "δ δ δ", "M = (Q,", ")))"]:
            res = parse(text)
            self.assertFalse(res.ok, text)
            self.assertEqual(len(res.syntax_errors), 1, text)


if __name__ == "__main__":
    unittest.main()
