import sys
from dataclasses import dataclass
from functools import cache
from pathlib import Path
import typing as t
import itertools as it


# SDD Node Classes
@dataclass
class SDDNode:
    node_id: int
    vtree: int


@dataclass
class LiteralNode(SDDNode):
    literal: int


@dataclass
class DecompositionNode(SDDNode):
    elements: list[tuple[int, int]]


@dataclass
class TrueNode(SDDNode):
    def __init__(self, node_id: int):
        super().__init__(node_id, -1)


@dataclass
class FalseNode(SDDNode):
    def __init__(self, node_id: int):
        super().__init__(node_id, -1)


class SDDToNNFConverter:
    sdd_nodes: dict[int, SDDNode]
    nnf_node_counter: t.Generator[int]
    nnf_edges_lines: list[str]
    nnf_nodes_lines: list[str]
    present: list[bool]

    def __init__(self):
        self.sdd_nodes = {}

        # NNF Generation State
        # Start IDs from 1 as per typical d4/c2d conventions (positive integers)
        self.nnf_node_counter = it.count(1)

        self.nnf_nodes_lines = []
        self.nnf_edges_lines = []
        self.present = [False, False]

    def parse_sdd(self, filename: Path):
        """Parse SDD file and build node structure."""
        with open(filename, 'r') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('c') or line.startswith('sdd'):
                    continue

                head: str
                tail: list[int]
                head, *tail = line.split()
                tail = list(map(int, tail))

                match head:
                    case 'L':
                        node_id, vtree, literal = tail
                        self.sdd_nodes[node_id] = LiteralNode(node_id, vtree, literal)

                    case 'D':
                        node_id, vtree, _, *primes_n_subs = tail
                        elements = list(it.batched(primes_n_subs, 2))
                        self.sdd_nodes[node_id] = DecompositionNode(node_id, vtree, elements)

                    case 'F':
                        [node_id] = tail
                        self.sdd_nodes[node_id] = FalseNode(node_id)

                    case 'T':
                        [node_id] = tail
                        self.sdd_nodes[node_id] = TrueNode(node_id)

    def _id(self, boolean: bool) -> int:
        return self._const(boolean) if self.present[boolean] else -1

    @cache
    def _const(self, boolean: bool) -> int:
        node = next(self.nnf_node_counter)
        self.nnf_nodes_lines.append(f"{"tf"[boolean]} {node} 0")
        self.present[boolean] = True
        return node

    @cache
    def convert_node(self, sdd_id: int) -> tuple[int, list[int]]:
        """
        Convert an SDD node to NNF.
        Returns (nnf_node_id, edge_literals)
        The caller should create an edge to nnf_node_id labeled with edge_literals.
        """
        match self.sdd_nodes[sdd_id]:
            case TrueNode():
                # True Node maps to TrueNode with no literals
                return self._const(True), []
            case FalseNode():
                # False Node maps to FalseNode
                return self._const(False), []
            case LiteralNode(literal=literal):
                # Literal Node L(x) maps to TrueNode with literal x on the edge
                return self._const(True), [literal]
            case DecompositionNode(elements=elements):
                # Decomposition is an OR of elements
                # Each element (p, s) is an AND of p and s

                # First, recursively convert children
                children_results = [
                    (p_nnf_id, p_lits, s_nnf_id, s_lits)
                    for prime_id, sub_id in elements
                    for p_nnf_id, p_lits in [self.convert_node(prime_id)]
                    for s_nnf_id, s_lits in [self.convert_node(sub_id)]
                    # If any child is False, the term is False (p AND s = False)
                    # We skip False terms in an OR node
                    if self._id(False) not in [p_nnf_id, s_nnf_id]
                ]

                if not children_results:
                    # If all children are false or empty, this node is False
                    return self._const(False), []

                # Create OR Node
                or_nnf_id = next(self.nnf_node_counter)
                self.nnf_nodes_lines.append(f"o {or_nnf_id} 0")

                p_id: int
                s_id: int
                p_lits: list[int]
                s_lits: list[int]
                for p_id, p_lits, s_id, s_lits in children_results:
                    # We need to connect or_nnf_id to a structure representing (p AND s)

                    # Optimization: If both p and s connect to TrueNode
                    if self._id(True) == p_id == s_id:
                        # Term is (True ^ lits_p) ^ (True ^ lits_s) = True ^ (lits_p + lits_s)
                        self._add_edge(or_nnf_id, self._const(True), p_lits + s_lits)

                    elif self._id(True) == p_id:
                        # Term is (True ^ lits_p) ^ s = (lits_p) ^ s
                        self._add_edge(or_nnf_id, s_id, p_lits + s_lits)

                    elif self._id(True) == s_id:
                        # Term is p ^ (True ^ lits_s) = p ^ (lits_s)
                        self._add_edge(or_nnf_id, p_id, p_lits + s_lits)

                    else:
                        # General Case: Both are deep nodes. Need an AND node.
                        and_nnf_id = next(self.nnf_node_counter)
                        self.nnf_nodes_lines.append(f"a {and_nnf_id} 0")

                        # Connect OR -> AND
                        self._add_edge(or_nnf_id, and_nnf_id, [])

                        # Connect AND -> p
                        self._add_edge(and_nnf_id, p_id, p_lits)

                        # Connect AND -> s
                        self._add_edge(and_nnf_id, s_id, s_lits)

                return or_nnf_id, []

            case _:
                raise ValueError(f"Unknown node type for id {sdd_id}")

    def _add_edge(self, source: int, target: int, literals: list[int]) -> None:
        # Format: source target lit1 lit2 ... 0

        if literals:
            self.nnf_edges_lines.append(f"{source} {target} {" ".join(map(str, literals))} 0")
        else:
            self.nnf_edges_lines.append(f"{source} {target} 0")

    def convert(self, sdd_file: Path, nnf_file: Path) -> None:
        """Convert SDD file to NNF format."""
        self.parse_sdd(sdd_file)


        # Find root node (Convention: 0 or Max ID)
        # sdd.sdd provided has 'D 0 ...' as last line, suggesting 0 is root.
        # Common SDD convention: C library often returns root ID.
        # Here we guess: if 0 exists, it's root, else max.
        root_id: int = 0 if 0 in self.sdd_nodes else max(self.sdd_nodes.keys())

        # Convert starting from root
        self.convert_node(root_id)

        # Write NNF file
        with open(nnf_file, 'w') as f:
            f.writelines("\n".join(self.nnf_nodes_lines + self.nnf_edges_lines))


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print(f'Usage: python {Path(sys.argv[0]).name} <input.sdd> <output.nnf>')
        sys.exit(1)

    converter = SDDToNNFConverter()
    converter.convert(Path(sys.argv[1]), Path(sys.argv[2]))
