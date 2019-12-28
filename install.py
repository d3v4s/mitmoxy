#!/bin/env python3

from shutil import copytree, copy, rmtree

import os
import sys
import json
import mitmoxy
import pkg_resources

# check if is root user
if os.getuid() != 0:
    print("[!!] WTF!!! Are you drunk???")
    print("[!!] This script need root user")
    exit(-1)

# read arg if it passed
command = ""
if len(sys.argv) > 1:
    command = sys.argv[1]

# path to be insert the bash completions
completions_path = '/usr/share/bash-completion/completions'

# installation paths
install_path = "/opt/mitmoxy/{version}".format(version=mitmoxy.__version__)
service_path = '/usr/lib/systemd/system/mitmoxy.service'
symlink_bin = '/usr/bin/mitmoxy'
symlink_etc = '/etc/mitmoxy'


# path used for logs
logs_path = '/var/log/mitmoxy'

# files to be copied
install_files = [
    'conf',
    'mitmoxy',
    'mitmoxy.py',
    'mitmoxy.sh',
    'LICENSE',
    'README.md'
]

# files to be applied 'chmod +x'
exec_files = [
    'mitmoxy.py',
    'mitmoxy.sh',
    'conf/key/ck-gen.sh',
    'conf/key/fake-cert-gen.sh'
]

# read need packages from requirements.txt
file = open('requirements.txt')
req_packages = file.read()
file.close()
req_packages = req_packages.split('\n')
try:
    req_packages.remove('')
except ValueError:
    pass

# help
helpers = """
Usage: {name} [install|remove]
"""


def show_help():
    print(helpers.format(name=sys.argv[0]))


# function to install mitmoxy
def install():
    print("[*] Install starting...")
    try:
        # copy file on installation path
        os.makedirs(install_path)
        for f in install_files:
            to = '/'.join([install_path, f])
            if os.path.isfile(f):
                copy(f, to)
            else:
                copytree(f, to)

        # add execution permission
        for f in exec_files:
            os.system("chmod +x {path}/{file}".format(path=install_path, file=f))

        # change log directory
        path = '/'.join([install_path, 'conf', 'log.json'])
        f = open(path, 'r')
        conf_log = json.load(f)
        f.close()
        conf_log['log-dir'] = logs_path
        json_out = json.dumps(conf_log, sort_keys=True, indent=4, separators=(',', ': '))
        f = open(path, 'w')
        f.write(json_out)
        f.close()

        # create new key
        while 1:
            resp = input('[?] Generate new certificate? (Y/n): ')
            resp = resp.lower()
            if resp == '' or resp == 'y' or resp == 'ye' or resp == 'yes':
                # generate certificate with script
                exc = 'cd %s/conf/key && ./ck-gen.sh' % install_path
                os.system(exc)
                break
            elif resp == 'n' or resp == 'no':
                break

        # add bash complete
        if os.path.isdir(completions_path):
            copy('template/completions/mitmoxy', '%s/%s' % (completions_path, 'mitmoxy'))

        # create logs dir
        if not os.path.exists(logs_path):
            os.makedirs(logs_path)

        print('[*] Files copied')

        # create symbolic link on /usr/bin to mitmoxy
        os.symlink('/'.join([install_path, "mitmoxy.sh"]), symlink_bin)
        # create symlink on /etc/chissy to conf
        os.symlink('%s/%s' % (install_path, 'conf'), symlink_etc)
        print('[*] Symbolic links created')

        # add systemd unit
        service_file = open('template/systemd/mitmoxy.service', 'r')
        chiss_service = service_file.read()
        service_file.close()
        chiss_service = chiss_service.format(
            workdir=install_path,
            version=mitmoxy.__version__
        )
        f = open(service_path, 'w')
        f.write(chiss_service)
        f.close()
        os.system('systemctl daemon-reload')
        print('[*] Systemd unit created')

        # install require packages
        installed_pckgs = pkg_resources.working_set
        installed_pckgs = sorted(["%s" % i.key for i in installed_pckgs])
        for pckg in req_packages:
            if pckg not in installed_pckgs:
                install_package(pckg)

        print('[*] Installation complete')
        print()
        print('[*] Usage: mitmoxy {start|version|help} [options]')
        print('[*] Usage daemon: systemctl {start|stop|restart|status} mitmoxy')
        print()
    except Exception as e:
        print('[!!] Caught a exception while installing. ' + str(e))
        sys.exit(-1)


# function to uninstall mitmoxy
def uninstall():
    print()
    print("[*] Uninstall starting...")
    try:
        # remove service and symlink
        if os.path.exists(service_path):
            os.remove(service_path)
        if os.path.islink(symlink_bin):
            os.remove(symlink_bin)
        if os.path.islink(symlink_etc):
            os.remove(symlink_etc)

        # remove autocomplete
        mitmoxy_compl = '%s/%s' % (completions_path, 'mitmoxy')
        if os.path.exists(mitmoxy_compl):
            os.remove(mitmoxy_compl)

        print('[*] All installation files have been deleted')

        # remove log files
        while 1:
            resp = input('[?] Remove all log files? (y/N): ')
            resp = resp.lower()
            if resp == 'y' or resp == 'ye' or resp == 'yes':
                if os.path.exists(logs_path):
                    rmtree(logs_path)
                    break
            elif resp == "" or resp == "n" or resp == 'no':
                break

        # remove installation path
        rmtree(install_path)
        print("[*] Uninstall complete")
        print()
    except Exception as e:
        print('[!!] Caught a exception while uninstalling. ' + str(e))
        sys.exit(-1)


# function to check if chissy is already installed and install it
def check_install():
    if os.path.isdir(install_path):
        print('[!!] Mitmoxy is already installed')
        while 1:
            resp = input('[?] Do you want to reinstall it? (y/N): ')
            resp = resp.lower()
            if resp == "y" or resp == "ye" or resp == "yes":
                uninstall()
                break
            elif resp == "" or resp == "n" or resp == "no" or resp == "not":
                sys.exit(0)

    # remove service and symlink
    if os.path.exists(service_path):
        os.remove(service_path)
    if os.path.islink(symlink_bin):
        os.remove(symlink_bin)
    if os.path.islink(symlink_etc):
        os.remove(symlink_etc)

    # start install
    install()


# function to check if chissy is already installed
def check_uninstall():
    if os.path.isdir(install_path):
        while 1:
            resp = input('[?] Remove Mitmoxy? (y/N): ')
            resp = resp.lower()
            if resp == "y" or resp == "ye" or resp == "yes":
                uninstall()
                break
            elif resp == "" or resp == "n" or resp == "no":
                sys.exit(0)
    else:
        print()


def install_package(pckg):
    print('[!!] Mitmoxy application need ' + pckg)
    while 1:
        resp = input("[?] Install it now with pip? (Y/n): ")
        resp = resp.lower()
        if resp == '' or resp == 'y' or resp == 'ye' or resp == 'yes':
            if os.path.exists('/usr/bin/pip3'):
                os.system('pip3 install ' + pckg)
            else:
                print('[!!] You don\'t have pip3 installed!!!')
            break
        elif resp == 'n' or resp == 'no':
            break


# main
if __name__ == '__main__':
    switcher = {
        "": check_install,
        "install": check_install,
        "remove": check_uninstall,
        "help": show_help
    }
    func = switcher.get(command, show_help)
    func()
