#!/usr/bin/env python3

# Purpose: ####################################################################
# Show system information with an ASCII art representation of the operating   #
# system logo. Designed to be included in login scripts.                      #
#                                                                             #
###############################################################################

# License: ####################################################################
# This program is free software: you can redistribute it and/or modify it     #
# under the terms of the GNU General Public License as published by the Free  #
# Software Foundation, either version 3 of the License, or (at your option)   #
# any later version.                                                          #
#                                                                             #
# This program is distributed in the hope that it will be useful, but WITHOUT #
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or       #
# FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License for   #
# more details.                                                               #
#                                                                             #
# You should have received a copy of the GNU General Public License along     #
# with this program. If not, see <http://www.gnu.org/licenses/>.              #
#                                                                             #
###############################################################################

# History: ####################################################################
# Based on version 0.30, in turn based on version 0.2.8 - original notes:     #
#   Archey is a system information tool written in Python.                    #
#   Maintained by Melik Manukyan <melik@archlinux.us>                         #
#   ASCII art by Brett Bohnenkamper <kittykatt@silverirc.com>                 #
#   Changes Jerome Launay <jerome@projet-libre.org>                           #
#   Fedora support by YeOK <yeok@henpen.org>                                  #
#   Updates 2016-2023 by Manganar <david@manganar.com> (changelog.md)         #
#                                                                             #
###############################################################################

# TODO: #######################################################################
# None.                                                                       #
#                                                                             #
###############################################################################

# Import libraries ############################################################
import os, sys, re
import psutil                           # Access process information
import glob                             # File wildcard support
import shlex                            # Split with quoted sub-strings
import datetime                         # To allow logging of run time
import tempfile                         # Identify temporary directory
import plistlib                         # Access Apple plist files

from subprocess import Popen, PIPE, DEVNULL, STDOUT
from optparse import OptionParser       # Parse command line arguments
from getpass import getuser
from time import ctime, sleep, perf_counter
from pyparsing import *                 # Allow strip of ANSI sequences
from dotenv import dotenv_values        # Parse environment variable file.
from enum import Enum                   # Enum for distro identification.

# Define the escape sequences used to show colour output. #####################
clear    = '\x1b[0m'
blackN   = '\x1b[0;30m'; blackB   = '\x1b[1;30m'; blackH   = '\x1b[90m'
redN     = '\x1b[0;31m'; redB     = '\x1b[1;31m'; redH     = '\x1b[91m'
greenN   = '\x1b[0;32m'; greenB   = '\x1b[1;32m'; greenH   = '\x1b[92m'
yellowN  = '\x1b[0;33m'; yellowB  = '\x1b[1;33m'; yellowH  = '\x1b[93m'
blueN    = '\x1b[0;34m'; blueB    = '\x1b[1;34m'; blueH    = '\x1b[94m'
magentaN = '\x1b[0;35m'; magentaB = '\x1b[1;35m'; magentaH = '\x1b[95m'
cyanN    = '\x1b[0;36m'; cyanB    = '\x1b[1;36m'; cyanH    = '\x1b[96m'
whiteN   = '\x1b[0;37m'; whiteB   = '\x1b[1;37m'

# Background colours. #########################################################
bgBlack   = "\x1b[40m";  bgRed     = "\x1b[41m";  bgGreen   = "\x1b[42m"
bgYellow  = "\x1b[43m";  bgBlue    = "\x1b[44m";  bgCyan    = "\x1b[46m"
bgWhite   = "\x1b[47m"

# Define Display Contents: Comment/Uncomment to Enable/Disable information. ###
display = [
    'user',                             # Display Username
    'hostname',                         # Display Machine Hostname
    'distro',                           # Display Distribution
    'pimodel',                          # Display the model of Pi
    'kernel',                           # Display Kernel Version
    'uptime',                           # Display System Uptime
    'wm',                               # Display Window Manager
    'de',                               # Display Desktop Environment
    'sh',                               # Display Current Shell
    'term',                             # Display Current Terminal
    'packages',                         # Display No. of Packages Installed
    'resolution',                       # Display Screen Resolution
    'gpu',                              # Display GPU Model
    'cpu',                              # Display CPU Model
    'ram',                              # Display RAM Usage
    'disk'                              # Display Disk Usage
]

# Define an enum to support distro identification. ############################
Distro = Enum("Distro", ['Arch',      'BunsenLabs', 'CrunchBang', 'CentOS',
                        'Debian',     'Elementary', 'Fedora',     'FreeBSD',
                        'Kubuntu',    'Linuxmint',  'MacOS',      'Manjaro',
                        'ManjaroARM', 'Neon',       'PopOS',      'Raspbian',
                        'Ubuntu',     'Zorin',      'Unknown'])

# Dictionary to support mapping distro string ID to the enum ID.
DistroEnumDict = {
    'Arch'            : Distro.Arch,
    'Bunsenlabs'      : Distro.BunsenLabs,
    'Centos'          : Distro.CentOS,
    'CrunchBang'      : Distro.CrunchBang,
    'Debian'          : Distro.Debian,
    'Elementary'      : Distro.Elementary,
    'Fedora'          : Distro.Fedora,
    'Freebsd'         : Distro.FreeBSD,
    'Kubuntu'         : Distro.Kubuntu,
    'Linuxmint'       : Distro.Linuxmint,
    'MacOS'           : Distro.MacOS,
    'Manjaro'         : Distro.Manjaro,
    'Manjaro-ARM'     : Distro.ManjaroARM,
    'Neon'            : Distro.Neon,
    'Pop'             : Distro.PopOS,
    'Raspbian'        : Distro.Raspbian,
    'Ubuntu'          : Distro.Ubuntu,
    'Zorin'           : Distro.Zorin
}

# Dictionary identifying desktop environments based on process names. #########
DesktopEnvironmentProcessDict = {
    'cinnamon'        : 'Cinnamon',
    'dde-dock'        : 'Deepin',
    'fur-box-session' : 'Fur Box',
    'gnome-session'   : 'GNOME',
    'gnome-shell'     : 'GNOME',
    'ksmserver'       : 'KDE',
    'lxqt-session'    : 'LXQt',
    'lxsession'       : 'LXDE',
    'mate-session'    : 'MATE',
    'xfce4-session'   : 'Xfce'
}

# Dictionary identifying desktop environments based on XDG_CURRENT_DESKTOP. ###
DesktopEnvironmentShellVarDict = {
    'X-Cinnamon'      : 'Cinnamon',
    'GNOME'           : 'GNOME',
    'pop:GNOME'       : 'GNOME',
    'ubuntu:GNOME'    : 'GNOME',
    'KDE'             : 'KDE',
    'LXDE'            : 'LXDE',
    'MATE'            : 'MATE',
    'Pantheon'        : 'Pantheon',
    'unity'           : 'Unity',
    'Unity'           : 'Unity',
    'XFCE'            : 'Xfce'
}

# Dictionary defining the color to use for the field labels for each distro. ##
DistroColourDict = {
    Distro.Arch         : blueB,
    Distro.BunsenLabs   : whiteN,
    Distro.CentOS       : blueB,
    Distro.CrunchBang   : whiteN,
    Distro.Debian       : redB,
    Distro.Elementary   : blueB,
    Distro.Fedora       : blueB,
    Distro.FreeBSD      : redB,
    Distro.Kubuntu      : cyanB,
    Distro.Linuxmint    : greenB,
    Distro.MacOS        : yellowN,
    Distro.Manjaro      : greenB,
    Distro.ManjaroARM   : greenB,
    Distro.Neon         : blueB,
    Distro.PopOS        : cyanB,
    Distro.Raspbian     : redB,
    Distro.Ubuntu       : redB,
    Distro.Zorin        : cyanB
}

# Define the dictionary for identifying window managers. ######################
wm_dict = {
    'awesome'         : 'Awesome',
    'beryl'           : 'Beryl',
    'blackbox'        : 'Blackbox',
    'compiz'          : 'Compiz',
    'dwm'             : 'DWM',
    'enlightenment'   : 'Enlightenment',
    'fluxbox'         : 'Fluxbox',
    'fvwm'            : 'FVWM',
    'gnome shell'     : 'Mutter',
    'i3'              : 'i3',
    'icewm'           : 'IceWM',
    'kwin'            : 'KWin',
    'metacity'        : 'Metacity',
    'musca'           : 'Musca',
    'mutter'          : 'Mutter',
    'mutter(gala)'    : 'Gala',
    'mutter (muffin)' : 'mutter (muffin)',    
    'openbox'         : 'Openbox',
    'pekwm'           : 'PekWM',
    'ratpoison'       : 'Rat Poison',
    'scrotwm'         : 'ScrotWM',
    'wmaker'          : 'Window Maker',
    'wmfs'            : 'Wmfs',
    'wmii'            : 'Wmii',
    'xfwm4'           : 'Xfwm',
    'xmonad'          : 'Xmonad'
}

# Dictionary mapping revision code from /proc/cpuinfo to the Pi model (Code, GPU, Model).
# 0002 - 0015 for older Pi models, 2 - 23 for newer models.
RaspberryPiModelDict = {
    "0002" : ["VideoCore IV", "B"],
    "0003" : ["VideoCore IV", "B"],
    "0004" : ["VideoCore IV", "B"],
    "0005" : ["VideoCore IV", "B"],
    "0006" : ["VideoCore IV", "B"],
    "0007" : ["VideoCore IV", "A"],
    "0008" : ["VideoCore IV", "A"],
    "0009" : ["VideoCore IV", "A"],
    "000d" : ["VideoCore IV", "B"],
    "000e" : ["VideoCore IV", "B"],
    "000f" : ["VideoCore IV", "B"],
    "0010" : ["VideoCore IV", "B+"],
    "0011" : ["VideoCore IV", "CM1"],
    "0012" : ["VideoCore IV", "A+"],
    "0013" : ["VideoCore IV", "B+"],
    "0014" : ["VideoCore IV", "CM1"],
    "0015" : ["VideoCore IV", "A+"],
        2  : ['VideoCore IV', "A+"],
        3  : ['VideoCore IV', "B+"],
        4  : ['VideoCore IV', "2B"],
        6  : ['VideoCore IV', "CM1"],
        8  : ['VideoCore IV', "3B"],
        9  : ['VideoCore IV', "Zero"],
       10  : ['VideoCore IV', "CM3"],
       12  : ['VideoCore IV', "Zero W"],
       13  : ['VideoCore IV', "3B+"],
       14  : ['VideoCore IV', "3A+"],
       16  : ['VideoCore IV', "CM3+"],
       17  : ['VideoCore VI', "4B"],
       18  : ['VideoCore IV', "Zero 2 W"],
       19  : ['VideoCore VI', "Pi 400"],
       20  : ['VideoCore VI', "CM4"],
       23  : ['VideoCore VII', "5"]
}

