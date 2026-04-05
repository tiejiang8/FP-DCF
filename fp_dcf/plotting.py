from __future__ import annotations

from pathlib import Path

import numpy as np

from .schemas import SensitivityHeatmapOutput

try:  # pragma: no cover - optional dependency path
    import matplotlib.pyplot as plt
    from matplotlib.colors import LinearSegmentedColormap
    from matplotlib.patches import Rectangle
except ImportError:  # pragma: no cover - exercised when viz deps are missing
    plt = None
    LinearSegmentedColormap = None
    Rectangle = None


def _require_matplotlib() -> None:
    if plt is None or LinearSegmentedColormap is None or Rectangle is None:
        raise RuntimeError(
            "Heatmap rendering requires matplotlib. Install the optional viz dependencies first, "
            "for example with `python3 -m pip install .[viz]`."
        )


def _format_percent(value: float) -> str:
    return f"{value * 100:.1f}%"


def _format_metric(value: float | None, metric: str, currency: str | None) -> str:
    if value is None:
        return "NA"

    if metric == "per_share_value":
        prefix = f"{currency} " if currency else ""
        if abs(value) >= 1000:
            return f"{prefix}{value:,.0f}"
        if abs(value) >= 100:
            return f"{prefix}{value:,.1f}"
        return f"{prefix}{value:,.2f}"

    scale = 1.0
    suffix = ""
    if abs(value) >= 1_000_000_000_000:
        scale = 1_000_000_000_000
        suffix = "T"
    elif abs(value) >= 1_000_000_000:
        scale = 1_000_000_000
        suffix = "B"
    elif abs(value) >= 1_000_000:
        scale = 1_000_000
        suffix = "M"

    prefix = f"{currency} " if currency else ""
    return f"{prefix}{value / scale:,.1f}{suffix}"


def render_wacc_terminal_growth_heatmap(
    heatmap: SensitivityHeatmapOutput,
    output_path: str | Path,
    *,
    title: str | None = None,
) -> Path:
    _require_matplotlib()
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    display_rows = list(reversed(heatmap.matrix))
    display_wacc_values = list(reversed(heatmap.wacc_values))
    data = np.array([[np.nan if value is None else value for value in row] for row in display_rows], dtype=float)
    masked = np.ma.masked_invalid(data)

    cmap = LinearSegmentedColormap.from_list(
        "fp_dcf_heatmap",
        ["#8c2f39", "#e9c46a", "#2a9d8f"],
    )
    cmap.set_bad(color="#eceff1")

    fig_width = max(7.0, 1.15 * len(heatmap.terminal_growth_values) + 3.2)
    fig_height = max(5.2, 1.0 * len(heatmap.wacc_values) + 2.4)
    fig, ax = plt.subplots(figsize=(fig_width, fig_height), dpi=180)

    image = ax.imshow(masked, cmap=cmap, aspect="auto")
    ax.set_xticks(range(len(heatmap.terminal_growth_values)))
    ax.set_xticklabels([_format_percent(value) for value in heatmap.terminal_growth_values])
    ax.set_yticks(range(len(display_wacc_values)))
    ax.set_yticklabels([_format_percent(value) for value in display_wacc_values])
    ax.set_xlabel("Terminal Growth Rate")
    ax.set_ylabel("WACC")

    chart_title = title or f"{heatmap.ticker} Sensitivity Heatmap"
    ax.set_title(
        f"{chart_title}\n{heatmap.metric_label} across WACC x Terminal Growth",
        loc="left",
        fontsize=12,
        pad=14,
    )

    ax.set_xticks(np.arange(-0.5, len(heatmap.terminal_growth_values), 1), minor=True)
    ax.set_yticks(np.arange(-0.5, len(display_wacc_values), 1), minor=True)
    ax.grid(which="minor", color="#ffffff", linewidth=1.5)
    ax.tick_params(which="minor", bottom=False, left=False)

    for row_index, row in enumerate(display_rows):
        for col_index, value in enumerate(row):
            text = _format_metric(value, heatmap.metric, heatmap.currency)
            ax.text(
                col_index,
                row_index,
                text,
                ha="center",
                va="center",
                fontsize=8,
                color="#132a13" if value is not None else "#5c6770",
            )

    if heatmap.base_wacc in heatmap.wacc_values and heatmap.base_terminal_growth_rate in heatmap.terminal_growth_values:
        base_row = display_wacc_values.index(heatmap.base_wacc)
        base_col = heatmap.terminal_growth_values.index(heatmap.base_terminal_growth_rate)
        ax.add_patch(
            Rectangle(
                (base_col - 0.5, base_row - 0.5),
                1.0,
                1.0,
                fill=False,
                linewidth=2.5,
                edgecolor="#1d3557",
            )
        )

    colorbar = fig.colorbar(image, ax=ax, fraction=0.046, pad=0.04)
    colorbar.ax.set_ylabel(heatmap.metric_label, rotation=270, labelpad=18)

    fig.text(
        0.01,
        0.01,
        "Base case outlined in blue. Grey cells indicate terminal growth >= WACC and are left blank.",
        fontsize=8,
        color="#44515c",
    )

    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)
    return path
