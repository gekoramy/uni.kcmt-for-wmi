import re
import typing as t
from pathlib import Path

import polars as pl


def patch(path: Path) -> str:
    return re.sub(r'[\[\]]', '?', path.as_posix())


def parse_data(
        who: str,
        path: Path
) -> pl.DataFrame:
    match path.suffix:
        case '.steps':
            data: pl.DataFrame = pl.read_ndjson(
                patch(path),
                schema={'step': pl.String, 'took': pl.Float64},
            )
            data = (
                data
                .with_columns(pl.lit(True).alias('tmp'))
                .pivot(on=pl.col('step'), index=pl.col('tmp'))
                .select(pl.all().exclude('tmp'))
            )

        case '.out':
            data: pl.DataFrame = pl.read_json(
                path,
                schema={'wmi': pl.Float64, 'npolys': pl.Int64}
            )

        case '.err':
            text: str = path.read_text()
            data: pl.DataFrame = pl.DataFrame({'stderr': text})

        case '.jsonl':
            data: pl.DataFrame = pl.read_ndjson(
                patch(path),
                schema={
                    'cpu_time': pl.Float64,
                    'h:m:s': pl.String,
                    'io_in': pl.Float64,
                    'io_out': pl.Float64,
                    'max_pss': pl.Float64,
                    'max_rss': pl.Float64,
                    'max_uss': pl.Float64,
                    'max_vms': pl.Float64,
                    'mean_load': pl.Float64,
                    's': pl.Float64,
                }
            )

    return data.with_columns(
        pl.lit(path.stem).alias('density'),
        pl.lit(who).alias('who'),
    )


def main(who2paths: dict[str, list[Path]], output: Path) -> None:
    if (
            unknown := (next(
                (
                        path
                        for paths in who2paths.values()
                        for path in paths
                        if path.suffix not in ('.steps', '.out', '.err', '.jsonl')
                ),
                None,
            ))
    ):
        raise RuntimeError(f"unknown scheme: {unknown}")

    dataframes: t.Iterable[pl.DataFrame] = [
        parse_data(who, path)
        for who, paths in who2paths.items()
        for path in paths
        if path.stat().st_size > 0
    ]

    stacked: pl.DataFrame = pl.concat(dataframes, how='diagonal')

    merged: pl.DataFrame = (
        stacked
        .group_by(['density', 'who'])
        .agg(pl.all().first(ignore_nulls=True))
    )

    pivoted: pl.DataFrame = merged.pivot(on=pl.col('who'), index=pl.col('density'))

    final: pl.DataFrame = pivoted.select(col.name for col in pivoted if col.count())

    final.write_csv(output.as_posix())


if __name__ == '__main__':
    main(
        who2paths={name: [Path(file) for file in files] for name, files in snakemake.input.items()},
        output=Path(snakemake.output[0]),
    )
