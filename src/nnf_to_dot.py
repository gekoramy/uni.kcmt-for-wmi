import argparse
import itertools as it
import typing as t
from pathlib import Path

import graphviz

from src import utils


def html(literals: t.Iterable[str]) -> str:
    return ''.join((
        '<',
        '<TABLE BORDER="0" CELLBORDER="1" CELLSPACING="0" CELLPADDING="4">',
        '<TR>',
        *(
            part
            for l in literals
            for part in ('<TD>', l, '</TD>')
        ),
        '</TR>',
        '</TABLE>',
        '>',
    ))


def nnf2dot(file: t.Iterator[str]) -> graphviz.Graph:
    dot = graphviz.Graph('wide')

    ids = (str(i) for i in it.count(-1, -1))
    nnf2b: dict[str, bool] = {}

    for raw in file:
        line: str = raw.strip()
        if not line or line.startswith('c'):
            continue

        head: str
        tail: list[str]
        head, *tail = line.split()

        match head:
            case 'o':
                id, _ = tail
                dot.node(id, shape='invtriangle', color='blue')

            case 'a':
                id, _ = tail
                dot.node(id, shape='triangle', color='green')

            case 't':
                id, _ = tail
                nnf2b[id] = True

            case 'f':
                id, _ = tail
                nnf2b[id] = False

            case p:
                c, *literals = tail
                literals.pop()

                match nnf2b.get(c, None):
                    case True:
                        id4c = next(ids)
                        dot.node(id4c, 'T', shape='doublecircle', color='red')

                    case False:
                        id4c = next(ids)
                        dot.node(id4c, 'F', shape='doublecircle', color='red')

                    case _:
                        id4c = c

                dot.edge(
                    p,
                    id4c,
                    **(
                        {
                            'label': html(literals),
                            'decorate': 'true',
                        }
                        if literals else {}
                    ),
                )

    return dot


def translate(nnf: Path, dot: Path) -> None:
    with open(nnf, 'r', encoding='utf-8') as f:
        output = nnf2dot(f)

    output.render(dot.as_posix())


def main() -> None:
    parser: argparse.ArgumentParser = argparse.ArgumentParser()
    parser.add_argument('--nnf', type=utils.file, required=True)
    parser.add_argument('--dot', type=Path, required=True)
    args: argparse.Namespace = parser.parse_args()

    translate(args.nnf, args.dot)


if __name__ == '__main__':
    main()
