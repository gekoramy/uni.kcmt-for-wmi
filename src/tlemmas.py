import argparse
from pathlib import Path

import pysmt.shortcuts as smt
from pysmt.fnode import FNode
from pysmt.shortcuts import write_smtlib
from theorydd.solvers.lemma_extractor import extract
from theorydd.solvers.mathsat_partial_extended import MathSATExtendedPartialEnumerator
from wmpy.cli.density import Density

from src import utils


def main() -> None:
    parser: argparse.ArgumentParser = argparse.ArgumentParser()
    parser.add_argument('--steps', type=Path, required=True)
    parser.add_argument('--density', type=Path, required=True)
    parser.add_argument('--tlemmas', type=Path, required=True)
    parser.add_argument('--cores', type=int, required=True)
    args: argparse.Namespace = parser.parse_args()

    utils.setup(args.steps)

    density: Density = utils.read_density(args.density)
    formula: FNode = smt.And(density.support, smt.Bool(True))

    with utils.log('extract tlemmas'), utils.computations() as computations:
        tlemmas: list[FNode]
        _, tlemmas, _ = extract(
            formula,
            MathSATExtendedPartialEnumerator(
                computation_logger=computations,
                parallel_procs=args.cores,
            )
        )

    with utils.log('writing tlemmas'):
        write_smtlib(
            smt.And(tlemmas),
            args.tlemmas
        )


if __name__ == '__main__':
    main()
