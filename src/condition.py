import argparse
import itertools as it
import typing as t
from pathlib import Path

from src import utils


def dfs(visited: t.MutableSequence[bool], adjs: t.Sequence[t.Sequence[int]]):
    """
    >>> visited = [True, False, False]
    >>> adjs = [[1], [2], []]
    >>> dfs(visited, adjs)
    >>> print(visited)
    [True, True, True]

    >>> visited = [True, False, False]
    >>> adjs = [[1], [], []]
    >>> dfs(visited, adjs)
    >>> print(visited)
    [True, True, False]
    """

    stack: list[int] = [u for u, flag in enumerate(visited) if flag]
    while stack:
        u: int = stack.pop()

        for v in adjs[u]:
            if visited[v]: continue
            visited[v] = True
            stack.append(v)


def conditioning(
        raw: t.Iterator[str],
        assumptions: frozenset[int]
) -> list[str]:
    """
    >>> nnf = [
    ...   'a 1 0',
    ...   't 2 0',
    ...   '1 2 2 -1 0',
    ... ]
    >>> conditioning(iter(nnf), frozenset([1]))
    ['f 1']

    >>> nnf = [
    ...   'a 1 0',
    ...   't 2 0',
    ...   '1 2 2 0',
    ...   '1 2 -1 0',
    ... ]
    >>> conditioning(iter(nnf), frozenset([1]))
    ['f 1']

    >>> nnf = [
    ...   'a 1 0',
    ...   'a 2 0',
    ...   't 3 0',
    ...   '1 2 1 0',
    ...   '2 3 2 0',
    ... ]
    >>> conditioning(iter(nnf), frozenset([1, -2]))
    ['a 1', 'f 2', '1 2']

    >>> nnf = [
    ...   'o 1 0',
    ...   'o 2 0',
    ...   'o 3 0',
    ...   'f 4 0',
    ...   't 5 0',
    ...   '1 2 -1 0',
    ...   '2 3 -2 0',
    ...   '3 4 -3 0',
    ...   '1 5 1 0',
    ...   '2 5 2 0',
    ...   '3 5 3 0',
    ... ]
    >>> conditioning(iter(nnf), frozenset([1, 3]))
    ['o 1', 't 2', '1 2']

    >>> nnf = [
    ...   'a 1 0',
    ...   'o 2 0',
    ...   'o 3 0',
    ...   't 4 0',
    ...   '1 2 0',
    ...   '1 3 0',
    ...   '2 4 1 2 0',
    ...   '2 4 -1 2 0',
    ...   '3 4 3 0',
    ...   '3 4 -3 0',
    ... ]
    >>> conditioning(iter(nnf), frozenset([-2]))
    ['a 1', 'f 2', 'o 3', 't 4', '1 2', '1 3', '3 4 3', '3 4 -3']
    """

    nnfs: list[t.Literal['a', 'o', 't', 'f']] = ['a']
    pruned: list[tuple[int, int, t.Iterable[int]]] = [(0, 1, assumptions)]

    # check if it is reachable by the root node
    rootable: list[bool]
    children: list[list[int]] = [[1]]

    # and-nodes and or-nodes can become false in the process
    falsable: list[bool] = [False]

    for line in raw:

        words: list[str] = line.split()

        if words[0].isalpha():
            nnfs.append(words[0])
            falsable.append(False)
            children.append([])
        else:
            u, v, *literals = map(int, words[:-1])

            if any(-l in assumptions for l in literals):
                falsable[u] = True
                continue

            pruned.append((u, v, [l for l in literals if l not in assumptions]))
            children[u].append(v)

    for i, flag in enumerate(falsable):
        if not flag: continue
        if 'o' == nnfs[i] and children[i]: continue
        nnfs[i] = 'f'
        children[i] = []

    rootable = [False] * len(nnfs)
    rootable[1] = True

    dfs(rootable, children)

    cnt = it.count(1)
    ids: list[int] = [
        next(cnt) if rootable[i] else -1
        for i in range(len(nnfs))
    ]

    nodes: list[str] = [
        f'{nnf} {idu}'
        for nnf, idu in zip(nnfs, ids)
        if -1 != idu
    ]

    edges: list[str] = [
        ' '.join(map(str, (idu, idv, *ls)))
        for u, v, ls in pruned
        if 'f' != nnfs[u]
        if -1 != (idu := ids[u])
        if -1 != (idv := ids[v])
    ]

    return nodes + edges


def condition(
        nnf: Path,
        assumptions: frozenset[int],
        conditioned: Path,
) -> None:
    with open(nnf, 'rt') as f:
        output = conditioning(f, assumptions)

    with open(conditioned, 'wt') as f:
        f.writelines(
            part
            for line in output
            for part in (line, ' 0\n')
        )


def main() -> None:
    parser: argparse.ArgumentParser = argparse.ArgumentParser()
    parser.add_argument('--nnf', type=utils.file, required=True)
    parser.add_argument('--assumptions', type=int, nargs='+')
    parser.add_argument('--conditioned', type=Path, required=True)
    args: argparse.Namespace = parser.parse_args()

    condition(nnf=args.nnf, assumptions=args.assumptions, conditioned=args.conditioned)


if __name__ == '__main__':
    main()
