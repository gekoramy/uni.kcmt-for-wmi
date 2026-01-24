import argparse
import typing as t
from multiprocessing.pool import Pool
from pathlib import Path

from ddnnife import Ddnnf, DdnnfMut

from src import utils
from src.decdnnf import decdnnf

_ddnnf: DdnnfMut


def _init_worker(t_reduced_phi: Path) -> None:
    global _ddnnf
    _ddnnf = Ddnnf.from_file(t_reduced_phi.as_posix(), None).as_mut()


def if_satisfiable(model: dict[bool, list[int]]) -> dict[bool, list[int]] | None:
    global _ddnnf
    is_sat: bool = _ddnnf.is_sat([
        *model[True],
        *(-atom for atom in model[False])
    ])
    return model if is_sat else None


def main() -> None:
    with utils.use(argparse.ArgumentParser()) as parser:
        parser.add_argument('--cores', type=int, required=True)
        parser.add_argument('--phi', type=utils.file, required=True)
        parser.add_argument('--t_reduced_phi', type=utils.file, required=True)
        parser.add_argument('--output', type=Path, required=True)
        args: argparse.Namespace = parser.parse_args()

    assert args.cores > 1

    cores4decdnnf: int = max(1, args.cores // 3)
    cores4ddnnife: int = args.cores - cores4decdnnf

    models: t.Generator[dict[bool, list[int]]] = decdnnf.pipe(cores4decdnnf, args.phi)

    with Pool(cores4ddnnife, initializer=_init_worker, initargs=(args.t_reduced_phi,)) as pool:
        t_sat: t.Iterator[dict[bool, list[int]] | None] = pool.imap_unordered(
            if_satisfiable,
            models,
        )

        decdnnf.write_models(args.output, [mu for mu in t_sat if mu])


if __name__ == '__main__':
    main()
