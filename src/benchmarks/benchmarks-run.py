import itertools as it
import logging
import os.path
import subprocess
import sys
from datetime import timedelta
from pathlib import Path
from subprocess import CompletedProcess, TimeoutExpired

from math import prod
from tqdm import tqdm

handler: logging.Handler = logging.StreamHandler(sys.stderr)
handler.setFormatter(logging.Formatter('%(asctime)s :: %(levelname)-4s :: %(message)s'))

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
logger.propagate = False
logger.addHandler(handler)


def extract_ndjson(path: Path):
    with (
        open(path.rename(path.with_suffix('.log')), 'rt') as log,
        open(path, 'wt') as ndjson,
    ):
        ndjson.writelines(
            it.takewhile(
                lambda line: line.startswith('{'),
                log,
            )
        )


if __name__ == '__main__':
    wdr: Path = Path(__file__).parent.parent.parent
    src: Path = wdr / 'src'
    rsc: Path = wdr / 'resources'

    results: Path = rsc / 'results'
    results.mkdir(exist_ok=True)

    tlemmas: Path = results / 'tlemmas'
    tlemmas.mkdir(exist_ok=True)

    enumerators: list[str] = ['sae', 'd4', 'sdd']
    integrators: list[str] = ['noop']
    densities: list[Path] = [
        density
        for density in (rsc / 'densities').rglob('*.json', recurse_symlinks=True)
        if 0 != os.path.getsize(density)
    ]

    logger.debug(f'compute tlemmas')

    with tqdm(
            iterable=densities,
            ascii=' ⠁⠃⠇⠏⠟⠯⠷⠿⡿⣟⣯⣷⣾⣿',
            bar_format='{bar} {n_fmt}/{total_fmt} {elapsed}/{remaining}',
    ) as todo:

        for density in todo:

            path_xxx = tlemmas / f'{density.name}.timeout'
            path_err = tlemmas / f'{density.name}-stderr.ndjson'
            path_out = tlemmas / f'{density.name}.smt2'

            if any(path.exists() for path in (path_out, path_xxx)):
                logger.warning(f'skipping computing tlemmas for {density}')
                continue

            with (
                open(path_err, 'wt') as err,
            ):
                try:
                    p4tlemmas: CompletedProcess[str] = (
                        subprocess.run(
                            [
                                'python',
                                '-m',
                                'src.tlemmas',
                                f'--density={density.as_posix()}',
                                f'--tlemmas={path_out}',
                            ],
                            cwd=wdr,
                            text=True,
                            timeout=timedelta(minutes=20).total_seconds(),
                            stdout=None,
                            stderr=err,
                        )
                    )

                    if 0 != p4tlemmas.returncode:
                        logger.error(f'tlemmas {density} non-zero exit')
                        path_xxx.touch(exist_ok=True)

                except TimeoutExpired:
                    logger.warning(f'tlemmas {density} timed out')
                    path_xxx.touch(exist_ok=True)
                    extract_ndjson(path_err)

    logger.debug(f'compute wmi')

    with tqdm(
            iterable=it.product(enumerators, integrators, densities),
            total=prod(map(len, (enumerators, integrators, densities))),
            ascii=' ⠁⠃⠇⠏⠟⠯⠷⠿⡿⣟⣯⣷⣾⣿',
            bar_format='{bar} {n_fmt}/{total_fmt} {elapsed}/{remaining}',
    ) as todo:

        for enumerator, integrator, density in todo:

            path_err = results / f'{enumerator}-{integrator}-{density.name}-stderr.ndjson'
            path_out = results / f'{enumerator}-{integrator}-{density.name}-stdout.ndjson'
            path_tlemmas = tlemmas / f'{density.name}.smt2'

            with (
                open(path_out, 'wt') as out,
                open(path_err, 'wt') as err,
            ):
                try:
                    p4wmi: CompletedProcess[str] = (
                        subprocess.run(
                            [
                                'python',
                                '-m',
                                'src.wmi',
                                f'--density={density.as_posix()}',
                                f'--enumerator={enumerator}',
                                f'--integrator={integrator}',
                                f'--tlemmas={path_tlemmas.as_posix()}',
                            ],
                            cwd=wdr,
                            text=True,
                            timeout=timedelta(minutes=10).total_seconds(),
                            stdout=out,
                            stderr=err,
                        )
                    )

                    if 0 != p4wmi.returncode:
                        logger.error(f'{enumerator} {integrator} {density} non-zero exit')
                        path_err.rename(path_err.with_suffix('.log'))
                        path_err.touch()

                except TimeoutExpired:
                    logger.warning(f'{enumerator} {integrator} {density} timed out')
                    extract_ndjson(path_err)
