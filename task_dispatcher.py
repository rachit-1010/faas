import argparse
import redis
import serialize
from multiprocessing import Pool


class TaskDispacher():
  def __init__(self, args):
    self.mode = args.m
    self.port = args.p
    self.num_workers = args.w
    self.redis = redis.Redis(host='localhost', port=6379)
    self.pubsub = self.redis.pubsub()
    self.pubsub.subscribe('tasks')
    self.pool = Pool(self.num_workers)

  def callback(self, result):
    print("Callback")
    print(result)
    
  def error_callback(self, error):
    print("Error Callback")
    print(error)


  def execute_local(self, task_id, fn_payload, param_payload):
    # TODO:
    # 1. Try catch for error
    # 2. Add logic for assigning tasks based on operation mode - split into functions for local/push/pull
    # 3. Spawn self.num_worker procs for Local worker using multiprocessing pool
    # def cb (result) :
    #   print(self.mode, result)
    fn = serialize.deserialize(fn_payload)
    print(fn)
    args, kwargs = serialize.deserialize(param_payload)
    print(args)
    print(kwargs)
    self.pool.apply_async(fn, args, kwargs, self.callback, self.error_callback)

    # self.redis.hset(task_id, 'status', 'COMPLETED')
    # self.redis.hset(task_id, 'result', serialize.serialize(result))
    # print(result)

  def execute_pull(self, task_id, fn_payload, param_payload):
    pass

  def execute_push(self, task_id, fn_payload, param_payload):
    pass


  def execute_task(self, task_id, fn_payload, param_payload):
    if (self.mode == 'local'):
      self.execute_local(task_id, fn_payload, param_payload)
    elif (self.mode == 'pull'):
      self.execute_pull(task_id, fn_payload, param_payload)
    elif (self.mode == 'push'):
      self.execute_push(task_id, fn_payload, param_payload)


  def run(self):
    for message in self.pubsub.listen():
      # Filter only valid messages 
      if message['type'] == 'message':
        task_id = message['data']
        fn_payload = self.redis.hget(task_id, 'fn_payload').decode("utf-8")
        param_payload = self.redis.hget(task_id, 'param_payload').decode("utf-8")
        self.execute_task(task_id, fn_payload, param_payload)


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