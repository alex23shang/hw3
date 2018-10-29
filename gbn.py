import udt
import config
import util

# Go-Back-N reliable transport protocol.
class GoBackN:
  # "msg_handler" is used to deliver messages to application layer
  # when it's ready.
  def __init__(self, local_ip, local_port,
               remote_ip, remote_port, msg_handler):
    self.network_layer = udt.NetworkLayer(local_ip, local_port,
                                          remote_ip, remote_port, self)
    self.msg_handler = msg_handler
    self.base = 1
    self.next_seq = 1
    self.expect_seq = 1
    self.start_time = 0.0
    self.packets = [None]
    self.sendpkt = util.make_pack_with_header(config.MSG_TYPE_ACK, 0)
    self.time_on = False
  # "send" is called by application. Return true on success, false
  # otherwise.
  def is_timeout(self):
    return self.time_on and util.get_time() - self.start_time >= config.TIMEOUT_MSEC

  def start_timer(self):
    self.start_time = util.get_time()
    self.time_on = True
    
  def stop_time(self):
    self.time_on = False

  def send(self, msg):
    # TODO: impl protocol to send packet from application layer.
    # call self.network_layer.send() to send to network layer.

    if(self.is_timeout()):
      self.start_timer()
      for i in range(self.base, self.next_seq):
        self.network_layer.send(packets[i])
      return False

    if self.next_seq < self.base + config.WINDOW_SIZE:
      pack = util.make_pack(config.MSG_TYPE_DATA, self.next_seq, msg)
      self.packets.append(pack)
      self.network_layer.send(self.packets[self.next_seq])
      print(pack)
      if self.base == self.next_seq:
        self.start_timer()
      self.next_seq += 1
      return True


    return False

  # "handler" to be called by network layer when packet is ready.
  def handle_arrival_msg(self):
    msg = self.network_layer.recv()
    # TODO: impl protocol to handle arrived packet from network layer.
    # call self.msg_handler() to deliver to application layer.
    if msg and util.is_sender(msg):
      if(not util.is_corrupt(msg)):
        self.base = util.get_seq(msg) + 1
        if self.base == self.next_seq:
          self.stop_time()
        else:
          self.start_timer() 
    elif msg and not util.is_sender(msg):
      if not util.is_corrupt(msg) and util.valid_seq(msg, self.expect_seq):
        data = util.extract(msg)
        self.msg_handler(data)
        self.sendpkt = util.make_pack_with_header(config.MSG_TYPE_ACK, self.expect_seq)
        self.expect_seq += 1
      self.network_layer.send(self.sendpkt)

  # Cleanup resources.
  def shutdown(self):
    # TODO: cleanup anything else you may have when implementing this
    # class.
    while self.base < self.next_seq:
      if self.is_timeout():
        for i in range(self.base, self.next_seq):
          self.network_layer.send(self.packets[i])
    self.network_layer.shutdown()