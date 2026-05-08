import matplotlib
matplotlib.use("Qt5Agg")

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure


class ChartWidget(FigureCanvas):
    """Reusable Matplotlib chart widget with design-system dark theme."""

    BG_COLOR = "#222629"
    TEXT_COLOR = "#E5E5E5"
    MUTED_COLOR = "#BFC5C9"
    GRID_COLOR = "#2E3338"

    # Design system: primary accent, then supporting colors
    COLORS = [
        "#52796A", "#FFC107", "#64B5F6", "#E57373",
        "#BAC5AC", "#06b6d4", "#ec4899", "#f97316"
    ]

    def __init__(self, parent=None, width=5, height=4, dpi=100):
        self.fig = Figure(figsize=(width, height), dpi=dpi)
        self.fig.set_facecolor(self.BG_COLOR)
        super().__init__(self.fig)
        self.setParent(parent)

    def _style_axes(self, ax):
        """Apply design-system dark theme styling to axes."""
        ax.set_facecolor(self.BG_COLOR)
        ax.tick_params(colors=self.MUTED_COLOR, labelsize=8)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.spines["bottom"].set_color(self.GRID_COLOR)
        ax.spines["left"].set_color(self.GRID_COLOR)
        ax.xaxis.label.set_color(self.MUTED_COLOR)
        ax.yaxis.label.set_color(self.MUTED_COLOR)
        ax.title.set_color(self.TEXT_COLOR)
        ax.grid(True, axis="y", color=self.GRID_COLOR, linewidth=0.5, alpha=0.5)

    def plot_bar(self, categories: list, values: list, title: str = ""):
        """Draw a bar chart with accent yellow bars."""
        self.fig.clear()
        ax = self.fig.add_subplot(111)
        self._style_axes(ax)

        # Use accent yellow for bars
        bars = ax.bar(categories, values, color="#FFC107", width=0.6,
                      edgecolor="none", alpha=0.9)
        ax.set_title(title, fontsize=12, fontweight="bold")
        ax.set_ylabel("Count", color=self.MUTED_COLOR)

        # Value labels on bars
        for bar, val in zip(bars, values):
            ax.text(
                bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.5,
                str(val), ha="center", va="bottom",
                color=self.TEXT_COLOR, fontsize=8, fontweight="bold"
            )

        if len(categories) > 4:
            ax.tick_params(axis="x", rotation=45)

        self.fig.tight_layout()
        self.draw()

    def plot_pie(self, labels: list, values: list, title: str = ""):
        """Draw a pie chart with design-system colors."""
        self.fig.clear()
        ax = self.fig.add_subplot(111)
        ax.set_facecolor(self.BG_COLOR)

        colors = self.COLORS[:len(labels)]
        wedges, texts, autotexts = ax.pie(
            values, labels=labels, autopct="%1.1f%%", colors=colors,
            textprops={"color": self.TEXT_COLOR, "fontsize": 9},
            pctdistance=0.82, startangle=90,
            wedgeprops={"edgecolor": self.BG_COLOR, "linewidth": 2}
        )
        for t in autotexts:
            t.set_color("#E5E5E5")
            t.set_fontsize(8)
            t.set_fontweight("bold")

        ax.set_title(title, fontsize=12, fontweight="bold", color=self.TEXT_COLOR)
        self.fig.tight_layout()
        self.draw()

    def plot_donut(self, labels: list, values: list, title: str = "",
                   center_text: str = "", center_subtext: str = "",
                   color_map: dict = None, min_label_pct: float = 8.0):
        """Draw a clean donut: wedges only, percentage labels inside slices that
        are large enough (>= min_label_pct), and a big readable center value.

        Args:
            labels: per-wedge label (used for color_map lookup, not plotted around).
            values: per-wedge numeric value.
            title: optional axis title.
            center_text: large bold text drawn in the donut hole (e.g. total).
            center_subtext: smaller muted text below center_text.
            color_map: optional {label: hex_color}.
            min_label_pct: hide the in-wedge percent label below this percentage.
        """
        self.fig.clear()
        ax = self.fig.add_subplot(111)
        ax.set_facecolor(self.BG_COLOR)

        if color_map:
            colors = [color_map.get(label, self.COLORS[i % len(self.COLORS)])
                      for i, label in enumerate(labels)]
        else:
            colors = self.COLORS[:len(labels)]

        total = float(sum(values)) or 1.0

        def _autopct(pct):
            return f"{pct:.0f}%" if pct >= min_label_pct else ""

        wedges, _texts, autotexts = ax.pie(
            values,
            labels=None,                     # legend is rendered in Qt — no clutter here
            autopct=_autopct,
            colors=colors,
            pctdistance=0.78,
            startangle=90,
            counterclock=False,
            wedgeprops={
                "edgecolor": self.BG_COLOR,
                "linewidth": 3,
                "width": 0.34,                # ring thickness
                "antialiased": True,
            },
        )
        for t in autotexts:
            t.set_color("#1A1D1F")
            t.set_fontsize(10)
            t.set_fontweight("bold")

        ax.set_aspect("equal")

        if center_text:
            ax.text(0, 0.08 if center_subtext else 0, center_text,
                    ha="center", va="center",
                    fontsize=22, fontweight="bold", color=self.TEXT_COLOR)
        if center_subtext:
            ax.text(0, -0.18, center_subtext, ha="center", va="center",
                    fontsize=10, color=self.MUTED_COLOR)

        if title:
            ax.set_title(title, fontsize=12, fontweight="bold",
                         color=self.TEXT_COLOR)

        self.fig.subplots_adjust(left=0.02, right=0.98, top=0.98, bottom=0.02)
        self.draw()

    def plot_line(self, x_data: list, y_data: list, title: str = "",
                  xlabel: str = "", ylabel: str = ""):
        """Draw a smooth line chart with primary green."""
        self.fig.clear()
        ax = self.fig.add_subplot(111)
        self._style_axes(ax)

        ax.plot(
            x_data, y_data, color="#52796A",
            marker="o", linewidth=2.5, markersize=4,
            markerfacecolor="#52796A", markeredgecolor="#52796A"
        )
        ax.fill_between(x_data, y_data, alpha=0.10, color="#52796A")
        ax.set_title(title, fontsize=12, fontweight="bold")
        if xlabel:
            ax.set_xlabel(xlabel)
        if ylabel:
            ax.set_ylabel(ylabel)

        if len(x_data) > 10:
            n = max(1, len(x_data) // 8)
            ax.set_xticks(range(0, len(x_data), n))
            ax.set_xticklabels([x_data[i] for i in range(0, len(x_data), n)])

        if len(x_data) > 5:
            ax.tick_params(axis="x", rotation=45)

        self.fig.tight_layout()
        self.draw()

    def clear_chart(self):
        """Clear the chart."""
        self.fig.clear()
        self.draw()
