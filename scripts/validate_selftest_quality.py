#!/usr/bin/env python3
"""Validate self-test quality for current critical evaluator scripts.

This intentionally scans a narrow allowlist: the current FRK product-workflow
and TraceV2/HAAE evaluator chain. Older historical experiment scripts still
contain legacy self-test idioms and should be hardened separately when they
become active evidence routes.
"""

from __future__ import annotations

import argparse
import ast
import sys
from dataclasses import dataclass
from pathlib import Path


REPO = Path(__file__).resolve().parent.parent

DEFAULT_TARGETS = (
    "eval/frk_product_workflow_trace_benchmark.py",
    "eval/frk_product_workflow_failure_decomposition.py",
    "eval/frk_product_workflow_specific_retrieval_repair_design.py",
    "eval/frk_product_workflow_bounded_retrieval_repair_prototype.py",
    "eval/state_action_trace_v2_bootstrap.py",
    "eval/frk_p2_workflow_v2_task_state_capture_expansion.py",
    "eval/frk_p2r_targeted_capture_repair.py",
    "eval/haae_a2_offline_action_replay_smoke.py",
)

CHECK_NAMES = {"check", "_check"}
CHECK_CONDITION_KEYWORDS = {"condition", "ok"}
SELF_TEST_FUNCTION_NAMES = {"run_self_test", "run_self_tests"}
EXPECTED_TEXT_BOOLEAN_METHODS = {"startswith", "endswith"}


@dataclass(frozen=True)
class Issue:
    path: Path
    line: int
    column: int
    code: str
    message: str

    def format(self) -> str:
        rel = self.path.relative_to(REPO) if self.path.is_relative_to(REPO) else self.path
        return f"{rel}:{self.line}:{self.column}: {self.code}: {self.message}"


@dataclass(frozen=True)
class CheckExpression:
    call: ast.Call
    condition: ast.AST


