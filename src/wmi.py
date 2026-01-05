import argparse
import functools as fn
import itertools as it
import json
import sys
import typing as t
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pysmt.environment
import pysmt.shortcuts as s
from pysmt.environment import Environment
from pysmt.fnode import FNode
from pysmt.typing import BOOL
from wmpy.cli.density import Density
from wmpy.core import Polytope, Polynomial
from wmpy.core.weights import Weights
from wmpy.enumeration import SAEnumerator, Enumerator
from wmpy.integration import Integrator, LattEIntegrator, ParallelWrapper, CacheWrapper
from wmpy.solvers import WMISolver

import src.decdnnf.enumerator_baseline as decdnnf_baseline
import src.decdnnf.enumerator_two_steps as decdnnf_two_steps
from src import utils


class NoOpIntegrator(Integrator):
    def integrate(self, *_) -> float:
        return 1

    def integrate_batch(self, convex_integrals) -> np.ndarray:
        return np.ones(len(convex_integrals))


class LogIntegrator(Integrator):

    def __init__(self, integrator: Integrator):
        self.integrator = integrator

    def integrate(self, polytope: Polytope, polynomial: Polynomial) -> float:
        with utils.log("integrate"):
            return self.integrator.integrate(polytope, polynomial)

    def integrate_batch(
            self, convex_integrals: t.Collection[tuple[Polytope, Polynomial]]
    ) -> np.ndarray:
        with utils.log("integrate batch"):
            return self.integrator.integrate_batch(convex_integrals)


@dataclass
class Domain:
    chi: FNode
    weights: Weights


class FnEnumerator():

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


class LogEnumerator():

    def __init__(self, enumerator: Enumerator):
        self.enum = enumerator
        self.env = self.enum.env
        self.support = self.enum.support
        self.weights = self.enum.weights
        self.models: int = 0

    def enumerate(self, query: FNode) -> t.Iterable[tuple[dict[FNode, bool], int]]:
        with utils.log('enumerating'):
            models = list(self.enum.enumerate(query))

        self.models = len(models)
        yield from models


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
            len(
                bools
                .difference(b2atoms[False])
                .difference(b2atoms[True])
            )
        )
        for b2atoms in ta(env, formula)
    )


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

            with utils.use(sub.add_parser('decdnnf_baseline')) as subparser:
                subparser.add_argument('--nnf', type=utils.file, required=True)
                subparser.add_argument('--mapping', type=utils.file, required=True)

            with utils.use(sub.add_parser('decdnnf_two_steps')) as subparser:
                subparser.add_argument('--nnf_exists_x', type=utils.file, required=True)
                subparser.add_argument('--mapping', type=utils.file, required=True)

                with utils.use(subparser.add_subparsers(dest='using', required=True)) as subsub:
                    with utils.use(subsub.add_parser('d4')) as subsubparser:
                        subsubparser.add_argument('--nnf', type=utils.file, required=True)

                    with utils.use(subsub.add_parser('sdd')) as subsubparser:
                        subsubparser.add_argument('--vtree', type=utils.file, required=True)
                        subsubparser.add_argument('--sdd', type=utils.file, required=True)

        args: argparse.Namespace = parser.parse_args()

    utils.setup(args.steps)

    env: Environment = pysmt.environment.get_env()
    density: Density = utils.read_density(args.density)

    integrator: Integrator
    match args.integrator:
        case 'latte':
            integrator = LattEIntegrator()

        case 'noop':
            integrator = NoOpIntegrator()

        case _:
            raise RuntimeError()

    if args.parallel:
        integrator = ParallelWrapper(integrator, args.cores)

    if args.cached:
        integrator = CacheWrapper(integrator)

    enumerator: Enumerator
    match args.enumerator:
        case 'sae':
            enumerator = SAEnumerator(density.support, s.Real(1), env)

        case 'decdnnf_baseline' | 'decdnnf_two_steps':

            ta: t.Callable[[], t.Generator[dict[bool, list[FNode]]]]
            match args.enumerator:
                case 'decdnnf_baseline':
                    ta = lambda: decdnnf_baseline.enum(
                        env,
                        decdnnf_baseline.Arguments(
                            cores=args.cores,
                            nnf=args.nnf,
                            mapping=args.mapping
                        )
                    )

                case 'decdnnf_two_steps':
                    match args.using:
                        case 'd4':
                            ta = lambda: decdnnf_two_steps.enum(
                                env,
                                decdnnf_two_steps.Arguments(
                                    cores=args.cores,
                                    nnf_exists_x=args.nnf_exists_x,
                                    mapping=args.mapping,
                                    nnf=args.nnf,
                                )
                            )

                        case 'sdd':
                            ta = lambda: decdnnf_two_steps.enum_with_sdd(
                                env,
                                decdnnf_two_steps.ArgumentsWithSDD(
                                    cores=args.cores,
                                    nnf_exists_x=args.nnf_exists_x,
                                    mapping=args.mapping,
                                    vtree=args.vtree,
                                    sdd=args.sdd,
                                )
                            )

            enumerator = FnEnumerator(
                env,
                density.support,
                s.Real(1),
                fn.partial(enum, lambda _1, _2: ta())
            )

    with utils.log('total'):
        log_enum: LogEnumerator = LogEnumerator(enumerator)
        log_int: LogIntegrator = LogIntegrator(integrator)
        result = WMISolver(log_enum, log_int).compute(
            s.Bool(True),
            [v for v in density.domain.keys() if v.symbol_type() == s.REAL]
        )

    json.dump(result | {'models': log_enum.models}, sys.stdout)
    sys.stdout.write('\n')


if __name__ == '__main__':
    main()
