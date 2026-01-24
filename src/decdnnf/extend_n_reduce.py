import argparse
import gzip
from multiprocessing.pool import Pool
from pathlib import Path

from ddnnife import Ddnnf, DdnnfMut

from src import utils
from src.decdnnf import decdnnf

_ddnnf: DdnnfMut


def _init_worker(t_reduced_phi: Path) -> None:
    global _ddnnf
    _ddnnf = Ddnnf.from_file(t_reduced_phi.as_posix(), None).as_mut()


def is_satisfiable(model: dict[bool, list[int]]) -> bool:
    global _ddnnf
    return _ddnnf.is_sat([
        *model[True],
        *(-atom for atom in model[False])
    ])


def main() -> None:
    with utils.use(argparse.ArgumentParser()) as parser:
        parser.add_argument('--cores', type=int, required=True)
        parser.add_argument('--models', type=utils.file, required=True)
        parser.add_argument('--t_reduced_phi', type=utils.file, required=True)
        parser.add_argument('--output', type=Path, required=True)
        args: argparse.Namespace = parser.parse_args()

    with gzip.open(args.models, 'rt', encoding='utf-8') as f:
        models: list[dict[bool, list[int]]] = list(decdnnf.parse(f))

    with Pool(args.cores, initializer=_init_worker, initargs=(args.t_reduced_phi,)) as pool:
        t_sat: list[bool] = pool.map(
            is_satisfiable,
            models,
        )

    decdnnf.write_models(args.output, [mu for mu, is_t_sat in zip(models, t_sat) if is_t_sat])


if __name__ == '__main__':
    main()
