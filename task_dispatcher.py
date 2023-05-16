import argparse
import redis
import serialize
import multiprocessing
import dill
import threading
import queue
import zmq
from message import WorkerToDispatcherMessage, DispatcherToWorkerMessage
import time
from async_util import async_wrapper


class TaskDispacher():
  def __init__(self, args):
    self.mode = args.m
    self.port = args.p
    self.num_workers = args.w
    self.redis = redis.Redis(host='localhost', port=6379)
    self.pubsub = self.redis.pubsub()
    self.pubsub.subscribe('tasks')
    self.pool = multiprocessing.Pool(self.num_workers)
    self.task_queue = queue.Queue() # Thread safe queue
    # self.pool = multiprocessing.get_context('spawn').Pool(self.num_workers)
    self.context = zmq.Context()
    self.socket = None
    if (self.mode == "pull"):
      self.socket =  self.context.socket(zmq.REP)
    elif (self.mode == "push"):
      self.socket =  self.context.socket(zmq.ROUTER)
    
    if (self.mode != "local"):
      self.socket.bind('tcp://127.0.0.1:' + str(self.port))
    
    self.worker_availability = {}
    self.polling_interval = 0.1
    self.lock = threading.Lock()

  def callback(self, result, task_id):
    print("Callback for ", task_id)
    print(result)
    self.redis.hset(task_id, 'result', serialize.serialize(result))
    self.redis.hset(task_id, 'status', 'COMPLETED')

    
  def error_callback(self, result, task_id):
    print("Error Callback", task_id)
    print(result)
    self.redis.hset(task_id, 'result', serialize.serialize(result))
    self.redis.hset(task_id, 'status', 'FAILURE')

  

  def execute_local(self):
    # TODO:
    # 1. Try catch for error
    # 2. Add logic for assigning tasks based on operation mode - split into functions for local/push/pull
    # 3. Spawn self.num_worker procs for Local worker using multiprocessing pool

    while True:
      task = self.task_queue.get()
      task_id = task['task_id']
      fn_payload = task['fn_payload']
      param_payload = task['param_payload']

      fn = serialize.deserialize(fn_payload)
      print(fn)
      args, kwargs = serialize.deserialize(param_payload)
      print(args)
      print(kwargs)
      # set_start_method('fork')
      lambda_callback = lambda result : self.callback(result, task_id)
      lambda_error_callback = lambda result : self.error_callback(result, task_id)

      res = self.pool.apply_async(async_wrapper, (fn_payload, param_payload), {}, lambda_callback, lambda_error_callback)
      print("Execute_local")
      print(res)
      # self.redis.hset(task_id, 'status', 'COMPLETED')
      # self.redis.hset(task_id, 'result', serialize.serialize(result))
    # print(result)

  def set_result(self, m_recv):
    self.redis.hset(m_recv.task_id, 'result', m_recv.result)
    self.redis.hset(m_recv.task_id, 'status', m_recv.status)
    m_send = DispatcherToWorkerMessage(has_task=False, task_id="", fn_payload="", param_payload="")
    self.socket.send_pyobj(m_send)
  

  def send_pull_worker_task(self):
    m_send = DispatcherToWorkerMessage(has_task=False, task_id="", fn_payload="", param_payload="")
    print("Queue size = ",self.task_queue.qsize() )
    if (self.task_queue.qsize() > 0):
      task = self.task_queue.get()
      m_send.has_task = True
      m_send.task_id = task['task_id']
      m_send.fn_payload = task['fn_payload']
      m_send.param_payload = task['param_payload']
    
    self.socket.send_pyobj(m_send)
  

  def execute_pull(self):
    print("Listening to pull")

    while True:
      m_recv = self.socket.recv_pyobj()
      print("received pyobj")
      if (m_recv.has_result):
        # Got a result from worker. Set the output into redis DB
        self.set_result(m_recv)
      else:
        # Pop a task from queue if available and send it to worker
        self.send_pull_worker_task()


  def poll_push_worker(self):
    # Listen to push workers for regsitration and result messages
    while True:

      try:
        print("Trying to listen to worker")
        with self.lock:
          print("Lock acquired")
          m_recv = self.socket.recv_multipart(flags=zmq.NOBLOCK)
          print("Released lock")

        worker_id = m_recv[0]
        worker_response = dill.loads(m_recv[1])

        print("Worker Id = ", worker_id)
        if (hasattr(worker_response, 'num_procs')):
          # It is a new worker registration message
          print("Registered new worker with num procs = ", worker_response.num_procs)
          self.worker_availability[worker_id] = worker_response.num_procs
        else:
          # It is a result message
          self.set_result(worker_response)
          self.worker_availability[worker_id] += 1
      
      except:
        print("In exception. Sleep now")
        time.sleep(self.polling_interval)
      
  # Get best worker based on availability and using load balancing
  def get_free_worker(self):
    worker_id = max(self.worker_availability, key=self.worker_availability.get)
    if (self.worker_availability[worker_id] <= 0):
      return None
    return worker_id

  def send_push_worker_task(self):
    # Pop tasks from task_queue and assign to workers using load balancing
    while True:
      if self.task_queue.qsize() > 0 :
        worker_id = self.get_free_worker()
        if (worker_id != None):
          task = self.task_queue.get()
          m_send = DispatcherToWorkerMessage(has_task=True, task_id=task['task_id'], fn_payload=task['fn_payload'], param_payload=task['param_payload'])
          with self.lock:
            self.socket.send_multipart([worker_id, dill.dumps(m_send)])
          self.worker_availability[worker_id] -= 1
        else:
          time.sleep(self.polling_interval)
      else:
        time.sleep(self.polling_interval)


  def execute_push(self):
    poll_push_worker_thread = threading.Thread(target=self.poll_push_worker)
    poll_push_worker_thread.start()

    send_push_worker_task_thread = threading.Thread(target=self.send_push_worker_task)
    send_push_worker_task_thread.start()


  def execute_task(self):
    if (self.mode == 'local'):
      self.execute_local()
    elif (self.mode == 'pull'):
      self.execute_pull()
    elif (self.mode == 'push'):
      self.execute_push()

  def redis_subscriber(self):
    print("Listening to redis pubsub")
    for message in self.pubsub.listen():
      # Filter only valid messages 
      if message['type'] == 'message':
        task_id = message['data']
        print("Received task in pubsub", message)
        fn_payload = self.redis.hget(task_id, 'fn_payload').decode("utf-8")
        param_payload = self.redis.hget(task_id, 'param_payload').decode("utf-8")
        self.task_queue.put({'task_id' : task_id, 'fn_payload': fn_payload, 'param_payload': param_payload})


  def run(self):
    redis_subscriber_thread = threading.Thread(target=self.redis_subscriber)
    redis_subscriber_thread.start()

    execute_task_thread = threading.Thread(target=self.execute_task)
    execute_task_thread.start()

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-m', type=str, default='local')
    parser.add_argument('-p', type=int, default=5500)
    parser.add_argument('-w', type=int, default=1)
    args = parser.parse_args()

    # TODO: Add argument validation

    task_dispacher = TaskDispacher(args)
    task_dispacher.run()


# References:
# Redis pubsub: https://stackoverflow.com/questions/7871526/is-non-blocking-redis-pubsub-possible
# Deserialized function usage in multiprocessing: https://stackoverflow.com/questions/19984152/what-can-multiprocessing-and-dill-do-together
# Argmax of python dict : https://stackoverflow.com/questions/268272/getting-key-with-maximum-value-in-dictionary