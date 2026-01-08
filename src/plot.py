import argparse
import dataclasses
import itertools as it
import typing
from datetime import timedelta
from difflib import SequenceMatcher
from pathlib import Path

import math
import numpy as np
import polars as pl
from matplotlib import pyplot as plt, transforms, ticker, collections
from numpy import ndarray

from src import utils


@dataclasses.dataclass(frozen=True)
class Timeout:
    enumerator: timedelta
    compilator: timedelta
    tlemmas: timedelta


enumerator2steps: dict[str, list[str]] = {
    'sae': [
        'sae'
    ],
    **{
        f'decdnnf_baseline_{compiler}': [
            'tlemmas',
            f'tddnnf_{compiler}',
            f'decdnnf_{compiler}',
            f'decdnnf_baseline_{compiler}',
        ]
        for compiler in ['d4', 'sdd']
    },
    **{
        f'decdnnf_two_steps_exists_{qo}_{compiler}': [
            'tlemmas',
            f'tddnnf_{compiler}',
            f'tddnnf_exists_{qo}_{compiler}',
            f'decdnnf_exists_{qo}_{compiler}',
            f'decdnnf_two_steps_exists_{qo}_{compiler}',
        ]
        for compiler in ['d4', 'sdd']
        for qo in 'xA'
    },
}


