#! /usr/bin/python3
import signal
import sys
import mido
from string import Template

def printer(midi_dev_name, max_name_len):
    name_len = len(midi_dev_name)
    return lambda msg: print(midi_dev_name + ':' + ' '*( max_name_len - name_len )+ str(msg))


def open_ports(midi_dev_names):
    longest_name = max([len(name) for name in  midi_dev_names])

    monitored_ports = []
    for midi_dev_name in midi_dev_names:
        open_port = mido.open_input(midi_dev_name)
        open_port.callback = printer(midi_dev_name, longest_name)
        monitored_ports.append(open_port)

    return monitored_ports

def close_ports(monitored_ports):
    for port in monitored_ports:
        port.close()

def setup_prompt():
    def signal_handler(signal, frame):
        print("\nBye")
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    inputs = mido.get_input_names()
    listing_template = Template('$i: $name')
    print('choose input to monitor: \n', "\n".join([listing_template.substitute({'i':i, 'name':inputs[i]}) for i in range(len(inputs))]))
    choice = input("enter indicies: ")
    treated = set([int(index) for index in choice.split() if index.isdigit()])
    setup_monitor(inputs, treated)

def setup_monitor(inputs, selected):
    selected_dev_names = [inputs[x] for x in selected]
    print("showing midi for: \n",  '\n'.join(selected_dev_names))

    monitored = open_ports(selected_dev_names)

    def signal_handler(signal, frame):
        print('Closing connections')
        close_ports(monitored)
        setup_prompt()

    signal.signal(signal.SIGINT, signal_handler)
    signal.pause()

if(__name__=='__main__'):
    setup_prompt()
