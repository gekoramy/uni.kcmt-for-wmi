import argparse
import dataclasses
import itertools as it
import typing
from datetime import timedelta
from pathlib import Path

import math
import polars as pl
from matplotlib import pyplot as plt


@dataclasses.dataclass(frozen=True)
class Timeout:
    enumerator: timedelta
    tlemmas: timedelta

def plot(
        df: pl.DataFrame,
        column: str,
        timeout: Timeout | None = None,
) -> plt.Figure:
    padding: float = 2

    enumerators_wout_tlemmas: list[str] = ['sae']
    enumerators_with_tlemmas: list[str] = ['decdnnf_baseline_d4', 'decdnnf_baseline_sdd']

    limit_enum: float
    limit_tlemmas: float
    limit_tlemmas_enum: float

    match timeout:
        case None:
            maximum: float = (
                df.select(
                    pl.col(f'{column}_{enum}')
                    for enum in enumerators_wout_tlemmas + enumerators_with_tlemmas
                )
                .max()
                .max_horizontal()
                .first()
            )

            limit_enum = padding * maximum
            limit_tlemmas = padding * maximum
            limit_tlemmas_enum = padding * padding * maximum

        case Timeout(tlemmas=tout_tlemmas, enumerator=tout_enumerator):
            limit_enum = tout_enumerator.seconds
            limit_tlemmas = tout_tlemmas.seconds
            limit_tlemmas_enum = (tout_tlemmas + tout_enumerator).seconds

    minimum: float = (
        df.select(
            pl.col(f'{column}_{enum}')
            for enum in enumerators_wout_tlemmas + enumerators_with_tlemmas
        )
        .min()
        .min_horizontal()
        .first()
    )

    nrows: int = 1
    ncols: int = sum((
        len(enumerators_wout_tlemmas) * len(enumerators_with_tlemmas),
        math.comb(len(enumerators_with_tlemmas), 2),
    ))
    fig, axs = plt.subplots(nrows, ncols, figsize=(6 * ncols, 6 * nrows))

    iter4axs: typing.Iterator[plt.Axes] = iter(axs)

    ax: plt.Axes
    for (enum_x, enum_y), ax in zip(
            it.product(enumerators_wout_tlemmas, enumerators_with_tlemmas),
            iter4axs,
    ):
        both: pl.DataFrame = (
            df.filter(
                pl.col(f'{column}_{enum_x}').is_not_null() & pl.col(f'{column}_{enum_y}').is_not_null()
            )
        )

        tout: pl.DataFrame = (
            df.filter(
                pl.col(f'{column}_{enum_x}').is_null() | pl.col(f'{column}_{enum_y}').is_null()
            )
        )

        ax.set_xscale('log')
        ax.set_yscale('log')

        ax.set_xlim(minimum, padding * limit_enum)
        ax.set_ylim(minimum, padding * limit_tlemmas_enum)

        ax.axvline(x=limit_enum, color='darkgrey', linestyle='--')
        ax.axhline(y=limit_tlemmas, color='darkgrey', linestyle='--')
        ax.axhline(y=limit_tlemmas_enum, color='darkgrey', linestyle='--')

        ax.plot(
            (minimum, padding * limit_tlemmas_enum),
            (minimum, padding * limit_tlemmas_enum),
            color='darkgrey',
            linestyle=':',
            linewidth=1,
        )

        ax.scatter(
            x=both.select_seq(pl.col(f'{column}_{enum_x}')),
            y=both.select_seq(pl.col(f'{column}_{enum_y}')),
            color='C0',
            alpha=.5,
        )

        tout_tlemmas_t: pl.DataFrame = tout.filter(pl.col('stderr_tlemmas').is_not_null())
        tout_tlemmas_f: pl.DataFrame = tout.filter(pl.col('stderr_tlemmas').is_null())

        ax.scatter(
            x=tout_tlemmas_t.select_seq(pl.col(f'{column}_{enum_x}').fill_null(limit_enum)),
            y=tout_tlemmas_t.select_seq(pl.col(f'{column}_{enum_y}').fill_null(limit_tlemmas)),
            marker='x',
            color='C1',
            alpha=.5,
        )

        ax.scatter(
            x=tout_tlemmas_f.select_seq(pl.col(f'{column}_{enum_x}').fill_null(limit_enum)),
            y=tout_tlemmas_f.select_seq(pl.col(f'{column}_{enum_y}').fill_null(limit_tlemmas_enum)),
            marker='x',
            color='C2',
            alpha=.5,
        )

        ax.set_xlabel(enum_x)
        ax.set_ylabel(enum_y)
        ax.set_aspect('equal')

    for (enum_x, enum_y), ax in zip(
            it.combinations(enumerators_with_tlemmas, 2),
            iter4axs
    ):
        both: pl.DataFrame = (
            df.filter(
                pl.col(f'{column}_{enum_x}').is_not_null() & pl.col(f'{column}_{enum_y}').is_not_null()
            )
        )

        tout: pl.DataFrame = (
            df.filter(
                pl.col(f'{column}_{enum_x}').is_null() | pl.col(f'{column}_{enum_y}').is_null()
            )
        )

        ax.set_xscale('log')
        ax.set_yscale('log')

        ax.set_xlim(minimum, padding * limit_tlemmas_enum)
        ax.set_ylim(minimum, padding * limit_tlemmas_enum)

        ax.axvline(x=limit_tlemmas, color='darkgrey', linestyle='--')
        ax.axvline(x=limit_tlemmas_enum, color='darkgrey', linestyle='--')
        ax.axhline(y=limit_tlemmas, color='darkgrey', linestyle='--')
        ax.axhline(y=limit_tlemmas_enum, color='darkgrey', linestyle='--')

        ax.plot(
            (minimum, padding * limit_tlemmas_enum),
            (minimum, padding * limit_tlemmas_enum),
            color='darkgrey',
            linestyle=':',
            linewidth=1,
        )

        ax.scatter(
            x=both.select_seq(pl.col(f'{column}_{enum_x}')),
            y=both.select_seq(pl.col(f'{column}_{enum_y}')),
            color='C0',
            alpha=.5,
        )

        tout_tlemmas_t: pl.DataFrame = tout.filter(pl.col('stderr_tlemmas').is_not_null())
        tout_tlemmas_f: pl.DataFrame = tout.filter(pl.col('stderr_tlemmas').is_null())

        ax.scatter(
            x=tout_tlemmas_t.select_seq(pl.col(f'{column}_{enum_x}').fill_null(limit_tlemmas)),
            y=tout_tlemmas_t.select_seq(pl.col(f'{column}_{enum_y}').fill_null(limit_tlemmas)),
            marker='x',
            color='C1',
            alpha=.5,
        )

        ax.scatter(
            x=tout_tlemmas_f.select_seq(pl.col(f'{column}_{enum_x}').fill_null(limit_tlemmas_enum)),
            y=tout_tlemmas_f.select_seq(pl.col(f'{column}_{enum_y}').fill_null(limit_tlemmas_enum)),
            marker='x',
            color='C2',
            alpha=.5,
        )

        ax.set_xlabel(enum_x)
        ax.set_ylabel(enum_y)
        ax.set_aspect('equal')

    fig.suptitle(column)
    return fig


