from datetime import datetime
import argparse
import pyowm
import sys
import time

from Adafruit_LED_Backpack import SevenSegment
from Adafruit_MCP9808 import MCP9808


class ClockDisplay(SevenSegment.SevenSegment):
    COLON_OFF = 0x00
    COLON_CLOCK = 0x02
    COLON_UPPER_LEFT = 0x04
    COLON_LOWER_LEFT = 0x08
    COLON_UPPER_RIGHT = 0x10

    def set_colon(self, colon):
        self.buffer[4] = colon


class TempClock(object):
    def __init__(self, display, sensor, owm, zip_code, use_f=False):
        self._display = display
        self._sensor = sensor
        self._owm = owm
        self._zip_code = zip_code
        self._use_f = use_f
        self._time = '1200'
        self._pm = False
        self._inside = 0
        self._outside = 0

    def _update_time(self):
        now = datetime.now()
        self._time = now.strftime('%-I%M')
        self._pm = (now.strftime('%p') == 'PM')

    def show_time(self):
        self._update_time()
        self._display.clear()
        self._display.print_number_str(self._time)
        colon = ClockDisplay.COLON_CLOCK
        if self._pm:
            colon |= ClockDisplay.COLON_UPPER_LEFT

        self._display.set_colon(colon)
        self._display.write_display()

    def _update_inside_temperature(self):
        temp_c = self._sensor.readTempC()
        if self._use_f:
            self._inside = ((temp_c * 9.0) / 5.0) + 32.0
        else:
            self._inside = temp_c

    def _update_outside_temperature(self):
        observation = self._owm.weather_at_zip_code(self._zip_code, 'US')
        w = observation.get_weather()
        if self._use_f:
            temperature = w.get_temperature('fahrenheit')
        else:
            temperature = w.get_temperature('celsius')
        self._outside = temperature['temp_max']

    def update_temperature(self):
        self._update_inside_temperature()
        self._update_outside_temperature()

    def _show_temperature(self, temperature, inside=True):
        self._display.clear()
        self._display.print_number_str('{0} '.format(int(temperature)))
        colon = ClockDisplay.COLON_UPPER_RIGHT
        if inside:
            colon |= ClockDisplay.COLON_UPPER_LEFT
        else:
            colon |= ClockDisplay.COLON_LOWER_LEFT
        self._display.set_colon(colon)
        self._display.write_display()

    def show_inside_temperature(self):
        self._show_temperature(self._inside, True)

    def show_outside_temperature(self):
        self._show_temperature(self._outside, False)


def _define_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--api_key',
        help='OpenWeatherMap API Key',
        required=True,
    )
    parser.add_argument(
        '--zip_code',
        help='ZIP Code for weather lookup',
        required=True,
    )
    parser.add_argument(
        '--brightness',
        nargs='?',
        const=True,
        default=15,
        type=int,
        help='LED Brightness (0-15)'
    )
    parser.add_argument(
        '--use_f',
        nargs='?',
        const=True,
        default=False,
        type=bool,
        help='Use Fahrenheit instead of Celsius for temperature display',
    )
    parser.add_argument(
        '--display',
        nargs='?',
        const=True,
        default=5,
        type=int,
        help='Interval in seconds between display changes',
    )
    parser.add_argument(
        '--weather',
        nargs='?',
        const=True,
        default=300,
        type=int,
        help='Interval in seconds between weather updates',
    )
    return parser


def main():
    args = _define_args().parse_args()

    brightness = args.brightness
    if brightness not in range(0, 16):
        brightness = 15

    print 'Initializing display ...'
    display = ClockDisplay()
    display.begin()
    display.set_brightness(brightness)

    print 'Initializing temperature sensor ...'
    sensor = MCP9808.MCP9808()
    sensor.begin()

    print 'Initializing OWM API, this may take a few seconds ...'
    owm = pyowm.OWM(args.api_key)

    clock = TempClock(display, sensor, owm, args.zip_code, use_f=args.use_f)
    last_temperature = 0

    functions = [
        clock.show_time,
        clock.show_inside_temperature,
        clock.show_time,
        clock.show_outside_temperature,
    ]

    while True:
        if (time.time() - last_temperature) > args.weather:
            clock.update_temperature()
            last_temperature = time.time()
            continue
        f = functions.pop(0)
        f()
        functions.append(f)
        time.sleep(args.display)


if __name__ == '__main__':
    main()
