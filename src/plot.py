import argparse
import dataclasses
import itertools as it
import re
import typing as t
from collections import OrderedDict
from datetime import timedelta
from pathlib import Path

import math
import numpy as np
import polars as pl
import pypalettes
from matplotlib import pyplot as plt, transforms, ticker, colors, text
from scipy.stats import gaussian_kde

from src import utils


@dataclasses.dataclass(frozen=True)
class Timeout:
    enumerator: timedelta
    compilator: timedelta
    tlemmas: timedelta


enumerator2steps: dict[str, list[str]] = OrderedDict(
    **{
        'sae': [
            'sae'
        ],
        'sae_with_tlemmas': [
            'tlemmas_phi',
            'sae_with_tlemmas'
        ],
        'weighted_sae': [
            'weighted_sae'
        ],
    },
    **{
        f'wmi_decdnnf_{compiler}': [
            'tlemmas_phi',
            f'tddnnf_{compiler}_t_reduced',
            f'decdnnf_{compiler}_t_reduced',
            f'wmi_decdnnf_{compiler}',
        ]
        for compiler in ['d4', 'sdd']
    },
    **{
        f'wmi_decdnnf_exists_{qo}_{compiler}': [
            'tlemmas_phi',
            f'tddnnf_{compiler}_t_reduced',
            f'tddnnf_exists_{qo}_{compiler}_t_reduced',
            f'decdnnf_1st_step_exists_{qo}_{compiler}_t_reduced',
            f'decdnnf_2nd_step_exists_{qo}_{compiler}_t_reduced',
            f'wmi_decdnnf_exists_{qo}_{compiler}',
        ]
        for compiler in ['d4', 'sdd']
        for qo in 'xA'
    },
    **{
        f'wmi_decdnnf_n_ddnnife_phi_to_tlemmas_phi_{compiler}': [
            'tlemmas_phi',
            f'tddnnf_{compiler}_phi',
            f'tddnnf_{compiler}_tlemmas_phi',
            f'decdnnf_n_ddnnife_phi_to_tlemmas_phi_{compiler}',
            f'wmi_decdnnf_n_ddnnife_phi_to_tlemmas_phi_{compiler}',
        ]
        for compiler in ['d4', 'sdd']
    },
    **{
        f'wmi_decdnnf_n_ddnnife_phi_to_t_reduced_phi_{compiler}': [
            'tlemmas_phi',
            f'tddnnf_{compiler}_phi',
            f'tddnnf_{compiler}_t_reduced',
            f'decdnnf_n_ddnnife_phi_to_t_reduced_phi_{compiler}',
            f'wmi_decdnnf_n_ddnnife_phi_to_t_reduced_phi_{compiler}',
        ]
        for compiler in ['d4', 'sdd']
    },
    **{
        f'wmi_decdnnf_n_ddnnife_t_extended_phi_to_t_reduced_phi_{compiler}': [
            'tlemmas_phi',
            f'tddnnf_{compiler}_t_reduced',
            'tlemmas_not_phi',
            f'tddnnf_{compiler}_t_extended',
            f'decdnnf_n_ddnnife_t_extended_phi_to_t_reduced_phi_{compiler}',
            f'wmi_decdnnf_n_ddnnife_t_extended_phi_to_t_reduced_phi_{compiler}',
        ]
        for compiler in ['d4', 'sdd']
    },
    **{
        f'wmi_decdnnf_n_mathsat_{compiler}': [
            f'tddnnf_{compiler}_phi',
            f'decdnnf_n_mathsat_{compiler}',
            f'wmi_decdnnf_n_mathsat_{compiler}',
        ]
        for compiler in ['d4', 'sdd']
    },
    **{
        f'wmi_decdnnf_n_mathsat_d4_phi_n_skeleton': [
            f'tddnnf_d4_phi_n_skeleton',
            f'decdnnf_n_mathsat_d4_phi_n_skeleton',
            f'wmi_decdnnf_n_mathsat_d4_phi_n_skeleton',
        ],
    }
)


def cm(inches: float) -> float:
    return inches * 1 / 2.54


def axes(input: plt.Axes | np.ndarray) -> t.Iterator[plt.Axes]:
    if isinstance(input, plt.Axes):
        yield input
    else:
        yield from input.flatten()


def from_step(timeout: Timeout, step: str):
    if 'tlemmas' in step:
        return timeout.tlemmas

    if 'tddnnf' in step:
        return timeout.compilator

    if 'decdnnf' in step or 'sae' in step:
        return timeout.enumerator

    raise RuntimeError(f'unable to infer timeout from step name: {step}')


def label(step: str) -> str:
    return (
        step.replace('_', ' ')
        .replace('phi', r'$\varphi$')
        .replace('tlemmas', r'$T$-lemmas')
        .replace('t reduced', r'$T$-reduced $\varphi$')
        .replace('t extended', r'$T$-extended $\varphi$')
        .replace(r'$\varphi$ $\varphi$', r'$\varphi$')
        .replace('exists', r'$\exists$')
        .replace(' x', r' $\mathbf{B}$')
        .replace(' A', r' $\mathbf{A}$')
        .replace('1st', r'$1^{st}$')
        .replace('2nd', r'$2^{nd}$')
    )


