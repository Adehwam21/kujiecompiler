from pathlib import Path
from utils.helpers import read_source_file
from utils.lexer import Lexer
from utils.parser import Parser
from utils.codegen import Codegen

src_path = Path("examples") / "main.kj"
src = read_source_file(src_path)

lexer = Lexer(src)
parser = Parser(lexer.tokenize_as_object())
# parser.print_ast(parser.parse_program()) # Print abstract syntax tree to console
code_generator = Codegen()
code_generator.generate(parser.parse_program())
# cg.dump_ir()              # optionally print LLVM IR to console
code_generator.write_ir("out.ll")       # optionally save LLVM IR
code_generator.jit_run()                # execute the program
