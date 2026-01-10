import typing as t
from dataclasses import dataclass
from pathlib import Path

from pysmt.environment import Environment
from pysmt.fnode import FNode

from src.decdnnf import decdnnf
from src.tddnnf import tlemmas


@dataclass(frozen=True)
class Arguments:
    cores: int
    models: Path
    mapping: Path


def enum(
        env: Environment,
        args: Arguments,
) -> t.Generator[dict[bool, list[FNode]]]:
    mapping: dict[int, FNode] = tlemmas.read_mapping(env, args.mapping)

    with open(args.models, 'rt') as f:
        mus: list[dict[bool, list[int]]] = list(decdnnf.parse(f))

    yield from (
        tlemmas.convert(mapping, mu)
        for mu in mus
    )
