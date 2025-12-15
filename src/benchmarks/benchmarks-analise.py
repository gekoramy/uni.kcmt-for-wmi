import itertools as it
from pathlib import Path

import polars as pl

if __name__ == '__main__':

    wdr: Path = Path(__file__).parent.parent.parent
    rsc: Path = wdr / 'resources'

    results: Path = rsc / 'results'
    assert results.exists()

    enumerators = ['sae', 'd4', 'cudd']
    integrators = ['noop']
    densities = (rsc / 'densities').rglob('*.json', recurse_symlinks=True)

    dataframes: list[pl.DataFrame] = []

    for density in densities:

        df_density: pl.DataFrame = pl.DataFrame({'density': density.name})

        for enumerator, integrator in it.product(enumerators, integrators):
            df_enumerator: pl.DataFrame = pl.DataFrame({'enumerator': enumerator})

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

            dataframes.append(
                df_err
                .join(df_density, how='cross')
                .pivot(on=pl.col('step'), index=pl.col('density'))
                .join(df_out, how='cross')
                .join(df_enumerator, how='cross')
            )

    merge_raw = (
        pl
        .concat(dataframes, how='diagonal')
        .pivot(on=pl.col('enumerator'), index=pl.col('density'))
    )

    # filter out null-only columns
    (
        merge_raw.select(
            col.name
            for col in merge_raw
            if col.count()
        )
        .write_csv(rsc / "merge.csv")
    )
