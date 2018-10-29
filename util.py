import config
import dummy
import gbn
import ss
import threading
import struct
import time


# Factory method to construct transport layer.

def get_type(msg):
  return struct.unpack('!H', msg[0:2])[0]

def get_seq(msg):
  return struct.unpack('!H', msg[2:4])[0]

def get_sum(msg):
  return struct.unpack('!H', msg[4:6])[0]

def get_data(msg):
  return msg[6:]

def help_sum(num1, num2):
  res = num1 + num2
  return res

def get_time():
  return int(round(time.time() * 1000))

def cal_checksum(type, seq, data):
  res = help_sum(type, seq)
  carry = data[0:]
  if len(carry) % 2 == 1: 
    carry += b'\x00'
  for i in range(0, len(carry), 2):
    tmp = carry[i] + (carry[i+1] << 8)
    res = help_sum(res, tmp)
  return res % 65536

def is_sender(msg):
  return get_type(msg) == config.MSG_TYPE_ACK

def extract(msg):
  return msg[6::]

def is_corrupt(msg):
  type = struct.unpack('!H', msg[0:2])[0]
  seq = struct.unpack('!H', msg[2:4])[0]
  checksum = struct.unpack('!H', msg[4:6])[0]
  return checksum != cal_checksum(type, seq, msg[6:])

def make_pack_with_header(type, seq):
  res = b''
  res += struct.pack('!H', type)
  res += struct.pack('!H', seq)
  res += struct.pack('!H', cal_checksum(type, seq, b''))
  return res

def make_pack(type, seq, msg):
  res = b''
  res += struct.pack('!H', type)
  res += struct.pack('!H', seq)
  res += struct.pack('!H', cal_checksum(type, seq, msg))
  res += msg
  return res

def valid_seq(msg, expect_seq):
  return get_seq(msg) == expect_seq


def get_transport_layer(sender_or_receiver,
                        transport_layer_name,
                        msg_handler):
  assert sender_or_receiver == 'sender' or sender_or_receiver == 'receiver'
  if sender_or_receiver == 'sender':
    return _get_transport_layer_by_name(transport_layer_name,
                                        config.SENDER_IP_ADDRESS,
                                        config.SENDER_LISTEN_PORT,
                                        config.RECEIVER_IP_ADDRESS,
                                        config.RECEIVER_LISTEN_PORT,
                                        msg_handler)
  if sender_or_receiver == 'receiver':
    return _get_transport_layer_by_name(transport_layer_name,
                                        config.RECEIVER_IP_ADDRESS,
                                        config.RECEIVER_LISTEN_PORT,
                                        config.SENDER_IP_ADDRESS,
                                        config.SENDER_LISTEN_PORT,
                                        msg_handler)


def _get_transport_layer_by_name(name, local_ip, local_port, 
                                 remote_ip, remote_port, msg_handler):
  assert name == 'dummy' or name == 'ss' or name == 'gbn'
  if name == 'dummy':
    return dummy.DummyTransportLayer(local_ip, local_port,
                                     remote_ip, remote_port, msg_handler)
  if name == 'ss':
    return ss.StopAndWait(local_ip, local_port,
                          remote_ip, remote_port, msg_handler)
  if name == 'gbn':
    return gbn.GoBackN(local_ip, local_port,
                       remote_ip, remote_port, msg_handler)


# Convenient class to run a function periodically in a separate
# thread.
class PeriodicClosure:
  def __init__(self, handler, interval_sec):
    self._handler = handler
    self._interval_sec = interval_sec
    self._lock = threading.Lock()
    self._timer = None

  def _timeout_handler(self):
    with self._lock:
      self._handler()
      self.start()

  def start(self):
    self._timer = threading.Timer(self._interval_sec, self._timeout_handler)
    self._timer.start()

  def stop(self):
    with self._lock:
      if self._timer:
        self._timer.cancel()