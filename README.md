# GhostNet Robust Communications

This repository contains scripts for simple peer-to-peer voice and text communication.

## `gn4.sh`
Legacy bash implementation with menu driven interface using `ffmpeg` and `netcat`.

## `ghostnet.py`
Cross-platform Python rewrite featuring optional AES encryption and direct
command line arguments. The tool supports basic UDP text chat and now allows
selecting audio input/output devices by index. A `list-devices` command is
provided to display available devices.

### Usage

```bash
# Run voice server
python3 ghostnet.py server --port 7777 --password mysecret

# Use a specific output device (index 2)
python3 ghostnet.py server --port 7777 --output-device 2

# Run voice client
python3 ghostnet.py client --host 192.168.1.100 --port 7777 --password mysecret

# Use a specific input device (index 1)
python3 ghostnet.py client --host 192.168.1.100 --port 7777 --input-device 1

# Run text chat server
python3 ghostnet.py text-server --port 8888 --password mysecret

# Run text chat client
python3 ghostnet.py text-client --host 192.168.1.100 --port 8888 --password mysecret

# List available audio devices
python3 ghostnet.py list-devices
```

The text server now broadcasts messages to all connected clients, enabling
basic group chat.

Both server and client require `pyaudio` and, for encryption, the
`pycryptodome` package. These dependencies are listed in `requirements.txt` and
can be installed with:

```bash
pip install -r requirements.txt
```

### Building a Debian package

The repository includes a `debian` directory for generating a `.deb` package. To
build it locally, run:

```bash
dpkg-buildpackage -us -uc
```

The resulting package will install the Python script as `ghostnet` and the
legacy `gn4.sh` helper under `/usr/bin`.
