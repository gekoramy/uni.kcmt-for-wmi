import argparse
import itertools as it
import typing as t
from dataclasses import dataclass
from pathlib import Path

from src import utils

literal = t.NewType('literal', int)
index: t.TypeAlias = int


@dataclass(frozen=True)
class Conflict:
    on: literal
    true: index | None
    false: index | None


@dataclass(frozen=True)
class Node:
    op: t.Literal['a', 'o']
    literals: set[literal]
    indexes: list[index]


true = Node(op='a', literals=set(), indexes=[])
false = Node(op='o', literals=set(), indexes=[])


def raw2model(
        fst: str,
        snd: str,
        tail: list[str],
        c2ds: tuple[literal | Conflict | Node],
) -> literal | Conflict | Node:
    match fst:
        case 'L':
            return literal(int(snd))

        case 'A' if '0' == snd:
            return true

        case 'O' if '0' == snd:
            return false

        case 'A':
            literals: list[literal] = []
            indexes: list[index] = []

            for ix in map(int, tail):
                child = c2ds[ix]
                match child:
                    case int() as l:
                        literals.append(literal(l))

                    case Node(op='a') as a:
                        literals.extend(a.literals)
                        indexes.extend(a.indexes)

                    case Node() as o if false == o:
                        return false

                    case _:
                        indexes.append(ix)

            acc: set[literal] = set()
            for l in literals:
                if -l in acc:
                    return false
                acc.add(l)

            return Node(op='a', literals=acc, indexes=indexes)

        case 'O' if '0' != snd:
            on: int = int(snd)
            _, l, r = map(int, tail)

            # assumption:
            # * l is T
            # * r is F

            def index_or_none(ix: int) -> index | None:
                return None if isinstance(c2ds[ix], int) else ix

            return Conflict(literal(on), index_or_none(l), index_or_none(r))

        case 'O':
            literals: list[literal] = []
            indexes: list[index] = []

            for ix in map(int, tail):
                child = c2ds[ix]
                match child:
                    case int() as l:
                        literals.append(literal(l))

                    case Node(op='o') as o:
                        literals.extend(o.literals)
                        indexes.extend(o.indexes)

                    case Node() as fst if true == fst:
                        return true

                    case _:
                        # conflict | and
                        indexes.append(ix)

            acc: set[literal] = set()
            for l in literals:
                if -l in acc:
                    return true
                acc.add(l)

            return Node(op='o', literals=acc, indexes=indexes)

    raise RuntimeError("wth?")


def c2d2d4(c2d: t.Iterator[str]) -> list[str]:
    c2ds: list[literal | Conflict | Node] = []

    for raw in c2d:
        line: str = raw.strip()
        if not line or line.startswith('nnf'):
            continue

        fst: str
        snd: str
        tail: list[str]
        fst, snd, *tail = line.split()

        c2ds.append(
            raw2model(fst, snd, tail, c2ds)
        )

    d4 = it.count(1)
    d4s: list[int] = [-1] * len(c2ds)
    tys: list[str] = [""] * len(c2ds)
    edges: list[str] = []

    d4s[-1] = next(d4)

    def fix(ix: index) -> int:
        if -1 == d4s[ix]: d4s[ix] = next(d4)
        return d4s[ix]

    for i, thing in reversed(list(enumerate(c2ds))):
        if -1 == d4s[i]:
            continue

        match thing:
            case Node() as op if true == op:
                tys[i] = 't'

            case Node() as op if false == op:
                tys[i] = 'f'

            case Node(op='o') as o:
                assert not o.literals, '[non-conflict or] cannot point a [literal]'

                tys[i] = 'o'
                edges.extend(f"{fix(i)} {fix(ix)}" for ix in o.indexes)

            case Node(op='a') as a:
                tys[i] = 'a'

                if a.literals:
                    edges.append(" ".join(map(str, (fix(i), next(d4), *a.literals))))

                edges.extend(f"{fix(i)} {fix(ix)}" for ix in a.indexes)

            case Conflict() as o:
                tys[i] = 'o'

                for ix, on in zip((o.true, o.false), (o.on, -o.on)):
                    edges.append(f'{fix(i)} {fix(ix) if ix else next(d4)} {on}')

            case xxx:
                raise RuntimeError(f"wth? {xxx}")

    ttt = ['t'] * next(d4)
    for i, ty in zip(d4s, tys):
        if -1 == i: continue
        ttt[i] = ty

    nodes: list[str] = [f"{ty} {i}" for i, ty in enumerate(ttt[1:], 1)]

    return nodes + edges


def main(c2d: Path, d4: Path) -> None:
    with open(c2d, 'rt') as f:
        output = c2d2d4(f)

    with open(d4, 'wt') as f:
        f.writelines(
            part
            for line in output
            for part in (line, ' 0\n')
        )


if __name__ == '__main__':
    parser: argparse.ArgumentParser = argparse.ArgumentParser()
    parser.add_argument('--c2d', type=utils.file, required=True)
    parser.add_argument('--d4', type=Path, required=True)
    args: argparse.Namespace = parser.parse_args()

    main(args.c2d, args.d4)
    # main(Path('../ac.nnf'), Path('../ac-d4.nnf'))
