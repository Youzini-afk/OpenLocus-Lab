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
import builtins
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
GENERATOR_CONSUMING_CALL_NAMES = {"all", "any", "dict", "list", "max", "min", "next", "set", "sorted", "sum", "tuple"}
TRY_STATEMENT_TYPES = (ast.Try,) + ((ast.TryStar,) if hasattr(ast, "TryStar") else ())
MAX_STATIC_STRING_CHARS = 4096
MAX_STATIC_VALUE_ITEMS = 128
MAX_STATIC_INT_BITS = 1024


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
        self._class_scope_depth = 0
        self._future_annotations = False

    def visit_Module(self, node: ast.Module) -> None:
        self._future_annotations = self._module_has_future_annotations(node)
        self._visit_statements(node.body)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._visit_function_definition_expressions(node)
        if node.name in SELF_TEST_FUNCTION_NAMES:
            self.selftest_function_count += 1
        self._function_stack.append(node.name)
        body_is_deferred = node.name not in SELF_TEST_FUNCTION_NAMES or self._function_body_contains_yield(node.body)
        if body_is_deferred:
            self._deferred_scope_depth += 1
        saved_class_scope_depth = self._class_scope_depth
        self._class_scope_depth = 0
        self._visit_statements(node.body)
        self._class_scope_depth = saved_class_scope_depth
        if body_is_deferred:
            self._deferred_scope_depth -= 1
        self._function_stack.pop()

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._visit_function_definition_expressions(node)
        if node.name in SELF_TEST_FUNCTION_NAMES:
            self.selftest_function_count += 1
        self._function_stack.append(node.name)
        self._deferred_scope_depth += 1
        saved_class_scope_depth = self._class_scope_depth
        self._class_scope_depth = 0
        self._visit_statements(node.body)
        self._class_scope_depth = saved_class_scope_depth
        self._deferred_scope_depth -= 1
        self._function_stack.pop()

    def visit_Lambda(self, node: ast.Lambda) -> None:
        self._visit_arguments_defaults(node.args)
        self._deferred_scope_depth += 1
        self.visit(node.body)
        self._deferred_scope_depth -= 1

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        for decorator in node.decorator_list:
            self.visit(decorator)
        for base in node.bases:
            self.visit(base)
        for keyword in node.keywords:
            self.visit(keyword.value)
        self._class_scope_depth += 1
        self._visit_statements(node.body)
        self._class_scope_depth -= 1

    def _visit_function_definition_expressions(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        for decorator in node.decorator_list:
            self.visit(decorator)
        self._visit_arguments_defaults(node.args)
        self._visit_arguments_annotations(node.args)
        if node.returns is not None:
            self._visit_annotation(node.returns, evaluated=not self._future_annotations)

    def _visit_arguments_defaults(self, node: ast.arguments) -> None:
        for default in node.defaults:
            self.visit(default)
        for default in node.kw_defaults:
            if default is not None:
                self.visit(default)

    def _visit_arguments_annotations(self, node: ast.arguments) -> None:
        for arg in [*node.posonlyargs, *node.args, *node.kwonlyargs]:
            if arg.annotation is not None:
                self._visit_annotation(arg.annotation, evaluated=not self._future_annotations)
        if node.vararg is not None and node.vararg.annotation is not None:
            self._visit_annotation(node.vararg.annotation, evaluated=not self._future_annotations)
        if node.kwarg is not None and node.kwarg.annotation is not None:
            self._visit_annotation(node.kwarg.annotation, evaluated=not self._future_annotations)

    def visit_AnnAssign(self, node: ast.AnnAssign) -> None:
        if node.value is not None:
            self.visit(node.value)
            if self._expression_guarantees_raise(node.value):
                self._visit_unreachable(node.target)
                self._visit_unreachable(node.annotation)
                return
        self.visit(node.target)
        if self._assignment_store_target_guarantees_raise(node.target):
            self._visit_unreachable(node.annotation)
            return
        annotation_is_evaluated = not self._future_annotations and (not self._function_stack or self._class_scope_depth > 0)
        self._visit_annotation(node.annotation, evaluated=annotation_is_evaluated)

    def visit_Assign(self, node: ast.Assign) -> None:
        self.visit(node.value)
        if self._expression_guarantees_raise(node.value):
            for target in node.targets:
                self._visit_unreachable(target)
            return
        for target in node.targets:
            self.visit(target)

    def visit_AugAssign(self, node: ast.AugAssign) -> None:
        self.visit(node.target)
        if self._expression_guarantees_raise(node.target):
            self._visit_unreachable(node.value)
            return
        self.visit(node.value)

    def _visit_annotation(self, node: ast.AST, *, evaluated: bool) -> None:
        if evaluated:
            self.visit(node)
        else:
            self._visit_unreachable(node)

    @staticmethod
    def _module_has_future_annotations(node: ast.Module) -> bool:
        for statement in node.body:
            if not isinstance(statement, ast.ImportFrom) or statement.module != "__future__":
                continue
            if any(alias.name == "annotations" for alias in statement.names):
                return True
        return False

    @staticmethod
    def _function_body_contains_yield(statements: list[ast.stmt]) -> bool:
        class YieldFinder(ast.NodeVisitor):
            def __init__(self) -> None:
                self.found = False

            def visit_Yield(self, node: ast.Yield) -> None:
                self.found = True

            def visit_YieldFrom(self, node: ast.YieldFrom) -> None:
                self.found = True

            def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
                return

            def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
                return

            def visit_Lambda(self, node: ast.Lambda) -> None:
                return

            def visit_ClassDef(self, node: ast.ClassDef) -> None:
                return

        finder = YieldFinder()
        for statement in statements:
            finder.visit(statement)
            if finder.found:
                return True
        return False

    def visit_BoolOp(self, node: ast.BoolOp) -> None:
        if isinstance(node.op, ast.And):
            for index, value in enumerate(node.values):
                self.visit(value)
                if self._literal_truth_value(value) is False:
                    for later_value in node.values[index + 1 :]:
                        self._visit_unreachable(later_value)
                    return
            return
        if isinstance(node.op, ast.Or):
            for index, value in enumerate(node.values):
                self.visit(value)
                if self._literal_truth_value(value) is True:
                    for later_value in node.values[index + 1 :]:
                        self._visit_unreachable(later_value)
                    return
            return
        self.generic_visit(node)

    def visit_IfExp(self, node: ast.IfExp) -> None:
        self.visit(node.test)
        test_truth = self._literal_truth_value(node.test)
        if test_truth is True:
            self.visit(node.body)
            self._visit_unreachable(node.orelse)
            return
        if test_truth is False:
            self._visit_unreachable(node.body)
            self.visit(node.orelse)
            return
        self.visit(node.body)
        self.visit(node.orelse)

    def visit_Assert(self, node: ast.Assert) -> None:
        self.visit(node.test)
        if node.msg is None:
            return
        test_truth = self._literal_truth_value(node.test)
        if test_truth is True:
            self._visit_unreachable(node.msg)
            return
        self.visit(node.msg)

    def visit_Compare(self, node: ast.Compare) -> None:
        self.visit(node.left)
        known_left, left_value = self._static_comparison_value(node.left)
        comparison_still_reachable = True
        for op, comparator in zip(node.ops, node.comparators):
            if comparison_still_reachable:
                self.visit(comparator)
            else:
                self._visit_unreachable(comparator)
                continue
            known_right, right_value = self._static_comparison_value(comparator)
            if not known_left or not known_right:
                known_left = known_right
                left_value = right_value
                continue
            pair_truth = self._literal_compare_pair_truth_value(left_value, op, right_value)
            if pair_truth is False:
                comparison_still_reachable = False
            known_left = True
            left_value = right_value

    def visit_ListComp(self, node: ast.ListComp) -> None:
        self._visit_comprehension(node.generators, [node.elt])

    def visit_SetComp(self, node: ast.SetComp) -> None:
        self._visit_comprehension(node.generators, [node.elt])

    def visit_DictComp(self, node: ast.DictComp) -> None:
        self._visit_comprehension(node.generators, [node.key, node.value])

    def visit_GeneratorExp(self, node: ast.GeneratorExp) -> None:
        self._visit_lazy_generator_expression(node)

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
        test_truth = self._literal_truth_value(node.test)
        if test_truth is False:
            self._visit_unreachable_statements(node.body)
            self._visit_statements(node.orelse)
            return
        if test_truth is True:
            self._visit_statements(node.body)
            self._visit_unreachable_statements(node.orelse)
            return
        self._visit_statements(node.body)
        self._visit_statements(node.orelse)

    def visit_For(self, node: ast.For) -> None:
        self.visit(node.iter)
        iter_truth = self._literal_iter_truth_value(node.iter)
        if iter_truth is False:
            self._visit_unreachable(node.target)
            self._visit_unreachable_statements(node.body)
            self._visit_statements(node.orelse)
            return
        self.visit(node.target)
        if iter_truth is True:
            self._visit_statements(node.body)
            if self._block_guarantees_loop_else_skip(node.body):
                self._visit_unreachable_statements(node.orelse)
            else:
                self._visit_statements(node.orelse)
            return
        self._visit_statements(node.body)
        self._visit_statements(node.orelse)

    def visit_AsyncFor(self, node: ast.AsyncFor) -> None:
        self.visit(node.iter)
        iter_truth = self._literal_iter_truth_value(node.iter)
        if iter_truth is False:
            self._visit_unreachable(node.target)
            self._visit_unreachable_statements(node.body)
            self._visit_statements(node.orelse)
            return
        self.visit(node.target)
        if iter_truth is True:
            self._visit_statements(node.body)
            if self._block_guarantees_loop_else_skip(node.body):
                self._visit_unreachable_statements(node.orelse)
            else:
                self._visit_statements(node.orelse)
            return
        self._visit_statements(node.body)
        self._visit_statements(node.orelse)

    def visit_With(self, node: ast.With) -> None:
        if self._visit_with_items(node.items):
            self._visit_statements(node.body)
        else:
            self._visit_unreachable_statements(node.body)

    def visit_AsyncWith(self, node: ast.AsyncWith) -> None:
        if self._visit_with_items(node.items):
            self._visit_statements(node.body)
        else:
            self._visit_unreachable_statements(node.body)

    def visit_Try(self, node: ast.Try) -> None:
        self._visit_try_like(node)

    def visit_TryStar(self, node: ast.AST) -> None:
        self._visit_try_like(node)

    def _visit_try_like(self, node: ast.Try) -> None:
        self._visit_statements(node.body)
        body_cannot_raise = self._block_cannot_raise(node.body)
        guaranteed_raise = self._block_guaranteed_raise_exception(node.body)
        known_raise_caught = False
        unknown_handler_before = False
        for handler in node.handlers:
            if body_cannot_raise:
                self._visit_unreachable(handler)
            elif known_raise_caught:
                self._visit_unreachable(handler)
            elif guaranteed_raise is not None and not unknown_handler_before:
                match = self._handler_matches_exception(handler.type, guaranteed_raise)
                if match is False:
                    self._visit_unreachable(handler)
                else:
                    self.visit(handler)
                    if match is True:
                        known_raise_caught = True
                    else:
                        unknown_handler_before = True
            else:
                self.visit(handler)
        if self._block_guarantees_exit(node.body):
            self._visit_unreachable_statements(node.orelse)
        else:
            self._visit_statements(node.orelse)
        self._visit_statements(node.finalbody)

    def visit_Match(self, node: ast.Match) -> None:
        self.visit(node.subject)
        known, subject_value = self._static_match_subject_value(node.subject)
        if not known:
            for case in node.cases:
                self._visit_match_case(case)
            return

        selected = False
        for index, case in enumerate(node.cases):
            if selected:
                self._visit_unreachable_match_case(case)
                continue
            pattern_match = self._match_pattern_matches_literal(subject_value, case.pattern)
            if pattern_match is False:
                self._visit_unreachable_match_case(case)
                continue
            if pattern_match is None:
                self._visit_match_case(case)
                for later_case in node.cases[index + 1 :]:
                    self._visit_match_case(later_case)
                return
            guard_truth = True if case.guard is None else self._literal_truth_value(case.guard)
            if guard_truth is False:
                self._visit_match_case_guard(case)
                self._visit_unreachable_statements(case.body)
                continue
            self._visit_match_case(case)
            if guard_truth is True:
                selected = True

    def _visit_match_case(self, case: ast.match_case) -> None:
        self._visit_match_case_guard(case)
        self._visit_statements(case.body)

    def _visit_unreachable_match_case(self, case: ast.match_case) -> None:
        if case.guard is not None:
            self._visit_unreachable(case.guard)
        self._visit_unreachable_statements(case.body)

    def _visit_match_case_guard(self, case: ast.match_case) -> None:
        if case.guard is not None:
            self.visit(case.guard)

    def _visit_with_items(self, items: list[ast.withitem]) -> bool:
        body_is_reachable = True
        for item in items:
            if not body_is_reachable:
                self._visit_unreachable(item.context_expr)
                if item.optional_vars is not None:
                    self._visit_unreachable(item.optional_vars)
                continue
            self.visit(item.context_expr)
            if self._expression_guarantees_raise(item.context_expr):
                if item.optional_vars is not None:
                    self._visit_unreachable(item.optional_vars)
                body_is_reachable = False
                continue
            if item.optional_vars is not None:
                self.visit(item.optional_vars)
                if self._assignment_store_target_guarantees_raise(item.optional_vars):
                    body_is_reachable = False
        return body_is_reachable

    @classmethod
    def _with_context_expression_guarantees_raise(cls, node: ast.With | ast.AsyncWith) -> bool:
        if not node.items:
            return False
        return cls._expression_guarantees_raise(node.items[0].context_expr)

    def _visit_comprehension(self, generators: list[ast.comprehension], result_nodes: list[ast.AST]) -> None:
        can_yield = True
        for generator in generators:
            if not can_yield:
                self._visit_unreachable(generator.target)
                self._visit_unreachable(generator.iter)
                for if_clause in generator.ifs:
                    self._visit_unreachable(if_clause)
                continue

            self.visit(generator.iter)
            if self._literal_iter_truth_value(generator.iter) is False:
                can_yield = False
                self._visit_unreachable(generator.target)
                for if_clause in generator.ifs:
                    self._visit_unreachable(if_clause)
                continue
            self.visit(generator.target)

            for if_clause in generator.ifs:
                if not can_yield:
                    self._visit_unreachable(if_clause)
                    continue
                self.visit(if_clause)
                if self._literal_truth_value(if_clause) is False:
                    can_yield = False

        for result_node in result_nodes:
            if can_yield:
                self.visit(result_node)
            else:
                self._visit_unreachable(result_node)

    def _visit_lazy_generator_expression(self, node: ast.GeneratorExp) -> None:
        if not node.generators:
            self._visit_unreachable(node.elt)
            return
        first_generator = node.generators[0]
        self.visit(first_generator.iter)
        self._visit_unreachable(first_generator.target)
        for if_clause in first_generator.ifs:
            self._visit_unreachable(if_clause)
        for generator in node.generators[1:]:
            self._visit_unreachable(generator.target)
            self._visit_unreachable(generator.iter)
            for if_clause in generator.ifs:
                self._visit_unreachable(if_clause)
        self._visit_unreachable(node.elt)

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
        if isinstance(node, ast.Assert):
            return cls._literal_truth_value(node.test) is False
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
            return cls._while_statement_guarantees_exit(node)
        if isinstance(node, (ast.For, ast.AsyncFor)):
            return cls._for_statement_guarantees_exit(node)
        if isinstance(node, (ast.With, ast.AsyncWith)):
            if cls._with_context_expression_guarantees_raise(node):
                return True
            return cls._block_guarantees_nonsuppressible_exit(node.body)
        if isinstance(node, TRY_STATEMENT_TYPES):
            if cls._block_guarantees_exit(node.finalbody):
                return True
            guaranteed_raise = cls._block_guaranteed_raise_exception(node.body)
            if guaranteed_raise is not None:
                handler_resolution, handler_body = cls._known_exception_handler_resolution(node.handlers, guaranteed_raise)
                if handler_resolution == "uncaught":
                    return True
                if handler_resolution == "caught":
                    return cls._block_guarantees_exit(handler_body or [])
            normal_path_exits = cls._block_guarantees_exit(node.body) or (bool(node.orelse) and cls._block_guarantees_exit(node.orelse))
            if cls._block_cannot_raise(node.body):
                return normal_path_exits
            if not node.handlers:
                return normal_path_exits
            return normal_path_exits and all(cls._block_guarantees_exit(handler.body) for handler in node.handlers)
        if isinstance(node, ast.Match):
            return cls._match_statement_guarantees(
                node, cls._block_guarantees_exit, guard_exception_counts=True
            )
        return False

    @classmethod
    def _block_guarantees_exit(cls, statements: list[ast.stmt]) -> bool:
        return any(cls._statement_guarantees_exit(statement) for statement in statements)

    @classmethod
    def _while_statement_guarantees_exit(cls, node: ast.While) -> bool:
        test_truth = cls._literal_truth_value(node.test)
        if test_truth is True:
            return not cls._block_may_reach_loop_break(node.body)
        if test_truth is False:
            return cls._block_guarantees_exit(node.orelse)
        return not cls._block_may_reach_loop_break(node.body) and cls._block_guarantees_exit(node.orelse)

    @classmethod
    def _for_statement_guarantees_exit(cls, node: ast.For | ast.AsyncFor) -> bool:
        iter_truth = cls._literal_iter_truth_value(node.iter)
        body_guarantees_function_exit = cls._block_guarantees_function_exit(node.body)
        body_may_break = cls._block_may_reach_loop_break(node.body)
        orelse_guarantees_exit = cls._block_guarantees_exit(node.orelse)
        if iter_truth is False:
            return orelse_guarantees_exit
        if iter_truth is True:
            return body_guarantees_function_exit or (not body_may_break and orelse_guarantees_exit)
        return not body_may_break and orelse_guarantees_exit

    @classmethod
    def _block_cannot_raise(cls, statements: list[ast.stmt]) -> bool:
        for statement in statements:
            if not cls._statement_cannot_raise(statement):
                return False
            if cls._statement_guarantees_exit(statement):
                return True
        return True

    @classmethod
    def _statement_cannot_raise(cls, node: ast.stmt) -> bool:
        if isinstance(node, (ast.Pass, ast.Break, ast.Continue)):
            return True
        if isinstance(node, (ast.Global, ast.Nonlocal)):
            return True
        if isinstance(node, ast.Return):
            return node.value is None or cls._expression_cannot_raise(node.value)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            return cls._function_definition_statement_cannot_raise(node)
        if isinstance(node, ast.ClassDef):
            return cls._class_definition_statement_cannot_raise(node)
        if isinstance(node, ast.Expr):
            return cls._expression_cannot_raise(node.value)
        if isinstance(node, ast.Assign):
            return cls._expression_cannot_raise(node.value) and all(
                cls._assignment_statement_target_cannot_raise(target, node.value) for target in node.targets
            )
        if isinstance(node, ast.AnnAssign):
            return cls._annassign_statement_cannot_raise(node)
        if isinstance(node, ast.Assert):
            return cls._expression_cannot_raise(node.test) and cls._literal_truth_value(node.test) is True
        if isinstance(node, ast.If):
            if not cls._expression_cannot_raise(node.test):
                return False
            test_truth = cls._literal_truth_value(node.test)
            if test_truth is True:
                return cls._block_cannot_raise(node.body)
            if test_truth is False:
                return cls._block_cannot_raise(node.orelse)
            return cls._block_cannot_raise(node.body) and cls._block_cannot_raise(node.orelse)
        if isinstance(node, ast.While):
            return cls._while_statement_cannot_raise(node)
        if isinstance(node, ast.For):
            return cls._for_statement_cannot_raise(node)
        if isinstance(node, ast.Match):
            return cls._match_statement_cannot_raise(node)
        if isinstance(node, TRY_STATEMENT_TYPES):
            guaranteed_raise = cls._block_guaranteed_raise_exception(node.body)
            if guaranteed_raise is not None:
                handler_resolution, handler_body = cls._known_exception_handler_resolution(node.handlers, guaranteed_raise)
                if handler_resolution == "caught":
                    return cls._block_cannot_raise(handler_body or []) and cls._block_cannot_raise(node.finalbody)
                if handler_resolution == "uncaught":
                    return False
            if not cls._block_cannot_raise(node.body):
                return False
            return cls._block_cannot_raise(node.orelse) and cls._block_cannot_raise(node.finalbody)
        return False

    @classmethod
    def _while_statement_cannot_raise(cls, node: ast.While) -> bool:
        if not cls._expression_cannot_raise(node.test):
            return False
        test_truth = cls._literal_truth_value(node.test)
        if test_truth is False:
            return cls._block_cannot_raise(node.orelse)
        if test_truth is True:
            return cls._block_cannot_raise(node.body)
        return False

    @classmethod
    def _for_statement_cannot_raise(cls, node: ast.For) -> bool:
        iter_cannot_raise, iter_truth = cls._iter_expression_cannot_raise_and_truth(node.iter)
        if not iter_cannot_raise:
            return False
        if iter_truth is False:
            return cls._block_cannot_raise(node.orelse)
        if iter_truth is not True or not isinstance(node.target, ast.Name):
            return False
        if not cls._block_cannot_raise(node.body):
            return False
        if cls._block_guarantees_loop_else_skip(node.body):
            return True
        return cls._block_cannot_raise(node.orelse)

    @classmethod
    def _match_statement_cannot_raise(cls, node: ast.Match) -> bool:
        if not cls._expression_cannot_raise(node.subject):
            return False
        known, subject_value = cls._static_match_subject_value(node.subject)
        if not known:
            return False
        for case in node.cases:
            pattern_match = cls._match_pattern_matches_literal(subject_value, case.pattern)
            if pattern_match is False:
                continue
            if pattern_match is None:
                return False
            if case.guard is not None:
                if not cls._expression_cannot_raise(case.guard):
                    return False
                guard_truth = cls._literal_truth_value(case.guard)
                if guard_truth is False:
                    continue
                if guard_truth is not True:
                    return False
            return cls._block_cannot_raise(case.body)
        return True

    @classmethod
    def _class_definition_statement_cannot_raise(cls, node: ast.ClassDef) -> bool:
        if node.decorator_list or node.bases or node.keywords:
            return False
        return cls._class_block_cannot_raise(node.body)

    @classmethod
    def _class_block_cannot_raise(cls, statements: list[ast.stmt]) -> bool:
        return all(cls._class_statement_cannot_raise(statement) for statement in statements)

    @classmethod
    def _class_statement_cannot_raise(cls, node: ast.stmt) -> bool:
        if isinstance(node, ast.Pass):
            return True
        if isinstance(node, ast.Expr):
            return cls._expression_cannot_raise(node.value)
        if isinstance(node, ast.Assign):
            return cls._expression_cannot_raise(node.value) and all(
                cls._assignment_statement_target_cannot_raise(target, node.value) for target in node.targets
            )
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            return cls._function_definition_statement_cannot_raise(node)
        if isinstance(node, ast.ClassDef):
            return cls._class_definition_statement_cannot_raise(node)
        if isinstance(node, ast.If):
            if not cls._expression_cannot_raise(node.test):
                return False
            test_truth = cls._literal_truth_value(node.test)
            if test_truth is True:
                return cls._class_block_cannot_raise(node.body)
            if test_truth is False:
                return cls._class_block_cannot_raise(node.orelse)
            return cls._class_block_cannot_raise(node.body) and cls._class_block_cannot_raise(node.orelse)
        if isinstance(node, ast.While):
            return cls._class_while_statement_cannot_raise(node)
        if isinstance(node, ast.For):
            return cls._class_for_statement_cannot_raise(node)
        if isinstance(node, ast.Match):
            return cls._class_match_statement_cannot_raise(node)
        if isinstance(node, TRY_STATEMENT_TYPES):
            return cls._class_try_statement_cannot_raise(node)
        return False

    @classmethod
    def _class_while_statement_cannot_raise(cls, node: ast.While) -> bool:
        if not cls._expression_cannot_raise(node.test):
            return False
        test_truth = cls._literal_truth_value(node.test)
        if test_truth is False:
            return cls._class_block_cannot_raise(node.orelse)
        if test_truth is True:
            return cls._class_block_cannot_raise(node.body)
        return False

    @classmethod
    def _class_for_statement_cannot_raise(cls, node: ast.For) -> bool:
        iter_cannot_raise, iter_truth = cls._iter_expression_cannot_raise_and_truth(node.iter)
        if not iter_cannot_raise:
            return False
        if iter_truth is False:
            return cls._class_block_cannot_raise(node.orelse)
        if iter_truth is not True or not isinstance(node.target, ast.Name):
            return False
        if not cls._class_block_cannot_raise(node.body):
            return False
        if cls._block_guarantees_loop_else_skip(node.body):
            return True
        return cls._class_block_cannot_raise(node.orelse)

    @classmethod
    def _class_match_statement_cannot_raise(cls, node: ast.Match) -> bool:
        if not cls._expression_cannot_raise(node.subject):
            return False
        known, subject_value = cls._static_match_subject_value(node.subject)
        if not known:
            return False
        for case in node.cases:
            pattern_match = cls._match_pattern_matches_literal(subject_value, case.pattern)
            if pattern_match is False:
                continue
            if pattern_match is None:
                return False
            if case.guard is not None:
                if not cls._expression_cannot_raise(case.guard):
                    return False
                guard_truth = cls._literal_truth_value(case.guard)
                if guard_truth is False:
                    continue
                if guard_truth is not True:
                    return False
            return cls._class_block_cannot_raise(case.body)
        return True

    @classmethod
    def _class_try_statement_cannot_raise(cls, node: ast.Try) -> bool:
        guaranteed_raise = cls._class_block_guaranteed_raise_exception(node.body)
        if guaranteed_raise is not None:
            handler_resolution, handler_body = cls._known_exception_handler_resolution(node.handlers, guaranteed_raise)
            if handler_resolution == "caught":
                return cls._class_block_cannot_raise(handler_body or []) and cls._class_block_cannot_raise(node.finalbody)
            return False
        if not cls._class_block_cannot_raise(node.body):
            return False
        return cls._class_block_cannot_raise(node.orelse) and cls._class_block_cannot_raise(node.finalbody)

    @classmethod
    def _class_block_guaranteed_raise_exception(cls, statements: list[ast.stmt]) -> type[BaseException] | None:
        for statement in statements:
            raised_type = cls._class_statement_guaranteed_raise_exception(statement)
            if raised_type is not None:
                return raised_type
            if cls._statement_guarantees_exit(statement):
                return None
            if not cls._class_statement_cannot_raise(statement):
                return None
        return None

    @classmethod
    def _class_statement_guaranteed_raise_exception(cls, node: ast.stmt) -> type[BaseException] | None:
        if isinstance(node, ast.Raise):
            return cls._raised_exception_type(node.exc)
        if isinstance(node, ast.If):
            if not cls._expression_cannot_raise(node.test):
                return None
            test_truth = cls._literal_truth_value(node.test)
            if test_truth is True:
                return cls._class_block_guaranteed_raise_exception(node.body)
            if test_truth is False:
                return cls._class_block_guaranteed_raise_exception(node.orelse)
        if isinstance(node, ast.Match):
            selected_body = cls._known_match_selected_body(node)
            if selected_body is not None:
                return cls._class_block_guaranteed_raise_exception(selected_body)
        return None

    @classmethod
    def _function_definition_statement_cannot_raise(cls, node: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
        if node.decorator_list:
            return False
        if cls._function_definition_has_annotations(node):
            return False
        defaults = [*node.args.defaults, *(default for default in node.args.kw_defaults if default is not None)]
        return all(cls._expression_cannot_raise(default) for default in defaults)

    @staticmethod
    def _function_definition_has_annotations(node: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
        if node.returns is not None:
            return True
        args = node.args
        for arg in [*args.posonlyargs, *args.args, *args.kwonlyargs]:
            if arg.annotation is not None:
                return True
        if args.vararg is not None and args.vararg.annotation is not None:
            return True
        return args.kwarg is not None and args.kwarg.annotation is not None

    @classmethod
    def _annassign_statement_cannot_raise(cls, node: ast.AnnAssign) -> bool:
        if not isinstance(node.target, ast.Name):
            return False
        return node.value is None or cls._expression_cannot_raise(node.value)

    @classmethod
    def _assignment_target_cannot_raise(cls, node: ast.AST) -> bool:
        if isinstance(node, ast.Name):
            return True
        if isinstance(node, ast.Starred):
            return isinstance(node.value, ast.Name)
        if isinstance(node, (ast.Tuple, ast.List)):
            return all(cls._assignment_target_cannot_raise(element) for element in node.elts)
        return False

    @classmethod
    def _assignment_statement_target_cannot_raise(cls, target: ast.AST, value: ast.AST) -> bool:
        if isinstance(target, ast.Name):
            return True
        if isinstance(target, (ast.Tuple, ast.List)):
            known, static_value = cls._static_comparison_value(value)
            return known and cls._unpack_assignment_target_matches_value(target, static_value)
        return False

    @classmethod
    def _assignment_store_target_guarantees_raise(cls, target: ast.AST) -> bool:
        if isinstance(target, (ast.Name, ast.Starred)):
            return False
        if isinstance(target, (ast.Tuple, ast.List)):
            return any(cls._assignment_store_target_guarantees_raise(element) for element in target.elts)
        if isinstance(target, ast.Attribute):
            return cls._expression_guarantees_raise(target.value)
        if isinstance(target, ast.Subscript):
            if cls._expression_guarantees_raise(target.value) or cls._expression_guarantees_raise(target.slice):
                return True
            known_value, value = cls._static_comparison_value(target.value)
            known_slice, slice_value = cls._static_slice_value(target.slice)
            if not known_value or not known_slice:
                return False
            if isinstance(target.slice, ast.Slice):
                return not isinstance(value, list)
            if isinstance(value, tuple):
                return True
            if isinstance(value, str):
                return True
            if isinstance(value, list):
                if not isinstance(slice_value, int):
                    return True
                index = slice_value if slice_value >= 0 else len(value) + slice_value
                return index < 0 or index >= len(value)
            if isinstance(value, dict):
                return not cls._static_value_is_hashable(slice_value)
        return False

    @classmethod
    def _unpack_assignment_target_matches_value(cls, target: ast.AST, value: object) -> bool:
        if isinstance(target, ast.Name):
            return True
        if isinstance(target, ast.Starred):
            return isinstance(target.value, ast.Name)
        if not isinstance(target, (ast.Tuple, ast.List)):
            return False
        if not isinstance(value, (tuple, list)):
            return False
        starred_indexes = [index for index, element in enumerate(target.elts) if isinstance(element, ast.Starred)]
        if len(starred_indexes) > 1:
            return False
        if not starred_indexes:
            if len(target.elts) != len(value):
                return False
            return all(
                cls._unpack_assignment_target_matches_value(element, item)
                for element, item in zip(target.elts, value)
            )

        starred_index = starred_indexes[0]
        starred_target = target.elts[starred_index]
        if not isinstance(starred_target, ast.Starred) or not isinstance(starred_target.value, ast.Name):
            return False
        prefix_targets = target.elts[:starred_index]
        suffix_targets = target.elts[starred_index + 1 :]
        if len(value) < len(prefix_targets) + len(suffix_targets):
            return False
        suffix_offset = len(value) - len(suffix_targets)
        return all(
            cls._unpack_assignment_target_matches_value(element, item)
            for element, item in zip(prefix_targets, value[: len(prefix_targets)])
        ) and all(
            cls._unpack_assignment_target_matches_value(element, item)
            for element, item in zip(suffix_targets, value[suffix_offset:])
        )

    @classmethod
    def _lambda_expression_cannot_raise(cls, node: ast.Lambda) -> bool:
        defaults = [*node.args.defaults, *(default for default in node.args.kw_defaults if default is not None)]
        return all(cls._expression_cannot_raise(default) for default in defaults)

    @classmethod
    def _iter_expression_cannot_raise_and_truth(cls, node: ast.AST) -> tuple[bool, bool | None]:
        iter_truth = cls._literal_iter_truth_value(node)
        if iter_truth is None:
            return False, None
        if cls._literal_range_truth_value(node) is not None:
            return True, iter_truth
        if not cls._expression_cannot_raise(node):
            return False, None
        return True, iter_truth

    @classmethod
    def _comprehension_generators_cannot_raise_and_yield_truth(
        cls, generators: list[ast.comprehension]
    ) -> tuple[bool, bool | None]:
        can_yield: bool | None = True
        for generator in generators:
            if generator.is_async:
                return False, None
            if can_yield is False:
                continue

            iter_cannot_raise, iter_truth = cls._iter_expression_cannot_raise_and_truth(generator.iter)
            if not iter_cannot_raise:
                return False, None
            if iter_truth is False:
                can_yield = False
                continue
            if not isinstance(generator.target, ast.Name):
                return False, None

            for if_clause in generator.ifs:
                if not cls._expression_cannot_raise(if_clause):
                    return False, None
                if_truth = cls._literal_truth_value(if_clause)
                if if_truth is False:
                    can_yield = False
                    break
                if if_truth is not True:
                    can_yield = None
        return True, can_yield

    @classmethod
    def _hashable_expression_cannot_raise(cls, node: ast.AST) -> bool:
        if not cls._expression_cannot_raise(node):
            return False
        known, value = cls._static_comparison_value(node)
        return known and cls._static_value_is_hashable(value)

    @classmethod
    def _eager_comprehension_result_cannot_raise(cls, node: ast.ListComp | ast.SetComp | ast.DictComp) -> bool:
        if isinstance(node, ast.ListComp):
            return cls._expression_cannot_raise(node.elt)
        if isinstance(node, ast.SetComp):
            return cls._hashable_expression_cannot_raise(node.elt)
        return cls._hashable_expression_cannot_raise(node.key) and cls._expression_cannot_raise(node.value)

    @classmethod
    def _eager_comprehension_cannot_raise(cls, node: ast.ListComp | ast.SetComp | ast.DictComp) -> bool:
        generators_cannot_raise, can_yield = cls._comprehension_generators_cannot_raise_and_yield_truth(node.generators)
        if not generators_cannot_raise:
            return False
        if can_yield is False:
            return True
        return cls._eager_comprehension_result_cannot_raise(node)

    @classmethod
    def _eager_comprehension_truth_value(cls, node: ast.ListComp | ast.SetComp | ast.DictComp) -> bool | None:
        generators_cannot_raise, can_yield = cls._comprehension_generators_cannot_raise_and_yield_truth(node.generators)
        if not generators_cannot_raise:
            return None
        if can_yield is False:
            return False
        if can_yield is True and cls._eager_comprehension_result_cannot_raise(node):
            return True
        return None

    @classmethod
    def _generator_expression_cannot_raise(cls, node: ast.GeneratorExp) -> bool:
        if not node.generators:
            return True
        first_generator = node.generators[0]
        if first_generator.is_async:
            return False
        iter_cannot_raise, _iter_truth = cls._iter_expression_cannot_raise_and_truth(first_generator.iter)
        return iter_cannot_raise

    @classmethod
    def _expression_cannot_raise(cls, node: ast.AST) -> bool:
        if isinstance(node, ast.Constant):
            return True
        if isinstance(node, (ast.Tuple, ast.List)):
            return all(cls._expression_cannot_raise(element) for element in node.elts)
        if isinstance(node, ast.Dict):
            return cls._dict_expression_cannot_raise(node)
        if isinstance(node, ast.Set):
            return cls._set_expression_cannot_raise(node)
        if isinstance(node, ast.UnaryOp):
            return cls._unaryop_expression_cannot_raise(node)
        if isinstance(node, ast.BinOp):
            return cls._binop_expression_cannot_raise(node)
        if isinstance(node, ast.BoolOp):
            return cls._boolop_expression_cannot_raise(node)
        if isinstance(node, ast.IfExp):
            if not cls._expression_cannot_raise(node.test):
                return False
            test_truth = cls._literal_truth_value(node.test)
            if test_truth is True:
                return cls._expression_cannot_raise(node.body)
            if test_truth is False:
                return cls._expression_cannot_raise(node.orelse)
            return cls._expression_cannot_raise(node.body) and cls._expression_cannot_raise(node.orelse)
        if isinstance(node, ast.Compare):
            return cls._literal_compare_truth_value(node) is not None
        if isinstance(node, ast.Subscript):
            return cls._subscript_expression_cannot_raise(node)
        if isinstance(node, ast.NamedExpr):
            return cls._assignment_target_cannot_raise(node.target) and cls._expression_cannot_raise(node.value)
        if isinstance(node, ast.JoinedStr):
            known, _value = cls._static_joined_str_value(node)
            return known
        if isinstance(node, ast.Lambda):
            return cls._lambda_expression_cannot_raise(node)
        if isinstance(node, (ast.ListComp, ast.SetComp, ast.DictComp)):
            return cls._eager_comprehension_cannot_raise(node)
        if isinstance(node, ast.GeneratorExp):
            return cls._generator_expression_cannot_raise(node)
        return False

    @classmethod
    def _expression_guarantees_raise(cls, node: ast.AST) -> bool:
        if isinstance(node, (ast.Tuple, ast.List, ast.Set)):
            return any(cls._expression_guarantees_raise(element) for element in node.elts)
        if isinstance(node, ast.Dict):
            for key, value in zip(node.keys, node.values):
                if key is not None and cls._expression_guarantees_raise(key):
                    return True
                if cls._expression_guarantees_raise(value):
                    return True
            return False
        if isinstance(node, ast.NamedExpr):
            return cls._expression_guarantees_raise(node.value)
        if isinstance(node, ast.IfExp):
            test_truth = cls._literal_truth_value(node.test)
            if test_truth is True:
                return cls._expression_guarantees_raise(node.body)
            if test_truth is False:
                return cls._expression_guarantees_raise(node.orelse)
            return cls._expression_guarantees_raise(node.body) and cls._expression_guarantees_raise(node.orelse)
        if isinstance(node, ast.UnaryOp):
            if cls._expression_guarantees_raise(node.operand):
                return True
            known_operand, operand_value = cls._static_comparison_value(node.operand)
            if not known_operand:
                return False
            try:
                if isinstance(node.op, ast.Not):
                    not operand_value
                elif isinstance(node.op, ast.UAdd):
                    +operand_value  # type: ignore[operator]
                elif isinstance(node.op, ast.USub):
                    -operand_value  # type: ignore[operator]
                elif isinstance(node.op, ast.Invert):
                    ~operand_value  # type: ignore[operator]
                else:
                    return False
            except (ArithmeticError, TypeError, ValueError, OverflowError):
                return True
            return False
        if isinstance(node, ast.BinOp):
            if cls._expression_guarantees_raise(node.left) or cls._expression_guarantees_raise(node.right):
                return True
            known_left, left_value = cls._static_comparison_value(node.left)
            known_right, right_value = cls._static_comparison_value(node.right)
            if not known_left or not known_right:
                return False
            try:
                if isinstance(node.op, ast.Add):
                    left_value + right_value  # type: ignore[operator]
                elif isinstance(node.op, ast.Sub) and cls._static_values_are_numbers(left_value, right_value):
                    left_value - right_value  # type: ignore[operator]
                elif isinstance(node.op, ast.Mult) and cls._static_values_are_numbers(left_value, right_value):
                    left_value * right_value  # type: ignore[operator]
                elif isinstance(node.op, ast.Div) and cls._static_values_are_numbers(left_value, right_value):
                    left_value / right_value  # type: ignore[operator]
                elif isinstance(node.op, ast.FloorDiv) and cls._static_values_are_numbers(left_value, right_value):
                    left_value // right_value  # type: ignore[operator]
                elif isinstance(node.op, ast.Mod) and cls._static_values_are_numbers(left_value, right_value):
                    left_value % right_value  # type: ignore[operator]
                elif isinstance(node.op, ast.BitAnd) and cls._static_values_are_ints(left_value, right_value):
                    left_value & right_value  # type: ignore[operator]
                elif isinstance(node.op, ast.BitOr) and cls._static_values_are_ints(left_value, right_value):
                    left_value | right_value  # type: ignore[operator]
                elif isinstance(node.op, ast.BitXor) and cls._static_values_are_ints(left_value, right_value):
                    left_value ^ right_value  # type: ignore[operator]
                else:
                    return False
            except (ArithmeticError, TypeError, ValueError, OverflowError):
                return True
            return False
        if isinstance(node, ast.Subscript):
            if cls._expression_guarantees_raise(node.value) or cls._expression_guarantees_raise(node.slice):
                return True
            known_value, value = cls._static_comparison_value(node.value)
            known_slice, slice_value = cls._static_slice_value(node.slice)
            if not known_value or not known_slice:
                return False
            try:
                value[slice_value]  # type: ignore[index]
            except (LookupError, TypeError, ValueError, OverflowError):
                return True
            return False
        return False

    @classmethod
    def _unaryop_expression_cannot_raise(cls, node: ast.UnaryOp) -> bool:
        if not cls._expression_cannot_raise(node.operand):
            return False
        if isinstance(node.op, ast.Not):
            return True
        known, _value = cls._static_unaryop_value(node)
        return known

    @classmethod
    def _boolop_expression_cannot_raise(cls, node: ast.BoolOp) -> bool:
        for value in node.values:
            if not cls._expression_cannot_raise(value):
                return False
            truth = cls._literal_truth_value(value)
            if isinstance(node.op, ast.And) and truth is False:
                return True
            if isinstance(node.op, ast.Or) and truth is True:
                return True
        return True

    @classmethod
    def _binop_expression_cannot_raise(cls, node: ast.BinOp) -> bool:
        if not cls._expression_cannot_raise(node.left) or not cls._expression_cannot_raise(node.right):
            return False
        known, _value = cls._static_binop_value(node)
        return known

    @classmethod
    def _subscript_expression_cannot_raise(cls, node: ast.Subscript) -> bool:
        if not cls._expression_cannot_raise(node.value) or not cls._slice_expression_cannot_raise(node.slice):
            return False
        known, _value = cls._static_subscript_value(node)
        return known

    @classmethod
    def _slice_expression_cannot_raise(cls, node: ast.AST) -> bool:
        if isinstance(node, ast.Slice):
            return all(
                part is None or cls._expression_cannot_raise(part)
                for part in (node.lower, node.upper, node.step)
            )
        return cls._expression_cannot_raise(node)

    @classmethod
    def _dict_expression_cannot_raise(cls, node: ast.Dict) -> bool:
        for key, value in zip(node.keys, node.values):
            if key is None:
                return False
            if not cls._expression_cannot_raise(key) or not cls._expression_cannot_raise(value):
                return False
            known_key, key_value = cls._static_comparison_value(key)
            if not known_key or not cls._static_value_is_hashable(key_value):
                return False
        return True

    @classmethod
    def _set_expression_cannot_raise(cls, node: ast.Set) -> bool:
        for element in node.elts:
            if not cls._expression_cannot_raise(element):
                return False
            known_value, value = cls._static_comparison_value(element)
            if not known_value or not cls._static_value_is_hashable(value):
                return False
        return True

    @staticmethod
    def _static_value_is_hashable(value: object) -> bool:
        try:
            hash(value)
        except TypeError:
            return False
        return True

    @classmethod
    def _block_guarantees_function_exit(cls, statements: list[ast.stmt]) -> bool:
        for statement in statements:
            if cls._statement_guarantees_function_exit(statement):
                return True
            if cls._statement_guarantees_exit(statement):
                return False
        return False

    @classmethod
    def _block_guarantees_nonsuppressible_exit(cls, statements: list[ast.stmt]) -> bool:
        for statement in statements:
            if cls._statement_guarantees_nonsuppressible_exit(statement):
                return True
            if cls._statement_guarantees_exit(statement):
                return False
        return False

    @classmethod
    def _statement_guarantees_nonsuppressible_exit(cls, node: ast.stmt) -> bool:
        if isinstance(node, (ast.Return, ast.Break, ast.Continue)):
            return True
        if isinstance(node, (ast.Raise, ast.Assert)):
            return False
        if isinstance(node, ast.If):
            test_truth = cls._literal_truth_value(node.test)
            if test_truth is True:
                return cls._block_guarantees_nonsuppressible_exit(node.body)
            if test_truth is False:
                return cls._block_guarantees_nonsuppressible_exit(node.orelse)
            if not node.orelse:
                return False
            return cls._block_guarantees_nonsuppressible_exit(node.body) and cls._block_guarantees_nonsuppressible_exit(
                node.orelse
            )
        if isinstance(node, (ast.With, ast.AsyncWith)):
            if cls._with_context_expression_guarantees_raise(node):
                return True
            return cls._block_guarantees_nonsuppressible_exit(node.body)
        if isinstance(node, ast.While):
            return cls._while_statement_guarantees_return(node)
        if isinstance(node, (ast.For, ast.AsyncFor)):
            return cls._for_statement_guarantees_return(node)
        if isinstance(node, TRY_STATEMENT_TYPES):
            if cls._block_guarantees_nonsuppressible_exit(node.finalbody):
                return True
            normal_path_exits = cls._block_guarantees_nonsuppressible_exit(node.body) or (
                bool(node.orelse) and cls._block_guarantees_nonsuppressible_exit(node.orelse)
            )
            if cls._block_cannot_raise(node.body):
                return normal_path_exits
            if not node.handlers:
                return normal_path_exits
            return normal_path_exits and all(cls._block_guarantees_nonsuppressible_exit(handler.body) for handler in node.handlers)
        if isinstance(node, ast.Match):
            return cls._match_statement_guarantees(node, cls._block_guarantees_nonsuppressible_exit)
        return False

    @classmethod
    def _statement_guarantees_function_exit(cls, node: ast.stmt) -> bool:
        if isinstance(node, (ast.Return, ast.Raise)):
            return True
        if isinstance(node, ast.Assert):
            return cls._literal_truth_value(node.test) is False
        if isinstance(node, ast.If):
            test_truth = cls._literal_truth_value(node.test)
            if test_truth is True:
                return cls._block_guarantees_function_exit(node.body)
            if test_truth is False:
                return cls._block_guarantees_function_exit(node.orelse)
            if not node.orelse:
                return False
            return cls._block_guarantees_function_exit(node.body) and cls._block_guarantees_function_exit(node.orelse)
        if isinstance(node, ast.While):
            return cls._while_statement_guarantees_function_exit(node)
        if isinstance(node, (ast.For, ast.AsyncFor)):
            return cls._for_statement_guarantees_function_exit(node)
        if isinstance(node, (ast.With, ast.AsyncWith)):
            if cls._with_context_expression_guarantees_raise(node):
                return True
            return cls._block_guarantees_return(node.body)
        if isinstance(node, TRY_STATEMENT_TYPES):
            if cls._block_guarantees_function_exit(node.finalbody):
                return True
            guaranteed_raise = cls._block_guaranteed_raise_exception(node.body)
            if guaranteed_raise is not None:
                handler_resolution, handler_body = cls._known_exception_handler_resolution(node.handlers, guaranteed_raise)
                if handler_resolution == "uncaught":
                    return True
                if handler_resolution == "caught":
                    return cls._block_guarantees_function_exit(handler_body or [])
            normal_path_exits = cls._block_guarantees_function_exit(node.body) or (
                bool(node.orelse) and cls._block_guarantees_function_exit(node.orelse)
            )
            if cls._block_cannot_raise(node.body):
                return normal_path_exits
            if not node.handlers:
                return normal_path_exits
            return normal_path_exits and all(cls._block_guarantees_function_exit(handler.body) for handler in node.handlers)
        if isinstance(node, ast.Match):
            return cls._match_statement_guarantees(
                node, cls._block_guarantees_function_exit, guard_exception_counts=True
            )
        return False

    @classmethod
    def _while_statement_guarantees_function_exit(cls, node: ast.While) -> bool:
        test_truth = cls._literal_truth_value(node.test)
        body_guarantees_function_exit = cls._block_guarantees_function_exit(node.body)
        orelse_guarantees_function_exit = cls._block_guarantees_function_exit(node.orelse)
        if test_truth is True:
            return not cls._block_may_reach_loop_break(node.body) and body_guarantees_function_exit
        if test_truth is False:
            return orelse_guarantees_function_exit
        return body_guarantees_function_exit and orelse_guarantees_function_exit

    @classmethod
    def _for_statement_guarantees_function_exit(cls, node: ast.For | ast.AsyncFor) -> bool:
        iter_truth = cls._literal_iter_truth_value(node.iter)
        body_guarantees_function_exit = cls._block_guarantees_function_exit(node.body)
        body_may_break = cls._block_may_reach_loop_break(node.body)
        orelse_guarantees_function_exit = cls._block_guarantees_function_exit(node.orelse)
        if iter_truth is False:
            return orelse_guarantees_function_exit
        if iter_truth is True:
            return not body_may_break and (body_guarantees_function_exit or orelse_guarantees_function_exit)
        return not body_may_break and body_guarantees_function_exit and orelse_guarantees_function_exit

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
        if isinstance(node, ast.While):
            return cls._while_statement_guarantees_return(node)
        if isinstance(node, (ast.For, ast.AsyncFor)):
            return cls._for_statement_guarantees_return(node)
        if isinstance(node, (ast.With, ast.AsyncWith)):
            return cls._block_guarantees_return(node.body)
        if isinstance(node, TRY_STATEMENT_TYPES):
            if cls._block_guarantees_return(node.finalbody):
                return True
            normal_path_returns = cls._block_guarantees_return(node.body) or (bool(node.orelse) and cls._block_guarantees_return(node.orelse))
            if cls._block_cannot_raise(node.body):
                return normal_path_returns
            if not node.handlers:
                return normal_path_returns
            return normal_path_returns and all(cls._block_guarantees_return(handler.body) for handler in node.handlers)
        if isinstance(node, ast.Match):
            return cls._match_statement_guarantees(node, cls._block_guarantees_return)
        return False

    @classmethod
    def _while_statement_guarantees_return(cls, node: ast.While) -> bool:
        test_truth = cls._literal_truth_value(node.test)
        body_guarantees_return = cls._block_guarantees_return(node.body)
        orelse_guarantees_return = cls._block_guarantees_return(node.orelse)
        if test_truth is True:
            return not cls._block_may_reach_loop_break(node.body) and body_guarantees_return
        if test_truth is False:
            return orelse_guarantees_return
        return body_guarantees_return and orelse_guarantees_return

    @classmethod
    def _for_statement_guarantees_return(cls, node: ast.For | ast.AsyncFor) -> bool:
        iter_truth = cls._literal_iter_truth_value(node.iter)
        body_guarantees_return = cls._block_guarantees_return(node.body)
        body_may_break = cls._block_may_reach_loop_break(node.body)
        orelse_guarantees_return = cls._block_guarantees_return(node.orelse)
        if iter_truth is False:
            return orelse_guarantees_return
        if iter_truth is True:
            return not body_may_break and (body_guarantees_return or orelse_guarantees_return)
        return not body_may_break and body_guarantees_return and orelse_guarantees_return

    @classmethod
    def _block_may_reach_loop_break(cls, statements: list[ast.stmt]) -> bool:
        for statement in statements:
            if cls._statement_may_reach_loop_break(statement):
                return True
            if cls._statement_guarantees_exit(statement):
                return False
        return False

    @classmethod
    def _statement_may_reach_loop_break(cls, node: ast.stmt) -> bool:
        if isinstance(node, ast.Break):
            return True
        if isinstance(node, ast.If):
            test_truth = cls._literal_truth_value(node.test)
            if test_truth is True:
                return cls._block_may_reach_loop_break(node.body)
            if test_truth is False:
                return cls._block_may_reach_loop_break(node.orelse)
            return cls._block_may_reach_loop_break(node.body) or cls._block_may_reach_loop_break(node.orelse)
        if isinstance(node, (ast.With, ast.AsyncWith)):
            return cls._block_may_reach_loop_break(node.body)
        if isinstance(node, TRY_STATEMENT_TYPES):
            body_cannot_raise = cls._block_cannot_raise(node.body)
            return (
                cls._block_may_reach_loop_break(node.body)
                or (not body_cannot_raise and any(cls._block_may_reach_loop_break(handler.body) for handler in node.handlers))
                or cls._block_may_reach_loop_break(node.orelse)
                or cls._block_may_reach_loop_break(node.finalbody)
            )
        if isinstance(node, ast.Match):
            selected_body = cls._known_match_selected_body(node)
            if selected_body is not None:
                return cls._block_may_reach_loop_break(selected_body)
            return any(cls._block_may_reach_loop_break(case.body) for case in node.cases)
        return False

    @classmethod
    def _block_guarantees_loop_else_skip(cls, statements: list[ast.stmt]) -> bool:
        for statement in statements:
            if cls._statement_guarantees_loop_else_skip(statement):
                return True
            if cls._statement_guarantees_exit(statement):
                return False
        return False

    @classmethod
    def _statement_guarantees_loop_else_skip(cls, node: ast.stmt) -> bool:
        if isinstance(node, (ast.Return, ast.Raise, ast.Break)):
            return True
        if isinstance(node, ast.Assert):
            return cls._literal_truth_value(node.test) is False
        if isinstance(node, ast.Continue):
            return False
        if isinstance(node, ast.If):
            test_truth = cls._literal_truth_value(node.test)
            if test_truth is True:
                return cls._block_guarantees_loop_else_skip(node.body)
            if test_truth is False:
                return cls._block_guarantees_loop_else_skip(node.orelse)
            if not node.orelse:
                return False
            return cls._block_guarantees_loop_else_skip(node.body) and cls._block_guarantees_loop_else_skip(node.orelse)
        if isinstance(node, (ast.With, ast.AsyncWith)):
            if cls._with_context_expression_guarantees_raise(node):
                return True
            return cls._block_guarantees_nonsuppressible_loop_else_skip(node.body)
        if isinstance(node, TRY_STATEMENT_TYPES):
            if cls._block_guarantees_loop_else_skip(node.finalbody):
                return True
            guaranteed_raise = cls._block_guaranteed_raise_exception(node.body)
            if guaranteed_raise is not None:
                handler_resolution, handler_body = cls._known_exception_handler_resolution(node.handlers, guaranteed_raise)
                if handler_resolution == "uncaught":
                    return True
                if handler_resolution == "caught":
                    return cls._block_guarantees_loop_else_skip(handler_body or [])
            normal_path_skips = cls._block_guarantees_loop_else_skip(node.body) or (
                bool(node.orelse) and cls._block_guarantees_loop_else_skip(node.orelse)
            )
            if cls._block_cannot_raise(node.body):
                return normal_path_skips
            if not node.handlers:
                return normal_path_skips
            return normal_path_skips and all(cls._block_guarantees_loop_else_skip(handler.body) for handler in node.handlers)
        if isinstance(node, ast.Match):
            return cls._match_statement_guarantees(
                node, cls._block_guarantees_loop_else_skip, guard_exception_counts=True
            )
        return False

    @classmethod
    def _block_guarantees_nonsuppressible_loop_else_skip(cls, statements: list[ast.stmt]) -> bool:
        for statement in statements:
            if cls._statement_guarantees_nonsuppressible_loop_else_skip(statement):
                return True
            if cls._statement_guarantees_exit(statement):
                return False
        return False

    @classmethod
    def _statement_guarantees_nonsuppressible_loop_else_skip(cls, node: ast.stmt) -> bool:
        if isinstance(node, (ast.Return, ast.Break)):
            return True
        if isinstance(node, (ast.Raise, ast.Assert, ast.Continue)):
            return False
        if isinstance(node, ast.If):
            test_truth = cls._literal_truth_value(node.test)
            if test_truth is True:
                return cls._block_guarantees_nonsuppressible_loop_else_skip(node.body)
            if test_truth is False:
                return cls._block_guarantees_nonsuppressible_loop_else_skip(node.orelse)
            if not node.orelse:
                return False
            return cls._block_guarantees_nonsuppressible_loop_else_skip(
                node.body
            ) and cls._block_guarantees_nonsuppressible_loop_else_skip(node.orelse)
        if isinstance(node, (ast.With, ast.AsyncWith)):
            if cls._with_context_expression_guarantees_raise(node):
                return True
            return cls._block_guarantees_nonsuppressible_loop_else_skip(node.body)
        if isinstance(node, TRY_STATEMENT_TYPES):
            if cls._block_guarantees_nonsuppressible_loop_else_skip(node.finalbody):
                return True
            normal_path_skips = cls._block_guarantees_nonsuppressible_loop_else_skip(node.body) or (
                bool(node.orelse) and cls._block_guarantees_nonsuppressible_loop_else_skip(node.orelse)
            )
            if cls._block_cannot_raise(node.body):
                return normal_path_skips
            if not node.handlers:
                return normal_path_skips
            return normal_path_skips and all(
                cls._block_guarantees_nonsuppressible_loop_else_skip(handler.body) for handler in node.handlers
            )
        if isinstance(node, ast.Match):
            return cls._match_statement_guarantees(node, cls._block_guarantees_nonsuppressible_loop_else_skip)
        return False

    @classmethod
    def _block_guaranteed_raise_exception(cls, statements: list[ast.stmt]) -> type[BaseException] | None:
        for statement in statements:
            raised_type = cls._statement_guaranteed_raise_exception(statement)
            if raised_type is not None:
                return raised_type
            if cls._statement_guarantees_exit(statement):
                return None
            if not cls._statement_cannot_raise(statement):
                return None
        return None

    @classmethod
    def _statement_guaranteed_raise_exception(cls, node: ast.stmt) -> type[BaseException] | None:
        if isinstance(node, ast.Raise):
            return cls._raised_exception_type(node.exc)
        if isinstance(node, ast.Assert) and cls._literal_truth_value(node.test) is False:
            return AssertionError
        if isinstance(node, ast.If):
            test_truth = cls._literal_truth_value(node.test)
            if test_truth is True:
                return cls._block_guaranteed_raise_exception(node.body)
            if test_truth is False:
                return cls._block_guaranteed_raise_exception(node.orelse)
            return None
        if isinstance(node, ast.Match):
            selected_body = cls._known_match_selected_body(node)
            if selected_body is not None:
                return cls._block_guaranteed_raise_exception(selected_body)
        return None

    @classmethod
    def _raised_exception_type(cls, node: ast.AST | None) -> type[BaseException] | None:
        if node is None:
            return None
        if isinstance(node, ast.Call):
            return cls._raised_exception_type(node.func)
        if isinstance(node, ast.Name):
            candidate = getattr(builtins, node.id, None)
            if isinstance(candidate, type) and issubclass(candidate, BaseException):
                return candidate
        return None

    @classmethod
    def _known_exception_handler_resolution(
        cls, handlers: list[ast.ExceptHandler], raised_type: type[BaseException]
    ) -> tuple[str, list[ast.stmt] | None]:
        for handler in handlers:
            match = cls._handler_matches_exception(handler.type, raised_type)
            if match is True:
                return "caught", handler.body
            if match is None:
                return "unknown", None
        return "uncaught", None

    @classmethod
    def _handler_matches_exception(cls, node: ast.AST | None, raised_type: type[BaseException]) -> bool | None:
        if node is None:
            return True
        if isinstance(node, ast.Tuple):
            saw_unknown = False
            for element in node.elts:
                match = cls._handler_matches_exception(element, raised_type)
                if match is True:
                    return True
                if match is None:
                    saw_unknown = True
            return None if saw_unknown else False
        if isinstance(node, ast.Name):
            candidate = getattr(builtins, node.id, None)
            if isinstance(candidate, type) and issubclass(candidate, BaseException):
                return issubclass(raised_type, candidate)
        return None

    @classmethod
    def _match_statement_guarantees(
        cls, node: ast.Match, block_checker, *, guard_exception_counts: bool = False
    ) -> bool:
        if guard_exception_counts:
            known, subject_value = cls._static_match_subject_value(node.subject)
            if known:
                return cls._known_subject_match_statement_guarantees(node, subject_value, block_checker)

        selected_body = cls._known_match_selected_body(node)
        if selected_body is not None:
            return block_checker(selected_body)
        if not any(cls._case_is_unguarded_irrefutable(case) for case in node.cases):
            return False
        return all(block_checker(case.body) for case in node.cases)

    @classmethod
    def _known_subject_match_statement_guarantees(cls, node: ast.Match, subject_value: object, block_checker) -> bool:
        return cls._known_subject_match_cases_guarantee_from(node.cases, subject_value, block_checker)

    @classmethod
    def _known_subject_match_cases_guarantee_from(
        cls, cases: list[ast.match_case], subject_value: object, block_checker
    ) -> bool:
        for index, case in enumerate(cases):
            pattern_match = cls._match_pattern_matches_literal(subject_value, case.pattern)
            if pattern_match is False:
                continue
            if pattern_match is None:
                if cls._case_is_unguarded_irrefutable(case):
                    return block_checker(case.body)
                if not block_checker(case.body):
                    return False
                return cls._known_subject_match_cases_guarantee_from(
                    cases[index + 1 :], subject_value, block_checker
                )
            if case.guard is None:
                return block_checker(case.body)
            guard_truth = cls._literal_truth_value(case.guard)
            if guard_truth is True:
                return block_checker(case.body)
            if guard_truth is False:
                continue
            return block_checker(case.body) and cls._known_subject_match_cases_guarantee_from(
                cases[index + 1 :], subject_value, block_checker
            )
        return False

    @classmethod
    def _case_is_unguarded_irrefutable(cls, case: ast.match_case) -> bool:
        return case.guard is None and cls._pattern_is_irrefutable(case.pattern)

    @classmethod
    def _pattern_is_irrefutable(cls, pattern: ast.pattern) -> bool:
        if isinstance(pattern, ast.MatchAs):
            if pattern.pattern is None:
                return True
            return cls._pattern_is_irrefutable(pattern.pattern)
        if isinstance(pattern, ast.MatchOr):
            return any(cls._pattern_is_irrefutable(subpattern) for subpattern in pattern.patterns)
        return False

    @classmethod
    def _known_match_selected_body(cls, node: ast.Match) -> list[ast.stmt] | None:
        known, subject_value = cls._static_match_subject_value(node.subject)
        if not known:
            return None
        for case in node.cases:
            pattern_match = cls._match_pattern_matches_literal(subject_value, case.pattern)
            if pattern_match is False:
                continue
            if pattern_match is None:
                return None
            if case.guard is None:
                guard_truth = True
            else:
                if not cls._expression_cannot_raise(case.guard):
                    return None
                guard_truth = cls._literal_truth_value(case.guard)
            if guard_truth is False:
                continue
            if guard_truth is True:
                return case.body
            return None
        return None

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
        self.visit(node.func)
        for arg in node.args:
            self._visit_call_argument(node, arg)
        for keyword in node.keywords:
            self._visit_call_argument(node, keyword.value)

    def _visit_call_argument(self, call: ast.Call, value: ast.AST) -> None:
        if isinstance(value, ast.GeneratorExp) and self._is_generator_consuming_call(call):
            self._visit_comprehension(value.generators, [value.elt])
            return
        self.visit(value)

    @classmethod
    def _is_generator_consuming_call(cls, node: ast.Call) -> bool:
        return isinstance(node.func, ast.Name) and node.func.id in GENERATOR_CONSUMING_CALL_NAMES

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
        if isinstance(node, ast.NamedExpr):
            if not cls._assignment_target_cannot_raise(node.target):
                return None
            return cls._literal_truth_value(node.value)
        if isinstance(node, ast.JoinedStr):
            known, value = cls._static_joined_str_value(node)
            if known:
                return bool(value)
            return None
        if isinstance(node, ast.Lambda):
            if cls._lambda_expression_cannot_raise(node):
                return True
            return None
        if isinstance(node, (ast.ListComp, ast.SetComp, ast.DictComp)):
            return cls._eager_comprehension_truth_value(node)
        if isinstance(node, ast.GeneratorExp):
            if cls._generator_expression_cannot_raise(node):
                return True
            return None
        if isinstance(node, (ast.Tuple, ast.List, ast.Set)):
            return bool(node.elts)
        if isinstance(node, ast.Dict):
            return bool(node.keys)
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):
            operand_truth = cls._literal_truth_value(node.operand)
            if operand_truth is not None:
                return not operand_truth
            return None
        if isinstance(node, ast.BoolOp):
            value_truths = [cls._literal_truth_value(value) for value in node.values]
            if isinstance(node.op, ast.And):
                if any(value_truth is False for value_truth in value_truths):
                    return False
                if all(value_truth is True for value_truth in value_truths):
                    return True
                return None
            if isinstance(node.op, ast.Or):
                if any(value_truth is True for value_truth in value_truths):
                    return True
                if all(value_truth is False for value_truth in value_truths):
                    return False
                return None
        compare_truth = cls._literal_compare_truth_value(node)
        if compare_truth is not None:
            return compare_truth
        signed_numeric = cls._signed_numeric_literal_value(node)
        if signed_numeric is not None:
            return bool(signed_numeric)
        return None

    @classmethod
    def _static_literal_value(cls, node: ast.AST) -> tuple[bool, object]:
        if isinstance(node, ast.Constant):
            return True, node.value
        if isinstance(node, ast.JoinedStr):
            return cls._static_joined_str_value(node)
        signed_numeric = cls._signed_numeric_literal_value(node)
        if signed_numeric is not None:
            return True, signed_numeric
        return False, None

    @classmethod
    def _static_joined_str_value(cls, node: ast.JoinedStr) -> tuple[bool, object]:
        parts = []
        for value in node.values:
            if not isinstance(value, ast.Constant) or not isinstance(value.value, str):
                return False, None
            parts.append(value.value)
        result = "".join(parts)
        if len(result) > MAX_STATIC_STRING_CHARS:
            return False, None
        return True, result

    @classmethod
    def _static_unaryop_value(cls, node: ast.UnaryOp) -> tuple[bool, object]:
        known_operand, operand_value = cls._static_comparison_value(node.operand)
        if not known_operand:
            return False, None
        try:
            if isinstance(node.op, ast.Not):
                value = not operand_value
            elif isinstance(node.op, ast.UAdd):
                value = +operand_value  # type: ignore[operator]
            elif isinstance(node.op, ast.USub):
                value = -operand_value  # type: ignore[operator]
            elif isinstance(node.op, ast.Invert):
                value = ~operand_value  # type: ignore[operator]
            else:
                return False, None
        except (ArithmeticError, TypeError, ValueError, OverflowError):
            return False, None
        if not cls._static_value_is_small(value):
            return False, None
        return True, value

    @classmethod
    def _static_binop_value(cls, node: ast.BinOp) -> tuple[bool, object]:
        known_left, left_value = cls._static_comparison_value(node.left)
        known_right, right_value = cls._static_comparison_value(node.right)
        if not known_left or not known_right:
            return False, None
        try:
            if isinstance(node.op, ast.Add):
                value = left_value + right_value  # type: ignore[operator]
            elif isinstance(node.op, ast.Sub) and cls._static_values_are_numbers(left_value, right_value):
                value = left_value - right_value  # type: ignore[operator]
            elif isinstance(node.op, ast.Mult) and cls._static_values_are_numbers(left_value, right_value):
                value = left_value * right_value  # type: ignore[operator]
            elif isinstance(node.op, ast.Div) and cls._static_values_are_numbers(left_value, right_value):
                value = left_value / right_value  # type: ignore[operator]
            elif isinstance(node.op, ast.FloorDiv) and cls._static_values_are_numbers(left_value, right_value):
                value = left_value // right_value  # type: ignore[operator]
            elif isinstance(node.op, ast.Mod) and cls._static_values_are_numbers(left_value, right_value):
                value = left_value % right_value  # type: ignore[operator]
            elif isinstance(node.op, ast.BitAnd) and cls._static_values_are_ints(left_value, right_value):
                value = left_value & right_value  # type: ignore[operator]
            elif isinstance(node.op, ast.BitOr) and cls._static_values_are_ints(left_value, right_value):
                value = left_value | right_value  # type: ignore[operator]
            elif isinstance(node.op, ast.BitXor) and cls._static_values_are_ints(left_value, right_value):
                value = left_value ^ right_value  # type: ignore[operator]
            else:
                return False, None
        except (ArithmeticError, TypeError, ValueError, OverflowError):
            return False, None
        if not cls._static_value_is_small(value):
            return False, None
        return True, value

    @classmethod
    def _static_slice_part_value(cls, node: ast.AST | None) -> tuple[bool, int | None]:
        if node is None:
            return True, None
        value = cls._integer_literal_value(node)
        if value is None:
            return False, None
        return True, value

    @classmethod
    def _static_slice_value(cls, node: ast.AST) -> tuple[bool, object]:
        if isinstance(node, ast.Slice):
            known_lower, lower = cls._static_slice_part_value(node.lower)
            known_upper, upper = cls._static_slice_part_value(node.upper)
            known_step, step = cls._static_slice_part_value(node.step)
            if not known_lower or not known_upper or not known_step:
                return False, None
            return True, slice(lower, upper, step)
        return cls._static_comparison_value(node)

    @classmethod
    def _static_subscript_value(cls, node: ast.Subscript) -> tuple[bool, object]:
        known_value, value = cls._static_comparison_value(node.value)
        known_slice, slice_value = cls._static_slice_value(node.slice)
        if not known_value or not known_slice:
            return False, None
        try:
            result = value[slice_value]  # type: ignore[index]
        except (LookupError, TypeError, ValueError, OverflowError):
            return False, None
        if not cls._static_value_is_small(result):
            return False, None
        return True, result

    @staticmethod
    def _static_values_are_numbers(left: object, right: object) -> bool:
        number_types = (int, float, complex)
        return (
            isinstance(left, number_types)
            and isinstance(right, number_types)
            and not isinstance(left, bool)
            and not isinstance(right, bool)
        )

    @staticmethod
    def _static_values_are_ints(left: object, right: object) -> bool:
        return isinstance(left, int) and isinstance(right, int) and not isinstance(left, bool) and not isinstance(right, bool)

    @classmethod
    def _static_value_is_small(cls, value: object) -> bool:
        if isinstance(value, bool):
            return True
        if isinstance(value, int):
            return value.bit_length() <= MAX_STATIC_INT_BITS
        if isinstance(value, (float, complex, type(None))):
            return True
        if isinstance(value, (str, bytes)):
            return len(value) <= MAX_STATIC_STRING_CHARS
        if isinstance(value, (tuple, list, set, frozenset)):
            return len(value) <= MAX_STATIC_VALUE_ITEMS and all(cls._static_value_is_small(element) for element in value)
        if isinstance(value, dict):
            return len(value) <= MAX_STATIC_VALUE_ITEMS and all(
                cls._static_value_is_small(key) and cls._static_value_is_small(item) for key, item in value.items()
            )
        return False

    @classmethod
    def _static_comparison_value(cls, node: ast.AST) -> tuple[bool, object]:
        known, value = cls._static_literal_value(node)
        if known:
            return True, value
        if isinstance(node, ast.UnaryOp):
            return cls._static_unaryop_value(node)
        if isinstance(node, ast.BinOp):
            return cls._static_binop_value(node)
        if isinstance(node, ast.Subscript):
            return cls._static_subscript_value(node)
        if isinstance(node, ast.NamedExpr):
            if not cls._assignment_target_cannot_raise(node.target):
                return False, None
            return cls._static_comparison_value(node.value)
        if isinstance(node, ast.Tuple):
            values = []
            for element in node.elts:
                known, value = cls._static_comparison_value(element)
                if not known:
                    return False, None
                values.append(value)
            return True, tuple(values)
        if isinstance(node, ast.List):
            values = []
            for element in node.elts:
                known, value = cls._static_comparison_value(element)
                if not known:
                    return False, None
                values.append(value)
            return True, values
        if isinstance(node, ast.Set):
            values = []
            for element in node.elts:
                known, value = cls._static_comparison_value(element)
                if not known:
                    return False, None
                values.append(value)
            try:
                return True, set(values)
            except TypeError:
                return False, None
        if isinstance(node, ast.Dict):
            pairs = []
            for key, value_node in zip(node.keys, node.values):
                if key is None:
                    return False, None
                known_key, key_value = cls._static_comparison_value(key)
                known_value, value = cls._static_comparison_value(value_node)
                if not known_key or not known_value:
                    return False, None
                pairs.append((key_value, value))
            try:
                return True, dict(pairs)
            except TypeError:
                return False, None
        return False, None

    @classmethod
    def _literal_compare_truth_value(cls, node: ast.AST) -> bool | None:
        if not isinstance(node, ast.Compare):
            return None
        known_left, left_value = cls._static_comparison_value(node.left)
        if not known_left:
            return None
        for op, comparator in zip(node.ops, node.comparators):
            known_right, right_value = cls._static_comparison_value(comparator)
            if not known_right:
                return None
            pair_truth = cls._literal_compare_pair_truth_value(left_value, op, right_value)
            if pair_truth is None:
                return None
            if pair_truth is False:
                return False
            left_value = right_value
        return True

    @staticmethod
    def _literal_compare_pair_truth_value(left: object, op: ast.cmpop, right: object) -> bool | None:
        try:
            if isinstance(op, ast.Eq):
                return left == right
            if isinstance(op, ast.NotEq):
                return left != right
            if isinstance(op, ast.Is):
                return left is right
            if isinstance(op, ast.IsNot):
                return left is not right
            if isinstance(op, ast.Lt):
                return left < right  # type: ignore[operator]
            if isinstance(op, ast.LtE):
                return left <= right  # type: ignore[operator]
            if isinstance(op, ast.Gt):
                return left > right  # type: ignore[operator]
            if isinstance(op, ast.GtE):
                return left >= right  # type: ignore[operator]
            if isinstance(op, ast.In):
                return left in right  # type: ignore[operator]
            if isinstance(op, ast.NotIn):
                return left not in right  # type: ignore[operator]
        except (TypeError, ValueError):
            return None
        return None

    @classmethod
    def _static_match_subject_value(cls, node: ast.AST) -> tuple[bool, object]:
        known, value = cls._static_literal_value(node)
        if known:
            return True, value
        if isinstance(node, (ast.Tuple, ast.List)):
            values = []
            for element in node.elts:
                known, value = cls._static_match_subject_value(element)
                if not known:
                    return False, None
                values.append(value)
            return True, tuple(values)
        if isinstance(node, ast.Dict):
            values = []
            for key, value_node in zip(node.keys, node.values):
                if key is None:
                    return False, None
                known_key, key_value = cls._static_match_subject_value(key)
                known_value, value = cls._static_match_subject_value(value_node)
                if not known_key or not known_value:
                    return False, None
                values.append((key_value, value))
            try:
                return True, dict(values)
            except TypeError:
                return False, None
        return False, None

    @classmethod
    def _match_pattern_matches_literal(cls, subject_value: object, pattern: ast.pattern) -> bool | None:
        if isinstance(pattern, ast.MatchAs):
            if pattern.pattern is None:
                return True
            return cls._match_pattern_matches_literal(subject_value, pattern.pattern)
        if isinstance(pattern, ast.MatchOr):
            results = [cls._match_pattern_matches_literal(subject_value, subpattern) for subpattern in pattern.patterns]
            if any(result is True for result in results):
                return True
            if all(result is False for result in results):
                return False
            return None
        if isinstance(pattern, ast.MatchSingleton):
            return subject_value is pattern.value
        if isinstance(pattern, ast.MatchValue):
            known, pattern_value = cls._static_literal_value(pattern.value)
            if not known:
                return None
            return subject_value == pattern_value
        if isinstance(pattern, ast.MatchSequence):
            if not isinstance(subject_value, tuple):
                return False
            if any(isinstance(subpattern, ast.MatchStar) for subpattern in pattern.patterns):
                return None
            if len(subject_value) != len(pattern.patterns):
                return False
            results = [
                cls._match_pattern_matches_literal(subject_element, subpattern)
                for subject_element, subpattern in zip(subject_value, pattern.patterns)
            ]
            if any(result is False for result in results):
                return False
            if all(result is True for result in results):
                return True
            return None
        if isinstance(pattern, ast.MatchMapping):
            if not isinstance(subject_value, dict):
                return False
            if pattern.rest is not None:
                return None
            results = []
            for key_node, value_pattern in zip(pattern.keys, pattern.patterns):
                known_key, key_value = cls._static_match_subject_value(key_node)
                if not known_key:
                    return None
                try:
                    if key_value not in subject_value:
                        return False
                    subject_element = subject_value[key_value]
                except TypeError:
                    return None
                results.append(cls._match_pattern_matches_literal(subject_element, value_pattern))
            if any(result is False for result in results):
                return False
            if all(result is True for result in results):
                return True
            return None
        return None

    @classmethod
    def _literal_iter_truth_value(cls, node: ast.AST) -> bool | None:
        if isinstance(node, (ast.Tuple, ast.List, ast.Set)):
            return bool(node.elts)
        if isinstance(node, ast.Dict):
            return bool(node.keys)
        if isinstance(node, ast.Constant) and isinstance(node.value, (str, bytes)):
            return bool(node.value)
        range_truth = cls._literal_range_truth_value(node)
        if range_truth is not None:
            return range_truth
        return None

    @classmethod
    def _literal_range_truth_value(cls, node: ast.AST) -> bool | None:
        if not isinstance(node, ast.Call):
            return None
        if not isinstance(node.func, ast.Name) or node.func.id != "range":
            return None
        if node.keywords or not 1 <= len(node.args) <= 3:
            return None
        values: list[int] = []
        for arg in node.args:
            value = cls._integer_literal_value(arg)
            if value is None:
                return None
            values.append(value)
        try:
            return bool(range(*values))
        except ValueError:
            return None

    @classmethod
    def _integer_literal_value(cls, node: ast.AST) -> int | None:
        if isinstance(node, ast.Constant) and isinstance(node.value, int) and not isinstance(node.value, bool):
            return node.value
        signed_numeric = cls._signed_numeric_literal_value(node)
        if isinstance(signed_numeric, int) and not isinstance(signed_numeric, bool):
            return signed_numeric
        return None

    @staticmethod
    def _signed_numeric_literal_value(node: ast.AST) -> int | float | complex | None:
        if not isinstance(node, ast.UnaryOp) or not isinstance(node.op, (ast.UAdd, ast.USub)):
            return None
        if not isinstance(node.operand, ast.Constant):
            return None
        value = node.operand.value
        if isinstance(value, (int, float, complex)) and not isinstance(value, bool):
            if isinstance(node.op, ast.USub):
                return -value
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
        ("direct_check_boolean_or_truthy_rejected", "def f(value):\n    check('bad', True or value)\n", 1),
        ("direct_check_boolean_and_false_allowed", "def f(value):\n    check('ok', False and value)\n", 0),
        ("direct_check_literal_compare_truthy_rejected", "def f():\n    check('bad', 1 == 1)\n", 1),
        ("direct_check_literal_compare_false_allowed", "def f():\n    check('ok', 1 == 2)\n", 0),
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
            2,
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
            "target_with_async_selftest_check_only_rejected",
            "async def run_self_tests(value):\n    check('ok', value is True)\n",
            ["missing_selftest_checks"],
        ),
        (
            "target_with_generator_selftest_check_only_rejected",
            "def run_self_tests(value):\n    check('ok', value is True)\n    yield None\n",
            ["missing_selftest_checks"],
        ),
        (
            "target_with_unreachable_yield_selftest_check_only_rejected",
            "def run_self_tests(value):\n    if False:\n        yield None\n    check('ok', value is True)\n",
            ["missing_selftest_checks"],
        ),
        (
            "target_with_yield_from_selftest_check_only_rejected",
            "def run_self_tests(value):\n    check('ok', value is True)\n    yield from []\n",
            ["missing_selftest_checks"],
        ),
        (
            "target_with_selftest_default_check_only_rejected",
            "def run_self_tests(value=check('bad', True)):\n    pass\n",
            ["literal_true_check", "missing_selftest_checks"],
        ),
        (
            "target_with_selftest_annotation_check_only_rejected",
            "def run_self_tests(value: check('bad', True)):\n    pass\n",
            ["literal_true_check", "missing_selftest_checks"],
        ),
        (
            "target_with_future_selftest_annotation_check_only_rejected",
            "from __future__ import annotations\n\ndef run_self_tests(value: check('bad', True)):\n    pass\n",
            ["literal_true_check", "missing_selftest_checks"],
        ),
        (
            "target_with_nested_helper_default_truthy_rejected",
            "def run_self_tests():\n    def helper(arg=check('bad', True)):\n        pass\n",
            ["literal_true_check"],
        ),
        (
            "target_with_nested_helper_annotation_truthy_rejected",
            "def run_self_tests():\n    def helper(arg: check('bad', True)):\n        pass\n",
            ["literal_true_check"],
        ),
        (
            "target_with_nested_helper_only_rejected",
            "def run_self_tests():\n    def helper(value):\n        check('ok', value is True)\n",
            ["missing_selftest_checks"],
        ),
        (
            "target_with_future_nested_helper_annotation_only_rejected",
            "from __future__ import annotations\n\ndef run_self_tests(value):\n    def helper(arg: check('ok', value is True)):\n        pass\n",
            ["missing_selftest_checks"],
        ),
        (
            "target_with_local_annotation_only_rejected",
            "def run_self_tests(value):\n    local: check('ok', value is True)\n",
            ["missing_selftest_checks"],
        ),
        (
            "target_with_method_local_annotation_only_rejected",
            "def run_self_tests(value):\n    class Helper:\n        def method(self):\n            local: check('ok', value is True)\n",
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
            "target_with_assert_true_message_check_only_rejected",
            "def run_self_tests():\n    assert True, check('ok', value is True)\n",
            ["missing_selftest_checks"],
        ),
        (
            "target_with_assert_not_false_message_check_only_rejected",
            "def run_self_tests():\n    assert not False, check('ok', value is True)\n",
            ["missing_selftest_checks"],
        ),
        (
            "target_with_not_lambda_branch_rejected",
            "def run_self_tests():\n    if not (lambda: 1):\n        check('ok', value is True)\n",
            ["missing_selftest_checks"],
        ),
        (
            "target_with_assert_false_then_check_rejected",
            "def run_self_tests():\n    assert False\n    check('ok', value is True)\n",
            ["missing_selftest_checks"],
        ),
        (
            "target_with_if_false_only_rejected",
            "def run_self_tests():\n    if False:\n        check('ok', value is True)\n",
            ["missing_selftest_checks"],
        ),
        (
            "target_with_namedexpr_false_branch_rejected",
            "def run_self_tests():\n    if (flag := False):\n        check('ok', value is True)\n",
            ["missing_selftest_checks"],
        ),
        (
            "target_with_assign_static_oob_rhs_subscript_target_check_rejected",
            "def run_self_tests(value, items):\n    items[check('ok', value is True)] = [][0]\n",
            ["missing_selftest_checks"],
        ),
        (
            "target_with_assign_static_missing_key_rhs_subscript_target_check_rejected",
            "def run_self_tests(value, items):\n    items[check('ok', value is True)] = {}['x']\n",
            ["missing_selftest_checks"],
        ),
        (
            "target_with_assign_static_divzero_rhs_subscript_target_check_rejected",
            "def run_self_tests(value, items):\n    items[check('ok', value is True)] = 1 / 0\n",
            ["missing_selftest_checks"],
        ),
        (
            "target_with_annassign_static_oob_rhs_subscript_target_check_rejected",
            "def run_self_tests(value, items):\n    items[check('ok', value is True)]: int = [][0]\n",
            ["missing_selftest_checks"],
        ),
        (
            "target_with_annassign_static_missing_key_rhs_subscript_target_check_rejected",
            "def run_self_tests(value, items):\n    items[check('ok', value is True)]: int = {}['x']\n",
            ["missing_selftest_checks"],
        ),
        (
            "target_with_annassign_static_divzero_rhs_subscript_target_check_rejected",
            "def run_self_tests(value, items):\n    items[check('ok', value is True)]: int = 1 / 0\n",
            ["missing_selftest_checks"],
        ),
        (
            "target_with_annassign_class_static_oob_rhs_annotation_check_rejected",
            "def run_self_tests(value):\n    class Helper:\n        field: check('ok', value is True) = [][0]\n",
            ["missing_selftest_checks"],
        ),
        (
            "target_with_annassign_static_oob_target_annotation_check_rejected",
            "def run_self_tests(value):\n    class Helper:\n        [][0]: check('ok', value is True)\n",
            ["missing_selftest_checks"],
        ),
        (
            "target_with_annassign_safe_rhs_subscript_target_check_allowed",
            "def run_self_tests(value, items):\n    items[check('ok', value is True)]: int = 1\n",
            [],
        ),
        (
            "target_with_annassign_dynamic_rhs_subscript_target_check_allowed",
            "def run_self_tests(value, items, maybe):\n    items[check('ok', value is True)]: int = maybe\n",
            [],
        ),
        (
            "target_with_annassign_rhs_check_before_later_raise_allowed",
            "def run_self_tests(value, items):\n    items[0]: int = (check('ok', value is True), [][0])\n",
            [],
        ),
        (
            "target_with_annassign_dict_store_target_annotation_check_allowed",
            "def run_self_tests(value):\n    class Helper:\n        {}['x']: check('ok', value is True) = 1\n",
            [],
        ),
        (
            "target_with_augassign_static_oob_target_rhs_check_rejected",
            "def run_self_tests(value):\n    [][0] += check('ok', value is True)\n",
            ["missing_selftest_checks"],
        ),
        (
            "target_with_augassign_static_missing_key_target_rhs_check_rejected",
            "def run_self_tests(value):\n    {}['x'] += check('ok', value is True)\n",
            ["missing_selftest_checks"],
        ),
        (
            "target_with_augassign_static_oob_target_index_check_allowed",
            "def run_self_tests(value):\n    [][check('ok', value is True)] += 1\n",
            [],
        ),
        (
            "target_with_augassign_safe_target_rhs_check_allowed",
            "def run_self_tests(value, items):\n    items[0] += check('ok', value is True)\n",
            [],
        ),
        (
            "target_with_with_static_oob_context_body_check_rejected",
            "def run_self_tests(value):\n    with [][0]:\n        check('ok', value is True)\n",
            ["missing_selftest_checks"],
        ),
        (
            "target_with_with_static_oob_context_optional_vars_check_rejected",
            "def run_self_tests(value, items):\n    with [][0] as items[check('ok', value is True)]:\n        pass\n",
            ["missing_selftest_checks"],
        ),
        (
            "target_with_with_static_oob_context_post_check_rejected",
            "def run_self_tests(value):\n    with [][0]:\n        pass\n    check('ok', value is True)\n",
            ["missing_selftest_checks"],
        ),
        (
            "target_with_with_static_oob_optional_vars_target_body_check_rejected",
            "def run_self_tests(value, guard):\n    with guard as [][0]:\n        check('ok', value is True)\n",
            ["missing_selftest_checks"],
        ),
        (
            "target_with_with_static_oob_optional_vars_target_check_allowed",
            "def run_self_tests(value, guard):\n    with guard as [][check('ok', value is True)]:\n        pass\n",
            [],
        ),
        (
            "target_with_with_dict_optional_vars_target_body_check_allowed",
            "def run_self_tests(value, guard):\n    with guard as {}['x']:\n        check('ok', value is True)\n",
            [],
        ),
        (
            "target_with_with_suppressible_optional_vars_target_then_post_check_allowed",
            "def run_self_tests(value, guard):\n    with guard as [][0]:\n        pass\n    check('ok', value is True)\n",
            [],
        ),
        (
            "target_with_with_second_static_oob_context_body_check_rejected",
            "def run_self_tests(value, guard):\n    with guard, [][0]:\n        check('ok', value is True)\n",
            ["missing_selftest_checks"],
        ),
        (
            "target_with_literal_fstring_false_branch_rejected",
            "def run_self_tests():\n    if f'':\n        check('ok', value is True)\n",
            ["missing_selftest_checks"],
        ),
        (
            "target_with_empty_listcomp_branch_rejected",
            "def run_self_tests():\n    if [risky() for item in []]:\n        check('ok', value is True)\n",
            ["missing_selftest_checks"],
        ),
        (
            "target_with_if_not_true_only_rejected",
            "def run_self_tests():\n    if not True:\n        check('ok', value is True)\n",
            ["missing_selftest_checks"],
        ),
        (
            "target_with_if_false_or_false_only_rejected",
            "def run_self_tests():\n    if False or False:\n        check('ok', value is True)\n",
            ["missing_selftest_checks"],
        ),
        (
            "target_with_if_true_and_false_only_rejected",
            "def run_self_tests():\n    if True and False:\n        check('ok', value is True)\n",
            ["missing_selftest_checks"],
        ),
        (
            "target_with_short_circuited_and_check_only_rejected",
            "def run_self_tests():\n    if False and check('ok', value is True):\n        pass\n",
            ["missing_selftest_checks"],
        ),
        (
            "target_with_namedexpr_short_circuited_and_check_rejected",
            "def run_self_tests():\n    if (flag := False) and check('ok', value is True):\n        pass\n",
            ["missing_selftest_checks"],
        ),
        (
            "target_with_short_circuited_or_check_only_rejected",
            "def run_self_tests():\n    if True or check('ok', value is True):\n        pass\n",
            ["missing_selftest_checks"],
        ),
        (
            "target_with_lambda_short_circuited_or_check_rejected",
            "def run_self_tests():\n    if (lambda: 1) or check('ok', value is True):\n        pass\n",
            ["missing_selftest_checks"],
        ),
        (
            "target_with_static_listcomp_short_circuited_or_check_rejected",
            "def run_self_tests():\n    if [1 for item in [1]] or check('ok', value is True):\n        pass\n",
            ["missing_selftest_checks"],
        ),
        (
            "target_with_empty_listcomp_short_circuited_and_check_rejected",
            "def run_self_tests():\n    if [risky() for item in []] and check('ok', value is True):\n        pass\n",
            ["missing_selftest_checks"],
        ),
        (
            "target_with_ifexp_false_branch_check_only_rejected",
            "def run_self_tests():\n    result = check('ok', value is True) if False else None\n",
            ["missing_selftest_checks"],
        ),
        (
            "target_with_if_literal_eq_false_only_rejected",
            "def run_self_tests():\n    if 1 == 2:\n        check('ok', value is True)\n",
            ["missing_selftest_checks"],
        ),
        (
            "target_with_if_literal_ne_false_only_rejected",
            "def run_self_tests():\n    if 'a' != 'a':\n        check('ok', value is True)\n",
            ["missing_selftest_checks"],
        ),
        (
            "target_with_if_literal_fstring_compare_false_only_rejected",
            "def run_self_tests():\n    if f'a' == 'b':\n        check('ok', value is True)\n",
            ["missing_selftest_checks"],
        ),
        (
            "target_with_if_literal_order_false_only_rejected",
            "def run_self_tests():\n    if 3 < 2:\n        check('ok', value is True)\n",
            ["missing_selftest_checks"],
        ),
        (
            "target_with_if_literal_membership_false_only_rejected",
            "def run_self_tests():\n    if 'x' in ('a', 'b'):\n        check('ok', value is True)\n",
            ["missing_selftest_checks"],
        ),
        (
            "target_with_if_literal_identity_false_only_rejected",
            "def run_self_tests():\n    if None is not None:\n        check('ok', value is True)\n",
            ["missing_selftest_checks"],
        ),
        (
            "target_with_short_circuited_compare_check_only_rejected",
            "def run_self_tests():\n    if 1 == 2 == check('ok', value is True):\n        pass\n",
            ["missing_selftest_checks"],
        ),
        (
            "target_with_empty_listcomp_check_only_rejected",
            "def run_self_tests():\n    checks = [check('ok', value is True) for value in []]\n",
            ["missing_selftest_checks"],
        ),
        (
            "target_with_empty_listcomp_subscript_target_check_rejected",
            "def run_self_tests(value, items):\n    checks = [1 for items[check('ok', value is True)] in []]\n",
            ["missing_selftest_checks"],
        ),
        (
            "target_with_empty_range_setcomp_check_only_rejected",
            "def run_self_tests():\n    checks = {check('ok', value is True) for value in range(0)}\n",
            ["missing_selftest_checks"],
        ),
        (
            "target_with_false_filter_dictcomp_check_only_rejected",
            "def run_self_tests():\n    checks = {item: check('ok', value is True) for item in [1] if False}\n",
            ["missing_selftest_checks"],
        ),
        (
            "target_with_empty_genexp_check_only_rejected",
            "def run_self_tests():\n    all(check('ok', value is True) for value in [])\n",
            ["missing_selftest_checks"],
        ),
        (
            "target_with_stored_genexp_check_only_rejected",
            "def run_self_tests():\n    gen = (check('ok', value is True) for item in [1])\n",
            ["missing_selftest_checks"],
        ),
        (
            "target_with_tuple_contained_genexp_check_only_rejected",
            "def run_self_tests():\n    holder = ((check('ok', value is True) for item in [1]),)\n",
            ["missing_selftest_checks"],
        ),
        (
            "target_with_nested_empty_comp_check_only_rejected",
            "def run_self_tests():\n    checks = [check('ok', value is True) for outer in [1] for inner in []]\n",
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
            "target_with_with_nested_while_return_then_check_rejected",
            "def run_self_tests(lock):\n    with lock:\n        while True:\n            return\n    check('ok', value is True)\n",
            ["missing_selftest_checks"],
        ),
        (
            "target_with_break_then_body_check_rejected",
            "def run_self_tests(lock):\n    for item in [1]:\n        with lock:\n            break\n        check('ok', value is True)\n",
            ["missing_selftest_checks"],
        ),
        (
            "target_with_continue_then_body_check_rejected",
            "def run_self_tests(lock):\n    for item in [1]:\n        with lock:\n            continue\n        check('ok', value is True)\n",
            ["missing_selftest_checks"],
        ),
        (
            "target_with_break_loop_else_check_rejected",
            "def run_self_tests(lock):\n    for item in [1]:\n        with lock:\n            break\n    else:\n        check('ok', value is True)\n",
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
            "target_with_while_true_no_break_then_check_rejected",
            "def run_self_tests():\n    while True:\n        pass\n    check('ok', value is True)\n",
            ["missing_selftest_checks"],
        ),
        (
            "target_with_while_true_else_check_rejected",
            "def run_self_tests():\n    while True:\n        break\n    else:\n        check('ok', value is True)\n",
            ["missing_selftest_checks"],
        ),
        (
            "target_with_unknown_while_else_return_then_check_rejected",
            "def run_self_tests(flag):\n    while flag:\n        pass\n    else:\n        return\n    check('ok', value is True)\n",
            ["missing_selftest_checks"],
        ),
        (
            "target_with_unknown_while_return_else_return_then_check_rejected",
            "def run_self_tests(flag):\n    while flag:\n        return\n    else:\n        return\n    check('ok', value is True)\n",
            ["missing_selftest_checks"],
        ),
        (
            "target_with_unknown_while_continue_else_return_then_check_rejected",
            "def run_self_tests(flag):\n    while flag:\n        continue\n    else:\n        return\n    check('ok', value is True)\n",
            ["missing_selftest_checks"],
        ),
        (
            "target_with_empty_for_only_rejected",
            "def run_self_tests():\n    for value in []:\n        check('ok', value is True)\n",
            ["missing_selftest_checks"],
        ),
        (
            "target_with_empty_for_subscript_target_check_rejected",
            "def run_self_tests(value, items):\n    for items[check('ok', value is True)] in []:\n        pass\n",
            ["missing_selftest_checks"],
        ),
        (
            "target_with_empty_range_for_only_rejected",
            "def run_self_tests():\n    for value in range(0):\n        check('ok', value is True)\n",
            ["missing_selftest_checks"],
        ),
        (
            "target_with_empty_range_for_subscript_target_check_rejected",
            "def run_self_tests(value, items):\n    for items[check('ok', value is True)] in range(0):\n        pass\n",
            ["missing_selftest_checks"],
        ),
        (
            "target_with_nonempty_for_return_then_check_rejected",
            "def run_self_tests():\n    for value in [1]:\n        return\n    check('ok', value is True)\n",
            ["missing_selftest_checks"],
        ),
        (
            "target_with_nonempty_range_return_then_check_rejected",
            "def run_self_tests():\n    for value in range(1):\n        return\n    check('ok', value is True)\n",
            ["missing_selftest_checks"],
        ),
        (
            "target_with_nested_while_return_then_check_rejected",
            "def run_self_tests():\n    for outer in [1]:\n        while True:\n            return\n    check('ok', value is True)\n",
            ["missing_selftest_checks"],
        ),
        (
            "target_with_nested_for_return_then_check_rejected",
            "def run_self_tests():\n    for outer in [1]:\n        for inner in [1]:\n            return\n    check('ok', value is True)\n",
            ["missing_selftest_checks"],
        ),
        (
            "target_with_nonempty_for_else_return_then_check_rejected",
            "def run_self_tests():\n    for value in [1]:\n        pass\n    else:\n        return\n    check('ok', value is True)\n",
            ["missing_selftest_checks"],
        ),
        (
            "target_with_nested_for_else_return_then_check_rejected",
            "def run_self_tests():\n    for outer in [1]:\n        for inner in [1]:\n            pass\n        else:\n            return\n    check('ok', value is True)\n",
            ["missing_selftest_checks"],
        ),
        (
            "target_with_unknown_for_else_return_then_check_rejected",
            "def run_self_tests(items):\n    for value in items:\n        pass\n    else:\n        return\n    check('ok', value is True)\n",
            ["missing_selftest_checks"],
        ),
        (
            "target_with_nonempty_for_continue_else_return_then_check_rejected",
            "def run_self_tests():\n    for value in [1]:\n        continue\n    else:\n        return\n    check('ok', value is True)\n",
            ["missing_selftest_checks"],
        ),
        (
            "target_with_nonempty_for_break_else_check_rejected",
            "def run_self_tests():\n    for value in [1]:\n        break\n    else:\n        check('ok', value is True)\n",
            ["missing_selftest_checks"],
        ),
        (
            "target_with_nonempty_range_break_else_check_rejected",
            "def run_self_tests():\n    for value in range(1):\n        break\n    else:\n        check('ok', value is True)\n",
            ["missing_selftest_checks"],
        ),
        (
            "target_with_negative_step_range_break_else_check_rejected",
            "def run_self_tests():\n    for value in range(3, 0, -1):\n        break\n    else:\n        check('ok', value is True)\n",
            ["missing_selftest_checks"],
        ),
        (
            "target_with_match_nonmatching_case_only_rejected",
            "def run_self_tests():\n    match 1:\n        case 2:\n            check('ok', value is True)\n",
            ["missing_selftest_checks"],
        ),
        (
            "target_with_match_or_nonmatching_case_only_rejected",
            "def run_self_tests():\n    match 3:\n        case 1 | 2:\n            check('ok', value is True)\n",
            ["missing_selftest_checks"],
        ),
        (
            "target_with_match_singleton_nonmatching_case_only_rejected",
            "def run_self_tests():\n    match 1:\n        case True:\n            check('ok', value is True)\n",
            ["missing_selftest_checks"],
        ),
        (
            "target_with_match_first_return_then_check_rejected",
            "def run_self_tests():\n    match 1:\n        case 1:\n            return\n        case _:\n            check('ok', value is True)\n",
            ["missing_selftest_checks"],
        ),
        (
            "target_with_match_guard_false_only_rejected",
            "def run_self_tests():\n    match 1:\n        case 1 if False:\n            check('ok', value is True)\n",
            ["missing_selftest_checks"],
        ),
        (
            "target_with_match_risky_truthy_guard_return_then_check_rejected",
            "def run_self_tests():\n    match 1:\n        case 1 if risky() or True:\n            return\n        case _:\n            pass\n    check('ok', value is True)\n",
            ["missing_selftest_checks"],
        ),
        (
            "target_with_match_risky_false_guard_wildcard_return_then_check_rejected",
            "def run_self_tests():\n    match 1:\n        case 1 if risky() and False:\n            pass\n        case _:\n            return\n    check('ok', value is True)\n",
            ["missing_selftest_checks"],
        ),
        (
            "target_with_match_risky_unknown_guard_all_paths_exit_then_check_rejected",
            "def run_self_tests():\n    match 1:\n        case 1 if risky():\n            return\n        case _:\n            return\n    check('ok', value is True)\n",
            ["missing_selftest_checks"],
        ),
        (
            "target_with_match_unknown_wildcard_return_then_check_rejected",
            "def run_self_tests(value):\n    match value:\n        case _:\n            return\n    check('ok', value is True)\n",
            ["missing_selftest_checks"],
        ),
        (
            "target_with_match_unknown_capture_return_then_check_rejected",
            "def run_self_tests(value):\n    match value:\n        case captured:\n            return\n    check('ok', value is True)\n",
            ["missing_selftest_checks"],
        ),
        (
            "target_with_match_unknown_literal_then_wildcard_return_then_check_rejected",
            "def run_self_tests(value):\n    match value:\n        case 1:\n            return\n        case _:\n            return\n    check('ok', value is True)\n",
            ["missing_selftest_checks"],
        ),
        (
            "target_with_match_tuple_sequence_return_then_check_rejected",
            "def run_self_tests(value):\n    match (1, 2):\n        case (1, 2):\n            return\n    check('ok', value is True)\n",
            ["missing_selftest_checks"],
        ),
        (
            "target_with_match_list_sequence_return_then_check_rejected",
            "def run_self_tests(value):\n    match [1, 2]:\n        case [1, 2]:\n            return\n    check('ok', value is True)\n",
            ["missing_selftest_checks"],
        ),
        (
            "target_with_match_sequence_or_return_then_check_rejected",
            "def run_self_tests(value):\n    match (1, 2):\n        case (0, 0) | (1, 2):\n            return\n    check('ok', value is True)\n",
            ["missing_selftest_checks"],
        ),
        (
            "target_with_match_nonmatching_sequence_only_rejected",
            "def run_self_tests(value):\n    match (1, 2):\n        case (1, 3):\n            check('ok', value is True)\n",
            ["missing_selftest_checks"],
        ),
        (
            "target_with_match_mapping_return_then_check_rejected",
            "def run_self_tests(value):\n    match {'a': 1}:\n        case {'a': 1}:\n            return\n    check('ok', value is True)\n",
            ["missing_selftest_checks"],
        ),
        (
            "target_with_match_mapping_extra_key_return_then_check_rejected",
            "def run_self_tests(value):\n    match {'a': 1, 'b': 2}:\n        case {'a': 1}:\n            return\n    check('ok', value is True)\n",
            ["missing_selftest_checks"],
        ),
        (
            "target_with_match_nonmatching_mapping_only_rejected",
            "def run_self_tests(value):\n    match {'a': 1}:\n        case {'a': 2}:\n            check('ok', value is True)\n",
            ["missing_selftest_checks"],
        ),
        (
            "target_with_try_return_then_check_rejected",
            "def run_self_tests():\n    try:\n        return\n    finally:\n        pass\n    check('ok', value is True)\n",
            ["missing_selftest_checks"],
        ),
        (
            "target_with_try_return_else_check_rejected",
            "def run_self_tests():\n    try:\n        return\n    except Error:\n        pass\n    else:\n        check('ok', value is True)\n",
            ["missing_selftest_checks"],
        ),
        (
            "target_with_try_pass_except_check_rejected",
            "def run_self_tests():\n    try:\n        pass\n    except Error as exc:\n        check('ok', 'needle' in str(exc))\n",
            ["missing_selftest_checks"],
        ),
        (
            "target_with_try_constant_except_check_rejected",
            "def run_self_tests():\n    try:\n        1\n    except Error as exc:\n        check('ok', 'needle' in str(exc))\n",
            ["missing_selftest_checks"],
        ),
        (
            "target_with_try_global_except_check_rejected",
            "def run_self_tests():\n    try:\n        global flag\n    except Error as exc:\n        check('ok', 'needle' in str(exc))\n",
            ["missing_selftest_checks"],
        ),
        (
            "target_with_try_functiondef_except_check_rejected",
            "def run_self_tests():\n    try:\n        def helper():\n            pass\n    except Error as exc:\n        check('ok', 'needle' in str(exc))\n",
            ["missing_selftest_checks"],
        ),
        (
            "target_with_try_async_functiondef_except_check_rejected",
            "def run_self_tests():\n    try:\n        async def helper():\n            pass\n    except Error as exc:\n        check('ok', 'needle' in str(exc))\n",
            ["missing_selftest_checks"],
        ),
        (
            "target_with_try_functiondef_literal_default_except_check_rejected",
            "def run_self_tests():\n    try:\n        def helper(value=1, *, other=f'ok'):\n            pass\n    except Error as exc:\n        check('ok', 'needle' in str(exc))\n",
            ["missing_selftest_checks"],
        ),
        (
            "target_with_try_classdef_except_check_rejected",
            "def run_self_tests():\n    try:\n        class Helper:\n            pass\n    except Error as exc:\n        check('ok', 'needle' in str(exc))\n",
            ["missing_selftest_checks"],
        ),
        (
            "target_with_try_classdef_body_assign_except_check_rejected",
            "def run_self_tests():\n    try:\n        class Helper:\n            value = 1\n    except Error as exc:\n        check('ok', 'needle' in str(exc))\n",
            ["missing_selftest_checks"],
        ),
        (
            "target_with_try_classdef_body_function_except_check_rejected",
            "def run_self_tests():\n    try:\n        class Helper:\n            def method(self):\n                pass\n    except Error as exc:\n        check('ok', 'needle' in str(exc))\n",
            ["missing_selftest_checks"],
        ),
        (
            "target_with_try_classdef_if_false_risky_body_except_check_rejected",
            "def run_self_tests():\n    try:\n        class Helper:\n            if False:\n                value = risky()\n    except Error as exc:\n        check('ok', 'needle' in str(exc))\n",
            ["missing_selftest_checks"],
        ),
        (
            "target_with_try_classdef_body_while_false_except_check_rejected",
            "def run_self_tests():\n    try:\n        class Helper:\n            while False:\n                risky()\n    except Error as exc:\n        check('ok', 'needle' in str(exc))\n",
            ["missing_selftest_checks"],
        ),
        (
            "target_with_try_classdef_body_for_empty_except_check_rejected",
            "def run_self_tests():\n    try:\n        class Helper:\n            for item in []:\n                risky()\n    except Error as exc:\n        check('ok', 'needle' in str(exc))\n",
            ["missing_selftest_checks"],
        ),
        (
            "target_with_try_classdef_body_for_static_assign_except_check_rejected",
            "def run_self_tests():\n    try:\n        class Helper:\n            for item in [1]:\n                value = 1\n    except Error as exc:\n        check('ok', 'needle' in str(exc))\n",
            ["missing_selftest_checks"],
        ),
        (
            "target_with_try_classdef_body_match_literal_except_check_rejected",
            "def run_self_tests():\n    try:\n        class Helper:\n            match 1:\n                case 1:\n                    value = 1\n    except Error as exc:\n        check('ok', 'needle' in str(exc))\n",
            ["missing_selftest_checks"],
        ),
        (
            "target_with_try_classdef_body_match_nonmatching_except_check_rejected",
            "def run_self_tests():\n    try:\n        class Helper:\n            match 1:\n                case 2:\n                    risky()\n    except Error as exc:\n        check('ok', 'needle' in str(exc))\n",
            ["missing_selftest_checks"],
        ),
        (
            "target_with_try_classdef_body_try_pass_except_check_rejected",
            "def run_self_tests():\n    try:\n        class Helper:\n            try:\n                pass\n            except Error:\n                pass\n    except Error as exc:\n        check('ok', 'needle' in str(exc))\n",
            ["missing_selftest_checks"],
        ),
        (
            "target_with_try_classdef_body_try_finally_except_check_rejected",
            "def run_self_tests():\n    try:\n        class Helper:\n            try:\n                value = 1\n            finally:\n                other = 2\n    except Error as exc:\n        check('ok', 'needle' in str(exc))\n",
            ["missing_selftest_checks"],
        ),
        (
            "target_with_try_classdef_body_try_else_except_check_rejected",
            "def run_self_tests():\n    try:\n        class Helper:\n            try:\n                value = 1\n            except Error:\n                pass\n            else:\n                other = 2\n    except Error as exc:\n        check('ok', 'needle' in str(exc))\n",
            ["missing_selftest_checks"],
        ),
        (
            "target_with_try_classdef_body_try_unreachable_handler_except_check_rejected",
            "def run_self_tests():\n    try:\n        class Helper:\n            try:\n                pass\n            except Error:\n                risky()\n    except Error as exc:\n        check('ok', 'needle' in str(exc))\n",
            ["missing_selftest_checks"],
        ),
        (
            "target_with_try_classdef_body_try_caught_exception_except_check_rejected",
            "def run_self_tests():\n    try:\n        class Helper:\n            try:\n                raise ValueError('x')\n            except ValueError:\n                pass\n    except Error as exc:\n        check('ok', 'needle' in str(exc))\n",
            ["missing_selftest_checks"],
        ),
        (
            "target_with_try_classdef_body_try_caught_finally_except_check_rejected",
            "def run_self_tests():\n    try:\n        class Helper:\n            try:\n                raise ValueError('x')\n            except ValueError:\n                value = 1\n            finally:\n                other = 2\n    except Error as exc:\n        check('ok', 'needle' in str(exc))\n",
            ["missing_selftest_checks"],
        ),
        (
            "target_with_try_classdef_body_try_caught_else_unreachable_except_check_rejected",
            "def run_self_tests():\n    try:\n        class Helper:\n            try:\n                raise ValueError('x')\n            except ValueError:\n                pass\n            else:\n                risky()\n    except Error as exc:\n        check('ok', 'needle' in str(exc))\n",
            ["missing_selftest_checks"],
        ),
        (
            "target_with_try_classdef_body_try_caught_bare_except_check_rejected",
            "def run_self_tests():\n    try:\n        class Helper:\n            try:\n                raise ValueError('x')\n            except:\n                pass\n    except Error as exc:\n        check('ok', 'needle' in str(exc))\n",
            ["missing_selftest_checks"],
        ),
        (
            "target_with_try_classdef_body_try_match_guard_true_caught_except_check_rejected",
            "def run_self_tests():\n    try:\n        class Helper:\n            try:\n                match 1:\n                    case 1 if True:\n                        raise ValueError('x')\n            except ValueError:\n                pass\n    except Error as exc:\n        check('ok', 'needle' in str(exc))\n",
            ["missing_selftest_checks"],
        ),
        (
            "target_with_try_while_false_except_check_rejected",
            "def run_self_tests():\n    try:\n        while False:\n            risky()\n    except Error as exc:\n        check('ok', 'needle' in str(exc))\n",
            ["missing_selftest_checks"],
        ),
        (
            "target_with_try_while_true_break_except_check_rejected",
            "def run_self_tests():\n    try:\n        while True:\n            break\n    except Error as exc:\n        check('ok', 'needle' in str(exc))\n",
            ["missing_selftest_checks"],
        ),
        (
            "target_with_try_for_empty_except_check_rejected",
            "def run_self_tests():\n    try:\n        for item in []:\n            risky()\n    except Error as exc:\n        check('ok', 'needle' in str(exc))\n",
            ["missing_selftest_checks"],
        ),
        (
            "target_with_try_for_empty_else_pass_except_check_rejected",
            "def run_self_tests():\n    try:\n        for item in range(0):\n            risky()\n        else:\n            pass\n    except Error as exc:\n        check('ok', 'needle' in str(exc))\n",
            ["missing_selftest_checks"],
        ),
        (
            "target_with_try_for_static_safe_body_except_check_rejected",
            "def run_self_tests():\n    try:\n        for item in [1]:\n            value = 1\n    except Error as exc:\n        check('ok', 'needle' in str(exc))\n",
            ["missing_selftest_checks"],
        ),
        (
            "target_with_try_match_literal_except_check_rejected",
            "def run_self_tests():\n    try:\n        match 1:\n            case 1:\n                pass\n    except Error as exc:\n        check('ok', 'needle' in str(exc))\n",
            ["missing_selftest_checks"],
        ),
        (
            "target_with_try_match_nonmatching_except_check_rejected",
            "def run_self_tests():\n    try:\n        match 1:\n            case 2:\n                risky()\n    except Error as exc:\n        check('ok', 'needle' in str(exc))\n",
            ["missing_selftest_checks"],
        ),
        (
            "target_with_try_match_false_guard_except_check_rejected",
            "def run_self_tests():\n    try:\n        match 1:\n            case 1 if False:\n                risky()\n    except Error as exc:\n        check('ok', 'needle' in str(exc))\n",
            ["missing_selftest_checks"],
        ),
        (
            "target_with_try_match_sequence_except_check_rejected",
            "def run_self_tests():\n    try:\n        match (1, 2):\n            case (1, 2):\n                value = 1\n    except Error as exc:\n        check('ok', 'needle' in str(exc))\n",
            ["missing_selftest_checks"],
        ),
        (
            "target_with_try_match_mapping_except_check_rejected",
            "def run_self_tests():\n    try:\n        match {'a': 1}:\n            case {'a': 1}:\n                value = 1\n    except Error as exc:\n        check('ok', 'needle' in str(exc))\n",
            ["missing_selftest_checks"],
        ),
        (
            "target_with_try_literal_unary_minus_except_check_rejected",
            "def run_self_tests():\n    try:\n        -1\n    except Error as exc:\n        check('ok', 'needle' in str(exc))\n",
            ["missing_selftest_checks"],
        ),
        (
            "target_with_try_literal_invert_int_except_check_rejected",
            "def run_self_tests():\n    try:\n        ~1\n    except Error as exc:\n        check('ok', 'needle' in str(exc))\n",
            ["missing_selftest_checks"],
        ),
        (
            "target_with_try_literal_not_except_check_rejected",
            "def run_self_tests():\n    try:\n        not False\n    except Error as exc:\n        check('ok', 'needle' in str(exc))\n",
            ["missing_selftest_checks"],
        ),
        (
            "target_with_try_assignment_except_check_rejected",
            "def run_self_tests():\n    try:\n        value = 1\n    except Error as exc:\n        check('ok', 'needle' in str(exc))\n",
            ["missing_selftest_checks"],
        ),
        (
            "target_with_try_annassign_except_check_rejected",
            "def run_self_tests():\n    try:\n        value: int = 1\n    except Error as exc:\n        check('ok', 'needle' in str(exc))\n",
            ["missing_selftest_checks"],
        ),
        (
            "target_with_try_annassign_no_value_except_check_rejected",
            "def run_self_tests():\n    try:\n        value: int\n    except Error as exc:\n        check('ok', 'needle' in str(exc))\n",
            ["missing_selftest_checks"],
        ),
        (
            "target_with_try_annassign_risky_annotation_except_check_rejected",
            "def run_self_tests():\n    try:\n        value: risky() = 1\n    except Error as exc:\n        check('ok', 'needle' in str(exc))\n",
            ["missing_selftest_checks"],
        ),
        (
            "target_with_try_literal_tuple_unpack_except_check_rejected",
            "def run_self_tests():\n    try:\n        a, b = (1, 2)\n    except Error as exc:\n        check('ok', 'needle' in str(exc))\n",
            ["missing_selftest_checks"],
        ),
        (
            "target_with_try_nested_literal_unpack_except_check_rejected",
            "def run_self_tests():\n    try:\n        a, (b, c) = (1, (2, 3))\n    except Error as exc:\n        check('ok', 'needle' in str(exc))\n",
            ["missing_selftest_checks"],
        ),
        (
            "target_with_try_star_tail_unpack_except_check_rejected",
            "def run_self_tests():\n    try:\n        a, *rest = (1, 2)\n    except Error as exc:\n        check('ok', 'needle' in str(exc))\n",
            ["missing_selftest_checks"],
        ),
        (
            "target_with_try_star_only_unpack_except_check_rejected",
            "def run_self_tests():\n    try:\n        *rest, = ()\n    except Error as exc:\n        check('ok', 'needle' in str(exc))\n",
            ["missing_selftest_checks"],
        ),
        (
            "target_with_try_star_middle_unpack_except_check_rejected",
            "def run_self_tests():\n    try:\n        a, *rest, b = (1, 2, 3)\n    except Error as exc:\n        check('ok', 'needle' in str(exc))\n",
            ["missing_selftest_checks"],
        ),
        (
            "target_with_try_nested_star_unpack_except_check_rejected",
            "def run_self_tests():\n    try:\n        a, (*mid, z) = (1, (2, 3))\n    except Error as exc:\n        check('ok', 'needle' in str(exc))\n",
            ["missing_selftest_checks"],
        ),
        (
            "target_with_try_empty_dict_except_check_rejected",
            "def run_self_tests():\n    try:\n        {}\n    except Error as exc:\n        check('ok', 'needle' in str(exc))\n",
            ["missing_selftest_checks"],
        ),
        (
            "target_with_try_static_dict_except_check_rejected",
            "def run_self_tests():\n    try:\n        {'a': 1}\n    except Error as exc:\n        check('ok', 'needle' in str(exc))\n",
            ["missing_selftest_checks"],
        ),
        (
            "target_with_try_static_set_except_check_rejected",
            "def run_self_tests():\n    try:\n        {1, 2}\n    except Error as exc:\n        check('ok', 'needle' in str(exc))\n",
            ["missing_selftest_checks"],
        ),
        (
            "target_with_try_literal_add_except_check_rejected",
            "def run_self_tests():\n    try:\n        1 + 2\n    except Error as exc:\n        check('ok', 'needle' in str(exc))\n",
            ["missing_selftest_checks"],
        ),
        (
            "target_with_try_literal_string_concat_except_check_rejected",
            "def run_self_tests():\n    try:\n        'a' + 'b'\n    except Error as exc:\n        check('ok', 'needle' in str(exc))\n",
            ["missing_selftest_checks"],
        ),
        (
            "target_with_try_literal_tuple_concat_except_check_rejected",
            "def run_self_tests():\n    try:\n        (1,) + (2,)\n    except Error as exc:\n        check('ok', 'needle' in str(exc))\n",
            ["missing_selftest_checks"],
        ),
        (
            "target_with_try_literal_tuple_subscript_except_check_rejected",
            "def run_self_tests():\n    try:\n        (1, 2)[0]\n    except Error as exc:\n        check('ok', 'needle' in str(exc))\n",
            ["missing_selftest_checks"],
        ),
        (
            "target_with_try_literal_string_subscript_except_check_rejected",
            "def run_self_tests():\n    try:\n        'abc'[1]\n    except Error as exc:\n        check('ok', 'needle' in str(exc))\n",
            ["missing_selftest_checks"],
        ),
        (
            "target_with_try_literal_slice_except_check_rejected",
            "def run_self_tests():\n    try:\n        (1, 2, 3)[1:]\n    except Error as exc:\n        check('ok', 'needle' in str(exc))\n",
            ["missing_selftest_checks"],
        ),
        (
            "target_with_try_literal_dict_subscript_except_check_rejected",
            "def run_self_tests():\n    try:\n        {'a': 1}['a']\n    except Error as exc:\n        check('ok', 'needle' in str(exc))\n",
            ["missing_selftest_checks"],
        ),
        (
            "target_with_try_true_or_risky_except_check_rejected",
            "def run_self_tests():\n    try:\n        True or risky()\n    except Error as exc:\n        check('ok', 'needle' in str(exc))\n",
            ["missing_selftest_checks"],
        ),
        (
            "target_with_try_false_and_risky_except_check_rejected",
            "def run_self_tests():\n    try:\n        False and risky()\n    except Error as exc:\n        check('ok', 'needle' in str(exc))\n",
            ["missing_selftest_checks"],
        ),
        (
            "target_with_try_known_raise_disjoint_except_check_rejected",
            "def run_self_tests():\n    try:\n        raise ValueError('needle')\n    except TypeError as exc:\n        check('ok', 'needle' in str(exc))\n",
            ["missing_selftest_checks"],
        ),
        (
            "target_with_try_known_raise_tuple_disjoint_except_check_rejected",
            "def run_self_tests():\n    try:\n        raise ValueError('needle')\n    except (TypeError, KeyError) as exc:\n        check('ok', 'needle' in str(exc))\n",
            ["missing_selftest_checks"],
        ),
        (
            "target_with_try_return_except_check_rejected",
            "def run_self_tests():\n    try:\n        return\n    except Error as exc:\n        check('ok', 'needle' in str(exc))\n",
            ["missing_selftest_checks"],
        ),
        (
            "target_with_try_return_except_pass_then_check_rejected",
            "def run_self_tests():\n    try:\n        return\n    except Error:\n        pass\n    check('ok', value is True)\n",
            ["missing_selftest_checks"],
        ),
        (
            "target_with_try_no_raise_else_return_then_check_rejected",
            "def run_self_tests():\n    try:\n        pass\n    except Error:\n        pass\n    else:\n        return\n    check('ok', value is True)\n",
            ["missing_selftest_checks"],
        ),
        (
            "target_with_try_global_else_return_then_check_rejected",
            "def run_self_tests(value):\n    try:\n        global flag\n    except Error:\n        pass\n    else:\n        return\n    check('ok', value is True)\n",
            ["missing_selftest_checks"],
        ),
        (
            "target_with_try_functiondef_else_return_then_check_rejected",
            "def run_self_tests(value):\n    try:\n        def helper():\n            pass\n    except Error:\n        pass\n    else:\n        return\n    check('ok', value is True)\n",
            ["missing_selftest_checks"],
        ),
        (
            "target_with_try_classdef_else_return_then_check_rejected",
            "def run_self_tests(value):\n    try:\n        class Helper:\n            pass\n    except Error:\n        pass\n    else:\n        return\n    check('ok', value is True)\n",
            ["missing_selftest_checks"],
        ),
        (
            "target_with_try_for_empty_else_return_then_check_rejected",
            "def run_self_tests(value):\n    try:\n        for item in []:\n            risky()\n    except Error:\n        pass\n    else:\n        return\n    check('ok', value is True)\n",
            ["missing_selftest_checks"],
        ),
        (
            "target_with_try_match_else_return_then_check_rejected",
            "def run_self_tests(value):\n    try:\n        match 1:\n            case 1:\n                pass\n    except Error:\n        pass\n    else:\n        return\n    check('ok', value is True)\n",
            ["missing_selftest_checks"],
        ),
        (
            "target_with_try_classdef_body_match_else_return_then_check_rejected",
            "def run_self_tests(value):\n    try:\n        class Helper:\n            match 1:\n                case 1:\n                    value = 1\n    except Error:\n        pass\n    else:\n        return\n    check('ok', value is True)\n",
            ["missing_selftest_checks"],
        ),
        (
            "target_with_try_classdef_body_try_else_return_then_check_rejected",
            "def run_self_tests(value):\n    try:\n        class Helper:\n            try:\n                value = 1\n            finally:\n                other = 2\n    except Error:\n        pass\n    else:\n        return\n    check('ok', value is True)\n",
            ["missing_selftest_checks"],
        ),
        (
            "target_with_try_classdef_body_try_caught_else_return_then_check_rejected",
            "def run_self_tests(value):\n    try:\n        class Helper:\n            try:\n                raise ValueError('x')\n            except ValueError:\n                value = 1\n    except Error:\n        pass\n    else:\n        return\n    check('ok', value is True)\n",
            ["missing_selftest_checks"],
        ),
        (
            "target_with_try_true_or_risky_else_return_then_check_rejected",
            "def run_self_tests(value):\n    try:\n        True or risky()\n    except Error:\n        pass\n    else:\n        return\n    check('ok', value is True)\n",
            ["missing_selftest_checks"],
        ),
        (
            "target_with_try_empty_dict_else_return_then_check_rejected",
            "def run_self_tests(value):\n    try:\n        {}\n    except Error:\n        pass\n    else:\n        return\n    check('ok', value is True)\n",
            ["missing_selftest_checks"],
        ),
        (
            "target_with_try_literal_add_else_return_then_check_rejected",
            "def run_self_tests(value):\n    try:\n        1 + 2\n    except Error:\n        pass\n    else:\n        return\n    check('ok', value is True)\n",
            ["missing_selftest_checks"],
        ),
        (
            "target_with_try_literal_subscript_else_return_then_check_rejected",
            "def run_self_tests(value):\n    try:\n        (1, 2)[0]\n    except Error:\n        pass\n    else:\n        return\n    check('ok', value is True)\n",
            ["missing_selftest_checks"],
        ),
        (
            "target_with_try_literal_fstring_except_check_rejected",
            "def run_self_tests():\n    try:\n        f'abc'\n    except Error as exc:\n        check('ok', 'needle' in str(exc))\n",
            ["missing_selftest_checks"],
        ),
        (
            "target_with_try_literal_fstring_else_return_then_check_rejected",
            "def run_self_tests(value):\n    try:\n        f'abc'\n    except Error:\n        pass\n    else:\n        return\n    check('ok', value is True)\n",
            ["missing_selftest_checks"],
        ),
        (
            "target_with_try_lambda_except_check_rejected",
            "def run_self_tests():\n    try:\n        lambda: 1\n    except Error as exc:\n        check('ok', 'needle' in str(exc))\n",
            ["missing_selftest_checks"],
        ),
        (
            "target_with_try_lambda_literal_default_except_check_rejected",
            "def run_self_tests():\n    try:\n        lambda item=1: item\n    except Error as exc:\n        check('ok', 'needle' in str(exc))\n",
            ["missing_selftest_checks"],
        ),
        (
            "target_with_try_lambda_else_return_then_check_rejected",
            "def run_self_tests(value):\n    try:\n        lambda: 1\n    except Error:\n        pass\n    else:\n        return\n    check('ok', value is True)\n",
            ["missing_selftest_checks"],
        ),
        (
            "target_with_try_empty_listcomp_except_check_rejected",
            "def run_self_tests():\n    try:\n        [risky() for item in []]\n    except Error as exc:\n        check('ok', 'needle' in str(exc))\n",
            ["missing_selftest_checks"],
        ),
        (
            "target_with_try_range_empty_listcomp_except_check_rejected",
            "def run_self_tests():\n    try:\n        [risky() for item in range(0)]\n    except Error as exc:\n        check('ok', 'needle' in str(exc))\n",
            ["missing_selftest_checks"],
        ),
        (
            "target_with_try_static_listcomp_except_check_rejected",
            "def run_self_tests():\n    try:\n        [1 for item in [1]]\n    except Error as exc:\n        check('ok', 'needle' in str(exc))\n",
            ["missing_selftest_checks"],
        ),
        (
            "target_with_try_empty_genexp_except_check_rejected",
            "def run_self_tests():\n    try:\n        (risky() for item in [])\n    except Error as exc:\n        check('ok', 'needle' in str(exc))\n",
            ["missing_selftest_checks"],
        ),
        (
            "target_with_try_static_setcomp_except_check_rejected",
            "def run_self_tests():\n    try:\n        {1 for item in [1]}\n    except Error as exc:\n        check('ok', 'needle' in str(exc))\n",
            ["missing_selftest_checks"],
        ),
        (
            "target_with_try_static_dictcomp_except_check_rejected",
            "def run_self_tests():\n    try:\n        {1: 2 for item in [1]}\n    except Error as exc:\n        check('ok', 'needle' in str(exc))\n",
            ["missing_selftest_checks"],
        ),
        (
            "target_with_try_empty_listcomp_else_return_then_check_rejected",
            "def run_self_tests(value):\n    try:\n        [risky() for item in []]\n    except Error:\n        pass\n    else:\n        return\n    check('ok', value is True)\n",
            ["missing_selftest_checks"],
        ),
        (
            "target_with_try_literal_unpack_else_return_then_check_rejected",
            "def run_self_tests(value):\n    try:\n        a, b = (1, 2)\n    except Error:\n        pass\n    else:\n        return\n    check('ok', value is True)\n",
            ["missing_selftest_checks"],
        ),
        (
            "target_with_try_annassign_else_return_then_check_rejected",
            "def run_self_tests(value):\n    try:\n        item: int = 1\n    except Error:\n        pass\n    else:\n        return\n    check('ok', value is True)\n",
            ["missing_selftest_checks"],
        ),
        (
            "target_with_try_star_unpack_else_return_then_check_rejected",
            "def run_self_tests(value):\n    try:\n        a, *rest = (1, 2)\n    except Error:\n        pass\n    else:\n        return\n    check('ok', value is True)\n",
            ["missing_selftest_checks"],
        ),
        (
            "target_with_try_namedexpr_literal_except_check_rejected",
            "def run_self_tests():\n    try:\n        (value := 1)\n    except Error as exc:\n        check('ok', 'needle' in str(exc))\n",
            ["missing_selftest_checks"],
        ),
        (
            "target_with_try_namedexpr_literal_else_return_then_check_rejected",
            "def run_self_tests(value):\n    try:\n        (item := 1)\n    except Error:\n        pass\n    else:\n        return\n    check('ok', value is True)\n",
            ["missing_selftest_checks"],
        ),
        (
            "target_with_try_known_raise_disjoint_except_then_check_rejected",
            "def run_self_tests():\n    try:\n        raise ValueError('needle')\n    except TypeError:\n        pass\n    check('ok', value is True)\n",
            ["missing_selftest_checks"],
        ),
        (
            "target_with_try_all_paths_exit_then_check_rejected",
            "def run_self_tests():\n    try:\n        return risky()\n    except Error:\n        return\n    check('ok', value is True)\n",
            ["missing_selftest_checks"],
        ),
        (
            "target_with_try_risky_except_check_allowed",
            "def run_self_tests():\n    try:\n        risky()\n    except Error as exc:\n        check('ok', 'needle' in str(exc))\n",
            [],
        ),
        (
            "target_with_try_false_or_risky_except_check_allowed",
            "def run_self_tests():\n    try:\n        False or risky()\n    except Error as exc:\n        check('ok', 'needle' in str(exc))\n",
            [],
        ),
        (
            "target_with_try_true_and_risky_except_check_allowed",
            "def run_self_tests():\n    try:\n        True and risky()\n    except Error as exc:\n        check('ok', 'needle' in str(exc))\n",
            [],
        ),
        (
            "target_with_try_unhashable_dict_key_except_check_allowed",
            "def run_self_tests():\n    try:\n        {[]: 1}\n    except Error as exc:\n        check('ok', 'needle' in str(exc))\n",
            [],
        ),
        (
            "target_with_try_dict_with_risky_value_except_check_allowed",
            "def run_self_tests():\n    try:\n        {'a': risky()}\n    except Error as exc:\n        check('ok', 'needle' in str(exc))\n",
            [],
        ),
        (
            "target_with_try_listcomp_risky_iter_except_check_allowed",
            "def run_self_tests():\n    try:\n        [item for item in risky()]\n    except Error as exc:\n        check('ok', 'needle' in str(exc))\n",
            [],
        ),
        (
            "target_with_try_listcomp_risky_result_except_check_allowed",
            "def run_self_tests():\n    try:\n        [risky() for item in [1]]\n    except Error as exc:\n        check('ok', 'needle' in str(exc))\n",
            [],
        ),
        (
            "target_with_try_listcomp_bound_name_result_except_check_allowed",
            "def run_self_tests():\n    try:\n        [item for item in [1]]\n    except Error as exc:\n        check('ok', 'needle' in str(exc))\n",
            [],
        ),
        (
            "target_with_try_genexp_risky_outer_iter_except_check_allowed",
            "def run_self_tests():\n    try:\n        (item for item in risky())\n    except Error as exc:\n        check('ok', 'needle' in str(exc))\n",
            [],
        ),
        (
            "target_with_try_setcomp_unhashable_result_except_check_allowed",
            "def run_self_tests():\n    try:\n        {[] for item in [1]}\n    except Error as exc:\n        check('ok', 'needle' in str(exc))\n",
            [],
        ),
        (
            "target_with_try_dictcomp_unhashable_key_except_check_allowed",
            "def run_self_tests():\n    try:\n        {[]: 1 for item in [1]}\n    except Error as exc:\n        check('ok', 'needle' in str(exc))\n",
            [],
        ),
        (
            "target_with_try_literal_divzero_except_check_allowed",
            "def run_self_tests():\n    try:\n        1 / 0\n    except Error as exc:\n        check('ok', 'needle' in str(exc))\n",
            [],
        ),
        (
            "target_with_try_literal_type_error_binop_except_check_allowed",
            "def run_self_tests():\n    try:\n        'a' + 1\n    except Error as exc:\n        check('ok', 'needle' in str(exc))\n",
            [],
        ),
        (
            "target_with_try_risky_binop_except_check_allowed",
            "def run_self_tests():\n    try:\n        risky() + 1\n    except Error as exc:\n        check('ok', 'needle' in str(exc))\n",
            [],
        ),
        (
            "target_with_try_literal_unary_plus_type_error_except_check_allowed",
            "def run_self_tests():\n    try:\n        +'x'\n    except Error as exc:\n        check('ok', 'needle' in str(exc))\n",
            [],
        ),
        (
            "target_with_try_literal_invert_type_error_except_check_allowed",
            "def run_self_tests():\n    try:\n        ~1.0\n    except Error as exc:\n        check('ok', 'needle' in str(exc))\n",
            [],
        ),
        (
            "target_with_try_risky_unary_except_check_allowed",
            "def run_self_tests():\n    try:\n        -risky()\n    except Error as exc:\n        check('ok', 'needle' in str(exc))\n",
            [],
        ),
        (
            "target_with_try_literal_subscript_oob_except_check_allowed",
            "def run_self_tests():\n    try:\n        (1, 2)[9]\n    except Error as exc:\n        check('ok', 'needle' in str(exc))\n",
            [],
        ),
        (
            "target_with_try_literal_subscript_missing_key_except_check_allowed",
            "def run_self_tests():\n    try:\n        {'a': 1}['b']\n    except Error as exc:\n        check('ok', 'needle' in str(exc))\n",
            [],
        ),
        (
            "target_with_try_literal_subscript_type_error_except_check_allowed",
            "def run_self_tests():\n    try:\n        1[0]\n    except Error as exc:\n        check('ok', 'needle' in str(exc))\n",
            [],
        ),
        (
            "target_with_try_dynamic_subscript_except_check_allowed",
            "def run_self_tests(value):\n    try:\n        value[0]\n    except Error as exc:\n        check('ok', 'needle' in str(exc))\n",
            [],
        ),
        (
            "target_with_try_namedexpr_risky_except_check_allowed",
            "def run_self_tests():\n    try:\n        (value := risky())\n    except Error as exc:\n        check('ok', 'needle' in str(exc))\n",
            [],
        ),
        (
            "target_with_try_dynamic_fstring_except_check_allowed",
            "def run_self_tests():\n    try:\n        f'{risky()}'\n    except Error as exc:\n        check('ok', 'needle' in str(exc))\n",
            [],
        ),
        (
            "target_with_try_functiondef_risky_default_except_check_allowed",
            "def run_self_tests():\n    try:\n        def helper(value=risky()):\n            pass\n    except Error as exc:\n        check('ok', 'needle' in str(exc))\n",
            [],
        ),
        (
            "target_with_try_functiondef_decorator_except_check_allowed",
            "def run_self_tests():\n    try:\n        @decorator\n        def helper():\n            pass\n    except Error as exc:\n        check('ok', 'needle' in str(exc))\n",
            [],
        ),
        (
            "target_with_try_functiondef_annotation_except_check_allowed",
            "def run_self_tests():\n    try:\n        def helper(value: int) -> int:\n            return value\n    except Error as exc:\n        check('ok', 'needle' in str(exc))\n",
            [],
        ),
        (
            "target_with_try_classdef_base_except_check_allowed",
            "def run_self_tests(Base):\n    try:\n        class Helper(Base):\n            pass\n    except Error as exc:\n        check('ok', 'needle' in str(exc))\n",
            [],
        ),
        (
            "target_with_try_classdef_decorator_except_check_allowed",
            "def run_self_tests():\n    try:\n        @decorator\n        class Helper:\n            pass\n    except Error as exc:\n        check('ok', 'needle' in str(exc))\n",
            [],
        ),
        (
            "target_with_try_classdef_risky_body_except_check_allowed",
            "def run_self_tests():\n    try:\n        class Helper:\n            value = risky()\n    except Error as exc:\n        check('ok', 'needle' in str(exc))\n",
            [],
        ),
        (
            "target_with_try_classdef_annassign_body_except_check_allowed",
            "def run_self_tests():\n    try:\n        class Helper:\n            value: int = 1\n    except Error as exc:\n        check('ok', 'needle' in str(exc))\n",
            [],
        ),
        (
            "target_with_try_classdef_body_for_risky_except_check_allowed",
            "def run_self_tests():\n    try:\n        class Helper:\n            for item in [1]:\n                risky()\n    except Error as exc:\n        check('ok', 'needle' in str(exc))\n",
            [],
        ),
        (
            "target_with_try_classdef_body_for_annassign_except_check_allowed",
            "def run_self_tests():\n    try:\n        class Helper:\n            for item in [1]:\n                value: risky() = 1\n    except Error as exc:\n        check('ok', 'needle' in str(exc))\n",
            [],
        ),
        (
            "target_with_try_classdef_body_for_dynamic_iter_except_check_allowed",
            "def run_self_tests(items):\n    try:\n        class Helper:\n            for item in items:\n                value = 1\n    except Error as exc:\n        check('ok', 'needle' in str(exc))\n",
            [],
        ),
        (
            "target_with_try_classdef_body_match_risky_body_except_check_allowed",
            "def run_self_tests():\n    try:\n        class Helper:\n            match 1:\n                case 1:\n                    risky()\n    except Error as exc:\n        check('ok', 'needle' in str(exc))\n",
            [],
        ),
        (
            "target_with_try_classdef_body_match_risky_guard_except_check_allowed",
            "def run_self_tests():\n    try:\n        class Helper:\n            match 1:\n                case 1 if risky() and False:\n                    value = 1\n    except Error as exc:\n        check('ok', 'needle' in str(exc))\n",
            [],
        ),
        (
            "target_with_try_classdef_body_try_risky_body_except_check_allowed",
            "def run_self_tests():\n    try:\n        class Helper:\n            try:\n                risky()\n            except Error:\n                pass\n    except Error as exc:\n        check('ok', 'needle' in str(exc))\n",
            [],
        ),
        (
            "target_with_try_classdef_body_try_annassign_except_check_allowed",
            "def run_self_tests():\n    try:\n        class Helper:\n            try:\n                value: risky() = 1\n            except Error:\n                pass\n    except Error as exc:\n        check('ok', 'needle' in str(exc))\n",
            [],
        ),
        (
            "target_with_try_classdef_body_try_finally_risky_except_check_allowed",
            "def run_self_tests():\n    try:\n        class Helper:\n            try:\n                value = 1\n            finally:\n                risky()\n    except Error as exc:\n        check('ok', 'needle' in str(exc))\n",
            [],
        ),
        (
            "target_with_try_classdef_body_try_else_risky_except_check_allowed",
            "def run_self_tests():\n    try:\n        class Helper:\n            try:\n                value = 1\n            except Error:\n                pass\n            else:\n                risky()\n    except Error as exc:\n        check('ok', 'needle' in str(exc))\n",
            [],
        ),
        (
            "target_with_try_classdef_body_try_disjoint_handler_except_check_allowed",
            "def run_self_tests():\n    try:\n        class Helper:\n            try:\n                raise ValueError('x')\n            except TypeError:\n                pass\n    except Error as exc:\n        check('ok', 'needle' in str(exc))\n",
            [],
        ),
        (
            "target_with_try_classdef_body_try_unknown_handler_except_check_allowed",
            "def run_self_tests():\n    try:\n        class Helper:\n            try:\n                raise ValueError('x')\n            except Error:\n                pass\n    except Error as exc:\n        check('ok', 'needle' in str(exc))\n",
            [],
        ),
        (
            "target_with_try_classdef_body_try_caught_handler_risky_except_check_allowed",
            "def run_self_tests():\n    try:\n        class Helper:\n            try:\n                raise ValueError('x')\n            except ValueError:\n                risky()\n    except Error as exc:\n        check('ok', 'needle' in str(exc))\n",
            [],
        ),
        (
            "target_with_try_classdef_body_try_caught_finally_risky_except_check_allowed",
            "def run_self_tests():\n    try:\n        class Helper:\n            try:\n                raise ValueError('x')\n            except ValueError:\n                pass\n            finally:\n                risky()\n    except Error as exc:\n        check('ok', 'needle' in str(exc))\n",
            [],
        ),
        (
            "target_with_try_classdef_body_try_annassign_before_caught_except_check_allowed",
            "def run_self_tests():\n    try:\n        class Helper:\n            try:\n                value: risky() = 1\n                raise ValueError('x')\n            except ValueError:\n                pass\n    except Error as exc:\n        check('ok', 'needle' in str(exc))\n",
            [],
        ),
        (
            "target_with_try_classdef_body_try_match_risky_guard_caught_except_check_allowed",
            "def run_self_tests():\n    try:\n        class Helper:\n            try:\n                match 1:\n                    case 1 if risky() or True:\n                        raise ValueError('x')\n            except ValueError:\n                pass\n    except Error as exc:\n        check('ok', 'needle' in str(exc))\n",
            [],
        ),
        (
            "target_with_try_while_false_risky_else_except_check_allowed",
            "def run_self_tests():\n    try:\n        while False:\n            pass\n        else:\n            risky()\n    except Error as exc:\n        check('ok', 'needle' in str(exc))\n",
            [],
        ),
        (
            "target_with_try_while_true_risky_body_except_check_allowed",
            "def run_self_tests():\n    try:\n        while True:\n            risky()\n    except Error as exc:\n        check('ok', 'needle' in str(exc))\n",
            [],
        ),
        (
            "target_with_try_dynamic_while_except_check_allowed",
            "def run_self_tests(flag):\n    try:\n        while flag:\n            pass\n    except Error as exc:\n        check('ok', 'needle' in str(exc))\n",
            [],
        ),
        (
            "target_with_try_for_empty_risky_else_except_check_allowed",
            "def run_self_tests():\n    try:\n        for item in []:\n            pass\n        else:\n            risky()\n    except Error as exc:\n        check('ok', 'needle' in str(exc))\n",
            [],
        ),
        (
            "target_with_try_for_static_risky_body_except_check_allowed",
            "def run_self_tests():\n    try:\n        for item in [1]:\n            risky()\n    except Error as exc:\n        check('ok', 'needle' in str(exc))\n",
            [],
        ),
        (
            "target_with_try_for_dynamic_iter_except_check_allowed",
            "def run_self_tests(items):\n    try:\n        for item in items:\n            pass\n    except Error as exc:\n        check('ok', 'needle' in str(exc))\n",
            [],
        ),
        (
            "target_with_try_for_static_unpack_target_except_check_allowed",
            "def run_self_tests():\n    try:\n        for first, second in [(1, 2)]:\n            pass\n    except Error as exc:\n        check('ok', 'needle' in str(exc))\n",
            [],
        ),
        (
            "target_with_try_match_risky_body_except_check_allowed",
            "def run_self_tests():\n    try:\n        match 1:\n            case 1:\n                risky()\n    except Error as exc:\n        check('ok', 'needle' in str(exc))\n",
            [],
        ),
        (
            "target_with_try_match_dynamic_subject_except_check_allowed",
            "def run_self_tests(value):\n    try:\n        match value:\n            case 1:\n                pass\n    except Error as exc:\n        check('ok', 'needle' in str(exc))\n",
            [],
        ),
        (
            "target_with_try_match_risky_guard_except_check_allowed",
            "def run_self_tests():\n    try:\n        match 1:\n            case 1 if risky() and False:\n                pass\n    except Error as exc:\n        check('ok', 'needle' in str(exc))\n",
            [],
        ),
        (
            "target_with_try_match_class_pattern_except_check_allowed",
            "def run_self_tests(Helper):\n    try:\n        match 1:\n            case Helper():\n                pass\n    except Error as exc:\n        check('ok', 'needle' in str(exc))\n",
            [],
        ),
        (
            "target_with_try_match_mapping_rest_except_check_allowed",
            "def run_self_tests():\n    try:\n        match {'a': 1, 'b': 2}:\n            case {'a': 1, **rest}:\n                value = 1\n    except Error as exc:\n        check('ok', 'needle' in str(exc))\n",
            [],
        ),
        (
            "target_with_try_lambda_risky_default_except_check_allowed",
            "def run_self_tests():\n    try:\n        lambda item=risky(): item\n    except Error as exc:\n        check('ok', 'needle' in str(exc))\n",
            [],
        ),
        (
            "target_with_try_unpack_noniterable_except_check_allowed",
            "def run_self_tests():\n    try:\n        a, b = 1\n    except Error as exc:\n        check('ok', 'needle' in str(exc))\n",
            [],
        ),
        (
            "target_with_try_unpack_too_short_except_check_allowed",
            "def run_self_tests():\n    try:\n        a, b = (1,)\n    except Error as exc:\n        check('ok', 'needle' in str(exc))\n",
            [],
        ),
        (
            "target_with_try_nested_unpack_mismatch_except_check_allowed",
            "def run_self_tests():\n    try:\n        a, (b, c) = (1, 2)\n    except Error as exc:\n        check('ok', 'needle' in str(exc))\n",
            [],
        ),
        (
            "target_with_try_dynamic_unpack_except_check_allowed",
            "def run_self_tests(items):\n    try:\n        a, b = items\n    except Error as exc:\n        check('ok', 'needle' in str(exc))\n",
            [],
        ),
        (
            "target_with_try_annassign_risky_value_except_check_allowed",
            "def run_self_tests():\n    try:\n        value: int = risky()\n    except Error as exc:\n        check('ok', 'needle' in str(exc))\n",
            [],
        ),
        (
            "target_with_try_annassign_attribute_except_check_allowed",
            "def run_self_tests(obj):\n    try:\n        obj.value: int = 1\n    except Error as exc:\n        check('ok', 'needle' in str(exc))\n",
            [],
        ),
        (
            "target_with_try_annassign_subscript_except_check_allowed",
            "def run_self_tests(items):\n    try:\n        items[0]: int = 1\n    except Error as exc:\n        check('ok', 'needle' in str(exc))\n",
            [],
        ),
        (
            "target_with_try_star_unpack_noniterable_except_check_allowed",
            "def run_self_tests():\n    try:\n        *rest, = 1\n    except Error as exc:\n        check('ok', 'needle' in str(exc))\n",
            [],
        ),
        (
            "target_with_try_star_middle_too_short_except_check_allowed",
            "def run_self_tests():\n    try:\n        a, *rest, b = (1,)\n    except Error as exc:\n        check('ok', 'needle' in str(exc))\n",
            [],
        ),
        (
            "target_with_try_nested_star_unpack_mismatch_except_check_allowed",
            "def run_self_tests():\n    try:\n        a, (*mid, z) = (1, ())\n    except Error as exc:\n        check('ok', 'needle' in str(exc))\n",
            [],
        ),
        (
            "target_with_try_dynamic_star_unpack_except_check_allowed",
            "def run_self_tests(items):\n    try:\n        a, *rest = items\n    except Error as exc:\n        check('ok', 'needle' in str(exc))\n",
            [],
        ),
        (
            "target_with_try_handler_then_check_allowed",
            "def run_self_tests(value):\n    try:\n        return risky()\n    except Error:\n        pass\n    check('ok', value is True)\n",
            [],
        ),
        (
            "target_with_try_known_raise_matching_except_check_allowed",
            "def run_self_tests():\n    try:\n        raise ValueError('needle')\n    except ValueError as exc:\n        check('ok', 'needle' in str(exc))\n",
            [],
        ),
        (
            "target_with_try_known_raise_base_except_check_allowed",
            "def run_self_tests():\n    try:\n        raise ValueError('needle')\n    except Exception as exc:\n        check('ok', 'needle' in str(exc))\n",
            [],
        ),
        (
            "target_with_try_unknown_before_known_raise_except_check_allowed",
            "def run_self_tests():\n    try:\n        risky()\n        raise ValueError('needle')\n    except TypeError as exc:\n        check('ok', 'needle' in str(exc))\n",
            [],
        ),
        (
            "target_with_try_no_raise_fallthrough_check_allowed",
            "def run_self_tests(value):\n    try:\n        value = 1\n    except Error:\n        pass\n    check('ok', value is True)\n",
            [],
        ),
        (
            "target_with_suppressible_raise_loop_else_check_allowed",
            "def run_self_tests(value, guard):\n    for item in [1]:\n        with guard:\n            raise ValueError('maybe suppressed')\n    else:\n        check('ok', value is True)\n",
            [],
        ),
        (
            "target_with_suppressible_assert_loop_else_check_allowed",
            "def run_self_tests(value, guard):\n    for item in [1]:\n        with guard:\n            assert False\n    else:\n        check('ok', value is True)\n",
            [],
        ),
        (
            "target_with_if_true_check_allowed",
            "def run_self_tests(value):\n    if True:\n        check('ok', value is True)\n",
            [],
        ),
        (
            "target_with_namedexpr_true_branch_allowed",
            "def run_self_tests(value):\n    if (flag := True):\n        check('ok', value is True)\n",
            [],
        ),
        (
            "target_with_literal_fstring_true_branch_allowed",
            "def run_self_tests(value):\n    if f'abc':\n        check('ok', value is True)\n",
            [],
        ),
        (
            "target_with_dynamic_fstring_branch_allowed",
            "def run_self_tests(value):\n    if f'{value}':\n        check('ok', value is True)\n",
            [],
        ),
        (
            "target_with_lambda_true_branch_allowed",
            "def run_self_tests(value):\n    if (lambda: 1):\n        check('ok', value is True)\n",
            [],
        ),
        (
            "target_with_lambda_risky_default_branch_allowed",
            "def run_self_tests(value):\n    if (lambda item=risky(): item):\n        check('ok', value is True)\n",
            [],
        ),
        (
            "target_with_namedexpr_unknown_branch_allowed",
            "def run_self_tests(value, flag):\n    if (seen := flag):\n        check('ok', value is True)\n",
            [],
        ),
        (
            "target_with_assert_true_then_check_allowed",
            "def run_self_tests(value):\n    assert True\n    check('ok', value is True)\n",
            [],
        ),
        (
            "target_with_assert_false_message_check_allowed",
            "def run_self_tests(value):\n    assert False, check('ok', value is True)\n",
            [],
        ),
        (
            "target_with_assert_unknown_message_check_allowed",
            "def run_self_tests(value, flag):\n    assert flag, check('ok', value is True)\n",
            [],
        ),
        (
            "target_with_if_not_false_check_allowed",
            "def run_self_tests(value):\n    if not False:\n        check('ok', value is True)\n",
            [],
        ),
        (
            "target_with_static_listcomp_true_branch_allowed",
            "def run_self_tests(value):\n    if [1 for item in [1]]:\n        check('ok', value is True)\n",
            [],
        ),
        (
            "target_with_unknown_filter_listcomp_branch_allowed",
            "def run_self_tests(value, flag):\n    if [1 for item in [1] if flag]:\n        check('ok', value is True)\n",
            [],
        ),
        (
            "target_with_genexp_true_branch_allowed",
            "def run_self_tests(value):\n    if (risky() for item in []):\n        check('ok', value is True)\n",
            [],
        ),
        (
            "target_with_if_true_or_unknown_check_allowed",
            "def run_self_tests(value, flag):\n    if True or flag:\n        check('ok', value is True)\n",
            [],
        ),
        (
            "target_with_if_unknown_or_true_check_allowed",
            "def run_self_tests(value, flag):\n    if flag or True:\n        check('ok', value is True)\n",
            [],
        ),
        (
            "target_with_ifexp_unknown_branch_check_allowed",
            "def run_self_tests(value, flag):\n    result = check('ok', value is True) if flag else None\n",
            [],
        ),
        (
            "target_with_if_literal_eq_true_check_allowed",
            "def run_self_tests(value):\n    if 1 == 1:\n        check('ok', value is True)\n",
            [],
        ),
        (
            "target_with_if_literal_membership_true_check_allowed",
            "def run_self_tests(value):\n    if 'a' in ('a', 'b'):\n        check('ok', value is True)\n",
            [],
        ),
        (
            "target_with_unknown_compare_check_allowed",
            "def run_self_tests(value, flag):\n    if flag == 1:\n        check('ok', value is True)\n",
            [],
        ),
        (
            "target_with_compare_operand_check_allowed",
            "def run_self_tests(value):\n    if 1 == check('ok', value is True):\n        pass\n",
            [],
        ),
        (
            "target_with_compare_chain_after_true_check_allowed",
            "def run_self_tests(value):\n    if 1 == 1 == check('ok', value is True):\n        pass\n",
            [],
        ),
        (
            "target_with_nested_helper_default_check_allowed",
            "def run_self_tests(value):\n    def helper(arg=check('ok', value is True)):\n        pass\n",
            [],
        ),
        (
            "target_with_nested_helper_arg_annotation_check_allowed",
            "def run_self_tests(value):\n    def helper(arg: check('ok', value is True)):\n        pass\n",
            [],
        ),
        (
            "target_with_nested_helper_return_annotation_check_allowed",
            "def run_self_tests(value):\n    def helper() -> check('ok', value is True):\n        pass\n",
            [],
        ),
        (
            "target_with_nested_helper_decorator_check_allowed",
            "def run_self_tests(value):\n    @check('ok', value is True)\n    def helper():\n        pass\n",
            [],
        ),
        (
            "target_with_lambda_default_check_allowed",
            "def run_self_tests(value):\n    helper = lambda arg=check('ok', value is True): None\n",
            [],
        ),
        (
            "target_with_nested_class_body_check_allowed",
            "def run_self_tests(value):\n    class Helper:\n        check('ok', value is True)\n",
            [],
        ),
        (
            "target_with_nested_class_base_check_allowed",
            "def run_self_tests(value):\n    class Helper(check('ok', value is True)):\n        pass\n",
            [],
        ),
        (
            "target_with_nested_class_decorator_check_allowed",
            "def run_self_tests(value):\n    @check('ok', value is True)\n    class Helper:\n        pass\n",
            [],
        ),
        (
            "target_with_nested_class_annotation_check_allowed",
            "def run_self_tests(value):\n    class Helper:\n        field: check('ok', value is True)\n",
            [],
        ),
        (
            "target_with_method_signature_annotation_check_allowed",
            "def run_self_tests(value):\n    class Helper:\n        def method(self, arg: check('ok', value is True)):\n            pass\n",
            [],
        ),
        (
            "target_with_local_annotation_value_check_allowed",
            "def run_self_tests(value):\n    local: object = check('ok', value is True)\n",
            [],
        ),
        (
            "target_with_assign_safe_rhs_subscript_target_check_allowed",
            "def run_self_tests(value, items):\n    items[check('ok', value is True)] = 1\n",
            [],
        ),
        (
            "target_with_assign_dynamic_rhs_subscript_target_check_allowed",
            "def run_self_tests(value, items):\n    items[check('ok', value is True)] = risky()\n",
            [],
        ),
        (
            "target_with_assign_rhs_check_before_static_raise_allowed",
            "def run_self_tests(value, items):\n    items[0] = (check('ok', value is True), [][0])\n",
            [],
        ),
        (
            "target_with_future_annotation_value_bad_annotation_rejected",
            "from __future__ import annotations\n\ndef run_self_tests(value):\n    local: check('bad', True) = check('ok', value is True)\n",
            ["literal_true_check"],
        ),
        (
            "target_with_nested_generator_helper_then_active_check_allowed",
            "def run_self_tests(value):\n    def helper():\n        yield value\n    check('ok', value is True)\n",
            [],
        ),
        (
            "target_with_nonempty_listcomp_check_allowed",
            "def run_self_tests(value):\n    checks = [check('ok', value is True) for item in [1]]\n",
            [],
        ),
        (
            "target_with_nonempty_listcomp_subscript_target_check_allowed",
            "def run_self_tests(value, items):\n    checks = [1 for items[check('ok', value is True)] in [1]]\n",
            [],
        ),
        (
            "target_with_unknown_comp_filter_check_allowed",
            "def run_self_tests(value, flag):\n    checks = [check('ok', value is True) for item in [1] if flag]\n",
            [],
        ),
        (
            "target_with_nonempty_genexp_check_allowed",
            "def run_self_tests(value):\n    all(check('ok', value is True) for item in [1])\n",
            [],
        ),
        (
            "target_with_list_consumed_genexp_check_allowed",
            "def run_self_tests(value):\n    list(check('ok', value is True) for item in [1])\n",
            [],
        ),
        (
            "target_with_lazy_genexp_outer_iter_check_allowed",
            "def run_self_tests(value):\n    gen = (item for item in check('ok', value is True))\n",
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
            "target_with_empty_range_else_check_allowed",
            "def run_self_tests(value):\n    for item in range(0):\n        other('bad', True)\n    else:\n        check('ok', value is True)\n",
            [],
        ),
        (
            "target_with_negative_step_empty_range_else_check_allowed",
            "def run_self_tests(value):\n    for item in range(0, 3, -1):\n        other('bad', True)\n    else:\n        check('ok', value is True)\n",
            [],
        ),
        (
            "target_with_while_true_break_then_check_allowed",
            "def run_self_tests(value):\n    while True:\n        break\n    check('ok', value is True)\n",
            [],
        ),
        (
            "target_with_unknown_while_no_else_check_allowed",
            "def run_self_tests(value, flag):\n    while flag:\n        pass\n    check('ok', value is True)\n",
            [],
        ),
        (
            "target_with_unknown_while_possible_break_else_return_then_check_allowed",
            "def run_self_tests(value, flag, stop):\n    while flag:\n        if stop:\n            break\n    else:\n        return\n    check('ok', value is True)\n",
            [],
        ),
        (
            "target_with_for_continue_else_check_allowed",
            "def run_self_tests(value):\n    for item in [1]:\n        continue\n    else:\n        check('ok', value is True)\n",
            [],
        ),
        (
            "target_with_nonempty_for_subscript_target_check_allowed",
            "def run_self_tests(value, items):\n    for items[check('ok', value is True)] in [1]:\n        pass\n",
            [],
        ),
        (
            "target_with_range_continue_else_check_allowed",
            "def run_self_tests(value):\n    for item in range(1):\n        continue\n    else:\n        check('ok', value is True)\n",
            [],
        ),
        (
            "target_with_possible_break_else_return_then_check_allowed",
            "def run_self_tests(value, flag):\n    for item in [1]:\n        if flag:\n            break\n    else:\n        return\n    check('ok', value is True)\n",
            [],
        ),
        (
            "target_with_nested_loop_possible_break_then_check_allowed",
            "def run_self_tests(value, flag):\n    for outer in [1]:\n        for inner in [1]:\n            if flag:\n                break\n            return\n    check('ok', value is True)\n",
            [],
        ),
        (
            "target_with_try_fallthrough_else_check_allowed",
            "def run_self_tests(value):\n    try:\n        other()\n    except Error:\n        return\n    else:\n        check('ok', value is True)\n",
            [],
        ),
        (
            "target_with_match_wildcard_check_allowed",
            "def run_self_tests(value):\n    match 1:\n        case _:\n            check('ok', value is True)\n",
            [],
        ),
        (
            "target_with_match_matching_literal_check_allowed",
            "def run_self_tests(value):\n    match 'ok':\n        case 'ok':\n            check('ok', value is True)\n",
            [],
        ),
        (
            "target_with_match_or_matching_check_allowed",
            "def run_self_tests(value):\n    match 2:\n        case 1 | 2:\n            check('ok', value is True)\n",
            [],
        ),
        (
            "target_with_match_value_equality_check_allowed",
            "def run_self_tests(value):\n    match True:\n        case 1:\n            check('ok', value is True)\n",
            [],
        ),
        (
            "target_with_match_guard_unknown_check_allowed",
            "def run_self_tests(value, flag):\n    match 1:\n        case 1 if flag:\n            check('ok', value is True)\n",
            [],
        ),
        (
            "target_with_match_risky_truthy_guard_pass_then_check_allowed",
            "def run_self_tests(value):\n    match 1:\n        case 1 if risky() or True:\n            pass\n        case _:\n            return\n    check('ok', value is True)\n",
            [],
        ),
        (
            "target_with_match_unknown_guarded_wildcard_then_check_allowed",
            "def run_self_tests(value, flag):\n    match value:\n        case _ if flag:\n            return\n    check('ok', value is True)\n",
            [],
        ),
        (
            "target_with_match_unknown_wildcard_nonexit_then_check_allowed",
            "def run_self_tests(value):\n    match value:\n        case _:\n            pass\n    check('ok', value is True)\n",
            [],
        ),
        (
            "target_with_match_unknown_no_irrefutable_then_check_allowed",
            "def run_self_tests(value):\n    match value:\n        case 1:\n            return\n    check('ok', value is True)\n",
            [],
        ),
        (
            "target_with_match_sequence_unknown_subject_element_allowed",
            "def run_self_tests(value):\n    match (1, value):\n        case (1, 2):\n            return\n    check('ok', value is True)\n",
            [],
        ),
        (
            "target_with_match_sequence_star_pattern_allowed",
            "def run_self_tests(value):\n    match (1, 2):\n        case (1, *rest):\n            return\n    check('ok', value is True)\n",
            [],
        ),
        (
            "target_with_match_sequence_length_mismatch_allowed",
            "def run_self_tests(value):\n    match (1, 2):\n        case (1, 2, 3):\n            return\n    check('ok', value is True)\n",
            [],
        ),
        (
            "target_with_match_mapping_missing_key_allowed",
            "def run_self_tests(value):\n    match {'a': 1}:\n        case {'b': 2}:\n            return\n    check('ok', value is True)\n",
            [],
        ),
        (
            "target_with_match_mapping_unknown_subject_value_allowed",
            "def run_self_tests(value):\n    match {'a': value}:\n        case {'a': 1}:\n            return\n    check('ok', value is True)\n",
            [],
        ),
        (
            "target_with_match_mapping_rest_allowed",
            "def run_self_tests(value):\n    match {'a': 1, 'b': 2}:\n        case {'a': 1, **rest}:\n            return\n    check('ok', value is True)\n",
            [],
        ),
        ("target_with_tuple_check_allowed", "def run_self_tests(value):\n    checks.append(('ok', value is True))\n", []),
    ]
    if hasattr(ast, "TryStar"):
        target_cases.extend(
            [
                (
                    "target_with_trystar_pass_exceptstar_check_rejected",
                    "def run_self_tests():\n    try:\n        pass\n    except* Error as exc:\n        check('ok', 'needle' in str(exc))\n",
                    ["missing_selftest_checks"],
                ),
                (
                    "target_with_trystar_return_exceptstar_pass_then_check_rejected",
                    "def run_self_tests():\n    try:\n        return\n    except* Error:\n        pass\n    check('ok', value is True)\n",
                    ["missing_selftest_checks"],
                ),
                (
                    "target_with_trystar_risky_exceptstar_check_allowed",
                    "def run_self_tests():\n    try:\n        risky()\n    except* Error as exc:\n        check('ok', 'needle' in str(exc))\n",
                    [],
                ),
            ]
        )
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
        print(
            "Self-test passed: self-test quality detector covers helper-call, keyword-condition, checks.append tuple-append, "
            "truthy-literal, expected exception-text, self-test entrypoint, deferred-scope, unreachable-body, loop/try-else, "
            "literal-range, literal-match, literal-bool, literal-compare, literal-comprehension, "
            "lazy-generator, definition-time/annotation expression, async/generator entrypoint, no-raise try handler/fallthrough, "
            "known-exception try handler/fallthrough, with-control-flow, try-star, assert-statement, no-break infinite-loop, "
            "for-else exit, nested-loop function-exit, unknown-while else-exit, irrefutable-match exit, sequence/mapping-match exit, "
            "risky match-guard exit, loop/comprehension target reachability, assignment target reachability, annotated assignment target reachability, augmented assignment/with context reachability, boolop no-raise, declaration/function/classdef/class-body try/loop/match no-raise, annassign no-raise, assignment-unpack/starred-unpack boundaries, "
            "literal-container/binop/unary/subscript/namedexpr/literal-fstring/lambda/comprehension-expression no-raise, "
            "and missing-check cases"
        )
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
