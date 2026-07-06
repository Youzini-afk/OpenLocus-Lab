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
SELF_TEST_FUNCTION_NAMES = {"run_self_test", "run_self_tests"}


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

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        if node.name in SELF_TEST_FUNCTION_NAMES:
            self.selftest_function_count += 1
        self._function_stack.append(node.name)
        self.generic_visit(node)
        self._function_stack.pop()

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        if node.name in SELF_TEST_FUNCTION_NAMES:
            self.selftest_function_count += 1
        self._function_stack.append(node.name)
        self.generic_visit(node)
        self._function_stack.pop()

    def visit_Call(self, node: ast.Call) -> None:
        check = self._as_check_expression(node)
        if check is not None:
            self.check_count += 1
            if self._inside_selftest_function():
                self.selftest_check_count += 1
        if check is not None and self._is_literal_true(check.condition):
            self.issues.append(
                Issue(
                    self.path,
                    node.lineno,
                    node.col_offset,
                    "literal_true_check",
                    "self-test check uses literal True as its condition",
                )
            )
        self.generic_visit(node)

    def _inside_selftest_function(self) -> bool:
        return any(name in SELF_TEST_FUNCTION_NAMES for name in self._function_stack)

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
            if not self._uses_exception_text(check.condition, node.name):
                self.issues.append(
                    Issue(
                        self.path,
                        check.call.lineno,
                        check.call.col_offset,
                        "exception_check_without_error_text",
                        "self-test exception handler check must assert expected error text with str(exc) or repr(exc)",
                    )
                )
        self.generic_visit(node)

    @classmethod
    def _as_check_expression(cls, node: ast.Call) -> CheckExpression | None:
        if cls._is_check_call(node):
            if len(node.args) < 2:
                return CheckExpression(node, ast.Constant(False))
            return CheckExpression(node, node.args[1])
        tuple_condition = cls._tuple_append_condition(node)
        if tuple_condition is not None:
            return CheckExpression(node, tuple_condition)
        return None

    @classmethod
    def _is_check_call(cls, node: ast.Call) -> bool:
        return isinstance(node.func, ast.Name) and node.func.id in CHECK_NAMES

    @staticmethod
    def _is_literal_true(node: ast.AST) -> bool:
        return isinstance(node, ast.Constant) and node.value is True

    @classmethod
    def _tuple_append_condition(cls, node: ast.Call) -> ast.AST | None:
        if not isinstance(node.func, ast.Attribute) or node.func.attr != "append":
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

    @staticmethod
    def _uses_exception_text(node: ast.AST, exception_name: str) -> bool:
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
        ("nested_append_literal_true", "def f():\n    checks.append(_check('bad', True))\n", 1),
        ("tuple_append_literal_true", "def f():\n    checks.append(('bad', True))\n", 1),
        ("real_condition_allowed", "def f(value):\n    check('ok', value is True)\n", 0),
        ("tuple_append_real_condition_allowed", "def f(value):\n    checks.append(('ok', value is True))\n", 0),
        ("non_check_call_allowed", "def f():\n    other('ok', True)\n", 0),
        ("keyword_literal_true_allowed", "def f():\n    check('ok', ok=True)\n", 0),
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
        print("Self-test passed: self-test quality detector covers helper-call, tuple-append, literal-true, exception-text, self-test entrypoint, and missing-check cases")
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
    print("  recognized helper-call and tuple-append checks inside run_self_test(s) in every target")
    print("  no literal True self-test check conditions")
    print("  exception-handler checks assert expected error text")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
