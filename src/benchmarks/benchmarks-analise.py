import itertools as it
import logging
import os
import sys
from pathlib import Path

import polars as pl

handler: logging.Handler = logging.StreamHandler(sys.stderr)
handler.setFormatter(logging.Formatter('%(asctime)s :: %(levelname)-4s :: %(message)s'))

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
logger.propagate = False
logger.addHandler(handler)


def read_tlemmas(
        tlemmas: Path,
        densities: list[Path],
) -> pl.DataFrame:
    df_tlemmas: list[pl.DataFrame] = []

    for density in densities:
        df_density: pl.DataFrame = pl.DataFrame({'density': density.name})

        err: Path = tlemmas / f'{density.name}-stderr.ndjson'

        df_err: pl.DataFrame = (
            pl.read_ndjson(err, schema={'step': pl.String, 'took': pl.Float64})
        )

        df_tlemmas.append(
            df_err.join(df_density, how='cross')
        )

    return (
        pl
        .concat(df_tlemmas, how="vertical")
        .pivot(on=pl.col('step'), index=pl.col('density'))
    )


def read_enumerators(
        results: Path,
        densities: list[Path],
        enumerators: list[str],
        integrators: list[str],
) -> pl.DataFrame:
    dfs: list[pl.DataFrame] = []

    for density in densities:

        df_density: pl.DataFrame = pl.DataFrame({'density': density.name})

        for enumerator, integrator in it.product(enumerators, integrators):
            df_enumerator: pl.DataFrame = pl.DataFrame({'enumerator': enumerator})

            logger.debug(f'{enumerator} {integrator} {density.name}')

            err: Path = results / f'{enumerator}-{integrator}-{density.name}-stderr.ndjson'
            out: Path = results / f'{enumerator}-{integrator}-{density.name}-stdout.ndjson'

            if not err.exists():
                continue

            # read
            df_err: pl.DataFrame = (
                pl.read_ndjson(err, schema={'step': pl.String, 'took': pl.Float64})
            )
            df_out: pl.DataFrame = (
                pl.read_ndjson(out, schema={'wmi': pl.Float64, 'npolys': pl.Int64})
                if out.exists()
                else pl.DataFrame()
            )

            dfs.append(
                df_err
                .join(df_density, how='cross')
                .pivot(on=pl.col('step'), index=pl.col('density'))
                .join(df_out, how='cross')
                .join(df_enumerator, how='cross')
            )

    merge: pl.DataFrame = (
        pl
        .concat(dfs, how='diagonal')
        .pivot(on=pl.col('enumerator'), index=pl.col('density'))
    )

    # filter out null-only columns
    return merge.select(col.name for col in merge if col.count())


if __name__ == '__main__':
    wdr: Path = Path(__file__).parent.parent.parent
    rsc: Path = wdr / 'resources'

    results: Path = rsc / 'results'
    assert results.exists()

    tlemmas: Path = results / 'tlemmas'
    assert tlemmas.exists()

    enumerators = ['sae', 'd4', 'sdd']
    integrators = ['noop']
    densities: list[Path] = [
        density
        for density in (rsc / 'densities').rglob('*-1.json', recurse_symlinks=True)
        if 0 != os.path.getsize(density)
    ]

    df_tlemmas = read_tlemmas(tlemmas, densities)

    df_enumerators = read_enumerators(results, densities, enumerators, integrators)

    merge = df_enumerators.join(df_tlemmas, on=pl.col('density'), how='left')

    merge.write_csv(rsc / "merge.csv")
