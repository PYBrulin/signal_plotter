from __future__ import annotations

import logging
import os
import sys

import numpy as np
from pyqtgraph import AxisItem, InfiniteLine, PlotCurveItem, PlotWidget, ViewBox, intColor
from pyqtgraph.Qt.QtCore import Qt, Signal, Slot
from pyqtgraph.Qt.QtGui import QColor, QPalette
from pyqtgraph.Qt.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QCompleter,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
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
logger.setLevel(logging.INFO)


pyqtSignal = Signal
pyqtSlot = Slot


class ListContainer(QScrollArea):
    changeItem = pyqtSignal(dict)

    def __init__(self, items: dict = None, sub_groups: dict = None, parent=None) -> None:
        super().__init__(parent)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        # self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.setWidgetResizable(True)

        # For each element in items add a "state" flag
        self.listItem = items
        for key, value in self.listItem.items():
            self.listItem[key].setdefault("state", False)
            self.listItem[key].setdefault("visible", True)

        # User-defined subgroups of signals
        self.listSubGroups = sub_groups

        self.itemChk = []
        self.initUI()

    @property
    def has_subgroups(self) -> bool:
        return self.listSubGroups is not None

    def set_manual_keys(self, items) -> None:
        # For each element in items add a "state" flag
        for key, _ in self.listItem.items():
            # self.listItem[key].setdefault("state", False)
            self.listItem[key]["state"] = key in items
        self.changeItem.emit({key: {"state": value["state"]} for key, value in self.listItem.items()})
        self.resetUI()  # Reset the UI to reflect the new state

    def clearSignals(self) -> None:
        # For each element in items add a "state" flag
        for key, _ in self.listItem.items():
            self.listItem[key]["state"] = False
        self.changeItem.emit({key: {"state": value["state"]} for key, value in self.listItem.items()})
        self.resetUI()  # Reset the UI to reflect the new state

    def set_item_visibility(self, text: str) -> None:
        search = text.split("||")
        for key in self.listItem:
            self.listItem[key]["visible"] = any([s in key for s in search])
        self.resetUI()  # Reset the UI to reflect the new state

    def select_visible_items(self) -> None:
        for key in self.listItem:
            # Visibility is already set by set_item_visibility during the text completion
            self.listItem[key]["state"] = self.listItem[key]["visible"]
        self.changeItem.emit({key: {"state": value["state"]} for key, value in self.listItem.items()})
        self.resetUI()  # Reset the UI to reflect the new state

    def initUI(self) -> None:
        # Create the tree widget
        self.tree = QTreeWidget()
        self.tree.setColumnCount(2)
        self.tree.header().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.tree.header().setMinimumSectionSize(1)
        self.tree.setColumnWidth(1, 1)
        self.tree.header().setSectionResizeMode(1, QHeaderView.Fixed)
        self.tree.setHeaderHidden(True)

        if self.has_subgroups:
            self.tree_splitter = QSplitter()
            self.tree_splitter.setOrientation(Qt.Vertical)
            self.tree_splitter.addWidget(self.tree)

            # Add a second tree for the subgroups
            self.subtree = QTreeWidget()
            self.subtree.setColumnCount(2)
            self.subtree.header().setSectionResizeMode(0, QHeaderView.ResizeToContents)
            self.subtree.header().setMinimumSectionSize(1)
            self.subtree.setColumnWidth(1, 1)
            self.subtree.header().setSectionResizeMode(1, QHeaderView.Fixed)
            self.subtree.setHeaderHidden(True)
            self.tree_splitter.addWidget(self.subtree)

            # Give the first tree more space by default
            self.tree_splitter.setStretchFactor(0, 5)
            self.tree_splitter.setStretchFactor(1, 1)

            # Set the splitter as the main widget
            self.setWidget(self.tree_splitter)
        else:
            # Set the tree as the main widget
            self.setWidget(self.tree)

        self.resetUI()  # Reset the UI to reflect the new state

    def update_selected_tree(self) -> None:
        # Clear the tree
        self.tree.clear()

        # Populate the tree
        # For each key in the dict Add a button to append the item to the selcted list
        current_box = []
        tree_parent_levels = [self.tree]

        for i, key in enumerate(sorted(self.listItem.keys())):
            # Skip invisible items
            if not self.listItem[key]["visible"]:
                continue

            depth = len(key.split("."))
            for j in range(depth):
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

                # Set the unit label at the end of the tree
                if j == depth - 1:
                    child.setText(
                        1, f'[{self.listItem[key]["units"]}]' if self.listItem[key].get("units", None) is not None else ""
                    )
                    child.setTextAlignment(1, Qt.AlignRight)

                tree_parent_levels.append(child)

    def update_selected_subtree(self) -> None:
        self.subtree.clear()
        for key, value in self.listSubGroups.items():
            child = QTreeWidgetItem(self.subtree)
            child.setText(0, key)
            child.setFlags(child.flags() | Qt.ItemIsAutoTristate | Qt.ItemIsUserCheckable)
            for sub_value in value:
                if sub_value not in self.listItem:
                    logger.warning(f"Subgroup {sub_value} not found in the list of items")
                    continue
                sub_child = QTreeWidgetItem(child)
                sub_child.setFlags(sub_child.flags() | child.flags() | Qt.ItemIsAutoTristate | Qt.ItemIsUserCheckable)
                sub_child.setCheckState(
                    0,
                    Qt.Unchecked if not self.listItem[sub_value]["state"] else Qt.Checked,
                )
                sub_child.setText(0, sub_value)

                # Set the unit label in the second column
                sub_child.setText(
                    1,
                    (
                        f'[{self.listItem[sub_value]["units"]}]'
                        if self.listItem[sub_value].get("units", None) is not None
                        else ""
                    ),
                )
                sub_child.setTextAlignment(1, Qt.AlignRight)

    def resetUI(self) -> None:
        self.update_selected_tree()
        self.tree.clicked.connect(self.items_selected)

        if self.has_subgroups:
            self.update_selected_subtree()
            self.subtree.clicked.connect(self.subgroups_selected)

    def items_selected(self) -> None:
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

        if self.has_subgroups:
            self.update_selected_subtree()

    def subgroups_selected(self) -> None:
        """Function to check whick box is checked inside de QTreeWidget in the tab window"""
        iterator = QTreeWidgetItemIterator(
            self.subtree,
            QTreeWidgetItemIterator.Checked,
        )
        checked = []
        while iterator.value():
            item = iterator.value()
            # Recusively find the parent of the item
            name = item.text(0)
            checked.append(name)
            iterator += 1

        # Set state and emit signal
        for key in self.listItem.keys():
            self.listItem[key]["state"] = key in checked
        self.changeItem.emit({key: {"state": value["state"]} for key, value in self.listItem.items()})

        self.update_selected_tree()


