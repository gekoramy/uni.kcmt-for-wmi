import sys
import typing as t
import itertools as it
import graphviz

from pathlib import Path


def nnf2svg(file: t.Iterator[str]) -> graphviz.Graph:
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

                if literals:
                    id4a = next(ids)
                    id4ls = [next(ids) for _ in literals]

                    dot.node(id4a, ' ', shape='triangle', style='dashed')
                    for id4l, l in zip(id4ls, literals):
                        dot.node(id4l, l, shape='square')

                    for src, trg in [(p, id4a)] + [(id4a, id) for id in [id4c] + id4ls if id]:
                        dot.edge(src, trg)
                else:
                    dot.edge(p, id4c)

    return dot


if __name__ == '__main__':
    if len(sys.argv) != 3:
        print(f'Usage: python {Path(sys.argv[0]).name} <input.nnf> <output.dot>')
        sys.exit(1)

    nnf = Path(sys.argv[1])
    svg = Path(sys.argv[2])

    with open(nnf, 'r') as f:
        output = nnf2svg(f)

    output.render(svg.as_posix())
