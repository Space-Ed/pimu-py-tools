#! /usr/bin/python3

import readline, socket

s = socket.socket()
s.connect(('localhost', 5000))
s.settimeout(0.2)

while True:
    a = input('send: ')
    s.send(a.encode('utf-8'))
    try:
        b = s.recv(1024)
        if b != '': print('resp:', b)
    except Exception:
        pass