class SignalContainer(PlotWidget):
    class AxeReference:
        def __init__(self, view: ViewBox, axis: AxisItem, line: InfiniteLine, units: str = None) -> None:
            self.view = view
            self.axis = axis
            self.line = line
            self.units = units

    def __init__(self, items: dict = None, x_component: str | None = "x", **kwargs) -> None:
        super().__init__()

        # Items dictionary of signals to be displayed
        self.items = items
        self.sub_goups = kwargs.get("sub_groups", None)

        # X-axis component
        self.x_component: str = x_component if x_component is not None else "x"
        self.x_options: list[str] = ["x"] + (list(self.items.keys()) if self.items is not None else [])

        # Signal state
        self.sigstate = []

        # Axes dictionary
        self.axes = {}
        self.linkAxis = True

        # Set up the UI
        self.initUI(**kwargs)

    def initUI(self, **kwargs) -> None:
        # region Plot Widget
        self.plotItem = self.getPlotItem()
        self.plotScene = self.scene()

        self.plotItem.vb.sigResized.connect(self.updateViews)

        # tune plots
        self.setBackground((25, 25, 25, 255))  # RGBA         #background
        # self.setTitle("Signal(t)", color="w", size="20pt")  # add title
        # styles = {"color": "r", "font-size": "20px"}  # add label style
        # self.setLabel("left", "signal [SI]", **styles)  # add ylabel
        self.getAxis("left").enableAutoSIPrefix(True)
        # self.setLabel("bottom", "time [s]", **styles)  # add xlabel
        self.getAxis("bottom").enableAutoSIPrefix(True)
        self.showGrid(x=True, y=True)  # add grid
        # Setup clipping and downsampling to reduce CPU usage
        # We expect very large signal data sets, so downsampling is a must
        self.setClipToView(clip=True)
        self.setDownsampling(
            ds=kwargs.get("downsampling", True),
            auto=True,
            mode="subsample",
        )
        self.legend = self.addLegend()  # add grid
        # endregion Plot Widget

        # Connect the sigYRangeChanged signal to the updateViews slot
        # self.plotItem.vb.sigYRangeChanged.connect(self.updateViews)

    @property
    def separateAxes(self) -> bool:
        return not self.linkAxis

    def setSeparateAxes(self, state: int) -> None:
        self.linkAxis = state

        # update graph (with the same signals)
        self.setSignal(self.sigstate)

    def setXAxis(self, index: int) -> None:
        self.x_component = self.x_options[index]

        # update graph (with the same signals)
        self.setSignal(self.sigstate)

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
            row = self.plotItem.layout.rowCount()
            col = self.plotItem.layout.columnCount()
            logging.debug(f"row {row} col {col}")
            self.plotItem.layout.addItem(self.axes[units].axis, 2, col)
            self.plotScene.addItem(self.axes[units].view)
            self.axes[units].axis.linkToView(self.axes[units].view)
            self.axes[units].view.setXLink(self.plotItem)
            self.axes[units].axis.setLabel(units, units=units, color=intColor(sorted(list(self.axes.keys())).index(units)))
            self.axes[units].view.addItem(self.axes[units].line)

        # Update wether the axis is linked or not (Do not link separate axes)
        self.axes[units].view.setYLink(self.plotItem if not self.separateAxes else None)

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
                or not self.separateAxes
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
        self.clear()
        for units, axis_item in self.axes.items():
            axis_item.view.clear()
            # Re-add the line which was removed by clear()
            if axis_item.line is not None:
                axis_item.view.addItem(axis_item.line)

        # Reset the y-axis label if axes are linked
        if not self.separateAxes:
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

        # self.plot(self.time, self.data,name = "signal",pen=self.pen,symbol='+', symbolSize=5, symbolBrush='w')
        for j, (key, data) in enumerate([(key, data) for key, data in self.items.items() if data["state"]]):
            # If units is provided, use it to display the signal according to the respective axis

            try:
                if self.x_component == "x":
                    if self.separateAxes and "units" in data and data["units"] is not None:
                        self.createAxis(data["units"])
                        units = data["units"]
                        plot = PlotCurveItem(data["x"], data["y"], name=key, pen=intColor(j))
                        self.axes[units].view.addItem(plot)
                        self.legend.addItem(plot, f"{key}" + (f" ({data['units']})" if "units" in data else ""))
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
                        self.items[self.x_component]["y"],
                        data["y"],
                        name=f"{key}" + (f" ({data['units']})" if "units" in data else ""),
                        pen=intColor(j),
                    )
            except Exception as e:
                logger.error(f"Error plotting signal {key}: {e}", exc_info=True)
        # Update the views
        self.updateViews()


