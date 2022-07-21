weewx-vedirect
Copyright 2018-2022 Matthew Wall

This is a driver for weewx that collects data from Victron devices such as the
MPPT using the VEDirect interface.

Installation

0) install weewx (see the weewx user guide)

1) install the driver

wee_extension --install https://github.com/matthewwall/weewx-vedirect/archive/master.zip

2) configure the driver

wee_config --reconfigure

3) start weewx

sudo /etc/init.d/weewx start