def plot(
        df: pl.DataFrame,
        column: str,
        timeout: Timeout | None = None,
) -> plt.Figure:
    padding: float = 2

    enumerators_wout_tlemmas: list[str] = ['sae']
    enumerators_with_tlemmas: list[str] = list(sorted(enumerator2steps.keys() - {'sae'}))

    limit_enum: float
    limit_tlemmas: float
    limit_tlemmas_comp: float
    limit_tlemmas_comp_enum: float

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
            limit_tlemmas_comp = padding * padding * maximum
            limit_tlemmas_comp_enum = padding * padding * padding * maximum

        case Timeout(tlemmas=tout_tlemmas, compilator=tout_compilator, enumerator=tout_enumerator):
            limit_enum = tout_enumerator.seconds
            limit_tlemmas = tout_tlemmas.seconds
            limit_tlemmas_comp = (tout_tlemmas + tout_compilator).seconds
            limit_tlemmas_comp_enum = (tout_tlemmas + tout_compilator + tout_enumerator).seconds

    minimum: float = (
        df.select(
            pl.col(f'{column}_{enum}')
            for enum in enumerators_wout_tlemmas + enumerators_with_tlemmas
        )
        .min()
        .min_horizontal()
        .first()
    )

    tot: int = sum((
        len(enumerators_wout_tlemmas) * len(enumerators_with_tlemmas),
        math.comb(len(enumerators_with_tlemmas), 2),
    ))
    nrows: int = 3
    ncols: int = math.ceil(tot / nrows)
    fig, axs = plt.subplots(nrows, ncols, figsize=(6 * ncols, 6 * nrows))

    iter4axs: typing.Iterator[plt.Axes] = iter(it.chain(*axs))

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
        ax.set_ylim(minimum, padding * limit_tlemmas_comp_enum)

        ax.axvline(x=limit_enum, color='darkgrey', linestyle='--')
        ax.axhline(y=limit_tlemmas, color='darkgrey', linestyle='--')
        ax.axhline(y=limit_tlemmas_comp, color='darkgrey', linestyle='--')
        ax.axhline(y=limit_tlemmas_comp_enum, color='darkgrey', linestyle='--')

        ax.plot(
            (minimum, padding * limit_tlemmas_comp_enum),
            (minimum, padding * limit_tlemmas_comp_enum),
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

        tout_tlemmas: pl.DataFrame = tout.filter(pl.col('stderr_tlemmas').is_not_null())
        tout_enum: pl.DataFrame = tout.filter(pl.col(f'stderr_{enum_y}').is_not_null())
        tout_comp: pl.DataFrame = tout.filter(
            pl.col('stderr_tlemmas').is_null(),
            pl.col(f'stderr_{enum_y}').is_null(),
        )

        ax.scatter(
            x=tout_tlemmas.select_seq(pl.col(f'{column}_{enum_x}').fill_null(limit_enum)),
            y=tout_tlemmas.select_seq(pl.col(f'{column}_{enum_y}').fill_null(limit_tlemmas)),
            marker='x',
            color='C1',
            alpha=.5,
        )

        ax.scatter(
            x=tout_comp.select_seq(pl.col(f'{column}_{enum_x}').fill_null(limit_enum)),
            y=tout_comp.select_seq(pl.col(f'{column}_{enum_y}').fill_null(limit_tlemmas_comp)),
            marker='x',
            color='C2',
            alpha=.5,
        )

        ax.scatter(
            x=tout_enum.select_seq(pl.col(f'{column}_{enum_x}').fill_null(limit_enum)),
            y=tout_enum.select_seq(pl.col(f'{column}_{enum_y}').fill_null(limit_tlemmas_comp_enum)),
            marker='x',
            color='C3',
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

        ax.set_xlim(minimum, padding * limit_tlemmas_comp_enum)
        ax.set_ylim(minimum, padding * limit_tlemmas_comp_enum)

        ax.axvline(x=limit_tlemmas, color='darkgrey', linestyle='--')
        ax.axvline(x=limit_tlemmas_comp, color='darkgrey', linestyle='--')
        ax.axvline(x=limit_tlemmas_comp_enum, color='darkgrey', linestyle='--')
        ax.axhline(y=limit_tlemmas, color='darkgrey', linestyle='--')
        ax.axhline(y=limit_tlemmas_comp, color='darkgrey', linestyle='--')
        ax.axhline(y=limit_tlemmas_comp_enum, color='darkgrey', linestyle='--')

        ax.plot(
            (minimum, padding * limit_tlemmas_comp_enum),
            (minimum, padding * limit_tlemmas_comp_enum),
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

        tout_tlemmas: pl.DataFrame = tout.filter(pl.col('stderr_tlemmas').is_not_null())
        tout_only_x: pl.DataFrame = tout.filter(
            pl.col('stderr_tlemmas').is_null(),
            pl.col(f'stderr_{enum_x}').is_not_null(),
            pl.col(f'stderr_{enum_y}').is_null(),
        )
        tout_only_y: pl.DataFrame = tout.filter(
            pl.col('stderr_tlemmas').is_null(),
            pl.col(f'stderr_{enum_x}').is_null(),
            pl.col(f'stderr_{enum_y}').is_not_null(),
        )
        tout_both: pl.DataFrame = tout.filter(
            pl.col('stderr_tlemmas').is_null(),
            pl.col(f'stderr_{enum_x}').is_not_null(),
            pl.col(f'stderr_{enum_y}').is_not_null(),
        )
        tout_comp: pl.DataFrame = tout.filter(
            pl.col('stderr_tlemmas').is_null(),
            pl.col(f'stderr_{enum_x}').is_null(),
            pl.col(f'stderr_{enum_y}').is_null(),
        )

        ax.scatter(
            x=tout_tlemmas.select_seq(pl.col(f'{column}_{enum_x}').fill_null(limit_tlemmas)),
            y=tout_tlemmas.select_seq(pl.col(f'{column}_{enum_y}').fill_null(limit_tlemmas)),
            marker='x',
            color='C1',
            alpha=.5,
        )

        ax.scatter(
            x=tout_comp.select_seq(pl.col(f'{column}_{enum_x}').fill_null(limit_tlemmas_comp)),
            y=tout_comp.select_seq(pl.col(f'{column}_{enum_y}').fill_null(limit_tlemmas_comp)),
            marker='x',
            color='C2',
            alpha=.5,
        )

        ax.scatter(
            x=tout_only_x.select_seq(pl.col(f'{column}_{enum_x}').fill_null(limit_tlemmas_comp_enum)),
            y=tout_only_x.select_seq(pl.col(f'{column}_{enum_y}')),
            marker='x',
            color='C3',
            alpha=.5,
        )

        ax.scatter(
            x=tout_only_y.select_seq(pl.col(f'{column}_{enum_x}')),
            y=tout_only_y.select_seq(pl.col(f'{column}_{enum_y}').fill_null(limit_tlemmas_comp_enum)),
            marker='x',
            color='C3',
            alpha=.5,
        )

        ax.scatter(
            x=tout_both.select_seq(pl.col(f'{column}_{enum_x}').fill_null(limit_tlemmas_comp_enum)),
            y=tout_both.select_seq(pl.col(f'{column}_{enum_y}').fill_null(limit_tlemmas_comp_enum)),
            marker='x',
            color='C3',
            alpha=.5,
        )

        ax.set_xlabel(enum_x)
        ax.set_ylabel(enum_y)
        ax.set_aspect('equal')

    fig.suptitle(column)
    return fig


def models_to_npolys(
        df: pl.DataFrame
) -> plt.Figure:
    padding: int = 2

    steps: list[list[str]] = [
        filtered
        for steps in enumerator2steps.values()
        if (filtered := [
            step
            for step in steps
            if 'decdnnf' in step and 'exists' in step
        ])
    ]

    columns: list[tuple[str, str]] = [
        (f'models_{a}', f'npolys_{b}')
        for a, b in steps
    ]

    sdf: pl.DataFrame = (
        df
        .select(
            *it.chain(*columns)
        )
    )

    minimum: int = (
        sdf
        .min_horizontal()
        .min()
    )

    maximum: int = (
        sdf
        .max_horizontal()
        .max()
    )

    limit: int = padding * maximum

    tot: int = math.comb(len(columns), 2)
    nrows: int = 2
    ncols: int = math.ceil(tot / nrows)
    fig, axs = plt.subplots(nrows, ncols, figsize=(6 * ncols, 6 * nrows))

    iter4axs: typing.Iterator[plt.Axes] = iter(it.chain(*axs))

    ax: plt.Axes
    for (step_x, step_y), ax in zip(
            it.combinations(columns, 2),
            iter4axs
    ):
        ax.set_xscale('log')
        ax.set_yscale('log')

        ax.set_xlim(minimum, padding * limit)
        ax.set_ylim(minimum, padding * limit)

        ax.axvline(x=limit, color='darkgrey', linestyle='--')
        ax.axhline(y=limit, color='darkgrey', linestyle='--')

        ax.plot(
            (minimum, padding * limit),
            (minimum, padding * limit),
            color='darkgrey',
            linestyle=':',
            linewidth=1,
        )

        src: ndarray[tuple[int, typing.Literal[2]], np.dtype[np.int64]] = np.column_stack((
            df.get_column(step_x[0]).fill_null(limit).to_numpy(),
            df.get_column(step_y[0]).fill_null(limit).to_numpy(),
        ))

        trg: ndarray[tuple[int, typing.Literal[2]], np.dtype[np.int64]] = np.column_stack((
            df.get_column(step_x[1]).fill_null(limit).to_numpy(),
            df.get_column(step_y[1]).fill_null(limit).to_numpy(),
        ))

        lines = collections.LineCollection(
            segments=(np.stack((src, trg), axis=1)),
            alpha=0.5,
        )

        ax.add_collection(
            lines
        )

        tout: list[ndarray[tuple[typing.Literal[2]], np.dtype[np.int64]]] = [
            xy
            for xy in it.chain(src, trg)
            if limit in xy
        ]

        if tout:
            xys: ndarray[tuple[int, typing.Literal[2]], np.dtype[np.int64]] = np.vstack([
                xy
                for xy in it.chain(src, trg)
                if limit in xy
            ])

            ax.scatter(
                x=xys[:, 0],
                y=xys[:, 1],
                marker='x',
                color='C3',
                alpha=.5,
            )

        match_x = SequenceMatcher(None, *step_x).find_longest_match()
        match_y = SequenceMatcher(None, *step_y).find_longest_match()
        ax.set_xlabel(step_x[0][match_x.a:match_x.a + match_x.size])
        ax.set_ylabel(step_y[0][match_y.a:match_y.a + match_y.size])
        ax.set_aspect('equal')

    fig.suptitle('models → npolys')
    return fig


def survival(
        df: pl.DataFrame,
) -> plt.Figure:
    tot: int = len(enumerator2steps)
    nrows: int = 1
    ncols: int = math.ceil(tot / nrows)
    fig, axs = plt.subplots(
        nrows,
        ncols,
        width_ratios=[1 + len(steps) for steps in enumerator2steps.values()],
        figsize=(6 * ncols, 6 * nrows),
        sharey=True,
    )

    ax: plt.Axes
    for ax, (enumerator, steps) in zip(axs, enumerator2steps.items()):

        ax.grid(True, 'major', axis='x')
        ax.grid(True, 'both', axis='y')
        ax.yaxis.set_minor_locator(ticker.AutoMinorLocator())
        ax.xaxis.set_major_locator(ticker.MultipleLocator(1))
        ax.set_axisbelow(True)
        ax.tick_params(
            axis='x',
            which='major',
            bottom=False,
            top=False,
            labelbottom=False,
        )

        cols: list[str] = [f'stderr_{step}' for step in steps]

        timeouts: pl.DataFrame = df.select(
            pl.col(step)
            .filter(pl.col(step).cast(pl.Utf8).str.contains('timeout'))
            .count()
            .alias(step)
            for step in cols
        )

        timed_out: list[int] = [
            timeouts[step].first()
            for step in cols
        ]

        xs = np.arange(1 + len(steps), dtype=np.int64)
        ys = list(it.accumulate(timed_out, lambda acc, x: acc - x, initial=len(df)))
        ax.plot(xs, ys, 'o--')
        ax.fill_between(xs, 0, ys, alpha=.5)

        ax.set_xlim(xs[0] - .5, xs[-1] + .5)
        ax.set_ylim(0, len(df) + 1)

        for x, step in zip(xs[1:], steps):
            ax.text(
                x=x,
                y=0,
                s=step,
                bbox=dict(boxstyle="square", fc=('white', .6), ls=''),
                rotation=90,
                rotation_mode='anchor',
                transform=transforms.offset_copy(ax.transData, units='dots', x=-10, y=+10),
                va='bottom',
            )

    fig.suptitle('survival')
    fig.tight_layout()
    return fig


def foreach_step(
        df: pl.DataFrame,
        column: str,
) -> plt.Figure:
    tot: int = len(enumerator2steps)
    nrows: int = 2
    ncols: int = math.ceil(tot / nrows)
    fig, axs = plt.subplots(
        nrows,
        ncols,
        figsize=(6 * ncols, 12 * nrows),
        sharey=True,
        sharex=True,
    )

    iter4axs: typing.Iterable[plt.Axes] = iter(it.chain(*axs))
    ax: plt.Axes
    height: float = 1 / (2 + max(map(len, enumerator2steps.values())))

    for ax, (enumerator, steps) in zip(iter4axs, enumerator2steps.items()):
        ax.invert_yaxis()
        ax.grid(True, 'both', axis='x')
        ax.xaxis.set_minor_locator(ticker.AutoMinorLocator())
        ax.yaxis.set_major_locator(ticker.MultipleLocator(1))
        ax.set_axisbelow(True)
        ax.tick_params(
            axis='x',
            which='both',
            bottom=True,
            top=True,
            labelbottom=True,
            labeltop=True,
        )

        data: pl.DataFrame = df.select(
            *[
                pl.col(f'{column}_{step}')
                for step in steps
            ],
            *[
                pl.col(f'stderr_{step}').fill_null('').str.contains('timeout').alias(f'tout_{step}')
                for step in steps
            ],
        )

        ys: np.ndarray[tuple[int], np.dtype[np.int32]] = np.arange(len(data), dtype=np.int32) + 1
        for i, step in enumerate(steps):
            offset = height * i

            mask: np.ndarray[tuple[int], np.dtype[np.bool]] = data.get_column(f'tout_{step}').to_numpy()
            xs: np.ndarray[tuple[int], np.dtype[np.float64]] = data.get_column(f'{column}_{step}').to_numpy()

            ax.hlines(y=ys[~mask] + offset, xmin=0, xmax=xs[~mask], colors=f'C{i}', linestyles='-', label=step)
            ax.hlines(y=ys[mask] + offset, xmin=0, xmax=xs[mask], colors=f'C{i}', linestyles='--')

            ax.scatter(y=ys[~mask] + offset, x=xs[~mask], marker='|', c=f'C{i}')
            ax.scatter(y=ys[mask] + offset, x=xs[mask], marker='x', c=f'C{i}')

        ax.legend(loc='upper right', ncols=1)
        ax.set_xscale('log')

    fig.suptitle(column)
    fig.tight_layout()
    return fig


def main() -> None:
    parser: argparse.ArgumentParser = argparse.ArgumentParser()
    parser.add_argument('--csv', type=utils.file, required=True)
    parser.add_argument('--column', type=str, required=True)
    parser.add_argument('--output', type=Path, required=True, nargs='+')
    parser.add_argument('--timeout_enumerator', type=int, required=True)
    parser.add_argument('--timeout_compilator', type=int, required=True)
    parser.add_argument('--timeout_tlemmas', type=int, required=True)
    parser.add_argument('--type', type=str, required=False)
    args: argparse.Namespace = parser.parse_args()

    df: pl.DataFrame = pl.read_csv(
        args.csv,
        has_header=True,
    ).with_columns(
        **{
            f'stderr_{step}': pl.coalesce(pl.col(f'^stderr_{step}$'), pl.lit(None))
            for steps in enumerator2steps.values()
            for step in steps
        },
    ).sort(by=pl.col('density'))

    fig: plt.Figure
    match args.type:
        case 'time':
            fig = plot(df, args.column, Timeout(
                enumerator=timedelta(minutes=args.timeout_enumerator),
                compilator=timedelta(minutes=args.timeout_compilator),
                tlemmas=timedelta(minutes=args.timeout_tlemmas),
            ))

        case 'steps':
            fig = foreach_step(df, args.column)

        case _:

            match args.column:
                case 'models to npolys':
                    fig = models_to_npolys(df)

                case 'survival':
                    fig = survival(df)

                case column:
                    fig = plot(df, column)

    for out in args.output:
        fig.savefig(out)


if __name__ == '__main__':
    main()