class PlotWindow(QWidget):
    def __init__(self, items: dict = None, x_component: str | None = "x", **kwargs) -> None:
        super().__init__()
        self.title = kwargs.get("title", "Signal plotter")

        # Items dictionary of signals to be displayed
        self.items = items
        self.sub_goups = kwargs.get("sub_groups", None)

        # X-axis component
        self.x_component: str = x_component if x_component is not None else "x"
        self.x_options: list[str] = ["x"] + list(self.items.keys())

        # Signal state
        self.sigstate = []

        # Axes dictionary
        self.axes = {}

        # Set up the UI
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

        # Define the main widgets of the window
        self.listWidget = ListContainer(self.items, self.sub_goups)
        self.signalWidget = SignalContainer(self.items, self.x_component)

        row = 0

        # Create the list container
        self.x_axis_label = QLabel("Signals:")
        self.selectorLayout.addWidget(self.x_axis_label, row, 0, 1, 1)
        # Clear button
        self.clearButton = QPushButton("Clear")
        self.clearButton.setAutoFillBackground(True)
        self.clearButton.clicked.connect(self.listWidget.clearSignals)
        self.selectorLayout.addWidget(self.clearButton, row, 2, 1, 1)
        # List container
        row += 1
        self.listWidget.changeItem.connect(self.signalWidget.setSignal)
        self.selectorLayout.addWidget(self.listWidget, row, 0, 1, 3)

        # Add the search bar
        row += 1
        self.searchbar = QLineEdit()
        self.searchbar.setPlaceholderText("Search...")
        self.searchbar.textChanged.connect(self.listWidget.set_item_visibility)
        self.searchbar.returnPressed.connect(self.listWidget.select_visible_items)
        self.selectorLayout.addWidget(self.searchbar, row, 0, 1, 3)
        self.completer = QCompleter(list(self.items.keys()))
        self.completer.setCaseSensitivity(Qt.CaseInsensitive)
        self.completer.setCompletionColumn(0)
        self.searchbar.setCompleter(self.completer)

        # Link axis checkbox
        row += 1
        self.linkAxis = QCheckBox("Link Y-axes")
        self.linkAxis.setChecked(True)
        self.linkAxis.toggled.connect(self.signalWidget.setSeparateAxes)
        self.selectorLayout.addWidget(self.linkAxis, row, 0, 1, 3)

        # Create the x_axis selector
        row += 1
        self.x_axis_label = QLabel("X axis:")
        self.selectorLayout.addWidget(self.x_axis_label, row, 0, 1, 1)
        self.x_axis = QComboBox()
        self.x_axis.addItems(self.x_options)
        self.x_axis.setCurrentIndex(self.x_options.index(self.x_component))
        self.x_axis.currentIndexChanged.connect(self.signalWidget.setXAxis)
        self.selectorLayout.addWidget(self.x_axis, row, 1, 1, 2)
        # endregion Selector Widget

        # region Plot Widget
        self.signalWidget.plotItem.vb.sigResized.connect(self.signalWidget.updateViews)

        # self.mainLayout.addLayout(self.signalLayout)
        self.splitter.addWidget(self.signalWidget)

        # Set Strecth factor to give plot the most space
        self.splitter.setStretchFactor(0, 1)
        self.splitter.setStretchFactor(1, 10)

        # tune plots
        self.signalWidget.setBackground((25, 25, 25, 255))  # RGBA         #background
        # self.signalWidget.setTitle("Signal(t)", color="w", size="20pt")  # add title
        # styles = {"color": "r", "font-size": "20px"}  # add label style
        # self.signalWidget.setLabel("left", "signal [SI]", **styles)  # add ylabel
        self.signalWidget.getAxis("left").enableAutoSIPrefix(True)
        # self.signalWidget.setLabel("bottom", "time [s]", **styles)  # add xlabel
        self.signalWidget.getAxis("bottom").enableAutoSIPrefix(True)
        self.signalWidget.showGrid(x=True, y=True)  # add grid
        # Setup clipping and downsampling to reduce CPU usage
        # We expect very large signal data sets, so downsampling is a must
        self.signalWidget.setClipToView(clip=True)
        self.signalWidget.setDownsampling(
            ds=kwargs.get("downsampling", True),
            auto=True,
            mode="subsample",
        )
        self.legend = self.signalWidget.addLegend()  # add grid
        # endregion Plot Widget

        # Connect the sigYRangeChanged signal to the updateViews slot
        # self.signalWidget.plotItem.vb.sigYRangeChanged.connect(self.updateViews)


