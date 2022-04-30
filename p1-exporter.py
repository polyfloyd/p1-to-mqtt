#!/usr/bin/env python3

import argparse
import os
import re
from typing import List

from prometheus_client import Gauge, start_http_server
import serial


p1_power_used = Gauge('p1_power_used_kwh', 'The total amount of power consumed from the net', ['tarif'])
p1_power_produced = Gauge('p1_power_produced_kwh', 'The total amount of power delivered back to the net', ['tarif'])
p1_tarif = Gauge('p1_tarif', 'The currently active tarif')
p1_actual_power_usage = Gauge('p1_actual_power_usage_kw', 'The current rate of power being consumed')
p1_actual_power_production = Gauge('p1_actual_power_production_kw', 'The current rate of power being produced')


def main():
    parser = argparse.ArgumentParser(description='Prometheus exporter for the P1 port of electricity meters')
    parser.add_argument('dev', type=str, help='P1 port TTY device')
    parser.add_argument('--port', type=int, default=9005,
                        help='The port number to bind the Prometheus exporter to')
    args = parser.parse_args()

    start_http_server(args.port)

    ser = configure_serial(args.dev)
    while True:
        packet = read_packet(ser)
        parse_packet(packet)


def parse_packet(packet: List[bytes]):
    # https://www.netbeheernederland.nl/_upload/Files/Slimme_meter_15_a727fce1f1.pdf, page 20
    k_power_used_tarif1       = '1-0:1.8.1'   # kwh
    k_power_used_tarif2       = '1-0:1.8.2'   # kwh
    k_power_produced_tarif1   = '1-0:2.8.1'   # kwh
    k_power_produced_tarif2   = '1-0:2.8.2'   # kwh
    k_tarif_indicator         = '0-0:96.14.0' # unitless
    k_actual_power_usage      = '1-0:1.7.0'   # kw
    k_actual_power_production = '1-0:2.7.0'   # kw

    strip_unit = lambda s: s.split('*')[0] if '*' in s else s
    expr = re.compile('^(.+?)\((.*?)\)(?:\((.*?)\))?$')

    for line in packet:
        line = line.decode('ascii')
        m = expr.findall(line)
        if not m:
            continue
        [(key, v0, v1)] = m

        if key == k_power_used_tarif1:
            p1_power_used.labels(tarif='1').set(float(strip_unit(v0)))
        elif key == k_power_used_tarif2:
            p1_power_used.labels(tarif='2').set(float(strip_unit(v0)))
        elif key == k_power_produced_tarif1:
            p1_power_produced.labels(tarif='1').set(float(strip_unit(v0)))
        elif key == k_power_produced_tarif2:
            p1_power_produced.labels(tarif='2').set(float(strip_unit(v0)))
        elif key == k_tarif_indicator:
            p1_tarif.set(int(v0))
        elif key == k_actual_power_usage:
            p1_actual_power_usage.set(float(strip_unit(v0)))
        elif key == p1_actual_power_production:
            p1_actual_power_production.set(float(strip_unit(v0)))


def read_packet(ser: serial.Serial) -> List[bytes]:
    lines = []

    line = b''
    while line != b'/KFM5KAIFA-METER\r\n':
        line = ser.readline()

    while not line.startswith(b'!'):
        line = ser.readline().strip()
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


main()
