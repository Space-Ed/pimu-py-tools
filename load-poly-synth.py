#! /bin/python3

import mido, subprocess, socket, os

# add a poly synth to the mod-host

with s = socket.open(5000):
    s.send('bundle_add <synth_bundle_dir>')
    s.send('add <synth_uri> 1')

# connect to playback 

subprocess(['jack_connect', 'effect_1:out1','system:playback1'])

# send messages from the keylab to the mod-host



