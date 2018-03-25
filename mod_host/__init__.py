import re
import subprocess as sub
import socket 
from time import sleep
LV2_BUNDLES = ['/home/pi/lv2plugins']

Errors = {
        -1:     "ERR_INSTANCE_INVALID",
        -2:     "ERR_INSTANCE_ALREADY_EXISTS",
        -3:     "ERR_INSTANCE_NON_EXISTS",
        -4:     "ERR_INSTANCE_UNLICENSED",
        -101:   "ERR_LV2_INVALID_URI",
        -102:   "ERR_LV2_INSTANTIATION",
        -103:   "ERR_LV2_INVALID_PARAM_SYMBOL",
        -104:   "ERR_LV2_INVALID_PRESET_URI",
        -105:   "ERR_LV2_CANT_LOAD_STATE",
        -201:   "ERR_JACK_CLIENT_CREATION",
        -202:   "ERR_JACK_CLIENT_ACTIVATION",
        -203:   "ERR_JACK_CLIENT_DEACTIVATION",
        -204:   "ERR_JACK_PORT_REGISTER",
        -205:   "ERR_JACK_PORT_CONNECTION",
        -206:   "ERR_JACK_PORT_DISCONNECTION",
        -301:   "ERR_ASSIGNMENT_ALREADY_EXISTS",
        -302:   "ERR_ASSIGNMENT_INVALID_OP",
        -303:   "ERR_ASSIGNMENT_LIST_FULL",
        -304:   "ERR_ASSIGNMENT_FAILED",
        -401:   "ERR_CONTROL_CHAIN_UNAVAILABLE",
        -402:   "ERR_LINK_UNAVAILABLE",
        -901:   "ERR_MEMORY_ALLOCATION",
        -902:   "ERR_INVALID_OPERATION"
}

class Plugin:
    def __init__(self, client, index, name):
        self.uri = "https://faustlv2.bitbucket.io/%s"%(name)
        self.client = client
        self.index = index
        self.name = name if not name in client.liveplugins else name+index
        result = self.client.send_command("add %s %d" % (self.uri, index))

    def remove(self):
        self.message('remove', [])

    def message(self, command, args):
        self.client.send_command("%s %d %s" % (command, self.index, " ".join(args)))

    def preset_load(self, preset_uri):
        self.message('preset_load', [preset_uri])

    def preset_save(self, preset_name, file_name):
        self.message('preset_save', [preset_name, file_name])

    def preset_show(self, preset_uri):
        self.message('preset_show', [preset_uri])

    def bypass(self, value):
        self.message('bypass', [value])

    def param_set(self, symbol, value):
        self.message('param_set',[symbol, value])

    def param_get(self, symbol):
        self.message('param_get',[symbol])

    def param_monitor(self, symbol, cond, value):
        self.message('param_monitor',[symbol, cond, value])

    def licencee(self):
        self.message('licencee', [])

    def monitor_output(self, symbol):
        self.message('monitor_output')

    def midi_learn(self, symbol, minimum, maximum):
        self.message('midi_learn', [symbol, minimum, maximum])

    def midi_map(self, symbol, midi_channel, midi_cc, minimum, maximum):
        self.message('midi_map', [midi_channel, midi_cc, minimum, maximum])

    def midi_unmap(self, symbol):
        self.message('midi_unmap', [symbol])

    def cc_map(self, symbol, device_id, actuator_id, label, value, minimum, maximum):
        self.message('cc_map',[symbol, device_id, actuator_id, label, value, minimum, maximum])

    def cc_unmap(self, symbol):
        self.message('cc_map',[symbol])

class Client:

    def __init__(self, port=5000, internal=False):
        if(internal):
            self.spawn_server()

        self.connect_to_server(port)
        self.port = port
        self.plugi = 0
        self.liveplugins = {}
        self.response_re = re.compile(r"resp (\-?\d*)")

    def spawn_server(self):
        self.mod_host_proc = sub.run(['mod-host', '-p','port'])

    def connect_to_server(self, port):
        self.socket = socket.create_connection(('localhost', port))

    def list_plugins(self):
        sub.run(['lv2ls', '-n'], shell=True).stdout

    def send_command(self, command):
        print("sending ", command)
        self.socket.send(bytes(command, 'utf-8'))
        resp = self.socket.recv(1024).decode()
        m = self.response_re.match(resp)

        if (m is None):
            raise Exception("unknown response: "+resp)
        else:
            code = int(m.groups(0)[0])
            if code in Errors:
                raise Exception(Errors[code])
        return resp

    def disconnect(self):
        for (k,v) in self.liveplugins.items():
            v.remove()

        self.socket.close()

    def add_bundle(self, path):
        return self.send_command("bundle_add %s" % (path)) 

    def add_plugin(self, name):
        plugin = Plugin(self, self.plugi, name)
        self.liveplugins[plugin.name] = plugin
        self.plugi = self.plugi+1

    def rm_bundle(self, path):
        self.send_command("bundle_remove %s"%(path))


if __name__== '__main__':
    client = Client(5000)
    resp = client.add_bundle("/home/pi/lv2plugins/faust.lv2")
    print("bundle add get: ", resp)
   
    sleep(2)

    violin = client.add_plugin("clarinet")
    print("add plugin response: ")

    client.rm_bundle("/home/pi/lv2plugins/faust.lv2")

    client.disconnect()


