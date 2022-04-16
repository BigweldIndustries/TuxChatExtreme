from PyQt5 import QtWidgets, uic, QtCore, QtGui
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
import sys
import qdarkstyle
import os
import socket
from datetime import datetime
import time
import urllib.request
import json

ran_server = False

class Send(QtCore.QThread):
    global window
    data = QtCore.pyqtSignal(str)

    def __init__(self, parent=None):
        super(Send, self).__init__(parent)
        self._stopped = True
        self._mutex = QtCore.QMutex()

    def stop(self):
        self._mutex.lock()
        self._stopped = True
        self._mutex.unlock()

    def run(self):
        global s
        global username
        tempusername = window.username_box.text()
        if tempusername != '' and window.host_box.text() != '' and window.port_box.text() != '':
            self.data.emit("CLEAR")
            username = tempusername
            rawmsg = window.input_box.text()
            #date_now = datetime.now().strftime('%Y-%m-%d %H:%M:%S') 
            message = {
                "username": username,
                "content": rawmsg
                }
            jsonmessage = json.dumps(message)
            s.send(jsonmessage.encode())
            self.data.emit(f"Me -> {message["content"]}")
        else:
            self.data.emit("CLEAR")
            self.data.emit("ERROR: No username or server selected")

class Connect(QtCore.QThread):
    global window
    data = QtCore.pyqtSignal(str)

    def __init__(self, parent=None):
        super(Connect, self).__init__(parent)
        self._stopped = True
        self._mutex = QtCore.QMutex()

    def stop(self):
        self._mutex.lock()
        self._stopped = True
        self._mutex.unlock()

    def run(self):
        global connections
        global s
        try:
            s = socket.socket()
            SERVER_HOST = window.host_box.text()
            SERVER_PORT = window.port_box.text()
            window._worker.stop()
            self.data.emit(f"Connecting to {SERVER_HOST}:{SERVER_PORT}...")
            s.connect((SERVER_HOST, int(SERVER_PORT)))
            self.data.emit("Connected - Listening for messages")
            window._worker.start()
        except Exception as e:
            self.data.emit(f"ERROR: {e}")

class Server(QtCore.QThread):
    global window
    data = QtCore.pyqtSignal(str)

    def __init__(self, parent=None):
        super(Server, self).__init__(parent)
        self._stopped = True
        self._mutex = QtCore.QMutex()

    def stop(self):
        self._mutex.lock()
        self._stopped = True
        self._mutex.unlock()

    def request_data(self,incoming_data):
        self.data.emit(f"{incoming_data}")

    def run(self):
        global connections
        try:
            connections = []
            con_thread_num = 0
            port = int(window.server_port_box.text())
            socket_instance = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            socket_instance.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            socket_instance.bind(('', port))
            socket_instance.listen(4)

            Xip = urllib.request.urlopen('https://ident.me').read().decode('utf8')
            Iip = socket.gethostbyname(socket.gethostname())
            self.data.emit(f"Server started on INTERNAL-{Iip} EXTERNAL-{Xip} on PORT-{str(port)}")
            while True:
                socket_connection, address = socket_instance.accept()
                connections.append(socket_connection)
                setattr(self, f"t{str(con_thread_num)}", ServeUser(socket_connection, address))
                tempthread = getattr(self, f"t{str(con_thread_num)}")
                tempthread.data.connect(self.request_data)
                tempthread.start()
                con_thread_num += 1
        except Exception as e:
            self.data.emit(f"ERROR: {e}")


class Mailbox(QtCore.QThread):
    global window
    data = QtCore.pyqtSignal(str)

    def __init__(self, parent=None):
        super(Mailbox, self).__init__(parent)
        self._stopped = True
        self._mutex = QtCore.QMutex()

    def stop(self):
        self._mutex.lock()
        self._stopped = True
        self._mutex.unlock()

    def run(self):
        global connected
        global s
        while True:
            message = s.recv(1024).decode()
            self.data.emit(message)

class ServeUser(QtCore.QThread):
    global window
    data = QtCore.pyqtSignal(str)

    def __init__(self, connection, address, parent=None):
        super(ServeUser, self).__init__(parent)
        self._stopped = True
        self._mutex = QtCore.QMutex()
        self.connection = connection
        self.address = address

    def stop(self):
        self._mutex.lock()
        self._stopped = True
        self._mutex.unlock()

    def broadcast(self, message: str, connection: socket.socket) -> None:
        global connections 
        for client_conn in connections:
            # Check if isn't the connection of who's send
            if client_conn != connection:
                try:
                    client_conn.send(message.encode())

                # if it fails, there is a chance of socket has died
                except Exception as e:
                    print('Error broadcasting message: {e}')
                    self.remove_connection(client_conn)


    def remove_connection(self, conn: socket.socket) -> None:
        global connections 
        # Check if connection exists on connections list
        if conn in connections:
            # Close socket connection and remove connection from connections list
            conn.close()
            connections.remove(conn)

    def run(self):
        global connections 
        while True:
            try:
                msg = self.connection.recv(1024)
                self.data.emit(f"INCOMING PACKET: {msg}")
                if msg:
                    msg = msg.decode()
                    msg = json.loads(msg)
                    # If no message is received, there is a chance that connection has ended
                    # so in this case, we need to close connection and remove it from connections list.
                    msg_to_send = f'{msg["username"]} ({self.address[0]}) -> {msg["content"]}'
                    self.broadcast(msg_to_send, self.connection)

                # Close connection if no message was sent
                else:
                    self.remove_connection(self.connection)
                    break

            except Exception as e:
                self.data.emit(f"ERROR: {e}")
                self.remove_connection(self.connection)
                break