def compare_columns(
        df: pl.DataFrame,
        columns_n_enumerators: list[tuple[tuple[str, str], str]],
) -> t.Generator[tuple[str, plt.Figure]]:
    minimum: float = (
        df.select(
            pl.col(column)
            for columns, _ in columns_n_enumerators
            for column in columns
        )
        .min_horizontal()
        .min()
    )
    minimum = 0.0 if minimum < 10 else minimum

    maximum: tuple[float, ...] = tuple(
        df.select(
            pl.col(columns[ix])
            for columns, _ in columns_n_enumerators
        )
        .max_horizontal()
        .max()
        for ix in range(2)
    )

    log_width: float = math.log10(max(1.0, maximum[0])) - math.log10(max(1.0, minimum))
    padding: float = 10 ** (max(1.0, log_width) / 10)

    cmap = pypalettes.load_cmap('Sunset2')
    tmin, tmax = max(1.0, minimum), maximum[0] * padding
    major: np.ndarray[tuple[int], np.dtype[np.float64]] = ticker.LogLocator(base=10).tick_values(tmin, tmax)
    major = major[(tmin <= major) & (major <= tmax)]
    minor: np.ndarray[tuple[int], np.dtype[np.float64]] = (
        ticker.LogLocator(base=10, subs=np.arange(2, 12, 2)).tick_values(tmin, tmax)
    )
    minor = minor[(tmin <= minor) & (minor <= tmax)]

    for (col_x, col_y), enum in columns_n_enumerators:

        fig: plt.Figure
        ax: plt.Axes
        fig, ax = plt.subplots(1, 1, figsize=(cm(15), cm(15)))

        steps_x: list[str] = enumerator2steps[enum]
        limits_x: list[float] = list(it.accumulate(steps_x, lambda acc, _: acc * padding, initial=maximum[0] * padding))

        if minimum <= 1:
            ax.set_xscale('symlog', linthresh=1, linscale=.25)
            ax.set_yscale('symlog', linthresh=1, linscale=.25)
        else:
            ax.set_xscale('log')
            ax.set_yscale('log')

        ax.set_xlim(minimum, limits_x[-1])
        ax.set_ylim(minimum, maximum[1] * padding)
        ax.xaxis.set_major_locator(ticker.FixedLocator(major))
        ax.yaxis.set_major_locator(ticker.SymmetricalLogLocator(base=10, linthresh=1))
        ax.xaxis.set_minor_locator(ticker.FixedLocator(minor))
        ax.yaxis.set_minor_locator(ticker.SymmetricalLogLocator(base=10, subs=np.arange(2, 10, 2), linthresh=1))
        ax.grid(visible=True, which='both', linewidth=.1)

        for step, limit in zip(steps_x, limits_x):
            ax.axvline(x=limit, color='black', linestyle='--', linewidth=1)
            ax.text(
                x=limit,
                y=minimum,
                s=label(step),
                bbox=dict(boxstyle='square', fc=('white', .6), ls=''),
                rotation=90,
                rotation_mode='anchor',
                transform=transforms.offset_copy(ax.transData, units='dots', x=+4 + plt.rcParams['font.size'], y=+4),
                va='baseline',
            )

        ax.plot(
            (minimum, max(limits_x)),
            (minimum, max(limits_x)),
            color='darkgrey',
            linestyle=':',
            linewidth=1,
        )

        data: pl.DataFrame = (
            df.select(
                pl.col(f'{col_x}'),
                pl.col(f'{col_y}'),
                *[
                    pl.col(f'stderr_{step}').fill_null('').str.contains('timeout').alias(f'tout_{step}')
                    for step in set(steps_x)
                ],
            )
        )

        rm = np.zeros(len(df), dtype=np.bool)

        xs = data.get_column(f'{col_x}').to_numpy(writable=True)
        ys = data.get_column(f'{col_y}').to_numpy(writable=True)
        for step, limit in zip(steps_x, limits_x):
            mask = data.get_column(f'tout_{step}').to_numpy()
            rm |= mask
            xs[mask] = limit

        xy = np.column_stack((xs, ys))

        # count points at each location for non-timeout points
        unique_regular, counts_regular = np.unique(xy[~rm], axis=0, return_counts=True)

        # count points at each location for timeout points
        unique_timeout, counts_timeout = np.unique(xy[rm], axis=0, return_counts=True)

        scatters: list[plt.PathCollection] = [
            ax.scatter(
                x=xy[:, 0],
                y=xy[:, 1],
                s=s * 32,
                zorder=3,
                **kwargs,
            )
            for xy, s, kwargs in [
                (unique_regular, counts_regular, dict(marker='o', edgecolors='none', facecolors=cmap(0), alpha=.6)),
                (unique_timeout, counts_timeout, dict(marker='x', color=cmap(0))),
            ]
        ]

        ax.set_xlabel(label(col_x))
        ax.set_ylabel(label(col_y))
        ax.set_aspect('equal')

        fig.tight_layout()
        yield enum, fig


