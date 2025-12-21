import re
import typing as t
from pathlib import Path
from re import Pattern

import polars as pl


def patch(path: Path) -> str:
    return re.sub(r'[\[\]]', '?', path.as_posix())


def parse_data(
        path: Path,
        who: str,
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

    return data.with_columns(
        pl.lit(path.stem).alias('density'),
        pl.lit(who).alias('who'),
    )


def main(paths: list[Path], output: Path) -> None:
    pattern4who: Pattern[str] = re.compile(r'.*/(?P<who>sae|d4|sdd|tlemmas)/.*')

    matches: list[re.Match | None] = [
        pattern4who.fullmatch(path.as_posix())
        for path in paths
    ]

    if (
            unknown := (next(
                (
                        path
                        for path in paths
                        if path.suffix not in ('.steps', '.out', '.err')
                ),
                None,
            ))
    ):
        raise RuntimeError(f"unknown scheme: {unknown}")

    if (
            unknown := (next(
                (
                        path
                        for path, who in zip(paths, matches)
                        if who is None
                ),
                None,
            ))
    ):
        raise RuntimeError(f'unknown who: {unknown}')

    dataframes: t.Iterable[pl.DataFrame] = [
        parse_data(density, match.group('who'))
        for density, match in zip(paths, matches)
        if density.stat().st_size > 0
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
        paths=[Path(path) for path in snakemake.input],
        output=Path(snakemake.output[0]),
    )
