import wifi
import socketpool
import ipaddress
import time
import neopixel
import board
from adafruit_motorkit import MotorKit

m1 = MotorKit().motor1
m2 = MotorKit().motor2
m1.throttle = 0.0
m2.throttle = 0.0
xSpeed = 0.0
ySpeed = 0.0
xDir = 0.0
yDir = 0.0

def motor_logic():
    global m1
    global m2
    global xDir
    global yDir
    global xSpeed
    global ySpeed
    if W:
        xDir = 1.0
        yDir = 1.0
        if A:
            xSpeed = 1.0
            ySpeed = 0.5
        elif D:
            xSpeed = 0.7
            ySpeed = 1.0
        else: 
            xSpeed = 1.0
            ySpeed = 1.0
    elif S:
        xDir = -1.0
        yDir = -1.0
        if A:
            xSpeed = 0.7
            ySpeed = 1.0
        elif D:
            xSpeed = 1.0
            ySpeed = 0.5
        else:
            xSpeed = 1.0
            ySpeed = 1.0
    elif D:
        xDir = -1.0
        xSpeed = 1.0
        yDir = 1.0
        ySpeed = 1.0
    elif A:
        xDir = 1.0
        xSpeed = 1.0
        yDir = -1.0
        ySpeed = 1.0
    else:
        xSpeed = 0.0
        ySpeed = 0.0
    #print(xSpeed * xDir, ySpeed *yDir )           
    m1.throttle = xDir * xSpeed 
    m2.throttle = yDir * ySpeed 



pixels = neopixel.NeoPixel(board.NEOPIXEL, 1)
rgb = 40
while rgb > 0:
    rgb-=1;
    pixels[0] = (rgb, 1, rgb)
    time.sleep(0.01)


# edit host and port to match server
SSID = "your-ssid"
PASS = "your-password"
HOST = "192.0.2.11"
PORT = 3333
TIMEOUT = 0.25
INTERVAL = 0.01
MAXBUF = 1024

W = False
A = False
S = False
D = False

while True:
    print("Connecting to Wifi")
    try:
        wifi.radio.connect(SSID, PASS)
        pixels[0] = (0, 0, 1) # color for state green connecting
        break
    except:
        print("Failed to connect to " + SSID)

pool = socketpool.SocketPool(wifi.radio)

print("Self IP", wifi.radio.ipv4_address)
server_ipv4 = ipaddress.ip_address(pool.getaddrinfo(HOST, PORT)[0][4][0])
print("Server ping", server_ipv4, wifi.radio.ping(server_ipv4), "ms")

buf = bytearray(MAXBUF)

print("Create UDP Client socket")
s = pool.socket(pool.AF_INET, pool.SOCK_DGRAM)
s.settimeout(TIMEOUT)

while True:
    try:
        size = s.sendto(b"Hello, world", (HOST, PORT))
        pixels[0] = (0, 0, 1) 
    except Exception as e:
        print(e)
        continue
    
    while True:
        try:
            size, addr = s.recvfrom_into(buf)
            #print(buf[:size])
            if buf[0] == 0: 
                W = False
                A = False
                S = False
                D = False
            else:
                W = (buf[0] | 0b11110111) == 0b11111111
                A = (buf[0] | 0b11111011) == 0b11111111
                S = (buf[0] | 0b11111101) == 0b11111111
                D = (buf[0] | 0b11111110) == 0b11111111
            motor_logic()
        
        except Exception as e:
            
            #print("nothing received into buffer"+str(e))
            pixels[0] = (1, 1, 0)
            W = False
            A = False
            S = False
            D = False
            motor_logic()

    time.sleep(INTERVAL)
    
s.close()
print("GoodBye")
