import sys
import time
import logging
import re
import operator
import numpy as np
import csv
import os

from PyQt5 import QtCore
from PyQt5.QtCore import QRect
from PyQt5.QtCore import Qt
from PyQt5.QtCore import (
    QObject,
    QThreadPool, 
    QRunnable, 
    pyqtSignal,
    Qt, 
    QTimer,
    pyqtSlot
)

from PyQt5.QtWidgets import (
    QApplication,
    QGridLayout,
    QMainWindow,
    QPushButton,
    QComboBox,
    QHBoxLayout,
    QVBoxLayout,
    QWidget,
    QLabel,
    QInputDialog,
    QFrame,
    QSplitter,
    QLineEdit
)

from PyQt5.QtGui import (
    QFont,
    QPixmap
)

import serial
import serial.tools.list_ports
import pyqtgraph as pg
from pyqtgraph import PlotWidget

###############
# User Interface #
###############

from PyQt5.QtWidgets import QApplication, QMainWindow, QLabel, QHBoxLayout, QVBoxLayout, QWidget, QFrame, QSpacerItem, QSizePolicy
from PyQt5.QtGui import QFont, QPixmap
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPolygon

class UserInterface(QMainWindow):

    def __init__(self):
        super().__init__()

        self.setWindowTitle("User Interface1")
        self.setMinimumSize(800, 600)
        self.threadpool = QThreadPool()
        self.initUI()
        self.is_calibrating = False
    
    def initUI(self):

        self.check_cal = True
        self.NEXT_STEP = False
        
        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)

        self.main_layout = QVBoxLayout(central_widget)
        self.main_layout.setAlignment(Qt.AlignTop | Qt.AlignHCenter)

        #calibration step
        self.cal_title = QLabel("CALIBRATION STEP", self)
        font = QFont('Arial', 25)
        font.setBold(True)
        self.cal_title.setFont(font)
        self.cal_title.setAlignment(Qt.AlignCenter)
        self.main_layout.addWidget(self.cal_title)
        
        #scritta
        scritta_layout1 = QHBoxLayout()
        self.main_layout.addLayout(scritta_layout1)

        self.scritta1 = QLabel("When you are ready,  click on the 'Calibration' button to carry out the calibration.\n      Remember to remain still,  without making any facial expressions!", self)
        self.scritta1.setFont(QFont('Arial', 17))
        self.scritta1.setAlignment(Qt.AlignCenter)
        scritta_layout1.addWidget(self.scritta1)
        
        #pulsante calibrazione
        button_layout = QVBoxLayout()
        self.main_layout.addLayout(button_layout)

        self.calibration_button = QPushButton("Calibration",self)
        self.calibration_button.setFont(QFont('Arial',20))
        self.calibration_button.setStyleSheet("color: red;")
        self.calibration_button.setFixedSize(500,50)
        button_layout.addWidget(self.calibration_button)
        button_layout.setAlignment(Qt.AlignCenter)
        self.calibration_button.clicked.connect(self.start_actn_cal)

        #linea divisoria
        line = QVBoxLayout()
        self.main_layout.addLayout(line)

        self.sep_line_cal = QLabel("_______________________________________________________________________________________________________________________________________________________________________________________________________", self)
        line.addWidget(self.sep_line_cal)
        self.sep_line_cal.setAlignment(Qt.AlignCenter)

        #scritta
        scritta_layout2 = QHBoxLayout()
        self.main_layout.addLayout(scritta_layout2)
        self.scritta2 = QLabel("Stand still for 5 seconds! We are calibrating the data...")
        self.scritta2.setFont(QFont('Arial', 17))
        self.scritta2.setAlignment(Qt.AlignCenter)
        scritta_layout2.addWidget(self.scritta2)


        box_layout = QHBoxLayout()
        self.main_layout.addLayout(box_layout)
        # Layout orizzontale per le immagini
        image_layout= QHBoxLayout()
        box_layout.addLayout(image_layout)

        #immagine attesa
        self.image = QLabel(self)
        self.pixmap = QPixmap("attesa2.png")
        scaled_pixmap = self.pixmap.scaled(150, 150, Qt.AspectRatioMode.KeepAspectRatio)
        self.image.setPixmap(scaled_pixmap)
        image_layout.addWidget(self.image)

        spacer_item = QSpacerItem(200, 200)
        image_layout.addItem(spacer_item)

        timer_button_layout = QHBoxLayout()
        box_layout.addLayout(timer_button_layout)

        #box
        self.cal_box = QLabel("", self) 
        self.cal_box.setStyleSheet("border: 3px solid black; font-size: 48px; color: red") 
        self.cal_box.setFixedSize(300, 150) 
        self.cal_box.setAlignment(Qt.AlignCenter) 
        box_layout.addWidget(self.cal_box)
        box_layout.setAlignment(Qt.AlignCenter)
        timer_button_layout.addWidget(self.cal_box)
        

        spacer_item = QSpacerItem(200, 200)
        timer_button_layout.addItem(spacer_item)



        #next botton
        self.next_button = QPushButton("Next Step", self)
        self.next_button.setFont(QFont('Arial', 14))
        timer_button_layout.addWidget(self.next_button)
        self.next_button.clicked.connect(self.hideElements)

        # legend
        legend_layout = QHBoxLayout()
        self.main_layout.addLayout(legend_layout)
        self.legend_label = QLabel("LEGEND:", self)
        font = QFont('Arial', 14)
        font.setBold(True)
        self.legend_label.setFont(font)
        self.legend_label.setAlignment(Qt.AlignRight)
        self.legend_label.hide()
        legend_layout.addWidget(self.legend_label)

        spacer_item = QSpacerItem(180, 0)
        legend_layout.addItem(spacer_item)

        image_legend_layout = QHBoxLayout()
        self.main_layout.addLayout(image_legend_layout)
        self.image_l = QLabel(self)
        self.pixmap = QPixmap("legend.jpeg")
        scaled_pixmap = self.pixmap.scaled(500, 500, Qt.AspectRatioMode.KeepAspectRatio)
        self.image_l.setPixmap(scaled_pixmap)
        self.image_l.setAlignment(Qt.AlignRight)
        self.image_l.hide()
        image_legend_layout.addWidget(self.image_l)

        #scritta
        scritta_layout3 = QHBoxLayout()
        self.main_layout.addLayout(scritta_layout3)
        self.scritta3 = QLabel("As soon as the timer is over, press the 'next step' button to move forward with the service request")
        self.scritta3.setFont(QFont('Arial', 17))
        self.scritta3.setAlignment(Qt.AlignCenter)
        scritta_layout3.addWidget(self.scritta3)

        self.main_layout.addStretch()









    def updateCountdownCal(self):
        if self.is_calibrating:
            if self.counter > 0:
                self.cal_box.setText(str(self.counter))
                self.counter -= 1
            else:
                self.timer.stop()
                self.cal_box.setText("Done!")
                self.NEXT_STEP = True
                self.is_calibrating = False

    def start_actn_cal(self):  
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.updateCountdownCal)
        self.counter = 5
        self.timer.start(1000)
        self.is_calibrating = True 




    def hideElements(self):
        if self.NEXT_STEP == True:
            self.cal_box.setText("")
        self.cal_title.setText("REQUEST STEP")
        self.scritta1.setText("Now you are ready to submit the request! Click on the 'Send Request' button,\nremembering to keep the facial expression corresponding to the request you wish to make:")
        self.calibration_button.setText("Send Request")
        self.scritta2.setText("Stay with the facial expression you want to communicate for 5 seconds! \nwe are analyzing your request...")
        self.pixmap = QPixmap("attesa2.png")
        self.next_button.setText("Restart")
        self.scritta3.hide()
        self.legend_label.show()
        self.image_l.show()

        




#run
if __name__ == '__main__':
    app = QApplication([])
    window = UserInterface()
    window.show()
    app.exec_()
