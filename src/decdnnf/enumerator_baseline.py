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
    mapping: abstraction.i2atom


def enum(
        args: Arguments,
) -> t.Generator[dict[bool, list[FNode]]]:
    with gzip.open(args.models, 'rt', encoding='utf-8') as f:
        mus: list[dict[bool, list[int]]] = list(decdnnf.parse(f))

    yield from (
        abstraction.convert(args.mapping, mu)
        for mu in mus
    )
