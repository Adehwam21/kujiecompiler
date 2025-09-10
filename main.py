from pathlib import Path
from utils.preprocessor import Preprocessor
from utils.lexer import Lexer
from utils.parser import Parser
from utils.codegen import Codegen

src_path = Path("examples") / "demo-lexer.kj"

preprocessor = Preprocessor()
src = preprocessor.preprocess_code(src_path)

lexer = Lexer(src)
print(lexer.tokenize_as_tuple())
# parser = Parser(lexer.tokenize_as_object())
# parser.print_ast(parser.parse_program()) # Print abstract syntax tree to console
# code_generator = Codegen()
# code_generator.generate(parser.parse_program()) # Generate IR of AST from parser
# code_generator.write_ir("out.ll")       # optionally save LLVM IR
# code_generator.jit_run()                # execute the program
