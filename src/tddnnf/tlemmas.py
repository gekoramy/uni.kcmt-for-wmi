import argparse
import itertools as it
import json
import typing as t
from abc import abstractmethod
from io import StringIO
from pathlib import Path

import pysmt.operators as op
import pysmt.shortcuts as smt
from pysmt.environment import Environment, get_env
from pysmt.fnode import FNode
from pysmt.smtlib.parser import SmtLibParser
from pysmt.smtlib.script import smtlibscript_from_formula
from pysmt.walkers import IdentityDagWalker, handles
from theorydd.solvers.mathsat_partial_extended import MathSATExtendedPartialEnumerator
from wmpy.cli.density import Density

from src import utils

i2atom: type['i2atom'] = t.NewType('i2atom', list[FNode])


def atoms(mapping: i2atom) -> int:
    return len(mapping) - 1


def entries(mapping: i2atom) -> t.Iterable[tuple[int, FNode]]:
    return it.islice(enumerate(mapping), 1, None)


def read_mapping(
        env: Environment,
        mapping: Path
) -> i2atom:
    with utils.log('parsing abstraction'), open(mapping, 'r', encoding='utf-8') as f:
        parser: SmtLibParser = SmtLibParser(environment=env)

        return i2atom(
            [smt.TRUE()] +
            [
                parser.get_script(StringIO(json.loads(line))).get_last_formula()
                for line in f
            ]
        )


def convert(
        mapping: i2atom,
        mu: dict[bool, list[int]],
) -> dict[bool, list[FNode]]:
    return {
        boolean: [mapping[l] for l in literals]
        for boolean, literals in mu.items()
    }


class Converter[A, B](t.Protocol):

    @abstractmethod
    def convert(self, a: A) -> B:
        raise NotImplementedError

    @abstractmethod
    def back(self, b: B) -> A:
        raise NotImplementedError


class NormalizeWalker[T](IdentityDagWalker):

    def __init__(self, converter: Converter[T, FNode], env: Environment, invalidate_memoization=None):
        super().__init__(env, invalidate_memoization)
        self.converter: Converter[T, FNode] = converter

    @handles(
        *op.THEORY_OPERATORS,
        *op.BV_RELATIONS,
        *op.IRA_RELATIONS,
        *op.STR_RELATIONS,
        op.REAL_CONSTANT,
        op.BV_CONSTANT,
        op.INT_CONSTANT,
        op.FUNCTION,
        op.EQUALS,
        op.SYMBOL,
    )
    def normalize(self, formula: FNode, args, **kwargs) -> FNode:
        term: T = self.converter.convert(formula)
        return self.converter.back(term)


def main() -> None:
    parser: argparse.ArgumentParser = argparse.ArgumentParser()
    parser.add_argument('--steps', type=Path, required=True)
    parser.add_argument('--density', type=utils.file, required=True)
    parser.add_argument('--tlemmas', type=Path, required=True)
    parser.add_argument('--mapping', type=Path, required=True)
    parser.add_argument('--phi_n_tlemmas', type=Path, required=True)
    parser.add_argument('--cores', type=int, required=True)
    args: argparse.Namespace = parser.parse_args()

    utils.setup(args.steps)

    environment: Environment = get_env()
    density: Density = utils.read_density(args.density)
    phi: FNode = smt.And(density.support, smt.Bool(True))

    with utils.log('extract tlemmas'), utils.computations() as computations:
        smt_solver: MathSATExtendedPartialEnumerator = MathSATExtendedPartialEnumerator(
            computation_logger=computations,
            parallel_procs=args.cores,
        )

        sat: bool = smt_solver.check_all_sat(phi=phi)
        tlemmas: list[FNode] = smt_solver.get_theory_lemmas()

    walker: IdentityDagWalker = NormalizeWalker(
        converter=smt_solver.get_converter(),
        env=environment,
    )

    with utils.log('normalizing tlemmas'):
        tlemmas: list[FNode] = [walker.walk(tlemma) for tlemma in tlemmas]

    with utils.log('normalizing phi'):
        phi_and_tlemmas: FNode = smt.And(walker.walk(phi), *tlemmas) if sat else smt.FALSE()

    with utils.log('writing tlemmas'), open(args.tlemmas, 'w', encoding='utf-8') as f:
        smtlibscript_from_formula(smt.And(tlemmas)).serialize(f)

    with utils.log('writing phi and tlemmas'), open(args.phi_n_tlemmas, 'w', encoding='utf-8') as f:
        smtlibscript_from_formula(phi_and_tlemmas).serialize(f)

    with utils.log('writing mapping'), open(args.mapping, 'w', encoding='utf-8') as f:
        for atom in phi_and_tlemmas.get_atoms():
            tmp: StringIO = StringIO()
            smtlibscript_from_formula(atom).serialize(tmp)
            json.dump(tmp.getvalue(), f)
            f.write('\n')


if __name__ == '__main__':
    main()