class Ui(QtWidgets.QMainWindow):
    
    keyPressed = QtCore.pyqtSignal(QtCore.QEvent)
    def __init__(self):
        super(Ui, self).__init__()
    
        # Load UI
        self.fontDB = QtGui.QFontDatabase()
        self.fontDB.addApplicationFont("assets/font.ttf")
        uic.loadUi('assets/main.ui', self)
        # Reveal window
        self.show()

        # Load threads
        self._worker = Mailbox()
        self._worker.started.connect(self.worker_started_callback)
        self._worker.finished.connect(self.worker_finished_callback)
        self._worker.data.connect(self.worker_data_callback)

        self._server = Server()
        self._server.started.connect(self.server_started_callback)
        self._server.finished.connect(self.server_finished_callback)
        self._server.data.connect(self.server_data_callback)

        self._connect = Connect()
        self._connect.started.connect(self.connect_started_callback)
        self._connect.finished.connect(self.connect_finished_callback)
        self._connect.data.connect(self.connect_data_callback)

        self._send = Send()
        self._send.started.connect(self.send_started_callback)
        self._send.finished.connect(self.send_finished_callback)
        self._send.data.connect(self.send_data_callback)
        
        # Load UI
        self.connect_button.clicked.connect(self.connect)
        self.keyPressed.connect(self.on_key)

        self.server_start_button.clicked.connect(self.start_server)

    
    def keyPressEvent(self, event):
        super(Ui, self).keyPressEvent(event)
        self.keyPressed.emit(event) 

    def on_key(self, event):
        if str(event.key()) == "16777220":
            if QApplication.focusWidget().objectName() == "input_box":
                self.send_message()


    def send_message(self):
        self._send.start()
        

    def worker_data_callback(self, data):
        self.chat_box.setPlainText(self.chat_box.toPlainText()+data+"\n")

        self.chat_box.moveCursor(QtGui.QTextCursor.End)
    def worker_started_callback(self):
        pass
    def worker_finished_callback(self):
        pass

    def server_data_callback(self, data):
        self.server_log_box.setPlainText(self.server_log_box.toPlainText()+data+"\n")
        self.server_log_box.moveCursor(QtGui.QTextCursor.End)
    def server_started_callback(self):
        self.server_log_box.setPlainText(self.server_log_box.toPlainText()+"Server starting...\n")
        pass
    def server_finished_callback(self):
        self.server_log_box.setPlainText(self.server_log_box.toPlainText()+"Previous server closed\n")
        self._server.start()
        pass
    
    def connect_data_callback(self, data):
        self.chat_box.setPlainText(self.chat_box.toPlainText()+data+"\n")
        self.chat_box.moveCursor(QtGui.QTextCursor.End)
    def connect_started_callback(self):
        pass
    def connect_finished_callback(self):
        pass

    def send_data_callback(self, data):
        if data == "CLEAR":
            self.input_box.setText("")
        else:
            self.chat_box.setPlainText(self.chat_box.toPlainText()+data+"\n")
            self.chat_box.moveCursor(QtGui.QTextCursor.End)
    def send_started_callback(self):
        pass
    def send_finished_callback(self):
        pass


    def connect(self):
        global s
        if self.username_box.text() != '' and self.host_box.text() != '' and self.port_box.text() != '':
            self._connect.start()
        else:
            self.chat_box.setPlainText(self.chat_box.toPlainText()+"ERROR: Make sure you have a host, port, and username that is valid before attempting to connect\n")
            self.chat_box.moveCursor(QtGui.QTextCursor.End)
            


    

    def start_server(self):
        global ran_server
        if ran_server:
            self.server_log_box.setPlainText(self.server_log_box.toPlainText()+"Restarting server thread...\n")
            self._server.terminate()
        else:
            self.server_log_box.setPlainText(self.server_log_box.toPlainText()+"Starting server thread...\n")
            self._server.start()
            ran_server = True
        



app = QtWidgets.QApplication(sys.argv)
window = Ui()
app.setStyleSheet(qdarkstyle.load_stylesheet())
app.exec_()