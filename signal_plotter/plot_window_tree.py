from __future__ import annotations

import logging
import os
import sys
from typing import NoReturn

import numpy as np
from pyqtgraph import AxisItem, InfiniteLine, PlotCurveItem, PlotWidget, ViewBox, intColor
from pyqtgraph.Qt.QtCore import Qt, Signal, Slot
from pyqtgraph.Qt.QtGui import QColor, QPalette
from pyqtgraph.Qt.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMainWindow,
    QPushButton,
    QScrollArea,
    QSplitter,
    QTreeWidget,
    QTreeWidgetItem,
    QTreeWidgetItemIterator,
    QWidget,
)

logger = logging.getLogger('plot_window_tree')
logger.setLevel(logging.DEBUG)


pyqtSignal = Signal
pyqtSlot = Slot


class ListContainer(QScrollArea):
    changeItem = pyqtSignal(dict)

    def __init__(self, items: dict = None, parent=None) -> None:
        super().__init__(parent)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        # self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.setWidgetResizable(True)

        # For each element in items add a "state" flag
        self.listItem = items
        for key, value in self.listItem.items():
            self.listItem[key].setdefault("state", False)

        self.itemChk = []
        self.initUI()

    def set_manual_keys(self, items) -> None:
        # For each element in items add a "state" flag
        for key, _ in self.listItem.items():
            # self.listItem[key].setdefault("state", False)
            self.listItem[key]["state"] = key in items
        self.changeItem.emit({key: {"state": value["state"]} for key, value in self.listItem.items()})

        # Reset the UI to reflect the new state and check the pre-selected items
        self.resetUI()

    def initUI(self) -> None:
        self.tree = QTreeWidget()
        self.tree.setHeaderHidden(True)
        self.setWidget(self.tree)

        # Set size of all columns according to the content
        self.tree.header().setSectionResizeMode(QHeaderView.ResizeToContents)

        self.resetUI()

    def resetUI(self) -> None:
        # Clear the tree
        self.tree.clear()

        # Populate the tree
        # For each key in the dict Add a button to append the item to the selcted list
        current_box = []

        current_box = []
        tree_parent_levels = [self.tree]

        for i, key in enumerate(sorted(self.listItem.keys())):
            for j in range(len(key.split("."))):
                if len(current_box) <= j:
                    # if current_box size is smaller than the current level
                    current_box.append(key.split(".")[j])

                else:
                    if key.split(".")[j] != current_box[j]:
                        current_box[j] = key.split(".")[j]
                        # Remove all the items after the current level
                        for k in range(j + 1, len(current_box)):
                            current_box.pop()
                    else:
                        continue
                    tree_parent_levels = tree_parent_levels[: j + 1]

                child = QTreeWidgetItem(tree_parent_levels[-1])
                # if j == len(key.split(".")) - 1:
                #     self.itemChk.append(child)
                if j > 0:
                    child.setFlags(
                        child.flags() | tree_parent_levels[-1].flags() | Qt.ItemIsAutoTristate | Qt.ItemIsUserCheckable
                    )
                else:
                    child.setFlags(child.flags() | Qt.ItemIsAutoTristate | Qt.ItemIsUserCheckable)
                child.setCheckState(
                    0,
                    Qt.Unchecked if not self.listItem[key]["state"] else Qt.Checked,
                )
                child.setText(0, key.split(".")[j])
                tree_parent_levels.append(child)

        self.tree.clicked.connect(self.vrfs_selected)

    def vrfs_selected(self) -> None:
        """Function to check whick box is checked inside de QTreeWidget in the tab window"""
        iterator = QTreeWidgetItemIterator(
            self.tree,
            QTreeWidgetItemIterator.Checked,
        )
        checked = []
        while iterator.value():
            item = iterator.value()
            # Recusively find the parent of the item
            name = item.text(0)
            parent = item.parent()
            while parent is not None:
                name = parent.text(0) + "." + name
                parent = parent.parent()
            checked.append(name)
            iterator += 1

        # Set state and emit signal
        for key in self.listItem.keys():
            self.listItem[key]["state"] = key in checked
        self.changeItem.emit({key: {"state": value["state"]} for key, value in self.listItem.items()})


