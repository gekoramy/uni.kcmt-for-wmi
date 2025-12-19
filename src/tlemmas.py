import argparse
import logging
import typing as t
from dataclasses import dataclass
from pathlib import Path
from time import perf_counter

import pysmt.shortcuts as smt
from pysmt.fnode import FNode
from pysmt.shortcuts import write_smtlib
from theorydd.solvers.lemma_extractor import extract
from theorydd.solvers.mathsat_partial_extended import MathSATExtendedPartialEnumerator
from wmpy.cli.density import Density


@dataclass
class Log:
    step: str

    def __enter__(self):
        self.start: float = perf_counter()

    def __exit__(self, *_):
        dump_step(self.step, perf_counter() - self.start)


def dump_step(step: str, took: float) -> None:
    logger.debug('{"step": "%s", "took": %f}', step, took)


def read_density(file: Path) -> Density:
    with Log(f'parsing density'):
        density = Density.from_file(file.as_posix())
        density.add_bounds()
        return density


def times(whatever: dict[str, dict | float]) -> t.Iterable[tuple[str, float]]:
    """
    >>> list(extract({ 'alpha time': 1.0, 'alpha': { 'beta time': 2.0, 'beta': { 'gamma time': 3.0 } } }))
    [('alpha time', 1.0), ('beta time', 2.0), ('gamma time', 3.0)]
    """

    for key, value in whatever.items():

        match value:
            case float() if 'time' in key:
                yield key, value

            case dict():
                yield from times(value)


if __name__ == '__main__':
    parser: argparse.ArgumentParser = argparse.ArgumentParser()
    parser.add_argument('--steps', type=Path, required=True)
    parser.add_argument('--density', type=Path, required=True)
    parser.add_argument('--tlemmas', type=Path, required=True)
    parser.add_argument('--cores', type=int, required=True)
    args: argparse.Namespace = parser.parse_args()

    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)
    logger.propagate = False
    logger.addHandler(logging.FileHandler(args.steps))

    density: Density = read_density(args.density)
    formula: FNode = smt.And(density.support, smt.Bool(True))

    with Log('extract tlemmas'):
        computations: dict = {}

        tlemmas: list[FNode]
        _, tlemmas, _ = extract(
            formula,
            MathSATExtendedPartialEnumerator(
                computation_logger=computations,
                parallel_procs=args.cores,
            )
        )

        for step, took in times(computations):
            dump_step(step.removesuffix(' time'), took)

    with Log('writing tlemmas'):
        write_smtlib(
            smt.And(tlemmas),
            args.tlemmas
        )
