import argparse
import functools as ft
import itertools as it
import json
import sys
import typing as t
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pysmt.shortcuts as smt
from numpy.typing import ArrayLike
from pysmt.environment import Environment, get_env
from pysmt.fnode import FNode
from wmpy.cli.density import Density
from wmpy.core.polynomial import PolynomialParser
from wmpy.core.weights import Weights
from wmpy.enumeration import Enumerator
from wmpy.integration import Integrator, LattEIntegrator, ParallelWrapper, CacheWrapper

import src.decdnnf.enumerator_baseline as decdnnf_baseline
from src import utils
from src.sae import sae
from src.wmpy import custom


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
        with utils.log('enumerating'):
            yield from self.enum.enumerate(query)


def enum(
        ta: t.Callable[[Environment, FNode], t.Generator[dict[bool, list[FNode]]]],
        env: Environment,
        domain: Domain,
        phi: FNode,
) -> t.Generator[tuple[dict[FNode, bool], int]]:
    formula: FNode = env.formula_manager.And(domain.chi, phi)

    A: t.FrozenSet[FNode] = frozenset(
        a
        for a in it.chain(domain.weights.get_atoms(), env.ao.get_atoms(formula))
        if a.is_symbol(smt.BOOL)
    )

    yield from (
        (
            {
                atom: b
                for b, atoms in b2atoms.items()
                for atom in atoms
            },
            len(
                A
                .difference(b2atoms[False])
                .difference(b2atoms[True])
            )
        )
        for b2atoms in ta(env, formula)
    )


def wmi(
        enumerator: Enumerator,
        integrator: Integrator | None,
        query: FNode,
        domain: t.Collection[FNode],
) -> dict[str, ArrayLike]:
    enumerator = LogEnumerator(enumerator)
    converter = custom.AssignmentConverter(enumerator)
    polynomials = PolynomialParser(domain)

    distinct_by: dict[t.Literal['x', 'A'], set[frozenset[tuple[FNode, bool]]]] = {
        'x': set(),
        'A': set(),
    }

    convex_integrals: list[tuple[custom.Polytope, custom.Polynomial]] = []
    n_unassigned_bools: list[int] = []
    for truth_assignment, nub in enumerator.enumerate(query):
        x, A = [], []
        for atom, boolean in truth_assignment.items():
            (x, A)[atom.is_symbol(smt.BOOL)].append((atom, boolean))
        distinct_by['x'].add(frozenset(x))
        distinct_by['A'].add(frozenset(A))

        convex_integrals.append(converter.convert(truth_assignment, domain, polynomials))
        n_unassigned_bools.append(nub)

    result: dict[str, ArrayLike] = {
        'distinct_by_x': len(distinct_by['x']),
        'distinct_by_A': len(distinct_by['A']),
        'npolys': len(convex_integrals),
        'nuniquepolys': len(set(it.starmap(CacheWrapper._compute_key, convex_integrals))),
    }

    if integrator is None:
        return result

    with utils.log('integrate batch'):
        volume: np.ndarray[tuple[t.Literal[1]], np.dtype[np.float64]] = np.dot(
            integrator.integrate_batch(convex_integrals),
            2 ** np.array(n_unassigned_bools, dtype=np.float64),
        )

    return {
        **result,
        'wmi': volume,
    }


def main() -> None:
    with utils.use(argparse.ArgumentParser()) as parser:
        parser.add_argument('--steps', type=Path, required=True)
        parser.add_argument('--integrator', type=str, choices=['latte', 'noop'], required=True)
        parser.add_argument('--parallel', action='store_true')
        parser.add_argument('--cached', action='store_true')
        parser.add_argument('--density', type=utils.file, required=True)
        parser.add_argument('--cores', type=int, required=True)

        with utils.use(parser.add_subparsers(dest='enumerator', required=True)) as sub:
            sub.add_parser('sae')

            with utils.use(sub.add_parser('decdnnf')) as subparser:
                subparser.add_argument('--models', type=utils.file, required=True)
                subparser.add_argument('--mapping', type=utils.file, required=True)

        args: argparse.Namespace = parser.parse_args()

    utils.setup(args.steps)

    env: Environment = get_env()
    density: Density = utils.read_density(args.density)

    enumerator: Enumerator
    match args.enumerator:
        case 'sae':
            enumerator = sae.SAEnumerator(density.support, smt.Real(1), env)

        case 'decdnnf':
            ta: t.Callable[[], t.Generator[dict[bool, list[FNode]]]] = lambda: decdnnf_baseline.enum(
                env,
                decdnnf_baseline.Arguments(
                    cores=args.cores,
                    models=args.models,
                    mapping=args.mapping
                )
            )

            enumerator = FnEnumerator(
                env,
                density.support,
                smt.Real(1),
                ft.partial(enum, lambda _1, _2: ta())
            )

    integrator: Integrator | None
    match args.integrator:
        case 'latte':
            integrator: Integrator = LattEIntegrator()

            if args.parallel and args.cores > 1:
                integrator = ParallelWrapper(integrator, args.cores)

            if args.cached:
                integrator = CacheWrapper(integrator)

        case 'noop':
            integrator = None

        case _:
            raise RuntimeError()

    json.dump(
        wmi(
            enumerator=enumerator,
            integrator=integrator,
            query=smt.TRUE(),
            domain=[a for a in density.domain.keys() if a.is_symbol(smt.REAL)],
        ),
        sys.stdout,
    )
    sys.stdout.write('\n')


if __name__ == '__main__':
    main()