class SignalContainer(QWidget):
    changeParam = pyqtSignal(dict)

    class AxeReference:
        def __init__(self, view: ViewBox, axis: AxisItem, line: InfiniteLine, units: str = None) -> None:
            self.view = view
            self.axis = axis
            self.line = line
            self.units = units

    def __init__(self, items: dict = None, x_component: str | None = "x", **kwargs) -> None:
        super().__init__()
        self.items = items
        self.title = "Signal plotter"

        self.x_component: str = x_component if x_component is not None else "x"
        self.x_options: list[str] = ["x"] + list(self.items.keys())

        self.sigstate = []

        self.axes = {}

        self.initUI(**kwargs)

    def initUI(self, **kwargs) -> None:
        self.setWindowTitle(self.title)
        self.resize(800, 400)
        self.mainLayout = QHBoxLayout()
        self.setLayout(self.mainLayout)

        # Set up the splitter
        self.splitter = QSplitter()
        self.mainLayout.addWidget(self.splitter)

        # region Selector Widget
        self.selectorWidget = QWidget()
        self.selectorLayout = QGridLayout()
        self.selectorWidget.setLayout(self.selectorLayout)
        self.splitter.addWidget(self.selectorWidget)

        # Create the list container
        self.x_axis_label = QLabel("Signals:")
        self.selectorLayout.addWidget(self.x_axis_label, 0, 0, 1, 1)
        # Clear button
        self.clearButton = QPushButton("Clear")
        self.clearButton.setAutoFillBackground(True)
        self.clearButton.clicked.connect(self.clearSignals)
        self.selectorLayout.addWidget(self.clearButton, 0, 2, 1, 1)
        # List container
        self.select = ListContainer(self.items)
        self.select.changeItem.connect(self.setSignal)
        self.selectorLayout.addWidget(self.select, 1, 0, 1, 3)

        # Link axis checkbox
        self.linkAxis = QCheckBox("Link Y-axes")
        self.linkAxis.setChecked(True)
        self.linkAxis.stateChanged.connect(self.setSignal)
        self.selectorLayout.addWidget(self.linkAxis, 2, 0, 1, 3)

        # Create the x_axis selector
        self.x_axis_label = QLabel("X axis:")
        self.selectorLayout.addWidget(self.x_axis_label, 3, 0, 1, 1)
        self.x_axis = QComboBox()
        self.x_axis.addItems(self.x_options)
        self.x_axis.setCurrentIndex(self.x_options.index(self.x_component))
        self.x_axis.currentIndexChanged.connect(self.setXAxis)
        self.selectorLayout.addWidget(self.x_axis, 3, 1, 1, 2)
        # endregion Selector Widget

        # region Plot Widget
        self.graphWidget = PlotWidget()
        self.plotItem = self.graphWidget.getPlotItem()
        self.plotScene = self.graphWidget.scene()

        self.plotItem.vb.sigResized.connect(self.updateViews)

        # self.mainLayout.addLayout(self.signalLayout)
        self.splitter.addWidget(self.graphWidget)

        # Set Strecth factor to give plot the most space
        self.splitter.setStretchFactor(0, 1)
        self.splitter.setStretchFactor(1, 10)

        # tune plots
        self.graphWidget.setBackground((25, 25, 25, 255))  # RGBA         #background
        # self.graphWidget.setTitle("Signal(t)", color="w", size="20pt")  # add title
        # styles = {"color": "r", "font-size": "20px"}  # add label style
        # self.graphWidget.setLabel("left", "signal [SI]", **styles)  # add ylabel
        self.graphWidget.getAxis("left").enableAutoSIPrefix(True)
        # self.graphWidget.setLabel("bottom", "time [s]", **styles)  # add xlabel
        self.graphWidget.getAxis("bottom").enableAutoSIPrefix(True)
        self.graphWidget.showGrid(x=True, y=True)  # add grid
        # Setup clipping and downsampling to reduce CPU usage
        # We expect very large signal data sets, so downsampling is a must
        self.graphWidget.setClipToView(clip=True)
        self.graphWidget.setDownsampling(
            ds=kwargs.get("downsampling", True),
            auto=True,
            mode="subsample",
        )
        self.legend = self.graphWidget.addLegend()  # add grid
        # endregion Plot Widget

        # Connect the sigYRangeChanged signal to the updateViews slot
        # self.plotItem.vb.sigYRangeChanged.connect(self.updateViews)

    @property
    def sperateAxes(self) -> bool:
        return not self.linkAxis.isChecked()

    def setXAxis(self, index: int) -> None:
        self.x_component = self.x_options[index]

        # update graph (with the same signals)
        self.setSignal(self.sigstate)

    def clearSignals(self) -> None:
        # self.select.changeItem.emit([False] * len(self.items))
        self.select.set_manual_keys([])

    def updateViews(self) -> None:
        ## Handle view resizing
        ## view has resized; update auxiliary views to match
        for axis in self.axes.values():
            axis.view.setGeometry(self.plotItem.vb.sceneBoundingRect())
            ## need to re-update linked axes since this was called
            ## incorrectly while views had different shapes.
            ## (probably this should be handled in ViewBox.resizeEvent)
            axis.view.linkedViewChanged(self.plotItem.vb, axis.view.XAxis)

    def createAxis(self, units: str) -> None:
        # if the main axis does not have any units, give it priority over the others
        if not any(axis.view is self.plotItem.getViewBox() for axis in self.axes.values()):
            self.plotItem.setLabel("left", units, units=units)
            if units in self.axes:
                # Remove previous reference to this axis
                self.plotItem.layout.removeItem(self.axes[units].axis)
                self.plotScene.removeItem(self.axes[units].view)
                self.axes[units].view.deleteLater()
                self.axes[units].axis.deleteLater()
            # Set the main axis to the this units
            self.axes[units] = self.AxeReference(
                view=self.plotItem.getViewBox(),
                axis=self.plotItem.getAxis("left"),
                line=None,
                units=units,
            )

        # If self.axes is empty, create the first axis
        if not self.axes:
            self.plotItem.setLabel("left", units, units=units)
            self.axes[units] = self.AxeReference(
                view=self.plotItem.getViewBox(),
                axis=self.plotItem.getAxis("left"),
                line=None,
                units=units,
            )

        # Check if this units is already in the plot
        elif units not in self.axes:
            logger.debug(f"Creating new axis for units {units}")
            # Create a new axis for this units
            self.axes[units] = self.AxeReference(
                view=ViewBox(),
                axis=AxisItem('right'),
                line=InfiniteLine(pos=0, angle=0),
                units=units,
            )
            self.plotItem.layout.addItem(self.axes[units].axis, 2, list(sorted(self.axes.keys())).index(units) + 3)
            self.plotScene.addItem(self.axes[units].view)
            self.axes[units].axis.linkToView(self.axes[units].view)
            self.axes[units].view.setXLink(self.plotItem)
            self.axes[units].axis.setLabel(units, units=units, color=intColor(sorted(list(self.axes.keys())).index(units)))
            self.axes[units].view.addItem(self.axes[units].line)

        # Update wether the axis is linked or not
        self.axes[units].view.setYLink(self.plotItem if self.linkAxis.isChecked() else None)

    def cleanAxes(self) -> None:
        # Remove unused axis
        for units in list(self.axes.keys()):
            if (
                (
                    units
                    not in [
                        data["units"]
                        for data in self.items.values()
                        if "units" in data and data["units"] is not None and data["state"]
                    ]
                )
                or self.x_component != "x"
                or not self.sperateAxes
            ):
                logger.debug(f"Removing axis for units {units}")
                if self.axes[units].view is not self.plotItem.getViewBox():
                    self.plotItem.layout.removeItem(self.axes[units].axis)
                    self.plotScene.removeItem(self.axes[units].view)
                    self.axes[units].view.deleteLater()
                    self.axes[units].axis.deleteLater()
                del self.axes[units]

    @pyqtSlot(list)
    def setSignal(self, states) -> None:
        self.sigstate = states

        # update graph
        self.graphWidget.clear()
        for units, axis_item in self.axes.items():
            axis_item.view.clear()
            # Re-add the line which was removed by clear()
            if axis_item.line is not None:
                axis_item.view.addItem(axis_item.line)

        # Reset the y-axis label if axes are linked
        if not self.sperateAxes:
            self.plotItem.setLabel("left", label=None, units=None)

        self.cleanAxes()

        # clear legend
        self.legend.clear()

        # if X-axis is not default, change the label and units
        if self.x_component != "x":
            self.plotItem.setLabel(
                "bottom",
                self.x_component,
                units=self.items[self.x_component]["units"] if "units" in self.items[self.x_component] else None,
            )
        else:
            # Reset to default (Assume all signals are time-based)
            self.plotItem.setLabel("bottom", "time", units="s")

        # self.graphWidget.plot(self.time, self.data,name = "signal",pen=self.pen,symbol='+', symbolSize=5, symbolBrush='w')
        for j, (key, data) in enumerate([(key, data) for key, data in self.items.items() if data["state"]]):
            # If units is provided, use it to display the signal according to the respective axis

            if self.x_component == "x":
                if self.sperateAxes and "units" in data and data["units"] is not None:
                    self.createAxis(data["units"])
                    units = data["units"]
                    plot = PlotCurveItem(data["x"], data["y"], name=key, pen=intColor(j))
                    self.axes[units].view.addItem(plot)
                    self.legend.addItem(plot, f"{key} ({data['units']})")
                else:
                    self.plotItem.plot(data["x"], data["y"], name=key, pen=intColor(j))

            else:
                # if the signals don't have the same length, the plot will fail
                if len(self.items[self.x_component]["y"]) != len(data["y"]):
                    logger.error(
                        f"Signal {key} has different length for x and y components: "
                        + f"{len(self.items[self.x_component]['y'])} != {len(data['y'])}"
                    )
                    continue
                self.plotItem.plot(
                    self.items[self.x_component]["y"], data["y"], name=f"{key} ({data['units']})", pen=intColor(j)
                )

        # Update the views
        self.updateViews()


