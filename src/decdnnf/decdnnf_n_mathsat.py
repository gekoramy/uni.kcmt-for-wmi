import argparse
import multiprocessing as mp
import typing as t
from pathlib import Path
from typing import Generator

import pysmt.shortcuts as smt
from pysmt.environment import get_env, Environment
from pysmt.fnode import FNode
from pysmt.logics import LRA
from pysmt.solvers import msat

from src import utils
from src.decdnnf import decdnnf
from src.tddnnf import with_tlemmas

_i2atom: with_tlemmas.i2atom
_solver: msat.MathSAT5Solver


def _init_worker(i2atom: Path) -> None:
    global _i2atom, _solver
    env: Environment = get_env()
    _i2atom = with_tlemmas.read_mapping(env=env, mapping=i2atom)
    _solver = msat.MathSAT5Solver(environment=env, logic=LRA)


def t_atoms(ixs: t.Iterable[int]) -> Generator[FNode]:
    global _i2atom
    for ix in ixs:
        a: FNode = _i2atom[ix]
        if not a.is_symbol(smt.BOOL):
            yield a


def if_satisfiable(model: dict[bool, list[int]]) -> dict[bool, list[int]] | None:
    global _solver
    _solver.push()
    is_sat: bool = _solver.solve((
        *t_atoms(model[True]),
        *(smt.Not(a) for a in t_atoms(model[False])),
    ))
    _solver.pop()
    return model if is_sat else None


def main() -> None:
    with utils.use(argparse.ArgumentParser()) as parser:
        parser.add_argument('--cores', type=int, required=True)
        parser.add_argument('--mapping', type=utils.file, required=True)
        parser.add_argument('--phi', type=utils.file, required=True)
        parser.add_argument('--output', type=Path, required=True)
        args: argparse.Namespace = parser.parse_args()

    assert args.cores > 1

    cores4decdnnf: int = 1
    cores4mathsat: int = args.cores - cores4decdnnf

    with mp.get_context('spawn').Pool(cores4mathsat, initializer=_init_worker, initargs=(args.mapping,)) as pool:
        models: t.Generator[dict[bool, list[int]]] = decdnnf.pipe(cores4decdnnf, args.phi)

        t_sat: t.Iterator[dict[bool, list[int]] | None] = pool.imap_unordered(
            if_satisfiable,
            models,
            chunksize=cores4mathsat,
        )

        decdnnf.write_models(args.output, [mu for mu in t_sat if mu])


if __name__ == '__main__':
    main()
