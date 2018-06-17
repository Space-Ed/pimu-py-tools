#! python3
import mido
import sys
import signal
import time
from math import floor

def create_source(midi_dev_name):
    return  mido.open_input(midi_dev_name)

def create_sink(midi_dev_name):
    return mido.open_output(midi_dev_name)

def key_channel(message):
    return (message.channel, message.note)

class TapeEvent:
    def __init__(self, message, tape):
        self.atime = time.time()
        self.rtime = (self.atime - tape.clip_start)/tape.period
        self.partner = None
        self.message = message
        self.tape = tape
        self.standdown = True

    def pair(self, partner):
        self.partner = partner
        partner.partner = self

    def unpair(self):
        self.partner.partner = None
        self.partner = None

def between(a, b, c):
    return (a <= b and b <= c) or (c < a and ((0 <= b and b <= c) or (a <= b and b <= 1)))

class Tape:
    def __init__(self, keystate):
        self.events = []
        self.index = 0
        self.npos = 0
        self.period = 10
        self.clip_start = time.time()
        self.keystate = keystate

    def __repr__(self):
        canvas = ["-"]*100
        for ev in self.events:
            if (ev.message.type == 'note_on'):
                canvas[floor(ev.rtime*100)] = '/'
            else:
                canvas[floor(ev.rtime*100)] = '\\'

        canvas[floor(self.npos*100)] = '|'

        return str(self.index) + ":" + "".join(canvas)

    def set_period(self, seconds):
        if(seconds != self.period):
            atime = time.time()
            self.clip_start = atime - ((seconds*(atime-self.clip_start))/self.period)
            self.period = seconds

    def update(self, dt):
        if (dt > self.period): return

        oldp = self.npos
        newp = self.npos + (dt/self.period)

        if (newp > 1):
            self.npos = newp - 1
            self.clip_start = self.clip_start + self.period
        else:
            self.npos = newp

        if len(self.events) == 0: return# no events to trigger

        self.index = (self.insertionPoint(self.npos)-1)%len(self.events)
        next = self.events[self.index]
        rtime = next.rtime

        print("(oldp:%d, rtime:%d, newp:%d)", (oldp, rtime, self.npos))
        while between(oldp, rtime, self.npos):
            if self.keystate.held:
                self.erase_event(next) # when active we are erasing
            else:
                self.playEvent(next)

            if len(self.events) == 0: return# no events to trigger
            self.index = (self.index + 1)%len(self.events)
            next = self.events[self.index]
            rtime = next.rtime

    def insertionPoint(self, rtime):
        thumb = 0
        next = self.events[thumb]

        while next.rtime <= rtime: #find the index of the event after this one
            thumb += 1
            if thumb == len(self.events):
                break
            next = self.events[thumb]

        return thumb

    def playEvent(self, event):
        self.keystate.on = event.message.type == 'note_on'
        self.keystate.parent.output.send(event.message)


    def cut(self):
        #if this time lies between on and off events it will destroy them
        rtime = (time.time() - self.clip_start)/self.period


    def add_note(self, on_event, off_event):
        notelen = off_event.atime - on_event.atime
        if (notelen < self.period and notelen > 0.01):
            on_event.pair(off_event)
            self.insert_event(on_event)
            self.insert_event(off_event)

    def insert_event(self, event):
        if len(self.events) == 0:
            self.events.append(event)
            self.index = 0
        else:
            thumb = 0
            next = self.events[thumb]

            while next.rtime <= event.rtime: #find the index of the event after this one
                thumb += 1
                if thumb == len(self.events):
                    break
                next = self.events[thumb]

            #insering there inserts before
            self.events.insert(thumb, event)

            # if installed before current scanner head index it is shifted otherwise not
            if thumb < self.index:
                self.index = self.index + 1



    def events_between(self, event1, event2):
        return filter(lambda ev: between(event1.rtime, ev.rtime, event2.rtime), self.events)

    def erase_event(self, event):
        try:
            index = self.events.index(event)
            self.events.pop(index)

            #shift current position back
            if (index < self.index):
                self.index = self.index - 1
        except ValueError:
            pass

        #remove corresponding on/off message
        if not event.partner is None:
            partner = event.partner
            event.unpair()
            self.erase_event(partner)

    def clear(self):
        self.events = []
        self.index = 0

