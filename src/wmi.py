import argparse
import functools as fn
import itertools as it
import json
import logging
import re
import subprocess
import sys
import tempfile
import typing as t
from dataclasses import dataclass
from io import StringIO
from pathlib import Path
from subprocess import Popen
from time import perf_counter

import numpy as np
import pysmt.environment
import pysmt.shortcuts as s
from pysmt.environment import Environment
from pysmt.fnode import FNode
from pysmt.smtlib.parser import SmtLibParser
from pysmt.typing import BOOL
from theorydd.solvers.mathsat_partial_extended import MathSATExtendedPartialEnumerator
from theorydd.tdd.theory_sdd import TheorySDD
from theorydd.tddnnf.theory_ddnnf import TheoryDDNNF
from wmpy.cli.density import Density
from wmpy.core import Polytope, Polynomial
from wmpy.core.weights import Weights
from wmpy.enumeration import SAEnumerator, Enumerator
from wmpy.integration import Integrator, LattEIntegrator, ParallelWrapper, CacheWrapper
from wmpy.solvers import WMISolver

from src.sdd2nnf import main as sdd2nnf

b2regex: frozenset[tuple[bool, re.Pattern]] = frozenset([
    (False, re.compile(r'-(\d+)')),
    (True, re.compile(r' (\d+)')),
])


@dataclass
class Log:
    step: str

    def __enter__(self):
        self.start: float = perf_counter()

    def __exit__(self, *_):
        dump_step(self.step, perf_counter() - self.start)


def dump_step(step: str, took: float) -> None:
    logger.debug('{"step": "%s", "took": %f}', step, took)


def times(whatever: dict[str, dict | float]) -> t.Iterable[tuple[str, float]]:
    """
    >>> list(times({ 'alpha time': 1.0, 'alpha': { 'beta time': 2.0, 'beta': { 'gamma time': 3.0 } } }))
    [('alpha time', 1.0), ('beta time', 2.0), ('gamma time', 3.0)]
    """

    for key, value in whatever.items():

        match value:
            case float() if 'time' in key:
                yield key, value

            case dict():
                yield from times(value)


class NoOpIntegrator:
    def integrate(self, *_) -> float:
        return 1

    def integrate_batch(self, convex_integrals) -> np.ndarray:
        return np.ones(len(convex_integrals))


@dataclass
class Domain:
    chi: FNode
    weights: Weights


class FnEnumerator:

    def __init__(
            self,
            env: Environment,
            support: FNode,
            weight: FNode | None,
            fun: t.Callable[[Environment, Domain, FNode], t.Iterable[tuple[dict[FNode, bool], int]]]
    ):
        self.env = env
        self.support = support
        self.weights = Weights(weight or self.env.formula_manager.Real(1), env)
        self.fun = fun

    def enumerate(self, phi: FNode) -> t.Iterable[tuple[dict[FNode, bool], int]]:
        yield from self.fun(self.env, Domain(self.support, self.weights), phi)


class LogEnumerator:

    def __init__(self, enumerator: Enumerator):
        self.enum = enumerator
        self.env = self.enum.env
        self.support = self.enum.support
        self.weights = self.enum.weights

    def enumerate(self, query: FNode) -> t.Iterable[tuple[dict[FNode, bool], int]]:
        with Log('enumerating'):
            yield from self.enum.enumerate(query)


class LogIntegrator:

    def __init__(self, integrator: Integrator):
        self.integrator = integrator

    def integrate(self, polytope: Polytope, polynomial: Polynomial) -> float:
        with Log("integrate"):
            return self.integrator.integrate(polytope, polynomial)

    def integrate_batch(
            self, convex_integrals: t.Collection[tuple[Polytope, Polynomial]]
    ) -> np.ndarray:
        with Log("integrate batch"):
            return self.integrator.integrate_batch(convex_integrals)


def decdnnf(
        env: Environment,
        nnf: Path,
        mapping: Path,
        json2abs: t.Callable[[list[t.Any]], int],
        json2original: t.Callable[[list[t.Any]], str],
) -> t.Generator[dict[bool, list[FNode]]]:
    parser: SmtLibParser = SmtLibParser(environment=env)

    with Log('parsing abstraction'), open(mapping, 'rt') as f:
        abs2original: dict[int, FNode] = {
            json2abs(obj): parser.get_script(StringIO(json2original(obj))).get_last_formula()
            for obj in json.load(f)
        }

    with Log('decdnnf_rs'):
        decdnnf: Popen[str] = subprocess.Popen(
            args=[
                'decdnnf_rs',
                'model-enumeration',
                '--compact-free-vars',
                '--logging-level=off',
                f'--input={nnf.as_posix()}'
            ],
            stdout=subprocess.PIPE,
            text=True,
        )

        for line in decdnnf.stdout:
            model: str = line.strip().removesuffix('0')

            yield {
                boolean: list(abs2original[int(l)] for l in regex.findall(model))
                for boolean, regex in b2regex
            }

        decdnnf.poll()
        assert 0 == decdnnf.returncode


