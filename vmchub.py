from PyQt6.QtWidgets import QApplication, QLabel, QGridLayout, QLineEdit, QPushButton, QMainWindow, QWidget
from PyQt6.QtGui import QPixmap
from PyQt6 import QtCore
from PyQt6.QtCore import QObject, QThread, pyqtSignal, QRunnable, QThreadPool
from pynput import keyboard
from threading import Thread
from queue import Queue
from pythonosc import udp_client
from pythonosc.dispatcher import Dispatcher
from pythonosc import osc_server
import threading
import json
import yaml
import time
import os
import sys


class OscForwarder(QThread):

    def __init__(self, settings):
        super(OscForwarder, self).__init__()
        self.clients = []
        self.clients_active = []
        self.settings = settings
        self.recording_file = False
        self.idle_recording = []
        self.idle_animations = [None] * len(self.settings['forward_ports'])
        self.load_idle_animations()

    def load_idle_animations(self):
        for i in range(len(self.idle_animations)):
            try:
                if (os.path.exists('idle_animation_{num}.json'.format(num=(i+1)))):
                    print('opening this file '+'idle_animation_{num}.json'.format(num=(i+1)))
                    with open('idle_animation_{num}.json'.format(num=(i+1)), 'r') as open_file:
                        self.idle_animations[i] = {
                            'current_index': 0, 
                            'recording': json.load(open_file)}
                        self.idle_animations[i]['max_index'] = len(self.idle_animations[i]['recording'])
                else:
                    self.idle_animations[i] = None
            except Exception as e:
                print('Problem trying to load idle file')
                print(e)


    def start_idle_record(self, num):
        self.idle_recording = []
        self.recording_file = True

    def stop_idle_record(self, num):
        self.recording_file = False
        with open('idle_animation_{num}.json'.format(num=num), 'w+') as open_file:
            json.dump(self.idle_recording, open_file)
        self.idle_animations[num-1] = {'current_index': 0,
                                       'recording': self.idle_recording,
                                       'max_index': len(self.idle_recording)}
        self.idle_recording = []

    def set_forwarder_active(self, num):
        self.clients_active[num] = True

    def set_forwarder_inactive(self, num):
        self.clients_active[num] = False

    def forwarder(self, *cmd):
        if (self.recording_file):
            self.idle_recording.append(cmd)
        else:
            for i, client in enumerate(self.clients):
                if (self.clients_active[i] or ('/VMC/Ext/Blend' in cmd[0])):
                    client.send_message(cmd[0], cmd[1:])
                else:
                    anim = self.idle_animations[i]
                    if (anim is not None):
                        recording = anim['recording']
                        anim['current_index'] = anim['current_index']+1
                        if (anim['current_index'] >= anim['max_index']):
                            anim['current_index'] = 0
                        current_index = anim['current_index']
                        if('/VMC/Ext/Blend' not in recording[current_index][0]):
                            client.send_message(
                                recording[current_index][0], recording[anim['current_index']][1:])

    def run(self):
        self.dispatcher = Dispatcher()
        self.dispatcher.map('*', self.forwarder)
        server = osc_server.ThreadingOSCUDPServer(
            ('127.0.0.1', self.settings['source_port']), self.dispatcher)
        for fp in self.settings['forward_ports']:
            print('setting up :'+str(fp))
            client = udp_client.SimpleUDPClient('127.0.0.1', int(fp))
            self.clients.append(client)
            self.clients_active.append(False)
        server.serve_forever()