def file(arg: str) -> Path:
    if not (path := Path(arg)).is_file():
        raise FileNotFoundError(path)

    return path


if __name__ == '__main__':
    parser: argparse.ArgumentParser = argparse.ArgumentParser()
    parser.add_argument('--csv', type=file, required=True)
    parser.add_argument('--column', type=str, required=True)
    parser.add_argument('--output', type=Path, required=True, nargs='+')
    parser.add_argument('--timeout_enumerator', type=int, required=True)
    parser.add_argument('--timeout_tlemmas', type=int, required=True)
    parser.add_argument('--type', type=str, required=False)
    args: argparse.Namespace = parser.parse_args()

    df: pl.DataFrame = pl.read_csv(
        args.csv,
        has_header=True,
    ).with_columns(
        pl.col('enumerating_sae').alias('enumerating full_sae'),
        *[
            (
                pl.col(f'enumerating_{enumerator}_{tddnnf}')
                .add(pl.col(f'total_tddnnf_{tddnnf}'))
                .add(pl.col('Partial AllSMT_tlemmas'))
                .add(pl.col('extract tlemmas_tlemmas'))
            ).alias(f'enumerating full_{enumerator}_{tddnnf}')
            for tddnnf in ['d4', 'sdd']
            for enumerator in ['decdnnf_baseline']
        ],
    ).with_columns(
        stderr_tlemmas=pl.coalesce(pl.col('^stderr_tlemmas$'), pl.lit(None))
    )

    fig: plt.Figure
    match args.type:
        case 'time':
            fig = plot(df, args.column, Timeout(
                enumerator=timedelta(minutes=args.timeout_enumerator),
                tlemmas=timedelta(minutes=args.timeout_tlemmas),
            ))

        case _:
            fig = plot(df, args.column)

    for out in args.output:
        fig.savefig(out)
