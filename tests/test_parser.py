import unittest
from utils.lexer import Lexer
from utils.parser import Parser
from utils.ast import Program, VarDecl, Print, If, Number, Var, String, BinaryOp


SOURCE = "make x = 3; wrep x; if x > 0 do wrep \"greater\"; else wrep \"lesser\";"


class TestParser(unittest.TestCase):

    def setUp(self):
        lexer = Lexer(SOURCE)
        tokens = lexer.tokenize_as_object()
        self.parser = Parser(tokens)
        self.program = self.parser.parse_program()

    def test_program_structure(self):
        self.assertIsInstance(self.program, Program)
        self.assertEqual(len(self.program.statements), 3)  # VarDecl, Print, If

    def test_var_decl(self):
        var_decl = self.program.statements[0]
        self.assertIsInstance(var_decl, VarDecl)
        self.assertEqual(var_decl.name, "x")
        self.assertIsInstance(var_decl.expr, Number)
        self.assertEqual(var_decl.expr.value, 3)

    def test_print_stmt(self):
        print_stmt = self.program.statements[1]
        self.assertIsInstance(print_stmt, Print)
        self.assertIsInstance(print_stmt.expr, Var)
        self.assertEqual(print_stmt.expr.name, "x")

    def test_if_stmt(self):
        if_stmt = self.program.statements[2]
        self.assertIsInstance(if_stmt, If)

        # Condition check
        self.assertIsInstance(if_stmt.condition, BinaryOp)
        self.assertIsInstance(if_stmt.condition.left, Var)
        self.assertIsInstance(if_stmt.condition.right, Number)

        # Do block
        do_block = if_stmt.do_block
        self.assertEqual(len(do_block.statements), 1)
        self.assertIsInstance(do_block.statements[0], Print)
        self.assertIsInstance(do_block.statements[0].expr, String)
        self.assertEqual(do_block.statements[0].expr.value, "greater")

        # Else block
        else_block = if_stmt.else_block
        self.assertEqual(len(else_block.statements), 1)
        self.assertIsInstance(else_block.statements[0], Print)
        self.assertIsInstance(else_block.statements[0].expr, String)
        self.assertEqual(else_block.statements[0].expr.value, "lesser")


if __name__ == "__main__":
    unittest.main()
