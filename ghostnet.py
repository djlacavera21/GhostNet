#!/usr/bin/env python3
"""GhostNet Robust Communications Program

A cross-platform voice and text communication tool using UDP sockets.
Supports optional AES-256-GCM encryption with a shared passphrase.
Now includes basic text chat functionality.
"""

import argparse
import socket
import threading
import hashlib
import sys

try:
    import pyaudio
except ImportError:
    pyaudio = None

try:
    from Crypto.Cipher import AES
    from Crypto.Random import get_random_bytes
except ImportError:
    AES = None  # type: ignore
    get_random_bytes = None  # type: ignore

DEFAULT_RATE = 44100
DEFAULT_CHANNELS = 1
CHUNK = 1024


def derive_key(password: str) -> bytes:
    """Derive a 256-bit key from a password."""
    return hashlib.sha256(password.encode()).digest()


def list_devices(_: argparse.Namespace) -> None:
    """Print available audio input and output devices."""
    if pyaudio is None:
        print("pyaudio is required for device listing", file=sys.stderr)
        sys.exit(1)

    pa = pyaudio.PyAudio()
    try:
        for i in range(pa.get_device_count()):
            info = pa.get_device_info_by_index(i)
            flags = []
            if info.get("maxInputChannels", 0) > 0:
                flags.append("input")
            if info.get("maxOutputChannels", 0) > 0:
                flags.append("output")
            roles = "/".join(flags) if flags else ""
            print(f"{i}: {info.get('name', 'Unknown')} ({roles})")
    finally:
        pa.terminate()


class VoiceSocket:
    """Wrapper around a UDP socket with optional AES encryption."""

    def __init__(self, sock: socket.socket, encrypt: bool = False, key: bytes | None = None):
        self.sock = sock
        self.encrypt = encrypt and AES is not None and key is not None
        self.key = key

    def send(self, data: bytes, addr):
        if self.encrypt and self.key:
            nonce = get_random_bytes(12)
            cipher = AES.new(self.key, AES.MODE_GCM, nonce=nonce)
            ciphertext, tag = cipher.encrypt_and_digest(data)
            packet = nonce + tag + ciphertext
            self.sock.sendto(packet, addr)
        else:
            self.sock.sendto(data, addr)

    def recv(self, bufsize: int) -> tuple[bytes, tuple[str, int]]:
        data, addr = self.sock.recvfrom(bufsize)
        if self.encrypt and self.key:
            nonce = data[:12]
            tag = data[12:28]
            ciphertext = data[28:]
            cipher = AES.new(self.key, AES.MODE_GCM, nonce=nonce)
            try:
                plaintext = cipher.decrypt_and_verify(ciphertext, tag)
            except Exception:
                return b"", addr
            return plaintext, addr
        return data, addr


class VoiceServer:
    def __init__(self, host: str, port: int, key: bytes | None,
                 output_device: int | None = None):
        if pyaudio is None:
            raise RuntimeError("pyaudio is required for audio playback")
        self.audio = pyaudio.PyAudio()
        params = dict(format=pyaudio.paInt16, channels=DEFAULT_CHANNELS,
                      rate=DEFAULT_RATE, output=True,
                      frames_per_buffer=CHUNK)
        if output_device is not None:
            params["output_device_index"] = output_device
        self.stream = self.audio.open(**params)
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.bind((host, port))
        self.vsock = VoiceSocket(sock, key is not None, key)

    def serve(self):
        print("[Server] Listening for audio...")
        try:
            while True:
                data, _ = self.vsock.recv(4096)
                if data:
                    self.stream.write(data)
        except KeyboardInterrupt:
            pass
        finally:
            self.stream.stop_stream()
            self.stream.close()
            self.audio.terminate()


class VoiceClient:
    def __init__(self, host: str, port: int, key: bytes | None,
                 input_device: int | None = None):
        if pyaudio is None:
            raise RuntimeError("pyaudio is required for audio capture")
        self.target = (host, port)
        self.audio = pyaudio.PyAudio()
        params = dict(format=pyaudio.paInt16, channels=DEFAULT_CHANNELS,
                      rate=DEFAULT_RATE, input=True,
                      frames_per_buffer=CHUNK)
        if input_device is not None:
            params["input_device_index"] = input_device
        self.stream = self.audio.open(**params)
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.vsock = VoiceSocket(sock, key is not None, key)

    def start(self):
        print(f"[Client] Sending audio to {self.target[0]}:{self.target[1]}")
        try:
            while True:
                data = self.stream.read(CHUNK, exception_on_overflow=False)
                self.vsock.send(data, self.target)
        except KeyboardInterrupt:
            pass
        finally:
            self.stream.stop_stream()
            self.stream.close()
            self.audio.terminate()


