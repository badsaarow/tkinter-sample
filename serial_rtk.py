import json
import threading
import pynmea2, serial, os, time, sys, glob, datetime

global rtk_thread, nmea, rtk_status
rtk_status = {}

def logfilename():
    now = datetime.datetime.now()
    return 'NMEA_%0.4d-%0.2d-%0.2d_%0.2d-%0.2d-%0.2d.nmea' % \
                (now.year, now.month, now.day, now.hour, now.minute, now.second)

def _scan_ports():
    if sys.platform.startswith('win'):
        ports = ['COM%s' % (i + 1) for i in range(256)]
    elif sys.platform.startswith('linux') or sys.platform.startswith('cygwin'):
        # this excludes your current terminal "/dev/tty"
        patterns = ('/dev/tty[A-Za-z]*', '/dev/ttyUSB*')
        ports = [glob.glob(pattern) for pattern in patterns]
        ports = [item for sublist in ports for item in sublist]  # flatten
    elif sys.platform.startswith('darwin'):
        patterns = ('/dev/*serial*', '/dev/ttyUSB*', '/dev/ttyS*')
        ports = [glob.glob(pattern) for pattern in patterns]
        ports = [item for sublist in ports for item in sublist]  # flatten
    else:
        raise EnvironmentError('Unsupported platform')
    # return ports
    return ['COM9']

def handle_rtk(port, callback):
    global nmea, rtk_status
    rtk_status = {
        "SV ID12": 0,
        "PDOP (Dilution of precision)": 0,
        "HDOP (Horizontal DOP)": 0,
        "VDOP (Vertical DOP)": 0,
        "Mode": "A",
        "Mode fix type": 1,
        "Timestamp": 0.0,
        "Latitude": 0.0,
        "Latitude Direction": "N",
        "Longitude": 0.0,
        "Longitude Direction": "E",
        "GPS Quality Indicator": 0,
        "Number of Satellites in use": 0,
        "Horizontal Dilution of Precision": 0.0,
        "Antenna Alt above sea level (mean)": 0.0,
        "Units of altitude (meters)": "M",
        "Geoidal Separation": 0.0,
        "Units of Geoidal Separation (meters)": "M",
        "Age of Differential GPS Data (secs)": 790049.4,
        "Differential Reference Station ID": 4095,
        "Status": "A",
        "Speed Over Ground": 0.0,
        "True Course": 0.0,
        "Datestamp": "010119",
        "Magnetic Variation": 0.0,
        "Magnetic Variation Direction": "E",
        "Mode Indicator": 0,
        "Navigational Status": 0,
        "Number of messages of type in cycle": 0,
        "Message Number": 1,
        "Total number of SVs in view": "00",
        "SV PRN number 1": "0",
    }
    outfname = logfilename()
    sys.stderr.write('Trying port %s\n' % port)
    try:
        with serial.Serial(port, 115200, timeout=1) as ser:
            while True:
                for i in range(10):
                    ser.readline()
                nmea = pynmea2.parse(ser.readline().decode('ascii', errors='replace'))

                for i in range(len(nmea.fields)):
                    if i < len(nmea.data):
                        # print('%s: %s' % (nmea.fields[i][0], nmea.data[i]))
                        # update rtk_status if field is in rtk_status
                        if nmea.fields[i][0] in rtk_status:
                            rtk_status[nmea.fields[i][0]] = nmea.data[i]

                # print(json.dumps(rtk_status, indent=4)) 
                callback(rtk_status)
    except Exception as e:
        sys.stderr.write('Error reading serial port %s: %s\n' % (type(e).__name__, e))
    except KeyboardInterrupt as e:
        sys.stderr.write('Ctrl-C pressed, exiting log of %s to %s\n' % (port, outfname))

def get_rtk_data():
    global rtk_status
    # nmea object
    # Timestamp: 072344.707
    # Latitude: 
    # Latitude Direction: 
    # Longitude: 
    # Longitude Direction: 
    # GPS Quality Indicator: 0
    # Number of Satellites in use: 00
    # Horizontal Dilution of Precision:
    # Antenna Alt above sea level (mean):
    # Units of altitude (meters): M
    # Geoidal Separation:
    # Units of Geoidal Separation (meters): M
    # Age of Differential GPS Data (secs): 787726.7
    # Differential Reference Station ID: 4095    

    print('get_rtk_data', rtk_status)
    
    # 0: Invalid, 1: GPS SPS, 2: D-GPS, 3: GPS PPS, 4: RTK Fixed, 5: RTK Floating, 6: Dead Reckoning
    return rtk_status

def create_rtk_thread(port, callback):
    global rtk_thread
    rtk_thread = threading.Thread(target=handle_rtk, args=(port, callback))
    rtk_thread.daemon = True
    rtk_thread.start()

if __name__ =='__main__':
    while True:
        ports = _scan_ports()
        if len(ports) == 0:
            sys.stderr.write('No ports found, waiting 10 seconds...press Ctrl-C to quit...\n')
            time.sleep(10)
            continue

        for port in ports:
            # try to open serial port
            handle_rtk(port)

        sys.stderr.write('Scanned all ports, waiting 10 seconds...press Ctrl-C to quit...\n')
        time.sleep(10)

