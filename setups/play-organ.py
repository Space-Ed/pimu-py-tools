import signal
import sys
import mod_host
import time
if __name__ == '__main__':
    c = mod_host.Client(5000)

    def signal_handler(signal, frame):
        c.disconnect()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)

    try:
        c.add_bundle("/home/pi/lv2plugins/faust.lv2")
        c.add_plugin('organ')
        time.sleep(5) 
        signal.pause()
    except Exception as e:
        print(repr(e))
        signal_handler(signal.SIGINT, 0)
