from pathlib import Path
from utils.helpers import read_source_file
from utils.lexer import Lexer
from utils.parser import Parser
from utils.codegen import Codegen

src_path = Path("examples") / "new.kj"
src = read_source_file(src_path)

# Lexing, parsing, codegen
lex = Lexer(src)
tokens = lex.tokenize_as_object()
parser = Parser(tokens)
prog = parser.parse_program()
cg = Codegen()

cg.generate(prog)
# cg.dump_ir()              # optionally print LLVM IR
cg.write_ir("out.ll")       # optionally save LLVM IR
cg.jit_run()                # execute the program
