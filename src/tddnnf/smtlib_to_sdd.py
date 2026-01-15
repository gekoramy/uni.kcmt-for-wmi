import argparse
import functools as ft
import typing as t
from operator import iand, ior
from pathlib import Path

import pysmt.operators as op
import pysmt.shortcuts as smt
from array import array
from pysdd.sdd import SddManager, SddNode, Vtree
from pysmt.environment import Environment, get_env
from pysmt.fnode import FNode
from pysmt.smtlib.parser import SmtLibParser
from pysmt.walkers import DagWalker, handles

from src import utils
from src.tddnnf import tlemmas


def ref_sdd(sdd: SddNode) -> SddNode:
    sdd.ref()
    return sdd


class SDDWalker(DagWalker):

    def __init__(
            self,
            i2atom: tlemmas.i2atom,
            manager: SddManager,
            env: Environment,
            invalidate_memoization=False,
    ):
        DagWalker.__init__(self, env, invalidate_memoization)
        self.atom2literal: dict[FNode, SddNode] = {atom: manager.literal(i) for i, atom in tlemmas.entries(i2atom)}
        self.manager: SddManager = manager

    def walk_and(self, formula: FNode, args: t.Sequence[SddNode], **kwargs) -> SddNode:
        return ref_sdd(ft.reduce(iand, args))

    def walk_or(self, formula: FNode, args: t.Sequence[SddNode], **kwargs) -> SddNode:
        return ref_sdd(ft.reduce(ior, args))

    def walk_not(self, formula: FNode, args: t.Sequence[SddNode], **kwargs) -> SddNode:
        assert 1 == len(args) and args[0]
        return ref_sdd(~args[0])

    def walk_bool_constant(self, formula: FNode, args: t.Sequence[SddNode], **kwargs) -> SddNode:
        value: bool = formula.constant_value()
        return self.manager.true() if value else self.manager.false()

    def walk_iff(self, formula: FNode, args: t.Sequence[SddNode], **kwargs) -> SddNode:
        # IFF: a <-> b === (a & b) | (~a & ~b)
        assert 2 == len(args) and args[0] and args[1]
        return ref_sdd((args[0] & args[1]) | ((~args[0]) & (~args[1])))

    def walk_implies(self, formula: FNode, args: t.Sequence[SddNode], **kwargs) -> SddNode:
        # IMPLIES: a -> b === (~a | b)
        assert 2 == len(args) and args[0] and args[1]
        return ref_sdd((~args[0]) | args[1])

    def walk_ite(self, formula: FNode, args: t.Sequence[SddNode], **kwargs) -> SddNode:
        # ITE: if a then b else c === ((~a) | b) & (a | c)
        assert 3 == len(args) and args[0] and args[1] and args[2]
        return ref_sdd(((~args[0]) | args[1]) & (args[0] | args[2]))

    @handles(
        *op.THEORY_OPERATORS,
        *op.BV_RELATIONS,
        *op.IRA_RELATIONS,
        *op.STR_RELATIONS,
        op.EQUALS,
        op.FUNCTION,
        op.SYMBOL,
    )
    def apply_mapping(self, formula: FNode, args: t.Sequence[t.Any], **kwargs) -> SddNode | None:
        return self.atom2literal.get(formula)

    @handles(
        op.REAL_CONSTANT,
        op.INT_CONSTANT,
    )
    def ignore(self, formula: FNode, args: t.Sequence[t.Any], **kwargs) -> None:
        return None


def to_sdd(
        env: Environment,
        phi: FNode,
        i2atom: tlemmas.i2atom,
        constrained: t.Literal['x', 'A'] | None,
) -> tuple[Vtree, SddNode]:
    atoms: int = tlemmas.atoms(i2atom)

    vt: Vtree
    match constrained:
        case None:
            vt = Vtree.new_with_var_order(atoms, list(range(1, atoms + 1)), 'balanced')

        case 'x':
            which: list[int] = [0] * (1 + atoms)
            for i, atom in tlemmas.entries(i2atom):
                which[i] = not atom.is_symbol(smt.BOOL)

            vt = Vtree.new_with_X_constrained(atoms, array('q', which), 'balanced')

        case 'A':
            which: list[int] = [0] * (1 + atoms)
            for i, atom in tlemmas.entries(i2atom):
                which[i] = atom.is_symbol(smt.BOOL)

            vt = Vtree.new_with_X_constrained(atoms, array('q', which), 'balanced')

    mgr: SddManager = SddManager.from_vtree(vt)
    mgr.auto_gc_and_minimize_on()

    walker: SDDWalker = SDDWalker(i2atom=i2atom, manager=mgr, env=env)
    root: SddNode = walker.walk(phi)

    return vt, root


def translate(smtlib: Path, mapping: Path, vtree: Path, sdd: Path, constrained: t.Literal['x', 'A'] | None) -> None:
    env: Environment = get_env()
    i2atom: tlemmas.i2atom = tlemmas.read_mapping(env, mapping)

    with open(smtlib, 'r', encoding='utf-8') as f:
        parser: SmtLibParser = SmtLibParser(environment=env)
        phi: FNode = parser.get_script(f).get_last_formula()

    vt, root = to_sdd(
        env=env,
        phi=phi,
        i2atom=i2atom,
        constrained=constrained,
    )

    with utils.log('store'):
        vt.save(str.encode(vtree.as_posix()))
        root.save(str.encode(sdd.as_posix()))


def main() -> None:
    parser: argparse.ArgumentParser = argparse.ArgumentParser()
    parser.add_argument('--smtlib', type=utils.file, required=True)
    parser.add_argument('--mapping', type=utils.file, required=True)
    parser.add_argument('--vtree', type=Path, required=True)
    parser.add_argument('--sdd', type=Path, required=True)
    parser.add_argument('--constrained', type=str, choices=['x', 'A'], required=False)
    args: argparse.Namespace = parser.parse_args()

    translate(smtlib=args.smtlib, mapping=args.mapping, vtree=args.vtree, sdd=args.sdd, constrained=args.constrained)


if __name__ == '__main__':
    main()
