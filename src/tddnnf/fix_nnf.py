import argparse
import re
from pathlib import Path

p4edge: re.Pattern[str] = re.compile(r'^(\d+ \d+ )(.*)( 0\s*)$')
p4lits: re.Pattern[str] = re.compile(r'(-?)(\d+)')


def fixing(line: str) -> str:
    """
    >>> fixing('o 1 0')
    'o 1 0'

    >>> fixing('t 2 0')
    't 2 0'

    >>> fixing('1 2 3 -4 0')
    '1 2 2 -3 0'
    """

    return p4edge.sub(
        lambda m: ''.join((
            m[1],
            p4lits.sub(
                lambda mm: f'{mm[1]}{int(mm[2]) - 1}',
                m[2]
            ),
            m[3],
        )),
        line,
    )


def fix(nnf: tuple[Path, Path]) -> None:
    with open(nnf[0], 'rt') as fr, open(nnf[1], 'wt') as fw:
        fw.writelines(
            fixing(line)
            for line in fr
        )


def main() -> None:
    parser: argparse.ArgumentParser = argparse.ArgumentParser()
    parser.add_argument('--nnf', nargs=2, type=Path, required=True)
    args: argparse.Namespace = parser.parse_args()

    fix(args.nnf)


if __name__ == '__main__':
    main()
