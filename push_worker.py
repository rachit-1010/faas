import sys
import zmq
from message import WorkerToDispatcherMessage, DispatcherToWorkerMessage, WorkerRegistrationMessage
import time
import multiprocessing
import dill
import serialize
import threading
from async_util import async_wrapper

class PushWorker():
  def __init__(self, num_procs, dispatcher_url, polling_interval=0.1):
    self.num_procs = num_procs
    self.dispatcher_url = dispatcher_url
    self.context = zmq.Context()
    self.socket = self.context.socket(zmq.DEALER)
    self.socket.connect(self.dispatcher_url)
    self.polling_interval = polling_interval
    self.pool = multiprocessing.Pool(self.num_procs)
    self.lock = threading.Lock()
  
  def __del__(self):
    self.socket.disconnect(self.dispatcher_url)

  def send_result(self, m_send):
    with self.lock:
      self.socket.send(dill.dumps(m_send))

  def callback(self, result, task_id):
    m_send = WorkerToDispatcherMessage(has_result=True, task_id=task_id, result=serialize.serialize(result), status="COMPLETED")
    self.send_result(m_send)
    
  def error_callback(self, result, task_id):
    m_send = WorkerToDispatcherMessage(has_result=True, task_id=task_id, result=serialize.serialize(result), status="FAILED")
    self.send_result(m_send)

  def execute_task(self, m):
    lambda_callback = lambda result : self.callback(result, m.task_id)
    lambda_error_callback = lambda result : self.error_callback(result, m.task_id)
    self.pool.apply_async(async_wrapper, (m.fn_payload, m.param_payload), {}, lambda_callback, lambda_error_callback)

  def run(self):
    # Register worker with task dispatcher, and announce number of available procs with worker
    m_registration = WorkerRegistrationMessage(self.num_procs)
    self.socket.send(dill.dumps(m_registration))

    while (True):
      try:
        with self.lock:
          task = dill.loads(self.socket.recv(flags=zmq.NOBLOCK))
        self.execute_task(task)
      except:
        time.sleep(self.polling_interval)
      

if __name__ == '__main__':
  if (len(sys.argv) != 3):
    print("usage: python3 push_worker.py <num_worker_processors> <dispatcher url>")
    sys.exit()
  
  num_procs = int(sys.argv[1])
  dispatcher_url = sys.argv[2]

  worker = PushWorker(num_procs, dispatcher_url, 0.1)
  worker.run()

