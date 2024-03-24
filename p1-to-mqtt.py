#!/usr/bin/env python3

from typing import List
import argparse
import paho.mqtt.client as mqtt
import re
import serial


# https://www.netbeheernederland.nl/_upload/Files/Slimme_meter_15_a727fce1f1.pdf, page 20
k_power_used_tarif1       = '1-0:1.8.1'   # kwh
k_power_used_tarif2       = '1-0:1.8.2'   # kwh
k_power_produced_tarif1   = '1-0:2.8.1'   # kwh
k_power_produced_tarif2   = '1-0:2.8.2'   # kwh
k_tarif_indicator         = '0-0:96.14.0' # unitless
k_actual_power_usage      = '1-0:1.7.0'   # kw
k_actual_power_production = '1-0:2.7.0'   # kw
k_voltage_l1              = '1-0:32.7.0'  # v
k_voltage_l2              = '1-0:52.7.0'  # v
k_voltage_l3              = '1-0:72.7.0'  # v
k_gas_used                = '0-1:24.2.1'  # m3

unit = lambda s: float(s.split('*')[0] if '*' in s else s)
kilowatthours = lambda v: f'{unit(v)} kWh'
volt = lambda v: f'{unit(v)} V'
watt = lambda s: f'{unit(s) * 1000} W'
cubicmeters = lambda v: f'{unit(v)} m³'

packet_expr = re.compile('^(.+?)\((.*?)\)(?:\((.*?)\))?$')


def parse_packet(mqtt_client: mqtt.Client, packet: List[bytes]):
    power_used_total = 0
    power_produced_total = 0

    for line in packet:
        line = line.decode('ascii')
        m = packet_expr.findall(line)
        if not m:
            continue
        [(key, v0, v1)] = m

        if key == k_power_used_tarif1:
            mqtt_client.publish('p1/power_used/T1', kilowatthours(v0))
            power_used_total += unit(v0)
        elif key == k_power_used_tarif2:
            mqtt_client.publish('p1/power_used/T2', kilowatthours(v0))
            power_used_total += unit(v0)
        elif key == k_power_produced_tarif1:
            mqtt_client.publish('p1/power_produced/T1', kilowatthours(v0))
            power_produced_total += unit(v0)
        elif key == k_power_produced_tarif2:
            mqtt_client.publish('p1/power_produced/T2', kilowatthours(v0))
            power_produced_total += unit(v0)
        elif key == k_tarif_indicator:
            mqtt_client.publish('p1/tarif', f'T{int(v0)}')
        elif key == k_actual_power_usage:
            mqtt_client.publish('p1/actual_power_usage', watt(v0))
        elif key == k_actual_power_production:
            mqtt_client.publish('p1/actual_power_production', watt(v0))
        elif key == k_voltage_l1:
            mqtt_client.publish('p1/voltage/L1', volt(v0))
        elif key == k_voltage_l2:
            mqtt_client.publish('p1/voltage/L2', volt(v0))
        elif key == k_voltage_l3:
            mqtt_client.publish('p1/voltage/L3', volt(v0))
        elif key == k_gas_used:
            mqtt_client.publish('p1/gas_used', cubicmeters(v1))

    mqtt_client.publish('p1/power_used', f'{power_used_total} kWh')
    mqtt_client.publish('p1/power_produced', f'{power_produced_total} kWh')


def read_packet(ser: serial.Serial) -> List[bytes]:
    lines = []
    line = b''
    while not line.startswith(b'!'):
        line = ser.readline().strip()
        if line:
            lines.append(line)
    return lines


def configure_serial(dev: str) -> serial.Serial:
    ser = serial.Serial(dev)

    # DSMR 4.0/4.2 > 115200 8N1:
    ser.baudrate = 115200
    ser.bytesize = serial.EIGHTBITS
    ser.parity = serial.PARITY_NONE
    ser.stopbits = serial.STOPBITS_ONE

    if not ser.isOpen():
        ser.open()

    return ser


def main():
    parser = argparse.ArgumentParser(description='Prometheus exporter for the P1 port of electricity meters')
    parser.add_argument('dev', type=str, help='P1 port TTY device')
    parser.add_argument('--host', type=str, default='mqtt.local',
                        help='The hostname of the MQTT server')
    parser.add_argument('--port', type=int, default=1883,
                        help='The port of the MQTT server')
    args = parser.parse_args()

    client = mqtt.Client()
    client.connect(args.host, args.port, 60)
    client.loop_start()

    ser = configure_serial(args.dev)
    while True:
        packet = read_packet(ser)
        parse_packet(client, packet)


if __name__ == '__main__':
    main()
