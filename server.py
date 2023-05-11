from flask import Flask, jsonify, request
import redis
# from .serialize import serialize, deserialize
import serialize
import uuid

class Server():
  def __init__(self):
    self.redis = redis.Redis(host='localhost', port=6379)
  
  # Assign a UUID to the function and insert into Redis db. Returns the assigned UUID
  def register_function(self, name, fn_payload):
    function_id = uuid.uuid4()
    self.redis.hset(function_id, 'name', name)
    self.redis.hset(function_id, 'fn_payload', fn_payload)
    return function_id

  # Execute a valid function_id with given payload and return unique task_id with error code
  def execute_function(self, function_id, param_payload):
    task_id = uuid.uuid4()
    if (self.redis.exists(function_id) == 0):
      # Function id isn't registered. Return ERROR code 400
      return task_id, 400
    
    # Fetch function payload from given function id
    fn_payload = self.redis.hget(function_id, 'fn_payload')
    self.redis.hset(task_id, 'fn_payload', fn_payload)
    self.redis.hset(task_id, 'param_payload', param_payload)
    self.redis.hset(task_id, 'status', 'QUEUED')
    self.redis.hset(task_id, 'result', '')
    return task_id, 200

  # Fetch status of given task_id along with error code
  def get_status(self, task_id):
    status = ""
    if (self.redis.exists(task_id) == 0):
      # Task id isn't registered. Return ERROR code 400
      return status, 400

    # Fetch status key for given task_id
    status = self.redis.hget(task_id, 'status')
    return status, 200

  # Fetch result of given task_id along with error code. Result is valid only if task status is COMPLETED/FAILED
  def get_result(self, task_id):
    result = ""
    if (self.redis.exists(task_id) == 0):
      # Task id isn't registered. Return ERROR code 400
      return result, 400

    # Fetch result key for given task_id
    result = self.redis.hget(task_id, 'result')
    return result, 200

server = Server()

app = Flask(__name__)

@app.route('/register_function', methods=['POST'])
def register_function():
  name = request.json['name']
  payload = request.json['payload']
  function_id = server.register_function(name, payload)
  return jsonify({'function_id' : function_id}), 200

@app.route('/execute_function', methods=['POST'])
def execute_function():
  function_id = request.json['function_id']
  payload = request.json['payload']
  task_id, error_code = server.execute_function(function_id, payload)
  return jsonify({'task_id' : task_id}), error_code

@app.route('/status/<task_id>', methods=['POST'])
def status(task_id):
  status, error_code = server.get_status(task_id)
  return jsonify({'status' : status}), error_code


@app.route('/result/<task_id>', methods=['POST'])
def result(task_id):
  result, error_code = server.get_result(task_id)
  return jsonify({'result' : result}), error_code


# References:
# UUID: https://docs.python.org/3/library/uuid.html
# Redis hashes: https://redis.io/docs/data-types/hashes/, https://koalatea.io/python-redis-hash/