import time
import socket
import tkinter as tk
import VisualController as vc


HOST = "0.0.0.0"
PORT = 3333
TIMEOUT = 1
MAXBUF = 1024



print("Create UDP Server Socket")
s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
s.settimeout(TIMEOUT)

s.bind((HOST, PORT))

buf = bytearray(MAXBUF)


# Create main tkinter window
controller = vc.get_pressed_keys()
controller.root.update()

while True:
    try:
        controller.root.update()
        size, addr = s.recvfrom_into(buf)
        print("Init connection with robot")
        print("Received", buf[:size], size, "bytes from", addr)
    except socket.timeout:
        print("Waiting for connection...")
        continue
    except Exception as e:
        print("Error: ", e)
        continue
    
    while True:
        try:
            size = s.sendto(controller.get_keys().to_bytes(), addr)
            print("Sent", buf[:size], size, "bytes to", addr)
        except Exception as e:
            print("Error: ", e)
            controller.root.update()
            break
        controller.root.update()
        time.sleep(0.1)

