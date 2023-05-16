import serialize

def async_wrapper(fn_payload, param_payload):
  fn = serialize.deserialize(fn_payload)
  args, kwargs = serialize.deserialize(param_payload)
  return fn(*args, **kwargs)