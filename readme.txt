weewx-vedirect

This is a driver for weewx that collects data from Victron devices such as the
MPPT using the VEDirect interface.

Installation

0) install weewx (see the weewx user guide)

1) download the driver

wget -O weewx-vedirect.zip https://github.com/matthewwall/weewx-vedirect/archive/master.zip

2) install the driver

wee_extension --install weewx-vedirect.zip

3) configure the driver

wee_config --reconfigure

4) start weewx

sudo /etc/init.d/weewx start
