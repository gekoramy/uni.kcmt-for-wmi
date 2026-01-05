import argparse
import itertools as it
import typing as t
from collections import deque
from pathlib import Path


def dfs(adjs: t.Sequence[t.Sequence[int]]) -> list[int]:
    """
    >>> dfs([[1], [2], []])
    [0, 1, 2]

    >>> dfs([[1], [], []])
    [0, 1, -1]
    """

    counter: it.count[int] = it.count()
    ids: list[int] = [-1] * len(adjs)
    ids[0] = next(counter)
    stack: list[int] = [0]
    while stack:
        u: int = stack.pop()

        for v in adjs[u]:
            if -1 != ids[v]: continue
            ids[v] = next(counter)
            stack.append(v)

    return ids


def reversed_toposort(outdegree: t.MutableSequence[int], parents: t.Sequence[t.Sequence[int]]) -> t.Generator[int]:
    queue: deque[int] = deque((u for u, degree in enumerate(outdegree) if 0 == degree))
    while queue:
        u: int = queue.popleft()
        yield u

        for parent in parents[u]:
            outdegree[parent] -= 1
            if 0 == outdegree[parent]:
                queue.append(parent)


def minimizing(
        raw: t.Iterator[str],
) -> list[str]:
    nnfs: list[t.Literal['a', 'o', 't', 'f']] = ['t']

    children: list[dict[int, list[list[int]]]] = [{1: [[]]}]
    parents: list[list[int]] = [[], [0]]

    for line in raw:

        words: list[str] = line.split()

        if words[0].isalpha():
            nnfs.append(words[0])
            children.append({})
            parents.append([])
        else:
            u, v, *literals = map(int, words[:-1])
            children[u].setdefault(v, []).append(literals)
            parents[v].append(u)

    parents.pop()

    def apply_and(u: int) -> tuple[str, dict[int, list[list[int]]]]:
        acc: list[tuple[int, list[list[int]]]] = []
        for v, lls in children[u].items():
            tmp: list[list[int]] = []
            for ls in lls:
                if 't' == nnfs[v] and not ls: continue
                if 'f' == nnfs[v] and not ls: return 'f', {}
                tmp.append(ls)

            if tmp:
                acc.append((v, tmp))

        if acc:
            return 'a', dict(acc)
        else:
            return 't', {}

    def apply_or(u: int) -> tuple[str, dict[int, list[list[int]]]]:
        acc: list[tuple[int, list[list[int]]]] = []
        for v, lls in children[u].items():
            tmp: list[list[int]] = []
            for ls in lls:
                if 't' == nnfs[v] and not ls: return 't', {}
                if 'f' == nnfs[v] and not ls: continue
                tmp.append(ls)

            if tmp:
                acc.append((v, tmp))

        if acc:
            return 'o', dict(acc)
        else:
            return 'f', {}

    for u in list(reversed_toposort(list(map(len, children)), parents)):
        if 0 == u: continue

        match nnfs[u]:
            case 'a':
                nnfs[u], children[u] = apply_and(u)

            case 'o':
                nnfs[u], children[u] = apply_or(u)

        match list(children[u].items()):
            case [(v, [ls_uv])]:
                for p in parents[u]:
                    lls_pu = children[p].pop(u)
                    children[p].setdefault(v, []).extend(
                        ls_pu + ls_uv
                        for ls_pu in lls_pu
                    )

    ids: list[int] = dfs([to.keys() for to in children])

    nodes: list[str] = [''] * max(ids)
    for nnf, idu in zip(nnfs, ids):
        if idu <= 0: continue
        nodes[idu - 1] = f'{nnf} {idu}'

    edges: list[str] = [
        ' '.join(map(str, (idu, idv, *ls)))
        for u in range(len(nnfs))
        for v, lls in children[u].items()
        for ls in lls
        if 'f' != nnfs[u]
        if (idu := ids[u]) > 0
        if (idv := ids[v]) > 0
    ]

    return nodes + edges


def minimize(nnf: tuple[Path, Path]) -> None:
    with open(nnf[0], 'rt') as f:
        output = minimizing(f)

    with open(nnf[1], 'wt') as f:
        f.writelines(
            part
            for line in output
            for part in (line, ' 0\n')
        )


def main() -> None:
    parser: argparse.ArgumentParser = argparse.ArgumentParser()
    parser.add_argument('--nnf', nargs=2, type=Path, required=True)
    args: argparse.Namespace = parser.parse_args()

    minimize(args.nnf)


if __name__ == '__main__':
    main()
