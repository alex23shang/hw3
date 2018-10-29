import udt
import time
import config
import util
# Stop-And-Wait reliable transport protocol.
class StopAndWait:
  # "msg_handler" is used to deliver messages to application layer
  # when it's ready.
  def __init__(self, local_ip, local_port, 
               remote_ip, remote_port, msg_handler):
    self.network_layer = udt.NetworkLayer(local_ip, local_port,
                                          remote_ip, remote_port, self)
    self.msg_handler = msg_handler
    self.start_time = 0.0
    self.time_on = False
    self.sender_type = config.MSG_TYPE_DATA
    self.sender_seq = 0
    self.packet = b''
    self.expect_seq = 0
    self.receiver_pack = util.make_pack_with_header(config.MSG_TYPE_ACK, 1)
  def is_timeout(self):
    return self.time_on and util.get_time() - self.start_time >= config.TIMEOUT_MSEC

  def start_timer(self):
    self.start_time = util.get_time()
    self.time_on = True
    
  def stop_time(self):
    self.time_on = False


  # "send" is called by application. Return true on success, false
  # otherwise.
  def send(self, msg):
    # TODO: impl protocol to send packet from application layer.
    # call self.network_layer.send() to send to network layer.
    
    if self.sender_type == config.MSG_TYPE_DATA and self.sender_seq == 0:
      self.packet = util.make_pack(self.sender_type, 0, msg)
      self.network_layer.send(self.packet)
      self.start_timer()
      self.sender_type = config.MSG_TYPE_ACK
      return True
    elif self.sender_type == config.MSG_TYPE_DATA and self.sender_seq == 1:
      self.packet = util.make_pack(self.sender_type, 1, msg)
      self.network_layer.send(self.packet)
      self.start_timer()
      self.sender_type = config.MSG_TYPE_ACK
      return True
    else:
      if self.is_timeout():  
        self.network_layer.send(self.packet)
        self.start_timer()
      return False
  # "handler" to be called by network layer when packet is ready.
  def handle_arrival_msg(self):
    msg = self.network_layer.recv()
    # TODO: impl protocol to handle arrived packet from network layer.
    # call self.msg_handler() to deliver to application layer.
    if msg and util.is_sender(msg):
      if self.sender_type == config.MSG_TYPE_ACK and not util.is_corrupt(msg) and self.sender_seq == 0 and util.valid_seq(msg, 0):
        self.stop_time()
        self.sender_seq = 1
        self.sender_type = config.MSG_TYPE_DATA
      elif self.sender_type == config.MSG_TYPE_ACK and not util.is_corrupt(msg) and self.sender_seq == 1 and util.valid_seq(msg, 1):
        self.stop_time()
        self.sender_type = config.MSG_TYPE_DATA
        self.sender_seq = 0
    elif msg and not util.is_sender(msg):
      if self.expect_seq == 0:
        if not util.is_corrupt(msg) and util.valid_seq(msg, self.expect_seq):
          data = util.extract(msg)
          self.msg_handler(data)
          self.receiver_pack = util.make_pack_with_header(config.MSG_TYPE_ACK, 0)
          self.network_layer.send(self.receiver_pack)
          self.expect_seq = 1
        elif util.is_corrupt(msg) or not util.valid_seq(msg, self.expect_seq):
          self.network_layer.send(self.receiver_pack)
      elif self.expect_seq == 1:  
        if not util.is_corrupt(msg) and util.valid_seq(msg, self.expect_seq):
          data = util.extract(msg)
          self.receiver_pack = util.make_pack_with_header(config.MSG_TYPE_ACK, 1)
          self.msg_handler(data)
          self.network_layer.send(self.receiver_pack)
          self.expect_seq = 0
        elif util.is_corrupt(msg) or not util.valid_seq(msg, self.expect_seq):
          self.network_layer.send(self.receiver_pack)
  # Cleanup resources.
  def shutdown(self):
    # TODO: cleanup anything else you may have when implementing this
    # class.
    while True:
      if self.is_timeout():
        self.network_layer.send(self.packet)
        self.start_timer()
      if self.sender_type == config.MSG_TYPE_DATA:
        break
    self.network_layer.shutdown()