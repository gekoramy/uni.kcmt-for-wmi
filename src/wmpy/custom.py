import typing

import networkx as nx
import numpy as np
from pysmt.environment import Environment
from pysmt.fnode import FNode
from pysmt.typing import REAL, BOOL
from wmpy.core.polynomial import PolynomialParser
from wmpy.enumeration.enumerator import Enumerator


class Inequality:

    def __init__(
            self,
            expr: FNode,
            variables: typing.Collection[FNode],
            polynomials: PolynomialParser,
            env: Environment,
    ):
        if expr.is_le() or expr.is_lt():
            self.strict = expr.is_lt()
        else:
            raise ValueError("Not an inequality")

        self.mgr = env.formula_manager

        if len(variables) == 0:
            raise ValueError("Empty variables list")

        p1, p2 = expr.args()
        poly_sub = self.mgr.Plus(p1, self.mgr.Times(self.mgr.Real(-1), p2))
        self.polynomial = Polynomial(poly_sub, variables, polynomials, env)
        assert self.polynomial.degree == 1

    def to_numpy(self) -> tuple[np.ndarray, float]:
        N = len(self.polynomial.variables)
        const_key = tuple(0 for _ in range(N))
        key = lambda i: tuple(1 if j == i else 0 for j in range(N))
        A = [self.polynomial.monomials.get(key(i), 0) for i in range(N)]
        b = -self.polynomial.monomials.get(const_key, 0)
        return np.array(A), b

    def to_pysmt(self) -> FNode:
        op = self.mgr.LT if self.strict else self.mgr.LE
        return op(self.polynomial.to_pysmt(), self.mgr.Real(0))

    def __str__(self) -> str:
        opstr = "<" if self.strict else "<="
        return f"({str(self.polynomial)}) {opstr} 0"

    def __eq__(self, other: typing.Any) -> bool:
        raise NotImplementedError()

    def __hash__(self) -> int:
        raise NotImplementedError()


class Polytope:

    def __init__(
            self,
            expressions: typing.Collection[FNode],
            variables: typing.Collection[FNode],
            polynomials: PolynomialParser,
            env: Environment,
    ):
        self.inequalities: list[Inequality] = []
        for expr in expressions:
            if expr.is_le() or expr.is_lt():
                self.inequalities.append(Inequality(expr, variables, polynomials, env))
            else:
                raise ValueError(f"Can't parse {expr}, not an (in)equality.")

        self.N = len(variables)
        self.mgr = env.formula_manager

    def to_pysmt(self) -> FNode:
        clauses = [ineq.to_pysmt() for ineq in self.inequalities]
        return self.mgr.And(*clauses)

    def to_numpy(self) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        A, B, S = [], [], []
        for ineq in self.inequalities:
            Ab = ineq.to_numpy()
            A.append(Ab[0])
            B.append(Ab[1])
            S.append(1 if ineq.strict else 0)

        return np.array(A), np.array(B), np.array(S)

    def __str__(self) -> str:
        return "\n".join(["[" + str(b) + "]" for b in self.inequalities])


