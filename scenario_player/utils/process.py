import errno
import socket
from contextlib import closing
from socket import SocketKind

from raiden.network.utils import LOOPBACK


def unused_port() -> int:
    socket_kind = SocketKind.SOCK_STREAM

    while True:
        # Don't inline the variable until
        # https://github.com/PyCQA/pylint/issues/1437 is fixed
        sock = socket.socket(socket.AF_INET, socket_kind)
        with closing(sock):
            # Force the port into TIME_WAIT mode, ensuring that it will not
            # be considered 'free' by the OS for the next 60 seconds. This
            # does however require that the process using the port sets
            # SO_REUSEADDR on it's sockets. Most 'server' applications do.
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                sock.bind((LOOPBACK, 0))
            except OSError as ex:
                if ex.errno == errno.EADDRINUSE:
                    continue
                raise

            sock_addr = sock.getsockname()
            port = int(sock_addr[1])

            # Connect to the socket to force it into TIME_WAIT state (see
            # above)
            sock.listen(1)
            sock2 = socket.socket(socket.AF_INET, socket_kind)
            with closing(sock2):
                sock2.connect(sock_addr)
                sock.accept()

        return port