class SelfTestQualityVisitor(ast.NodeVisitor):
    def __init__(self, path: Path) -> None:
        self.path = path
        self.issues: list[Issue] = []
        self.check_count = 0
        self.selftest_check_count = 0
        self.selftest_function_count = 0
        self._function_stack: list[str] = []
        self._deferred_scope_depth = 0
        self._unreachable_scope_depth = 0

    def visit_Module(self, node: ast.Module) -> None:
        self._visit_statements(node.body)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        if node.name in SELF_TEST_FUNCTION_NAMES:
            self.selftest_function_count += 1
        self._function_stack.append(node.name)
        if node.name not in SELF_TEST_FUNCTION_NAMES:
            self._deferred_scope_depth += 1
        self._visit_statements(node.body)
        if node.name not in SELF_TEST_FUNCTION_NAMES:
            self._deferred_scope_depth -= 1
        self._function_stack.pop()

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        if node.name in SELF_TEST_FUNCTION_NAMES:
            self.selftest_function_count += 1
        self._function_stack.append(node.name)
        if node.name not in SELF_TEST_FUNCTION_NAMES:
            self._deferred_scope_depth += 1
        self._visit_statements(node.body)
        if node.name not in SELF_TEST_FUNCTION_NAMES:
            self._deferred_scope_depth -= 1
        self._function_stack.pop()

    def visit_Lambda(self, node: ast.Lambda) -> None:
        self._deferred_scope_depth += 1
        self.generic_visit(node)
        self._deferred_scope_depth -= 1

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        self._deferred_scope_depth += 1
        self._visit_statements(node.body)
        self._deferred_scope_depth -= 1

    def visit_If(self, node: ast.If) -> None:
        self.visit(node.test)
        test_truth = self._literal_truth_value(node.test)
        if test_truth is True:
            self._visit_statements(node.body)
            self._visit_unreachable_statements(node.orelse)
            return
        if test_truth is False:
            self._visit_unreachable_statements(node.body)
            self._visit_statements(node.orelse)
            return
        self._visit_statements(node.body)
        self._visit_statements(node.orelse)

    def visit_While(self, node: ast.While) -> None:
        self.visit(node.test)
        if self._literal_truth_value(node.test) is False:
            self._visit_unreachable_statements(node.body)
            self._visit_statements(node.orelse)
            return
        self._visit_statements(node.body)
        self._visit_statements(node.orelse)

    def visit_For(self, node: ast.For) -> None:
        self.visit(node.target)
        self.visit(node.iter)
        if self._literal_truth_value(node.iter) is False:
            self._visit_unreachable_statements(node.body)
            self._visit_statements(node.orelse)
            return
        self._visit_statements(node.body)
        self._visit_statements(node.orelse)

    def visit_AsyncFor(self, node: ast.AsyncFor) -> None:
        self.visit(node.target)
        self.visit(node.iter)
        if self._literal_truth_value(node.iter) is False:
            self._visit_unreachable_statements(node.body)
            self._visit_statements(node.orelse)
            return
        self._visit_statements(node.body)
        self._visit_statements(node.orelse)

    def visit_With(self, node: ast.With) -> None:
        self._visit_with_items(node.items)
        self._visit_statements(node.body)

    def visit_AsyncWith(self, node: ast.AsyncWith) -> None:
        self._visit_with_items(node.items)
        self._visit_statements(node.body)

    def visit_Try(self, node: ast.Try) -> None:
        self._visit_statements(node.body)
        for handler in node.handlers:
            self.visit(handler)
        self._visit_statements(node.orelse)
        self._visit_statements(node.finalbody)

    def _visit_with_items(self, items: list[ast.withitem]) -> None:
        for item in items:
            self.visit(item.context_expr)
            if item.optional_vars is not None:
                self.visit(item.optional_vars)

    def _visit_statements(self, statements: list[ast.stmt]) -> None:
        unreachable = False
        for statement in statements:
            if unreachable:
                self._visit_unreachable(statement)
            else:
                self.visit(statement)
            if self._statement_guarantees_exit(statement):
                unreachable = True

    def _visit_unreachable_statements(self, statements: list[ast.stmt]) -> None:
        for statement in statements:
            self._visit_unreachable(statement)

    def _visit_unreachable(self, node: ast.AST) -> None:
        self._unreachable_scope_depth += 1
        self.visit(node)
        self._unreachable_scope_depth -= 1

    @classmethod
    def _statement_guarantees_exit(cls, node: ast.stmt) -> bool:
        if isinstance(node, (ast.Return, ast.Raise, ast.Break, ast.Continue)):
            return True
        if isinstance(node, ast.If):
            test_truth = cls._literal_truth_value(node.test)
            if test_truth is True:
                return cls._block_guarantees_exit(node.body)
            if test_truth is False:
                return cls._block_guarantees_exit(node.orelse)
            if not node.orelse:
                return False
            return cls._block_guarantees_exit(node.body) and cls._block_guarantees_exit(node.orelse)
        if isinstance(node, ast.While):
            test_truth = cls._literal_truth_value(node.test)
            if test_truth is True:
                return cls._block_guarantees_function_exit(node.body)
            if test_truth is False:
                return cls._block_guarantees_exit(node.orelse)
            return False
        if isinstance(node, (ast.For, ast.AsyncFor)):
            iter_truth = cls._literal_truth_value(node.iter)
            if iter_truth is True:
                return cls._block_guarantees_function_exit(node.body)
            if iter_truth is False:
                return cls._block_guarantees_exit(node.orelse)
            return False
        if isinstance(node, (ast.With, ast.AsyncWith)):
            return cls._block_guarantees_return(node.body)
        if isinstance(node, ast.Try):
            if cls._block_guarantees_exit(node.finalbody):
                return True
            if node.handlers:
                return False
            return cls._block_guarantees_return(node.body)
        return False

    @classmethod
    def _block_guarantees_exit(cls, statements: list[ast.stmt]) -> bool:
        return any(cls._statement_guarantees_exit(statement) for statement in statements)

    @classmethod
    def _block_guarantees_function_exit(cls, statements: list[ast.stmt]) -> bool:
        for statement in statements:
            if cls._statement_guarantees_function_exit(statement):
                return True
            if cls._statement_guarantees_exit(statement):
                return False
        return False

    @classmethod
    def _statement_guarantees_function_exit(cls, node: ast.stmt) -> bool:
        if isinstance(node, (ast.Return, ast.Raise)):
            return True
        if isinstance(node, ast.If):
            test_truth = cls._literal_truth_value(node.test)
            if test_truth is True:
                return cls._block_guarantees_function_exit(node.body)
            if test_truth is False:
                return cls._block_guarantees_function_exit(node.orelse)
            if not node.orelse:
                return False
            return cls._block_guarantees_function_exit(node.body) and cls._block_guarantees_function_exit(node.orelse)
        if isinstance(node, (ast.With, ast.AsyncWith)):
            return cls._block_guarantees_return(node.body)
        if isinstance(node, ast.Try):
            if cls._block_guarantees_function_exit(node.finalbody):
                return True
            if node.handlers:
                return False
            return cls._block_guarantees_return(node.body)
        return False

    @classmethod
    def _block_guarantees_return(cls, statements: list[ast.stmt]) -> bool:
        for statement in statements:
            if cls._statement_guarantees_return(statement):
                return True
            if cls._statement_guarantees_exit(statement):
                return False
        return False

    @classmethod
    def _statement_guarantees_return(cls, node: ast.stmt) -> bool:
        if isinstance(node, ast.Return):
            return True
        if isinstance(node, ast.If):
            test_truth = cls._literal_truth_value(node.test)
            if test_truth is True:
                return cls._block_guarantees_return(node.body)
            if test_truth is False:
                return cls._block_guarantees_return(node.orelse)
            if not node.orelse:
                return False
            return cls._block_guarantees_return(node.body) and cls._block_guarantees_return(node.orelse)
        if isinstance(node, (ast.With, ast.AsyncWith)):
            return cls._block_guarantees_return(node.body)
        if isinstance(node, ast.Try):
            if cls._block_guarantees_return(node.finalbody):
                return True
            if node.handlers:
                return False
            return cls._block_guarantees_return(node.body)
        return False

    def visit_Call(self, node: ast.Call) -> None:
        check = self._as_check_expression(node)
        if check is None and self._is_check_call(node):
            self.issues.append(
                Issue(
                    self.path,
                    node.lineno,
                    node.col_offset,
                    "missing_check_condition",
                    "self-test check call must provide a recognized condition argument",
                )
            )
        if check is not None:
            self.check_count += 1
            if self._inside_active_selftest_body():
                self.selftest_check_count += 1
        if check is not None and self._is_truthy_literal(check.condition):
            self.issues.append(
                Issue(
                    self.path,
                    node.lineno,
                    node.col_offset,
                    "literal_true_check",
                    "self-test check uses a truthy literal as its condition",
                )
            )
        self.generic_visit(node)

    def _inside_active_selftest_body(self) -> bool:
        if self._deferred_scope_depth != 0 or self._unreachable_scope_depth != 0:
            return False
        return bool(self._function_stack) and self._function_stack[-1] in SELF_TEST_FUNCTION_NAMES

    def visit_ExceptHandler(self, node: ast.ExceptHandler) -> None:
        for check in self._check_expressions_in_body(node.body):
            if not node.name:
                self.issues.append(
                    Issue(
                        self.path,
                        check.call.lineno,
                        check.call.col_offset,
                        "exception_check_without_error_text",
                        "self-test exception handler check must bind and assert expected error text",
                    )
                )
                continue
            if not self._asserts_expected_exception_text(check.condition, node.name):
                self.issues.append(
                    Issue(
                        self.path,
                        check.call.lineno,
                        check.call.col_offset,
                        "exception_check_without_error_text",
                        "self-test exception handler check must compare expected error text with str(exc) or repr(exc)",
                    )
                )
        if node.type is not None:
            self.visit(node.type)
        self._visit_statements(node.body)

    @classmethod
    def _as_check_expression(cls, node: ast.Call) -> CheckExpression | None:
        if cls._is_check_call(node):
            condition = cls._check_call_condition(node)
            if condition is None:
                return None
            return CheckExpression(node, condition)
        tuple_condition = cls._tuple_append_condition(node)
        if tuple_condition is not None:
            return CheckExpression(node, tuple_condition)
        return None

    @classmethod
    def _is_check_call(cls, node: ast.Call) -> bool:
        return isinstance(node.func, ast.Name) and node.func.id in CHECK_NAMES

    @staticmethod
    def _check_call_condition(node: ast.Call) -> ast.AST | None:
        if len(node.args) >= 2:
            return node.args[1]
        for keyword in node.keywords:
            if keyword.arg in CHECK_CONDITION_KEYWORDS:
                return keyword.value
        return None

    @classmethod
    def _is_truthy_literal(cls, node: ast.AST) -> bool:
        return cls._literal_truth_value(node) is True

    @classmethod
    def _literal_truth_value(cls, node: ast.AST) -> bool | None:
        if isinstance(node, ast.Constant):
            return bool(node.value)
        if isinstance(node, (ast.Tuple, ast.List, ast.Set)):
            return bool(node.elts)
        if isinstance(node, ast.Dict):
            return bool(node.keys)
        signed_numeric = cls._signed_numeric_literal_value(node)
        if signed_numeric is not None:
            return bool(signed_numeric)
        return None

    @staticmethod
    def _signed_numeric_literal_value(node: ast.AST) -> int | float | complex | None:
        if not isinstance(node, ast.UnaryOp) or not isinstance(node.op, (ast.UAdd, ast.USub)):
            return None
        if not isinstance(node.operand, ast.Constant):
            return None
        value = node.operand.value
        if isinstance(value, (int, float, complex)) and not isinstance(value, bool):
            return value
        return None

    @classmethod
    def _tuple_append_condition(cls, node: ast.Call) -> ast.AST | None:
        if not isinstance(node.func, ast.Attribute) or node.func.attr != "append":
            return None
        if not isinstance(node.func.value, ast.Name) or node.func.value.id != "checks":
            return None
        if not node.args or not isinstance(node.args[0], ast.Tuple) or len(node.args[0].elts) < 2:
            return None
        label = node.args[0].elts[0]
        if not isinstance(label, ast.Constant) or not isinstance(label.value, str):
            return None
        return node.args[0].elts[1]

    @classmethod
    def _check_expressions_in_body(cls, body: list[ast.stmt]) -> list[CheckExpression]:
        checks: list[CheckExpression] = []
        for stmt in body:
            for node in ast.walk(stmt):
                if isinstance(node, ast.Call):
                    check = cls._as_check_expression(node)
                    if check is not None:
                        checks.append(check)
        return checks

    @classmethod
    def _asserts_expected_exception_text(cls, node: ast.AST, exception_name: str) -> bool:
        if isinstance(node, ast.BoolOp):
            if isinstance(node.op, ast.And):
                return any(cls._asserts_expected_exception_text(value, exception_name) for value in node.values)
            if isinstance(node.op, ast.Or):
                return all(cls._asserts_expected_exception_text(value, exception_name) for value in node.values)
            return False
        if isinstance(node, ast.Compare):
            return cls._compare_asserts_expected_exception_text(node, exception_name)
        if isinstance(node, ast.Call):
            if cls._method_asserts_expected_exception_text(node, exception_name):
                return True
            if isinstance(node.func, ast.Name) and node.func.id == "bool" and len(node.args) == 1:
                return cls._asserts_expected_exception_text(node.args[0], exception_name)
        if isinstance(node, ast.IfExp):
            return cls._asserts_expected_exception_text(node.body, exception_name) and cls._asserts_expected_exception_text(node.orelse, exception_name)
        return False

    @classmethod
    def _compare_asserts_expected_exception_text(cls, node: ast.Compare, exception_name: str) -> bool:
        left = node.left
        for op, right in zip(node.ops, node.comparators):
            if isinstance(op, (ast.In, ast.Eq)):
                if cls._is_nonempty_string_literal(left) and cls._contains_exception_text_call(right, exception_name):
                    return True
                if cls._contains_exception_text_call(left, exception_name) and cls._is_nonempty_string_literal(right):
                    return True
            left = right
        return False

    @classmethod
    def _method_asserts_expected_exception_text(cls, node: ast.Call, exception_name: str) -> bool:
        if not isinstance(node.func, ast.Attribute) or node.func.attr not in EXPECTED_TEXT_BOOLEAN_METHODS:
            return False
        if not cls._contains_exception_text_call(node.func.value, exception_name):
            return False
        return any(cls._is_nonempty_string_literal(arg) for arg in node.args)

    @staticmethod
    def _is_nonempty_string_literal(node: ast.AST) -> bool:
        return isinstance(node, ast.Constant) and isinstance(node.value, str) and bool(node.value.strip())

    @staticmethod
    def _contains_exception_text_call(node: ast.AST, exception_name: str) -> bool:
        for subnode in ast.walk(node):
            if not isinstance(subnode, ast.Call):
                continue
            if not isinstance(subnode.func, ast.Name) or subnode.func.id not in {"str", "repr"}:
                continue
            if subnode.args and isinstance(subnode.args[0], ast.Name) and subnode.args[0].id == exception_name:
                return True
        return False


