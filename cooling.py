import os
import csv
import time
import serial

import minimalmodbus

PORT_LIST = ['COM7', 'COM1', 'COM2', 'COM4', 'COM4', 'COM5', 'COM6', 'COM8', 'COM9']

#LOGFILE_ROOT_DIR = 'c:/OpenHardwareMonitor'
#CPU_TEMP_COLUMN_NAME = "/intelcpu/0/temperature/4"

LOGFILE_ROOT_DIR = 'c:/HWiNFO'
CPU_TEMP_COLUMN_NAME = "CPU Package [°C]"
CLOCKS_COLUMN_NAME = "Core Clocks (avg) [MHz]"

MIN_VOLT = 500
MAX_VOLT = 1200
VOLT_RANGE = MAX_VOLT - MIN_VOLT
MAX_TEMP = 100
MIN_TEMP = 75
TEMP_RANGE = MAX_TEMP - MIN_TEMP


CLOCKS_MAX_MHZ = 3890
CLOCKS_THROTTLING_FACTOR = 0  # %% of CLOCKS_MAX_MHZ that would indicate throttling
DOWN_STEP = 50
UP_STEP = 50
STAY_HIGH_MIN_DURATION = 2

def get_instrument():
    connected = False
    instrument = None
    while not connected:
        for port in PORT_LIST:
            try:
                instrument = minimalmodbus.Instrument(
                    port = port,
                    slaveaddress = 1,
                    mode = minimalmodbus.MODE_RTU,
                    close_port_after_each_call = False)

                instrument.serial.baudrate = 9600
                instrument.serial.bytesize = 8
                instrument.serial.timeout = 2

                instrument.read_register(2, 2) # test read 
                print ('Connected')
                connected = True
                break;
            except Exception as e:
                print (f'Failed to connect to port {port}: {e}')
                if (instrument is not None):
                    instrument.serial.close()
                continue
    return instrument

def find_oldest_csv(directory: str) -> str:
    """Find the oldest CSV file in a directory matching a specific pattern."""
    files = sorted([f for f in os.listdir(directory) if f.endswith(".CSV")]) # and f.startswith("OpenHardwareMonitorLog")
    if not files:
        raise FileNotFoundError("No matching CSV file found.")
    return os.path.join(directory, files[-1])

def get_last_values_from_csv(csv_file, column_names):
    with open(csv_file, 'r') as file:
        lines = file.readlines()
        first_line = lines[0]
        last_line = lines[-1]
        reader = csv.reader([first_line, last_line])
        columns = next(reader)
        data = list(reader)
        last_row = data[-1]
        #value = last_row[columns.index(column_name)]
        values = [last_row[columns.index(column_name)] for column_name in column_names]
    return values

def clocks_factor(clocks_value):
    return int(100 * clocks_value / CLOCKS_MAX_MHZ)

def when_can_go_down_in(from_volt):
    if(from_volt < MIN_VOLT):
        return 0
    return int(float(from_volt - MIN_VOLT) / VOLT_RANGE * 10 * STAY_HIGH_MIN_DURATION)

def main():
    can_go_down_in = 0
    volt_value = 0
    instrument = get_instrument()
    while True:
        oldest_csv = find_oldest_csv(LOGFILE_ROOT_DIR)
        if oldest_csv:
            #print (f"Looking into: {oldest_csv}")
            try:
                temp_value, clocks_value = [int(float(value)) for value in get_last_values_from_csv(oldest_csv, [CPU_TEMP_COLUMN_NAME, CLOCKS_COLUMN_NAME])]
                
                if clocks_factor(clocks_value) <= CLOCKS_THROTTLING_FACTOR:
                    target_volt_value = MAX_VOLT
                else:
                    if (temp_value >= MIN_TEMP):
                        target_volt_value = int(MIN_VOLT + (min(temp_value, MAX_TEMP) - MIN_TEMP) * VOLT_RANGE / TEMP_RANGE )
                    else:
                        target_volt_value = 0

                if (target_volt_value >= volt_value):
                    if (target_volt_value > volt_value):
                        min_value = max(volt_value, MIN_VOLT)
                        volt_value = min_value + UP_STEP
                    can_go_down_in = when_can_go_down_in(target_volt_value)
                else:
                    if (can_go_down_in <= 1):
                        volt_value = volt_value - DOWN_STEP
                        can_go_down_in = when_can_go_down_in(target_volt_value)
                    else:
                        can_go_down_in = can_go_down_in - 1
                
                # paranoid checks
                if (volt_value < MIN_VOLT):
                    volt_value = 0         

                if (volt_value > MAX_VOLT):
                    volt_value = MAX_VOLT

                # target volt change direction
                if (target_volt_value > volt_value):
                    target_direction_char = '↑'
                elif (target_volt_value < volt_value):
                    target_direction_char = '↓'
                else:
                    target_direction_char = '→'

                print(f"CPU: {temp_value: >3}°C  Clocks: {clocks_factor(clocks_value): >3}% | {volt_value/100: >4}V ({target_direction_char} {target_volt_value/100:4.1f}V {can_go_down_in: >2}s)")
                try:
                    instrument.write_register(0, volt_value)
                except Exception as e:
                    print(f"Can'r write register: {e}, reconnecting")
                    instrument = get_instrument()
                    
                time.sleep(1)
            except (ValueError, IndexError):
                print(f"Column {CPU_TEMP_COLUMN_NAME} or {CLOCKS_COLUMN_NAME} not found.")
                time.sleep(1)
                continue
        else:
            print ("Can't find log file")

if __name__ == "__main__":
    main()
