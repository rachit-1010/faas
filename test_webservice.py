import requests
from serialize import serialize, deserialize
# import serialize
import logging
import time
import random
from multiprocessing import Pool
import dill
import multiprocessing
import time
import uuid

base_url = "http://127.0.0.1:8000/"

valid_statuses = ["QUEUED", "RUNNING", "COMPLETED", "FAILED"]


def test_fn_registration():
    resp = requests.post(base_url + "register_function",
                         json={"name": "hello",
                               "payload": "payload"})

    assert resp.status_code == 200
    assert "function_id" in resp.json()


def double(x):
    return x * 2

def sum1to100():
    sum = 0
    for i in range(1,101):
        sum += i
    print("1to100 complete")
    return sum

def inverse(x):
    return 1/x

def test_execute_fn():
    resp = requests.post(base_url + "register_function",
                         json={"name": "hello",
                               "payload": serialize(double)})
    fn_info = resp.json()
    assert "function_id" in fn_info

    resp = requests.post(base_url + "execute_function",
                         json={"function_id": fn_info['function_id'],
                               "payload": serialize(((2,), {}))})
    
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
    got_result = False
    for i in range(20):

        resp = requests.get(f"{base_url}result/{task_id}")

        assert resp.status_code == 200
        assert resp.json()["task_id"] == task_id
        if resp.json()['status'] in ["COMPLETED", "FAILED"]:
            got_result = True
            logging.warning(f"Task is now in {resp.json()['status']}")
            s_result = resp.json()
            logging.warning(s_result)
            result = deserialize(s_result['result'])
            assert result == number*2
            break
        time.sleep(0.1)

    assert got_result == True


def test_http_status_reg_fn_200():
    resp = requests.post(base_url + "register_function",
                         json={"name": "sum1to100",
                               "payload": serialize(sum1to100)})
    assert resp.status_code == 200

def test_http_status_execute_fn_200():
    resp = requests.post(base_url + "register_function",
                         json={"name": "sum1to100",
                               "payload": serialize(sum1to100)})
    fn_info = resp.json()
    assert "function_id" in fn_info

    resp = requests.post(base_url + "execute_function",
                         json={"function_id": fn_info['function_id'],
                               "payload": serialize(((), {}))})
    assert resp.status_code == 200

def test_http_status_execute_fn_400():
    resp = requests.post(base_url + "execute_function",
                         json={"function_id": str(uuid.uuid4()),
                               "payload": serialize(((), {}))})
    assert resp.status_code == 400

def test_http_status_status_fn_200():
    resp = requests.post(base_url + "register_function",
                         json={"name": "sum1to100",
                               "payload": serialize(sum1to100)})
    fn_info = resp.json()
    assert "function_id" in fn_info

    resp = requests.post(base_url + "execute_function",
                         json={"function_id": fn_info['function_id'],
                               "payload": serialize(((), {}))})
    task_id = resp.json()["task_id"]

    resp = requests.get (base_url + f"status/{task_id}")
    assert resp.status_code == 200

def test_http_status_status_fn_400():
    resp = requests.get (base_url + f"status/{str(uuid.uuid4())}")
    assert resp.status_code == 400

def test_http_status_result_fn_200():
    resp = requests.post(base_url + "register_function",
                         json={"name": "sum1to100",
                               "payload": serialize(sum1to100)})
    fn_info = resp.json()
    assert "function_id" in fn_info

    resp = requests.post(base_url + "execute_function",
                         json={"function_id": fn_info['function_id'],
                               "payload": serialize(((), {}))})
    task_id = resp.json()["task_id"]

    # check the status of the task 20 times
    for i in range(20):
        resp = requests.get (base_url + f"result/{task_id}")
        if resp.status_code == 200:
            break
        time.sleep(0.1)
    assert resp.status_code == 200

def test_http_status_result_fn_400():
    resp = requests.get (base_url + f"result/{str(uuid.uuid4())}")
    assert resp.status_code == 400

# Send a task and check whether the status is set to COMPLETED when run
def test_task_status_completed():
    resp = requests.post(base_url + "register_function",
                         json={"name": "inverse",
                               "payload": serialize(inverse)})
    fn_info = resp.json()
    assert "function_id" in fn_info

    resp = requests.post(base_url + "execute_function",
                         json={"function_id": fn_info['function_id'],
                               "payload": serialize(((0.1,), {}))})
    
    assert resp.status_code == 200
    assert "task_id" in resp.json()

    task_id = resp.json()["task_id"]
    got_result = False
    for i in range(20):
        resp = requests.get(f"{base_url}result/{task_id}")
        assert resp.status_code == 200
        assert resp.json()["task_id"] == task_id
        if resp.json()['status'] in ["COMPLETED", "FAILED"]:
            got_result = True
            assert resp.json()['status'] == "COMPLETED"
            break
        time.sleep(0.1)
    print(resp.json()['status'])
    assert got_result == True

# Send a failing task and check whether the status is set to FAILED when run
def test_task_status_failed():
    resp = requests.post(base_url + "register_function",
                         json={"name": "inverse",
                               "payload": serialize(inverse)})
    fn_info = resp.json()
    assert "function_id" in fn_info

    resp = requests.post(base_url + "execute_function",
                         json={"function_id": fn_info['function_id'],
                               "payload": serialize(((0,), {}))})
    
    assert resp.status_code == 200
    assert "task_id" in resp.json()

    task_id = resp.json()["task_id"]

    got_result = False
    for i in range(20):
        resp = requests.get(f"{base_url}result/{task_id}")
        assert resp.status_code == 200
        assert resp.json()["task_id"] == task_id
        if resp.json()['status'] in ["COMPLETED", "FAILED"]:
            got_result = True
            assert resp.json()['status'] == "FAILED"
            break
        time.sleep(0.1)
    print(resp.json()['status'])
    assert got_result == True

def test_result_correctness():
    resp = requests.post(base_url + "register_function",
                         json={"name": "inverse",
                               "payload": serialize(inverse)})
    fn_info = resp.json()

    resp = requests.post(base_url + "execute_function",
                         json={"function_id": fn_info['function_id'],
                               "payload": serialize(((0.5,), {}))})

    assert resp.status_code == 200
    assert "task_id" in resp.json()

    task_id = resp.json()["task_id"]
    got_result = False
    for i in range(20):

        resp = requests.get(f"{base_url}result/{task_id}")

        assert resp.status_code == 200
        assert resp.json()["task_id"] == task_id
        if resp.json()['status'] in ["COMPLETED", "FAILED"]:
            got_result = True
            logging.warning(f"Task is now in {resp.json()['status']}")
            s_result = resp.json()
            logging.warning(s_result)
            result = deserialize(s_result['result'])
            print(result)
            assert result == 2
            break
        time.sleep(0.1)

    assert got_result == True