def plot(
        df: pl.DataFrame,
        columns_n_enumerators: list[tuple[str, str]] | None = None,
) -> t.Generator[tuple[str, plt.Figure]]:
    minimum: float = (
        df.select(
            pl.col(column)
            for column, _ in columns_n_enumerators
        )
        .min_horizontal()
        .min()
    )
    minimum = 0.0 if minimum < 10 else minimum

    maximum: float = (
        df.select(
            pl.col(column)
            for column, _ in columns_n_enumerators
        )
        .max_horizontal()
        .max()
    )

    log_width: float = math.log10(max(1.0, maximum)) - math.log10(max(1.0, minimum))
    padding: float = 10 ** (max(1.0, log_width) / 10)

    cmap = pypalettes.load_cmap('Sunset2')
    tmin, tmax = max(1.0, minimum), maximum * padding
    major: np.ndarray[tuple[int], np.dtype[np.float64]] = (
        ticker.LogLocator(base=10).tick_values(tmin, tmax)
    )
    major = major[(tmin <= major) & (major <= tmax)]
    minor: np.ndarray[tuple[int], np.dtype[np.float64]] = (
        ticker.LogLocator(base=10, subs=np.arange(2, 10, 2)).tick_values(tmin, tmax)
    )
    minor = minor[(tmin <= minor) & (minor <= tmax)]

    for (col_x, enum_x), (col_y, enum_y) in it.combinations(columns_n_enumerators, 2):

        fig: plt.Figure
        ax: plt.Axes
        fig, ax = plt.subplots(1, 1, figsize=(cm(15), cm(15)))

        steps_x: list[str] = enumerator2steps[enum_x]
        steps_y: list[str] = enumerator2steps[enum_y]

        limits_x: list[float] = list(it.accumulate(steps_x, lambda acc, _: acc * padding, initial=maximum * padding))
        limits_y: list[float] = list(it.accumulate(steps_y, lambda acc, _: acc * padding, initial=maximum * padding))

        if minimum <= 1:
            ax.set_xscale('symlog', linthresh=1, linscale=.25)
            ax.set_yscale('symlog', linthresh=1, linscale=.25)
        else:
            ax.set_xscale('log')
            ax.set_yscale('log')

        ax.set_xlim(minimum, limits_x[-1])
        ax.set_ylim(minimum, limits_y[-1])
        ax.xaxis.set_major_locator(ticker.FixedLocator(major))
        ax.yaxis.set_major_locator(ticker.FixedLocator(major))
        ax.xaxis.set_minor_locator(ticker.FixedLocator(minor))
        ax.yaxis.set_minor_locator(ticker.FixedLocator(minor))
        ax.grid(visible=True, which='both', linewidth=.1)

        for step, limit in zip(steps_x, limits_x):
            ax.axvline(x=limit, color='black', linestyle='--', linewidth=1)
            ax.text(
                x=limit,
                y=minimum,
                s=label(step),
                bbox=dict(boxstyle='square', fc=('white', .6), ls=''),
                rotation=90,
                rotation_mode='anchor',
                transform=transforms.offset_copy(ax.transData, units='dots', x=+4 + plt.rcParams['font.size'], y=+4),
                va='baseline',
            )

        for step, limit in zip(steps_y, limits_y):
            ax.axhline(y=limit, color='black', linestyle='--', linewidth=1)
            ax.text(
                x=minimum,
                y=limit,
                s=label(step),
                bbox=dict(boxstyle='square', fc=('white', .6), ls=''),
                transform=transforms.offset_copy(ax.transData, units='dots', x=+4, y=+6.5),
                va='baseline',
            )

        ax.plot(
            (minimum, max(*limits_x, *limits_y)),
            (minimum, max(*limits_x, *limits_y)),
            color='darkgrey',
            linestyle=':',
            linewidth=1,
        )

        data: pl.DataFrame = (
            df.select(
                pl.col(f'{col_x}'),
                pl.col(f'{col_y}'),
                *[
                    pl.col(f'stderr_{step}').fill_null('').str.contains('timeout').alias(f'tout_{step}')
                    for step in set(steps_x + steps_y)
                ],
            )
        )

        rm_x = np.zeros(len(df), dtype=np.bool)
        rm_y = np.zeros(len(df), dtype=np.bool)

        xs = data.get_column(f'{col_x}').to_numpy(writable=True)
        for step, limit in zip(steps_x, limits_x):
            mask = data.get_column(f'tout_{step}').to_numpy()
            rm_x |= mask
            xs[mask] = limit

        ys = data.get_column(f'{col_y}').to_numpy(writable=True)
        for step, limit in zip(steps_y, limits_y):
            mask = data.get_column(f'tout_{step}').to_numpy()
            rm_y |= mask
            ys[mask] = limit

        xy = np.column_stack((xs, ys))

        # count points at each location for non-timeout points
        unique_regular, counts_regular = np.unique(xy[~(rm_x | rm_y)], axis=0, return_counts=True)

        # count points at each location for timeout points
        unique_timeout_x, counts_timeout_x = np.unique(xy[rm_x & ~rm_y], axis=0, return_counts=True)
        unique_timeout_y, counts_timeout_y = np.unique(xy[~rm_x & rm_y], axis=0, return_counts=True)
        unique_timeout, counts_timeout = np.unique(xy[rm_x & rm_y], axis=0, return_counts=True)

        scatters: list[plt.PathCollection] = [
            ax.scatter(
                x=xy[:, 0],
                y=xy[:, 1],
                s=s * 32,
                zorder=3,
                **kwargs,
            )
            for xy, s, kwargs in [
                (unique_regular, counts_regular, dict(marker='o', edgecolors='none', facecolors=cmap(0), alpha=.6)),
                (unique_timeout_x, counts_timeout_x * 2, dict(marker='3', color=cmap(0))),
                (unique_timeout_y, counts_timeout_y * 2, dict(marker='1', color=cmap(0))),
                (unique_timeout, counts_timeout, dict(marker='x', color=cmap(0))),
            ]
        ]

        ax.set_xlabel(label(enum_x))
        ax.set_ylabel(label(enum_y))
        ax.set_aspect('equal')

        fig.tight_layout()
        yield f'{enum_x}_vs_{enum_y}', fig


