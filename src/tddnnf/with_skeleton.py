import argparse
import typing as t
from pathlib import Path

import pysmt.operators as op
import pysmt.shortcuts as smt
from pysmt.environment import Environment
from pysmt.environment import get_env
from pysmt.fnode import FNode
from pysmt.formula import FormulaManager
from pysmt.smtlib.script import smtlibscript_from_formula
from pysmt.walkers import IdentityDagWalker
from pysmt.walkers import TreeWalker, handles
from theorydd.solvers.mathsat_partial_extended import MathSATExtendedPartialEnumerator
from wmpy.cli.density import Density

from src import utils
from src.tddnnf import abstraction


class WeightConverterSkeleton(TreeWalker):
    """
    This internal class implements the conversion of a weight function into a weight skeleton,
    as described in "Enhancing SMT-based Weighted Model Integration by structure awareness" (Spallitta et al., 2024).
    """
    mgr: FormulaManager
    branch_condition: list[FNode]  # clause as a list of FNodes
    clauses: list[FNode]  # list of clauses, each clause is an Or of FNodes

    def __init__(self, env: Environment):
        super().__init__(env)
        self.mgr = self.env.formula_manager
        self.branch_condition = []
        self.clauses = []

    def convert(self, weight_func: FNode) -> FNode:
        self.clauses.clear()
        self.walk(weight_func)
        return self.mgr.And(self.clauses)

    @handles(op.SYMBOL)
    @handles(op.CONSTANTS)
    def walk_no_conditions(self, formula: FNode) -> None:
        return

    @handles(op.IRA_OPERATORS)
    def walk_operator(self, formula: FNode) -> t.Generator[FNode]:
        yield from formula.args()

    def walk_ite(self, formula: FNode) -> t.Generator[FNode]:
        psi: FNode
        left: FNode
        right: FNode
        psi, left, right = formula.args()

        # conds -> (psi V not psi)
        # branch_condition = not (conds)
        self.clauses.append(self.mgr.Or(*self.branch_condition, psi, self.mgr.Not(psi)))

        self.branch_condition.append(self.mgr.Not(psi))
        yield left  # recursion on the left branch
        self.branch_condition[-1] = psi
        yield right  # recursion on the right branch
        self.branch_condition.pop()


def main() -> None:
    parser: argparse.ArgumentParser = argparse.ArgumentParser()
    parser.add_argument('--steps', type=Path, required=True)
    parser.add_argument('--density', type=utils.file, required=True)
    parser.add_argument('--mapping', type=Path, required=True)
    parser.add_argument('--phi_n_skeleton', type=Path, required=True)
    args: argparse.Namespace = parser.parse_args()

    utils.setup(args.steps)

    environment: Environment = get_env()

    density: Density = utils.read_density(args.density)
    phi: FNode = density.support

    smt_solver: MathSATExtendedPartialEnumerator = MathSATExtendedPartialEnumerator()
    normalizer: IdentityDagWalker = abstraction.NormalizeWalker(
        converter=smt_solver.get_converter(),
        env=environment,
    )
    necromancer: WeightConverterSkeleton = WeightConverterSkeleton(
        env=environment
    )

    with utils.log('compute skeleton'):
        sk: FNode = necromancer.convert(density.weights)

    with utils.log('normalizing phi'):
        phi = normalizer.walk(phi)

    with utils.log('normalizing skeleton'):
        sk = normalizer.walk(sk)

    phi_n_sk: FNode = smt.And(phi, sk)

    with utils.log('writing mapping'):
        abstraction.write_mapping(phi_n_sk, args.mapping)

    with utils.log('writing phi n skeleton'), open(args.phi_n_skeleton, 'w', encoding='utf-8') as f:
        smtlibscript_from_formula(
            phi_n_sk
        ).serialize(f)


if __name__ == '__main__':
    main()