def resolve_paths(paths: list[str] | None) -> list[Path]:
    raw_paths = paths or list(DEFAULT_TARGETS)
    return [(REPO / p).resolve() if not Path(p).is_absolute() else Path(p).resolve() for p in raw_paths]


def collect_issues(paths: list[Path]) -> list[Issue]:
    issues: list[Issue] = []
    for path in paths:
        if not path.exists():
            issues.append(Issue(path, 0, 0, "missing_target", "target evaluator script does not exist"))
            continue
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except SyntaxError as exc:
            issues.append(Issue(path, exc.lineno or 0, exc.offset or 0, "syntax_error", exc.msg))
            continue
        visitor = SelfTestQualityVisitor(path)
        visitor.visit(tree)
        if visitor.selftest_function_count == 0:
            issues.append(Issue(path, 0, 0, "missing_selftest_entrypoint", "target evaluator script has no run_self_test(s) entrypoint"))
        elif visitor.selftest_check_count == 0:
            issues.append(Issue(path, 0, 0, "missing_selftest_checks", "target evaluator script has no recognized check expressions inside run_self_test(s)"))
        issues.extend(visitor.issues)
    return issues


def run_self_test() -> list[str]:
    failures: list[str] = []

    def issue_count(source: str) -> int:
        tree = ast.parse(source)
        visitor = SelfTestQualityVisitor(REPO / "selftest.py")
        visitor.visit(tree)
        return len(visitor.issues)

    def target_issue_codes(source: str) -> list[str]:
        tree = ast.parse(source)
        visitor = SelfTestQualityVisitor(REPO / "selftest.py")
        visitor.visit(tree)
        codes = [issue.code for issue in visitor.issues]
        if visitor.selftest_function_count == 0:
            codes.append("missing_selftest_entrypoint")
        elif visitor.selftest_check_count == 0:
            codes.append("missing_selftest_checks")
        return codes

    cases = [
        ("direct_check_literal_true", "def f():\n    check('bad', True)\n", 1),
        ("direct__check_literal_true", "def f():\n    _check('bad', True)\n", 1),
        ("direct_check_numeric_truthy_rejected", "def f():\n    check('bad', 1)\n", 1),
        ("direct_check_signed_numeric_truthy_rejected", "def f():\n    check('bad', -1)\n", 1),
        ("direct_check_string_truthy_rejected", "def f():\n    check('bad', 'passed')\n", 1),
        ("direct_check_bytes_truthy_rejected", "def f():\n    check('bad', b'passed')\n", 1),
        ("direct_check_tuple_truthy_rejected", "def f():\n    check('bad', ('passed',))\n", 1),
        ("direct_check_dict_truthy_rejected", "def f():\n    check('bad', {'passed': True})\n", 1),
        ("direct_check_literal_false_allowed", "def f():\n    check('ok', False)\n", 0),
        ("direct_check_zero_allowed", "def f():\n    check('ok', 0)\n", 0),
        ("direct_check_empty_string_allowed", "def f():\n    check('ok', '')\n", 0),
        ("direct_check_empty_tuple_allowed", "def f():\n    check('ok', ())\n", 0),
        ("keyword_ok_truthy_rejected", "def f():\n    check('bad', ok=True)\n", 1),
        ("keyword_condition_truthy_rejected", "def f():\n    check('bad', condition='passed')\n", 1),
        ("keyword_condition_real_allowed", "def f(value):\n    check('ok', condition=value is True)\n", 0),
        ("keyword_false_allowed", "def f():\n    check('ok', ok=False)\n", 0),
        ("missing_condition_rejected", "def f():\n    check('bad')\n", 1),
        ("unrecognized_keyword_condition_rejected", "def f():\n    check('bad', passed=True)\n", 1),
        ("nested_append_literal_true", "def f():\n    checks.append(_check('bad', True))\n", 1),
        ("tuple_append_literal_true", "def f():\n    checks.append(('bad', True))\n", 1),
        ("tuple_append_truthy_literal_rejected", "def f():\n    checks.append(('bad', 'passed'))\n", 1),
        ("real_condition_allowed", "def f(value):\n    check('ok', value is True)\n", 0),
        ("tuple_append_real_condition_allowed", "def f(value):\n    checks.append(('ok', value is True))\n", 0),
        ("non_check_call_allowed", "def f():\n    other('ok', True)\n", 0),
        (
            "exception_text_check_allowed",
            "def f():\n    try:\n        raise Error('needle')\n    except Error as exc:\n        check('ok', 'needle' in str(exc))\n",
            0,
        ),
        (
            "exception_tuple_text_check_allowed",
            "def f():\n    try:\n        raise Error('needle')\n    except Error as exc:\n        checks.append(('ok', 'needle' in str(exc)))\n",
            0,
        ),
        (
            "exception_repr_check_allowed",
            "def f():\n    try:\n        raise Error('needle')\n    except Error as exc:\n        check('ok', 'needle' in repr(exc))\n",
            0,
        ),
        (
            "exception_method_text_check_allowed",
            "def f():\n    try:\n        raise Error('needle')\n    except Error as exc:\n        check('ok', str(exc).startswith('needle'))\n",
            0,
        ),
        (
            "exception_or_text_check_allowed",
            "def f():\n    try:\n        raise Error('needle')\n    except Error as exc:\n        check('ok', 'needle' in str(exc) or 'pin' in str(exc))\n",
            0,
        ),
        (
            "exception_and_text_check_allowed",
            "def f(value):\n    try:\n        raise Error('needle')\n    except Error as exc:\n        check('ok', value and 'needle' in str(exc))\n",
            0,
        ),
        (
            "exception_bool_wrapped_text_check_allowed",
            "def f():\n    try:\n        raise Error('needle')\n    except Error as exc:\n        check('ok', bool('needle' in str(exc)))\n",
            0,
        ),
        (
            "exception_check_without_text_rejected",
            "def f(value):\n    try:\n        raise Error('needle')\n    except Error as exc:\n        check('bad', value)\n",
            1,
        ),
        (
            "exception_tuple_check_without_text_rejected",
            "def f(value):\n    try:\n        raise Error('needle')\n    except Error as exc:\n        checks.append(('bad', value))\n",
            1,
        ),
        (
            "exception_type_check_without_text_rejected",
            "def f():\n    try:\n        raise Error('needle')\n    except Error as exc:\n        check('bad', isinstance(exc, Error))\n",
            1,
        ),
        (
            "exception_bool_text_without_expected_text_rejected",
            "def f():\n    try:\n        raise Error('needle')\n    except Error as exc:\n        check('bad', bool(str(exc)))\n",
            1,
        ),
        (
            "exception_empty_text_compare_rejected",
            "def f():\n    try:\n        raise Error('needle')\n    except Error as exc:\n        check('bad', str(exc) != '')\n",
            1,
        ),
        (
            "exception_negative_text_compare_rejected",
            "def f():\n    try:\n        raise Error('needle')\n    except Error as exc:\n        check('bad', 'needle' not in str(exc))\n",
            1,
        ),
        (
            "exception_nonempty_not_equal_rejected",
            "def f():\n    try:\n        raise Error('needle')\n    except Error as exc:\n        check('bad', str(exc) != 'needle')\n",
            1,
        ),
        (
            "exception_unrelated_literal_and_text_rejected",
            "def f():\n    try:\n        raise Error('needle')\n    except Error as exc:\n        check('bad', 'needle' and str(exc))\n",
            1,
        ),
        (
            "exception_text_or_true_rejected",
            "def f():\n    try:\n        raise Error('needle')\n    except Error as exc:\n        check('bad', 'needle' in str(exc) or True)\n",
            1,
        ),
        (
            "exception_text_or_vacuous_text_rejected",
            "def f():\n    try:\n        raise Error('needle')\n    except Error as exc:\n        check('bad', 'needle' in str(exc) or bool(str(exc)))\n",
            1,
        ),
        (
            "exception_bare_find_rejected",
            "def f():\n    try:\n        raise Error('needle')\n    except Error as exc:\n        check('bad', str(exc).find('needle'))\n",
            1,
        ),
        (
            "exception_bare_index_rejected",
            "def f():\n    try:\n        raise Error('needle')\n    except Error as exc:\n        check('bad', str(exc).index('needle'))\n",
            1,
        ),
        (
            "exception_bare_count_rejected",
            "def f():\n    try:\n        raise Error('needle')\n    except Error as exc:\n        check('bad', str(exc).count('needle'))\n",
            1,
        ),
        (
            "unbound_exception_check_rejected",
            "def f():\n    try:\n        raise Error('needle')\n    except Error:\n        check('bad', False)\n",
            1,
        ),
    ]
    for name, source, expected in cases:
        actual = issue_count(source)
        if actual != expected:
            failures.append(f"{name}: expected {expected}, got {actual}")

    target_cases = [
        ("target_without_selftest_entrypoint_rejected", "def helper(value):\n    check('ok', value is True)\n", ["missing_selftest_entrypoint"]),
        ("target_without_checks_rejected", "def run_self_tests():\n    other('ok', True)\n", ["missing_selftest_checks"]),
        (
            "target_with_helper_check_but_empty_selftest_rejected",
            "def helper(value):\n    check('ok', value is True)\n\ndef run_self_tests():\n    pass\n",
            ["missing_selftest_checks"],
        ),
        (
            "target_with_wrong_tuple_receiver_rejected",
            "def run_self_tests(value):\n    not_checks.append(('ok', value is True))\n",
            ["missing_selftest_checks"],
        ),
        (
            "target_with_malformed_check_rejected",
            "def run_self_tests():\n    check('bad')\n",
            ["missing_check_condition", "missing_selftest_checks"],
        ),
        (
            "target_with_nested_helper_only_rejected",
            "def run_self_tests():\n    def helper(value):\n        check('ok', value is True)\n",
            ["missing_selftest_checks"],
        ),
        (
            "target_with_lambda_only_rejected",
            "def run_self_tests():\n    helper = lambda value: check('ok', value is True)\n",
            ["missing_selftest_checks"],
        ),
        (
            "target_with_nested_class_only_rejected",
            "def run_self_tests():\n    class Helper:\n        def check_value(self, value):\n            check('ok', value is True)\n",
            ["missing_selftest_checks"],
        ),
        (
            "target_with_if_false_only_rejected",
            "def run_self_tests():\n    if False:\n        check('ok', value is True)\n",
            ["missing_selftest_checks"],
        ),
        (
            "target_with_after_return_only_rejected",
            "def run_self_tests():\n    return\n    check('ok', value is True)\n",
            ["missing_selftest_checks"],
        ),
        (
            "target_with_if_true_return_then_check_rejected",
            "def run_self_tests():\n    if True:\n        return\n    check('ok', value is True)\n",
            ["missing_selftest_checks"],
        ),
        (
            "target_with_try_after_return_only_rejected",
            "def run_self_tests():\n    try:\n        return\n        check('ok', value is True)\n    finally:\n        pass\n",
            ["missing_selftest_checks"],
        ),
        (
            "target_with_with_after_return_only_rejected",
            "def run_self_tests(lock):\n    with lock:\n        return\n        check('ok', value is True)\n",
            ["missing_selftest_checks"],
        ),
        (
            "target_with_suppressible_raise_then_check_allowed",
            "def run_self_tests(value, guard):\n    with guard:\n        raise Error('maybe suppressed')\n    check('ok', value is True)\n",
            [],
        ),
        (
            "target_with_except_after_return_only_rejected",
            "def run_self_tests():\n    try:\n        raise Error('needle')\n    except Error as exc:\n        return\n        check('ok', 'needle' in str(exc))\n",
            ["missing_selftest_checks"],
        ),
        (
            "target_with_while_false_only_rejected",
            "def run_self_tests():\n    while False:\n        check('ok', value is True)\n",
            ["missing_selftest_checks"],
        ),
        (
            "target_with_while_true_return_then_check_rejected",
            "def run_self_tests():\n    while True:\n        return\n    check('ok', value is True)\n",
            ["missing_selftest_checks"],
        ),
        (
            "target_with_empty_for_only_rejected",
            "def run_self_tests():\n    for value in []:\n        check('ok', value is True)\n",
            ["missing_selftest_checks"],
        ),
        (
            "target_with_nonempty_for_return_then_check_rejected",
            "def run_self_tests():\n    for value in [1]:\n        return\n    check('ok', value is True)\n",
            ["missing_selftest_checks"],
        ),
        (
            "target_with_try_return_then_check_rejected",
            "def run_self_tests():\n    try:\n        return\n    finally:\n        pass\n    check('ok', value is True)\n",
            ["missing_selftest_checks"],
        ),
        (
            "target_with_try_handler_then_check_allowed",
            "def run_self_tests(value):\n    try:\n        return risky()\n    except Error:\n        pass\n    check('ok', value is True)\n",
            [],
        ),
        (
            "target_with_if_true_check_allowed",
            "def run_self_tests(value):\n    if True:\n        check('ok', value is True)\n",
            [],
        ),
        (
            "target_with_if_false_else_check_allowed",
            "def run_self_tests(value):\n    if False:\n        other('bad', True)\n    else:\n        check('ok', value is True)\n",
            [],
        ),
        (
            "target_with_empty_for_else_check_allowed",
            "def run_self_tests(value):\n    for item in []:\n        other('bad', True)\n    else:\n        check('ok', value is True)\n",
            [],
        ),
        (
            "target_with_while_true_break_then_check_allowed",
            "def run_self_tests(value):\n    while True:\n        break\n    check('ok', value is True)\n",
            [],
        ),
        ("target_with_tuple_check_allowed", "def run_self_tests(value):\n    checks.append(('ok', value is True))\n", []),
    ]
    for name, source, expected in target_cases:
        actual = target_issue_codes(source)
        if actual != expected:
            failures.append(f"{name}: expected {expected}, got {actual}")

    return failures


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="*", help="optional repo-relative or absolute Python files to scan")
    parser.add_argument("--self-test", action="store_true", help="run synthetic validator self-test")
    args = parser.parse_args(argv)

    if args.self_test:
        failures = run_self_test()
        if failures:
            print("Self-test FAILED:")
            for failure in failures:
                print(f"  - {failure}")
            return 1
        print("Self-test passed: self-test quality detector covers helper-call, keyword-condition, checks.append tuple-append, truthy-literal, expected exception-text, self-test entrypoint, deferred-scope, unreachable-body, and missing-check cases")
        return 0

    targets = resolve_paths(args.paths)
    issues = collect_issues(targets)
    if issues:
        print("Validation FAILED:")
        for issue in issues:
            print(f"  - {issue.format()}")
        return 1
    print("Validation passed:")
    print(f"  scanned files: {len(targets)}")
    print("  recognized helper-call, keyword-condition, and checks.append tuple-append checks inside run_self_test(s) in every target")
    print("  no malformed self-test check calls")
    print("  no truthy literal self-test check conditions")
    print("  exception-handler checks compare expected error text")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