# Define the dictionary for identifying Mac OS version names. #################
MacOSVersion_dict = {
    '10.4'  : 'Mac OS X Tiger',
    '10.5'  : 'Mac OS X Leopard',
    '10.6'  : 'Mac OS X Snow Leopard',
    '10.7'  : 'Mac OS X Lion',
    '10.8'  : 'OS X Mountain Lion',
    '10.9'  : 'OS X Mavericks',
    '10.10' : 'OS X Yosemite',
    '10.11' : 'OS X El Capitan',
    '10.12' : 'macOS Sierra',
    '10.13' : 'macOS High Sierra',
    '10.14' : 'macOS Mojave',
    '10.15' : 'macOS Catalina',
    '10.16' : 'macOS Big Sur',
    '11.0'  : 'macOS Big Sur'
}

# Set up global variables. ####################################################
result = []                     # Results to show.
DistroID = Distro.Unknown       # The distribution we are running on.
DistroTitle = "Unknown"         # The display title of the distribution.
GlobalTerminal = "Unset"        # Variable for "static" terminal ID.

# Define the correct logo for the specified distribution. #####################
def DefineDistroLogo(LogoID):

    if LogoID == Distro.Ubuntu:

        # Ubuntu Logo #################################################################

        DistroLogo     = [f"{redB}               .-/+oossssoo+/-."]
        DistroLogo.append(f"{redB}           `:+ssssssssssssssssss+:`")
        DistroLogo.append(f"{redB}         -+ssssssssssssssssssyyssss+-")
        DistroLogo.append(f"{redB}       .ossssssssssssssssss{whiteB}dMMMNy{redB}sssso.")
        DistroLogo.append(f"{redB}      /sssssssssss{whiteB}hdmmNNmmyNMMMMh{redB}ssssss/")
        DistroLogo.append(f"{redB}     +sssssssss{whiteB}hm{redB}yd{whiteB}MMMMMMMNddddy{redB}ssssssss+")
        DistroLogo.append(f"{redB}    /ssssssss{whiteB}hNMMM{redB}yh{whiteB}hyyyyhmNMMMNh{redB}ssssssss/")
        DistroLogo.append(f"{redB}   .ssssssss{whiteB}dMMMNh{redB}ssssssssss{whiteB}hNMMMd{redB}ssssssss.")
        DistroLogo.append(f"{redB}   +ssss{whiteB}hhhyNMMNy{redB}ssssssssssss{whiteB}yNMMMy{redB}sssssss+")
        DistroLogo.append(f"{redB}   oss{whiteB}yNMMMNyMMh{redB}ssssssssssssss{whiteB}hmmmh{redB}ssssssso")
        DistroLogo.append(f"{redB}   oss{whiteB}yNMMMNyMMh{redB}sssssssssssssshmmmhssssssso")
        DistroLogo.append(f"{redB}   +ssss{whiteB}hhhyNMMNy{redB}ssssssssssss{whiteB}yNMMMy{redB}sssssss+")
        DistroLogo.append(f"{redB}   .ssssssss{whiteB}dMMMNh{redB}ssssssssss{whiteB}hNMMMd{redB}ssssssss.")
        DistroLogo.append(f"{redB}    /ssssssss{whiteB}hNMMM{redB}yh{whiteB}hyyyyhdNMMMNh{redB}ssssssss/")
        DistroLogo.append(f"{redB}     +sssssssss{whiteB}dm{redB}yd{whiteB}MMMMMMMMddddy{redB}ssssssss+")
        DistroLogo.append(f"{redB}      /sssssssssss{whiteB}hdmNNNNmyNMMMMh{redB}ssssss/")
        DistroLogo.append(f"{redB}     .ossssssssssssssssss{whiteB}dMMMNy{redB}sssso.")
        DistroLogo.append(f"{redB}         -+sssssssssssssssss{whiteB}yyy{redB}ssss+-")
        DistroLogo.append(f"{redB}           `:+ssssssssssssssssss+:`")
        DistroLogo.append(f"{redB}               .-/+oossssoo+/-.{clear}")

    elif LogoID == Distro.Arch:

        # Arch Logo ###################################################################

        DistroLogo     = [f"{blueB}                 +"]
        DistroLogo.append(f"{blueB}                 #")
        DistroLogo.append(f"{blueB}                ###")
        DistroLogo.append(f"{blueB}               #####")
        DistroLogo.append(f"{blueB}               ######")
        DistroLogo.append(f"{blueB}              ; #####;")
        DistroLogo.append(f"{blueB}             +##.#####")
        DistroLogo.append(f"{blueB}            +##########")
        DistroLogo.append(f"{blueB}           #############;")
        DistroLogo.append(f"{blueB}          ###############+")
        DistroLogo.append(f"{blueB}         #######   #######")
        DistroLogo.append(f"{blueB}       .######;     ;###;`\".")
        DistroLogo.append(f"{blueB}      .#######;     ;#####.")
        DistroLogo.append(f"{blueB}      #########.   .########`")
        DistroLogo.append(f"{blueB}     ######'           '######")
        DistroLogo.append(f"{blueB}    ;####                 ####;")
        DistroLogo.append(f"{blueB}    ##'                     '##")
        DistroLogo.append(f"{blueB}   #'                         `#{clear}")

    elif LogoID in [Distro.Manjaro, Distro.ManjaroARM]:

        # Manjaro Logo ################################################################

        DistroLogo     = [f"{greenB}   ██████████████████  ████████"]
        DistroLogo.append(f"{greenB}   ██████████████████  ████████")
        DistroLogo.append(f"{greenB}   ██████████████████  ████████")
        DistroLogo.append(f"{greenB}   ██████████████████  ████████")
        DistroLogo.append(f"{greenB}   ████████            ████████")
        DistroLogo.append(f"{greenB}   ████████  ████████  ████████")
        DistroLogo.append(f"{greenB}   ████████  ████████  ████████")
        DistroLogo.append(f"{greenB}   ████████  ████████  ████████")
        DistroLogo.append(f"{greenB}   ████████  ████████  ████████")
        DistroLogo.append(f"{greenB}   ████████  ████████  ████████")
        DistroLogo.append(f"{greenB}   ████████  ████████  ████████")
        DistroLogo.append(f"{greenB}   ████████  ████████  ████████")
        DistroLogo.append(f"{greenB}   ████████  ████████  ████████")
        DistroLogo.append(f"{greenB}   ████████  ████████  ████████{clear}")

    elif LogoID == Distro.Debian:

        # New Version of Debian Logo ##################################################

        DistroLogo     = [f"{whiteB}         _,met$$$$$gg."]
        DistroLogo.append(f"{whiteB}      ,g$$$$$$$$$$$$$$$P.")
        DistroLogo.append(f"{whiteB}    ,g$$P\"     \"\"\"Y$$.\".")
        DistroLogo.append(f"{whiteB}    ,$$P'              `$$$.")
        DistroLogo.append(f"{whiteB}  ',$$P       ,ggs.     `$$b:")
        DistroLogo.append(f"{whiteB}  `d$$'     ,$P\"'   {redB}.{whiteB}    $$$")
        DistroLogo.append(f"{whiteB}   $$P      d$'     {redB},{whiteB}    $$P")
        DistroLogo.append(f"{whiteB}   $$:      $$.   {redB}-{whiteB}    ,d$$'")
        DistroLogo.append(f"{whiteB}   $$;      Y$b._   _,d$P'")
        DistroLogo.append(f"{whiteB}   Y$$.    {redB}`.{whiteB}`\"Y$$$$P\"'")
        DistroLogo.append(f"{whiteB}   `$$b      {redB}\"-.__")
        DistroLogo.append(f"{whiteB}    `Y$$")
        DistroLogo.append(f"{whiteB}     `Y$$.")
        DistroLogo.append(f"{whiteB}       `$$b.")
        DistroLogo.append(f"{whiteB}         `Y$$b.")
        DistroLogo.append(f"{whiteB}            `\"Y$b._")
        DistroLogo.append(f"{whiteB}                `\"\"\"{clear}")

    elif LogoID == Distro.Fedora:

        # Fedora Logo #################################################################

        DistroLogo     = [f"{blueN}             :/------------://"]
        DistroLogo.append(f"{blueN}          :------------------://")
        DistroLogo.append(f"{blueN}        :-----------{whiteB}/shhdhyo/{blueN}-://")
        DistroLogo.append(f"{blueN}      /-----------{whiteB}omMMMNNNMMMd/{blueN}-:/")
        DistroLogo.append(f"{blueN}     :-----------{whiteB}sMMMdo:/{blueN}       -:/")
        DistroLogo.append(f"{blueN}    :-----------{whiteB}:MMMd{blueN}-------    --:/")
        DistroLogo.append(f"{blueN}    /-----------{whiteB}:MMMy{blueN}-------    ---/")
        DistroLogo.append(f"{blueN}   :------    --{whiteB}/+MMMh/{blueN}--        ---:")
        DistroLogo.append(f"{blueN}   :---     {whiteB}oNMMMMMMMMMNho{blueN}     -----:")
        DistroLogo.append(f"{blueN}   :--      {whiteB}+shhhMMMmhhy++{blueN}   ------:")
        DistroLogo.append(f"{blueN}   :-      -----{whiteB}:MMMy{blueN}--------------/")
        DistroLogo.append(f"{blueN}   :-     ------{whiteB}/MMMy{blueN}-------------:")
        DistroLogo.append(f"{blueN}   :-      ----{whiteB}/hMMM+{blueN}------------:")
        DistroLogo.append(f"{blueN}   :--{whiteB}:dMMNdhhdNMMNo{blueN}-----------:")
        DistroLogo.append(f"{blueN}   :---{whiteB}:sdNMMMMNds:{blueN}----------:")
        DistroLogo.append(f"{blueN}   :------{whiteB}:://:{blueN}-----------://")
        DistroLogo.append(f"{blueN}   :--------------------://{clear}")

    elif LogoID == Distro.CrunchBang:

        # CrunchBang Logo #############################################################

        DistroLogo     = [f"{whiteN}                  ___       ___      _"]
        DistroLogo.append(f"{whiteN}                 /  /      /  /     | |")
        DistroLogo.append(f"{whiteN}                /  /      /  /      | |")
        DistroLogo.append(f"{whiteN}               /  /      /  /       | |")
        DistroLogo.append(f"{whiteN}       _______/  /______/  /______  | |")
        DistroLogo.append(f"{whiteN}      /______   _______   _______/  | |")
        DistroLogo.append(f"{whiteN}            /  /      /  /          | |")
        DistroLogo.append(f"{whiteN}           /  /      /  /           | |")
        DistroLogo.append(f"{whiteN}          /  /      /  /            | |")
        DistroLogo.append(f"{whiteN}   ______/  /______/  /______       | |")
        DistroLogo.append(f"{whiteN}  /_____   _______   _______/       | |")
        DistroLogo.append(f"{whiteN}       /  /      /  /               | |")
        DistroLogo.append(f"{whiteN}      /  /      /  /                |_|")
        DistroLogo.append(f"{whiteN}     /  /      /  /                  _ ")
        DistroLogo.append(f"{whiteN}    /  /      /  /                  | |")
        DistroLogo.append(f"{whiteN}   /__/      /__/                   |_|{clear}")

    elif LogoID == Distro.BunsenLabs:

        # BunsenLabs Logo #############################################################

        DistroLogo     = [f"{whiteN}        `++"]
        DistroLogo.append(f"{whiteN}      -yMMs")
        DistroLogo.append(f"{whiteN}    `yMMMMN`")
        DistroLogo.append(f"{whiteN}   -NMMMMMMm.")
        DistroLogo.append(f"{whiteN}  :MMMMMMMMMN-")
        DistroLogo.append(f"{whiteN} .NMMMMMMMMMMM/")
        DistroLogo.append(f"{whiteN} yMMMMMMMMMMMMM/")
        DistroLogo.append(f"{whiteN}`MMMMMMNMMMMMMMN.")
        DistroLogo.append(f"{whiteN}-MMMMN+ /mMMMMMMy")
        DistroLogo.append(f"{whiteN}-MMMm`   `dMMMMMM")
        DistroLogo.append(f"{whiteN}`MMN.     .NMMMMM.")
        DistroLogo.append(f"{whiteN} hMy       yMMMMM`")
        DistroLogo.append(f"{whiteN} -Mo       +MMMMN")
        DistroLogo.append(f"{whiteN}  /o       +MMMMs")
        DistroLogo.append(f"{whiteN}           +MMMN`")
        DistroLogo.append(f"{whiteN}           hMMM:")
        DistroLogo.append(f"{whiteN}          `NMM/")
        DistroLogo.append(f"{whiteN}          +MN:")
        DistroLogo.append(f"{whiteN}          mh.")
        DistroLogo.append(f"{whiteN}         -/{clear}")

    elif LogoID == Distro.Linuxmint:

        # Linux Mint Logo #############################################################

        DistroLogo     = [f"{whiteB}   MMMMMMMMMMMMMMMMMMMMMMMMMmds+."]
        DistroLogo.append(f"{whiteB}   MMm----::-://////////////oymNMd+`")
        DistroLogo.append(f"{whiteB}   MMd      {greenB}/++                {whiteB}-sNMd:")
        DistroLogo.append(f"{whiteB}   MMNso/`  {greenB}dMM    `.::-. .-::.` {whiteB}.hMN:")
        DistroLogo.append(f"{whiteB}   ddddMMh  {greenB}dMM   :hNMNMNhNMNMNh: `{whiteB}NMm")
        DistroLogo.append(f"{whiteB}       NMm  {greenB}dMM  .NMN/-+MMM+-/NMN` {whiteB}dMM")
        DistroLogo.append(f"{whiteB}       NMm  {greenB}dMM  -MMm  `MMM   dMM. {whiteB}dMM")
        DistroLogo.append(f"{whiteB}       NMm  {greenB}dMM  -MMm  `MMM   dMM. {whiteB}dMM")
        DistroLogo.append(f"{whiteB}       NMm  {greenB}dMM  .mmd  `mmm   yMM. {whiteB}dMM")
        DistroLogo.append(f"{whiteB}       NMm  {greenB}dMM`  ..`   ...   ydm. {whiteB}dMM")
        DistroLogo.append(f"{whiteB}       hMM-  {greenB}+MMd/-------...-:sdds {whiteB}MMM")
        DistroLogo.append(f"{whiteB}       -NMm-  {greenB}:hNMNNNmdddddddddy/` {whiteB}dMM")
        DistroLogo.append(f"{whiteB}        -dMNs-``{greenB}-::::-------.``    {whiteB}dMM")
        DistroLogo.append(f"{whiteB}         `/dMNmy+/:-------------:/yMMM")
        DistroLogo.append(f"{whiteB}            ./ydNMMMMMMMMMMMMMMMMMMMMM{clear}")

    elif LogoID == Distro.Raspbian:

        # Raspbian Logo ###############################################################

        DistroLogo     = [f"{greenB}    `.::///+:/-.        --///+//-:``"]
        DistroLogo.append(f"{greenB}   `+oooooooooooo:   `+oooooooooooo:")
        DistroLogo.append(f"{greenB}    /oooo++//ooooo:  ooooo+//+ooooo.")
        DistroLogo.append(f"{greenB}    `+ooooooo:-:oo-  +o+::/ooooooo:")
        DistroLogo.append(f"{greenB}     `:oooooooo+``    `.oooooooo+-")
        DistroLogo.append(f"{greenB}       `:++ooo/.        :+ooo+/.`")
        DistroLogo.append(f"{redB}          ...`  `.----.` ``..")
        DistroLogo.append(f"{redB}       .::::-``:::::::::.`-:::-`")
        DistroLogo.append(f"{redB}      -:::-`   .:::::::-`  `-:::-")
        DistroLogo.append(f"{redB}     `::.  `.--.`  `` `.---.``.::`")
        DistroLogo.append(f"{redB}         .::::::::`  -::::::::` `")
        DistroLogo.append(f"{redB}   .::` .:::::::::- `::::::::::``::.")
        DistroLogo.append(f"{redB}  -:::` ::::::::::.  ::::::::::.`:::-")
        DistroLogo.append(f"{redB}  ::::  -::::::::.   `-::::::::  ::::")
        DistroLogo.append(f"{redB}  -::-   .-:::-.``....``.-::-.   -::-")
        DistroLogo.append(f"{redB}   .. ``       .::::::::.     `..`..")
        DistroLogo.append(f"{redB}     -:::-`   -::::::::::`  .:::::`")
        DistroLogo.append(f"{redB}     :::::::` -::::::::::` :::::::.")
        DistroLogo.append(f"{redB}     .:::::::  -::::::::. ::::::::")
        DistroLogo.append(f"{redB}      `-:::::`   ..--.`   ::::::.")
        DistroLogo.append(f"{redB}        `...`  `...--..`  `...`")
        DistroLogo.append(f"{redB}              .::::::::::")
        DistroLogo.append(f"{redB}               `.-::::-`{clear}")

    elif LogoID == Distro.Zorin:

        # Zorin Logo ##################################################################

        DistroLogo     = [f"{blueN}          `osssssssssssssssssssso`"]
        DistroLogo.append(f"{blueN}         .osssssssssssssssssssssso.")
        DistroLogo.append(f"{blueN}        .+oooooooooooooooooooooooo+.")
        DistroLogo.append(f"{blueN}")
        DistroLogo.append(f"{blueN}")
        DistroLogo.append(f"{blueN}    `::::::::::::::::::::::.         .:`")
        DistroLogo.append(f"{blueN}   `+ssssssssssssssssss+:.`     `.:+ssso`")
        DistroLogo.append(f"{blueN}  .ossssssssssssssso/.       `-+ossssssso.")
        DistroLogo.append(f"{blueN}  ssssssssssssso/-`      `-/osssssssssssss")
        DistroLogo.append(f"{blueN}  .ossssssso/-`      .-/ossssssssssssssso.")
        DistroLogo.append(f"{blueN}   `+sss+:.      `.:+ssssssssssssssssss+`")
        DistroLogo.append(f"{blueN}    `:.         .::::::::::::::::::::::`")
        DistroLogo.append(f"{blueN}")
        DistroLogo.append(f"{blueN}")
        DistroLogo.append(f"{blueN}        .+oooooooooooooooooooooooo+.")
        DistroLogo.append(f"{blueN}         -osssssssssssssssssssssso-")
        DistroLogo.append(f"{blueN}          `osssssssssssssssssssso`{clear}")

    elif LogoID == Distro.Kubuntu:

        # Kubuntu Logo ################################################################

        DistroLogo  = [f"{blueN}             `.:/ossyyyysso/:."]
        DistroLogo.append(f"{blueN}          .:oyyyyyyyyyyyyyyyyyyo:`")
        DistroLogo.append(f"{blueN}        -oyyyyyyyo{whiteB}dMMy{blueN}yyyyyyysyyyyo-")
        DistroLogo.append(f"{blueN}      -syyyyyyyyyy{whiteB}dMMy{blueN}oyyyy{whiteB}dmMMy{blueN}yyyys-")
        DistroLogo.append(f"{blueN}     oyyys{whiteB}dMy{blueN}syyyy{whiteB}dMMMMMMMMMMMMMy{blueN}yyyyyyo")
        DistroLogo.append(f"{blueN}   `oyyyy{whiteB}dMMMMy{blueN}syysoooooo{whiteB}dMMMMy{blueN}yyyyyyyyo`")
        DistroLogo.append(f"{blueN}   oyyyyyy{whiteB}dMMMMy{blueN}yyyyyyyyyyys{whiteB}dMMy{blueN}sssssyyyo")
        DistroLogo.append(f"{blueN}  -yyyyyyyy{whiteB}dMy{blueN}syyyyyyyyyyyyyys{whiteB}dMMMMMy{blueN}syyy-")
        DistroLogo.append(f"{blueN}  oyyyysoo{whiteB}dMy{blueN}yyyyyyyyyyyyyyyyyy{whiteB}dMMMMy{blueN}syyyo")
        DistroLogo.append(f"{blueN}  yyys{whiteB}dMMMMMy{blueN}yyyyyyyyyyyyyyyyyysosyyyyyyyy")
        DistroLogo.append(f"{blueN}  yyys{whiteB}dMMMMMy{blueN}yyyyyyyyyyyyyyyyyyyyyyyyyyyyy")
        DistroLogo.append(f"{blueN}  oyyyyysos{whiteB}dy{blueN}yyyyyyyyyyyyyyyyyy{whiteB}dMMMMy{blueN}syyyo")
        DistroLogo.append(f"{blueN}  -yyyyyyyy{whiteB}dMy{blueN}syyyyyyyyyyyyyys{whiteB}dMMMMMy{blueN}syyy-")
        DistroLogo.append(f"{blueN}   oyyyyyy{whiteB}dMMMy{blueN}syyyyyyyyyyys{whiteB}dMMy{blueN}oyyyoyyyo")
        DistroLogo.append(f"{blueN}   `oyyyy{whiteB}dMMMy{blueN}syyyoooooo{whiteB}dMMMMy{blueN}oyyyyyyyyo")
        DistroLogo.append(f"{blueN}     oyyysyyoyyyys{whiteB}dMMMMMMMMMMMy{blueN}yyyyyyyo")
        DistroLogo.append(f"{blueN}      -syyyyyyyyy{whiteB}dMMMy{blueN}syyy{whiteB}dMMMy{blueN}syyyys-")
        DistroLogo.append(f"{blueN}        -oyyyyyyy{whiteB}dMMy{blueN}yyyyyysosyyyyo-")
        DistroLogo.append(f"{blueN}          ./oyyyyyyyyyyyyyyyyyyo/.")
        DistroLogo.append(f"{blueN}             `.:/oosyyyysso/:.`{clear}")

    elif LogoID == Distro.PopOS:

        # PopOS Logo ##################################################################

        DistroLogo     = [f"{cyanB}               /////////////"]
        DistroLogo.append(f"{cyanB}           /////////////////////")
        DistroLogo.append(f"{cyanB}        ///////{whiteB}*767{cyanB}////////////////")
        DistroLogo.append(f"{cyanB}      //////{whiteB}7676767676*{cyanB}//////////////")
        DistroLogo.append(f"{cyanB}     /////{whiteB}76767{cyanB}//{whiteB}7676767{cyanB}//////////////")
        DistroLogo.append(f"{cyanB}    /////{whiteB}767676{cyanB}///{whiteB}*76767{cyanB}///////////////")
        DistroLogo.append(f"{cyanB}   ///////{whiteB}767676{cyanB}///{whiteB}76767{cyanB}.///{whiteB}7676*{cyanB}///////")
        DistroLogo.append(f"{cyanB}  /////////{whiteB}767676{cyanB}//{whiteB}76767{cyanB}///{whiteB}767676{cyanB}////////")
        DistroLogo.append(f"{cyanB}  //////////{whiteB}76767676767{cyanB}////{whiteB}76767{cyanB}/////////")
        DistroLogo.append(f"{cyanB}  ///////////{whiteB}76767676{cyanB}//////{whiteB}7676{cyanB}//////////")
        DistroLogo.append(f"{cyanB}  ////////////,{whiteB}7676{cyanB},///////{whiteB}767{cyanB}///////////")
        DistroLogo.append(f"{cyanB}  /////////////*{whiteB}7676{cyanB}///////{whiteB}76{cyanB}////////////")
        DistroLogo.append(f"{cyanB}  ///////////////{whiteB}7676{cyanB}////////////////////")
        DistroLogo.append(f"{cyanB}   ///////////////{whiteB}7676{cyanB}///{whiteB}767{cyanB}////////////")
        DistroLogo.append(f"{cyanB}    //////////////////////{whiteB}'{cyanB}////////////")
        DistroLogo.append(f"{cyanB}     //////{whiteB}.7676767676767676767,{cyanB}//////")
        DistroLogo.append(f"{cyanB}      /////{whiteB}767676767676767676767{cyanB}/////")
        DistroLogo.append(f"{cyanB}        ///////////////////////////")
        DistroLogo.append(f"{cyanB}           /////////////////////")
        DistroLogo.append(f"{cyanB}               /////////////{clear}")

    elif LogoID == Distro.MacOS:

        # Mac OS Logo #################################################################

        DistroLogo     = [f"{greenN}                     'c."]
        DistroLogo.append(f"{greenN}                   ,xNMM.")
        DistroLogo.append(f"{greenN}                 .OMMMMo")
        DistroLogo.append(f"{greenN}                 OMMM0,")
        DistroLogo.append(f"{greenN}       .;loddo:' loolloddol;.")
        DistroLogo.append(f"{greenN}     cKMMMMMMMMMMNWMMMMMMMMMM0:")
        DistroLogo.append(f"{yellowN}   .KMMMMMMMMMMMMMMMMMMMMMMMWd.")
        DistroLogo.append(f"{yellowN}   XMMMMMMMMMMMMMMMMMMMMMMMX.")
        DistroLogo.append(f"{redN}  ;MMMMMMMMMMMMMMMMMMMMMMMM:")  
        DistroLogo.append(f"{redN}  :MMMMMMMMMMMMMMMMMMMMMMMM:")
        DistroLogo.append(f"{redN}  .MMMMMMMMMMMMMMMMMMMMMMMMX.")
        DistroLogo.append(f"{redN}   kMMMMMMMMMMMMMMMMMMMMMMMMWd.")
        DistroLogo.append(f"{magentaN}   .XMMMMMMMMMMMMMMMMMMMMMMMMMMk")
        DistroLogo.append(f"{magentaN}    .XMMMMMMMMMMMMMMMMMMMMMMMMK.")
        DistroLogo.append(f"{blueN}      kMMMMMMMMMMMMMMMMMMMMMMd")
        DistroLogo.append(f"{blueN}       ;KMMMMMMMWXXWMMMMMMMk.")
        DistroLogo.append(f"{blueN}         .cooc,.    .,coo:.{clear}")

    elif LogoID == Distro.Neon:

        # KDE Neon Logo ###############################################################

        DistroLogo     = [f"{greenN}               `..---+/---..`"]
        DistroLogo.append(f"{greenN}           `---.``   ``   `.---.`")
        DistroLogo.append(f"{greenN}        .--.`        ``        `-:-.")
        DistroLogo.append(f"{greenN}      `:/:     `.----//----.`     :/-")
        DistroLogo.append(f"{greenN}     .:.    `---`          `--.`    .:`")
        DistroLogo.append(f"{greenN}    .:`   `--`                .:-    `:.")
        DistroLogo.append(f"{greenN}   `/    `:.      `.-::-.`      -:`   `/`")
        DistroLogo.append(f"{greenN}   /.    /.     `:++++++++:`     .:    .:")
        DistroLogo.append(f"{greenN}  `/    .:     `+++++++++++/      /`   `+`")
        DistroLogo.append(f"{greenN}  /+`   --     .++++++++++++`     :.   .+:")
        DistroLogo.append(f"{greenN}  `/    .:     `+++++++++++/      /`   `+`")
        DistroLogo.append(f"{greenN}   /`    /.     `:++++++++:`     .:    .:")
        DistroLogo.append(f"{greenN}   ./    `:.      `.:::-.`      -:`   `/`")
        DistroLogo.append(f"{greenN}    .:`   `--`                .:-    `:.")
        DistroLogo.append(f"{greenN}     .:.    `---`          `--.`    .:`")
        DistroLogo.append(f"{greenN}      `:/:     `.----//----.`     :/-")
        DistroLogo.append(f"{greenN}        .-:.`        ``        `-:-.")
        DistroLogo.append(f"{greenN}           `---.``   ``   `.---.`")
        DistroLogo.append(f"{greenN}               `..---+/---..`{clear}")

    elif LogoID == Distro.Elementary:

        # Elementary OS Logo ##########################################################

        DistroLogo     = [f"{blueN}           eeeeeeeeeeeeeeeee"]
        DistroLogo.append(f"{blueN}        eeeeeeeeeeeeeeeeeeeeeee")
        DistroLogo.append(f"{blueN}      eeeee  eeeeeeeeeeee   eeeee")
        DistroLogo.append(f"{blueN}    eeee   eeeee       eee     eeee")
        DistroLogo.append(f"{blueN}   eeee   eeee          eee     eeee")
        DistroLogo.append(f"{blueN}  eee    eee            eee       eee")
        DistroLogo.append(f"{blueN}  eee   eee            eee        eee")
        DistroLogo.append(f"{blueN}  ee    eee           eeee       eeee")
        DistroLogo.append(f"{blueN}  ee    eee         eeeee      eeeeee")
        DistroLogo.append(f"{blueN}  ee    eee       eeeee      eeeee ee")
        DistroLogo.append(f"{blueN}  eee   eeee   eeeeee      eeeee  eee")
        DistroLogo.append(f"{blueN}  eee    eeeeeeeeee     eeeeee    eee")
        DistroLogo.append(f"{blueN}   eeeeeeeeeeeeeeeeeeeeeeee    eeeee")
        DistroLogo.append(f"{blueN}    eeeeeeee eeeeeeeeeeee      eeee")
        DistroLogo.append(f"{blueN}      eeeee                 eeeee")
        DistroLogo.append(f"{blueN}        eeeeeee         eeeeeee")
        DistroLogo.append(f"{blueN}           eeeeeeeeeeeeeeeee{clear}")

    elif LogoID == Distro.FreeBSD:

        # FreeBSD Logo ################################################################

        DistroLogo     = [f"{redB}              ,        ,"]
        DistroLogo.append(f"{redB}             /(        )`")
        DistroLogo.append(f"{redB}             \ \___   / |")
        DistroLogo.append(f"{redB}             /- {whiteB}_{redB}  `-/  '")
        DistroLogo.append(f"{redB}            ({whiteB}/\/ \{redB} \   /\\")
        DistroLogo.append(f"{whiteB}            / /   |{redB} `    \\")
        DistroLogo.append(f"{blueB}            O O   {whiteB}){redB} /    |")
        DistroLogo.append(f"{whiteB}            `-^--'{redB}`<     '")
        DistroLogo.append(f"{redB}           (_.)  _  )   /")
        DistroLogo.append(f"{redB}            `.___/`    /")
        DistroLogo.append(f"{redB}              `-----' /")
        DistroLogo.append(f"{yellowB} <----.{redB}     __ / __   \\")
        DistroLogo.append(f"{yellowB} <----|===={redB}O))){yellowB}=={redB}) \) /{yellowB}====")
        DistroLogo.append(f"{yellowB} <----'{redB}    `--' `.__,' \\")
        DistroLogo.append(f"{redB}              |        |")
        DistroLogo.append(f"{redB}               \       /      /\\")
        DistroLogo.append(f"{cyanB}         ______{redB}( (_  / \______/")
        DistroLogo.append(f"{cyanB}       ,'  ,-----'   |")
        DistroLogo.append(f"{cyanB}       `--(__________){clear}")

    elif LogoID == Distro.CentOS:

        # FreeBSD Logo ################################################################

        DistroLogo     = [f"{yellowB}                 .."]
        DistroLogo.append(f"{yellowB}               .PLTJ.")
        DistroLogo.append(f"{yellowB}              <><><><>")
        DistroLogo.append(f"{greenB}     KKSSV' 4KKK {yellowB}LJ{magentaB} KKKL.'VSSKK")
        DistroLogo.append(f"{greenB}     KKV' 4KKKKK {yellowB}LJ{magentaB} KKKKAL 'VKK")
        DistroLogo.append(f"{greenB}     V' ' 'VKKKK {yellowB}LJ${magentaB} KKKKV' ' 'V")
        DistroLogo.append(f"{greenB}     .4MA.' 'VKK {yellowB}LJ{magentaB} KKV' '.4Mb.")
        DistroLogo.append(f"{magentaB}   . {greenB}KKKKKA.' 'V {yellowB}LJ{magentaB} V' '.4KKKKK {blueB}.")
        DistroLogo.append(f"{magentaB} .4D {greenB}KKKKKKKA.'' {yellowB}LJ{magentaB} ''.4KKKKKKK {blueB}FA.")
        DistroLogo.append(f"{magentaB}<QDD ++++++++++++  {blueB}++++++++++++ GFD>")
        DistroLogo.append(f"{magentaB} 'VD {blueB}KKKKKKKK'.. {greenB}LJ {yellowB}..'KKKKKKKK {blueB}FV")
        DistroLogo.append(f"{magentaB}   ' {blueB}VKKKKK'. .4 {greenB}LJ {yellowB}K. .'KKKKKV {blueB}'")
        DistroLogo.append(f"{blueB}      'VK'. .4KK {greenB}LJ {yellowB}KKA. .'KV'")
        DistroLogo.append(f"{blueB}     A. . .4KKKK {greenB}LJ {yellowB}KKKKA. . .4")
        DistroLogo.append(f"{blueB}     KKA. 'KKKKK {greenB}LJ {yellowB}KKKKK' .4KK")
        DistroLogo.append(f"{blueB}     KKSSA. VKKK {greenB}LJ {yellowB}KKKV .4SSKK")
        DistroLogo.append(f"{greenB}              <><><><>")
        DistroLogo.append(f"{greenB}               'MKKM'")
        DistroLogo.append(f"{greenB}                 ''{clear}")

    else:

        # Large Tux Logo ##############################################################

        #tuxbg = blackN         # Colour behind Tux.
        tuxbg = clear + blackH  # Colour behind Tux. Clear other colours, set background.
        tuxfg = blackB          # Tux line colour.

        DistroLogo     = [f"{tuxfg}{tuxbg}               ▄█████▄"]
        DistroLogo.append(f"{tuxfg}{tuxbg}              █████████")
        DistroLogo.append(f"{tuxfg}{tuxbg}             {bgWhite}████████▀██{tuxbg}")
        DistroLogo.append(f"{tuxfg}{tuxbg}            {bgWhite}██████████▄██{tuxbg}")
        DistroLogo.append(f"{tuxfg}{tuxbg}            {bgWhite}██▀▀███▀▀████{tuxbg}")
        DistroLogo.append(f"{tuxfg}{tuxbg}            {bgWhite}████ █ ██ ███{tuxbg}")
        DistroLogo.append(f"{tuxfg}{tuxbg}            {bgYellow}█         ████{tuxbg}")
        DistroLogo.append(f"{tuxfg}{tuxbg}            {bgYellow}█       ▄ ████{tuxbg}")
        DistroLogo.append(f"{tuxfg}{tuxbg}            {bgYellow}███▀▀▀▀▀▄{bgWhite}▀████{tuxbg}")
        DistroLogo.append(f"{tuxfg}{tuxbg}            {bgWhite}██▀▀▀▀▀▀   ███{tuxbg}▄")
        DistroLogo.append(f"{tuxfg}{tuxbg}          ▄█{bgWhite}▀          █████{tuxbg}")
        DistroLogo.append(f"{tuxfg}{tuxbg}         {bgWhite}███           ██████{tuxbg}")
        DistroLogo.append(f"{tuxfg}{tuxbg}        {bgWhite}███             ██████{tuxbg}")
        DistroLogo.append(f"{tuxfg}{tuxbg}       {bgWhite}█▀██              ██████{tuxbg}")
        DistroLogo.append(f"{tuxfg}{tuxbg}       {bgWhite}█ █               █ ████{tuxbg}")
        DistroLogo.append(f"{tuxfg}{tuxbg}       {bgWhite}█ █               ██ ███{tuxbg}")
        DistroLogo.append(f"{tuxfg}{tuxbg}      {bgWhite}██ ▀               █▀ ████{tuxbg}")
        DistroLogo.append(f"{tuxfg}{tuxbg}      {bgWhite}███                   ████{tuxbg}")
        DistroLogo.append(f"{tuxfg}{tuxbg}     {bgWhite}█████               ███ ███{tuxbg}")
        DistroLogo.append(f"{tuxfg}{tuxbg}     {bgYellow}█▀▀███{bgWhite}             █████████{tuxbg}")
        DistroLogo.append(f"{tuxfg}{tuxbg}    ▄{bgYellow}█   ███{bgWhite}           █{bgYellow}▀ ████  ▀█{tuxbg}")
        DistroLogo.append(f"{tuxfg}{tuxbg}  ▄█{bgYellow}▀     ████{bgWhite}         █{bgYellow}   ▀     █{tuxbg}")
        DistroLogo.append(f"{tuxfg}{tuxbg} █{bgYellow}         ████{bgWhite}     █  █{bgYellow}         ██{tuxbg}")
        DistroLogo.append(f"{tuxfg}{tuxbg}  █{bgYellow}         ██{bgWhite}       █ █{bgYellow}          ▀█{tuxbg}")
        DistroLogo.append(f"{tuxfg}{tuxbg} █{bgYellow}           █{bgWhite}      █  █{bgYellow}          █{tuxbg}")
        DistroLogo.append(f"{tuxfg}{tuxbg} █{bgYellow}           ███████████{bgYellow}        ▄{tuxbg}▀")
        DistroLogo.append(f"{tuxfg}{tuxbg}  █{bgYellow}▄         █{tuxbg} ▀▀▀▀▀▀▀ █{bgYellow}      ▄{tuxbg}▀")
        DistroLogo.append(f"{tuxfg}{tuxbg}    ▀▀▀▀▀{bgYellow}▄▄▄█{tuxbg}▀         ▀{bgYellow}▄    █{tuxbg}")
        DistroLogo.append(f"{tuxfg}{tuxbg}                         ▀▀▀▀{clear}")

    # Return the logo information as a list. ##################################

    return(DistroLogo)

