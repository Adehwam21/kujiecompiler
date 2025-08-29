# utils/codegen.py
import llvmlite.ir as ir
import llvmlite.binding as llvm
from utils.lexer import TokenType
from utils.ast import *

# Initialize LLVM (safe to call multiple times)
llvm.initialize()
llvm.initialize_native_target()
llvm.initialize_native_asmprinter()

class Codegen:
    def __init__(self):
        self.module = ir.Module(name="kujie_module")
        self.builder = None
        self.func = None
        self.printf = None

        # maps variable name -> LLVM pointer (alloca for ints) or GlobalVariable for strings
        self.variables = {}

        # map literal string -> GlobalVariable (deduplicate)
        self.string_constants = {}

        self._declare_printf()

    # --- Helpers ---
    def _declare_printf(self):
        voidptr_ty = ir.IntType(8).as_pointer()
        printf_ty = ir.FunctionType(ir.IntType(32), [voidptr_ty], var_arg=True)
        # declare printf if it doesn't already exist
        if "printf" in self.module.globals:
            self.printf = self.module.globals["printf"]
        else:
            self.printf = ir.Function(self.module, printf_ty, name="printf")

    def _get_string_global(self, s: str) -> ir.GlobalVariable:
        """Return a global constant for the given Python string `s` (null-terminated)."""
        if s in self.string_constants:
            return self.string_constants[s]
        data = bytearray(s.encode("utf8")) + b"\0"
        const = ir.Constant(ir.ArrayType(ir.IntType(8), len(data)), data)
        name = f"str_{len(self.string_constants)}"
        gvar = ir.GlobalVariable(self.module, const.type, name=name)
        gvar.linkage = "internal"
        gvar.global_constant = True
        gvar.initializer = const
        self.string_constants[s] = gvar
        return gvar

    def _is_i8_ptr(self, val: ir.Value) -> bool:
        """Return True if val is an i8* pointer (string pointer)."""
        return isinstance(val.type, ir.PointerType) and isinstance(val.type.pointee, ir.IntType) and val.type.pointee.width == 8

    def _printf(self, fmt_literal: str, *args):
        """Helper to call printf with a format string literal and args (LLVM values)."""
        g_fmt = self._get_string_global(fmt_literal)
        fmt_ptr = self.builder.bitcast(g_fmt, ir.IntType(8).as_pointer())
        return self.builder.call(self.printf, [fmt_ptr, *args])

    # --- Top-level generate ---
    def generate(self, node):
        # create `int main()` function
        func_ty = ir.FunctionType(ir.IntType(32), [])
        self.func = ir.Function(self.module, func_ty, name="main")
        entry = self.func.append_basic_block(name="entry")
        self.builder = ir.IRBuilder(entry)

        self.codegen(node)

        # ensure main returns 0
        self.builder.ret(ir.IntType(32)(0))
        return str(self.module)

    def codegen(self, node):
        method = getattr(self, f"codegen_{type(node).__name__}", None)
        if not method:
            raise NotImplementedError(f"No codegen method for {type(node).__name__}")
        return method(node)

    # === AST handlers ===
    def codegen_Program(self, node: Program):
        for stmt in node.statements:
            self.codegen(stmt)

    def codegen_Block(self, node: Block):
        for stmt in node.statements:
            self.codegen(stmt)

    def codegen_Number(self, node: Number):
        return ir.IntType(32)(node.value)

    def codegen_String(self, node: String):
        # Return Python string; will turn into global when needed
        return node.value

    def codegen_VarDecl(self, node: VarDecl):
        # If expression is a string literal, create/store a global string var
        if isinstance(node.expr, String):
            literal = self.codegen(node.expr)  # Python str
            gvar = self._get_string_global(literal)
            # store the global variable object in variables map
            self.variables[node.name] = gvar
            return gvar
        else:
            # integer (or numeric expression)
            val = self.codegen(node.expr)
            ptr = self.builder.alloca(ir.IntType(32), name=node.name)
            self.builder.store(val, ptr)
            self.variables[node.name] = ptr
            return ptr

    def codegen_Var(self, node: Var):
        if node.name not in self.variables:
            raise NameError(f"Undefined variable: {node.name}")
        var = self.variables[node.name]
        # string globals are GlobalVariable objects -> return i8*
        if isinstance(var, ir.GlobalVariable):
            return self.builder.bitcast(var, ir.IntType(8).as_pointer())
        # otherwise it's an alloca ptr for integer -> load i32
        return self.builder.load(var, name=node.name)

    def codegen_Assign(self, node: Assign):
        # assignment must target existing var (per your parser semantics)
        if node.name not in self.variables:
            raise NameError(f"Assign to undefined variable: {node.name}")

        # if assigning a string literal: create new global and update mapping
        if isinstance(node.expr, String):
            literal = self.codegen(node.expr)
            gvar = self._get_string_global(literal)
            self.variables[node.name] = gvar
            return gvar

        # numeric expr
        val = self.codegen(node.expr)
        var = self.variables[node.name]
        if isinstance(var, ir.GlobalVariable):
            # previously a string var, replacing with string expected; error if trying to store int
            raise TypeError(f"Cannot store integer into string variable '{node.name}'")
        else:
            # store integer into existing alloca
            self.builder.store(val, var)
            return var

    def codegen_BinaryOp(self, node: BinaryOp):
        # left/right may be i32 or i8*? (we only support numeric binary ops here)
        left = self.codegen(node.left)
        right = self.codegen(node.right)
        op = node.op

        # arithmetic (assume ints)
        if op == TokenType.PLUS:
            return self.builder.add(left, right)
        if op == TokenType.MINUS:
            return self.builder.sub(left, right)
        if op == TokenType.ASTERISK:
            return self.builder.mul(left, right)
        if op == TokenType.SLASH:
            return self.builder.sdiv(left, right)
        if op == TokenType.PERCENT:
            return self.builder.srem(left, right)

        # comparisons -> produce i1 (boolean) for branching
        if op == TokenType.GT:
            return self.builder.icmp_signed(">", left, right)
        if op == TokenType.LT:
            return self.builder.icmp_signed("<", left, right)
        if op == TokenType.GTEQ:
            return self.builder.icmp_signed(">=", left, right)
        if op == TokenType.LTEQ:
            return self.builder.icmp_signed("<=", left, right)
        if op == TokenType.EQEQ:
            return self.builder.icmp_signed("==", left, right)
        if op == TokenType.NOTEQ:
            return self.builder.icmp_signed("!=", left, right)

        raise NotImplementedError(f"Unknown binary op {op}")

    def codegen_UnaryOp(self, node: UnaryOp):
        val = self.codegen(node.operand)
        op = node.op
        if op == TokenType.MINUS:
            return self.builder.neg(val)
        if op == TokenType.PLUS:
            return val
        raise NotImplementedError(f"Unknown unary op {op}")

    def codegen_Print(self, node: Print):
        """
        Print handles:
         - string literal (AST String) -> prints "%s\n" global
         - string variable (i8* returned from codegen_Var) -> print with "%s\n"
         - integer or comparison (i32 or i1) -> print with "%d\n"
        """
        # If expr is a string literal AST node
        if isinstance(node.expr, String):
            literal = self.codegen(node.expr)  # Python str
            g = self._get_string_global(literal)
            sptr = self.builder.bitcast(g, ir.IntType(8).as_pointer())
            self._printf("%s\n", sptr)
            return

        # Otherwise evaluate expression
        val = self.codegen(node.expr)

        # If codegen returned an i8* pointer (string variable), print with %s
        if self._is_i8_ptr(val):
            self._printf("%s\n", val)
            return

        # Otherwise, treat as integer. If it's i1 (cmp), zext to i32.
        if isinstance(val.type, ir.IntType) and val.type.width == 1:
            val = self.builder.zext(val, ir.IntType(32))
        elif isinstance(val.type, ir.IntType) and val.type.width != 32:
            # truncate/extend to 32 if necessary (future-proof)
            if val.type.width > 32:
                val = self.builder.trunc(val, ir.IntType(32))
            else:
                val = self.builder.zext(val, ir.IntType(32))

        # call printf("%d\n", val)
        self._printf("%d\n", val)

    def codegen_If(self, node: If):
        # condition may produce i1 or i32; ensure i1 for branch
        cond_val = self.codegen(node.condition)
        if not (isinstance(cond_val.type, ir.IntType) and cond_val.type.width == 1):
            # convert i32 -> i1 by comparing != 0
            cond_bool = self.builder.icmp_signed("!=", cond_val, ir.Constant(ir.IntType(32), 0))
        else:
            cond_bool = cond_val

        then_bb = self.func.append_basic_block("if.then")
        else_bb = self.func.append_basic_block("if.else") if node.else_block else None
        merge_bb = self.func.append_basic_block("if.end")

        if else_bb:
            self.builder.cbranch(cond_bool, then_bb, else_bb)
        else:
            self.builder.cbranch(cond_bool, then_bb, merge_bb)

        # then
        self.builder.position_at_end(then_bb)
        self.codegen(node.do_block)
        self.builder.branch(merge_bb)

        # else
        if node.else_block:
            self.builder.position_at_end(else_bb)
            self.codegen(node.else_block)
            self.builder.branch(merge_bb)

        # continue at merge
        self.builder.position_at_end(merge_bb)

    # --- output / run helpers ---
    def dump_ir(self):
        print(self.module)

    def write_ir(self, path: str):
        with open(path, "w", encoding="utf8") as f:
            f.write(str(self.module))

    def jit_run(self):
        llvm.initialize()
        llvm.initialize_native_target()
        llvm.initialize_native_asmprinter()
        target = llvm.Target.from_default_triple()
        tm = target.create_target_machine()
        backing = llvm.parse_assembly(str(self.module))
        engine = llvm.create_mcjit_compiler(backing, tm)
        engine.finalize_object()
        ptr = engine.get_function_address("main")
        import ctypes
        cfunc = ctypes.CFUNCTYPE(ctypes.c_int)(ptr)
        return cfunc()
