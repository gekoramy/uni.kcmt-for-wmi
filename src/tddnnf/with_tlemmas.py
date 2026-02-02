import argparse
import os
from pathlib import Path

import pysmt.shortcuts as smt
from pysmt.environment import Environment, get_env
from pysmt.fnode import FNode
from pysmt.smtlib.parser import SmtLibParser
from pysmt.smtlib.script import smtlibscript_from_formula
from pysmt.walkers import IdentityDagWalker
from theorydd.solvers.mathsat_partial_extended import MathSATExtendedPartialEnumerator
from wmpy.cli.density import Density

from src import utils
from src.tddnnf import abstraction


def main() -> None:
    parser: argparse.ArgumentParser = argparse.ArgumentParser()
    parser.add_argument('--steps', type=Path, required=True)
    parser.add_argument('--density', type=utils.file, required=True)
    parser.add_argument('--tlemmas_phi', type=utils.file, required=True)
    parser.add_argument('--tlemmas_not_phi', type=utils.file, required=True)
    parser.add_argument('--mapping', type=Path, required=True)
    parser.add_argument('--phi', type=Path, required=True)
    parser.add_argument('--normalized_tlemmas_phi', type=Path, required=True)
    parser.add_argument('--t_reduced_phi', type=Path, required=True)
    parser.add_argument('--t_extended_phi', type=Path, required=True)
    args: argparse.Namespace = parser.parse_args()

    utils.setup(args.steps)

    environment: Environment = get_env()
    parser: SmtLibParser = SmtLibParser(environment=environment)

    density: Density = utils.read_density(args.density)
    phi: FNode = density.support

    smt_solver: MathSATExtendedPartialEnumerator = MathSATExtendedPartialEnumerator()
    normalizer: IdentityDagWalker = abstraction.NormalizeWalker(
        converter=smt_solver.get_converter(),
        env=environment,
    )

    with utils.log('normalizing phi'):
        phi: FNode = normalizer.walk(phi)

    with utils.log('writing mapping'):
        abstraction.write_mapping(phi, args.mapping)

    with utils.log('writing phi'), open(args.phi, 'w', encoding='utf-8') as f:
        smtlibscript_from_formula(
            phi
        ).serialize(f)

    if os.path.getsize(args.tlemmas_phi):
        with utils.log('read tlemmas(phi)'), open(args.tlemmas_phi, 'r', encoding='utf-8') as f:
            tlemmas_phi: FNode = parser.get_script(f).get_last_formula()

        with utils.log('normalizing tlemmas(phi)'):
            tlemmas_phi = normalizer.walk(tlemmas_phi)

        with utils.log('writing normalized tlemmas(phi)'), open(args.normalized_tlemmas_phi, 'w', encoding='utf-8') as f:
            smtlibscript_from_formula(
                tlemmas_phi
            ).serialize(f)

        with utils.log('writing t-reduced phi'), open(args.t_reduced_phi, 'w', encoding='utf-8') as f:
            smtlibscript_from_formula(
                smt.And(phi, *tlemmas_phi.args())
            ).serialize(f)

    if os.path.getsize(args.tlemmas_not_phi):
        with utils.log('read tlemmas(not phi)'), open(args.tlemmas_not_phi, 'r', encoding='utf-8') as f:
            tlemmas_not_phi: FNode = parser.get_script(f).get_last_formula()

        with utils.log('normalizing tlemmas(not phi)'):
            tlemmas_not_phi = normalizer.walk(tlemmas_not_phi)

        with utils.log('writing t-extended phi'), open(args.t_extended_phi, 'w', encoding='utf-8') as f:
            smtlibscript_from_formula(
                smt.Or(phi, *map(smt.Not, tlemmas_not_phi.args()))
            ).serialize(f)


if __name__ == '__main__':
    main()
