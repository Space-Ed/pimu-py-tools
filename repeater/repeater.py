from key_state import KeyState

class Repeater:
    def __init__(self, output):
        self.keys = dict()
        self.output = output
        self.sustain = False
        self.lock = False
        self.loop = False

        self.highq = 0
        self.lowq = 0
        self.unitp = 1

    def getKeyState(self, message):
        key = (message.channel, message.note)
        state = self.keys.get(key)

        if (state is None):
            state = KeyState(message, self)
            self.keys[key] = state

        return state

    def heldNotes(self, is_held=True):
        return filter(lambda ks: ks.held == is_held, self.keys.values())
    def onNotes(self, is_on=True):
        return filter(lambda ks: ks.on == is_on, self.keys.values())

    def noteOn(self, message):
        keystate = self.getKeyState(message)
        keystate.noteOn(message)

    def noteOff(self, message):
        keystate = self.getKeyState(message)
        keystate.noteOff(message)

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

    def loopOn(self):
        self.loop = True

    def loopOff(self):
        self.loop = False
        # remove all events from the tapes
        self.clearAllTapes()
        self.turnOffUnheld()

    def set_lowQ(self, lowq):
        self.lowq = lowq
        self.reset_periods()

    def set_highQ(self, highq):
        self.highq = highq
        self.reset_periods()

    def set_unit_period(self, period):
        self.unitp = period
        self.reset_periods()

    def reset_periods(self):
        for ks in self.keys.values():
            ks.set_quantized_period(self.lowq, self.highq, self.unitp)

    def clearAllTapes(self):
        for ks in self.keys.values():
            ks.tape.clear()

    def turnOffUnheld(self):
        for ks in self.keys.values():
            if ks.on and not ks.held:
                ks.turnOff()

    def update(self, dt):
        for keystate in self.keys.values():
            keystate.update(dt)

    def panic(self):
        self.output.reset()