def plot_time(
        df: pl.DataFrame,
        timeout: Timeout,
        expression_n_enumerator: list[tuple[pl.Expr, str]],
) -> t.Generator[tuple[str, plt.Figure]]:
    padding: float = 1.4
    minimum: float = (
        df.select(
            expr.alias(enum)
            for expr, enum in expression_n_enumerator
        )
        .min_horizontal()
        .min()
    )
    minimum = 0 if minimum < padding else minimum / padding

    cmap = pypalettes.load_cmap('Sunset2')

    for (expression_x, enum_x), (expression_y, enum_y) in it.combinations(expression_n_enumerator, 2):

        fig: plt.Figure
        ax: plt.Axes
        fig, ax = plt.subplots(1, 1, figsize=(cm(15), cm(15)))

        steps_x = enumerator2steps[enum_x]
        steps_y = enumerator2steps[enum_y]

        limits_x: list[float] = list(it.accumulate([from_step(timeout, step).total_seconds() for step in steps_x]))
        limits_x.append(padding * limits_x[-1])
        limits_y: list[float] = list(it.accumulate([from_step(timeout, step).total_seconds() for step in steps_y]))
        limits_y.append(padding * limits_y[-1])

        if minimum <= 1:
            ax.set_xscale('symlog', linthresh=1, linscale=.25)
            ax.set_yscale('symlog', linthresh=1, linscale=.25)
        else:
            ax.set_xscale('log')
            ax.set_yscale('log')

        ax.yaxis.set_minor_locator(ticker.SymmetricalLogLocator(base=10, subs=np.arange(2, 10, 2), linthresh=1))
        ax.xaxis.set_minor_locator(ticker.SymmetricalLogLocator(base=10, subs=np.arange(2, 10, 2), linthresh=1))

        trans_x = transforms.blended_transform_factory(ax.transData, ax.transAxes)
        trans_y = transforms.blended_transform_factory(ax.transAxes, ax.transData)

        for i, (step, limit) in enumerate(zip(steps_x, limits_x)):
            ax.annotate(
                label(step),
                xy=(limit, 0),
                xycoords=trans_x,
                xytext=(0, 6 + i * 12),
                textcoords=text.OffsetFrom(trans_x, (limit, 1), 'points'),
                ha='right',
                va='baseline',
                zorder=1,
                arrowprops=dict(
                    arrowstyle='-',
                    color='black',
                    linestyle='--',
                    capstyle='butt',
                    linewidth=.75,
                    relpos=(1, 0),
                ),
            )

        for i, (step, limit) in enumerate(zip(steps_y, limits_y)):
            ax.annotate(
                label(step),
                xy=(0, limit),
                xycoords=trans_y,
                xytext=(6 + i * 12 + plt.rcParams['font.size'], 0),
                textcoords=text.OffsetFrom(trans_y, (1, limit), 'points'),
                rotation=90,
                rotation_mode='anchor',
                ha='right',
                va='baseline',
                zorder=1,
                arrowprops=dict(
                    arrowstyle='-',
                    color='black',
                    linestyle='--',
                    capstyle='butt',
                    linewidth=.75,
                    relpos=(.5, 1),
                ),
            )

        ax.set_xlim(minimum, limits_x[-1])
        ax.set_ylim(minimum, limits_y[-1])

        ax.grid(visible=True, which='both', linewidth=.1)
        ax.plot(
            (minimum, max(*limits_x, *limits_y)),
            (minimum, max(*limits_x, *limits_y)),
            color='darkgrey',
            linestyle=':',
            linewidth=1,
        )

        data: pl.DataFrame = (
            df.select(
                *[
                    pl.col(f's_{step}')
                    for step in set(steps_x + steps_y)
                ],
                *[
                    pl.col(f'stderr_{step}').fill_null('').str.contains('timeout').alias(f'tout_{step}')
                    for step in set(steps_x + steps_y)
                ],
            ).with_columns(
                **{
                    enum_x: expression_x,
                    enum_y: expression_y,
                }
            )
        )

        rm_x = np.zeros(len(df), dtype=np.bool)
        xs = data.get_column(enum_x).to_numpy(writable=True)
        for step, limit in zip(steps_x, limits_x):
            mask = data.get_column(f'tout_{step}').to_numpy()
            rm_x |= mask
            xs[mask] = limit

        rm_y = np.zeros(len(df), dtype=np.bool)
        ys = data.get_column(enum_y).to_numpy(writable=True)
        for step, limit in zip(steps_y, limits_y):
            mask = data.get_column(f'tout_{step}').to_numpy()
            rm_y |= mask
            ys[mask] = limit

        coordinates = np.column_stack((xs, ys))

        scatters: list[plt.PathCollection] = [
            ax.scatter(
                x=xy[:, 0],
                y=xy[:, 1],
                zorder=3,
                **kwargs,
            )
            for xy, kwargs in [
                (coordinates[~rm_x & ~rm_y], dict(marker='o', edgecolors='none', facecolors=cmap(0), alpha=.6)),
                (coordinates[rm_x & ~rm_y], dict(marker='3', s=2 ** 6, color=cmap(0), alpha=.6)),
                (coordinates[~rm_x & rm_y], dict(marker='1', s=2 ** 6, color=cmap(0), alpha=.6)),
                (coordinates[rm_x & rm_y], dict(marker='x', color=cmap(0), alpha=.6)),
            ]
        ]

        ax.set_xlabel(f'{label(enum_x)} [$s$]')
        ax.set_ylabel(f'{label(enum_y)} [$s$]')
        ax.set_aspect('equal')

        fig.tight_layout()
        yield f'{enum_x}_vs_{enum_y}', fig