# Check if a command line tool is installed. ##################################
def CheckCommandInstalled(CommandName):

    WhichOutput = Popen(['which', CommandName], stdout=PIPE).communicate()[0].decode("utf-8").split('\n')

    return ( len(WhichOutput) > 1 )

# Function to run a command and return the first line of output. ##############
def GetCommandOutputList(CommandList):

    if CheckCommandInstalled(CommandList[0]):
        Output = Popen(CommandList, stdout=PIPE, stderr=DEVNULL).communicate()[0].decode("utf-8").split('\n')
    else:
        Output = []

    return Output

# Function to run a command and return the first line of output. ##############
def GetCommandOutput(CommandList):

    if CheckCommandInstalled(CommandList[0]):
        Output = Popen(CommandList, stdout=PIPE, stderr=DEVNULL).communicate()[0].decode("utf-8").split('\n')[0]
    else:
        Output = ""

    return Output

# Function to run a command and count the lines of output. ####################
def CountCommandOutput(CommandList):

    if CheckCommandInstalled(CommandList[0]):
        OutputList = Popen(CommandList, stdout=PIPE).communicate()[0].decode("utf-8").split('\n')
        OutputCount = len(OutputList) - 1
    else:
        OutputCount = 0

    return OutputCount

# Function to print coloured key with normal value. ###########################
def output(key, value):

    if DistroID in DistroColourDict:
        DistroColour = DistroColourDict[DistroID]
    else:
        DistroColour = redB

    result.append(f"{DistroColour}{key}:{clear} {value}")