class TextServer:
    """Simple UDP text chat server with basic message broadcasting."""

    def __init__(self, host: str, port: int, key: bytes | None):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.bind((host, port))
        self.vsock = VoiceSocket(sock, key is not None, key)
        self.clients: set[tuple[str, int]] = set()

    def serve(self):
        print("[TextServer] Listening for messages...")
        try:
            while True:
                data, addr = self.vsock.recv(4096)
                if not data:
                    continue
                self.clients.add(addr)
                msg = data.decode(errors="replace")
                print(f"{addr[0]}:{addr[1]} > {msg}")
                for client in self.clients:
                    if client != addr:
                        self.vsock.send(data, client)
        except KeyboardInterrupt:
            pass


class TextClient:
    """Simple UDP text chat client."""

    def __init__(self, host: str, port: int, key: bytes | None):
        self.target = (host, port)
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.vsock = VoiceSocket(sock, key is not None, key)

    def start(self):
        print(
            f"[TextClient] Sending text to {self.target[0]}:{self.target[1]} (Ctrl+C to quit)"
        )
        try:
            while True:
                msg = input("> ")
                if not msg:
                    continue
                self.vsock.send(msg.encode(), self.target)
        except KeyboardInterrupt:
            pass


def run_server(args):
    key = derive_key(args.password) if args.password else None
    server = VoiceServer(args.host, args.port, key, args.output_device)
    server.serve()


def run_client(args):
    key = derive_key(args.password) if args.password else None
    client = VoiceClient(args.host, args.port, key, args.input_device)
    client.start()


def run_text_server(args):
    key = derive_key(args.password) if args.password else None
    server = TextServer(args.host, args.port, key)
    server.serve()


def run_text_client(args):
    key = derive_key(args.password) if args.password else None
    client = TextClient(args.host, args.port, key)
    client.start()


def main():
    parser = argparse.ArgumentParser(description="GhostNet Robust Communications")
    sub = parser.add_subparsers(dest="mode", required=True)

    srv = sub.add_parser("server", help="Run in server mode")
    srv.add_argument("--host", default="0.0.0.0", help="Host to bind")
    srv.add_argument("--port", type=int, default=7777, help="UDP port")
    srv.add_argument("--password", help="Shared password for encryption")
    srv.add_argument("--output-device", type=int,
                     help="PyAudio output device index")
    srv.set_defaults(func=run_server)

    cli = sub.add_parser("client", help="Run in client mode")
    cli.add_argument("--host", required=True, help="Server address")
    cli.add_argument("--port", type=int, default=7777, help="UDP port")
    cli.add_argument("--password", help="Shared password for encryption")
    cli.add_argument("--input-device", type=int,
                     help="PyAudio input device index")
    cli.set_defaults(func=run_client)

    tsrv = sub.add_parser("text-server", help="Run text chat server")
    tsrv.add_argument("--host", default="0.0.0.0", help="Host to bind")
    tsrv.add_argument("--port", type=int, default=8888, help="UDP port for text chat")
    tsrv.add_argument("--password", help="Shared password for encryption")
    tsrv.set_defaults(func=run_text_server)

    tcli = sub.add_parser("text-client", help="Run text chat client")
    tcli.add_argument("--host", required=True, help="Server address")
    tcli.add_argument("--port", type=int, default=8888, help="UDP port for text chat")
    tcli.add_argument("--password", help="Shared password for encryption")
    tcli.set_defaults(func=run_text_client)

    ldev = sub.add_parser("list-devices", help="List audio devices")
    ldev.set_defaults(func=list_devices)

    args = parser.parse_args()

    if AES is None and args.password:
        print("[!] Encryption requested but pycryptodome is missing", file=sys.stderr)
        sys.exit(1)

    args.func(args)


if __name__ == "__main__":
    main()
