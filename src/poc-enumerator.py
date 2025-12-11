import functools as fn
import itertools as it
import json
import logging
import os.path
import re
import subprocess
import tempfile
import typing as t
from dataclasses import dataclass
from datetime import timedelta
from io import StringIO
from multiprocessing import Process
from operator import isub
from pathlib import Path
from subprocess import Popen

import numpy as np
import pysmt.environment
import pysmt.shortcuts as s
from pysmt.environment import Environment
from pysmt.fnode import FNode
from pysmt.smtlib.parser import SmtLibParser
from pysmt.typing import BOOL
from theorydd.tdd.theory_sdd import TheorySDD
from theorydd.tddnnf.theory_ddnnf import TheoryDDNNF
from wmpy.cli.density import Density
from wmpy.core.weights import Weights
from wmpy.enumeration import SAEnumerator, Enumerator
from wmpy.integration import Integrator
from wmpy.solvers import WMISolver

from src.sdd2nnf import main as sdd2nnf

formatter = logging.Formatter('%(asctime)s :: %(levelname)-4s :: %(message)s')
handler = logging.StreamHandler()
handler.setFormatter(formatter)

LOG = logging.getLogger(__name__)
LOG.setLevel(logging.DEBUG)
LOG.propagate = False
LOG.addHandler(handler)


@dataclass(frozen=True)
class Log:
    what: str

    def __enter__(self):
        LOG.info(f'enter [{self.what}]')

    def __exit__(self, *_):
        LOG.info(f' exit [{self.what}]')


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
            fn: t.Callable[[Environment, Domain, FNode], t.Iterable[tuple[dict[FNode, bool], int]]]
    ):
        self.env = env
        self.support = support
        self.weights = Weights(weight or self.env.formula_manager.Real(1), env)
        self.fn = fn

    def enumerate(self, phi: FNode) -> t.Iterable[tuple[dict[FNode, bool], int]]:
        return self.fn(self.env, Domain(self.support, self.weights), phi)


def decdnnf(
        env: Environment,
        nnf: Path,
        mapping: Path,
        json2abs: t.Callable[[list[t.Any]], int],
        json2original: t.Callable[[list[t.Any]], str],
) -> t.Generator[dict[bool, t.FrozenSet[FNode]]]:
    parser: SmtLibParser = SmtLibParser(environment=env)

    with open(mapping, 'rt') as f:
        abs2original: dict[int, FNode] = {
            json2abs(obj): parser.get_script(StringIO(json2original(obj))).get_last_formula()
            for obj in json.load(f)
        }

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

    b2regex: dict[bool, re.Pattern] = {
        False: re.compile(r'-(\d+)'),
        True: re.compile(r' (\d+)'),
    }

    for line in decdnnf.stdout:
        model: str = line.strip().removesuffix('0')

        yield {
            boolean: frozenset(abs2original[int(l)] for l in regex.findall(model))
            for boolean, regex in b2regex.items()
        }

    decdnnf.poll()
    assert 0 == decdnnf.returncode


def with_tddnnf(
        env: Environment,
        phi: FNode,
) -> t.Generator[dict[bool, t.FrozenSet[FNode]]]:
    with tempfile.TemporaryDirectory() as path:
        folder: Path = Path(path)

        with Log('pysmt -> t-d-DNNF'):
            TheoryDDNNF(
                phi,
                base_out_path=folder.as_posix(),
                store_tlemmas=True,
                stop_after_allsmt=False,
            )

        yield from decdnnf(
            env,
            folder / 'compilation_output.nnf',
            folder / 'mapping' / 'mapping.json',
            lambda xs: xs[0],
            lambda xs: xs[1],
        )


def with_tssdd(
        env: Environment,
        phi: FNode,
) -> t.Generator[dict[bool, t.FrozenSet[FNode]]]:
    with tempfile.TemporaryDirectory() as path:
        folder: Path = Path(path)

        with Log('pysmt -> t-SDD'):
            tdd: TheorySDD = TheorySDD(
                phi,
                vtree_type='balanced',
            )

            tdd.save_to_folder(folder.as_posix())

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
        ta: t.Callable[[Environment, FNode], t.Generator[dict[bool, t.FrozenSet[FNode]]]],
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
            len(fn.reduce(isub, b2atoms.values(), bools))
        )
        for b2atoms in ta(env, formula)
    )


class NoOpIntegrator:
    def integrate(self, polytope, integrand) -> float:
        return 1

    def integrate_batch(self, convex_integrals) -> np.ndarray:
        return np.ones(len(convex_integrals))


def compute(enumerator: Enumerator, density: Density) -> None:
    integrator: Integrator = NoOpIntegrator()
    LOG.info(
        WMISolver(enumerator, integrator).compute(
            s.Bool(True),
            [v for v in density.domain.keys() if v.symbol_type() == s.REAL]
        )
    )


def sae(density: Density) -> None:
    env: Environment = pysmt.environment.get_env()
    compute(SAEnumerator(density.support, s.Real(1), env), density)


def td4(density: Density) -> None:
    env: Environment = pysmt.environment.get_env()
    compute(FnEnumerator(env, density.support, s.Real(1), fn.partial(enum, with_tddnnf)), density)


def tsdd(density: Density) -> None:
    env: Environment = pysmt.environment.get_env()
    compute(FnEnumerator(env, density.support, s.Real(1), fn.partial(enum, with_tssdd)), density)


if __name__ == "__main__":

    for file in (Path(__file__).parent / 'benchmarks').rglob('*.json', recurse_symlinks=True):

        if 0 == os.path.getsize(file):
            LOG.warning(f'skipping {file}')
            continue

        with Log(f'reading {file.name}'):
            density = Density.from_file(file.as_posix())
            density.add_bounds()

        for name, method in [
            ('sae', sae),
            (' d4', td4),
            ('sdd', tsdd),
        ]:

            with Log(f'solving with {name}'):
                p = Process(target=method, args=(density,))
                p.start()
                p.join(timedelta(minutes=10).total_seconds())
                if p.is_alive():
                    p.terminate()
                    LOG.error("timed out")
                    p.join()