# Function to identify installed RAM and how much is being used. ##############
def ram_display():

    if DistroID == Distro.MacOS:
        RawRAMInfo = GetCommandOutputList(['sysctl', '-n', 'hw.memsize'])
        RAMInfo = [ "Mem:", str(int(int(RawRAMInfo[0])/1048576)), 0, 0, 0, 0, 0]

        RAMUsedInfo = GetCommandOutputList(['vm_stat'])
        for EachVM_StatItem in RAMUsedInfo:
            WorkingLine = re.sub("\.", "", EachVM_StatItem)     # Remove trailing full stop.
            SplitLine = WorkingLine.split(":")                  # Split at the colon.
            if re.search(" wired", SplitLine[0]):
                VM_Wired = int(SplitLine[1])
            if re.search(" active", SplitLine[0]):
                VM_Active = int(SplitLine[1])
            if re.search(" occupied", SplitLine[0]):
                VM_Compressed = int(SplitLine[1])

        RAMInfo[2] = (VM_Wired + VM_Active + VM_Compressed) * 4 / 1024

    elif DistroID == Distro.FreeBSD:
        MemTotal = int(int(GetCommandOutput(['sysctl', '-n', 'hw.physmem']))  / 1024 / 1024)
        HWPageSize  = int(GetCommandOutput(['sysctl', '-n', 'hw.pagesize']))
        MemInactive = int(GetCommandOutput(['sysctl', '-n', 'vm.stats.vm.v_inactive_count'])) * HWPageSize
        MemUnused   = int(GetCommandOutput(['sysctl', '-n', 'vm.stats.vm.v_free_count'])) * HWPageSize
        MemCache    = int(GetCommandOutput(['sysctl', '-n', 'vm.stats.vm.v_cache_count'])) * HWPageSize
        MemFree     = int((MemInactive + MemUnused + MemCache) / 1024 / 1024)

        RAMInfo = [ "Mem:", MemTotal, MemTotal - MemFree, 0, 0, 0, 0, 0]

    else:
        # Use the free command to gather memory info in mebibytes (1024*1024 bytes)
        RawRAMInfo = GetCommandOutputList(['free', '-m'])

        # Find the line starting with "Mem", split each entry in that line into a list.
        RAMInfo = ''.join(filter(re.compile('Mem').search, RawRAMInfo)).split()

    # Prepare the RAM information for display.
    RAMTotal = int(RAMInfo[1])
    RAMUsed = int(RAMInfo[2])
    RAMUsedPercent = int((RAMUsed / RAMTotal) * 100)

    if RAMUsedPercent >= 80:
        RAMColour = redB
    elif RAMUsedPercent <= 50:
        RAMColour = greenB
    else:
        RAMColour = yellowB

    output('RAM', f"{RAMColour}{RAMUsed} MB {clear}/ {RAMTotal} MB")

