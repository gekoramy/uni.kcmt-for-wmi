import argparse
import itertools as it
import typing as t
from collections import deque
from pathlib import Path


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

    children: list[dict[int, list[int]]] = [{1: []}]
    parents: list[list[int]] = [[], [0]]

    for line in raw:

        words: list[str] = line.split()

        if words[0].isalpha():
            nnfs.append(words[0])
            children.append({})
            parents.append([])
        else:
            u, v, *literals = map(int, words[:-1])
            children[u][v] = literals
            parents[v].append(u)

    parents.pop()

    def apply_and(u: int) -> tuple[str, dict[int, list[int]]]:
        acc: list[tuple[int, list[int]]] = []
        for v, literals in children[u].items():
            if literals:
                acc.append((v, literals))
                continue

            if 't' == nnfs[v]: continue
            if 'f' == nnfs[v]: return 'f', {}
            acc.append((v, literals))

        if acc:
            return 'a', dict(acc)
        else:
            return 't', {}

    def apply_or(u: int) -> tuple[str, dict[int, list[int]]]:
        acc: list[tuple[int, list[int]]] = []
        for v, literals in children[u].items():
            if literals:
                acc.append((v, literals))
                continue

            if 't' == nnfs[v]: return 't', {}
            if 'f' == nnfs[v]: continue
            acc.append((v, literals))

        if acc:
            return 'o', dict(acc)
        else:
            return 'f', {}

    for u in reversed_toposort(list(map(len, children)), parents):
        if 0 == u: continue

        match nnfs[u]:
            case 'a':
                nnfs[u], children[u] = apply_and(u)

            case 'o':
                nnfs[u], children[u] = apply_or(u)

        if len(children[u]) == 1:
            v, literals_uv = children[u].popitem()
            for p in parents[u]:
                literals_pu = children[p].pop(u)
                children[p][v] = literals_pu + literals_uv

    # check if it is reachable by the root node
    rootable: list[bool] = [False] * len(nnfs)
    rootable[0] = True

    dfs(rootable, [to.keys() for to in children])

    cnt = it.count(1)
    ids: list[int] = [
        next(cnt) if rootable[i] and 0 != i else -1
        for i in range(len(nnfs))
    ]

    nodes: list[str] = [
        f'{nnf} {idu}'
        for nnf, idu in zip(nnfs, ids)
        if -1 != idu
    ]

    edges: list[str] = [
        ' '.join(map(str, (idu, idv, *ls)))
        for u in range(len(nnfs))
        for v, ls in children[u].items()
        if 'f' != nnfs[u]
        if -1 != (idu := ids[u])
        if -1 != (idv := ids[v])
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
