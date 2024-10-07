#!/usr/bin/python3
# -*- coding: latin-1 -*-
import sys, posix, time, binascii, socket, select, ssl
import hashlib
import argparse
import re


class ApiRos:
    "Routeros api"
    def __init__(self, sk):
        self.sk = sk
        self.currenttag = 0

    def login(self, username, pwd):
        for repl, attrs in self.talk(
            ["/login", "=name=" + username, "=password=" + pwd]
        ):
            if repl == "!trap":
                return False
            elif "=ret" in attrs.keys():
                # for repl, attrs in self.talk(["/login"]):
                chal = binascii.unhexlify((attrs["=ret"]).encode(sys.stdout.encoding))
                md = hashlib.md5()
                md.update(b"\x00")
                md.update(pwd.encode(sys.stdout.encoding))
                md.update(chal)
                for repl2, attrs2 in self.talk(
                    [
                        "/login",
                        "=name=" + username,
                        "=response=00"
                        + binascii.hexlify(md.digest()).decode(sys.stdout.encoding),
                    ]
                ):
                    if repl2 == "!trap":
                        return False
        return True

    def talk(self, words):
        if self.writeSentence(words) == 0:
            return
        r = []
        while 1:
            i = self.readSentence()
            if len(i) == 0:
                continue
            reply = i[0]
            attrs = {}
            for w in i[1:]:
                j = w.find("=", 1)
                if j == -1:
                    attrs[w] = ""
                else:
                    attrs[w[:j]] = w[j + 1 :]
            r.append((reply, attrs))
            if reply == "!done":
                return r

    def writeSentence(self, words):
        ret = 0
        for w in words:
            self.writeWord(w)
            ret += 1
        self.writeWord("")
        return ret

    def readSentence(self):
        r = []
        while 1:
            w = self.readWord()
            if w == "":
                return r
            r.append(w)

    def writeWord(self, w):
        print(("<<< " + w))
        self.writeLen(len(w))
        self.writeStr(w)

    def readWord(self):
        ret = self.readStr(self.readLen())
        ret =ret.replace("=", "", 1)
        #print(ret)
        return ret

    def writeLen(self, l):
        if l < 0x80:
            self.writeByte((l).to_bytes(1, sys.byteorder))
        elif l < 0x4000:
            l |= 0x8000
            tmp = (l >> 8) & 0xFF
            self.writeByte(((l >> 8) & 0xFF).to_bytes(1, sys.byteorder))
            self.writeByte((l & 0xFF).to_bytes(1, sys.byteorder))
        elif l < 0x200000:
            l |= 0xC00000
            self.writeByte(((l >> 16) & 0xFF).to_bytes(1, sys.byteorder))
            self.writeByte(((l >> 8) & 0xFF).to_bytes(1, sys.byteorder))
            self.writeByte((l & 0xFF).to_bytes(1, sys.byteorder))
        elif l < 0x10000000:
            l |= 0xE0000000
            self.writeByte(((l >> 24) & 0xFF).to_bytes(1, sys.byteorder))
            self.writeByte(((l >> 16) & 0xFF).to_bytes(1, sys.byteorder))
            self.writeByte(((l >> 8) & 0xFF).to_bytes(1, sys.byteorder))
            self.writeByte((l & 0xFF).to_bytes(1, sys.byteorder))
        else:
            self.writeByte((0xF0).to_bytes(1, sys.byteorder))
            self.writeByte(((l >> 24) & 0xFF).to_bytes(1, sys.byteorder))
            self.writeByte(((l >> 16) & 0xFF).to_bytes(1, sys.byteorder))
            self.writeByte(((l >> 8) & 0xFF).to_bytes(1, sys.byteorder))
            self.writeByte((l & 0xFF).to_bytes(1, sys.byteorder))

    def readLen(self):
        c = ord(self.readStr(1))
        # print (">rl> %i" % c)
        if (c & 0x80) == 0x00:
            pass
        elif (c & 0xC0) == 0x80:
            c &= ~0xC0
            c <<= 8
            c += ord(self.readStr(1))
        elif (c & 0xE0) == 0xC0:
            c &= ~0xE0
            c <<= 8
            c += ord(self.readStr(1))
            c <<= 8
            c += ord(self.readStr(1))
        elif (c & 0xF0) == 0xE0:
            c &= ~0xF0
            c <<= 8
            c += ord(self.readStr(1))
            c <<= 8
            c += ord(self.readStr(1))
            c <<= 8
            c += ord(self.readStr(1))
        elif (c & 0xF8) == 0xF0:
            c = ord(self.readStr(1))
            c <<= 8
            c += ord(self.readStr(1))
            c <<= 8
            c += ord(self.readStr(1))
            c <<= 8
            c += ord(self.readStr(1))
        return c

    def writeStr(self, str):
        n = 0
        while n < len(str):
            r = self.sk.send(bytes(str[n:], "UTF-8"))
            if r == 0:
                raise RuntimeError("connection closed by remote end")
            n += r

    def writeByte(self, str):
        n = 0
        while n < len(str):
            r = self.sk.send(str[n:])
            if r == 0:
                raise RuntimeError("connection closed by remote end")
            n += r

    def readStr(self, length):
        ret = ""
        # print ("length: %i" % length)
        while len(ret) < length:
            s = self.sk.recv(length - len(ret))
            if s == b"":
                raise RuntimeError("connection closed by remote end")
            # print (b">>>" + s)
            # atgriezt kaa byte ja nav ascii chars
            if s >= (128).to_bytes(1, "big"):
                return s
            # print((">>> " + s.decode(sys.stdout.encoding, 'ignore')))
            ret += s.decode(sys.stdout.encoding, "replace")
        return ret

    def command(self, cmd):
        self.writeSentence(cmd)
        result = []
        while 1:
            r = select.select([self.sk], [], [], None)
            if self.sk in r[0]:
                x = self.readSentence()
                if x == ["!done"]:
                    return result
                o = list_to_dict(x)
                check_for_failure(str(cmd),o)
                result.append(o)