# Function to identify the release and architecture. ##########################
def distro_display(): 

    output('OS', DistroTitle)

# Function to identify the kernel version. ####################################
def kernel_display():

    # Don't show the kernel on FreeBSD - it duplicates the distro title.
    if Distro != Distro.FreeBSD:
        # Originally used uname -r, added -sr to improve display on Mac OS.
        kernel = GetCommandOutput(['uname', '-sr'])
        output('Kernel', kernel)

# Function to identify the user name. #########################################
def user_display():

    output('User', getuser())

# Function to identify the hostname. ##########################################
def hostname_display():

    hostname = GetCommandOutput(['uname', '-n'])

    # Remove ".local" from the hostname if present.
    hostname = re.sub('.local', ' ', hostname)

    output('Hostname', hostname)

# Function to identify the CPU. ###############################################
def cpu_display():

    if DistroID == Distro.MacOS:
        PrettyCPUInfo = GetCommandOutput(['sysctl', '-n', 'machdep.cpu.brand_string'])

    elif DistroID == Distro.FreeBSD:
        PrettyCPUInfo = GetCommandOutput(['sysctl', '-n', 'hw.model'])

    elif CheckCommandInstalled("lscpu"):

        TempCPU = GetCommandOutputList(['lscpu'])

        # Set Default Values
        CPUVendorID = ""
        CPUModelName = ""
        RawCPUMaxMhz = ""
        PrettyCPUInfo = ""

        for EachLine in TempCPU:
            if "Vendor ID:" in EachLine:
                CPUVendorID = (EachLine.replace("Vendor ID:", "")).strip()
            elif "Model name:" in EachLine:
                CPUModelName = (EachLine.replace("Model name:", "")).strip()
            elif "CPU max MHz:" in EachLine:
                RawCPUMaxMhz = (EachLine.replace("CPU max MHz:", "")).strip()

        if RawCPUMaxMhz != "":
            # Convert Raw Mhz value into a displayable value.
            NumericCPUMhz = float(RawCPUMaxMhz)

            # Check if less that 1000 and show in Mhz rather than Ghz.
            if NumericCPUMhz < 1000:
                CPUMaxMhz = str(NumericCPUMhz) + " MHz"
            else:
                NumericCPUMhz = round(NumericCPUMhz / 1000, 2)
                CPUMaxMhz = str(NumericCPUMhz) + " GHz"

        else:
            CPUMaxMhz = ""

        # If this is an ARM CPU and ARM is not mentioned in the model name, add it.
        if CPUVendorID == "ARM" and not ("ARM" in CPUModelName):
            PrettyCPUInfo = CPUVendorID + " " + CPUModelName
        elif CPUModelName != "":
            PrettyCPUInfo = CPUModelName

        # If CPU speed identified and not already included in the model name, add it.
        if PrettyCPUInfo != "" and CPUMaxMhz != "" and not ("@" in PrettyCPUInfo):
            PrettyCPUInfo += " @ " + CPUMaxMhz

        if PrettyCPUInfo == "":
            PrettyCPUInfo = "Undetermined"

    else:
        PrettyCPUInfo = "Undetermined (lscpu not available)"

    # Some model names contain multiple spaces. Remove them if present.
    PrettyCPUInfo = re.sub(r' {2,}', ' ', PrettyCPUInfo)

    output('CPU', PrettyCPUInfo)

