import sys
import zmq
from message import WorkerToDispatcherMessage, DispatcherToWorkerMessage, WorkerRegistrationMessage
import time
import multiprocessing
import dill
import serialize
import threading


dill.Pickler.dumps, dill.Pickler.loads = dill.dumps, dill.loads
multiprocessing.reduction.ForkingPickler = dill.Pickler
multiprocessing.reduction.dump = dill.dump

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

  def send_result(self, m_send):
    with self.lock:
      self.socket.send(dill.dumps(m_send))

  def callback(self, result, task_id):
    print("Callback for ", task_id)
    print(result)
    m_send = WorkerToDispatcherMessage(has_result=True, task_id=task_id, result=serialize.serialize(result), status="COMPLETED")
    self.send_result(m_send)
    
  def error_callback(self, result, task_id):
    print("Error Callback", task_id)
    print(result)
    m_send = WorkerToDispatcherMessage(has_result=True, task_id=task_id, result=serialize.serialize(result), status="FAILURE")
    self.send_result(m_send)

  def execute_task(self, m):
    print("Attempting to deserialize")
    fn = serialize.deserialize(m.fn_payload)
    args, kwargs = serialize.deserialize(m.param_payload)
    print("Deserialization successful")
    lambda_callback = lambda result : self.callback(result, m.task_id)
    lambda_error_callback = lambda result : self.error_callback(result, m.task_id)
    print("Inserting task into pool:", m.task_id)
    res = self.pool.apply_async(fn, args, kwargs, lambda_callback, lambda_error_callback)
    print("Insertion successful")

  def run(self):
    # Register worker with task dispatcher, and announce number of available procs with worker
    m_registration = WorkerRegistrationMessage(self.num_procs)
    self.socket.send(dill.dumps(m_registration))
    # msg = "Hello"
    # self.socket.send(msg.encode())

    print("Sent registration message")
    # Listen to tasks from dispatcher
    while (True):
      try:
        with self.lock:
          task = dill.loads(self.socket.recv(flags=zmq.NOBLOCK))
        print("Received task to work on")
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