def plot_lines(
        df: pl.DataFrame,
        columns_n_enumerators: list[tuple[tuple[str, str], str]],
) -> t.Generator[tuple[str, plt.Figure]]:
    columns: set[str] = {
        col
        for cols, _ in columns_n_enumerators
        for col in cols
    }

    minimum: float = (
        df.select(columns)
        .min_horizontal()
        .min()
    )
    minimum = 0.0 if minimum < 10 else minimum

    maximum: float = (
        df.select(columns)
        .max_horizontal()
        .max()
    )

    log_width: float = math.log10(max(1.0, maximum)) - math.log10(max(1.0, minimum))
    padding: float = 10 ** (max(1.0, log_width) / 10)

    cmap = pypalettes.load_cmap('Sunset2')
    tmin, tmax = max(1.0, minimum), maximum * padding
    major: np.ndarray[tuple[int], np.dtype[np.float64]] = (
        ticker.LogLocator(base=10).tick_values(tmin, tmax)
    )
    major = major[(tmin <= major) & (major <= tmax)]
    minor: np.ndarray[tuple[int], np.dtype[np.float64]] = (
        ticker.LogLocator(base=10, subs=np.arange(2, 10, 2)).tick_values(tmin, tmax)
    )
    minor = minor[(tmin <= minor) & (minor <= tmax)]

    for (cols_x, enum_x), (cols_y, enum_y) in it.combinations(columns_n_enumerators, 2):

        fig: plt.Figure
        ax: plt.Axes
        fig, ax = plt.subplots(1, 1, figsize=(cm(15), cm(15)))

        steps_x: list[str] = enumerator2steps[enum_x]
        steps_y: list[str] = enumerator2steps[enum_y]

        limits_x: list[float] = list(it.accumulate(steps_x, lambda acc, _: acc * padding, initial=maximum * padding))
        limits_y: list[float] = list(it.accumulate(steps_y, lambda acc, _: acc * padding, initial=maximum * padding))

        if minimum <= 1:
            ax.set_xscale('symlog', linthresh=1, linscale=.25)
            ax.set_yscale('symlog', linthresh=1, linscale=.25)
        else:
            ax.set_xscale('log')
            ax.set_yscale('log')

        ax.set_xlim(minimum, limits_x[-1])
        ax.set_ylim(minimum, limits_y[-1])
        ax.xaxis.set_major_locator(ticker.FixedLocator(major))
        ax.yaxis.set_major_locator(ticker.FixedLocator(major))
        ax.xaxis.set_minor_locator(ticker.FixedLocator(minor))
        ax.yaxis.set_minor_locator(ticker.FixedLocator(minor))
        ax.grid(visible=True, which='both', linewidth=.1)

        for step, limit in zip(steps_x, limits_x):
            ax.axvline(x=limit, color='black', linestyle='--', linewidth=1)
            ax.text(
                x=limit,
                y=minimum,
                s=label(step),
                bbox=dict(boxstyle='square', fc=('white', .6), ls=''),
                rotation=90,
                rotation_mode='anchor',
                transform=transforms.offset_copy(ax.transData, units='dots', x=+4 + plt.rcParams['font.size'], y=+4),
                va='baseline',
            )

        for step, limit in zip(steps_y, limits_y):
            ax.axhline(y=limit, color='black', linestyle='--', linewidth=1)
            ax.text(
                x=minimum,
                y=limit,
                s=label(step),
                bbox=dict(boxstyle='square', fc=('white', .6), ls=''),
                transform=transforms.offset_copy(ax.transData, units='dots', x=+4, y=+6.5),
                va='baseline',
            )

        ax.plot(
            (minimum, max(*limits_x, *limits_y)),
            (minimum, max(*limits_x, *limits_y)),
            color='darkgrey',
            linestyle=':',
            linewidth=1,
        )

        data: pl.DataFrame = (
            df.select(
                *(
                    pl.col(col)
                    for col in set(cols_x + cols_y)
                ),
                **{
                    f'tout_{step}': pl.col(f'stderr_{step}').fill_null('').str.contains('timeout')
                    for step in set(steps_x + steps_y)
                },
            )
        )

        src_rm_x = np.zeros(len(df), dtype=np.bool)
        src_rm_y = np.zeros(len(df), dtype=np.bool)

        trg_rm_x = np.zeros(len(df), dtype=np.bool)
        trg_rm_y = np.zeros(len(df), dtype=np.bool)

        src_x = data.get_column(f'{cols_x[0]}').to_numpy(writable=True)
        trg_x = data.get_column(f'{cols_x[1]}').to_numpy(writable=True)
        for i, step, limit in zip(it.count(), steps_x, limits_x):
            mask = data.get_column(f'tout_{step}').to_numpy()
            if i <= len(steps_x) - 2:
                src_rm_x |= mask
                src_x[mask] = limit
            trg_x[mask] = limit
            trg_rm_x |= mask

        src_y = data.get_column(f'{cols_y[0]}').to_numpy(writable=True)
        trg_y = data.get_column(f'{cols_y[1]}').to_numpy(writable=True)
        for i, step, limit in zip(it.count(), steps_y, limits_y):
            mask = data.get_column(f'tout_{step}').to_numpy()
            if i <= len(steps_y) - 2:
                src_rm_y |= mask
                src_y[mask] = limit
            trg_y[mask] = limit
            trg_rm_y |= mask

        ax.quiver(
            src_x,
            src_y,
            trg_x - src_x,
            trg_y - src_y,
            angles='xy',
            scale_units='xy',
            scale=1,
            alpha=0.5,
            color=cmap(0),
        )

        for x, y, rm_x, rm_y in [(src_x, src_y, src_rm_x, src_rm_y), (trg_x, trg_y, trg_rm_x, trg_rm_y)]:
            xy = np.column_stack((x, y))

            unique_timeout_x, counts_timeout_x = np.unique(xy[rm_x & ~rm_y], axis=0, return_counts=True)
            unique_timeout_y, counts_timeout_y = np.unique(xy[~rm_x & rm_y], axis=0, return_counts=True)
            unique_timeout, counts_timeout = np.unique(xy[rm_x & rm_y], axis=0, return_counts=True)

            scatters: list[plt.PathCollection] = [
                ax.scatter(
                    x=xy[:, 0],
                    y=xy[:, 1],
                    s=s * 32,
                    zorder=3,
                    **kwargs,
                )
                for xy, s, kwargs in [
                    (unique_timeout_x, counts_timeout_x * 2, dict(marker='3', color=cmap(0))),
                    (unique_timeout_y, counts_timeout_y * 2, dict(marker='1', color=cmap(0))),
                    (unique_timeout, counts_timeout, dict(marker='x', color=cmap(0))),
                ]
            ]

        ax.set_xlabel(label(enum_x))
        ax.set_ylabel(label(enum_y))
        ax.set_aspect('equal')

        fig.tight_layout()
        yield f'{enum_x}_vs_{enum_y}', fig


