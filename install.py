# installer for victron vedirect driver
# Copyright 2018 Matthew Wall

from setup import ExtensionInstaller

def loader():
    return VEDirectInstaller()

class VEDirectInstaller(ExtensionInstaller):
    def __init__(self):
        super(VEDirectInstaller, self).__init__(
            version="0.1",
            name='vedirect',
            description='Collect data from Victron VEDirect devices',
            author="Matthew Wall",
            author_email="mwall@users.sourceforge.net",
            files=[('bin/user', ['bin/user/vedirect.py'])]
            )
