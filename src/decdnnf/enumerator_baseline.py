import gzip
import typing as t
from dataclasses import dataclass
from pathlib import Path

from pysmt.environment import Environment
from pysmt.fnode import FNode

from src.decdnnf import decdnnf
from src.tddnnf import abstraction


@dataclass(frozen=True)
class Arguments:
    cores: int
    models: Path
    mapping: Path


def enum(
        env: Environment,
        args: Arguments,
) -> t.Generator[dict[bool, list[FNode]]]:
    mapping: abstraction.i2atom = abstraction.read_mapping(env, args.mapping)

    with gzip.open(args.models, 'rt', encoding='utf-8') as f:
        mus: list[dict[bool, list[int]]] = list(decdnnf.parse(f))

    yield from (
        abstraction.convert(mapping, mu)
        for mu in mus
    )
