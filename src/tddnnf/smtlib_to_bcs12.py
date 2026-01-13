import argparse
import typing as t
from pathlib import Path

import pysmt.operators as op
from pysmt.environment import Environment, get_env
from pysmt.fnode import FNode
from pysmt.smtlib.parser import SmtLibParser
from pysmt.walkers import DagWalker, handles

from src import utils
from src.tddnnf import tlemmas


def negate(gate: str) -> str:
    return f'-{gate}'.removeprefix('--')


class BCS12Walker(DagWalker):

    def __init__(
            self,
            atom2i: dict[FNode, str],
            env: Environment,
            invalidate_memoization=False,
    ):
        DagWalker.__init__(self, env, invalidate_memoization)
        self.atom2id = atom2i
        self.gates = [
            'G gF := A 1 -1',
            'G gT := O 1 -1',
        ]

    def _new_gate(self, kind: t.Literal['A', 'O'], *definition: str) -> str:
        gate: str = f'g{len(self.gates)}'
        self.gates.append(' '.join(('G', gate, ':=', kind, *set(definition))))
        return gate

    def walk_and(self, formula: FNode, args: t.Sequence[str], **kwargs) -> str:
        return self._new_gate('A', *args)

    def walk_or(self, formula: FNode, args: t.Sequence[str], **kwargs) -> str:
        return self._new_gate('O', *args)

    def walk_not(self, formula: FNode, args: t.Sequence[str], **kwargs) -> str:
        assert 1 == len(args) and args[0]
        return negate(args[0])

    def walk_bool_constant(self, formula: FNode, args: t.Sequence[str], **kwargs) -> str:
        value: bool = formula.constant_value()
        return 'gT' if value else 'gF'

    def walk_iff(self, formula: FNode, args: t.Sequence[str], **kwargs) -> str:
        # IFF: a <-> b === (a & b) | (~a & ~b)
        assert 2 == len(args) and args[0] and args[1]

        # (a & b)
        fst = self._new_gate('A', args[0], args[1])

        # (~a & ~b)
        snd = self._new_gate('A', negate(args[0]), negate(args[1]))

        # (a & b) | (~a & ~b)
        return self._new_gate('O', fst, snd)

    def walk_implies(self, formula: FNode, args: t.Sequence[str], **kwargs) -> str:
        # IMPLIES: a -> b === (~a | b)
        assert 2 == len(args) and args[0] and args[1]
        return self._new_gate('O', negate(args[0]), args[1])

    def walk_ite(self, formula: FNode, args: t.Sequence[str], **kwargs) -> str:
        # ITE: if a then b else c === ((~a) | b) & (a | c)
        assert 3 == len(args) and args[0] and args[1] and args[2]

        # (~a | b)
        fst: str = self._new_gate('O', negate(args[0]), args[1])

        # (a | c)
        snd: str = self._new_gate('O', args[0], args[2])

        # ((~a) | b) & (a | c)
        return self._new_gate('A', fst, snd)

    @handles(
        *op.THEORY_OPERATORS,
        *op.BV_RELATIONS,
        *op.IRA_RELATIONS,
        *op.STR_RELATIONS,
        op.EQUALS,
        op.FUNCTION,
        op.SYMBOL,
    )
    def apply_mapping(self, formula: FNode, args: t.Sequence[t.Any], **kwargs) -> str | None:
        return self.atom2id.get(formula)

    @handles(
        op.REAL_CONSTANT,
        op.INT_CONSTANT,
    )
    def ignore(self, formula: FNode, args: t.Sequence[t.Any], **kwargs) -> None:
        return None


def to_bcs12(env: Environment, phi: FNode, i2atom: tlemmas.i2atom, project_onto: list[int] | None) -> list[str]:
    walker: BCS12Walker = BCS12Walker(
        atom2i={v: str(k) for k, v in tlemmas.entries(i2atom)},
        env=env
    )
    root: str = walker.walk(phi)

    atoms: int = tlemmas.atoms(i2atom)
    lines: list[str] = ['c BC-S1.2']

    for i in tlemmas.entries(i2atom):
        lines.append(f'I {i}')

    # this gate references all atoms to ensure deterministic id assignment
    lines.append(
        f'G reserved := O {
        ' '.join(map(str, (
            l
            for a in range(1, atoms + 1)
            for l in [+a, -a]
        )))
        }'
    )
    lines.extend(walker.gates)
    lines.append(' '.join(('P', *(map(str, project_onto if project_onto else range(1, atoms + 1))))))
    lines.append(f'T {root}')

    return lines


def translate(smtlib: Path, mapping: Path, project_onto: list[int] | None, bcs12: Path) -> None:
    env: Environment = get_env()
    i2atom: tlemmas.i2atom = tlemmas.read_mapping(env, mapping)

    with open(smtlib, 'r', encoding='utf-8') as f:
        parser: SmtLibParser = SmtLibParser(environment=env)
        phi: FNode = parser.get_script(f).get_last_formula()

    with open(bcs12, 'w', encoding='utf-8') as f:
        f.writelines(
            part
            for line in to_bcs12(env, phi, i2atom, project_onto)
            for part in (line, '\n')
        )


def main() -> None:
    parser: argparse.ArgumentParser = argparse.ArgumentParser()
    parser.add_argument('--smtlib', type=utils.file, required=True)
    parser.add_argument('--mapping', type=utils.file, required=True)
    parser.add_argument('--bcs12', type=Path, required=True)
    parser.add_argument('--project_onto', type=int, nargs='*')
    args: argparse.Namespace = parser.parse_args()

    translate(smtlib=args.smtlib, mapping=args.mapping, project_onto=args.project_onto, bcs12=args.bcs12)


if __name__ == '__main__':
    main()
