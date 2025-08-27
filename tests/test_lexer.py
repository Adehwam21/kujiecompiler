import unittest
from utils.lexer import Lexer, TokenType   # adjust path if needed


class TestLexer(unittest.TestCase):

    def lex_all_tokens(self, src):
        """Helper to run lexer until EOF and return (kind, text) pairs."""
        lexer = Lexer(src)
        return lexer.tokenize_as_tuple()

    def assertTokensEqual(self, src, expected):
        """Assert that tokens (excluding EOF) equal expected, and EOF is last."""
        tokens = self.lex_all_tokens(src)
        self.assertEqual(tokens[:-1], expected)
        self.assertEqual(tokens[-1][0], TokenType.EOF)

    def test_simple_number(self):
        self.assertTokensEqual("123", [(TokenType.NUMBER, "123")])

    def test_identifier(self):
        self.assertTokensEqual(
            "foo bar123",
            [
                (TokenType.IDENTIFIER, "foo"),
                (TokenType.IDENTIFIER, "bar123")
            ]
        )

    def test_keywords(self):
        self.assertTokensEqual(
            "if then endif",
            [
                (TokenType.IF, "if"),
                (TokenType.THEN, "then"),
                (TokenType.ENDIF, "endif")
            ]
        )

    def test_keyword_case_insensitive(self):
        self.assertTokensEqual(
            "IF If if",
            [
                (TokenType.IF, "IF"),
                (TokenType.IF, "If"),
                (TokenType.IF, "if")
            ]
        )

    def test_string_literal(self):
        self.assertTokensEqual(
            '"hello world"',
            [(TokenType.STRING, "hello world")]
        )

    def test_basic_operators(self):
        self.assertTokensEqual(
            "+-*/=",
            [
                (TokenType.PLUS, "+"),
                (TokenType.MINUS, "-"),
                (TokenType.ASTERISK, "*"),
                (TokenType.SLASH, "/"),
                (TokenType.EQ, "=")
            ]
        )

    def test_comparisons(self):
        self.assertTokensEqual(
            "== != <= < >= >",
            [
                (TokenType.EQEQ, "=="),
                (TokenType.NOTEQ, "!="),
                (TokenType.LTEQ, "<="),
                (TokenType.LT, "<"),
                (TokenType.GTEQ, ">="),
                (TokenType.GT, ">"),
            ]
        )

    def test_percent_operator(self):
        self.assertTokensEqual(
            "100 % 5",
            [
                (TokenType.NUMBER, "100"),
                (TokenType.PERCENT, "%"),
                (TokenType.NUMBER, "5")
            ]
        )

    def test_newlines_and_semicolon(self):
        tokens = self.lex_all_tokens("a;\nb")
        self.assertEqual(tokens[0][0], TokenType.IDENTIFIER)
        self.assertEqual(tokens[1][0], TokenType.ENDLINE)
        self.assertEqual(tokens[2][0], TokenType.NEWLINE)
        self.assertEqual(tokens[3][0], TokenType.IDENTIFIER)
        self.assertEqual(tokens[-1][0], TokenType.EOF)

    def test_comments(self):
        self.assertTokensEqual(
            "foo ~ this is a comment \n bar",
            [
                (TokenType.IDENTIFIER, "foo"),
                (TokenType.NEWLINE, "\n"),
                (TokenType.IDENTIFIER, "bar")
            ]
        )

    # Error case tests (SystemExit expected)
    def test_unclosed_string(self):
        with self.assertRaises(SystemExit):
            lexer = Lexer('"oops')
            lexer.tokenize_as_tuple()

    def test_unknown_character(self):
        with self.assertRaises(SystemExit):
            lexer = Lexer("@")
            lexer.tokenize_as_tuple()


if __name__ == "__main__":
    unittest.main()
