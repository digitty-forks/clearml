from __future__ import print_function, unicode_literals

import ast
import sys
from typing import Callable, Iterable, TextIO, Tuple, Optional, Any

import six
from six import StringIO

# Large float and imaginary literals get turned into infinities in the AST.
# We unparse those infinities to INFSTR.
INFSTR = "1e" + repr(sys.float_info.max_10_exp + 1)


def interleave(inter: Callable[[], None], f: Callable[[Any], None], seq: Iterable[Any]) -> None:
    """Call f on each item in seq, calling inter() in between."""
    seq = iter(seq)
    try:
        f(next(seq))
    except StopIteration:
        pass
    else:
        for x in seq:
            inter()
            f(x)


class Unparser:
    """Methods in this class recursively traverse an AST and
    output source code for the abstract syntax; original formatting
    is disregarded."""

    def __init__(self, tree: ast.AST, file: TextIO = sys.stdout) -> None:
        """Unparser(tree, file=sys.stdout) -> None.
        Print the source for tree to file."""
        self.f = file
        self.future_imports = []
        self._indent = 0
        self.dispatch(tree)
        print("", file=self.f)
        self.f.flush()

    def fill(self, text: str = "") -> None:
        """Indent a piece of text, according to the current indentation level"""
        self.f.write("\n" + "    " * self._indent + text)

    def write(self, text: Any) -> None:
        """Append a piece of text to the current line."""
        self.f.write(six.text_type(text))

    def enter(self) -> None:
        """Print ':', and increase the indentation."""
        self.write(":")
        self._indent += 1

    def leave(self) -> None:
        """Decrease the indentation level."""
        self._indent -= 1

    def dispatch(self, tree: ast.AST) -> None:
        """
        Dispatcher function, dispatching tree type T to method _T.
        """
        if isinstance(tree, list):
            for t in tree:
                self.dispatch(t)
            return
        meth = getattr(self, "_" + tree.__class__.__name__)
        meth(tree)

    """
    ############### Unparsing methods ######################
    # There should be one method per concrete grammar type #
    # Constructors should be grouped by sum type. Ideally, #
    # this would follow the order in the grammar, but      #
    # currently doesn't.                                   #
    ########################################################
    """

    def _Module(self, tree: ast.Module) -> None:
        for stmt in tree.body:
            self.dispatch(stmt)

    def _Interactive(self, tree: ast.Interactive) -> None:
        for stmt in tree.body:
            self.dispatch(stmt)

    def _Expression(self, tree: ast.Expression) -> None:
        self.dispatch(tree.body)

    # stmt
    def _Expr(self, tree: ast.Expr) -> None:
        self.fill()
        self.dispatch(tree.value)

    def _NamedExpr(self, tree: Any) -> None:
        self.write("(")
        self.dispatch(tree.target)
        self.write(" := ")
        self.dispatch(tree.value)
        self.write(")")

    def _Import(self, t: ast.Import) -> None:
        self.fill("import ")
        interleave(lambda: self.write(", "), self.dispatch, t.names)

    def _ImportFrom(self, t: ast.ImportFrom) -> None:
        # A from __future__ import may affect unparsing, so record it.
        if t.module and t.module == "__future__":
            self.future_imports.extend(n.name for n in t.names)

        self.fill("from ")
        self.write("." * t.level)
        if t.module:
            self.write(t.module)
        self.write(" import ")
        interleave(lambda: self.write(", "), self.dispatch, t.names)

    def _Assign(self, t: ast.Assign) -> None:
        self.fill()
        for target in t.targets:
            self.dispatch(target)
            self.write(" = ")
        self.dispatch(t.value)

    def _AugAssign(self, t: ast.AugAssign) -> None:
        self.fill()
        self.dispatch(t.target)
        self.write(" " + self.binop[t.op.__class__.__name__] + "= ")
        self.dispatch(t.value)

    def _AnnAssign(self, t: ast.AnnAssign) -> None:
        self.fill()
        if not t.simple and isinstance(t.target, ast.Name):
            self.write("(")
        self.dispatch(t.target)
        if not t.simple and isinstance(t.target, ast.Name):
            self.write(")")
        self.write(": ")
        self.dispatch(t.annotation)
        if t.value:
            self.write(" = ")
            self.dispatch(t.value)

    def _Return(self, t: ast.Return) -> None:
        self.fill("return")
        if t.value:
            self.write(" ")
            self.dispatch(t.value)

    def _Pass(self, t: ast.AST) -> None:
        self.fill("pass")

    def _Break(self, t: ast.Break) -> None:
        self.fill("break")

    def _Continue(self, t: ast.Continue) -> None:
        self.fill("continue")

    def _Delete(self, t: ast.Delete) -> None:
        self.fill("del ")
        interleave(lambda: self.write(", "), self.dispatch, t.targets)

    def _Assert(self, t: ast.Assert) -> None:
        self.fill("assert ")
        self.dispatch(t.test)
        if t.msg:
            self.write(", ")
            self.dispatch(t.msg)

    def _Exec(self, t: Any) -> None:
        self.fill("exec ")
        self.dispatch(t.body)
        if t.globals:
            self.write(" in ")
            self.dispatch(t.globals)
        if t.locals:
            self.write(", ")
            self.dispatch(t.locals)

    def _Print(self, t: Any) -> None:
        self.fill("print ")
        do_comma = False
        if t.dest:
            self.write(">>")
            self.dispatch(t.dest)
            do_comma = True
        for e in t.values:
            if do_comma:
                self.write(", ")
            else:
                do_comma = True
            self.dispatch(e)
        if not t.nl:
            self.write(",")

    def _Global(self, t: ast.Global) -> None:
        self.fill("global ")
        interleave(lambda: self.write(", "), self.write, t.names)

    def _Nonlocal(self, t: ast.Nonlocal) -> None:
        self.fill("nonlocal ")
        interleave(lambda: self.write(", "), self.write, t.names)

    def _Await(self, t: ast.Await) -> None:
        self.write("(")
        self.write("await")
        if t.value:
            self.write(" ")
            self.dispatch(t.value)
        self.write(")")

    def _Yield(self, t: ast.Yield) -> None:
        self.write("(")
        self.write("yield")
        if t.value:
            self.write(" ")
            self.dispatch(t.value)
        self.write(")")

    def _YieldFrom(self, t: ast.YieldFrom) -> None:
        self.write("(")
        self.write("yield from")
        if t.value:
            self.write(" ")
            self.dispatch(t.value)
        self.write(")")

    def _Raise(self, t: ast.Raise) -> None:
        self.fill("raise")
        if six.PY3:
            if not t.exc:
                assert not t.cause
                return
            self.write(" ")
            self.dispatch(t.exc)
            if t.cause:
                self.write(" from ")
                self.dispatch(t.cause)
        else:
            self.write(" ")
            if t.type:
                self.dispatch(t.type)
            if t.inst:
                self.write(", ")
                self.dispatch(t.inst)
            if t.tback:
                self.write(", ")
                self.dispatch(t.tback)

    def _Try(self, t: ast.Try) -> None:
        self.fill("try")
        self.enter()
        self.dispatch(t.body)
        self.leave()
        for ex in t.handlers:
            self.dispatch(ex)
        if t.orelse:
            self.fill("else")
            self.enter()
            self.dispatch(t.orelse)
            self.leave()
        if t.finalbody:
            self.fill("finally")
            self.enter()
            self.dispatch(t.finalbody)
            self.leave()

    def _TryExcept(self, t: ast.Try) -> None:
        self.fill("try")
        self.enter()
        self.dispatch(t.body)
        self.leave()

        for ex in t.handlers:
            self.dispatch(ex)
        if t.orelse:
            self.fill("else")
            self.enter()
            self.dispatch(t.orelse)
            self.leave()

    def _TryFinally(self, t: ast.Try) -> None:
        if len(t.body) == 1 and isinstance(t.body[0], ast.Try):
            # try-except-finally
            self.dispatch(t.body)
        else:
            self.fill("try")
            self.enter()
            self.dispatch(t.body)
            self.leave()

        self.fill("finally")
        self.enter()
        self.dispatch(t.finalbody)
        self.leave()

    def _ExceptHandler(self, t: ast.ExceptHandler) -> None:
        self.fill("except")
        if t.type:
            self.write(" ")
            self.dispatch(t.type)
        if t.name:
            self.write(" as ")
            if six.PY3:
                self.write(t.name)
            else:
                self.dispatch(t.name)
        self.enter()
        self.dispatch(t.body)
        self.leave()

    def _ClassDef(self, t: ast.ClassDef) -> None:
        self.write("\n")
        for deco in t.decorator_list:
            self.fill("@")
            self.dispatch(deco)
        self.fill("class " + t.name)
        if six.PY3:
            self.write("(")
            comma = False
            for e in t.bases:
                if comma:
                    self.write(", ")
                else:
                    comma = True
                self.dispatch(e)
            for e in t.keywords:
                if comma:
                    self.write(", ")
                else:
                    comma = True
                self.dispatch(e)
            if sys.version_info[:2] < (3, 5):
                if t.starargs:
                    if comma:
                        self.write(", ")
                    else:
                        comma = True
                    self.write("*")
                    self.dispatch(t.starargs)
                if t.kwargs:
                    if comma:
                        self.write(", ")
                    else:
                        comma = True
                    self.write("**")
                    self.dispatch(t.kwargs)
            self.write(")")
        elif t.bases:
            self.write("(")
            for a in t.bases:
                self.dispatch(a)
                self.write(", ")
            self.write(")")
        self.enter()
        self.dispatch(t.body)
        self.leave()

    def _FunctionDef(self, t: ast.FunctionDef) -> None:
        self.__FunctionDef_helper(t, "def")

    def _AsyncFunctionDef(self, t: ast.AsyncFunctionDef) -> None:
        self.__FunctionDef_helper(t, "async def")

    def __FunctionDef_helper(self, t: ast.FunctionDef, fill_suffix: str) -> None:
        self.write("\n")
        for deco in t.decorator_list:
            self.fill("@")
            self.dispatch(deco)
        def_str = fill_suffix + " " + t.name + "("
        self.fill(def_str)
        self.dispatch(t.args)
        self.write(")")
        if getattr(t, "returns", False):
            self.write(" -> ")
            self.dispatch(t.returns)
        self.enter()
        self.dispatch(t.body)
        self.leave()

    def _For(self, t: ast.For) -> None:
        self.__For_helper("for ", t)

    def _AsyncFor(self, t: ast.AsyncFor) -> None:
        self.__For_helper("async for ", t)

    def __For_helper(self, fill: str, t: ast.For) -> None:
        self.fill(fill)
        self.dispatch(t.target)
        self.write(" in ")
        self.dispatch(t.iter)
        self.enter()
        self.dispatch(t.body)
        self.leave()
        if t.orelse:
            self.fill("else")
            self.enter()
            self.dispatch(t.orelse)
            self.leave()

    def _If(self, t: ast.If) -> None:
        self.fill("if ")
        self.dispatch(t.test)
        self.enter()
        self.dispatch(t.body)
        self.leave()
        # collapse nested ifs into equivalent elifs.
        while t.orelse and len(t.orelse) == 1 and isinstance(t.orelse[0], ast.If):
            t = t.orelse[0]
            self.fill("elif ")
            self.dispatch(t.test)
            self.enter()
            self.dispatch(t.body)
            self.leave()
        # final else
        if t.orelse:
            self.fill("else")
            self.enter()
            self.dispatch(t.orelse)
            self.leave()

    def _While(self, t: ast.While) -> None:
        self.fill("while ")
        self.dispatch(t.test)
        self.enter()
        self.dispatch(t.body)
        self.leave()
        if t.orelse:
            self.fill("else")
            self.enter()
            self.dispatch(t.orelse)
            self.leave()

    def _generic_With(self, t: ast.withitem, async_: bool = False) -> None:
        self.fill("async with " if async_ else "with ")
        if hasattr(t, "items"):
            interleave(lambda: self.write(", "), self.dispatch, t.items)
        else:
            self.dispatch(t.context_expr)
            if t.optional_vars:
                self.write(" as ")
                self.dispatch(t.optional_vars)
        self.enter()
        self.dispatch(t.body)
        self.leave()

    def _With(self, t: Any) -> None:
        self._generic_With(t)

    def _AsyncWith(self, t: ast.AsyncWith) -> None:
        self._generic_With(t, async_=True)

    # expr
    def _Bytes(self, t: ast.Bytes) -> None:
        self.write(repr(t.s))

    def _Str(self, tree: ast.Str) -> None:
        if six.PY3:
            self.write(repr(tree.s))
        else:
            # if from __future__ import unicode_literals is in effect,
            # then we want to output string literals using a 'b' prefix
            # and unicode literals with no prefix.
            if "unicode_literals" not in self.future_imports:
                self.write(repr(tree.s))
            elif isinstance(tree.s, str):
                self.write("b" + repr(tree.s))
            elif isinstance(tree.s, unicode):  # noqa
                self.write(repr(tree.s).lstrip("u"))
            else:
                assert False, "shouldn't get here"

    def _JoinedStr(self, t: ast.JoinedStr) -> None:
        # JoinedStr(expr* values)
        self.write("f")
        string = StringIO()
        self._fstring_JoinedStr(t, string.write)
        # Deviation from `unparse.py`: Try to find an unused quote.
        # This change is made to handle _very_ complex f-strings.
        v = string.getvalue()
        if "\n" in v or "\r" in v:
            quote_types = ["'''", '"""']
        else:
            quote_types = ["'", '"', '"""', "'''"]
        for quote_type in quote_types:
            if quote_type not in v:
                v = "{quote_type}{v}{quote_type}".format(quote_type=quote_type, v=v)
                break
        else:
            v = repr(v)
        self.write(v)

    def _FormattedValue(self, t: ast.FormattedValue) -> None:
        # FormattedValue(expr value, int? conversion, expr? format_spec)
        self.write("f")
        string = StringIO()
        self._fstring_JoinedStr(t, string.write)
        self.write(repr(string.getvalue()))

    def _fstring_JoinedStr(self, t: ast.JoinedStr, write: Callable[[str], None]) -> None:
        for value in t.values:
            meth = getattr(self, "_fstring_" + type(value).__name__)
            meth(value, write)

    def _fstring_Str(self, t: ast.Str, write: Callable[[str], None]) -> None:
        value = t.s.replace("{", "{{").replace("}", "}}")
        write(value)

    def _fstring_Constant(self, t: ast.Constant, write: Callable[[str], None]) -> None:
        assert isinstance(t.value, str)
        value = t.value.replace("{", "{{").replace("}", "}}")
        write(value)

    def _fstring_FormattedValue(self, t: ast.FormattedValue, write: Callable[[str], None]) -> None:
        write("{")
        expr = StringIO()
        Unparser(t.value, expr)
        expr = expr.getvalue().rstrip("\n")
        if expr.startswith("{"):
            write(" ")  # Separate pair of opening brackets as "{ {"
        write(expr)
        if t.conversion != -1:
            conversion = chr(t.conversion)
            assert conversion in "sra"
            write("!{conversion}".format(conversion=conversion))
        if t.format_spec:
            write(":")
            meth = getattr(self, "_fstring_" + type(t.format_spec).__name__)
            meth(t.format_spec, write)
        write("}")

    def _Name(self, t: ast.Name) -> None:
        self.write(t.id)

    def _NameConstant(self, t: ast.NameConstant) -> None:
        self.write(repr(t.value))

    def _Repr(self, t: ast.AST) -> None:
        self.write("`")
        self.dispatch(t.value)
        self.write("`")

    def _write_constant(self, value: Any) -> None:
        if isinstance(value, (float, complex)):
            # Substitute overflowing decimal literal for AST infinities.
            self.write(repr(value).replace("inf", INFSTR))
        else:
            self.write(repr(value))

    def _Constant(self, t: ast.Constant) -> None:
        value = t.value
        if isinstance(value, tuple):
            self.write("(")
            if len(value) == 1:
                self._write_constant(value[0])
                self.write(",")
            else:
                interleave(lambda: self.write(", "), self._write_constant, value)
            self.write(")")
        elif value is Ellipsis:  # instead of `...` for Py2 compatibility
            self.write("...")
        else:
            if t.kind == "u":
                self.write("u")
            self._write_constant(t.value)

    def _Num(self, t: ast.Num) -> None:
        repr_n = repr(t.n)
        if six.PY3:
            self.write(repr_n.replace("inf", INFSTR))
        else:
            # Parenthesize negative numbers, to avoid turning (-1)**2 into -1**2.
            if repr_n.startswith("-"):
                self.write("(")
            if "inf" in repr_n and repr_n.endswith("*j"):
                repr_n = repr_n.replace("*j", "j")
            # Substitute overflowing decimal literal for AST infinities.
            self.write(repr_n.replace("inf", INFSTR))
            if repr_n.startswith("-"):
                self.write(")")

    def _List(self, t: ast.List) -> None:
        self.write("[")
        interleave(lambda: self.write(", "), self.dispatch, t.elts)
        self.write("]")

    def _ListComp(self, t: ast.ListComp) -> None:
        self.write("[")
        self.dispatch(t.elt)
        for gen in t.generators:
            self.dispatch(gen)
        self.write("]")

    def _GeneratorExp(self, t: ast.GeneratorExp) -> None:
        self.write("(")
        self.dispatch(t.elt)
        for gen in t.generators:
            self.dispatch(gen)
        self.write(")")

    def _SetComp(self, t: ast.SetComp) -> None:
        self.write("{")
        self.dispatch(t.elt)
        for gen in t.generators:
            self.dispatch(gen)
        self.write("}")

    def _DictComp(self, t: ast.DictComp) -> None:
        self.write("{")
        self.dispatch(t.key)
        self.write(": ")
        self.dispatch(t.value)
        for gen in t.generators:
            self.dispatch(gen)
        self.write("}")

    def _comprehension(self, t: ast.comprehension) -> None:
        if getattr(t, "is_async", False):
            self.write(" async for ")
        else:
            self.write(" for ")
        self.dispatch(t.target)
        self.write(" in ")
        self.dispatch(t.iter)
        for if_clause in t.ifs:
            self.write(" if ")
            self.dispatch(if_clause)

    def _IfExp(self, t: ast.IfExp) -> None:
        self.write("(")
        self.dispatch(t.body)
        self.write(" if ")
        self.dispatch(t.test)
        self.write(" else ")
        self.dispatch(t.orelse)
        self.write(")")

    def _Set(self, t: ast.Set) -> None:
        assert t.elts  # should be at least one element
        self.write("{")
        interleave(lambda: self.write(", "), self.dispatch, t.elts)
        self.write("}")

    def _Dict(self, t: ast.Dict) -> None:
        self.write("{")

        def write_key_value_pair(k: Any, v: Any) -> None:
            self.dispatch(k)
            self.write(": ")
            self.dispatch(v)

        def write_item(item: Tuple[Optional[Any], Any]) -> None:
            k, v = item
            if k is None:
                # for dictionary unpacking operator in dicts {**{'y': 2}}
                # see PEP 448 for details
                self.write("**")
                self.dispatch(v)
            else:
                write_key_value_pair(k, v)

        interleave(lambda: self.write(", "), write_item, zip(t.keys, t.values))
        self.write("}")

    def _Tuple(self, t: ast.Tuple) -> None:
        self.write("(")
        if len(t.elts) == 1:
            elt = t.elts[0]
            self.dispatch(elt)
            self.write(",")
        else:
            interleave(lambda: self.write(", "), self.dispatch, t.elts)
        self.write(")")

    unop = {"Invert": "~", "Not": "not", "UAdd": "+", "USub": "-"}

    def _UnaryOp(self, t: ast.UnaryOp) -> None:
        self.write("(")
        self.write(self.unop[t.op.__class__.__name__])
        self.write(" ")
        if six.PY2 and isinstance(t.op, ast.USub) and isinstance(t.operand, ast.Num):
            # If we're applying unary minus to a number, parenthesize the number.
            # This is necessary: -2147483648 is different from -(2147483648) on
            # a 32-bit machine (the first is an int, the second a long), and
            # -7j is different from -(7j).  (The first has real part 0.0, the second
            # has real part -0.0.)
            self.write("(")
            self.dispatch(t.operand)
            self.write(")")
        else:
            self.dispatch(t.operand)
        self.write(")")

    binop = {
        "Add": "+",
        "Sub": "-",
        "Mult": "*",
        "MatMult": "@",
        "Div": "/",
        "Mod": "%",
        "LShift": "<<",
        "RShift": ">>",
        "BitOr": "|",
        "BitXor": "^",
        "BitAnd": "&",
        "FloorDiv": "//",
        "Pow": "**",
    }

    def _BinOp(self, t: ast.BinOp) -> None:
        self.write("(")
        self.dispatch(t.left)
        self.write(" " + self.binop[t.op.__class__.__name__] + " ")
        self.dispatch(t.right)
        self.write(")")

    cmpops = {
        "Eq": "==",
        "NotEq": "!=",
        "Lt": "<",
        "LtE": "<=",
        "Gt": ">",
        "GtE": ">=",
        "Is": "is",
        "IsNot": "is not",
        "In": "in",
        "NotIn": "not in",
    }

    def _Compare(self, t: ast.Compare) -> None:
        self.write("(")
        self.dispatch(t.left)
        for o, e in zip(t.ops, t.comparators):
            self.write(" " + self.cmpops[o.__class__.__name__] + " ")
            self.dispatch(e)
        self.write(")")

    boolops = {ast.And: "and", ast.Or: "or"}

    def _BoolOp(self, t: ast.BoolOp) -> None:
        self.write("(")
        s = " %s " % self.boolops[t.op.__class__]
        interleave(lambda: self.write(s), self.dispatch, t.values)
        self.write(")")

    def _Attribute(self, t: ast.Attribute) -> None:
        self.dispatch(t.value)
        # Special case: 3.__abs__() is a syntax error, so if t.value
        # is an integer literal then we need to either parenthesize
        # it or add an extra space to get 3 .__abs__().
        if isinstance(t.value, getattr(ast, "Constant", getattr(ast, "Num", None))) and isinstance(t.value.n, int):
            self.write(" ")
        self.write(".")
        self.write(t.attr)

    def _Call(self, t: ast.Call) -> None:
        self.dispatch(t.func)
        self.write("(")
        comma = False
        for e in t.args:
            if comma:
                self.write(", ")
            else:
                comma = True
            self.dispatch(e)
        for e in t.keywords:
            if comma:
                self.write(", ")
            else:
                comma = True
            self.dispatch(e)
        if sys.version_info[:2] < (3, 5):
            if t.starargs:
                if comma:
                    self.write(", ")
                else:
                    comma = True
                self.write("*")
                self.dispatch(t.starargs)
            if t.kwargs:
                if comma:
                    self.write(", ")
                else:
                    comma = True
                self.write("**")
                self.dispatch(t.kwargs)
        self.write(")")

    def _Subscript(self, t: ast.Subscript) -> None:
        self.dispatch(t.value)
        self.write("[")
        self.dispatch(t.slice)
        self.write("]")

    def _Starred(self, t: ast.Starred) -> None:
        self.write("*")
        self.dispatch(t.value)

    # slice
    def _Ellipsis(self, t: ast.Ellipsis) -> None:
        self.write("...")

    def _Index(self, t: ast.Index) -> None:
        self.dispatch(t.value)

    def _Slice(self, t: ast.Slice) -> None:
        if t.lower:
            self.dispatch(t.lower)
        self.write(":")
        if t.upper:
            self.dispatch(t.upper)
        if t.step:
            self.write(":")
            self.dispatch(t.step)

    def _ExtSlice(self, t: ast.ExtSlice) -> None:
        interleave(lambda: self.write(", "), self.dispatch, t.dims)

    # argument
    def _arg(self, t: ast.arg) -> None:
        self.write(t.arg)
        if t.annotation:
            self.write(": ")
            self.dispatch(t.annotation)

    # others
    def _arguments(self, t: ast.arguments) -> None:
        first = True
        # normal arguments
        all_args = getattr(t, "posonlyargs", []) + t.args
        defaults = [None] * (len(all_args) - len(t.defaults)) + t.defaults
        for index, elements in enumerate(zip(all_args, defaults), 1):
            a, d = elements
            if first:
                first = False
            else:
                self.write(", ")
            self.dispatch(a)
            if d:
                self.write("=")
                self.dispatch(d)
            if index == len(getattr(t, "posonlyargs", ())):
                self.write(", /")

        # varargs, or bare '*' if no varargs but keyword-only arguments present
        if t.vararg or getattr(t, "kwonlyargs", False):
            if first:
                first = False
            else:
                self.write(", ")
            self.write("*")
            if t.vararg:
                if hasattr(t.vararg, "arg"):
                    self.write(t.vararg.arg)
                    if t.vararg.annotation:
                        self.write(": ")
                        self.dispatch(t.vararg.annotation)
                else:
                    self.write(t.vararg)
                    if getattr(t, "varargannotation", None):
                        self.write(": ")
                        self.dispatch(t.varargannotation)

        # keyword-only arguments
        if getattr(t, "kwonlyargs", False):
            for a, d in zip(t.kwonlyargs, t.kw_defaults):
                if first:
                    first = False
                else:
                    self.write(", ")
                self.dispatch(a),
                if d:
                    self.write("=")
                    self.dispatch(d)

        # kwargs
        if t.kwarg:
            if first:
                first = False
            else:
                self.write(", ")
            if hasattr(t.kwarg, "arg"):
                self.write("**" + t.kwarg.arg)
                if t.kwarg.annotation:
                    self.write(": ")
                    self.dispatch(t.kwarg.annotation)
            else:
                self.write("**" + t.kwarg)
                if getattr(t, "kwargannotation", None):
                    self.write(": ")
                    self.dispatch(t.kwargannotation)

    def _keyword(self, t: ast.keyword) -> None:
        if t.arg is None:
            # starting from Python 3.5 this denotes a kwargs part of the invocation
            self.write("**")
        else:
            self.write(t.arg)
            self.write("=")
        self.dispatch(t.value)

    def _Lambda(self, t: ast.Lambda) -> None:
        self.write("(")
        self.write("lambda ")
        self.dispatch(t.args)
        self.write(": ")
        self.dispatch(t.body)
        self.write(")")

    def _alias(self, t: ast.alias) -> None:
        self.write(t.name)
        if t.asname:
            self.write(" as " + t.asname)

    def _withitem(self, t: ast.withitem) -> None:
        self.dispatch(t.context_expr)
        if t.optional_vars:
            self.write(" as ")
            self.dispatch(t.optional_vars)


def unparse(tree: ast.AST) -> str:
    v = six.moves.cStringIO()
    Unparser(tree, file=v)
    return v.getvalue()
