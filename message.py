

class WorkerToDispatcherMessage():
  def __init__(self, has_result, task_id, result, status):
    # has_result = True => There is a result to be returned
    # has_result = False => Just checking in if there's an available task
    self.has_result = has_result
    self.task_id = task_id
    self.result = result
    self.status = status


class DispatcherToWorkerMessage():
  def __init__(self, has_task, task_id, fn_payload, param_payload):
    # has_task = True => There is a task to be executed.
    # has_task = False => Acknowledgement for receiving the result
    self.has_task = has_task
    self.task_id = task_id
    self.fn_payload = fn_payload
    self.param_payload = param_payload


class WorkerRegistrationMessage():
  def __init__(self, num_procs):
    self.num_procs = num_procs
        