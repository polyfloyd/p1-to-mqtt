P1 To MQTT
==========

A Python program that listens on the P1 serial port of modern electricity meters and relays the
received statistics to an MQTT server.

It is intended to be used with USB serial converter cables such as
[this one](https://nl.aliexpress.com/item/33025118684.html).


## Usage
```
$ p1-to-mqtt.py /dev/ttyUSB0
```

Tip: Use a udev rule to ensure that your the serial device will have a consistent name so it will
not get mixed up with other serial devices. The example below adds a symlink from `/dev/ttyP1`.
You may need to check whether attributes are unique enough for your setup as it matches any FTDI
device it finds.

```
SUBSYSTEM=="tty", ATTRS{idVendor}=="0403", ATTRS{idProduct}=="6001", SYMLINK+="ttyP1", TAG+="systemd"
```

Tip: If you use Systemd, the `TAG+="systemd"` udev directive tells systemd that it should make a `.device` unit. You can then use `After=dev-ttyP1.device` in the `.service` file to only start after the device is attached.
