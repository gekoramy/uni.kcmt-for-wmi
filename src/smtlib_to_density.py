import argparse
from pathlib import Path

from pysmt.environment import Environment, get_env
from pysmt.fnode import FNode
from pysmt.smtlib.parser import SmtLibParser
from wmpy.cli.density import Density

from src import utils


def translate(smtlib: Path, density: tuple[Path, Path]) -> None:
    env: Environment = get_env()
    original: Density = Density.from_file(density[0].as_posix())

    with open(smtlib, 'r', encoding='utf-8') as f:
        parser: SmtLibParser = SmtLibParser(environment=env)
        phi: FNode = parser.get_script(f).get_last_formula()

    changed: Density = Density(
        support=phi,
        weights=original.weights,
        domain=original.domain,
        queries=original.queries,
    )

    changed.to_file(density[1].as_posix())


def main() -> None:
    parser: argparse.ArgumentParser = argparse.ArgumentParser()
    parser.add_argument('--smtlib', type=utils.file, required=True)
    parser.add_argument('--density', type=Path, nargs=2, required=True)
    args: argparse.Namespace = parser.parse_args()

    translate(smtlib=args.smtlib, density=args.density)


if __name__ == '__main__':
    main()
