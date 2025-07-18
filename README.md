# GhostNet Robust Communications

This repository contains scripts for simple peer-to-peer voice and text communication.

## `gn4.sh`
Legacy bash implementation with menu driven interface using `ffmpeg` and `netcat`.

## `ghostnet.py`
Cross-platform Python rewrite featuring optional AES encryption and direct
command line arguments.

### Usage

```bash
# Run server
python3 ghostnet.py server --port 7777 --password mysecret

# Run client
python3 ghostnet.py client --host 192.168.1.100 --port 7777 --password mysecret
```

Both server and client require `pyaudio` and, for encryption, the
`pycryptodome` package.
