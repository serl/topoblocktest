# TopoBlockTest


**WARNING: the numpy version (1.10.4) used in this project has some known vulnerabilities. Use at your own risk, or upgrade it in `requirements.txt`.**


## Installation

You can choose either to run everything on a virtual machine via Vagrant or run on your own system. In both cases, the deploy will take some time, because of the compilation of some Python dependencies.

The first case should **not** be taken as an option if you're interested on the results, as they'll be biased by the virtualization layer (but it's useful to do little experiments and play around).


### Vagrant
You need [VirtualBox](https://www.virtualbox.org/) and [Vagrant](https://www.vagrantup.com/).

* `vagrant up` will create and configure an Ubuntu Wily virtual machine.
* Then, use `vagrant ssh` to connect to it. During the first login, it will install/compile Python dependencies (go to grab a beer).


### System-wide
You need:

* ethtool, iperf, iostat, tshark: `sudo apt-get install ethtool iperf iperf3 sysstat tshark`
* Python 3.4.x and pyvenv: `python3.4 python3.4-venv python3.4-dev`
* the dependencies for the dependencies
  * scipy: `gfortran libopenblas-dev liblapack-dev`
  * matplotlib: `libpng-dev libfreetype6-dev pkg-config`
  * pyside: `cmake qt4-dev-tools qt4-qmake`
* Open vSwitch ~2.3.0
* Docker ~1.10.2

Configure the environment with `source .env`; it will also install/compile the Python dependencies. Exit the pyvenv (and restart using your good ole Python version) by running `deactivate`.