def plot_window(items: dict = None, pre_select: list[str] = None, x_component: str = None, **kwargs) -> NoReturn:
    """
    Initialize an oscilloscope-like window with the given signals.

    Args:
        items (dict): Dictionary of signals to be displayed. Each key is a signal name and the value is another dict with both "x" and "y" keys, each containing a numpy array with the signal data.
        pre_select (list[str]): List of signal names to be pre-selected.
        x_component (str): Name of the signal to be used as x axis. If None, the first signal will be used.

    Returns:
        NoReturn: None
    """

    app = QApplication(sys.argv)

    # Now use a palette to switch to dark colors:
    palette = QPalette()
    palette.setColor(QPalette.Window, QColor(50, 50, 50))
    palette.setColor(QPalette.WindowText, Qt.white)
    palette.setColor(QPalette.Base, QColor(25, 25, 25))
    palette.setColor(QPalette.AlternateBase, QColor(50, 50, 50))
    palette.setColor(QPalette.ToolTipBase, Qt.white)
    palette.setColor(QPalette.ToolTipText, Qt.white)
    palette.setColor(QPalette.Text, Qt.white)
    palette.setColor(QPalette.Button, Qt.black)
    palette.setColor(QPalette.ButtonText, Qt.white)
    palette.setColor(QPalette.BrightText, Qt.red)
    palette.setColor(QPalette.Link, QColor(99, 190, 231))
    palette.setColor(QPalette.Highlight, QColor(99, 190, 231))
    palette.setColor(QPalette.HighlightedText, Qt.white)
    palette.setColor(QPalette.WindowText, Qt.white)
    app.setPalette(palette)

    # Set custom arrow style as the color is not configurable through the palette
    app.setStyleSheet(
        """
        QTreeView::branch::closed::has-children {
            image: url("""
        + os.path.relpath(os.path.join(os.path.dirname(__file__), "arrow.png"), os.getcwd()).replace("\\", "/")
        + """);
        }
        QTreeView::branch::open::has-children {
            image: url("""
        + os.path.relpath(os.path.join(os.path.dirname(__file__), "arrow-closed.png"), os.getcwd()).replace("\\", "/")
        + """);
        }
        QComboBox { background-color: black; }
        QPushButton { background-color: black; }
        """
    )

    # Check if the x_component is safe to use
    if x_component is not None:
        if x_component not in items:
            logger.error(f"Selected x_component {x_component} not found in items dict")
            x_component = None

    # Create the main window
    main_window = QMainWindow()
    main_window.setWindowTitle("Signal plotter")
    main_window.resize(800, 400)

    ex = SignalContainer(items=items, x_component=x_component, **kwargs)
    main_window.setCentralWidget(ex)

    # Set pre-selected items
    if pre_select is not None:
        ex.select.set_manual_keys(pre_select)

    # Show the window
    main_window.show()

    # Run the application and wait for the window to be closed
    sys.exit(app.exec())


