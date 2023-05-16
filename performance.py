import subprocess
import requests
import serialize
import time

def mpcs_sleep(t):
  import time
  time.sleep(t)
  return t

class StrongScaling():
  def __init__(self, num_tasks, num_workers, num_procs, mode, port, param_payload):
    self.num_tasks = num_tasks
    self.num_workers = num_workers
    self.num_procs = num_procs
    self.mode = mode
    self.port = port
    self.param_payload = param_payload
    self.pending_task_ids = set()
    self.subprocesses = []
    self.fastapi_url = "http://127.0.0.1:8000/"
    self.fn_id = None
    self.polling_interval = 0.1
  
  def register_function(self):
    resp = requests.post(self.fastapi_url + "register_function",
                         json={"name": "mpcs_sleep",
                               "payload": serialize.serialize(mpcs_sleep)})
    fn_info = resp.json()
    assert "function_id" in fn_info
    return resp.json()["function_id"]

  # Returns bool whether the task has been successfully completed or not
  def query_task_status(self, task_id):
    resp = requests.get(self.fastapi_url + "status/" + str(task_id))
    resp_json = resp.json()
    assert resp.status_code == 200
    assert resp_json["task_id"] == task_id
    print("Got status = ", resp_json["status"])
    return resp_json["status"] == "COMPLETED"

  def submit_tasks(self):
    for i in range(self.num_tasks):
      resp = requests.post(self.fastapi_url + "execute_function",
                         json={"function_id": self.fn_id,
                               "payload": serialize.serialize(((self.param_payload,), {}))})

      assert resp.status_code == 200
      resp_json = resp.json()
      assert "task_id" in resp_json
      task_id = resp_json["task_id"]
      self.pending_task_ids.add(task_id)

  # Blocking call to wait for all tasks to be completed
  def aggregate_results(self):
    while len(self.pending_task_ids) > 0 :
      for task_id in self.pending_task_ids.copy():
        if (self.query_task_status(task_id)):
          # Task is successfully completed. Pop from set
          self.pending_task_ids.remove(task_id)
      time.sleep(self.polling_interval)

  def kill_procs(self):
    print("Killing processes: ", len(self.subprocesses))
    for proc in self.subprocesses:
      proc.terminate()

  def run(self):
    # Requirements: Redis server and main (mpcsFaaS) should be running before initiating perfomance tests
    # Execution:
    # 1. Run task_dispatcher with relevant mode, port and num_workers
    # 2. Run relevant worker instances (if not local mode)
    # 3. Register 1 function
    # 4. Start timer
    # 5. Submit num_tasks tasks
    # 6. Repeatedly query for results. Quering continues only for task_ids with pending results.
    # 7. Stop timer when all tasks completed (i.e. pending_task_ids = {})
    # 8. Kill task_dispatcher and worker instances

    # Run task_dispatcher with relevant mode, port and num_workers
    p = subprocess.Popen(["python3", "task_dispatcher.py", "-m", str(self.mode), "-p", str(self.port), "-w", str(self.num_workers)]) 
    self.subprocesses.append(p)

    # Run relevant worker instances (if not local mode)
    dispatcher_url = "tcp://localhost:" + str(self.port)
    if (self.mode != "local"):
      for i in range(self.num_workers):
        p = subprocess.Popen(["python3", self.mode + "_worker.py", str(self.num_procs), dispatcher_url])
        self.subprocesses.append(p)

    # Register 1 function
    self.fn_id = self.register_function()

    # Start timer
    start_time = time.time()

    # Submit num_tasks tasks
    self.submit_tasks()

    # Repeatedly query for results. Quering continues only for task_ids with pending results. This is a blocking call
    self.aggregate_results()

    # Stop timer when all tasks completed (i.e. pending_task_ids = {})
    end_time = time.time()

    # Kill task_dispatcher and worker instances
    self.kill_procs()

    return end_time - start_time




if __name__ == '__main__':
  ss = StrongScaling(1, 1, 1, "local", 5500, 5)
  print(ss.run())


# References:
# Using subprocess popen to run tasks in background: https://stackoverflow.com/questions/636561/how-can-i-run-an-external-command-asynchronously-from-python 