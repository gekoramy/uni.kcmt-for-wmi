import argparse
import typing as t
import multiprocessing as mp
from pathlib import Path

from ddnnife import Ddnnf, DdnnfMut

from src import utils
from src.decdnnf import decdnnf

_ddnnf: Ddnnf
_ddnnf_mut: DdnnfMut


def _init_worker() -> None:
    global _ddnnf, _ddnnf_mut
    _ddnnf_mut = _ddnnf.as_mut()


def if_satisfiable(model: dict[bool, list[int]]) -> dict[bool, list[int]] | None:
    global _ddnnf_mut
    is_sat: bool = _ddnnf_mut.is_sat([
        *model[True],
        *(-atom for atom in model[False])
    ])
    return model if is_sat else None


def main() -> None:
    with utils.use(argparse.ArgumentParser()) as parser:
        parser.add_argument('--cores', type=int, required=True)
        parser.add_argument('--phi', type=utils.file, required=True)
        parser.add_argument('--t_sat', type=utils.file, required=True)
        parser.add_argument('--output', type=Path, required=True)
        args: argparse.Namespace = parser.parse_args()

    assert args.cores > 1
    global _ddnnf
    _ddnnf = Ddnnf.from_file(args.t_sat.as_posix(), None)

    mp.set_start_method('fork')

    cores4decdnnf: int = 1
    cores4ddnnife: int = args.cores - cores4decdnnf

    with mp.Pool(cores4ddnnife, initializer=_init_worker, initargs=()) as pool:
        models: t.Generator[dict[bool, list[int]]] = decdnnf.pipe(cores4decdnnf, args.phi)

        t_sat: t.Iterator[dict[bool, list[int]] | None] = pool.imap_unordered(
            if_satisfiable,
            models,
            chunksize=cores4ddnnife,
        )

        decdnnf.write_models(args.output, [mu for mu in t_sat if mu])


if __name__ == '__main__':
    main()
