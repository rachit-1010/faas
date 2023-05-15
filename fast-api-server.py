from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import redis
import uuid

app = FastAPI()

class Server():
  def __init__(self):
    self.redis = redis.Redis(host='localhost', port=6379)
    # TODO: Check whether we need to flush DB on server init using flushdb()
    # Redis retains data acorss restarts
  
  # Assign a UUID to the function and insert into Redis db. Returns the assigned UUID
  def register_function(self, name, fn_payload):
    function_id = str(uuid.uuid4())
    self.redis.hset(function_id, 'name', name)
    self.redis.hset(function_id, 'fn_payload', fn_payload)
    return function_id

  # Execute a valid function_id with given payload and return unique task_id with error code
  def execute_function(self, function_id, param_payload):
    task_id = str(uuid.uuid4())
    if (self.redis.exists(function_id) == 0):
      # Function id isn't registered. Return ERROR code 400
      return task_id, 400
    
    # Fetch function payload from given function id
    fn_payload = self.redis.hget(function_id, 'fn_payload')
    self.redis.hset(task_id, 'fn_payload', fn_payload)
    self.redis.hset(task_id, 'param_payload', param_payload)
    self.redis.hset(task_id, 'status', "QUEUED")
    self.redis.hset(task_id, 'result', '')

    # Publish the new task id for task_dispatcher to execute
    self.redis.publish('tasks', task_id)
    return task_id, 200

  # Fetch status of given task_id along with error code
  def get_status(self, task_id):
    status = ""
    if (self.redis.exists(task_id) == 0):
      # Task id isn't registered. Return ERROR code 400
      return status, 400

    # Fetch status key for given task_id
    status = self.redis.hget(task_id, 'status')
    return status.decode("utf-8"), 200

  # Fetch result of given task_id along with error code. Result is valid only if task status is COMPLETED/FAILED
  def get_result(self, task_id):
    result = ""
    if (self.redis.exists(task_id) == 0):
      # Task id isn't registered. Return ERROR code 400
      return result, 400

    # Fetch result & status key for given task_id
    result = self.redis.hget(task_id, 'result')
    status = self.redis.hget(task_id, 'status')
    return result.decode("utf-8"), status.decode("utf-8"), 200
    
server = Server()


@app.post("/register_function")
async def register_function(request: Request):
    body = await request.json()
    name = body['name']
    payload = body['payload']
    function_id = server.register_function(name, payload)
    return JSONResponse(content={'function_id': function_id}, status_code=200)


@app.post("/execute_function")
async def execute_function(request: Request):
    body = await request.json()
    function_id = body['function_id']
    payload = body['payload']
    task_id, error_code = server.execute_function(function_id, payload)
    return JSONResponse(content={'task_id': task_id}, status_code=error_code)


@app.get('/status/{task_id}')
async def status(task_id):
    status, error_code = server.get_status(task_id)
    return JSONResponse(content={'task_id': task_id, 'status': status}, status_code=error_code)


@app.get('/result/{task_id}')
async def result(task_id):
    result, status, error_code = server.get_result(task_id)
    return JSONResponse(content={'task_id': task_id, 'result': result, 'status': status}, status_code=error_code)