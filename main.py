from utils.lexer import Lexer
from utils.parser import Parser

SOURCE = "make x = 3;wrep x;if x > 0 do wrep \"greater\"; else do wrep \"lesser\";"


lex = Lexer(SOURCE)
parser = Parser(lex.tokenize_as_object())

parser.print_ast()