class VmcHubWindow(QMainWindow):

    turn_off_osc_forward = pyqtSignal(int)
    turn_on_osc_forward = pyqtSignal(int)
    turn_on_record_idle = pyqtSignal(int)
    turn_off_record_idle = pyqtSignal(int)

    settings = {
        'forward_ports': [39541, 39542, 39543, 39544],
        'source_port': 39540
    }

    def __init__(self):
        super(VmcHubWindow, self).__init__()
        # attempt to read settings
        self.read_settings_from_file()
        # set window geometry
        self.setGeometry(100, 100, 650, 200)
        self.setFixedSize(650, 300)
        # set main widget
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        # hardcoded values (should be dynamic)
        num_of_rows = len(self.settings['forward_ports'])
        # setup layout
        layout = QGridLayout()
        active_label = QLabel("<h3>ACTIVE</h3>")
        active_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignHCenter)
        layout.addWidget(active_label, 0, 0, 1, 1,
                         QtCore.Qt.AlignmentFlag.AlignHCenter)
        shortcut_label = QLabel("<h3>SHORTCUT KEY</h3>")
        shortcut_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(shortcut_label, 0, 1, 1, 1,
                         QtCore.Qt.AlignmentFlag.AlignLeft)
        record_idle = QLabel("<h3>RECORD IDLE</h3>")
        record_idle.setAlignment(QtCore.Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(record_idle, 0, 2, 1, 1,
                         QtCore.Qt.AlignmentFlag.AlignLeft)
        idle_exists = QLabel("<h3>IDLE EXISTS</h3>")
        idle_exists.setAlignment(QtCore.Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(idle_exists, 0, 3, 1, 1,
                         QtCore.Qt.AlignmentFlag.AlignLeft)
        forward_port = QLabel("<h3>FORWARD PORT</h3>")
        forward_port.setAlignment(QtCore.Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(forward_port, 0, 4, 1, 1,
                         QtCore.Qt.AlignmentFlag.AlignLeft)
        # setup rows container
        self.rows = [None] * num_of_rows
        # construct the rows in the UI
        for i in range(num_of_rows):
            self.make_row_of_widgets(
                layout, i, self.settings['forward_ports'], self.rows)
        # set the layout on the main widget
        layout.addWidget(QLabel("-"*125), (num_of_rows+2), 0,
                         1, 5, QtCore.Qt.AlignmentFlag.AlignHCenter)
        # set source port
        layout.addWidget(QLabel("<h3>SOURCE PORT</h3>"), (num_of_rows+3),
                         4, 1, 1, QtCore.Qt.AlignmentFlag.AlignLeft)
        self.source_port = QLineEdit(str(self.settings['source_port']))
        self.source_port.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight)
        layout.addWidget(self.source_port, (num_of_rows+4), 4,
                         1, 1, QtCore.Qt.AlignmentFlag.AlignLeft)
        # add save / close button
        layout.addWidget(QLabel("-"*125), (num_of_rows+5), 0,
                         1, 5, QtCore.Qt.AlignmentFlag.AlignHCenter)
        self.save_button = QPushButton("Save/Apply")
        self.save_button.clicked.connect(self.save_and_apply)
        layout.addWidget(self.save_button, (num_of_rows+6), 4,
                         1, 1, QtCore.Qt.AlignmentFlag.AlignHCenter)
        # finally set the layout
        main_widget.setLayout(layout)
        self.hotkey_listener = HotkeyListener()
        self.hotkey_listener.hotkey_emitter.hotkey_switch_active.connect(
            self.switch_active)
        self.hotkey_listener.start()
        self.osc_server = OscForwarder(self.settings)
        self.turn_on_osc_forward.connect(self.osc_server.set_forwarder_active)
        self.turn_on_record_idle.connect(self.osc_server.start_idle_record)
        self.turn_off_record_idle.connect(self.osc_server.stop_idle_record)
        self.turn_off_osc_forward.connect(
            self.osc_server.set_forwarder_inactive)
        self.osc_server.start()

    # override exit event

    def closeEvent(self, event):
        # close window
        self.osc_server.quit()
        self.hotkey_listener.quit()
        event.accept()

    def save_settings_to_file(self):
        with open('settings.yaml', 'w') as file:
            yaml.dump(self.settings, file)

    def read_settings_from_file(self):
        try:
            with open('settings.yaml', 'r') as file:
                tmp_settings = yaml.safe_load(file)
                valid = True
                if ('forward_ports' not in tmp_settings):
                    valid = False
                if ('source_port' not in tmp_settings):
                    valid = False
                if (valid):
                    if (len(tmp_settings['forward_ports']) < 1):
                        valid = False
                if (valid):
                    self.settings = tmp_settings
                else:
                    print('Invalid Settings File')
        except Exception as e:
            print('Unable to read Settings File :')
            print(e)

    def sync_ui_to_settings(self):
        try:
            for i, row in enumerate(self.rows):
                forward_port = int(row['forward_port'].text())
                self.settings['forward_ports'][i] = forward_port
            self.settings['source_port'] = int(self.source_port.text())
        except Exception as e:
            print('could not sync ui with settings : ')
            print(e)

    def sync_settings_to_ui(self):
        try:
            for i, port in enumerate(self.settings['forward_ports']):
                forward_port_widget = self.rows[i]['forward_port']
                forward_port_widget.setText(str(int(port)))
            self.source_port.setText(str(int(self.settings['source_port'])))
        except Exception as e:
            print('could not sync settings with ui : ')
            print(e)

    def check_if_idle_file_exists(self, row_num):
        if (os.path.exists('idle_animation_{num}.json'.format(num=row_num))):
            return True
        else:
            return False

    def update_idle_file_exist_labels(self):
        for i, row in enumerate(self.rows):
            idle_file_exists_label = row['idle_exists_label']
            check_exist = self.check_if_idle_file_exists(i+1)
            idle_file_exists_label.setText(
                '<h4>{check_exist}</h4>'.format(check_exist=check_exist))

    def save_and_apply(self):
        self.sync_ui_to_settings()
        self.save_settings_to_file()

    def make_row_of_widgets(self, layout, row_num, row_ports, rows):
        row = {}
        # active marker
        active_star_pixmap = QPixmap('star.png').scaled(15, 15)
        is_active_label = QLabel()
        is_active_label.setPixmap(active_star_pixmap)
        row['is_active_label'] = is_active_label
        layout.addWidget(is_active_label, (row_num+1), 0, 1,
                         1, QtCore.Qt.AlignmentFlag.AlignHCenter)
        is_active_label.hide()
        # shortcut
        shortcut_label = QLabel("<h4>Numpad {}</h4>".format(row_num+1))
        layout.addWidget(shortcut_label, (row_num+1), 1, 1,
                         1, QtCore.Qt.AlignmentFlag.AlignLeft)
        row['shortcut_label'] = shortcut_label
        # record/stop
        idle_button = QPushButton('Record Idle')
        layout.addWidget(idle_button, (row_num+1), 2, 1, 1,
                         QtCore.Qt.AlignmentFlag.AlignLeft)
        idle_button.clicked.connect(lambda: self.switch_idle_record(row_num+1))
        row['idle_button'] = idle_button
        # idle exists label
        check_exist = str(self.check_if_idle_file_exists(row_num+1))
        idle_exists_label = QLabel(
            '<h4>{check_exist}</h4>'.format(check_exist=check_exist))
        layout.addWidget(idle_exists_label, (row_num+1), 3, 1,
                         1, QtCore.Qt.AlignmentFlag.AlignLeft)
        row['idle_exists_label'] = idle_exists_label
        # port forward
        forward_port = QLineEdit(str(row_ports[row_num]))
        forward_port.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight)
        layout.addWidget(forward_port, (row_num+1), 4, 1, 1,
                         QtCore.Qt.AlignmentFlag.AlignLeft)
        row['forward_port'] = forward_port
        # add row to rows collection
        rows[row_num] = row

    def disable_all_idle_buttons(self):
        for row in self.rows:
            idle_button = row['idle_button']
            forward_port = row['forward_port']
            source_port = self.source_port
            save_button = self.save_button
            idle_button.setEnabled(False)
            forward_port.setEnabled(False)
            source_port.setEnabled(False)
            save_button.setEnabled(False)

    def enable_all_idle_buttons(self):
        for row in self.rows:
            idle_button = row['idle_button']
            forward_port = row['forward_port']
            source_port = self.source_port
            save_button = self.save_button
            idle_button.setEnabled(True)
            forward_port.setEnabled(True)
            source_port.setEnabled(True)
            save_button.setEnabled(True)

    def switch_idle_record(self, num):
        idle_button = self.rows[num-1]['idle_button']
        if (idle_button.text() == 'Record Idle'):
            self.disable_all_idle_buttons()
            idle_button.setText('Stop Record')
            idle_button.setEnabled(True)
            self.turn_on_record_idle.emit(num)
        else:
            self.turn_off_record_idle.emit(num)
            idle_button.setText('Record Idle')
            self.enable_all_idle_buttons()
            self.update_idle_file_exist_labels()

    def switch_active(self, num):
        if (num <= len(self.rows)):
            active_label = self.rows[(num-1)]['is_active_label']
            if (active_label.isVisible()):
                active_label.hide()
                self.turn_off_osc_forward.emit((num-1))
            else:
                active_label.show()
                self.turn_on_osc_forward.emit((num-1))


class HotkeyEmitter(QObject):
    hotkey_switch_active = pyqtSignal(int)


class HotkeyListener(QThread):

    def __init__(self):
        super(HotkeyListener, self).__init__()
        self.hotkey_emitter = HotkeyEmitter()

    def run(self):
        listener = keyboard.Listener(on_press=self.on_press)
        listener.start()

    def send_switch_active_event(self, num):
        self.hotkey_emitter.hotkey_switch_active.emit(num)

    def on_press(self, key):
        if hasattr(key, 'vk'):
            match key.vk:
                case 97:
                    self.send_switch_active_event(1)
                case 98:
                    self.send_switch_active_event(2)
                case 99:
                    self.send_switch_active_event(3)
                case 100:
                    self.send_switch_active_event(4)
                case 101:
                    self.send_switch_active_event(5)
                case 102:
                    self.send_switch_active_event(6)
                case 103:
                    self.send_switch_active_event(7)
                case 104:
                    self.send_switch_active_event(8)
                case 105:
                    self.send_switch_active_event(9)


app = QApplication([])
window = VmcHubWindow()
window.save_button.setFocus()
window.show()
sys.exit(app.exec())