class KeyState:
    def __init__(self, message, parent):
        self.note = message.note
        self.channel = message.channel
        self.held = False
        self.on = False
        self.tape = Tape(self)
        #self.set_quantized_period(parent.lowq, parent.highq)
        self.parent = parent
        self.current = message

    def set_quantized_period(self, qlow, qhigh):
        p = 2**floor(((self.note - 60)*(qhigh-qlow))/60.0 + qlow)
        self.tape.set_period(p)

    def noteOn(self, message):
        self.held = True
        parent = self.parent

        if parent.loop:
            if self.on:
                self.tape.cut() #remove the currently playing event of the tape
                self.turnOff()
        elif (parent.sustain or self.parent.lock) and keystate.on:
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
        print(self.tape)

class Sustainer:
    def __init__(self, output):
        self.keys = dict()
        self.output = output
        self.sustain = False
        self.lock = False
        self.loop = False
        self.highq = 0
        self.lowq = 0

    def getKeyState(self, message):
        key = key_channel(message)
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

    def set_lowQ(self, lowq):
        self.lowq = lowq
        for ks in self.keys.values():
            ks.set_quantized_period(self.lowq, self.highq)

    def set_lowQ(self, lowq):
        self.lowq = lowq
        for ks in self.keys.values():
            ks.set_quantized_period(self.lowq, self.highq)

    def clearAllTapes(self):
        for ks in self.keys.values():
            ks.tape.clear()

    def turnOffUnheld(self):
        for ks in self.keys.values():
            if ks.on and not ks.held:
                ks.sendOff()

    def update(self, dt):
        for keystate in self.keys.values():
            keystate.update(dt)

    def panic(self):
        self.output.reset()

def inputs(match):
    return [i for i in map(lambda name: create_source(name), filter(lambda name:match in name, mido.get_input_names()))]

def main_loop(inputs, output, config):
    monolith = Sustainer(output)

    def dispatch(message):
        if message.type == 'control_change':
            if message.control == config['sustainCC']:
                if message.value == 127:
                    monolith.sustainOn()
                else:
                    monolith.sustainOff()
            elif message.control == config['lockCC']:
                if message.value == 127:
                    monolith.lockOn()
                else:
                    monolith.lockOff()
            elif message.control == config['loopCC']:
                if message.value == 127:
                    monolith.loopOn()
                else:
                    monolith.loopOff()
            elif message.control == config['lowQCC']:
                monolith.set_lowQ(((message.value-64)/64.0)*4)
            elif message.control == config['highQCC']:
                monolith.set_highQ(((message.value-64)/64.0)*4)
            else:
                output.send(message)
        elif message.type == 'note_on':
            monolith.noteOn(message)
        elif message.type == 'note_off':
            monolith.noteOff(message)
        else:
            output.send(message)

    atime = time.time()
    dt = 0

    while True:
        for input in inputs:
            for m in input.iter_pending():
                dispatch(m)

        monolith.update(dt)

        atime2 = time.time()
        dt = atime2 - atime
        atime = atime2

        time.sleep(0.16)

if __name__=='__main__':
    try:
        inputPortName = sys.argv[1]
        outputPortName = sys.argv[2]
    except IndexError:
        print("must provide input and output device names as args")

    try:
        inputs = inputs(inputPortName)
        sink = create_sink(outputPortName)
    except OSError as err:
        print(err)
        sys.exit(1)

    def signal_handler(signal, frame):
        print("closing ports and exiting")
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)


    main_loop(inputs, sink, {
        'sustainCC':64,
        'lockCC':3,
        'loopCC':2,
        'lowQCC':73,
        'highQCC':75,
    })