def plot_window(
    items: dict = None,
    pre_select: list[str] = None,
    x_component: str = None,
    sub_groups: dict[str, list[str]] = None,
    **kwargs,
) -> None:
    """
    Initialize an oscilloscope-like window with the given signals.

    Args:
        items (dict): Dictionary of signals to be displayed. Each key is a signal name and the value is another dict with both "x" and "y" keys, each containing a numpy array with the signal data.
        pre_select (list[str]): List of signal names to be pre-selected.
        x_component (str): Name of the signal to be used as x axis. If None, the first signal will be used.

    Returns:
        None: None
    """

    app = QApplication(sys.argv)

    # Now use a palette to switch to dark colors (personal preference)
    # TODO: Allow the user to set the color palette (or at least switch between dark and light themes)
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
        QLineEdit { color: rgb(255,255,255); background: rgb(25, 25, 25); }
        """
    )

    # Check if the x_component is safe to use
    if x_component is not None:
        if x_component not in items:
            logger.error(f"Selected x_component {x_component} not found in items dict")
            x_component = None

    # Create the main window
    main_window = QMainWindow()
    main_window.setWindowTitle(kwargs.get("title", "Signal plotter"))
    main_window.resize(800, 400)

    ex = PlotWindow(items=items, x_component=x_component, sub_groups=sub_groups, **kwargs)
    main_window.setCentralWidget(ex)

    # Set pre-selected items
    if pre_select is not None:
        ex.listWidget.set_manual_keys(pre_select)

    # Show the window
    main_window.setFocus()
    main_window.show()

    # Run the application and wait for the window to be closed
    app.exec()


if __name__ == "__main__":
    #
    # The following code is a simple example for testing purposes only
    #
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

        items[f"external_signal{i}"] = {
            "x": time,
            "y": x * fun(time) + np.random.normal(scale=s, size=len(time)),
            "units": "A",
        }

    items.update(
        {
            f"external_signal99": {
                "x": time,
                "y": np.random.rand(len(time)) * 100,
                "units": "Nm",
            }
        }
    )

    plot_window(
        items=items,
        pre_select=[
            "group_0.signal_0.subsignal_2",
            "external_signal4",
        ],
        # x_component="group_0.signal_0.subsignal_0",
        sub_groups={
            "even": [signal for signal in items if "." not in signal and int(signal[-1]) % 2 == 0],
            "odd": [signal for signal in items if "." not in signal and int(signal[-1]) % 2 == 1],
        },
        downsampling=False,
    )
