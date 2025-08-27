import llvmlite.ir as ir
import llvmlite.binding as llvm
from utils.lexer import TokenType
from utils.ast import *

# Initialize LLVM
llvm.initialize()
llvm.initialize_native_target()
llvm.initialize_native_asmprinter()

class Codegen:
    def __init__(self):
        self.module = ir.Module(name="kujie_module")
        self.builder = None
        self.func = None
        self.printf = None
        self.variables = {}
        self.string_constants = {}  # track string constants
        self._declare_printf()

    def _declare_printf(self):
        voidptr_ty = ir.IntType(8).as_pointer()
        printf_ty = ir.FunctionType(ir.IntType(32), [voidptr_ty], var_arg=True)
        self.printf = ir.Function(self.module, printf_ty, name="printf")

    def _get_string_global(self, string_val):
        if string_val in self.string_constants:
            return self.string_constants[string_val]
        name = f"str_{len(self.string_constants)}"
        c_fmt = ir.Constant(ir.ArrayType(ir.IntType(8), len(string_val)+1),
                            bytearray(string_val.encode("utf8")+b'\0'))
        gvar = ir.GlobalVariable(self.module, c_fmt.type, name=name)
        gvar.linkage = 'internal'
        gvar.global_constant = True
        gvar.initializer = c_fmt
        self.string_constants[string_val] = gvar
        return gvar

    def generate(self, node):
        func_ty = ir.FunctionType(ir.IntType(32), [])
        self.func = ir.Function(self.module, func_ty, name="main")
        block = self.func.append_basic_block(name="entry")
        self.builder = ir.IRBuilder(block)
        self.codegen(node)
        self.builder.ret(ir.IntType(32)(0))
        return str(self.module)

    def codegen(self, node):
        method_name = f"codegen_{type(node).__name__}"
        method = getattr(self, method_name, None)
        if not method:
            raise NotImplementedError(f"No codegen method for {type(node).__name__}")
        return method(node)

    # === AST Handlers ===
    def codegen_Program(self, node):
        for stmt in node.statements:
            self.codegen(stmt)

    def codegen_Block(self, node):
        for stmt in node.statements:
            self.codegen(stmt)

    def codegen_Number(self, node):
        return ir.IntType(32)(node.value)

    def codegen_String(self, node):
        return node.value

    def codegen_VarDecl(self, node):
        val = self.codegen(node.expr)
        if isinstance(node.expr, String):
            # Strings are stored as global variables
            gvar = self._get_string_global(val)
            self.variables[node.name] = gvar
        else:
            # Integers
            ptr = self.builder.alloca(ir.IntType(32), name=node.name)
            self.builder.store(val, ptr)
            self.variables[node.name] = ptr

    def codegen_Var(self, node):
        var = self.variables[node.name]
        if isinstance(var, ir.GlobalVariable):
            # String variable, return pointer
            return self.builder.bitcast(var, ir.IntType(8).as_pointer())
        else:
            # Integer variable
            return self.builder.load(var, name=node.name)


    def codegen_Assign(self, node):
        val = self.codegen(node.expr)
        ptr = self.variables[node.name]
        if isinstance(ptr.type.pointee, ir.ArrayType):
            # For string assignment, override the global pointer
            gvar = self._get_string_global(val)
            self.variables[node.name] = gvar
        else:
            self.builder.store(val, ptr)

    def codegen_BinaryOp(self, node):
        left = self.codegen(node.left)
        right = self.codegen(node.right)
        op = node.op

        if op == TokenType.PLUS:
            return self.builder.add(left, right)
        elif op == TokenType.MINUS:
            return self.builder.sub(left, right)
        elif op == TokenType.ASTERISK:
            return self.builder.mul(left, right)
        elif op == TokenType.SLASH:
            return self.builder.sdiv(left, right)
        elif op == TokenType.PERCENT:
            return self.builder.srem(left, right)
        # Comparison ops -> return i1
        elif op == TokenType.GT:
            return self.builder.icmp_signed('>', left, right)
        elif op == TokenType.LT:
            return self.builder.icmp_signed('<', left, right)
        elif op == TokenType.GTEQ:
            return self.builder.icmp_signed('>=', left, right)
        elif op == TokenType.LTEQ:
            return self.builder.icmp_signed('<=', left, right)
        elif op == TokenType.EQEQ:
            return self.builder.icmp_signed('==', left, right)
        elif op == TokenType.NOTEQ:
            return self.builder.icmp_signed('!=', left, right)
        else:
            raise NotImplementedError(f"Unknown binary op {op}")

    def codegen_UnaryOp(self, node):
        val = self.codegen(node.operand)
        op = node.op
        if op == TokenType.MINUS:
            return self.builder.neg(val)
        elif op == TokenType.PLUS:
            return val
        else:
            raise NotImplementedError(f"Unknown unary op {op}")

    def codegen_Print(self, node):
        val = self.codegen(node.expr)
        # String
        if isinstance(node.expr, String):
            gvar = self._get_string_global(val)
            fmt_ptr = self.builder.bitcast(gvar, ir.IntType(8).as_pointer())
            self.builder.call(self.printf, [fmt_ptr])
        else:
            # int or i1
            if val.type == ir.IntType(1):
                val = self.builder.zext(val, ir.IntType(32))
            fmt_str = "%d\n"
            gvar = self._get_string_global(fmt_str)
            fmt_ptr = self.builder.bitcast(gvar, ir.IntType(8).as_pointer())
            self.builder.call(self.printf, [fmt_ptr, val])

    def codegen_If(self, node):
        cond_val = self.codegen(node.condition)

        then_bb = self.func.append_basic_block("if.then")
        else_bb = self.func.append_basic_block("if.else") if node.else_block else None
        merge_bb = self.func.append_basic_block("if.end")

        if else_bb:
            self.builder.cbranch(cond_val, then_bb, else_bb)
        else:
            self.builder.cbranch(cond_val, then_bb, merge_bb)

        # Then block
        self.builder.position_at_end(then_bb)
        self.codegen(node.do_block)
        self.builder.branch(merge_bb)

        # Else block
        if node.else_block:
            self.builder.position_at_end(else_bb)
            self.codegen(node.else_block)
            self.builder.branch(merge_bb)

        # Merge
        self.builder.position_at_end(merge_bb)

    # ----------------- output / run helpers -----------------
    def dump_ir(self):
        print(self.module)

    def write_ir(self, path):
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
