import time
import logging
import numpy as np
import pickle
from scipy import stats
import pandas as pd
import serial
import serial.tools.list_ports
import pyqtgraph as pg
from pyqtgraph import PlotWidget

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
    QMainWindow,
    QPushButton,
    QComboBox,
    QHBoxLayout,
    QVBoxLayout,
    QWidget,
    QLabel,
    QSpacerItem,
    QWidget
)

from PyQt5.QtGui import (
    QFont,
    QPixmap
)

# Globals
CONN_STATUS = False
KILL        = False
CALIBRATION = False
UPDATE      = False
PREDICTION  = False
RESTART     = False

#########################
# SERIAL_WORKER_SIGNALS #
#########################
class SerialWorkerSignals(QObject):

    device_port = pyqtSignal(str)
    status = pyqtSignal(str, int)
    data_ready = pyqtSignal(list, list, list, list, list)
    calibration = pyqtSignal(float, float, float, float)
    prediction = pyqtSignal(float, float, float, float)

#################
# SERIAL_WORKER #
#################
class SerialWorker(QRunnable):
    
    def __init__(self, serial_port_name):

        super().__init__()

        self.time = []
        self.cap1 = []
        self.cap2 = []
        self.cap3 = []
        self.cap4 = []

        self.port = serial.Serial()
        self.port_name = serial_port_name
        self.baudrate = 9600
        self.signals = SerialWorkerSignals()

    @pyqtSlot()
    def run(self):

        global CONN_STATUS
        global UPDATE
        global CALIBRATION
        global RESTART

        if not CONN_STATUS:
            try:
                self.port = serial.Serial(port=self.port_name, baudrate=self.baudrate,
                                        write_timeout=0, timeout=0.1)                
                if self.port.is_open:
                    CONN_STATUS = True
                    status_check = 0
                    self.timer_count = 0
                    update_plot = False
                    capacitance_values =  []
                    self.signals.status.emit(self.port_name, 1)

                    while True:
                        if status_check == 0:
                            print('\n')
                            flag = self.port.read_until(b'\n').decode()
                            if flag == 'SOS\n':
                                status_check = 1
                        if status_check == 1:
                            capacitance = self.port.read_until(b'EOS\n').decode().split()
                            capacitance_values.append(capacitance)
                            capacitance_values = [j.replace('\n', '') for j in capacitance]
                            capacitance_values = capacitance_values[:-1] 
                            newcap1 = capacitance_values[0]
                            newcap1 = float(newcap1)
                            print(newcap1)
                            newcap2 = capacitance_values[1]
                            newcap2 = float(newcap2)
                            print(newcap2)
                            newcap3 = capacitance_values[2]
                            newcap3 = float(newcap3)
                            print(newcap3)
                            newcap4 = capacitance_values[3]
                            newcap4 = float(newcap4)
                            print(newcap4)         
                            status_check = 0

                            self.time.append(self.timer_count*0.1)
                            self.timer_count = self.timer_count + 1
                            self.cap1.append(newcap1)
                            self.cap2.append(newcap2)
                            self.cap3.append(newcap3)
                            self.cap4.append(newcap4)
                            
                            if CALIBRATION == True:
                                self.signals.calibration.emit(newcap1, newcap2, newcap3, newcap4)
                            
                            if PREDICTION == True:
                                self.signals.prediction.emit(newcap1, newcap2, newcap3, newcap4)

                            if UPDATE == True: 
                                self.signals.data_ready.emit(self.time, self.cap1, self.cap2, self.cap3, self.cap4)

                        if len(self.time) == 50:
                            update_plot = True
                        
                        if update_plot == True:
                            self.time = self.time[1:]
                            self.cap1 = self.cap1[1:]
                            self.cap2 = self.cap2[1:]
                            self.cap3 = self.cap3[1:]
                            self.cap4 = self.cap4[1:]
                            update_plot = False
                            if UPDATE == True:
                                self.signals.data_ready.emit(self.time, self.cap1, self.cap2, self.cap3, self.cap4)

            except serial.SerialException:
                logging.info("Error with port {}.".format(self.port_name))
                self.signals.status.emit(self.port_name, 0)
                time.sleep(0.01)

    @pyqtSlot()
    def send(self, char):
        """!
        @brief Basic function to send a single char on serial port.
        """
        try:
            self.port.write(char.encode('utf-8'))
            logging.info("Written {} on port {}.".format(char, self.port_name))
        except:
            logging.info("Could not write {} on port {}.".format(char, self.port_name))

    @pyqtSlot()
    def killed(self):
        """!
        @brief Close the serial port before closing the app.
        """
        global CONN_STATUS
        global KILL

        if KILL and CONN_STATUS:
            self.port.close()
            time.sleep(0.01)
            CONN_STATUS = False
            self.signals.device_port.emit(self.port_name)
            
        KILL = False
        logging.info("Process killed")

