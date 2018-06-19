import time

class TapeEvent:
    def __init__(self, message, tape):
        self.atime = time.time()
        self.ntime = (self.atime - tape.clip_start)/tape.period
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
                canvas[floor(ev.ntime*100)] = '/'
            else:
                canvas[floor(ev.ntime*100)] = '\\'

        canvas[floor(self.npos*100)] = '|'

        return str(self.index) + ":" + "".join(canvas)

    def set_period(self, seconds):
        if(seconds != self.period):
            atime = time.time()
            self.clip_start = atime - ((seconds*(atime-self.clip_start))/self.period)
            self.period = seconds

    def update(self, dt):
        if (dt > self.period): return

        #calculate new cursor position
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
        ntime = next.ntime

        #print("(oldp:%d, ntime:%d, newp:%d)", (oldp, ntime, self.npos))
        while between(oldp, ntime, self.npos):
            if self.keystate.held:
                self.erase_event(next) # when active we are erasing
            else:
                self.playEvent(next)

            if len(self.events) == 0: return# no events to trigger
            self.index = (self.index + 1)%len(self.events)
            next = self.events[self.index]
            oldp = ntime
            ntime = next.ntime

    def insertionPoint(self, ntime):
        thumb = 0
        next = self.events[thumb]

        while next.ntime <= ntime: #find the index of the event after this one
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
        ntime = (time.time() - self.clip_start)/self.period
        index = self.insertionPoint(ntime)%len(self.events)
        next_ev = self.events[index]
        if next_ev.message.type == 'note_on':
            self.erase_event(next_ev)


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
            thumb = self.insertionPoint(event.ntime)

            #insering there inserts before
            self.events.insert(thumb, event)

            # if installed before current scanner head index it is shifted otherwise not
            if thumb < self.index:
                self.index = self.index + 1

    def events_between(self, event1, event2):
        return filter(lambda ev: between(event1.ntime, ev.ntime, event2.ntime), self.events)

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
