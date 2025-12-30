import argparse
import typing as t
from pathlib import Path

from src import utils


def nnf2bcs12(file: t.Iterator[str], project: list[int]) -> list[str]:
    gate = t.NewType('gate', tuple[t.Literal['A', 'O'], list[int]])
    literals: int = 0
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
                literals = max(0, literals, *map(abs, ls))

    lines: list[str] = ['c BC-S1.2']

    if project:
        lines.append(' '.join(('P', *(f'a{a}' for a in project))))

    for i in range(1, literals + 1):
        lines.append(f'I a{i}')

    for i, (op, ts) in enumerate(gates[1:], 1):
        lines.append(f'G g{i} := {op} {' '.join(f't{tm}' for tm in ts)}')

    for i, (op, (head, *tail)) in enumerate(subs):
        lines.append(f'G t{i} := {op} g{head} {' '.join(f'a{l}' if l > 0 else f'-a{-l}' for l in tail)}')

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