###############
# User Interface #
###############
class UserInterface(QMainWindow):

    def __init__(self):
        super(UserInterface, self).__init__()

        self.serial_worker = SerialWorker(None)

        self.local_time = []
        self.cap1 = []
        self.cap2 = []
        self.cap3 = []
        self.cap4 = []
        
        self.cap1fullcal = []
        self.cap2fullcal = []
        self.cap3fullcal = []
        self.cap4fullcal = []
        self.i = 0

        self.cap1fullprediction = []
        self.cap2fullprediction = []
        self.cap3fullprediction = []
        self.cap4fullprediction = []
        self.j = 0

        self.dict_output = {
            0: 'PAIN WARNING',
            1: 'ASSISTENCE REQUEST',
            2: 'TOO COLD',
            3: 'TOO HOT',
            4: 'HUNGER WARMING',
            }

        self.meancal1 = 0
        self.meancal2 = 0
        self.meancal3 = 0
        self.meancal4 = 0

        self.cal_start = False
        self.cal_finished = False
        self.pred_start = False
        self.pred_finished = False
        self.NEXT_STEP = False

        self.setWindowTitle("User Interface1")
        self.setMinimumSize(800, 600)
        self.threadpool = QThreadPool()
        self.connected = CONN_STATUS
        self.serialscan()
        self.initUI()
    
    def initUI(self):
 
        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)

        button_conn = QVBoxLayout()
        button_conn.addWidget(self.com_list_widget)
        button_conn.addWidget(self.conn_btn)  

        self.main_layout = QVBoxLayout(central_widget)
        self.main_layout.setAlignment(Qt.AlignTop | Qt.AlignHCenter)

        self.main_layout.addLayout(button_conn)

        central_widget.setLayout(self.main_layout)

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
        self.calibration_button.clicked.connect(self.start_actn)

        #linea divisoria
        line = QVBoxLayout()
        self.main_layout.addLayout(line)

        self.sep_line_cal = QLabel("______________________________________________________________________________________________________________________________________________________________________________________________________________________________________________________", self)
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
        self.cal_box.setStyleSheet("border: 3px solid black; font-size: 30px; color: red") 
        self.cal_box.setFixedSize(600, 150)
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

        self.image_legend_layout = QHBoxLayout()
        self.main_layout.addLayout(self.image_legend_layout)

        self.graphWidget = PlotWidget()
        self.graphWidget.showGrid(x=True, y=True)
        self.graphWidget.setBackground('white')
        self.graphWidget.setTitle("Capacitance measurement [pF]")
        styles = {'color':'k', 'font-size':'15px'}
        self.graphWidget.setLabel('left', 'Capacity', **styles)
        self.graphWidget.setLabel('bottom', 'Time [s]', **styles)
        self.graphWidget.addLegend()
        self.image_legend_layout.addWidget(self.graphWidget)

        self.image_l = QLabel(self)
        self.pixmap_l = QPixmap("legend.jpeg")
        scaled_pixmap_l = self.pixmap_l.scaled(500, 500, Qt.AspectRatioMode.KeepAspectRatio)
        self.image_l.setPixmap(scaled_pixmap_l)
        self.image_l.setAlignment(Qt.AlignRight)
        self.image_l.hide()
        self.image_legend_layout.addWidget(self.image_l)
        self.draw()
        self.main_layout.addStretch()

    def updateCountdownCal(self):
        if self.counter > 0:
            self.cal_box.setText(str(self.counter / 10) + " s")
            self.counter -= 1
        else:
            self.timer.stop()
            self.NEXT_STEP = True
            self.cal_start = True
            self.pred_start = True
            self.cal_box.setText("Done!")

    def updateCountdownReq(self):
        if self.counter > 0:
            self.cal_box.setText(str(self.counter / 10) + " s")
            self.counter -= 1
        else:
            self.timer.stop()
            self.cal_box.setText(str(self.dict_output[self.prediction_value[0]]) + "\nIf the request is wrong,\nclick on the 'Restart' button\nand repeat the calibration.")
            self.pred_finished = True

    def start_actn(self):  
        global CALIBRATION
        global PREDICTION

        if self.cal_start == False:
            self.timer = QTimer(self)
            self.timer.timeout.connect(self.updateCountdownCal)
            self.counter = 50
            self.timer.start(100)
        if CALIBRATION == False:
            CALIBRATION = True
            self.i = 0
        if self.pred_start == True:
            self.timer = QTimer(self)
            self.timer.timeout.connect(self.updateCountdownReq)
            self.counter = 50
            self.timer.start(100)
            PREDICTION = True
            self.j = 0
    
    def calibration(self, cap1, cap2, cap3, cap4):

        global CALIBRATION
        
        if CALIBRATION == True:
            if self.i < 50:
                self.cap1fullcal.append(cap1)
                self.cap2fullcal.append(cap2)
                self.cap3fullcal.append(cap3)
                self.cap4fullcal.append(cap4)
                self.i = self.i + 1
            if self.i >= 50:
                CALIBRATION = False
                self.meancal1 = np.round((np.array(self.cap1fullcal)).mean(), decimals=2)
                self.meancal2 = np.round((np.array(self.cap2fullcal)).mean(), decimals=2)
                self.meancal3 = np.round((np.array(self.cap3fullcal)).mean(), decimals=2)
                self.meancal4 = np.round((np.array(self.cap4fullcal)).mean(), decimals=2)
                self.cap1fullcal = []
                self.cap2fullcal = []
                self.cap3fullcal = []
                self.cap4fullcal = []

    def prediction(self, cap1, cap2, cap3, cap4):
        
        global PREDICTION
        
        with open('mlp_1.pkl', 'rb') as file:
            model_mlp = pickle.load(file)

        if self.j < 50:
            self.cap1fullprediction.append(cap1 - self.meancal1)
            self.cap2fullprediction.append(cap2 - self.meancal2)
            self.cap3fullprediction.append(cap3 - self.meancal3)
            self.cap4fullprediction.append(cap4 - self.meancal4)
            self.j = self.j + 1
        if self.j >= 50:
            print("PREDICTION FINITA")
            PREDICTION = False
            array_cap2 = np.array(self.cap2fullprediction)
            mean_left = array_cap2.mean()
            var_left = array_cap2.var()
            mode_left = stats.mode(array_cap2, axis=None, keepdims=True)
            mode_value_left = mode_left.mode[0]
            max_left = array_cap2.max()
            min_left = array_cap2.min()

            array_cap3 = np.array(self.cap3fullprediction)
            mean_center = array_cap3.mean()
            var_center = array_cap3.var()
            mode_center = stats.mode(array_cap3, axis=None, keepdims=True)
            mode_value_center = mode_center.mode[0]
            max_center = array_cap3.max()
            min_center = array_cap3.min()

            array_cap4 = np.array(self.cap4fullprediction)
            mean_eyebrow = array_cap4.mean()
            var_eyebrow = array_cap4.var()
            mode_eyebrow = stats.mode(array_cap4, axis=None, keepdims=True)
            mode_value_eyebrow = mode_eyebrow.mode[0]
            max_eyebrow = array_cap4.max()
            min_eyebrow = array_cap4.min()

            array_cap1 = np.array(self.cap1fullprediction)
            mean_right = array_cap1.mean()
            var_right = array_cap1.var()
            mode_right = stats.mode(array_cap1, axis=None, keepdims=True)
            mode_value_right = mode_right.mode[0]
            max_right = array_cap1.max()
            min_right = array_cap1.min()

            self.cap1fullprediction = []
            self.cap2fullprediction = []
            self.cap3fullprediction = []
            self.cap4fullprediction = []

            df = pd.DataFrame({
                'Mean_Left': [mean_left],
                'Var_Left': [var_left],
                'Mode_Left': [mode_value_left],
                'Max_Left': [max_left],
                'Min_Left': [min_left],
                'Mean_Center': [mean_center],
                'Var_Center': [var_center],
                'Mode_Center': [mode_value_center],
                'Max_Center': [max_center],
                'Min_Center': [min_center],
                'Mean_Right': [mean_right],
                'Var_Right': [var_right],
                'Mode_Right': [mode_value_right],
                'Max_Right': [max_right],
                'Min_Right': [min_right],
                'Mean_Eyebrow': [mean_eyebrow],
                'Var_Eyebrow': [var_eyebrow],
                'Mode_Eyebrow': [mode_value_eyebrow],
                'Max_Eyebrow': [max_eyebrow],
                'Min_Eyebrow': [min_eyebrow],
            })

            self.prediction_value = model_mlp.predict(df)

    def hideElements(self):
        global UPDATE
        global RESTART

        if self.pred_finished == False:
            if self.NEXT_STEP == True:
                self.cal_box.setText("")
            self.cal_title.setText("REQUEST STEP")
            self.scritta1.setText("Now you are ready to submit the request! Click on the 'Send Request' button,\nremember to keep the facial expression corresponding to the request you wish to make:")
            self.calibration_button.setText("Send Request")
            self.scritta2.setText("Stay with the facial expression you want to communicate for 5 seconds! \nWe are analyzing your request...")
            self.pixmap = QPixmap("attesa2.png")
            self.next_button.setText("Restart")
            self.legend_label.show()
            self.image_l.show()
            UPDATE = True
        else:
            RESTART = True
            self.initUI()
            self.reset_values()
    
    def reset_values(self):
        global UPDATE
        global RESTART

        RESTART             = False
        UPDATE              = False
        self.cal_start      = False
        self.cal_finished   = False
        self.pred_start     = False
        self.pred_finished  = False
        self.NEXT_STEP      = False
        self.pred_finished  = False

        self.graphWidget.clear()
        self.draw()

        self.local_time = []
        self.cap1 = []
        self.cap2 = []
        self.cap3 = []
        self.cap4 = []
        
        self.cap1fullcal = []
        self.cap2fullcal = []
        self.cap3fullcal = []
        self.cap4fullcal = []
        self.i = 0

        self.cap1fullprediction = []
        self.cap2fullprediction = []
        self.cap3fullprediction = []
        self.cap4fullprediction = []
        self.j = 0

        self.meancal1 = 0
        self.meancal2 = 0
        self.meancal3 = 0
        self.meancal4 = 0
    
        self.cap1line.setData(x=self.local_time, y=self.cap1)
        self.cap2line.setData(x=self.local_time, y=self.cap2)
        self.cap3line.setData(x=self.local_time, y=self.cap3)
        self.cap4line.setData(x=self.local_time, y=self.cap4)

    def draw(self):

        self.cap1line = self.plot(self.graphWidget, self.local_time, self.cap1, 'Right', 'black')
        self.cap2line = self.plot(self.graphWidget, self.local_time, self.cap2, 'Left', 'blue')
        self.cap3line = self.plot(self.graphWidget, self.local_time, self.cap3, 'Center', 'red')
        self.cap4line = self.plot(self.graphWidget, self.local_time, self.cap4, 'Eyebrow', 'green') 
        
    def plot(self, graph, x, y, curve_name, color):

        pen = pg.mkPen(color=color)
        line = graph.plot(x, y, name=curve_name, pen=pen)
        graph.getViewBox().setYRange(-0.3, 0.6)
        return line
    
    def add_data(self, time, cap1, cap2, cap3, cap4):

        self.local_time = time
        self.cap1 = cap1 - self.meancal1
        self.cap2 = cap2 - self.meancal2
        self.cap3 = cap3 - self.meancal3
        self.cap4 = cap4 - self.meancal4

        self.cap1line.setData(x=self.local_time, y=self.cap1)
        self.cap2line.setData(x=self.local_time, y=self.cap2)
        self.cap3line.setData(x=self.local_time, y=self.cap3)
        self.cap4line.setData(x=self.local_time, y=self.cap4)

    ####################
    # SERIAL INTERFACE #
    ####################
    def serialscan(self):
        """!
        @brief Scans all serial ports and create a list.
        """
        # Create the combo box to host port list
        self.port_text = ""
        self.com_list_widget = QComboBox()
        self.com_list_widget.currentTextChanged.connect(self.port_changed)
        
        # Create the connection button
        self.conn_btn = QPushButton(
            text=("Connect to port {}".format(self.port_text)), 
            checkable=True,
            toggled=self.on_toggle      
        )
        # Acquire list of serial ports and add it to the combo box
        serial_ports = [
                p.name
                for p in serial.tools.list_ports.comports()
            ]
        self.com_list_widget.addItems(serial_ports)

    ##################
    # SERIAL SIGNALS #
    ##################
    def port_changed(self):
        """!
        @brief Update conn_btn label based on selected port.
        """
        self.port_text = self.com_list_widget.currentText()
        self.conn_btn.setText("Connect to port {}".format(self.port_text))

    @pyqtSlot(bool)
    def on_toggle(self, checked):
        """!
        @brief Allow connection and disconnection from selected serial port.
        """
        if checked:
            # setup reading worker
            self.serial_worker = SerialWorker(self.port_text) # needs to be re defined
            # connect worker signals to functions
            self.serial_worker.signals.status.connect(self.check_serialport_status)
            self.serial_worker.signals.device_port.connect(self.connected_device)
            self.serial_worker.signals.data_ready.connect(self.add_data)
            self.serial_worker.signals.calibration.connect(self.calibration)
            self.serial_worker.signals.prediction.connect(self.prediction)
            # execute the worker
            self.threadpool.start(self.serial_worker)
        else:
            global KILL
            KILL = True
            self.serial_worker.killed()
            self.com_list_widget.setDisabled(False) # enable the possibility to change port
            self.conn_btn.setText(
                "Connect to port {}".format(self.port_text)
            )

    def check_serialport_status(self, port_name, status):
        """!
        @brief Handle the status of the serial port connection.
        Available status:
            - 0  --> Error during opening of serial port
            - 1  --> Serial port opened correctly
        """
        if status == 0:
            self.conn_btn.setChecked(False)
        elif status == 1:
            # enable all the widgets on the interface
            self.com_list_widget.setDisabled(True) # disable the possibility to change COM port when already connected
            self.conn_btn.setText(
                "Disconnect from port {}".format(port_name)
            )
            logging.info("Connected to port {}".format(port_name))

    def connected_device(self, port_name):
        """!
        @brief Checks on the termination of the serial worker.
        """
        logging.info("Port {} closed.".format(port_name))

    def ExitHandler(self):
        """!
        @brief Kill every possible running thread upon exiting application.
        """
        global KILL
        KILL = True
        self.serial_worker.killed()

#run
if __name__ == '__main__':
    app = QApplication([])
    window = UserInterface()
    app.aboutToQuit.connect(window.ExitHandler)
    window.show()
    app.exec_()