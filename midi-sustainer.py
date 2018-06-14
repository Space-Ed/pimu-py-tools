#! python3
import mido
import sys
import signal

def create_source(midi_dev_name):
    return  mido.open_input(midi_dev_name)

def create_sink(midi_dev_name):
    return mido.open_output(midi_dev_name)

class Sustainer:
    def __init__(self, output, sustainCC):
        self.notesPlaying = set()
        self.notesHeld = set()
        self.output = output
        self.sustain = False
        self.sustainCC = sustainCC
        self.sustainHeld = False

    def send(self, message):
        if message.type == 'control_change':
            if message.control == self.sustainCC:
                if message.value == 127:
                    self.sustainOn()
                else:
                    self.sustainOff()
            elif message.control == 3:
                if message.value == 127: 
                    self.holdSustain()
                else:
                    self.unholdSustain()
        elif message.type == 'note_on':
            self.noteOn(message)
        elif message.type == 'note_off':
            self.noteOff(message)
        else:
            self.output.send(message)

    def noteOn(self, message):
        note = message.note
        self.notesHeld.add(note)

        if self.sustain:
            if note in self.notesPlaying:
                self.output.send(mido.Message('note_off', note=note))

            self.notesPlaying.add(note)
            self.output.send(message)
        else:
            self.output.send(message)

    def noteOff(self, message):
        note = message.note
        self.notesHeld.remove(note)

        #note off only turns off when sustain is off
        if not self.sustain:
            self.output.send(message)

    def holdSustain(self):
        self.sustainHeld = True

        if not self.sustain:
            self.sustainOn()

    def unholdSustain(self):
        self.sustainHeld = False
        if self.sustain:
            self.sustainOff()

    def sustainOn(self):
        if not self.sustainHeld:
            self.notesPlaying = self.notesHeld.copy()

        self.sustain = True;

    def sustainOff(self):
        if self.sustainHeld:
            return

        self.sustain = False

        # send note off for unheld notes
        for note in self.notesPlaying:
            if not note in self.notesHeld:
                self.output.send(mido.Message('note_off', note=note))

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

