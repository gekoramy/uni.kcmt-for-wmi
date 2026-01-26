import re
import subprocess
import sys
import typing as t
from dataclasses import dataclass
from pathlib import Path

b2regex: frozenset[tuple[bool, re.Pattern]] = frozenset([
    (False, re.compile(r'-(\d+)')),
    (True, re.compile(r' (\d+)')),
])


@dataclass
class NNF:
    models: int
    vars: int
    nodes: int
    edges: int


def args(
        cores: int,
        nnf: Path,
) -> list[str]:
    return [
        'decdnnf_rs',
        'model-enumeration',
        '--compact-free-vars',
        '--logging-level', 'off',
        '--input', nnf.as_posix(),
        *(
            ['--threads', str(cores)]
            if cores > 1
            else []
        )
    ]


def pipe(cores: int, nnf: Path) -> t.Generator[dict[bool, list[int]]]:
    decdnnf: subprocess.Popen[str] = subprocess.Popen(
        args=args(cores=cores, nnf=nnf),
        encoding='utf-8',
        stdout=subprocess.PIPE,
        stderr=sys.stderr,
    )

    yield from parse(decdnnf.stdout)

    assert 0 == (code := decdnnf.wait()), f"decdnnf exited with code {code}"


def raw(cores: int, nnf: Path) -> t.Generator[dict[bool, list[int]]]:
    decdnnf: subprocess.CompletedProcess[str] = subprocess.run(
        args=args(cores=cores, nnf=nnf),
        encoding='utf-8',
        capture_output=True,
    )

    assert 0 == decdnnf.returncode, decdnnf.stdout

    yield from parse(decdnnf.stdout.splitlines())


def ta(nnf: Path) -> NNF:
    decdnnf: subprocess.CompletedProcess[str] = subprocess.run(
        args=[
            'decdnnf_rs',
            'model-counting',
            '--compact-free-vars',
            '--input', nnf.as_posix(),
        ],
        encoding='utf-8',
        capture_output=True,
    )

    assert 0 == decdnnf.returncode, decdnnf.stdout

    matches: dict[str, int] = {
        key: int(value)
        for key, value in re.findall(r'number of (\w+): (\d+)', decdnnf.stderr)
    }

    return NNF(
        models=int(decdnnf.stdout),
        vars=matches['variables'],
        nodes=matches['nodes'],
        edges=matches['edges'],
    )


def parse(lines: t.Iterable[str]) -> t.Generator[dict[bool, list[int]]]:
    yield from (
        {
            boolean: [int(l) for l in regex.findall(line.strip().removesuffix('0'))]
            for boolean, regex in b2regex
        }
        for line in lines
    )


def write_models(
        output: Path,
        models: t.Iterable[dict[bool, list[int]]],
) -> None:
    with open(output, 'w', encoding='utf-8') as f:
        f.writelines(
            part
            for model in models
            for part in (
                write_model(model),
                '\n'
            )
        )


def write_model(
        mu: dict[bool, list[int]]
) -> str:
    return f'v {' '.join([
        *[f' {atom}' for atom in mu[True]],
        *[f'-{atom}' for atom in mu[False]],
    ])} 0'