def survival(
        df: pl.DataFrame,
        enums: list[str] | None = None,
) -> t.Generator[tuple[str, plt.Figure]]:
    enums = enums if enums else enumerator2steps.keys()
    cmap = pypalettes.load_cmap('Sunset2')

    for enumerator in enums:

        fig: plt.Figure
        ax: plt.Axes
        fig, ax = plt.subplots(
            1, 1,
            figsize=(cm(3 + 2 * len(enumerator2steps[enumerator])), cm(15)),
        )

        steps: list[str] = enumerator2steps[enumerator]

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

        survived: pl.DataFrame = df.select(
            pl.col(f'stderr_{step}').cast(pl.Utf8).fill_null('').str.contains('timeout').alias(step)
            for step in steps
        ).select(
            pl.any_horizontal(steps[:i + 1]).not_().sum().alias(step)
            for i, step in enumerate(steps)
        )

        xs = np.arange(1 + len(steps), dtype=np.int64)
        ys = [len(df), *(survived[step].first() for step in steps)]
        ax.plot(xs, ys, 'o--', color=cmap(0))
        ax.fill_between(xs, 0, ys, color=cmap(0), alpha=.5)

        ax.set_xlim(xs[0] - .5, xs[-1] + .5)
        ax.set_ylim(0, len(df) + 1)

        for x, step in zip(xs[1:], steps):
            ax.text(
                x=x,
                y=0,
                s=label(step),
                bbox=dict(boxstyle='square', fc=('white', .8), ls=''),
                rotation=90,
                rotation_mode='anchor',
                transform=transforms.offset_copy(ax.transData, units='dots', x=-10, y=+10),
                va='bottom',
            )

        fig.tight_layout()
        yield enumerator, fig


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
        figsize=(8 * ncols, 16 * nrows),
        sharey=True,
        sharex=True,
    )

    ax: plt.Axes
    height: float = 1 / (1 + max(map(len, enumerator2steps.values())))

    for ax, (enumerator, steps) in zip(axes(axs), enumerator2steps.items()):
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

            ax.hlines(y=ys[~mask] + offset, xmin=0, xmax=xs[~mask], colors=f'C{i}', linestyles='-', label=label(step))
            ax.hlines(y=ys[mask] + offset, xmin=0, xmax=xs[mask], colors=f'C{i}', linestyles='--')

            ax.scatter(y=ys[~mask] + offset, x=xs[~mask], marker='|', c=f'C{i}')
            ax.scatter(y=ys[mask] + offset, x=xs[mask], marker='x', c=f'C{i}')

        ax.legend(loc='upper right', ncols=1)
        ax.set_xscale('log')

    fig.suptitle(column)
    fig.tight_layout()
    return fig


