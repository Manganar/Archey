#!/bin/bash

# Purpose: ####################################################################
# Install a home-grown script (usually Python) that may require an icon and a #
# desktop launcher file in the appropriate system directories.                # 
# Installation locations can be:                                              #
#   Icon in /usr/share/icons                                                  #
#   Desktop file in /usr/share/applications                                   #
#   Script file in /opt/manganar                                              #
#   Startup scripts for command line utilities in /usr/local/bin              #
#                                                                             #
# Manganar's Python scripts often look for their icon in the same             #
# folder they were installed in. In that case, the desktop file               #
# should refer to the icon in that location, and the locations for            #
# the files would be:                                                         #
#   Icon in /usr/share/icons                                                  #
#   Desktop file in /usr/share/applications                                   #
#   Script file in /opt/manganar                                              #
#                                                                             #
# In this specific case, to install Archey to /usr/bin, confirming            #
# installation & dependencies.                                                #
###############################################################################
# History:                                                                    #
# 
# Updates by Manganar: ########################################################
# May-23:   Updated pip install commands.                                     #
#           Updated apt based distros to use apt packages for python elements #
# Apr-23:   Updated with dependency on python-dotenv                          #
# Mar-23:   Support install on KDE Neon, new code to detect package manager.  #
# Dec-22:   Support Mac OS.                                                   #
# Aug-22:   Updated to use bash-includes.                                     #
# May-22:   Support multiple distributions.                                   #
# Jan-22:   Check for required dependencies.                                  #
# Aug-21:   Initial version (1.0) developed.                                  #
###############################################################################

# Dependencies: ###############################################################
# Assumes that terminal colour codes are supported.                           #
# Fedora may need an extra package installed for distro detection:            #
#   sudo dnf install redhat-lsb-core                                          #
###############################################################################

# Notes: ######################################################################
# None.                                                                       #
###############################################################################

# Include standard functions. #################################################
if [ ! -f /opt/manganar/bash-includes.sh ]; then
        echo "ERROR: bash-includes missing, exiting..."
        exit 999
fi
source /opt/manganar/bash-includes.sh

# Main code start #############################################################

colEcho $greenB "\nInstaller Script for Archey - V1.91 January 2024\n"

# Ensure we are running with the required privileges to install files.
CheckElevated

# Identify the Linux distro we are running on - exit if not supported.
CheckLinuxDistro

# Install the script.
if [ "$DetectDistro" = "MacOS" ]; then
    InstallFileAs archey.py /opt/local/bin archey
    chmod og+rx /opt/local/bin/archey
else
    InstallFileAs archey.py /usr/bin archey
fi

# Check dependencies are installed ############################################

colEcho $greenB "\nChecking that dependencies are met..."

# Identify package manager based on distribution.
case "$DetectDistro" in
    Ubuntu|Raspbian|Pop|Debian|Linuxmint|Kubuntu)   PackageManager="apt";;
    CrunchBang|Bunsenlabs|Zorin|Neon|Elementary)    PackageManager="apt";;
    Arch|Manjaro-ARM|ManjaroLinux)                  PackageManager="pacman";;
    Fedora)                                         PackageManager="dnf";;
    MacOS)                                          PackageManager="brew";;
    CentOS)                                         PackageManager="yum";;
    *)                                              PackageManager="unknown";;
esac

if [ "$PackageManager" == "apt" ]; then

    DebianCheckPackageInstalled "python3-psutil" "sudo apt install python3-psutil"
    DebianCheckPackageInstalled "python3-pyparsing" "sudo apt install python3-pyparsing"
    DebianCheckPackageInstalled "python3-dotenv" "sudo apt install python3-dotenv"
    DebianCheckPackageInstalled "x11-utils" "sudo apt install x11-utils"
    DebianCheckPackageInstalled "x11-xserver-utils" "sudo apt install x11-xserver-utils"

elif [ "$PackageManager" = "dnf" ]; then

    # If python3-pip is installed, confirm the required python modules are installed.
    FedoraCheckPackageInstalled "python3-pip" "sudo dnf install python3-pip"
    if [ "$?" = "0" ]; then
        CheckPipPackageInstalled "psutil" "pip install psutil"
        CheckPipPackageInstalled "pyparsing" "pip install pyparsing"
        CheckPipPackageInstalled "python-dotenv" "pip install python-dotenv"
    else
        colEcho $redB "python3 pip not installed - unable to check if python modules are installed."
    fi

    FedoraCheckPackageInstalled "xprop" "sudo dnf install xprop"
    FedoraCheckPackageInstalled "xrandr" "sudo dnf install xrandr"

elif [ "$PackageManager" = "pacman" ]; then

    ArchCheckPackageInstalled "which" "sudo pacman -S which"
    ArchCheckPackageInstalled "python-psutil" "sudo pacman -S python-psutil"
    ArchCheckPackageInstalled "python-pyparsing" "sudo pacman -S python-pyparsing"
    ArchCheckPackageInstalled "python-dotenv" "sudo pacman -S python-dotenv"
    ArchCheckPackageInstalled "x11-utils" "sudo pacman -S x11-utils"
    ArchCheckPackageInstalled "x11-xserver-utils" "sudo pacman -S x11-xserver-utils"

elif [ "$PackageManager" = "brew" ]; then

    colEcho $cyanB "Dependencies must be checked manually on Mac OS."

elif [ "$PackageManager" = "yum" ]; then

    CentOSCheckPackageInstalled "python3-psutil" "sudo yum install python3-psutil"
    CentOSCheckPackageInstalled "python3-pyparsing" "sudo yum install python3-pyparsing"
    CentOSCheckPackageInstalled "python3-dotenv" "sudo yum install python3-dotenv"
    CentOSCheckPackageInstalled "xorg-x11-utils" "sudo yum install xorg-x11-utils"
    CentOSCheckPackageInstalled "xorg-x11-server-utils" "sudo yum install xorg-x11-server-utils"

else

    # Unsupported distribution.
    colEcho $redB "Unsupported distribution $whiteB$DetectDistro$redB detected - aborting..."
    exit 5

fi

colEcho $greenB "Installation process complete."

exit
