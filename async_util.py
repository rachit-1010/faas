import serialize

def async_wrapper(fn_payload, param_payload, task_id):
  fn = serialize.deserialize(fn_payload)
  args, kwargs = serialize.deserialize(param_payload)
  return (task_id, fn(*args, **kwargs))