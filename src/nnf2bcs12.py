import argparse
import re
import typing as t
from pathlib import Path

from src import utils

p4edge: re.Pattern[str] = re.compile(r'^(\d+ \d+ )(.*)( 0\s*)$')
p4lits: re.Pattern[str] = re.compile(r'(-?)(\d+)')


def fix_nnf(line: str) -> str:
    """
    >>> fix_nnf('o 1 0')
    'o 1 0'

    >>> fix_nnf('t 2 0')
    't 2 0'

    >>> fix_nnf('1 2 3 -4 0')
    '1 2 2 -3 0'
    """

    return p4edge.sub(
        lambda m: ''.join((
            m[1],
            p4lits.sub(
                lambda mm: f'{mm[1]}{int(mm[2]) - 1}',
                m[2]
            ),
            m[3],
        )),
        line,
    )


def nnf2bcs12(file: t.Iterator[str], project: list[int]) -> list[str]:
    gate = t.NewType('gate', tuple[t.Literal['A', 'O'], list[int]])
    atoms: int = 0
    gates: list[gate] = [gate(('A', []))]
    subs: list[gate] = []

    for raw in file:
        line: str = raw.strip()
        words: list[str] = line.split()

        match words[0]:
            case 'o':
                gates.append(gate(('O', [])))

            case 'a':
                gates.append(gate(('A', [])))

            case 't':
                gates.append(gate(('O', [1, -1])))

            case 'f':
                gates.append(gate(('A', [1, -1])))

            case _:
                ls: list[int]
                u, v, *ls = map(int, words[:-1])
                gates[u][1].append(len(subs))
                subs.append(gate(('A', [v, *ls])))
                atoms = max(0, atoms, *map(abs, ls))

    lines: list[str] = ['c BC-S1.2']

    for i in range(1, atoms + 1):
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

    for i, (op, ts) in enumerate(gates[1:], 1):
        lines.append(f'G g{i} := {op} {' '.join(f't{tm}' for tm in ts)}')

    for i, (op, (head, *tail)) in enumerate(subs):
        lines.append(f'G t{i} := {op} g{head} {' '.join(map(str, tail))}')

    lines.append(' '.join(('P', *(map(str, project if project else range(1, atoms + 1))))))

    lines.append('T g1')

    return lines


def translate(nnf: Path, project: list[int], bcs12: Path) -> None:
    with open(nnf, 'rt') as f:
        output = nnf2bcs12(f, project)

    with open(bcs12, 'wt') as f:
        f.writelines(
            part
            for line in output
            for part in (line, '\n')
        )


def main() -> None:
    parser: argparse.ArgumentParser = argparse.ArgumentParser()
    parser.add_argument('--nnf', type=utils.file, required=True)
    parser.add_argument('--bcs12', type=Path, required=True)
    parser.add_argument('--project', type=int, nargs='*')
    args: argparse.Namespace = parser.parse_args()

    translate(nnf=args.nnf, project=args.project, bcs12=args.bcs12)


if __name__ == '__main__':
    main()
