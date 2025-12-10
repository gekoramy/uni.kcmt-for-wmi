# %%
import functools as fn
import itertools as it
import json
import logging
import os.path
import re
import subprocess
import tempfile
import typing as t
from concurrent.futures import ThreadPoolExecutor, Future, CancelledError
from dataclasses import dataclass
from io import StringIO
from operator import isub
from pathlib import Path
from subprocess import Popen

import pysmt.environment
import pysmt.shortcuts as s
from pysmt.environment import Environment
from pysmt.fnode import FNode
from pysmt.smtlib.parser import SmtLibParser
from pysmt.typing import BOOL
from theorydd.tdd.theory_sdd import TheorySDD
from theorydd.tddnnf.theory_ddnnf import TheoryDDNNF
from wmpy.core.weights import Weights
from wmpy.enumeration import SAEnumerator
from wmpy.integration import LattEIntegrator, Integrator
from wmpy.solvers import WMISolver

from src.parse import nested_to_smt
from src.sdd2nnf import main as sdd2nnf


# %%
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


# %%
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


# %%
@dataclass(frozen=True)
class Log:
    what: str

    def __enter__(self):
        logging.info(f'enter [{self.what}]')

    def __exit__(self, *_):
        logging.info(f' exit [{self.what}]')


logging.basicConfig(
    format='%(asctime)s :: %(levelname)-4s :: %(message)s',
    level=logging.INFO,
)

# %%
env: Environment = pysmt.environment.get_env()
integrator: Integrator = (LattEIntegrator())

cwd: Path = Path(__file__).parent
parser: SmtLibParser = SmtLibParser(environment=env)

# %%
for file in it.islice(list((cwd / 'benchmarks' / 'structured').rglob('*.json')), 1, 2):

    if 0 == os.path.getsize(file):
        print(f'skipping {file}')
        continue

    with Log(f'reading {file.name}'):

        with open(file, 'rt') as f:
            instance = json.load(f)

        domain: tuple[str, t.Literal['real'] | t.Literal['bool'], tuple[int, int] | None] = instance['domain']
        support: FNode = nested_to_smt(instance['formula'])
        w = s.Real(1)

        A: list[s.Symbol] = []
        x: list[s.Symbol] = []
        for t in domain:
            match t:
                case name, 'real', [lower, upper]:
                    symbol = s.Symbol(name, s.REAL)
                    x.append(symbol)
                    support = env.formula_manager.And(support, s.LE(s.Real(lower), symbol), s.LE(symbol, s.Real(upper)))

                case name, 'bool', None:
                    symbol = s.Symbol(name, s.BOOL)
                    A.append(symbol)

                case _:
                    raise RuntimeError(f'unknown tuple : {t}')

    with ThreadPoolExecutor(max_workers=1) as executor:

        for name, enumerator in [
            ('sae', SAEnumerator(support, w, env)),
            (' d4', FnEnumerator(env, support, w, fn.partial(enum, with_tddnnf))),
            ('sdd', FnEnumerator(env, support, w, fn.partial(enum, with_tssdd))),
        ]:
            with Log(f'solwing with {name}'):
                try:
                    future: Future = executor.submit(lambda : WMISolver(enumerator, integrator).compute(s.Bool(True), A + x))
                    logging.info(future.result(5 * 60))
                except CancelledError:
                    logging.error("timed out")