def with_d4(
        env: Environment,
        phi: FNode,
        tlemmas: Path | None = None,
) -> t.Generator[dict[bool, list[FNode]]]:
    with tempfile.TemporaryDirectory() as path:
        folder: Path = Path(path)

        computations: dict = {}

        with Log('pysmt -> t-d-DNNF'):
            TheoryDDNNF(
                phi,
                load_lemmas=tlemmas.as_posix() if tlemmas else None,
                sat_result=True if tlemmas else None,
                base_out_path=folder.as_posix(),
                store_tlemmas=True,
                stop_after_allsmt=False,
                computation_logger=computations,
                solver=MathSATExtendedPartialEnumerator(
                    computation_logger=computations,
                    parallel_procs=cores,
                ),
            )

            for step, took in times(computations):
                dump_step(step.removesuffix(' time'), took)

        yield from decdnnf(
            env,
            folder / 'compilation_output.nnf',
            folder / 'mapping' / 'mapping.json',
            lambda xs: xs[0],
            lambda xs: xs[1],
        )


def with_sdd(
        env: Environment,
        phi: FNode,
        tlemmas: Path | None = None,
) -> t.Generator[dict[bool, list[FNode]]]:
    with tempfile.TemporaryDirectory() as path:
        folder: Path = Path(path)

        with Log('pysmt -> t-SDD'):
            computations: dict = {}

            tdd: TheorySDD = TheorySDD(
                phi,
                load_lemmas=tlemmas.as_posix() if tlemmas else None,
                vtree_type='balanced',
                computation_logger=computations,
                solver=MathSATExtendedPartialEnumerator(
                    computation_logger=computations,
                    parallel_procs=cores,
                ),
            )

            for step, took in times(computations):
                dump_step(step.removesuffix(' time'), took)

        with Log('extract sdd'):
            tdd.save_to_folder(folder.as_posix())

        with Log('sdd -> nnf'):
            sdd: Path = folder / 'sdd.sdd'
            nnf: Path = folder / 'sdd.nff'

            sdd2nnf(sdd, nnf)

        yield from decdnnf(
            env,
            nnf,
            folder / 'abstraction.json',
            lambda xs: xs[1],
            lambda xs: xs[0],
        )


def enum(
        ta: t.Callable[[Environment, FNode], t.Generator[dict[bool, list[FNode]]]],
        env: Environment,
        domain: Domain,
        phi: FNode,
) -> t.Generator[tuple[dict[FNode, bool], int]]:
    formula: FNode = env.formula_manager.And(domain.chi, phi)

    bools: t.FrozenSet[FNode] = frozenset(
        a
        for a in it.chain(domain.weights.get_atoms(), env.ao.get_atoms(formula))
        if a.is_symbol(BOOL)
    )

    yield from (
        (
            {
                atom: b
                for b, atoms in b2atoms.items()
                for atom in atoms
            },
            len(fn.reduce(lambda acc, xs: acc.difference(xs), b2atoms.values(), bools))
        )
        for b2atoms in ta(env, formula)
    )


def read_density(file: Path) -> Density:
    with Log(f'parsing density'):
        density = Density.from_file(file.as_posix())
        density.add_bounds()
        return density


def file(arg: str) -> Path:
    if not (path := Path(arg)).is_file():
        raise FileNotFoundError(path)

    return path


if __name__ == '__main__':

    parser: argparse.ArgumentParser = argparse.ArgumentParser()
    parser.add_argument('--steps', type=Path, required=True)
    parser.add_argument('--enumerator', type=str, choices=['sae', 'd4', 'sdd'], required=True)
    parser.add_argument('--integrator', type=str, choices=['latte', 'noop'], required=True)
    parser.add_argument('--parallel', action='store_true')
    parser.add_argument('--cached', action='store_true')
    parser.add_argument('--density', type=file, required=True)
    parser.add_argument('--tlemmas', type=file, required=False)
    parser.add_argument('--cores', type=int, required=True)
    args: argparse.Namespace = parser.parse_args()

    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)
    logger.propagate = False
    logger.addHandler(logging.FileHandler(args.steps))

    cores: int = args.cores

    env: Environment = pysmt.environment.get_env()
    density: Density = read_density(args.density)

    enumerator: Enumerator
    match args.enumerator:
        case 'sae':
            enumerator = SAEnumerator(density.support, s.Real(1), env)

        case 'd4':
            enumerator = FnEnumerator(
                env,
                density.support,
                s.Real(1),
                fn.partial(enum, fn.partial(with_d4, tlemmas=args.tlemmas))
            )

        case 'sdd':
            enumerator = FnEnumerator(
                env,
                density.support,
                s.Real(1),
                fn.partial(enum, fn.partial(with_sdd, tlemmas=args.tlemmas))
            )

        case _:
            raise argparse.ArgumentError()

    integrator: Integrator
    match args.integrator:
        case 'latte':
            integrator = LattEIntegrator()

        case 'noop':
            integrator = NoOpIntegrator()

        case _:
            raise RuntimeError()

    if args.parallel:
        integrator = ParallelWrapper(integrator, cores)

    if args.cached:
        integrator = CacheWrapper(integrator)

    with Log('total'):
        result = WMISolver(LogEnumerator(enumerator), LogIntegrator(integrator)).compute(
            s.Bool(True),
            [v for v in density.domain.keys() if v.symbol_type() == s.REAL]
        )

    json.dump(result, sys.stdout)
    sys.stdout.write('\n')