if __name__ == "__main__":
    console_handler = logging.StreamHandler()
    logger.addHandler(console_handler)

    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    console_handler.setFormatter(formatter)

    # Generate random data
    items = {}
    time = np.linspace(0, 1, 5) * 10
    for i in range(3):
        for j in range(4):
            for k in range(3):
                x = np.random.choice([-1, 1])  # random sign
                s = np.random.rand() * 0.2  # random scale
                fun = np.random.choice([np.sin, np.cos])  # random function

                items[f"group_{i}.signal_{j}.subsignal_{k}"] = {
                    "x": time,
                    "y": x * fun(time) + np.random.normal(scale=s, size=len(time)),
                    "units": "V",
                }

    for i in range(10):
        x = np.random.choice([-1, 1])  # random sign
        s = np.random.rand() * 0.2  # random scale
        fun = np.random.choice([np.sin, np.cos])  # random function

        items["external_signal{}".format(i)] = {
            "x": time,
            "y": x * fun(time) + np.random.normal(scale=s, size=len(time)),
            "units": "A",
        }

    items.update(
        {
            "external_signal99".format(i): {
                "x": time,
                "y": np.random.rand(len(time)) * 100,
                "units": "Nm",
            }
        }
    )

    plot_window(
        items={
            'signal_1': {'x': [0, 1, 2, 3, 4, 5], 'y': [0, 4, 2, 3, 1, 5], 'units': 'V'},
            'signal_2.sub_signal_1': {'x': [0, 1, 2, 3, 4, 5], 'y': [5, 4, 3, 2, 1, 0], 'units': 'A'},
            'signal_2.sub_signal_2': {'x': [0, 1, 2, 3, 4, 5], 'y': [0, 1, 2, 3, 4, 5], 'units': 'A'},
        },
        # pre_select=[
        #     "group_0.signal_0.subsignal_2",
        #     "external_signal4",
        # ],
        # x_component="group_0.signal_0.subsignal_0",
        downsampling=False,
    )
