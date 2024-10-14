import binascii, socket, select, ssl
import hashlib
import argparse
import re
from os import error
from typing import Callable, Optional, Any, Dict
class CallbackList:
    def __init__(self, cb: Callable[..., Any], next_cb: Optional['CallbackList'] = None, **args):
        self._end_callback: Optional[Callable[..., Any]] = None
        self._current: Callable[..., Any] = cb
        self._next: Optional['CallbackList'] = next_cb
        self._args: Dict[str, Any] = args
        self._previous: Optional['CallbackList'] = None

    def add(self, cb: Callable[..., Any], **args) -> 'CallbackList':
        new_node = CallbackList(cb, None, **args)
        return self.append(new_node)

    def append(self, new_node: 'CallbackList') -> 'CallbackList':
        """
        TODO add some method named like finish that reverses list 
        """
        new_node._previous = self
        current = self
        while current._next:
            current = current._next
        # go to the tail: reverse list, connect to the last element
        current._next = new_node
        return self

    def previous(self) -> tuple[Optional['CallbackList'], Dict[str, Any]]:
        if self._previous:
            return self._previous, self._previous._args
        return None, {}
    def current(self) -> tuple[Callable[..., Any], Dict[str, Any]]:
        return self._current, self._args
    def next(self):
        nxt = self._next
        self._current = nxt._current
        self._args = nxt._args
        self._next = nxt._next
        self._previous = nxt._previous

    def retry(self):
        pass
    def is_tail(self):
        return self._next == self._end_callback

    def branch(self, skip_to: 'CallbackList'):
        skip_to._previous = self
        self._next = skip_to


MAX_BUFFER_SIZE=1024*1024*64
def read_until(condition_fn: Callable[[...], Any]):
    def _read_until(stream, events, data: ConsoleContext, **args):
        console = data.console
        decoded_buffer = getattr(data, 'decoded_buffer', '')
        remaining_bytes = getattr(data, 'remaining_bytes', b'')

        while True:
            if len(remaining_bytes) > MAX_BUFFER_SIZE:
                raise BufferError()

            recv_data = console.stream.recv(1024 * 32)
            if isinstance(recv_data, int) and recv_data <= 0:
                """Console not ready. Continue from __init__ main loop"""
                data.set_return(decoded_buffer=decoded_buffer, remaining_bytes=remaining_bytes)
                return None

            while recv_data != b'':
                new_data = console.stream.recv(1024 * 32)
                if not isinstance(new_data, int) or new_data > 0:
                    recv_data += new_data
                else:
                    break

            recv_data = remaining_bytes + recv_data
            try:
                decoded_data = recv_data.decode('utf-8')
                remaining_bytes = b''
            except UnicodeDecodeError as e:
                error_pos = e.start
                decoded_data = recv_data[:error_pos].decode('utf-8')
                remaining_bytes = recv_data[error_pos:]

            decoded_buffer += decoded_data
            os.write(1, decoded_data.encode("utf-8"))

            res = condition_fn(decoded_buffer, **args)
            if res:
                ret = data.set_return(**res)
                return ret


    return _read_until



def find_str(decoded, **args):
    pattern = args['pattern']
    match = re.search(pattern, decoded)
    if match:
         return {'match': match}
    return None

def continue_read(decoded, **args):
    return True


def send_command(cmd):
    def _send(stream, events, context, **args):
        nonlocal cmd
        if not cmd.endswith('\n'):
            cmd += '\n'
        try:
            context.console.stream.send(cmd.encode('utf-8'))
        except libvirt.libvirtError as e:
            # if you debug it can result in broken pipe when send is called
            error(e)
            breakpoint()
            return None
        return context
    return _send



def lifecycle_callback (connection, domain, event, detail, console):
    console.state = console.domain.state(0)
    logging.info("%s transitioned to state %d, reason %d",
                 console.name, console.state[0], console.state[1])



class ConsoleContext:
    def __init__(self, console, callbacks: 'CallbackList'):
        self.console = console
        self._callbacks = callbacks
    @property
    def callbacks(self):
        return self._callbacks

    def update_callbacks(self, cb):
        self._callbacks = cb
    def __copy__(self):
        new_instance = self.__class__.__new__(self.__class__)
        new_instance.__dict__.update(self.__dict__)
        return new_instance

    def set_return(self, **args):
        for field, value in args.items():
            setattr(self, field, value)
        return self




