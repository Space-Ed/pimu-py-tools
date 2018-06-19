from math import floor
import mido
from tape import Tape, TapeEvent

class KeyState:
    def __init__(self, message, parent):
        self.note = message.note
        self.channel = message.channel
        self.held = False
        self.on = False
        self.tape = Tape(self)
        self.set_quantized_period(parent.lowq, parent.highq, parent.unitp)
        self.parent = parent
        self.current = message

    def set_quantized_period(self, qlow, qhigh, unit):
        p = unit*2**floor(((self.note - 60)/60.0)*(qhigh-qlow) + qlow)
        self.tape.set_period(p)

    def noteOn(self, message):
        self.held = True
        parent = self.parent

        if parent.loop:
            if self.on:
                self.tape.cut() #remove the currently playing event of the tape
                self.turnOff()
        elif (parent.sustain or self.parent.lock) and self.on:
            self.turnOff()

        self.parent.output.send(message)
        self.on = True
        self.current = TapeEvent(message, self.tape)

    def turnOff(self):
        self.on = False
        self.parent.output.send(mido.Message('note_off', note=self.note, channel=self.channel))

    def noteOff(self, message):
        self.held = False
        parent = self.parent

        if parent.loop:
            # insert note into tape
            self.tape.add_note(self.current, TapeEvent(message, self.tape))
            parent.output.send(message)
            self.on = False

        #note off only turns off when sustain and lock are off
        elif not (parent.sustain or parent.lock):
            parent.output.send(message)
            self.on = False

        self.current = None

    def update(self, dt):
        self.tape.update(dt)
        # print(self.tape)
