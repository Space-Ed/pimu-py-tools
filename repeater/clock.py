import time

class Clock:
    def __init__(self):
        self.clock_time = time.time()
        self.period = 1
        self.oldp = 1
        self.changed = False

    def tick(self):
        nct = time.time()
        dct = nct - self.clock_time
        self.clock_time = nct
        self.period = 24*dct

        if (abs(self.oldp - self.period)>0.01):
            self.changed = True
            self.oldp = self.period
