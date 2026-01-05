import argparse
import itertools as it
import typing as t
from collections import OrderedDict
from dataclasses import dataclass
from pathlib import Path

from src import utils


@dataclass(frozen=True)
class NNF:
    id: int


@dataclass(frozen=True)
class B:
    id: bool


@dataclass(frozen=True)
class OR:
    l_n_l: list[tuple[str, str]]
    nnf_n_l: list[tuple[NNF | B, str]]
    nnf_n_nnf: list[tuple[NNF | B, NNF | B]]


def sdd2nnf(sdd: t.Iterator[str]) -> list[str]:
    sdd2nnf: OrderedDict[str, tuple[NNF, OR] | tuple[B, tuple[()]]] = OrderedDict()
    sdd2l: dict[str, str] = {}
    sdd2b: set[bool] = set()

    nnfs = it.count()

    for raw in sdd:
        line: str = raw.strip()
        if not line or line.startswith('c') or line.startswith('sdd'):
            continue

        head: str
        tail: list[str]
        head, *tail = line.split()

        match head:
            case 'L':
                node, _, literal = tail
                sdd2l[node] = literal

            case 'D':
                node, _, _, *primes_n_subs = tail
                new = OR([], [], [])

                for prime, sub in it.batched(primes_n_subs, 2):

                    match sdd2l.get(prime), sdd2l.get(sub):
                        case None, None:
                            new.nnf_n_nnf.append((sdd2nnf[prime][0], sdd2nnf[sub][0]))

                        case None, ls:
                            new.nnf_n_l.append((sdd2nnf[prime][0], ls))

                        case lp, None:
                            new.nnf_n_l.append((sdd2nnf[sub][0], lp))

                        case lp, ls:
                            new.l_n_l.append((lp, ls))
                            sdd2b.add(True)

                sdd2nnf[node] = NNF(next(nnfs)), new

            case 'T' | 'F':
                [node] = tail
                boolean = 'T' == head
                sdd2nnf[node] = B(boolean), ()
                sdd2b.add(boolean)

    ors: int = next(nnfs)

    nnf4b: list[int | None] = [next(nnfs) if b in sdd2b else None for b in [False, True]]

    nodes = [f'o {nnf + 1}' for nnf in range(ors)] + [f'{b} {nnf}' for b, nnf in zip('ft', nnf4b) if nnf]

    def fix(i: NNF | B) -> int:
        match i:
            case NNF(nnf):
                return ors - nnf

            case B(boolean):
                return nnf4b[boolean]

    edges = []

    for entry in reversed(sdd2nnf.values()):
        match entry:
            case parent, OR(l_n_l, nnf_n_l, nnf_n_nnf):

                for ls in l_n_l:
                    edges.append(f'{fix(parent)} {nnf4b[True]} {' '.join(ls)}')

                for child, l in nnf_n_l:
                    edges.append(f'{fix(parent)} {fix(child)} {l}')

                for children in nnf_n_nnf:
                    nnf_and = next(nnfs)
                    nodes.append(f'a {nnf_and}')
                    edges.append(f'{fix(parent)} {nnf_and}')
                    edges.extend(f'{nnf_and} {fix(child)}' for child in children)

    return nodes + edges


def translate(sdd: Path, nnf: Path) -> None:
    with open(sdd, 'rt') as f:
        output = sdd2nnf(f)

    with open(nnf, 'wt') as f:
        f.writelines(
            part
            for line in output
            for part in (line, ' 0\n')
        )


def main() -> None:
    parser: argparse.ArgumentParser = argparse.ArgumentParser()
    parser.add_argument('--sdd', type=utils.file, required=True)
    parser.add_argument('--nnf', type=Path, required=True)
    args: argparse.Namespace = parser.parse_args()

    translate(args.sdd, args.nnf)


if __name__ == '__main__':
    main()
