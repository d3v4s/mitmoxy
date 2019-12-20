#!/bin/env python3

import sys
import json
import bitoxy

from bitoxy.controllers.controller import Controller

helpers = """
Bitoxy {version} -- Proxy Server
Developed by {author}

Usage: {name} start|version|help [option]

Arguments:

    start
        starting a proxy server.

    version
        get the version of Bitoxy.

    help
        show this helps.


Examples:
    {name} start

"""

helpers = helpers.format(name=sys.argv[0], version=bitoxy.__version__, author=bitoxy.__author__)


# function to show help
def show_help():
    print(helpers)
    sys.exit(0)


# function to show Bitoxy version
def show_version():
    print('Bitoxy {version} - Proxy server - Developed by {author}'.
          format(version=bitoxy.__version__, author=bitoxy.__author__))
    sys.exit(0)


# function to execute controller
def exec_controller():
    with open('conf/server.json') as file:
        conf_server = json.load(file)

    with open('conf/log.json') as file:
        conf_log = json.load(file)

    ctrl = Controller(command, conf_server, conf_log)
    ctrl.execute()


# main function
if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('[!!] Bitoxy need a argument')
        print(helpers)
        sys.exit(-1)

    command = sys.argv[1]

    # switcher to show help or version
    # to default execute controller
    switcher = {
        'help': show_help,
        'version': show_version
    }
    exc = switcher.get(command, exec_controller)
    exc()
