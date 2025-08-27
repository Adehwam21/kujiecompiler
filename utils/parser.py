from utils.lexer import *
from utils.ast import *

class Parser:
    def __init__(self, tokens):
        self.tokens = tokens
        self.pos = 0

    def peek(self):
        return self.tokens[self.pos] if self.pos < len(self.tokens) else None

    def advance(self):
        tok = self.peek()
        if tok:
            self.pos += 1
        return tok

    def expect(self, kind):
        tok = self.advance()
        if not tok or tok.kind != kind:
            raise SyntaxError(f"Expected {kind}, got {tok.kind if tok else None}")
        return tok
    
    def parse_program(self):
        stmts = []
        while self.peek() and self.peek().kind != TokenType.EOF:
            # Skip blank lines / standalone ENDLINEs
            while self.peek() and self.peek().kind == TokenType.ENDLINE:
                self.advance()
            if self.peek() and self.peek().kind != TokenType.EOF:
                stmt = self.parse_statement()
                stmts.append(stmt)
        return Program(stmts)

    # Statement Parsing
    def parse_statement(self):
        tok = self.peek()

        if tok.kind == TokenType.MAKE:
            return self.parse_vardecl()

        elif tok.kind == TokenType.WREP:
            return self.parse_print()

        elif tok.kind == TokenType.IF:
            return self.parse_if()

        elif tok.kind == TokenType.IDENTIFIER:
            return self.parse_assign()

        else:
            raise SyntaxError(f"Unexpected token \"{tok.text}\", line {tok.line}, col {tok.col}")
      
    # Parsing Statement types
    def parse_vardecl(self):
        self.expect(TokenType.MAKE)
        name = self.expect(TokenType.IDENTIFIER).text
        self.expect(TokenType.EQ)
        expr = self.parse_expression()
        return VarDecl(name, expr)

    def parse_assign(self):
        name = self.expect(TokenType.IDENTIFIER).text
        self.expect(TokenType.EQ)
        expr = self.parse_expression()
        return Assign(name, expr)

    def parse_print(self):
        self.expect(TokenType.WREP)
        expr = self.parse_expression()
        return Print(expr)

    def parse_if(self):
        self.expect(TokenType.IF)
        cond = self.parse_expression()
        self.expect(TokenType.DO)
        do_block = self.parse_block()

        else_block = None
        if self.peek() and self.peek().kind == TokenType.ELSE:
            self.advance()
            else_block = self.parse_block()

        return If(cond, do_block, else_block)
    
    def parse_block(self):
      stmts = []
      while self.peek() and self.peek().kind not in (TokenType.ELSE, TokenType.EOF):
          # Skip blank lines inside blocks
          while self.peek() and self.peek().kind == TokenType.ENDLINE:
              self.advance()
          if self.peek() and self.peek().kind not in (TokenType.ELSE, TokenType.EOF):
              stmt = self.parse_statement()
              stmts.append(stmt)
              # Expect a semicolon (ENDLINE) after each statement
              if self.peek() and self.peek().kind == TokenType.ENDLINE:
                  self.advance()
      return Block(stmts)

    # Expression Parsing
    def parse_expression(self):
        return self.parse_equality()

    def parse_equality(self):
        expr = self.parse_comparison()
        while self.peek() and self.peek().kind in (TokenType.EQEQ, TokenType.NOTEQ):
            op = self.advance()
            right = self.parse_comparison()
            expr = BinaryOp(op.kind, expr, right)
        return expr

    def parse_comparison(self):
        expr = self.parse_term()
        while self.peek() and self.peek().kind in (TokenType.LT, TokenType.LTEQ, TokenType.GT, TokenType.GTEQ):
            op = self.advance()
            right = self.parse_term()
            expr = BinaryOp(op.kind, expr, right)
        return expr

    def parse_term(self):
        expr = self.parse_factor()
        while self.peek() and self.peek().kind in (TokenType.PLUS, TokenType.MINUS):
            op = self.advance()
            right = self.parse_factor()
            expr = BinaryOp(op.kind, expr, right)
        return expr

    def parse_factor(self):
        expr = self.parse_unary()
        while self.peek() and self.peek().kind in (TokenType.ASTERISK, TokenType.SLASH, TokenType.PERCENT):
            op = self.advance()
            right = self.parse_unary()
            expr = BinaryOp(op.kind, expr, right)
        return expr

    def parse_unary(self):
        if self.peek() and self.peek().kind in (TokenType.MINUS, TokenType.PLUS):
            op = self.advance()
            right = self.parse_unary()
            return UnaryOp(op.kind, right)
        return self.parse_primary()

    def parse_primary(self):
        tok = self.advance()
        if tok.kind == TokenType.NUMBER:
            return Number(int(tok.text))
        elif tok.kind == TokenType.STRING:
            return String(tok.text.strip('"'))
        elif tok.kind == TokenType.IDENTIFIER:
            return Var(tok.text)
        else:
            raise SyntaxError(f"Unexpected token \"{tok.text}\", line {tok.line}, col {tok.col}")
    
    # Print AST
    def print_ast(self, node, indent=0):
        prefix = " " * indent

        if isinstance(node, Program):
            print(f"{prefix}Program")
            for stmt in node.statements:
                self.print_ast(stmt, indent + 2)

        elif isinstance(node, Block):
            print(f"{prefix}Block")
            for stmt in node.statements:
                self.print_ast(stmt, indent + 2)

        elif isinstance(node, VarDecl):
            print(f"{prefix}VarDecl {node.name}")
            self.print_ast(node.expr, indent + 2)

        elif isinstance(node, Assign):
            print(f"{prefix}Assign {node.name}")
            self.print_ast(node.expr, indent + 2)

        elif isinstance(node, Print):
            print(f"{prefix}Print")
            self.print_ast(node.expr, indent + 2)

        elif isinstance(node, If):
            print(f"{prefix}If")
            print(f"{prefix}  Condition:")
            self.print_ast(node.condition, indent + 4)
            print(f"{prefix}  Do:")
            self.print_ast(node.do_block, indent + 4)
            if node.else_block:
                print(f"{prefix}  Else:")
                self.print_ast(node.else_block, indent + 4)

        elif isinstance(node, BinaryOp):
            print(f"{prefix}BinaryOp {node.op.name}")
            self.print_ast(node.left, indent + 2)
            self.print_ast(node.right, indent + 2)

        elif isinstance(node, UnaryOp):
            print(f"{prefix}UnaryOp {node.op.name}")
            self.print_ast(node.operand, indent + 2)

        elif isinstance(node, Number):
            print(f"{prefix}Number {node.value}")

        elif isinstance(node, String):
            print(f"{prefix}String \"{node.value}\"")

        elif isinstance(node, Var):
            print(f"{prefix}Var {node.name}")

        else:
            print(f"{prefix}Unknown node: {node}")
