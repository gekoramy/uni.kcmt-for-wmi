import itertools as it
import sys
import typing as t
from pathlib import Path

def sdd2nnf(sdd: t.Iterator[str]) -> list[str]:
    true_mask: str = 'T'
    true_node: None | str = None

    nodes: list[str] = []
    edges: list[str] = []

    for raw in sdd:
        line: str = raw.strip()
        if not line or line.startswith('c'):
            continue

        head: str
        tail: list[str]
        head, *tail = line.split()
        ints: list[int] = list(map(int, tail))

        match head:
            case 'sdd':
                [total] = ints
                nodes = [''] * (total + 1)

            case 'L':
                node_id, _, literal = ints
                node_id += 1
                nodes[node_id] = f'a {node_id}'
                edges.append(f'{node_id} {true_mask} {literal}')

            case 'D':
                node_id, _, _, *primes_n_subs = ints
                node_id += 1
                nodes[node_id] = f'o {node_id}'
                for prime, sub in it.batched(primes_n_subs, 2):
                    edges.append(f'{node_id} {sub + 1} {prime + 1}')

            case 'F':
                [node_id] = ints
                node_id += 1
                nodes[node_id] = f'f {node_id}'

            case 'T':
                [node_id] = ints
                node_id += 1
                true_node = str(node_id)
                nodes[node_id] = f't {true_node}'

    if not true_node:
        node_id = len(nodes)
        true_node = str(node_id)
        nodes.append(f't {true_node}')

    assert '' == nodes[0]

    return nodes[1:] + [edge.replace(true_mask, true_node, 1) for edge in edges]


if __name__ == '__main__':
    if len(sys.argv) != 3:
        print(f'Usage: python {Path(sys.argv[0]).name} <input.sdd> <output.nnf>')
        sys.exit(1)

    sdd = Path(sys.argv[1])
    nnf = Path(sys.argv[2])

    with open(sdd, 'r') as f:
        output = sdd2nnf(f)

    with open(nnf, 'w') as f:
        f.writelines(line + ' 0 \n' for line in output)
