import sys
import time
import logging
import numpy as np
import pickle  
from scipy import stats
import csv
import pandas as pd
import os

from PyQt5 import QtCore
from PyQt5.QtCore import (
    QObject,
    QThreadPool, 
    QRunnable, 
    pyqtSignal, 
    pyqtSlot
)

from PyQt5.QtWidgets import (
    QApplication,
    QMainWindow,
    QPushButton,
    QComboBox,
    QHBoxLayout,
    QVBoxLayout,
    QWidget
)
 
import serial
import serial.tools.list_ports
import pyqtgraph as pg
from pyqtgraph import PlotWidget

# Globals
CONN_STATUS = False
SAMPLE      = False
KILL        = False
CALIBRATION = False
SAVE        = False
UPDATE      = False
PREDICTION = False

MEAN1CAL = 0
MEAN2CAL = 0
MEAN3CAL = 0
MEAN4CAL = 0

#########################
# SERIAL_WORKER_SIGNALS #
#########################
class SerialWorkerSignals(QObject):

    device_port = pyqtSignal(str)
    status = pyqtSignal(str, int)
    data_ready = pyqtSignal(list, list, list, list, list)
    calibration = pyqtSignal(float, float, float, float)
    prediction = pyqtSignal(float, float, float, float)
    sample = pyqtSignal(float, float, float, float)
    save = pyqtSignal()

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
        global SAMPLE
        global UPDATE
        global CALIBRATION
        global SAVE
        global PREDICTION

        if not CONN_STATUS:
            try:
                self.port = serial.Serial(port=self.port_name, baudrate=self.baudrate,
                                        write_timeout=0, timeout=0.1)                
                if self.port.is_open:
                    CONN_STATUS = True
                    status_check = 0
                    timer_count = 0
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

                            self.time.append(timer_count*0.1)
                            timer_count = timer_count + 1
                            self.cap1.append(newcap1)
                            self.cap2.append(newcap2)
                            self.cap3.append(newcap3)
                            self.cap4.append(newcap4)

                            if UPDATE == True:
                                self.signals.data_ready.emit(self.time, self.cap1, self.cap2, self.cap3, self.cap4)
                            if CALIBRATION == True:
                                self.signals.calibration.emit(newcap1, newcap2, newcap3, newcap4)
                            if SAMPLE == True:
                                self.signals.sample.emit(newcap1, newcap2, newcap3, newcap4)
                            if SAVE == True:
                                self.signals.save.emit()
                            if PREDICTION == True:
                                self.signals.prediction.emit(newcap1, newcap2, newcap3, newcap4)
               

                        if len(self.time) == 50:
                            update_plot = True

                        if update_plot == True:
                            self.time = self.time[1:]
                            self.cap1 = self.cap1[1:]
                            self.cap2 = self.cap2[1:]
                            self.cap3 = self.cap3[1:]
                            self.cap4 = self.cap4[1:]
                            update_plot = False
 
                            #Line to constantly update data in the graph with every new acquisition
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
# MAIN WINDOW #
###############
class MainWindow(QMainWindow): 
    def __init__(self):

        super(MainWindow, self).__init__() 

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

        self.cap1fullsample = []
        self.cap2fullsample = []
        self.cap3fullsample = []
        self.cap4fullsample = []
        self.j = 0

        self.cap1fullprediction = []
        self.cap2fullprediction = []
        self.cap3fullprediction = []
        self.cap4fullprediction = []
        self.k = 0
        
        self.dict_output = {
            0: 'Angry',
            1: 'Default',
            2: 'Head-down',
            3: 'Head-up',
            4: 'Smile'
            }
        

        self.setWindowTitle("GUI")
        width = 200
        height = 160
        self.setMinimumSize(width, height)
        self.threadpool = QThreadPool()
        self.connected = CONN_STATUS
        self.serialscan()
        self.initUI()

    #####################
    # GRAPHIC INTERFACE #
    #####################
    def initUI(self):

        self.graphWidget = PlotWidget()    

        self.sample_btn = QPushButton(
            text="Sample",
            clicked=self.trigger_sample
        )
        self.add_btn = QPushButton(
            text="Add data",
            clicked=self.trigger_data
        )
        self.save_btn = QPushButton(
            text="Save data",
            clicked=self.trigger_save
        )
        self.calibration_btn = QPushButton(
            text="Calibration",
            clicked=self.trigger_calibration
        )
        self.prediction_btn = QPushButton(
            text="Prediction",
            clicked=self.trigger_prediction
        )

        # Layout
        button_conn = QHBoxLayout()
        button_conn.addWidget(self.com_list_widget)
        button_conn.addWidget(self.conn_btn)
        button_hlay = QHBoxLayout()
        button_hlay.addWidget(self.add_btn)
        button_hlay.addWidget(self.sample_btn)
        button_hlay.addWidget(self.save_btn)
        button_hlay.addWidget(self.calibration_btn)
        button_hlay.addWidget(self.prediction_btn)
        vlay = QVBoxLayout()
        vlay.addLayout(button_conn)
        vlay.addLayout(button_hlay)
        vlay.addWidget(self.graphWidget)
        widget = QWidget()
        widget.setLayout(vlay)
        self.setCentralWidget(widget)

        # Plot settings
        self.graphWidget.showGrid(x=True, y=True)
        self.graphWidget.setBackground('k')
        self.graphWidget.setTitle("Capacitance measurement [pF]")
        styles = {'color':'k', 'font-size':'15px'}
        self.graphWidget.setLabel('left', 'Capacity', **styles)
        self.graphWidget.setLabel('bottom', 'Time [s]', **styles)
        self.graphWidget.addLegend()
        self.draw()

    def trigger_data(self):
        global UPDATE
        if UPDATE == False:
            UPDATE = True   

    def trigger_calibration(self):
        global CALIBRATION
        if CALIBRATION == False:
            CALIBRATION = True
            self.cap1fullcal = []
            self.cap2fullcal = []
            self.cap3fullcal = []
            self.cap4fullcal = []
            self.i = 0
    
    def trigger_sample(self):
        global SAMPLE
        if SAMPLE == False:
            SAMPLE = True
            self.j = 0

    def trigger_save(self):
        global SAVE
        if SAVE == False:
            SAVE = True

    
    def trigger_prediction(self):
        global PREDICTION
        if PREDICTION == False:
            PREDICTION = True
            self.cap1fullprediction = []
            self.cap2fullprediction = []
            self.cap3fullprediction = []
            self.cap4fullprediction = []
            self.k = 0

    def calibration(self, cap1, cap2, cap3, cap4):

        global CALIBRATION
        global MEAN1CAL
        global MEAN2CAL
        global MEAN3CAL
        global MEAN4CAL
        
        if CALIBRATION == True:
            if self.i < 50:
                self.cap1fullcal.append(cap1)
                self.cap2fullcal.append(cap2)
                self.cap3fullcal.append(cap3)
                self.cap4fullcal.append(cap4)
                self.i = self.i + 1
                print(self.i)
            if self.i >= 50:
                print("CALIBRATION DONE")
                CALIBRATION = False
                MEAN1CAL = np.round((np.array(self.cap1fullcal)).mean(), decimals=2)
                MEAN2CAL = np.round((np.array(self.cap2fullcal)).mean(), decimals=2)
                MEAN3CAL = np.round((np.array(self.cap3fullcal)).mean(), decimals=2)
                MEAN4CAL = np.round((np.array(self.cap4fullcal)).mean(), decimals=2)
                print(MEAN1CAL)

    def prediction(self, cap1, cap2, cap3, cap4):
        
        global PREDICTION
        global MEAN1CAL
        global MEAN2CAL
        global MEAN3CAL
        global MEAN4CAL
        
        with open('test_mlp_1.pkl', 'rb') as file:
            model_mlp = pickle.load(file) 

        if self.k < 50:
            self.cap1fullprediction.append(cap1 - MEAN1CAL)
            self.cap2fullprediction.append(cap2 - MEAN2CAL)
            self.cap3fullprediction.append(cap3 - MEAN3CAL)
            self.cap4fullprediction.append(cap4 - MEAN4CAL)
            self.k = self.k + 1
        if self.k >= 50:
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
                'Min_Eyebrow': [min_eyebrow]
            })

            prediction = model_mlp.predict(df)
            predicted_target = self.dict_output[prediction[0]]
            print("MLP:")
            print(predicted_target)
            print("********************************") 


    def draw(self):

        self.cap1line = self.plot(self.graphWidget, self.local_time, self.cap1, 'Right', 'r')
        self.cap2line = self.plot(self.graphWidget, self.local_time, self.cap2, 'Left', 'c')
        self.cap3line = self.plot(self.graphWidget, self.local_time, self.cap3, 'Center', 'y')
        self.cap4line = self.plot(self.graphWidget, self.local_time, self.cap4, 'Eyebrow', 'w')
   
    def plot(self, graph, x, y, curve_name, color):

        pen = pg.mkPen(color=color)
        line = graph.plot(x, y, name=curve_name, pen=pen)
        graph.getViewBox().setYRange(-0.3, 0.6)
        return line
        
    def add_data(self, time, cap1, cap2, cap3, cap4):

        global MEAN1CAL
        global MEAN2CAL
        global MEAN3CAL
        global MEAN4CAL
        global UPDATE

        self.local_time = time
        self.cap1 = cap1 - MEAN1CAL
        self.cap2 = cap2 - MEAN2CAL
        self.cap3 = cap3 - MEAN3CAL
        self.cap4 = cap4 - MEAN4CAL

        self.cap1line.setData(x=self.local_time, y=self.cap1)
        self.cap2line.setData(x=self.local_time, y=self.cap2)
        self.cap3line.setData(x=self.local_time, y=self.cap3)
        self.cap4line.setData(x=self.local_time, y=self.cap4)

    def sample(self, cap1, cap2, cap3, cap4):
        
        global MEAN1CAL
        global MEAN2CAL
        global MEAN3CAL
        global MEAN4CAL
        global SAMPLE

        if SAMPLE == True:
            if MEAN1CAL == 0 or MEAN2CAL == 0 or MEAN3CAL == 0 or MEAN4CAL == 0:
                print("Error! Remember to do the calibration first!\nClick on the 'Restart' button to repeat the proceeding")
                SAMPLE = False
            else:
                if self.j < 50:
                    self.cap1fullsample.append(cap1 - MEAN1CAL)
                    self.cap2fullsample.append(cap2 - MEAN2CAL)
                    self.cap3fullsample.append(cap3 - MEAN3CAL)
                    self.cap4fullsample.append(cap4 - MEAN4CAL)
                    self.j = self.j + 1
                if self.j >= 50:
                    print("SAMPLE DONE")
                    SAMPLE = False
    
    @pyqtSlot()
    def save(self):

        global SAVE

        if SAVE == True:

            with open("Default Left.csv", "a", newline="") as file:
                writer = csv.writer(file)
                writer.writerow(np.round([row for row in self.cap2fullsample], decimals=2))

            with open("Default Center.csv", "a", newline="") as file:
                writer = csv.writer(file)
                writer.writerow(np.round([row for row in self.cap3fullsample], decimals=2))

            with open("Default Eyebrow.csv", "a", newline="") as file:
                writer = csv.writer(file)
                writer.writerow(np.round([row for row in self.cap4fullsample], decimals=2))

            with open("Default Right.csv", "a", newline="") as file:
                writer = csv.writer(file)
                writer.writerow(np.round([row for row in self.cap1fullsample], decimals=2))

                current_directory = os.getcwd()
                print("Current directory:", current_directory)
            
            SAVE = False
            self.cap1fullsample = []
            self.cap2fullsample = []
            self.cap3fullsample = []
            self.cap4fullsample = []

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
            self.serial_worker.signals.sample.connect(self.sample)
            self.serial_worker.signals.save.connect(self.save)
            self.serial_worker.signals.prediction.connect(self.prediction)
            # execute the worker
            self.threadpool.start(self.serial_worker)
        else:
            # kill thread
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

#############
#  RUN APP  #
#############
if __name__ == '__main__':
    app = QApplication(sys.argv)
    w = MainWindow()
    app.aboutToQuit.connect(w.ExitHandler)
    w.show()
    sys.exit(app.exec_())