class Polynomial:

    def __init__(
            self,
            expr: FNode,
            variables: typing.Collection[FNode],
            polynomials: PolynomialParser,
            env: Environment,
    ):
        self.monomials = polynomials.walk(expr)
        const_key = tuple(0 for _ in range(len(variables)))
        if const_key in self.monomials and self.monomials[const_key] == 0:
            self.monomials.pop(const_key)
        self.variables = variables
        self.ordered_keys = sorted(self.monomials.keys())
        self.mgr = env.formula_manager

    @property
    def degree(self) -> int:
        if self.is_zero:
            return 0
        else:
            return max(sum(exponents) for exponents in self.monomials)

    @property
    def is_zero(self) -> bool:
        return len(self.monomials) == 0

    def to_numpy(self) -> typing.Callable[[np.ndarray], np.ndarray]:
        return lambda x: np.sum(
            np.array(
                [k * np.prod(np.pow(x, e), axis=1) for e, k in self.monomials.items()]
            ).T,
            axis=1,
        )

    def to_pysmt(self) -> FNode:
        if len(self.monomials) == 0:
            return self.mgr.Real(0)

        pysmt_monos = []
        for key in self.ordered_keys:
            factors = [self.mgr.Real(self.monomials[key])]
            for i, var in enumerate(self.variables):
                if key[i] > 1 or key[i] < 0:
                    factors.append(self.mgr.Pow(var, self.mgr.Real(key[i])))
                elif key[i] == 1:
                    factors.append(var)

            pysmt_monos.append(self.mgr.Times(*factors))

        return self.mgr.Plus(*pysmt_monos)

    def __len__(self) -> int:
        return len(self.monomials)

    def __str__(self) -> str:
        str_monos = []
        for key in self.ordered_keys:
            coeff = f"{self.monomials[key]}"

            term = "*".join(
                [
                    f"{var.symbol_name()}^{key[i]}"
                    # " * ".join([f"{var.symbol_name()}^{key[i]}"
                    for i, var in enumerate(self.variables)
                    if key[i] != 0
                ]
            )

            mono = f"{coeff}*{term}" if term else coeff
            str_monos.append(mono)

        return " + ".join(str_monos)


class AssignmentConverter:

    def __init__(self, enumerator: Enumerator) -> None:
        self.enumerator = enumerator

    def convert(
            self,
            truth_assignment: dict[FNode, bool],
            domain: typing.Collection[FNode],
            polynomials: PolynomialParser,
    ) -> tuple[Polytope, Polynomial]:

        mgr = self.enumerator.env.formula_manager

        uncond_weight = self.enumerator.weights.weight_from_assignment(truth_assignment)

        Gsub: nx.DiGraph = nx.DiGraph()
        constants = {}
        aliases: dict[FNode, FNode] = {}
        inequalities = []
        for atom, truth_value in truth_assignment.items():

            if atom.is_le() or atom.is_lt():
                inequalities.append(atom if truth_value else mgr.Not(atom))
            elif atom.is_equals() and truth_value:
                left, right = atom.args()

                if left.is_symbol(REAL):
                    alias, expr = left, right
                elif right.is_symbol(REAL):
                    alias, expr = right, left
                else:
                    raise ValueError(f"Malformed alias {atom}")

                if alias in aliases:
                    msg = f"Multiple aliases {alias}:\n1) {expr}\n2) {aliases[alias]}"
                    raise ValueError(msg)

                aliases[alias] = expr
                for var in expr.get_free_variables():
                    Gsub.add_edge(alias, var)

                if len(expr.get_free_variables()) == 0:  # constant handled separately
                    constants.update({alias: expr})
            elif atom.is_symbol(BOOL):
                pass
            else:
                raise ValueError(f"Unsupported atom in assignment: {atom}")

        try:
            order = [node for node in nx.topological_sort(Gsub) if node in aliases]
        except nx.NetworkXUnfeasible:
            raise ValueError("Cyclic aliases definition")

        convex_formula = mgr.And(inequalities)
        for alias in order:
            convex_formula = convex_formula.substitute({alias: aliases[alias]})
            uncond_weight = uncond_weight.substitute({alias: aliases[alias]})

        if constants:
            uncond_weight = uncond_weight.substitute(constants)
            convex_formula = convex_formula.substitute(constants)

        inequalities = []
        for literal in convex_formula.args():

            if literal.is_not():
                negated_atom = literal.args()[0]
                left, right = negated_atom.args()
                if negated_atom.is_le():
                    atom = mgr.LT(right, left)
                elif negated_atom.is_lt():
                    atom = mgr.LE(right, left)
                else:
                    raise NotImplementedError("Unhandled case")
            else:
                atom = literal

            if atom.is_le() or atom.is_lt():
                inequalities.append(atom)
            else:
                raise NotImplementedError("Unhandled case")

        polytope = Polytope(inequalities, domain, polynomials, env=self.enumerator.env)
        polynomial = Polynomial(uncond_weight, domain, polynomials, env=self.enumerator.env)

        return polytope, polynomial