class LibvirtConsoleHandler:
    def __init__(self, console: Any, initial_callbacks: CallbackList):
        self._context = ConsoleContext(console, initial_callbacks)
        console.stdin_watch = libvirt.virEventAddHandle(0, libvirt.VIR_EVENT_HANDLE_READABLE, self.stdin_callback, console)

    def stdin_callback(self, watch: int, fd: int, events: int, console: Console) -> None:
        readbuf = os.read(fd, 1024)
        if readbuf.startswith(b""):
            console.run_console = False
            return
        if console.stream:
            console.stream.send(readbuf)

    def main_callback(self, stream: Any, events: int, data: ConsoleContext) -> None:
        self._context = data  # Update the current data
        while True:
            callbacks = self._context.callbacks
            if callbacks.is_tail():
                stream.eventRemoveCallback()
                return

            current_fn, args = callbacks.current()
            result = current_fn(stream, events, self._context, **args)

            if result is None:
                self._handle_no_result(args)
                return
            else:
                self._context = result
                callbacks.next()

    def _handle_no_result(self, args):
        if 'skip_to' in args:
            skip_to: Optional['CallbackList'] = args['skip_to']
            self._context.callbacks.branch(skip_to)
        else:
            self._context.callbacks.retry()

    def check_console(self) -> bool:
        console = self._context.console
        if (console.state[0] == libvirt.VIR_DOMAIN_RUNNING or
            console.state[0] == libvirt.VIR_DOMAIN_PAUSED):
            if console.stream is None:
                console.stream = console.connection.newStream(libvirt.VIR_STREAM_NONBLOCK)
                console.domain.openConsole(None, console.stream, libvirt.VIR_DOMAIN_CONSOLE_FORCE)
                console.stream.eventAddCallback(libvirt.VIR_STREAM_EVENT_READABLE, self.main_callback, self._context)
        else:
            if console.stream:
                console.stream.eventRemoveCallback()
                console.stream = None

        return console.run_console

    def run(self) -> None:
        # If console.stream.recv returns -2 on read it will become availiable after this call. If it actually has data
        while self.check_console():
            libvirt.virEventRunDefaultImpl()




"""
https://libvirt.org/formatdomain.html#relationship-between-serial-ports-and-consoles
https://gitlab.com/qemu-project/qemu/-/blob/master/include/hw/virtio/virtio-serial.h?ref_type=heads#L215
https://github.com/qemu/qemu/blob/e22f675bdd3689472032d0de0799519c3e07fd2c/hw/char/virtio-console.c
"""
def main2():
    """
    Example for Mikrotik Cloud Hosted Router
    Althoug the same task can be acoplished using standart UNIX utils
    like cat, grep and echo 
    The simplest example:  
        terminal1: cat /dev/pts/5 
        terminal2: echo "something" > /dev/pts/5
    """

    print ("Escape character is ^]")
    logging.basicConfig(filename='msg.log', level=logging.DEBUG)

    libvirt.virEventRegisterDefaultImpl()
    libvirt.registerErrorHandler(error_handler, None)

    console = Console("qemu:///session", 'linux2022')

    cb = CallbackList(read_until(find_str), pattern="new password")
    cb = cb.add(send_command("123456"))
    cb = cb.add(read_until(find_str), pattern="repeat new password")
    pw_cb = cb.add(send_command("123456"))

    # set processing using callbacks linked list
    cb = CallbackList(read_until(find_str), None, pattern="Login:")
    cb = cb.add(send_command("admin"))
    cb = cb.add(read_until(find_str), pattern="Password:")
    cb = cb.add(send_command("\n"))
    cb = cb.add(read_until(find_str), pattern="Do you want to see the software license", )
    cb = cb.add(send_command("N"))
    cb = cb.append(pw_cb)


    processor = LibvirtConsoleHandler(console, cb)
    processor.run()



if __name__ == "__main__":
    main2()
