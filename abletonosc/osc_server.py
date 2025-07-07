from typing import Tuple, Any, Callable
from .constants import OSC_LISTEN_PORT, OSC_RESPONSE_PORT
from ..pythonosc.osc_message import OscMessage, ParseError
from ..pythonosc.osc_message_builder import OscMessageBuilder, BuildError

import re
import errno
import socket
import logging
import traceback
import time

class OSCServer:
    def __init__(self,
                 local_addr: Tuple[str, int] = ('0.0.0.0', OSC_LISTEN_PORT),
                 remote_addr: Tuple[str, int] = ('127.0.0.1', OSC_RESPONSE_PORT)):
        """
        Class that handles OSC server responsibilities, including support for sending
        reply messages.

        Implemented because pythonosc's OSC server causes a beachball when handling
        incoming messages. To investigate, as it would be ultimately better not to have
        to roll our own.

        Args:
            local_addr: Local address and port to listen on.
                        By default, binds to the wildcard address 0.0.0.0, which means listening on
                        every available local IPv4 interface (including 127.0.0.1).
            remote_addr: Remote address to send replies to, by default. Can be overridden in send().
        """

        self._local_addr = local_addr
        self._remote_addr = remote_addr
        self._response_port = remote_addr[1]

        self._socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._socket.setblocking(0)
        self._socket.bind(self._local_addr)
        self._callbacks = {}

        self.logger = logging.getLogger("abletonosc")
        self.logger.info("Starting OSC server (local %s, response port %d)",
                         str(self._local_addr), self._response_port)
        
        # DEBUG: Add TouchOSC debugging
        self.debug_touchosc = True
        self.message_count = 0
        self.listener_message_count = 0

    def add_handler(self, address: str, handler: Callable) -> None:
        """
        Add an OSC handler.

        Args:
            address: The OSC address string
            handler: A handler function, with signature:
                     params: Tuple[Any, ...]
        """
        self._callbacks[address] = handler

    def clear_handlers(self) -> None:
        """
        Remove all existing OSC handlers.
        """
        self._callbacks = {}

    def send(self,
             address: str,
             params: Tuple = (),
             remote_addr: Tuple[str, int] = None) -> None:
        """
        Send an OSC message.

        Args:
            address: The OSC address (e.g. /frequency)
            params: A tuple of zero or more OSC params
            remote_addr: The remote address to send to, as a 2-tuple (hostname, port).
                         If None, uses the default remote address.
        """
        msg_builder = OscMessageBuilder(address)
        for param in params:
            msg_builder.add_arg(param)

        try:
            msg = msg_builder.build()
            if remote_addr is None:
                remote_addr = self._remote_addr
            self._socket.sendto(msg.dgram, remote_addr)
        except BuildError:
            self.logger.error("AbletonOSC: OSC build error: %s" % (traceback.format_exc()))

    def process(self) -> None:
        """
        Synchronously process all data queued on the OSC socket.
        """
        try:
            repeats = 0
            while True:
                repeats += 1
                if repeats > 20:
                    self.logger.error(f"TOO MANY REPEATS IN SINGLE TICK! Last message: {message.address if 'message' in locals() else 'unknown'}")
                    fd = open("/tmp/TOO_MANY_REPEATS", "w")
                    # Fix: Convert bytes to string
                    fd.write(data.decode('utf-8', errors='ignore'))
                    fd.close()
                    break
                #--------------------------------------------------------------------------------
                # Loop until no more data is available.
                #--------------------------------------------------------------------------------
                data, remote_addr = self._socket.recvfrom(65536)
                #--------------------------------------------------------------------------------
                # Update the default reply address to the most recent client. Used when
                # sending (e.g) /live/song/beat messages and listen updates.
                #
                # This is slightly ugly and prevents registering listeners from different IPs.
                #--------------------------------------------------------------------------------
                self._remote_addr = (remote_addr[0], OSC_RESPONSE_PORT)
                try:
                    message = OscMessage(data)
                    
                    # DEBUG: Log all messages if debugging is enabled
                    if self.debug_touchosc:
                        self.message_count += 1
                        if "listen" in message.address:
                            self.listener_message_count += 1
                            self.logger.warning(f"[DEBUG {time.time():.3f}] LISTENER MSG #{self.listener_message_count}: {message.address} params: {message.params}")
                        elif self.message_count % 10 == 0 or "refresh" in message.address or "get" in message.address:
                            self.logger.info(f"[DEBUG] OSC msg #{self.message_count}: {message.address} params: {message.params[:3]}...")  # Limit param logging

                    if message.address in self._callbacks:
                        callback = self._callbacks[message.address]
                        
                        # DEBUG: Log callback execution time for listeners
                        if self.debug_touchosc and "listen" in message.address:
                            start_time = time.time()
                            rv = callback(message.params)
                            elapsed = time.time() - start_time
                            if elapsed > 0.1:  # Log slow callbacks
                                self.logger.warning(f"[DEBUG] SLOW CALLBACK: {message.address} took {elapsed:.3f}s")
                        else:
                            rv = callback(message.params)

                        if rv is not None:
                            assert isinstance(rv, tuple)
                            remote_hostname, _ = remote_addr
                            response_addr = (remote_hostname, self._response_port)
                            self.send(address=message.address,
                                      params=rv,
                                      remote_addr=response_addr)
                    elif "*" in message.address:
                        if self.debug_touchosc:
                            self.logger.info(f"[DEBUG] Wildcard OSC address: {message.address}")
                            
                        regex = message.address.replace("*", "[^/]+")
                        matched_count = 0
                        for callback_address, callback in self._callbacks.items():
                            if re.match(regex, callback_address):
                                matched_count += 1
                                try:
                                    rv = callback(message.params)
                                except ValueError:
                                    #--------------------------------------------------------------------------------
                                    # Don't throw errors for queries that require more arguments
                                    # (e.g. /live/track/get/send with no args)
                                    #--------------------------------------------------------------------------------
                                    continue
                                except AttributeError:
                                    #--------------------------------------------------------------------------------
                                    # Don't throw errors when trying to create listeners for properties that can't
                                    # be listened for (e.g. can_be_armed, is_foldable)
                                    #--------------------------------------------------------------------------------
                                    continue
                                if rv is not None:
                                    assert isinstance(rv, tuple)
                                    remote_hostname, _ = remote_addr
                                    response_addr = (remote_hostname, self._response_port)
                                    self.send(address=callback_address,
                                              params=rv,
                                              remote_addr=response_addr)
                        
                        if self.debug_touchosc and matched_count > 0:
                            self.logger.info(f"[DEBUG] Wildcard matched {matched_count} callbacks")
                    else:
                        self.logger.error("AbletonOSC: Unknown OSC address: %s" % message.address)
                except ParseError:
                    self.logger.error("AbletonOSC: OSC parse error: %s" % (traceback.format_exc()))

        except socket.error as e:
            if e.errno == errno.ECONNRESET:
                #--------------------------------------------------------------------------------
                # This benign error seems to occur on startup on Windows
                #--------------------------------------------------------------------------------
                self.logger.warning("AbletonOSC: Non-fatal socket error: %s" % (traceback.format_exc()))
            elif e.errno == errno.EAGAIN or e.errno == errno.EWOULDBLOCK:
                #--------------------------------------------------------------------------------
                # Another benign networking error, throw when no data is received
                # on a call to recvfrom() on a non-blocking socket
                #--------------------------------------------------------------------------------
                pass
            else:
                #--------------------------------------------------------------------------------
                # Something more serious has happened
                #--------------------------------------------------------------------------------
                self.logger.error("AbletonOSC: Socket error: %s" % (traceback.format_exc()))

        except Exception as e:
            self.logger.error("AbletonOSC: Error handling OSC message: %s" % e)
            self.logger.warning("AbletonOSC: %s" % traceback.format_exc())

    def shutdown(self) -> None:
        """
        Shutdown the server network sockets.
        """
        self._socket.close()
