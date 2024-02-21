from __future__ import annotations

import logging
import sys
from typing import NoReturn

import numpy as np
from pyqtgraph import PlotWidget, intColor
from PySide6.QtCore import Qt, Signal, Slot
from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QApplication, QCheckBox, QHBoxLayout, QScrollArea, QSplitter, QVBoxLayout, QWidget

pyqtSignal = Signal
pyqtSlot = Slot


class ListContainer(QScrollArea):
    changeItem = pyqtSignal(list)

    def __init__(self, items: dict = None, parent=None) -> None:
        super(ListContainer, self).__init__(parent)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.setWidgetResizable(True)

        # For each element in items add a "state" flag
        self.listItem = items
        for key, value in self.listItem.items():
            self.listItem[key].setdefault("state", False)

        self.itemChk = []
        self.initUI()

    def set_items(self, items) -> None:
        # Update the list of items and reset the UI
        self.listItem.update(items)
        self.resetUI()

    def initUI(self) -> None:
        self.container = QWidget()
        self.setWidget(self.container)
        self.listLayout = QVBoxLayout(self.container)
        self.resetUI()

    def resetUI(self) -> None:
        # Clear the UI and rebuild it
        self.itemChk = []
        while self.listLayout.count():
            item = self.listLayout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
            else:
                self.listLayout.removeItem(item)

        # Create a checkbox for each item
        for i, (key, value) in enumerate(self.listItem.items()):
            self.itemChk.append(QCheckBox(key))
            self.itemChk[i].setChecked(self.listItem[key]["state"])
            self.itemChk[i].stateChanged.connect(self.changeChk)
            self.listLayout.addWidget(self.itemChk[i])

    def changeChk(self, state):
        logging.debug("{} : {}".format(self.sender().text(), True if state > 0 else False))
        self.listItem[self.sender().text()]["state"] = True if state > 0 else False
        self.changeItem.emit([self.listItem[k]["state"] for k in self.listItem.keys()])


class SignalContainer(QWidget):
    changeParam = pyqtSignal(dict)

    def __init__(self, items: dict = None) -> None:
        super().__init__()
        self.items = items
        self.title = "Signal plotter"

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

        # Create the list container
        self.select = ListContainer(self.items)
        self.select.changeItem.connect(self.setSignal)
        self.splitter.addWidget(self.select)

        self.signalLayout = QVBoxLayout()

        # Create the graph
        self.graphWidget = PlotWidget()
        self.signalLayout.addWidget(self.graphWidget)
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

    @pyqtSlot(list)
    def setSignal(self, states) -> None:
        self.sigstate = states

        # update graph
        self.graphWidget.clear()
        # self.graphWidget.plot(self.time, self.data,name = "signal",pen=self.pen,symbol='+', symbolSize=5, symbolBrush='w')
        j = 0
        for i, (key, data) in enumerate(self.items.items()):
            if self.sigstate[i]:  # display signal
                self.graphWidget.plot(data["x"], data["y"], name=key, pen=intColor(j))
                j += 1


def main(items: dict = None) -> NoReturn:
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
    palette.setColor(QPalette.HighlightedText, Qt.black)
    app.setPalette(palette)

    ex = SignalContainer(items=items)
    ex.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    # Generate random data
    items = {}
    time = np.linspace(0, 1, 1000) * 10
    for i in range(20):
        x = np.random.choice([-1, 1])  # random sign
        s = np.random.rand() * 0.2  # random scale
        fun = np.random.choice([np.sin, np.cos])  # random function

        items["signal{}".format(i)] = {
            "x": time,
            "y": x * fun(time) + np.random.normal(scale=s, size=len(time)),
        }

    main(items=items)
