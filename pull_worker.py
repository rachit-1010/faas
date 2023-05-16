import sys
import zmq
from message import WorkerToDispatcherMessage, DispatcherToWorkerMessage
import time
import multiprocessing
import serialize
import threading
from async_util import async_wrapper

class PullWorker():
  def __init__(self, num_procs, dispatcher_url, polling_interval=0.1):
    self.num_procs = num_procs
    self.dispatcher_url = dispatcher_url
    self.context = zmq.Context()
    self.socket = self.context.socket(zmq.REQ)
    self.num_avail_procs = self.num_procs
    self.polling_interval = polling_interval
    self.pool = multiprocessing.Pool(self.num_procs)
    self.lock = threading.Lock()


  def send_and_receive_message(self, m_send):
    with self.lock:
      self.socket.connect(self.dispatcher_url)
      self.socket.send_pyobj(m_send)
      m_recv = self.socket.recv_pyobj()
      self.socket.disconnect(self.dispatcher_url)
    return m_recv

  def callback(self, result, task_id):
    m_send = WorkerToDispatcherMessage(has_result=True, task_id=task_id, result=serialize.serialize(result), status="COMPLETED")
    m_recv = self.send_and_receive_message(m_send)
    self.num_avail_procs += 1
    
  def error_callback(self, result, task_id):
    m_send = WorkerToDispatcherMessage(has_result=True, task_id=task_id, result=serialize.serialize(result), status="FAILURE")
    m_recv = self.send_and_receive_message(m_send)
    self.num_avail_procs += 1

  def execute_task(self, m):
    lambda_callback = lambda result : self.callback(result, m.task_id)
    lambda_error_callback = lambda result : self.error_callback(result, m.task_id)
    self.pool.apply_async(async_wrapper, (m.fn_payload, m.param_payload), {}, lambda_callback, lambda_error_callback)


  def run(self):
    while (True):
      if (self.num_avail_procs > 0):
        m_send = WorkerToDispatcherMessage(has_result=False, task_id="", result="", status="")
        m_recv = self.send_and_receive_message(m_send)
        if (m_recv.has_task):
          self.num_avail_procs -= 1
          self.execute_task(m_recv)
      
      time.sleep(self.polling_interval)

    
if __name__ == '__main__':
  if (len(sys.argv) != 3):
    print("usage: python3 pull_worker.py <num_worker_processors> <dispatcher url>")
    sys.exit()
  
  num_procs = int(sys.argv[1])
  dispatcher_url = sys.argv[2]

  worker = PullWorker(num_procs, dispatcher_url, 0.1)
  worker.run()