# Function to identify uptime. ################################################
def uptime_display():

    if DistroID in [Distro.MacOS, Distro.FreeBSD]:
        BootTime = GetCommandOutputList(['sysctl', '-n', 'kern.boottime'])
        BootTime = re.sub('{ sec = ', '', BootTime[0])  # Strip leading characters.
        BootTime = int(BootTime[0:BootTime.find(",")])  # Remove everything after first comma.
        CurrentTime = int(datetime.datetime.timestamp(datetime.datetime.now()))
        fuptime = CurrentTime - BootTime
    else:
        fuptime = int(open('/proc/uptime').read().split('.')[0])

    day = int(fuptime / 86400)
    fuptime = fuptime % 86400
    hour = int(fuptime / 3600)
    fuptime = fuptime % 3600
    minute = int(fuptime / 60)

    uptime = ''
    
    if day == 1:
        uptime += '%d day, ' % day
    else:
        uptime += '%d days, ' % day

    if hour == 1:
        uptime += '%d hour, ' % hour
    else:
        uptime += '%d hours, ' % hour

    if minute == 1:
        uptime += '%d minute.' % minute
    else:
        uptime += '%d minutes.' % minute

    output('Uptime', uptime)

# Function to identify and return the Desktop Environment. ####################
# Used to both identify Ubuntu variants, and called by de_display to 
# populate the output.
def DesktopEvironmentID():

    DesktopEnvironment = "None"

    if DistroID == Distro.MacOS:
        DesktopEnvironment = "Aqua"
    else:
        # Attempt to read the desktop environment from a shell variable.
        DesktopEnvironmentShellVar = os.getenv('XDG_CURRENT_DESKTOP')

        if DesktopEnvironmentShellVar in DesktopEnvironmentShellVarDict:

            # Desktop Environment detected from shell variable, return that.
            DesktopEnvironment = DesktopEnvironmentShellVarDict[DesktopEnvironmentShellVar]

        else:

            # Check the process list for any matching environments
            for proc in psutil.process_iter():

                try:
                    # Get process name & pid from process object.
                    processName = proc.name()

                    # Check the process list for any matching environments
                    for de_id, de_name in DesktopEnvironmentProcessDict.items():
                        if de_id == processName:
                            DesktopEnvironment = de_name
                            break

                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    pass

    return DesktopEnvironment

# Return detailed information on the version of KDE. ##########################
def KDEVersionInfo():

    KDEVersionNumber = os.getenv("KDE_SESSION_VERSION")

    # If the KDE session version is not available, assume version 4.
    if KDEVersionNumber == None:
        KDEVersionNumber = "4"

    KDEVersion = GetCommandOutput(["kded" + KDEVersionNumber, "--version"])
    KDEVersion = re.sub("kded" + KDEVersionNumber + " ", "", KDEVersion)

    PlasmaShellVersion = GetCommandOutput(["plasmashell", "--version"])
    PlasmaShellVersion = re.sub("plasmashell ", "", PlasmaShellVersion)

    PrettyKDEVersion = "KDE"

    if KDEVersion != "":
        PrettyKDEVersion += " " + KDEVersion

    if PlasmaShellVersion != "":
        PrettyKDEVersion = PrettyKDEVersion + " / Plasma " + PlasmaShellVersion

    return PrettyKDEVersion

# Return detailed information on the version of GNOME. ########################
def GNOMEVersionInfo():

    # Read the GNOME shell version.
    GNOMEVersion = GetCommandOutput(["gnome-shell", "--version"]).upper()
    GNOMEVersion = re.sub("GNOME.SHELL ", "", GNOMEVersion)

    # If we could not get the version from gnome-shell, try gnome-session-properties.
    if GNOMEVersion == "":
        GNOMEVersion = GetCommandOutput(["gnome-session-properties", "--version"]).upper()
        GNOMEVersion = re.sub("GNOME-SESSION-PROPERTIES ", "", GNOMEVersion)

    # If neither of the previous methods worked, try gnome-control-center.
    if GNOMEVersion == "":
        GNOMEVersion = GetCommandOutput(["gnome-control-center", "--version"]).upper()
        GNOMEVersion = re.sub("GNOME-CONTROL-CENTER ", "", GNOMEVersion)

    PrettyGNOMEVersion = "GNOME"

    if GNOMEVersion != "":
        PrettyGNOMEVersion += " " + GNOMEVersion

    return PrettyGNOMEVersion

# Function to add the Desktop Environment to the output. ######################
def de_display():

    # Identify the desktop environment.
    DesktopEnvironment = DesktopEvironmentID()

    # If KDE or GNOME, enhance the information with version numbers.
    if DesktopEnvironment == "KDE":
        DesktopEnvironment = KDEVersionInfo()
    elif DesktopEnvironment == "GNOME":
        DesktopEnvironment = GNOMEVersionInfo()

    if DesktopEnvironment != "None":
        output('Desktop Environment', DesktopEnvironment)

# Identify the operating system / distribution ################################
def IdentifyOS():

    # Check if we are running on Mac OS or Linux
    if CheckCommandInstalled('uname'):
        DetectBaseSystem = GetCommandOutput(['uname', '-s'])
    else:
        DetectBaseSystem = "Unknown"

    # Use the base system to determine further details.
    if DetectBaseSystem == "Darwin":

        OSReleaseID = "MacOS"

        with open("/System/Library/CoreServices/SystemVersion.plist","rb") as SystemVersionFile:
            SystemVersionInfo = plistlib.load(SystemVersionFile)
            SystemVersionFile.close()

        OSXVersion = SystemVersionInfo['ProductUserVisibleVersion']
        MinorVersionLocation = OSXVersion.find(".", OSXVersion.find(".") + 1)
        BaseOSXVersion = OSXVersion[:MinorVersionLocation]

        if BaseOSXVersion in MacOSVersion_dict:
            OSReleasePretty = MacOSVersion_dict[BaseOSXVersion] + " (" + OSXVersion + ")"
        else:
            OSReleasePretty = "Mac OS Version " + OSXVersion

    elif DetectBaseSystem in ["Linux", "FreeBSD"]:

        # Check if the os-release file is present.
        OSReleaseFile = os.path.join(os.sep, 'etc', 'os-release')

        if os.path.exists(OSReleaseFile):

            # /etc/os-release file exists, use that to get the distro ID and pretty name.
            OSRelease = dotenv_values(OSReleaseFile)

            if "ID" in OSRelease:
                OSReleaseID = OSRelease['ID'].capitalize()
            else:
                OSReleaseID     = "Undetermined"

            if "PRETTY_NAME" in OSRelease:
                OSReleasePretty = OSRelease['PRETTY_NAME']
            else:
                OSReleasePretty = "Undetermined"

        elif CheckCommandInstalled('lsb_release'):

            # The lsb_release command is installed, use that to get the distro ID and pretty name.
            OSReleaseID = GetCommandOutput(['lsb_release', '-is'])
            OSReleasePretty = GetCommandOutput(['lsb_release', '-ds'])

        else:

            # No method to identify the distro ID was identified, set to defaults.
            OSReleaseID = "Undetermined"
            OSReleasePretty = "Undetermined"

    else:
            OSReleaseID = "Undetermined"
            OSReleasePretty = "Undetermined"

    # Tag the architecture onto the end of the pretty name if possible.
    if CheckCommandInstalled('uname'):
        OSArchitecture = GetCommandOutput(['uname', '-m'])
        OSReleasePretty = OSReleasePretty + " " + OSArchitecture

    # TODO: Check if we have found the required names.

    # Special case for Kubuntu/Ubuntu Studio.
    if OSReleaseID == "Ubuntu" and DesktopEvironmentID() == "KDE":
        OSReleaseID = "Kubuntu"
        OSReleasePretty = "Ku" + OSReleasePretty[1:]

    # Special case: Raspberry Pi OS 64 Bit Reports as Debian. Check if we are on a Raspberry Pi.
    if OSReleaseID == "Debian" and os.path.exists("/proc/device-tree/model"):
        with open('/proc/device-tree/model') as ModelInfoFile:
            ModelInfo = ModelInfoFile.read()
        if "Raspberry Pi" in ModelInfo:
            OSReleaseID = "Raspbian"
            OSReleasePretty = "Rasp" + OSReleasePretty[2:]

    # Convert the string distro ID into an ID value from the Distro enum.
    if OSReleaseID in DistroEnumDict:
        OSEnumID = DistroEnumDict[OSReleaseID]
    else:
        OSEnumID = Distro.Unknown

    return OSReleaseID, OSEnumID, OSReleasePretty

