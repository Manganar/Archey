Dependencies: ###############################################################
Uses Python library psutil to list process.
Uses Python library pyparsing to support removal of ANSI codes.
Uses Python library dotenv to parse the /etc/os-release file
Uses xprop:
  sudo apt install x11-utils
Uses xrandr to identify the screen resolution:
  sudo apt-get install x11-xserver-utils
Fedora needs extra packages installed for distro and resolution detection:
  sudo dnf install redhat-lsb-core xrandr

Notes: ######################################################################
Useful command when checking CPU: lscpu | grep 'Model name\|Vendor ID'

Raspberry Pi Information ####################################################
BCM2835   (VideoCore IV): Pi 1 Models A, A+, B, B+, Zero, Zero W and CM1.
BCM2836   (VideoCore IV): Pi 2 Models B.
BCM2837   (VideoCore IV): Pi 3 Models B, later Pi 2 Model B and CM3.
BCM2837B0 (VideoCore IV): Pi 3 Models A+, B+ and CM3+.
BCM2711   (VideoCore VI): Pi 4 Models B, 400 and CM4.
To identify the RAM on a Raspberry Pi, use this in the revision decoding:
  RevisionMemory = ( (RevisionCode >> 20) & 0x7 ) - 1

Updates by Manganar: ########################################################

Jan-24:   Changed Distro ID to be a number rather than text using an enum.
          Arch: Confirmed support and updated installer.
          Added support for BunsenLabs.
          Did not add support for CrunchBang++ as it identifies as Debian.
          Added window manager details for Linux Mint Cinnamon.

Dec-23:   Changed code for Raspberry Pi GPU detection to be more robust.
          Added spaces to the start of old logo and switched the unknown
          logo to the large Tux one.
          Extracted change history into a separate file (changelog.md).
          Added support for CentOS.

Sep-23:   Added spaces to start of Debian logo, removed old Debian logo.
          In progress: enum created for distro identification...

Aug-23:   Added new Debian logo.
          Enhanced Desktop Environment to show versions for KDE and GNOME.
          Enhanced CPU display to include maximum speed in MHz / GHz, and
          to display ARM models properly.

Jul-23:   Added colour bars under the system information.                  
          Extensive changes to the logo structures and display code:       
          converted logo function to generate list using format strings.   
          modified display code to auto pad the logo width.                
          Tidied up the free disk space function.                          
          Added session type (X11/Wayland/TTY) to window manager display.  
          Simplified output loop removing iteration on ANSILen/truncation. 
          Added a short sleep before reading the terminal size. This is to 
          address issues when reading the size too soon after logging in   
          from a mobile device.                                            

May-23:   Completed FreeBSD support (not able to support disk usage)       
          Expanded use of GetCommandOutput/OutputList across all areas.               

Apr-23:   Improved detection of the distro, pretty name and architecture by
          using the /etc/os-release file where possible.                   
          Tidied up the tab/space in the display dictionary.               
          Created a new function (CountCommandOutput) to remove repeated   
          code used to run a command and count the lines of output. Stopped
          piping to wc and used the length of the resulting list.          
          Changed desktop environment detection (DesktopEvironmentID) to   
          use the XDG_CURRENT_DESKTOP environment variable if present.     
          Simplified the output function to determine colour by using a    
          dictionary rather than repeating code.                           
          Simplified the ram_display function.                             
          Simplified packages_display using the CountCommandOutput function
          Added incomplete FreeBSD support.                                

Mar-23:   Updated CPU detection on Raspberry Pi (same as Manjaro-ARM)      
          Added code to round the display frequency value to a whole number
          Modified CheckCommandInstalled to use the returncode which is    
          simpler and works on Mac and Linux.                              
          Added support for Elementary OS, Fedora and Manjaro              
          Updated CPU detection to use lscpu by default.                   
          Updated GPU detection to allow RPi to work with multiple OS.     

Jan-23:   Moved logo setup to a function and modified display section to   
          accommodate this. Updated display to not show logo when terminal 
          is less than 70 columns wide.                                    

Dec-22:   Added support for MacOS                                          

Feb-22:   Added support for Raspberry Pi 64 Bit reporting as Debian        

Jan-22:   Enhanced comment block                                           
          Enhanced installer to include dependencies                       
          Removed screenshot capability and dependency on scrot            

Dec-21:   Added support for Pop!_OS                                        
          Modified to truncate output to fit terminal width.               

Aug-21:   Corrected hard coded home directory when searching for appimages 
          Added Kubuntu (as Debian) for the package number display.        
          Formated remaining display sections to move them to multi-line.  

Jul-21:   Adding support for Manjaro-ARM                                   

Jun-21:   Modified to use user specific log file name to avoid permission  
          issues for multiple user logins (e.g. on manganar)               

May-21:   Modified to detect Ubuntu Studio using OS and Window Manager     
          Added Kubuntu logo.                                              
          Moved stty size check to function and check for null return.     

Apr-21:   Modified to write logfile to the system temporary folder.        
          Added support for Zorin OS                                       

Mar-21:   Re-enabled a range of attributes to display, and added some based
          Neofetch capabilities. Improved ASCII art for Pi & Ubuntu Logos. 
          Added a progress indicator as it parses the required data, and   
          logging of how long it takes for each data collection function.  
          Modified resolution and desktop environment functions to not use 
          X to determine values if running through SSH.                    

Jul-20:   Restuctured and moved to Python 3.                               
          Removed process based method for display manager & window manager
          identification as they no longer appear to work.                 
          Consider alternatives.                                           

Aug-16:   Added support for Raspbian.                                      
          Corrected the overly complex memory calculation,which gave a     
          negative figure on Ubuntu.                                       
          For CPU, model is in file[4] of /proc/cpuinfo in most cases.     
          For Raspbian, it is in file[1]. Added a condition to correct.    
          Requested disk space in human readable form, then ignored units. 
          Treats tera- as gigabytes. Changed to multiply by 1024 if needed.