class RosApiException(Exception):
    pass

def check_for_failure(cmd, data):
    if isinstance(data, dict) and 'message' in data:
        message = data['message']
        if 'failure' in message:
            raise RosApiException(f"Command: {cmd}, {message}")

def open_socket(dst, port, secure=False):
    s = None
    res = socket.getaddrinfo(dst, port, socket.AF_UNSPEC, socket.SOCK_STREAM)
    af, socktype, proto, canonname, sockaddr = res[0]
    skt = socket.socket(af, socktype, proto)
    if secure:
        s = ssl.wrap_socket(
            skt, ssl_version=ssl.PROTOCOL_TLSv1_2, ciphers="ECDHE-RSA-AES256-GCM-SHA384"
        )  # ADH-AES128-SHA256
    else:
        s = skt
    s.connect(sockaddr)
    return s

def list_to_dict(lst):
    result = {}
    for item in lst[1:]:  # Skip the first '!re' element
        if '=' in item:
            key, value = item.split('=', 1)
            # Remove the leading dot if present
            key = key[1:] if key.startswith('.') else key
            # Convert 'true' and 'false' strings to boolean
            if value.lower() == 'true':
                value = True
            elif value.lower() == 'false':
                value = False
            result[key] = value
    return result


def parse_args():
    parser = argparse.ArgumentParser(description="Connect to MikroTik router")
    parser.add_argument('--dst', default="192.168.122.3", help="Destination IP address")
    parser.add_argument('--user', default="admin", help="Username")
    parser.add_argument('--passw', default="1", help="Password")
    parser.add_argument('--secure', action='store_true', help="Use secure connection")
    parser.add_argument('--port', type=int, default=0, help="Port number (0 for default)")

    args, unknown = parser.parse_known_args()
    for arg in unknown:
        if '=' in arg:
            key, value = arg.split('=', 1)
            setattr(args, key.lstrip('-'), value)

    return args


def parse_commands(file):
    result = []
    for line in file:
        line = line.strip()
        if not line:  # Skip empty lines
            continue
        # Split the line into command and arguments
        match = re.match(r'(.*?)(\s+\S+=|\S+=)', line)
        if match:
            command = match.group(1).strip()
            args_part = line[len(match.group(1)):].strip()
        else:
            command = line
            args_part = ''

        # If there are arguments, split them
        if args_part:
            # Split arguments based on "key=value" pattern
            arguments = re.findall(r'(\S+=\S+)(?:\s|$)', args_part)
            # Ensure leading '=' for each argument
            arguments = ['=' + arg.lstrip('=') for arg in arguments]
        else:
            arguments = []

        # Combine command and arguments into a single list
        result.append([command] + arguments)

    return result


def main():
    import os
    args = parse_args()

    if args.port == 0:
        args.port = 8729 if args.secure else 8728

    s = open_socket(args.dst, args.port, args.secure)
    if s is None:
        print("Could not open socket")
        sys.exit(1)

    apiros = ApiRos(s)
    if not apiros.login(args.user, args.passw):
        print("Login failed")
        sys.exit(1)

    commands = None

    current_dir = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(current_dir, 'router_cmd')
    with open(file_path, 'r') as file:
        commands = parse_commands(file)

    # Print the result
    for command in commands:
        r = apiros.command(command)
        print(r)


if __name__ == "__main__":
    main()