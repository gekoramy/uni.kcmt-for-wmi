import argparse
from pathlib import Path

import pysmt.shortcuts as smt
from pysmt.environment import Environment
from pysmt.environment import get_env
from pysmt.fnode import FNode
from pysmt.smtlib.script import smtlibscript_from_formula
from pysmt.walkers import IdentityDagWalker
from theorydd.solvers.mathsat_partial_extended import MathSATExtendedPartialEnumerator
from wmpy.cli.density import Density

from src import utils
from src.tddnnf import abstraction
from src.tddnnf import with_skeleton


def main() -> None:
    parser: argparse.ArgumentParser = argparse.ArgumentParser()
    parser.add_argument('--cores', type=int, required=True)
    parser.add_argument('--steps', type=Path, required=True)
    parser.add_argument('--density', type=utils.file, required=True)
    parser.add_argument('--mapping', type=Path, required=True)
    parser.add_argument('--phi_n_skeleton_n_tlemmas', type=Path, required=True)
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
    necromancer: with_skeleton.WeightConverterSkeleton = with_skeleton.WeightConverterSkeleton(env=environment)

    with utils.log('compute skeleton'):
        sk: FNode = necromancer.convert(density.weights)

    with utils.log('extract tlemmas'), utils.computations() as computations:
        smt_solver: MathSATExtendedPartialEnumerator = MathSATExtendedPartialEnumerator(
            computation_logger=computations,
            parallel_procs=args.cores,
        )

        sat: bool = smt_solver.check_all_sat(phi=phi, atoms=list(environment.ao.get_atoms(smt.And(phi, sk))))
        phi_n_sk_n_tlemmas: FNode = smt.And(phi, sk, *smt_solver.get_theory_lemmas()) if sat else smt.FALSE()

    with utils.log('normalizing'):
        phi_n_sk_n_tlemmas = normalizer.walk(phi_n_sk_n_tlemmas)

    with utils.log('writing mapping'):
        abstraction.write_mapping(phi_n_sk_n_tlemmas, args.mapping)

    with utils.log('writing phi n skeleton n tlemmas'), open(args.phi_n_skeleton_n_tlemmas, 'w', encoding='utf-8') as f:
        smtlibscript_from_formula(
            phi_n_sk_n_tlemmas
        ).serialize(f)


if __name__ == '__main__':
    main()
