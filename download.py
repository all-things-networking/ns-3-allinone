#! /usr/bin/env python3
import sys
from optparse import OptionParser
import os
import shutil
try:
    import urllib.request
except Exception as e:
    if sys.version_info[0] == 2:
        print("Python 3 required for download.py")
        sys.exit(1)
    else:
        print("Exception %s upon import", e)
        sys.exit(1)
from glob import glob

from util import run_command, fatal, CommandError
import constants
from xml.dom import minidom as dom


def get_ns3(ns3_branch):
    print("""
    #
    # Get NS-3
    #
    """)
    ns3_dir = 'ns-3-dev'
    if ns3_branch != "master":
        ns3_dir = ns3_branch

    if not os.path.exists(ns3_dir):
        if ns3_branch == "master":
            print("Cloning ns-3 development repository")
            run_command(['git', 'clone', constants.NSNAM_CODE_BASE_URL])
        else:
            print("Cloning ns-3 development repository and checking out branch %s" % ns3_branch)
            run_command(['git', 'clone', constants.NSNAM_CODE_BASE_URL, '--branch', ns3_branch, ns3_branch])
    else:
        if ns3_branch == "master":
            print("Updating ns-3 repository")
            run_command(['git', '-C', ns3_dir, 'pull'])
        else:
            print("Suppressing update on existing %s directory containing a non-master branch" % ns3_branch)
            print("Exiting...")
            sys.exit(0)

    return ns3_dir


def get_netanim(ns3_dir):
    print("""
    #
    # Get NetAnim
    #
    """)

    if sys.platform in ['cygwin']:
        print("Architecture (%s) does not support NetAnim... skipping" % (sys.platform))
        raise RuntimeError

    required_netanim_version = None
    # (peek into ns-3 and extract the required netanim version)
    # In ns-3.36 and later, this is maintained in _required_netanim_version.py
    if ns3_dir != 'ns-3-dev':
        # For the recent versions
        try:
            netanim_version_file = open(os.path.join(ns3_dir, "src", "netanim", "_required_netanim_version.py"), "rt")
            for line in netanim_version_file:
                if line.startswith('__required_netanim_version__'):
                    required_netanim_version = eval(line.split('=')[1].strip())
                    netanim_version_file.close()
                    break
        except:
            pass
        if required_netanim_version is None:
            # In ns-3.35 and earlier, this is maintained in wscript 
            try:
                netanim_wscript = open(os.path.join(ns3_dir, "src", "netanim", "wscript"), "rt")
                for line in netanim_wscript:
                    if line.startswith('NETANIM_RELEASE_NAME'):
                        required_netanim_version = eval(line.split('=')[1].strip())
                        netanim_wscript.close()
                        break
            except:
                pass
        if required_netanim_version is None:
            print("Unable to detect NetAnim required version.Skipping download")
            return
        else:
            print("Required NetAnim version: ", required_netanim_version)
        # continue below

    def netanim_clone():
        print("Retrieving NetAnim from " + constants.NETANIM_REPO)
        run_command(['git', 'clone', constants.NETANIM_REPO, constants.LOCAL_NETANIM_PATH])

    def netanim_update():
        print("Pulling NetAnim updates from " + constants.NETANIM_REPO)
        run_command(['git', '-C', constants.LOCAL_NETANIM_PATH, 'pull'])

    def netanim_download():
        local_file = required_netanim_version + ".tar.bz2"
        remote_file_path = required_netanim_version + "/" + "netanim-" + required_netanim_version + ".tar.bz2"
        remote_file = constants.NETANIM_RELEASE_URL + "/" + remote_file_path
        print("Retrieving NetAnim from " + remote_file)
        urllib.request.urlretrieve(remote_file, local_file)
        print("Uncompressing " + local_file)
        run_command(["tar", "-xjf", local_file])
        # the untar will unpack to a directory name prepended with 'netanim-'
        archive_directory_name = "netanim-" + required_netanim_version
        run_command(["mv", archive_directory_name, required_netanim_version])
        print("Create symlink from %s to %s" % (required_netanim_version, constants.LOCAL_NETANIM_PATH))
        os.symlink(required_netanim_version, constants.LOCAL_NETANIM_PATH)
        os.remove(local_file)

    if ns3_dir != 'ns-3-dev':
        netanim_download()
    elif not os.path.exists(constants.LOCAL_NETANIM_PATH):
        netanim_clone()
    else:
        netanim_update()

    return (constants.LOCAL_NETANIM_PATH, required_netanim_version)


def get_bake(ns3_dir):
    print("""
    #
    # Get bake
    #
    """)

    def bake_clone():
        print("Retrieving bake from " + constants.BAKE_REPO)
        run_command(['git', 'clone', constants.BAKE_REPO])

    def bake_update():
        print("Pulling bake updates from " + constants.BAKE_REPO)
        run_command(['git', '-C', 'bake', 'pull'])

    if not os.path.exists('bake'):
        bake_clone()
    else:
        bake_update()


def main():
    parser = OptionParser()
    parser.add_option("-n", "--ns3-branch", dest="ns3_branch", default="master",
                      help="Name of the ns-3 repository", metavar="BRANCH_NAME")
    (options, dummy_args) = parser.parse_args()

    # first of all, change to the directory of the script
    os.chdir(os.path.abspath(os.path.dirname(__file__)))

    # Create the configuration file
    config = dom.getDOMImplementation().createDocument(None, "config", None)


    # -- download NS-3 --
    ns3_dir = get_ns3(options.ns3_branch)

    ns3_config = config.documentElement.appendChild(config.createElement("ns-3"))
    ns3_config.setAttribute("dir", ns3_dir)
    ns3_config.setAttribute("branch", options.ns3_branch)

    # -- download NetAnim --
    try:
        netanim_dir, netanim_version = get_netanim(ns3_dir)
    except (CommandError, IOError, RuntimeError):
        print(" *** Did not fetch NetAnim offline animator. Please visit https://www.nsnam.org/wiki/NetAnim")
    else:
        netanim_config = config.documentElement.appendChild(config.createElement("netanim"))
        netanim_config.setAttribute("dir", netanim_dir)
        netanim_config.setAttribute("version", netanim_version)

    # -- download bake --
    try:
        get_bake(ns3_dir)
    except (CommandError, IOError, RuntimeError):
        print(" *** Did not fetch bake build tool.")
    else:
        bake_config = config.documentElement.appendChild(config.createElement("bake"))
        bake_config.setAttribute("dir", "bake")
        bake_config.setAttribute("version", "bake")

    # write the config to a file
    dot_config = open(".config", "wt")
    config.writexml(dot_config, addindent="    ", newl="\n")
    dot_config.close()

    return 0

if __name__ == '__main__':
    sys.exit(main())
