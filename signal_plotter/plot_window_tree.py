from __future__ import annotations

import logging
import os
import sys
from typing import NoReturn, Optional

import numpy as np
from pyqtgraph import PlotWidget, intColor
from PySide6.QtCore import Qt, Signal, Slot
from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QScrollArea,
    QSplitter,
    QTreeWidget,
    QTreeWidgetItem,
    QTreeWidgetItemIterator,
    QVBoxLayout,
    QWidget,
)

logger = logging.getLogger('plot_window_tree')
logger.setLevel(logging.INFO)


pyqtSignal = Signal
pyqtSlot = Slot


class ListContainer(QScrollArea):
    changeItem = pyqtSignal(list)

    def __init__(self, items: dict = None, parent=None) -> None:
        super(ListContainer, self).__init__(parent)
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
        for key, value in self.listItem.items():
            # self.listItem[key].setdefault("state", False)
            self.listItem[key]["state"] = key in items
        self.changeItem.emit([self.listItem[k]["state"] for k in self.listItem.keys()])

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

            logger.debug(
                [
                    i,
                    j,
                    key,
                    child.text(0),
                    current_box,
                    [item.text(0) for item in tree_parent_levels[1:]],
                ]
            )

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
        self.changeItem.emit([self.listItem[k]["state"] for k in self.listItem.keys()])


class SignalContainer(QWidget):
    changeParam = pyqtSignal(dict)

    def __init__(self, items: dict = None, x_component: Optional[str] = "x") -> None:
        super().__init__()
        self.items = items
        self.title = "Signal plotter"

        self.x_component: str = x_component if x_component is not None else "x"
        self.x_options: list[str] = ["x"] + list(self.items.keys())

        self.sigstate = []
        self.initUI()

    def initUI(self) -> None:
        self.setWindowTitle(self.title)
        self.resize(800, 400)
        self.mainLayout = QHBoxLayout()
        self.setLayout(self.mainLayout)

        # Set up the splitter
        self.splitter = QSplitter()
        self.mainLayout.addWidget(self.splitter)

        self.selectorWidget = QWidget()
        self.selectorLayout = QVBoxLayout()
        self.selectorWidget.setLayout(self.selectorLayout)
        self.splitter.addWidget(self.selectorWidget)

        # Create the list container
        self.x_axis_label = QLabel("Signals:")
        self.selectorLayout.addWidget(self.x_axis_label)
        self.select = ListContainer(self.items)
        self.select.changeItem.connect(self.setSignal)
        self.selectorLayout.addWidget(self.select)
        # self.splitter.addWidget(self.select)

        # Create the x_axis selector
        self.x_axis_label = QLabel("X axis:")
        self.selectorLayout.addWidget(self.x_axis_label)
        self.x_axis = QComboBox()
        self.x_axis.addItems(self.x_options)
        self.x_axis.setCurrentIndex(self.x_options.index(self.x_component))
        self.x_axis.currentIndexChanged.connect(self.setXAxis)
        self.selectorLayout.addWidget(self.x_axis)

        # Create the graph
        self.graphWidget = PlotWidget()
        # self.mainLayout.addLayout(self.signalLayout)
        self.splitter.addWidget(self.graphWidget)

        # tune plots
        self.graphWidget.setBackground((50, 50, 50, 220))  # RGBA         #background
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
        self.graphWidget.setDownsampling(ds=True, auto=True, mode="subsample")
        self.graphWidget.addLegend()  # add grid

    def setXAxis(self, index: int) -> None:
        self.x_component = self.x_options[index]

        # update graph (with the same signals)
        self.setSignal(self.sigstate)

    @pyqtSlot(list)
    def setSignal(self, states) -> None:
        self.sigstate = states

        # update graph
        self.graphWidget.clear()
        # self.graphWidget.plot(self.time, self.data,name = "signal",pen=self.pen,symbol='+', symbolSize=5, symbolBrush='w')
        j = 0
        for i, (key, data) in enumerate(self.items.items()):
            if self.sigstate[i]:  # display signal
                if self.x_component == "x":
                    self.graphWidget.plot(data["x"], data["y"], name=key, pen=intColor(j))
                else:
                    # if the signals don't have the same length, the plot will fail
                    if len(self.items[self.x_component]["y"]) != len(data["y"]):
                        logger.error(
                            f"Signal {key} has different length for x and y components: "
                            + f"{len(self.items[self.x_component]['y'])} != {len(data['y'])}"
                        )
                        continue
                    self.graphWidget.plot(self.items[self.x_component]["y"], data["y"], name=key, pen=intColor(j))
                j += 1


def main(items: dict = None, pre_select: list[str] = None, x_component: str = None) -> NoReturn:
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
    palette.setColor(QPalette.Button, QColor(50, 50, 50))
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
    """
    )

    # Check if the x_component is safe to use
    if x_component is not None:
        if x_component not in items:
            logger.error(f"Selected x_component {x_component} not found in items dict")
            x_component = None

    # Create the main window
    ex = SignalContainer(items=items, x_component=x_component)

    # Set pre-selected items
    if pre_select is not None:
        ex.select.set_manual_keys(pre_select)

    # Show the window
    ex.show()

    # Run the application and wait for the window to be closed
    sys.exit(app.exec())


if __name__ == "__main__":
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
                }

    for i in range(10):
        x = np.random.choice([-1, 1])  # random sign
        s = np.random.rand() * 0.2  # random scale
        fun = np.random.choice([np.sin, np.cos])  # random function

        items["external_signal{}".format(i)] = {
            "x": time,
            "y": x * fun(time) + np.random.normal(scale=s, size=len(time)),
        }

    main(
        items=items,
        pre_select=[
            "group_0.signal_0.subsignal_2",
            "external_signal4",
        ],
        # x_component="group_0.signal_0.subsignal_0",
    )
