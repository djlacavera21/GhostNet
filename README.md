# GhostNet Robust Communications

This repository contains scripts for simple peer-to-peer voice and text communication.

## `gn4.sh`
Legacy bash implementation with menu driven interface using `ffmpeg` and `netcat`.

## `ghostnet.py`
Cross-platform Python rewrite featuring optional AES encryption and direct
command line arguments. As of the latest version, the script also supports
basic UDP text chat.

### Usage

```bash
# Run voice server
python3 ghostnet.py server --port 7777 --password mysecret

# Run voice client
python3 ghostnet.py client --host 192.168.1.100 --port 7777 --password mysecret

# Run text chat server
python3 ghostnet.py text-server --port 8888 --password mysecret

# Run text chat client
python3 ghostnet.py text-client --host 192.168.1.100 --port 8888 --password mysecret
```

The text server now broadcasts messages to all connected clients, enabling
basic group chat.

Both server and client require `pyaudio` and, for encryption, the
`pycryptodome` package. These dependencies are listed in `requirements.txt` and
can be installed with:

```bash
pip install -r requirements.txt
```

## `ghostnet_gui.py`

For users who prefer a graphical interface there is a small Tkinter based GUI.
It wraps the command line script and launches the desired mode with the
arguments you provide.

```bash
python3 ghostnet_gui.py
```

Use the radio buttons to select voice or text mode, fill in host and port
information, and start or stop the underlying process. Output from the running
command appears in the window.

### Building a Debian package

The repository includes a `debian` directory for generating a `.deb` package. To
build it locally, run:

```bash
dpkg-buildpackage -us -uc
```

The resulting package will install the Python script as `ghostnet` and the
legacy `gn4.sh` helper under `/usr/bin`.
