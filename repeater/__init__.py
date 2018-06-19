import time
import mido
import sys
import signal
import re
from types import FunctionType
import repeater
import clock

class TransportControl:
    def __init__(self, config, output):
        self.preload = 15
        self.config = config
        self.output = output
        self.loads = {}

        for key, (off_msg, on_msg, load) in config['inputs'].items():
            d = self.loads.setdefault(load, dict())
            d[on_msg] = (key, True)
            d[off_msg] = (key, False)

    def interpret(self, message):
        if (message.control == self.config['load_cc']):
            self.preload = message.value
        elif(message.control == self.config['control']):
            key, is_on = self.loads[self.preload][message.value]

            key_opt = self.config['output'][key]
            if (type(key_opt) == FunctionType):
                key_opt(self.output)
            else:
                channel, note = key_opt
                self.output.send(mido.Message('note_on' if is_on else 'note_off', channel=channel, note=note))


def open_inputs(inpd):
    available = mido.get_input_names()
    prep = dict()

    for k, name in inpd.items():
        regex = re.compile(name)
        matching = tuple(filter(regex.search, available))

        if len(matching) == 1:
            prep[k] = mido.open_input(matching[0])
        elif len(matching) > 1:
            raise ValueError("Multiple inputs matching %s"%(name))
        else:
            raise ValueError("No input midi device matching %s"%(name))

    return prep

def open_output(name):
    available = mido.get_output_names()
    regex = re.compile(name)
    matching = [i for i in filter(regex.search, available)]

    if len(matching) == 1:
        return mido.open_output(matching[0])
    elif len(matching) > 1:
        raise ValueError("Multiple outputs matching %s"%(name))
    else:
        raise ValueError("No output midi device matching %s"%(name))

def main_loop(config):
    inputs = open_inputs(config['inputs'])
    output = open_output(config['output'])

    monolith = repeater.Repeater(output)
    clk = clock.Clock()
    transport = TransportControl(config['transport'], output)

    def dispatch(source, message):
        if source == 'um' and message.type == 'clock':
            clk.tick()
            monolith.set_unit_period(clk.period)
            output.send(message)

        if source == 'keylab-main':
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
                    monolith.set_lowQ(((message.value-64)/64.0)*config['lowQlimit'])
                elif message.control == config['highQCC']:
                    monolith.set_highQ(((message.value-64)/64.0)*config['highQlimit'])
                else:
                    output.send(message)
            elif message.type == 'note_on':
                monolith.noteOn(message)
            elif message.type == 'note_off':
                monolith.noteOff(message)
            else:
                output.send(message)
        if source == 'keylab-meta':
            transport.interpret(message)

    atime = time.time()
    dt = 0

    while True:
        for (key, input) in inputs.items():
            for m in input.iter_pending():
                dispatch(key, m)

        monolith.update(dt)

        atime2 = time.time()
        dt = atime2 - atime
        atime = atime2

        time.sleep(0.016)

if __name__=='__main__':

    def signal_handler(signal, frame):
        print("closing ports and exiting")
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)

    main_loop({
        'output': r'^Deluge.*0$',
        'inputs':{
            'um':r'^UM-1.*0$',
            'keylab-main':r'^Arturia.*:0$',
            'keylab-meta':r'^Arturia.*:1$',
        },
        'sustainCC':64,
        'lockCC':3,
        'loopCC':2,
        'lowQCC':74,
        'highQCC':71,
        'lowQlimit':4,
        'highQlimit':4,
        'transport':{
            'control':47,
            'load_cc':15,
            'inputs':{
                'loop':(3, 67, 15),
                'left':(1, 65, 14),
                'right':(2, 66, 14),
                'stop' :(3, 67, 14),
                'play' :(4, 68, 14),
                'rec'  :(5, 69, 14),
                'save' :(7, 71, 8),
                'punch':(4,68,  15),
                'undo':(3, 67, 8)
            },
            'output':{
                'loop':(15, 0),
                'left':(15, 1),
                'right':(15, 2),
                'stop':lambda port: port.panic(),
                'play':(15, 4),
                'rec':(15, 5),
                'save':(15, 6),
                'punch':(15, 7),
                'undo':(15, 8)
            }
        }
    })