def ridgeplot(
        df: pl.DataFrame,
        column: str,
) -> t.Generator[tuple[str, plt.Figure]]:
    cmap: colors.Colormap = plt.get_cmap('tab20b')

    maximum: float = (
        df.select({
            f'{column}_{step}'
            for steps in enumerator2steps.values()
            for step in steps
        })
        .max_horizontal()
        .max()
    )

    for (enumerator, steps) in enumerator2steps.items():
        fig: plt.Figure
        fig, axs = plt.subplots(
            nrows=len(steps),
            figsize=(cm(15), cm(4 + 2 * len(steps))),
            height_ratios=[1] * len(steps),
            sharex=True,
        )

        data: pl.DataFrame = (
            df.with_columns(
                *[
                    pl.col(f'stderr_{step}').fill_null('').str.contains('timeout').alias(step)
                    for step in steps
                ],
            )
            .select(
                *[
                    pl.col(f'{column}_{step}')
                    for step in steps
                ],
                *[
                    pl.any_horizontal(steps[:i + 1]).alias(step)
                    for i, step in enumerate(steps)
                ],
            )
        )

        ax: plt.Axes
        for i, (ax, step) in enumerate(zip(axes(axs), steps)):
            ax.patch.set_alpha(0)
            ax.xaxis.set_minor_locator(ticker.LogLocator(base=10, subs=np.arange(2, 10, 2)))
            ax.xaxis.grid(which='both', linewidth=.1)
            ax.set_xscale('log')
            ax.set_xlim(1e-1, maximum)
            ax.set_ylim(0, 1)
            ax.set_yticks([])
            ax.tick_params(
                axis='both',
                which='both',
                left=False,
                right=False,
                bottom=i == len(steps) - 1,
                top=False,
            )

            fig.text(
                x=0,
                y=0,
                s=label(step),
                bbox=dict(boxstyle='square', fc=('white', .8), ls=''),
                transform=transforms.offset_copy(ax.transAxes, units='dots', x=10, y=10),
                va='bottom',
                zorder=9,
            )

            for s in ["top", "right", "left", "bottom"]:
                ax.spines[s].set_visible(False)

            mask: np.ndarray[tuple[int], np.dtype[np.bool]] = data.get_column(step).to_numpy()
            xs: np.ndarray[tuple[int], np.dtype[np.float64]] = data.get_column(f'{column}_{step}').to_numpy()

            valid = xs[~mask]

            if len(valid) < 2:
                continue

            log_valid = np.log10(valid)
            kde = gaussian_kde(log_valid)

            x_grid_log = np.linspace(log_valid.min(), log_valid.max(), 100)
            y_grid = kde(x_grid_log)

            if y_grid.max() > 0:
                y_grid = y_grid / y_grid.max() * 0.9

            x_grid = 10 ** x_grid_log

            ax.plot(x_grid, y_grid, color=cmap(i))
            ax.fill_between(x_grid, 0, y_grid, color=cmap(i), alpha=0.5)

        class LogSecondsFormatter(ticker.LogFormatterMathtext):
            def __call__(self, x, pos=None):
                return fr'{super().__call__(x, pos)}$s$'

        ax.xaxis.set_major_formatter(LogSecondsFormatter())

        fig.tight_layout()
        fig.subplots_adjust(hspace=-0.5)
        yield enumerator, fig


