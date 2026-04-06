import matplotlib
matplotlib.use("Qt5Agg")

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure


class ChartWidget(FigureCanvas):
    """Reusable Matplotlib chart widget embedded in PyQt5."""

    COLORS = [
        "#00b894", "#0984e3", "#fdcb6e", "#d63031",
        "#6c5ce7", "#00cec9", "#fd79a8", "#e17055"
    ]

    def __init__(self, parent=None, width=5, height=4, dpi=100):
        self.fig = Figure(figsize=(width, height), dpi=dpi)
        self.fig.set_facecolor("#1a1a35")
        super().__init__(self.fig)
        self.setParent(parent)

    def _style_axes(self, ax):
        """Apply dark theme styling to axes."""
        ax.set_facecolor("#1a1a35")
        ax.tick_params(colors="#8888aa", labelsize=8)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.spines["bottom"].set_color("#3a3a5a")
        ax.spines["left"].set_color("#3a3a5a")
        ax.xaxis.label.set_color("#8888aa")
        ax.yaxis.label.set_color("#8888aa")
        ax.title.set_color("#e0e0e0")

    def plot_bar(self, categories: list, values: list, title: str = ""):
        """Draw a bar chart."""
        self.fig.clear()
        ax = self.fig.add_subplot(111)
        self._style_axes(ax)

        colors = self.COLORS[:len(categories)]
        ax.bar(categories, values, color=colors, width=0.6)
        ax.set_title(title, fontsize=12, fontweight="bold")
        ax.set_ylabel("Count")

        # Rotate labels if needed
        if len(categories) > 4:
            ax.tick_params(axis="x", rotation=45)

        self.fig.tight_layout()
        self.draw()

    def plot_pie(self, labels: list, values: list, title: str = ""):
        """Draw a pie chart."""
        self.fig.clear()
        ax = self.fig.add_subplot(111)
        ax.set_facecolor("#1a1a35")

        colors = self.COLORS[:len(labels)]
        wedges, texts, autotexts = ax.pie(
            values, labels=labels, autopct="%1.1f%%", colors=colors,
            textprops={"color": "#e0e0e0", "fontsize": 9},
            pctdistance=0.85, startangle=90
        )
        for t in autotexts:
            t.set_color("#ffffff")
            t.set_fontsize(8)

        ax.set_title(title, fontsize=12, fontweight="bold", color="#e0e0e0")
        self.fig.tight_layout()
        self.draw()

    def plot_line(self, x_data: list, y_data: list, title: str = "", xlabel: str = "", ylabel: str = ""):
        """Draw a line chart."""
        self.fig.clear()
        ax = self.fig.add_subplot(111)
        self._style_axes(ax)

        ax.plot(x_data, y_data, color="#00b894", marker="o", linewidth=2, markersize=4)
        ax.fill_between(x_data, y_data, alpha=0.1, color="#00b894")
        ax.set_title(title, fontsize=12, fontweight="bold")
        if xlabel:
            ax.set_xlabel(xlabel)
        if ylabel:
            ax.set_ylabel(ylabel)

        if len(x_data) > 5:
            ax.tick_params(axis="x", rotation=45)

        self.fig.tight_layout()
        self.draw()

    def clear_chart(self):
        """Clear the chart."""
        self.fig.clear()
        self.draw()
