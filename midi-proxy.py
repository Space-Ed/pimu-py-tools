#! python3
import mido
import sys
import signal

def create_source(midi_dev_name):
    return  mido.open_input(midi_dev_name)

def create_sink(midi_dev_name):
    return mido.open_output(midi_dev_name)

def forwardMessage(sink):
    def forwarder(msg):

        if (msg.type != 'clock'):
            sink.send(msg)
            print(msg)


    return forwarder

def connect(source, sink):
    source.callback = forwardMessage(sink)

if __name__=='__main__':
    inputPortName = sys.argv[1]
    outputPortName  = sys.argv[2]

    try:
        source = create_source(inputPortName)
        sink = create_sink(outputPortName)
    except OSError as err:
        print(err)
        sys.exit(1)

    print("setting up link from '%s' to '%s'" % (inputPortName, outputPortName))
    connect(source, sink)

    def signal_handler(signal, frame):
        print("closing ports and exiting")
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.pause()