def inspection(
        df: pl.DataFrame,
        qo: t.Literal['x', 'A'],
) -> plt.Figure:
    fig, ax = plt.subplots(1, 1, figsize=(300, 20))
    cmap: colors.Colormap = plt.get_cmap('tab20b')

    oq: t.Literal['x', 'A'] = 'xA'.replace(qo, '')

    enumerators: list[tuple[str, tuple[str, str, str]]] = [
        (enum, (f'models_{enum}', f'distinct_by_{oq}_{enum}', f'npolys_{enum}'))
        for enum in enumerator2steps.keys()
        if re.search(fr'sae|exists_{qo}', enum)
    ]

    many: int = sum(len(cols) for _, cols in enumerators)
    width: float = 1 / (many + len(enumerators) - 1)

    ax.set_axisbelow(True)
    ax.set_yscale('symlog', linthresh=10)
    ax.yaxis.set_minor_locator(ticker.FixedLocator([
        *range(0, 10, 2),
        *[
            x
            for exp in range(1, 6)
            for x in np.arange(2, 10) * (10 ** exp)
        ],
    ]))

    ax.grid()
    ax.yaxis.grid(which='minor')

    ax.xaxis.set_major_locator(ticker.MultipleLocator(1))
    ax.tick_params(
        axis='y',
        which='both',
        left=True,
        right=True,
        labelleft=True,
        labelright=True,
    )

    data: pl.DataFrame = df.select(
        *(
            col
            for _, cols in enumerators
            for col in cols
        )
    )

    xs: np.ndarray[tuple[int], np.dtype[np.int64]] = np.arange(len(data), dtype=np.int64) + 1
    for i, (enum, cols) in enumerate(enumerators):
        for j, col in enumerate(cols):
            offset: float = width * (4 * i + j)

            ax.bar(
                x=xs + offset,
                height=data.get_column(col).to_numpy(),
                color=cmap(4 * i + j),
                label=label(col),
                width=width,
            )

    ax.set_xlim(.5, len(data) + .5)
    ax.legend(loc='upper left', ncols=len(enumerators))

    fig.suptitle('inspection')
    fig.tight_layout()
    return fig


def main() -> None:
    parser: argparse.ArgumentParser = argparse.ArgumentParser()
    parser.add_argument('--csv', type=utils.file, required=True)
    parser.add_argument('--timeout_enumerator', type=int, required=True)
    parser.add_argument('--timeout_compilator', type=int, required=True)
    parser.add_argument('--timeout_tlemmas', type=int, required=True)
    parser.add_argument('--pattern', type=str, required=False, default='*')
    parser.add_argument('--type', type=str, required=True)
    parser.add_argument('--folder', type=Path, required=True)
    args: argparse.Namespace = parser.parse_args()

    global enumerator2steps
    match args.pattern:
        case '*':
            pass

        case pattern:
            enumerator2steps = OrderedDict(
                (k, v)
                for k, v in enumerator2steps.items()
                if pattern in k or 'sae' == k
            )

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

    timeout: Timeout = Timeout(
        enumerator=timedelta(minutes=args.timeout_enumerator),
        compilator=timedelta(minutes=args.timeout_compilator),
        tlemmas=timedelta(minutes=args.timeout_tlemmas),
    )

    folder: Path = args.folder
    folder.mkdir(exist_ok=True)

    match args.type:
        case 'npolys' | 'models' | 'distinct_by_x' | 'distinct_by_A' | 'nuniquepolys':
            for name, fig in plot(
                    df,
                    [(f'{args.type}_{enum}', enum) for enum in enumerator2steps.keys()]
            ):
                fig.savefig(args.folder / f'{name}.pdf')
                plt.close(fig)

        case 'models to npolys' | 'models to nuniquepolys' | 'nuniquepolys to npolys' | 'models to distinct_by_x' | 'models to distinct_by_A':
            src, trg = args.type.split(' to ')
            for name, fig in plot_lines(
                    df,
                    [((f'{src}_{enum}', f'{trg}_{enum}'), enum) for enum in enumerator2steps.keys()]
            ):
                fig.savefig(args.folder / f'{name}.pdf')
                plt.close(fig)

        case 'time':
            for name, fig in plot_time(
                    df,
                    timeout,
                    [
                        (pl.sum_horizontal(pl.col(f's_{step}') for step in steps), enum)
                        for enum, steps in enumerator2steps.items()
                    ]
            ):
                fig.savefig(args.folder / f'{name}.pdf')
                plt.close(fig)

        case 'enumerating':
            for name, fig in plot_time(
                    df,
                    timeout,
                    [
                        *[
                            (pl.col(f's_{steps[-1]}'), enum)
                            for enum, steps in enumerator2steps.items()
                            if 'sae' in enum
                        ],
                        *[
                            (pl.sum_horizontal(pl.col(f's_{step}') for step in steps if 'decdnnf' in step), enum)
                            for enum, steps in enumerator2steps.items()
                            if 'decdnnf' in enum
                        ],
                    ]
            ):
                fig.savefig(args.folder / f'{name}.pdf')
                plt.close(fig)

        case 'survival':
            for name, fig in survival(df):
                fig.savefig(args.folder / f'{name}.pdf')
                plt.close(fig)

        case 'models vs npolys':
            y, x = args.type.split(' vs ')
            for name, fig in compare_columns(df, [((f'{x}_{enum}', f'{y}_{enum}'), enum) for enum in
                                                  enumerator2steps.keys()]):
                fig.savefig(args.folder / f'{name}.pdf')
                plt.close(fig)

        case 'ridgeplot_s':
            column = args.type.removeprefix('ridgeplot_')
            for name, fig in ridgeplot(df, column):
                fig.savefig(args.folder / f'{name}.pdf')
                plt.close(fig)

        case _:
            raise RuntimeError('?')


if __name__ == '__main__':
    main()
