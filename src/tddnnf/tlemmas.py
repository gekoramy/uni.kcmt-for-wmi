import argparse
from pathlib import Path

import pysmt.shortcuts as smt
from pysmt.fnode import FNode
from pysmt.smtlib.script import smtlibscript_from_formula
from theorydd.solvers.mathsat_partial_extended import MathSATExtendedPartialEnumerator
from wmpy.cli.density import Density

from src import utils


def main() -> None:
    parser: argparse.ArgumentParser = argparse.ArgumentParser()
    parser.add_argument('--cores', type=int, required=True)
    parser.add_argument('--steps', type=Path, required=True)
    parser.add_argument('--density', type=utils.file, required=True)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--phi', action='store_true')
    group.add_argument('--not_phi', action='store_true')
    parser.add_argument('--tlemmas', type=Path, required=True)
    args: argparse.Namespace = parser.parse_args()

    utils.setup(args.steps)

    density: Density = utils.read_density(args.density)
    phi: FNode = density.support

    if args.not_phi:
        phi = smt.Not(phi)

    with utils.log('extract tlemmas'), utils.computations() as computations:
        smt_solver: MathSATExtendedPartialEnumerator = MathSATExtendedPartialEnumerator(
            computation_logger=computations,
            parallel_procs=args.cores,
        )

        sat: bool = smt_solver.check_all_sat(phi=phi)
        tlemmas: FNode = smt.And(smt_solver.get_theory_lemmas()) if sat else smt.FALSE()

    with utils.log('writing tlemmas'), open(args.tlemmas, 'w', encoding='utf-8') as f:
        smtlibscript_from_formula(tlemmas).serialize(f)


if __name__ == '__main__':
    main()
