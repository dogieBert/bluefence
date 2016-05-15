'''Bluefence module including the connection services'''
#!/usr/bin/python

import os
import argparse
import time
import bluetooth

# Parse the args from command line
parser = argparse.ArgumentParser(description='Bluefence utility')
parser.add_argument('-v', '--verbose', help='Display verbose help', action="store_true")
parser.add_argument('--delay', metavar='SECONDS', type=int, default=5,
                    help='Time between two scans')
parser.add_argument('--cmd', metavar='COMMAND', type=str,
                    default='dbus-send --type=method_call --dest=org.gnome.ScreenSaver /org/gnome/ScreenSaver org.gnome.ScreenSaver.Lock',
                    help='Time between two scans')
parser.add_argument('--missed', metavar='NUMBER', type=int, default=3,
                    help='Number of missed scans to trigger lock')
parser.add_argument('-w', '--wait', action="store_true",
                    help='Disables the need for your device to be connected initially')
parser.add_argument('-o', '--once', action="store_true",
                    help='Only fires the command once')
parser.add_argument('-d', '--distance', type=int,
                    help='Querry the distance. Devices needs to be connected')
parser.add_argument('ADDR', help='Identifier needed')
args = parser.parse_args()

class Connection(object):
    '''Connection Abstract Class'''
    debug = False
    btAddr = ''
    status = ''
    away_counter = 0
    missed = 0

    def execute(self):
        ''' Execute the Command on gone'''
        if args.once is not None:
            if self.status == 'gone' and self.away_counter == 0:
                os.system(args.cmd)
            elif self.status == 'gone':
                os.system(args.cmd)

    def measure(self):
        ''' interface '''
        pass

    def logs(self):
        ''' interface '''
        pass

    def evaluate(self):
        ''' interface '''
        pass

class DistanceService(Connection):
    '''Service if distance mode is enabled'''
    def __init__(self, btAddr, debug):
        self.debug = debug
        self.distance = 0
        if self.debug:
            print('\033[92m[STATUS]\033[0m', 'Using distance mode')
        self.bluetooth_addr = btAddr

    # Taken and modified from blueproximity.py
    def measure(self):
        '''Using the hcitool which needs the device to be connected'''
        rssi = os.popen("hcitool rssi " + self.bluetooth_addr + " 2>/dev/null").readlines()
        # Check if there is a result otherwise the device is not connected
        if rssi == []:
            self.distance = -255
            if self.debug:
                print('\033[91m[ERROR]\033[0m Device is not connected')
        # Extract the rssi and use it as an indicator for the distance
        else:
            self.distance = int(rssi[0].split(':')[1].strip(' '))

    def logs(self):
        '''Logs the current status'''
        if self.debug:
            print('\033[92m[STATUS]\033[0m', 'Device is', self.status,
                  'for', self.away_counter*5, 'seconds with a distance of', self.distance)

    def evaluate(self):
        '''Check if the distance is smaller then given and otherwise trigger away'''
        if self.distance < args.distance:
            self.status = 'near'
            self.away_counter = 0
        else:
            self.status = 'away'
            self.away_counter += 1

        if self.away_counter > args.missed:
            self.away_counter = 0
            self.status = 'gone'

class NameService(Connection):
    '''Service if distance is disable just querry for the device'''
    def __init__(self, btAddr, debug):
        self.debug = debug
        self.name = ''
        if self.debug:
            print('\033[92m[STATUS]\033[0m', 'Using name mode')
        self.bluetooth_addr = btAddr

    # Taken form bluefence, this does not need your device to be conncted
    def measure(self):
        '''Using the bluetooth lookup the devices, which does not need the device to be connected'''
        self.name = bluetooth.lookup_name(self.bluetooth_addr, timeout=2)

    def logs(self):
        '''Logs the current status'''
        if self.debug:
            print('\033[92m[STATUS]\033[0m', 'Device is', self.status,
                  'for', self.away_counter*5, 'seconds')

    def evaluate(self):
        '''Check if the device is in range and otherwise trigger away'''
        if self.name:
            self.status = 'near'
            self.away_counter = 0
        else:
            self.status = 'away'
            self.away_counter += 1

        if self.away_counter > args.missed:
            self.away_counter = 0
            self.status = 'gone'

def main():
    '''Main Methond'''
    # The command to run when the device is out of range

    if args.verbose:
        print('\033[92m[STATUS]\033[0m Checking for device')

    try:
        name = ""

        if args.wait:
            while True:
                name = bluetooth.lookup_name(args.ADDR, timeout=5)
                print('\033[92m[STATUS]\033[0m Waiting for devices')
                if name:
                    break
        else:
            # initial check, see if mentioned BT device active. If it's not, clean exit
            name = bluetooth.lookup_name(args.ADDR, timeout=5)

        if name:
            if args.verbose:
                print('\033[93m[STATUS]\033[0m Found', args.ADDR, 'as', name)

            connection = create_connection()

            while True:
                connection.measure()
                connection.evaluate()
                connection.logs()
                connection.execute()

                time.sleep(args.delay)

        else:
            print('\033[91m[ERROR]\033[0m Bluetooth device is not active')

    # this usually happen when your PC's bluetooth is disabled.
    except Exception:
        print('\033[91m[ERROR]\033[0m Bluetooth is not active')
        if args.verbose:
            print(Exception)

def create_connection():
    '''Factory for the distance service'''
    if args.distance is not None:
        return DistanceService(args.ADDR, args.verbose)
    else:
        return NameService(args.ADDR, args.verbose)

if __name__ == '__main__':
    main()
