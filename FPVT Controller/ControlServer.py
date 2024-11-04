import time
import socket
import tkinter as tk
import VisualController as vc


class Server:
    def __init__(self):
        self.HOST = "0.0.0.0"
        self.PORT = 3333
        self.TIMEOUT = 3
        self.MAXBUF = 1024
        print("Create UDP Server Socket")
        self.socks = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socks.settimeout(self.TIMEOUT)
        self.socks.bind((self.HOST, self.PORT))
        self.buf = bytearray(self.MAXBUF)

    def connect(self):
        try:
            self.size, self.addr = self.socks.recvfrom_into(self.buf)
            print("Init connection with robot")
            print("Received", self.buf[:self.size], self.size, "bytes from", self.addr)
            return True
        except socket.timeout:
            print("Waiting for connection...")
            return False
        except Exception as e:
            print("Error: ", e)
            return False

    def send(self, data):
        try:
            self.size = self.socks.sendto(data, self.addr)
            print("Sent", self.buf[:self.size], self.size, "bytes to", self.addr)
            return True
        except Exception as e:
            print("Error: ", e)
            return False
        
    def close(self):
        self.socks.close()

controller = vc.get_pressed_keys()
controller.root.update()
connected = False
s = Server()
while True:
    controller.root.update()
    if not connected:
        connected = s.connect()
    if controller.get_keys() != 0: s.send(controller.keybyte.to_bytes())
    time.sleep(0.08)
    
