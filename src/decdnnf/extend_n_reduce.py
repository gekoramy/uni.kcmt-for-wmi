import argparse
import itertools as it
import subprocess
from multiprocessing.pool import Pool
from pathlib import Path

from src import utils
from src.decdnnf import decdnnf


def is_satisfiable(
        t_reduced_phi: Path,
        model_t_extended_phi: dict[bool, list[int]],
) -> bool:
    decdnnf: subprocess.CompletedProcess[str] = subprocess.run(
        args=[
            'decdnnf_rs',
            'compute-model',
            '--logging-level', 'off',
            '--input', t_reduced_phi.as_posix(),
            '--assumptions', ' '.join(map(str, [
                *model_t_extended_phi[True],
                *(-atom for atom in model_t_extended_phi[False])
            ])),
        ],
        capture_output=True,
        encoding='utf-8',
    )

    assert 0 == decdnnf.returncode, decdnnf.stdout

    return 'UNSATISFIABLE' not in decdnnf.stdout


def main() -> None:
    with utils.use(argparse.ArgumentParser()) as parser:
        parser.add_argument('--cores', type=int, required=True)
        parser.add_argument('--models_t_extended_phi', type=utils.file, required=True)
        parser.add_argument('--t_reduced_phi', type=utils.file, required=True)
        parser.add_argument('--output', type=Path, required=True)
        args: argparse.Namespace = parser.parse_args()

    with open(args.models_t_extended_phi, 'r', encoding='utf-8') as f:
        models_t_extended_phi: list[dict[bool, list[int]]] = list(decdnnf.parse(f))

    with Pool(args.cores) as pool:
        t_sat: list[bool] = pool.starmap(
            is_satisfiable,
            zip(
                it.cycle([args.t_reduced_phi]),
                models_t_extended_phi,
            )
        )

    decdnnf.write_models(args.output, [mu for mu, is_t_sat in zip(models_t_extended_phi, t_sat) if is_t_sat])


if __name__ == '__main__':
    main()