# Function to identify the Window Manager. ####################################
def wm_display():

    # Set a default value
    WindowManager = "Undetermined"

    # Check if we are running on the main console.
    # If so, show that instead of a window manager.
    if CheckCommandInstalled("tty"):
        TTYID = GetCommandOutput(['tty'])
    else:
        TTYID = "Undetermined"

    # tty1 is the main console for linux, ttyv0 is the main console for FreeBSD.
    if TTYID in ["/dev/tty1", "/dev/ttyv0"]:
        WindowManager = "Main Console"
        RawXpropWindowID = ""
    elif IdentifyTerminal() == "sshd":
        WindowManager = "SSH Console"
        RawXpropWindowID = ""
    elif DistroID == Distro.MacOS:
        WindowManager = "Quartz Compositor"
        RawXpropWindowID = ""
    elif CheckCommandInstalled("xprop"):
        # Run xprop to get window information
        RawXpropWindowID = GetCommandOutput(['xprop', '-root', '-notype', '_NET_SUPPORTING_WM_CHECK'])
    else:
        WindowManager = "Undetermined (xprop not installed)"
        RawXpropWindowID = ""

    # Find the window ID
    IndexXpropWindowID = RawXpropWindowID.find("window id # ")
    if IndexXpropWindowID != -1:

        XpropWindowID = RawXpropWindowID[IndexXpropWindowID + 12:]
        RawWindowMgr = GetCommandOutputList(['xprop', '-id', XpropWindowID, '-notype', '-f', '_NET_WM_NAME', '8t'])

        for EachLine in RawWindowMgr:
            # Find the line with "_WM_NAME = ", indicating it contains the window manager.
            IndexWindowMgr = EachLine.find("WM_NAME = ")
            if IndexWindowMgr != -1:
                WindowManager = EachLine[IndexWindowMgr + 10:].lower()
                WindowManager = WindowManager.replace("\"", "")

                # Look up in wm_dict, return the result of that lookup or the raw answer.
                if WindowManager in wm_dict:
                    WindowManager = wm_dict[WindowManager]
                else:
                    WindowManager = WindowManager + " (Not Recognised)"

    # Tag the session type (X11 or Wayland) onto the end of the Window Manager.
    SessionTypeShellVar = os.getenv('XDG_SESSION_TYPE')
    if SessionTypeShellVar != None:
        if SessionTypeShellVar != "tty":
            SessionTypeShellVar = SessionTypeShellVar.capitalize()
        WindowManager = WindowManager + f" ({SessionTypeShellVar})"

    output('Window Manager', WindowManager)

# Function to identify the Shell. #############################################
def sh_display():

    # Read the SHELL environment variable.
    EnvShell = os.getenv("SHELL").split('/')[-1]

    # For Bash, get enhanced output identifying the version.
    if EnvShell == "bash":
        ShellVersion = GetCommandOutputList([EnvShell, '--version'])
    else:
        ShellVersion = []

    # If we have at least one entry in the list, return that.
    if len(ShellVersion) > 0:
        ShellDisplay = ShellVersion[0]
    else:
        ShellDisplay = EnvShell

    output ('Shell', ShellDisplay)

# Function to identify the Terminal. ##########################################
def IdentifyTerminal():

    global GlobalTerminal

    if GlobalTerminal == "Unset":
        # Use ps to find the ID of the grandparent process (the terminal program).
        GrandParentPID = GetCommandOutput(["ps", "-p", str(os.getppid()), "-oppid=" ])
        GrandParentProcess = psutil.Process(int(GrandParentPID))
        GlobalTerminal = GrandParentProcess.name()

    return GlobalTerminal

# Function to read the number of rows and columns for the terminal. ###########
def IdentifyRowsColumns():

    # On some occassions 'ssty size' can return nothing, presumably because there is no terminal open.
    # As a result there is a two step process - read the output, check it isn't empty, then return results.

    CheckResult = []
    CheckResult = os.popen('stty size', 'r').read().split()

    if len(CheckResult) != 2:
        # Did not get a valid return from ssty - set defaults.
        ConsoleRows = 24
        ConsoleColumns = 80
    else:
        # Return values from ssty call.
        ConsoleRows = int(CheckResult[0])
        ConsoleColumns = int(CheckResult[1])

    return ConsoleRows, ConsoleColumns

# Wrapper function for main code to identify the terminal. ####################
def term_display():

    term = IdentifyTerminal()

    output ('Terminal', term)

# Determine the number of appimages installed in Debian based distributions. ##
def DebianAppImagesCount():

    HomeDirName = getuser()

    AppImages =  len(glob.glob('/home/' + HomeDirName + '/.local/bin/*.AppImage'))
    AppImages += len(glob.glob('/home/' + HomeDirName + '/bin/*.AppImage'))
    AppImages += len(glob.glob('/home/' + HomeDirName + '/.bin/*.AppImage'))

    return int(AppImages)

# Function to identify the number of installed packages. ######################
def packages_display():

    if DistroID in [Distro.Ubuntu, Distro.Kubuntu, Distro.Raspbian, Distro.Debian, Distro.CrunchBang, Distro.Linuxmint, 
                    Distro.Zorin, Distro.PopOS, Distro.Elementary]:

        Packages = CountCommandOutput(['dpkg-query', '-W']) # Remove DebianDpkgCount()
        Flatpaks = CountCommandOutput(['flatpak', 'list'])  # Remove DebianFlatpakCount()
        Snaps = CountCommandOutput(['snap', 'list'])        # Remove DebianSnapCount()
        AppImages = DebianAppImagesCount()

        InterimResult = str(Packages) + " (dpkg)"

        if Flatpaks > 0:
            InterimResult += ", " + str(Flatpaks) + " (flatpak)"
            
        if Snaps > 0:
            InterimResult += ", " + str(Snaps) + " (snap)"
            
        if AppImages > 0:
            InterimResult += ", " + str(AppImages) + " (appimaged)"

        output ('Packages', InterimResult)

    elif DistroID in [Distro.Arch, Distro.ManjaroARM, Distro.Manjaro]:

        Packages = CountCommandOutput(['pacman', '-Q'])
        output ('Packages', Packages)

    elif DistroID == Distro.Fedora:

        Packages = CountCommandOutput(['rpm', '-qa'])
        output ('Packages', Packages)

    elif DistroID == Distro.MacOS:

        if CheckCommandInstalled("brew"):
            BrewPackageCount = len(glob.glob('/usr/local/Cellar/*'))

        # MacPorts: https://en.wikipedia.org/wiki/MacPorts; https://www.macports.org/install.php
        if CheckCommandInstalled("port"):
            PortPackageCount = CountCommandOutput(['port', 'installed']) - 1

        if PortPackageCount > 0 and BrewPackageCount > 0:
            packages = str(BrewPackageCount) + " (brew), " + str(PortPackageCount) + " (port)"
        elif BrewPackageCount > 0:
            packages = str(BrewPackageCount) + " (brew)"
        elif PortPackageCount > 0:
            packages = str(PortPackageCount) + " (port)"
        else:
            packages = "No Package Managers Installed"

        output ('Packages', packages)

# Convert capacity in Kb into a string, showing in the appropriate unit. ######
def ConvertDiskSize(DiskSize):

    Megabyte = 1024
    Gigabyte = Megabyte*1024
    Terabyte = Gigabyte*1024

    if DiskSize < Megabyte:
        DisplayDiskValue = str(int(DiskSize))+"K"
    elif DiskSize < Gigabyte:
        DisplayDiskValue = str(int(DiskSize / Megabyte))+"M"
    elif DiskSize < Terabyte:
        DisplayDiskValue = str(int(DiskSize / Gigabyte))+"G"
    else:
        DisplayDiskValue = str(int(DiskSize / Terabyte))+"T"

    return(DisplayDiskValue)

# Function to identify the disk capacity and utilisation. #####################
def disk_display():

    if DistroID == Distro.MacOS:

        RealDisks = []
        DiskOutput = "Not Supported"

        # Get list of drives from the OS. -k uses 1024 byte blocks.
        DriveList = GetCommandOutputList(['df', '-k'])

        # For each real physical disk entry, remove duplicate spaces and split into a list.
        for EachDisk in DriveList:
            if EachDisk[:9] == "/dev/disk":

                while re.search("  ", EachDisk):
                    EachDisk = re.sub("  ", " ", EachDisk)    # Remove multiple spaces.

                RealDisks.append(EachDisk.split(" "))

        # Now have a list of physical disks and their attributes - de-duplicate it.
        if len(RealDisks) == 0:
            DiskOutput = "No disks found"
        else:

            # WARNING: This only works for machines with a single disk.
            # It takes the first entry that is a real disk and shows that.
            # TODO: Could iterate over RealDisks and calculate total for all disks.

            # Read the capacity and available values, converting them to numbers.
            DiskCapacityValue = int(RealDisks[0][1])
            DiskAvailableValue = int(RealDisks[0][3])
            DiskUsedValue = DiskCapacityValue - DiskAvailableValue

            DiskCapacity = ConvertDiskSize(DiskCapacityValue)
            DiskUsed = ConvertDiskSize(DiskUsedValue)

            # Generate output using colour to indicate usage level.
            Usage = (DiskUsedValue / DiskCapacityValue) * 100

            DiskCapacityStatus = greenB
            if Usage > 70:
                DiskCapacityStatus = yellowB
            if Usage >= 90:
                DiskCapacityStatus = redB

            DiskOutput = f"{DiskCapacityStatus}{DiskUsed}{clear} / {DiskCapacity}  ({Usage:.0f}%)"

    elif DistroID == Distro.FreeBSD:

        # There does not appear to be a programmatic way to get free disk space on FreeBSD.
        # Neofetch does not display it either, presumably for this reason.
        DiskOutput = "Unsupported"

    else:
        p1 = Popen(['df', '-Tlh', '--total', '-t', 'ext4', '-t', 'ext3', '-t', 'ext2', '-t', 'reiserfs', '-t', 'jfs', '-t', 'ntfs', '-t', 'fat32', '-t', 'btrfs', '-t', 'fuseblk', '-t', 'xfs'], stdout=PIPE).communicate()[0].decode("utf-8")

        total = p1.splitlines()[-1]
        used = total.split()[3]
        size = total.split()[2]

        scaledSize = float(re.sub("[A-Z]", "", size))
        if size[len(size)-1] == 'T':
            scaledSize = scaledSize * 1024

        scaledUsed = float(re.sub("[A-Z]", "", used))
        if used[len(used)-1] == 'T':
            scaledUsed = scaledUsed * 1024

        usedpercent = scaledUsed / scaledSize * 100

        DiskCapacityStatus = greenB
        if usedpercent > 70 and usedpercent < 90:
            DiskCapacityStatus = yellowB
        if usedpercent >= 90:
            DiskCapacityStatus = redB

        DiskOutput = f"{DiskCapacityStatus}{used}{clear} / {size} ({usedpercent:.0f}%)"

    # If disk space reporting is supported in this distro, add it to the output array.
    if DiskOutput != "Unsupported":
        output ('Disk', DiskOutput)

