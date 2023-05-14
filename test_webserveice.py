import requests
from serialize import serialize, deserialize
# import serialize
import logging
import time
import random
from multiprocessing import Pool
import dill
import multiprocessing

base_url = "http://127.0.0.1:8000/"

valid_statuses = ["QUEUED", "RUNNING", "COMPLETED", "FAILED"]


def test_fn_registration():
    resp = requests.post(base_url + "register_function",
                         json={"name": "hello",
                               "payload": "payload"})

    assert resp.status_code == 200
    assert "function_id" in resp.json()


def double(x):
    print("OKOK")
    return x/0

def callback(result):
    print("Callback")

def error_callback(result):
    print("Error Callback")

def test_execute_fn():
    resp = requests.post(base_url + "register_function",
                         json={"name": "hello",
                               "payload": serialize(double)})
    fn_info = resp.json()
    assert "function_id" in fn_info

    resp = requests.post(base_url + "execute_function",
                         json={"function_id": fn_info['function_id'],
                               "payload": serialize(((2,), {}))})

    # print(resp)
    # dill.Pickler.dumps, dill.Pickler.loads = dill.dumps, dill.loads
    # multiprocessing.reduction.ForkingPickler = dill.Pickler
    # multiprocessing.reduction.dump = dill.dump
    # multiprocessing.queues._ForkingPickler = dill.Pickler


    assert resp.status_code == 200
    assert "task_id" in resp.json()

    task_id = resp.json()["task_id"]

    resp = requests.get(f"{base_url}status/{task_id}")
    print(resp.json())
    assert resp.status_code == 200
    assert resp.json()["task_id"] == task_id
    assert resp.json()["status"] in valid_statuses


def test_roundtrip():
    resp = requests.post(base_url + "register_function",
                         json={"name": "double",
                               "payload": serialize(double)})
    fn_info = resp.json()

    number = random.randint(0, 10000)
    resp = requests.post(base_url + "execute_function",
                         json={"function_id": fn_info['function_id'],
                               "payload": serialize(((number,), {}))})

    assert resp.status_code == 200
    assert "task_id" in resp.json()

    task_id = resp.json()["task_id"]

    for i in range(20):

        resp = requests.get(f"{base_url}result/{task_id}")

        assert resp.status_code == 200
        assert resp.json()["task_id"] == task_id
        if resp.json()['status'] in ["COMPLETED", "FAILED"]:
            logging.warning(f"Task is now in {resp.json()['status']}")
            s_result = resp.json()
            logging.warning(s_result)
            result = deserialize(s_result['result'])
            assert result == number*2
            break
        time.sleep(0.01)


if __name__ == '__main__':
  test_fn_registration()
  test_execute_fn()
  test_roundtrip()