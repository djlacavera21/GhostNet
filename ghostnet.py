#!/usr/bin/env python3
"""GhostNet Robust Communications Program

A cross-platform voice and text communication tool using UDP sockets.
Supports optional AES-256-GCM encryption with a shared passphrase.
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
    def __init__(self, host: str, port: int, key: bytes | None):
        if pyaudio is None:
            raise RuntimeError("pyaudio is required for audio playback")
        self.audio = pyaudio.PyAudio()
        self.stream = self.audio.open(format=pyaudio.paInt16, channels=DEFAULT_CHANNELS,
                                      rate=DEFAULT_RATE, output=True, frames_per_buffer=CHUNK)
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
    def __init__(self, host: str, port: int, key: bytes | None):
        if pyaudio is None:
            raise RuntimeError("pyaudio is required for audio capture")
        self.target = (host, port)
        self.audio = pyaudio.PyAudio()
        self.stream = self.audio.open(format=pyaudio.paInt16, channels=DEFAULT_CHANNELS,
                                      rate=DEFAULT_RATE, input=True, frames_per_buffer=CHUNK)
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


def run_server(args):
    key = derive_key(args.password) if args.password else None
    server = VoiceServer(args.host, args.port, key)
    server.serve()


def run_client(args):
    key = derive_key(args.password) if args.password else None
    client = VoiceClient(args.host, args.port, key)
    client.start()


def main():
    parser = argparse.ArgumentParser(description="GhostNet Robust Communications")
    sub = parser.add_subparsers(dest="mode", required=True)

    srv = sub.add_parser("server", help="Run in server mode")
    srv.add_argument("--host", default="0.0.0.0", help="Host to bind")
    srv.add_argument("--port", type=int, default=7777, help="UDP port")
    srv.add_argument("--password", help="Shared password for encryption")
    srv.set_defaults(func=run_server)

    cli = sub.add_parser("client", help="Run in client mode")
    cli.add_argument("--host", required=True, help="Server address")
    cli.add_argument("--port", type=int, default=7777, help="UDP port")
    cli.add_argument("--password", help="Shared password for encryption")
    cli.set_defaults(func=run_client)

    args = parser.parse_args()

    if AES is None and args.password:
        print("[!] Encryption requested but pycryptodome is missing", file=sys.stderr)
        sys.exit(1)

    args.func(args)


if __name__ == "__main__":
    main()