# Function to identify the screen resolution ##################################
def resolution_display():

    # Set a default value
    Resolution = "Undetermined"

    # Check if we are running on the main console.
    # If so, show resolution as text lines and columns.
    if CheckCommandInstalled("tty"):
        TTYID = GetCommandOutput(['tty'])
    else:
        TTYID = "Undetermined"

    if TTYID in ["/dev/tty1", "/dev/ttyv0"]:
        ConsoleRows, ConsoleColumns = IdentifyRowsColumns()
        Resolution = f"Main Console {ConsoleColumns}x{ConsoleRows}"

    elif IdentifyTerminal() == "sshd":
        ConsoleRows, ConsoleColumns = IdentifyRowsColumns()
        Resolution = f"SSH Console {ConsoleColumns}x{ConsoleRows}"

    elif DistroID == Distro.MacOS:
        if CheckCommandInstalled("screenresolution"):
            # Note that screenresolution get writes to stderr so GetCommandOutputList is not used.
            RawResolution = Popen(['screenresolution', 'get'], stdout=PIPE, stderr=STDOUT).communicate()[0].decode("utf-8").split('\n')
            for ResolutionLine in RawResolution:
                DisplayTextLocation = ResolutionLine.find("Display 0: ")
                if DisplayTextLocation != -1:
                    Resolution = ResolutionLine[DisplayTextLocation + 11:]
                    break

            # If there is an "@" symbol the refresh rate is included - add "Hz" to the end.
            if Resolution.find("@") != -1:
                Resolution = Resolution + "Hz"

        else:
            RawResolution = GetCommandOutputList(['system_profiler', 'SPDisplaysDataType'])
            for ResolutionLine in RawResolution:
                ResolutionTextLocation = ResolutionLine.find("Resolution:")
                if ResolutionTextLocation != -1:
                    Resolution = ResolutionLine[ResolutionTextLocation + 12:]
                    break

    elif CheckCommandInstalled("xrandr"):
        RawResolution = GetCommandOutputList(['xrandr', '--nograb', '--current'])

        for EachLine in RawResolution:
            # Find the line with the asterisk, indicating it is the current active resolution.
            AsteriskLocation = EachLine.find("*")
            if AsteriskLocation != -1:
                ResolutionLine = EachLine[:AsteriskLocation].strip()
                ResolutionLine = ResolutionLine.split(" ")

                try:
                    Frequency = ", " + str(round(float(ResolutionLine[len(ResolutionLine)-1]))) + " Hz"
                except:
                    Frequency = ""

                # Special case (happens on FreeBSD) where frequency returns 0.
                if Frequency == ", 0 Hz":
                    Frequency = ""

                Resolution = f"{ResolutionLine[0]}{Frequency}"

    output ('Resolution', Resolution)

# Function to collate GPU information on FreeBSD. #############################
def FreeBSDGetGPUInfo():

    # Use the pciconf command to read the device information.
    pciconfOutput = GetCommandOutputList(['pciconf', '-lv'])

    # Find the first entry with a class of display.
    DisplayClassIndex = -1
    for ListIndex, EachLine in enumerate(pciconfOutput):
        if "    class      = display" in EachLine:
            DisplayClassIndex = ListIndex
            break

    if DisplayClassIndex < 3:
        GPUInfo = "No Display Information Found"

    else:

        # Set default values.
        GPUDevice = ""
        GPUVendor = ""

        for FindDetails in range(DisplayClassIndex, DisplayClassIndex - 3, -1):
            if "    device     = " in pciconfOutput[FindDetails]:
                GPUDevice = pciconfOutput[FindDetails][18:].strip(" '")

            if "    vendor     = " in pciconfOutput[FindDetails]:
                GPUVendor = pciconfOutput[FindDetails][18:].strip(" '")

        # May have one, both or neither of vendor and device, construct appropriately.
        if GPUVendor == "" and GPUDevice == "":
            GPUInfo = "No Display Information Found"
        elif GPUVendor == "":
            GPUInfo = GPUDevice
        else:
            GPUInfo = GPUVendor + " " + GPUDevice

    return GPUInfo

# Look up the Raspberry Pi GPU using the revision code. #######################
def IdentifyPiGPU():

    # Set default values.
    RawRevisionCode = ""
    PiGPU = "Undetermined"

    # If the cpuinfo file exists, read the revision code from it.
    if os.path.exists('/proc/cpuinfo'):

        with open('/proc/cpuinfo', 'r') as CPUInfoFile:
            CPUInfo = CPUInfoFile.readlines()
        
        for EachLine in CPUInfo:
            if EachLine[0:10] == "Revision\t:":
                RawRevisionCode = EachLine[11:-1]
                break

    # If we have identified a revision code, use that to determine GPU.
    if RawRevisionCode != "":

        RevisionCode   = int(RawRevisionCode, 16)
        RevisionNew    = (RevisionCode >> 23) & 0x1
        RevisionModel  = (RevisionCode >> 4) & 0xff

        if not RevisionNew:
            RevisionModel = RawRevisionCode

        if RevisionModel in RaspberryPiModelDict:
            PiGPU = RaspberryPiModelDict[RevisionModel][0]
        else:
            PiGPU = f"Unrecognised Pi Model {RevisionModel}."

    return PiGPU

# Function to identify the GPU model ##########################################
def gpu_display():

    # Set a default value
    GPU = "Undetermined"

    if DistroID == Distro.MacOS:

        RawGPU = GetCommandOutputList(['system_profiler', 'SPDisplaysDataType'])

        for EachLine in RawGPU:
            LocateMatch = EachLine.find("Chipset Model: ")
            if LocateMatch != -1:
                GPU = EachLine[LocateMatch + 15:]

    elif DistroID == Distro.FreeBSD:

        GPU = FreeBSDGetGPUInfo()

    elif CheckCommandInstalled("lspci"):

        RawGPU = GetCommandOutputList(['lspci', '-m'])

        # Find the line(s) mentioning "Display", "3D" or "VGA".
        for EachLine in RawGPU:
            VGALocation = EachLine.find("VGA")
            DisplayLocation = EachLine.find("Display")
            Location3D = EachLine.find("3D")
            if VGALocation != -1 or DisplayLocation != -1 or Location3D != -1:
                GPULine = shlex.split(EachLine)
                GPU = f"{GPULine[2]}, {GPULine[3]}"

    # If we have not found a GPU at this point, may be running on a Raspberry Pi.
    if GPU == "Undetermined":
        GPU = IdentifyPiGPU()

    output ('GPU', GPU)

# Function to identify the Raspberry Pi model #################################
def pimodel_display():

    # Check if the os-release file is present.
    DeviceTreeFile = os.path.join(os.sep, 'proc', 'device-tree', 'model')

    if os.path.exists(DeviceTreeFile):

        with open(DeviceTreeFile) as ModelInfoFile:
            ModelInfo = ModelInfoFile.read()

        if "Raspberry" in ModelInfo:
            output ('Pi Model', ModelInfo)

# Function to identify length of a string excluding ANSI sequences ############
def ANSILen(ANSIString):

    # Word(nums) is from pyparsing and returns a pyparsing word-regex "W:(0-9)".
    integer = Word(nums)

    # Combine is from pyparsing and concatentates all the elements of the required regex.
    escapeSeq = Combine(Literal('\x1b') + '[' + Optional(delimitedList(integer,';')) + oneOf(list(alphas)))

    # Suppress is from pyparsing eliminates the specified regex from the output.
    NonANSIString = Suppress(escapeSeq).transformString(ANSIString)

    # Return the length of the string without escape sequences, and the length of the escape sequences
    return(len(NonANSIString), len(ANSIString)-len(NonANSIString))

# Left justify a string, taking into account non-printing ANSI sequences. #####
def ANSIljust(ANSIString, MinLength):

    # Get the number of ANSI characters in the string
    Ignore, ANSICount = ANSILen(ANSIString)

    # Pad the string to be MinLength + number of ANSI characters long.
    PaddedANSIString = ANSIString.ljust(MinLength + ANSICount)

    return PaddedANSIString

# Main Program Start ##########################################################

# Identify the distribution and a suitable title for display.
Ignore, DistroID, DistroTitle = IdentifyOS()

# print(f"\n\n[{Ignore}] [{DistroID}] [{DistroTitle}]\n\n")     # Used for new distros.

# Initialise performance log file.
LogFileName = tempfile.gettempdir() + "/" + getuser() + "-archey.log"
with open(LogFileName, "w") as LogFile:
    LogDate = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"Archey Performance Log {LogDate}", file=LogFile)

# Determine the number of terminal columns to allow formatting of the progress messages.
# The sleep avoids issues reading the size too soon after logging in from a mobile device.
sleep(0.2)
IgnoreRows, RawTerminalColumns = IdentifyRowsColumns()
TerminalColumns = RawTerminalColumns - 1

# Run functions found in 'display' array to build the required output.
for EachAttribute in display:

    # Advise user - often too quick to see, but useful on older systems.
    ProgressMessage = f"\rCollating system information: {EachAttribute}...{' ' * TerminalColumns}"
    print(ProgressMessage[:TerminalColumns], end="")

    # Track performance of each function for degbugging purposes.
    PerformanceTrack = perf_counter()

    # For each attribute, generate the function name and then call the function.
    # TODO: Building function names from the dictonary then calling them. Is this acceptable practice?
    FunctionName = EachAttribute + '_display'
    func = locals()[FunctionName]
    func()

    # Calculate and record the performance of each function for degbugging purposes.
    PerformanceTrack = perf_counter() - PerformanceTrack
    with open(LogFileName, "a") as LogFile:
        print(f"{FunctionName}, {PerformanceTrack:.3f}", file=LogFile)

# Add colour bars under the system information.
result.append(f"{redN}▬▬▬▬▬ {greenN}▬▬▬▬▬ {yellowN}▬▬▬▬▬ {blueN}▬▬▬▬▬ {magentaN}▬▬▬▬▬ {cyanN}▬▬▬▬▬{clear}")
result.append(f"{redH}▬▬▬▬▬ {greenH}▬▬▬▬▬ {yellowH}▬▬▬▬▬ {blueH}▬▬▬▬▬ {magentaH}▬▬▬▬▬ {cyanH}▬▬▬▬▬{clear}")

# Clear the progress indicator text before showing the output.
print(f"\r{' ' * TerminalColumns}\r", end="")

# To support logo testing allow DistroID to be overridden from the command line.
if len(sys.argv) == 2:
    LogoOverride = (str(sys.argv[1]))
    # Convert the string distro ID into an ID value from the Distro enum.
    if LogoOverride in DistroEnumDict:
        DistroID = DistroEnumDict[LogoOverride]
    else:
        DistroID = Distro.Unknown

# Merge the logo and result lists. Where terminal is less than 70 columns exclude logo.
ArcheyOutputList = []

if TerminalColumns < 70:
    ArcheyOutputList = result

else:
    LogoOutputList = DefineDistroLogo(DistroID)

    # Ensure lists are same length by padding the result or Logo list.
    ListSizeDiff = len(LogoOutputList) - len(result)

    if ListSizeDiff > 0:
        AdditionalList = [""] * ListSizeDiff
        result.extend(AdditionalList)

    elif ListSizeDiff < 0:
        AdditionalList = [""] * abs(ListSizeDiff)
        LogoOutputList.extend(AdditionalList)

    # Set a minimum width for the logo based on the non-ANSI length.
    MinLogoWidth = 0
    for EachLine in LogoOutputList:
        LenLogoLine, ANSIWidth = ANSILen(EachLine)
        if LenLogoLine > MinLogoWidth:
            MinLogoWidth = LenLogoLine

    for EachLogo, EachData in zip(LogoOutputList, result):
        ArcheyOutputList.append(ANSIljust(EachLogo, MinLogoWidth) + "    " + EachData)

# Print the created output list, truncating to fit the terminal width.

print("")

for EachLine in ArcheyOutputList:
    NonANSILen, ANSIChars = ANSILen(EachLine)
    print(EachLine[:TerminalColumns+ANSIChars])

print("")
