#! python3
import mido
import sys
import signal

def create_source(midi_dev_name):
    return  mido.open_input(midi_dev_name)

def create_sink(midi_dev_name):
    return mido.open_output(midi_dev_name)

def key_channel(message):
    return (message.channel, message.note)

class Tape:
    def __init__(self):
        pass

class KeyState:
    def __init__(self, message):
        self.note = message.note
        self.channel = message.channel
        self.held = False
        self.on = False
        self.tape = Tape()

class Sustainer:
    def __init__(self, output, sustainCC):
        self.keys = dict()
        self.output = output
        self.sustain = False
        self.sustainCC = sustainCC
        self.lock = False

    def send(self, message):
        if message.type == 'control_change':
            if message.control == self.sustainCC:
                if message.value == 127:
                    self.sustainOn()
                else:
                    self.sustainOff()
            elif message.control == 3:
                if message.value == 127:
                    self.lockOn()
                else:
                    self.lockOff()
        elif message.type == 'note_on':
            self.noteOn(message)
        elif message.type == 'note_off':
            self.noteOff(message)
        else:
            self.output.send(message)

    def getKeyState(self, message):
        key = key_channel(message)
        state = self.keys.get(key)

        if (state is None):
            state = KeyState(message)
            self.keys[key] = state

        return state

    def heldNotes(self, is_held=True):
        return filter(lambda ks: ks.held == is_held, self.keys.values())
    def onNotes(self, is_on=True):
        return filter(lambda ks: ks.on == is_on, self.keys.values())

    def noteOn(self, message):
        keystate = self.getKeyState(message)
        keystate.held = True

        if (self.sustain or self.lock) and keystate.on:
            self.output.send(mido.Message('note_off', note=keystate.note, channel=keystate.channel))

        self.output.send(message)

        keystate.on = True

    def noteOff(self, message):
        keystate = self.getKeyState(message)
        keystate.held = False

        #note off only turns off when sustain and lock are off
        if not (self.sustain or self.lock):
            self.output.send(message)
            keystate.on = False

    def lockOn(self):
        self.lock = True

    def lockOff(self):
        self.lock = False

        if not self.sustain:
            self.turnOffUnheld()

    def sustainOn(self):
        self.sustain = True;

    def sustainOff(self):
        self.sustain = False

        if not self.lock:
            self.turnOffUnheld()

    def turnOffUnheld(self):
        for ks in self.keys.values():
            if ks.on and not ks.held:
                self.output.send(mido.Message('note_off', note=ks.note, channel=ks.channel))
                ks.on = False

    def panic():
        pass

def connect(source, sink):
    sustainer = Sustainer(sink, 64)
    source.callback = lambda msg: sustainer.send(msg)

if __name__=='__main__':
    try:
        inputPortName = sys.argv[1]
        outputPortName = sys.argv[2]
    except IndexError:
        print("must provide input and output device names as args")

    try:
        source = create_source(inputPortName)
        sink = create_sink(outputPortName)
    except OSError as err:
        print(err)
        sys.exit(1)

    print("setting up sustain from '%s' to '%s'" % (inputPortName, outputPortName))
    connect(source, sink)

    def signal_handler(signal, frame):
        print("closing ports and exiting")
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.pause()
