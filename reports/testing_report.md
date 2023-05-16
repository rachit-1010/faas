**Testing Report**

The provided testing script consists of multiple tests that aim to validate the functionality and behavior of our MPCSFaaS service in registering, executing, and retrieving results of functions. Here is a general overview of the types of tests conducted:

**PyTests**

The pytests are available in tests/test_webservice.py
Please use the following command for running the tests from the parent repo directory:

> pytest tests

**1. Function Registration Tests:**

- These tests focus on registering functions within the system.

- They verify that function registration is successful by checking the response status code and the presence of a "function\_id" in the response JSON.

**2. Function Execution Tests:**

- These tests involve executing registered functions with parameter payloads.

- They ensure that function execution is successful by checking the response status code and the presence of a "task\_id" in the response JSON.

**3. Status Retrieval Tests:**

- These tests aim to retrieve the status of tasks (representing function executions) within the system.

- They verify that the status retrieval process is functioning correctly by checking the response status code and validating the retrieved status against a set of valid statuses. Though it is difficult to check the "QUEUED" and "RUNNING" statuses automatically using a script since it is not possible to know when exactly would the task be picked up by the worker and when exactly would they be completed.

**4. Result Retrieval Tests:**

- These tests focus on retrieving the results of completed tasks.

- They ensure that the result retrieval process is functioning correctly by checking the response status code and validating the correctness of the retrieved results against expected values.

**5. HTTP Status Code Tests:**

- These tests specifically verify the HTTP status codes returned by different API endpoints.

- They check that the status codes are correct for different scenarios, such as successful requests, invalid requests, and retrieval of non-existent resources.

By covering these different aspects, the testing script aims to provide comprehensive testing coverage for the system, ensuring its functionality, reliability, and accuracy in handling function registration, execution, and result retrieval operations.

**Additional Tests**

Several other additional tests were conducted to test the robustness, fault tolerance, and efficient resource utilization our MPCSFaaS Service.

**1. Testing Shutting Down Workers:**

- This test focuses on the behavior of our system when one or more workers are intentionally shut down or becomes unavailable.

- We verified that our system can handle worker failures and ensures that worker failures does not lead to system failures. Although, considering the scope of this assignment, the system does not have the ability to reassign tasks already working tasks to other available workers.

**2. Testing Redis Database:**

- We tested the robustness of Redis database by intentionally disconnecting or stopping the Redis server to observe the behavior of the system, such as the ability to retrieve tasks, and handle Redis-related errors.

- Since Redis is an in-memory database, stopping and restarting the Redis server does not mean the data will be lost unless the main memory is somehow flushed.

- Our tests verify that none of the functions\_ids or task\_ids are lost when the Redis server is shut-down

**3. Testing Server Shutdown:**

- We tested this by intentionally shutting down one of the servers.

- We can verify that the system gracefully handles server failures, such as by gracefully shutting down workers and persisting any necessary state or data.

**4. Load Balancing by Task Dispatcher:**

- Load balancing is crucial in a distributed system to distribute tasks efficiently among workers and ensure optimal resource utilization.

- We tested this by simulating different workloads and evaluating our system's effectiveness in handling varying levels of task demand

- Our test verifies that tasks are evenly distributed among workers, preventing overloading of a specific worker and achieving better overall system performance.

These tests help identify potential issues, validate system behavior under different failure scenarios, and ensure that the system can effectively handle and distribute tasks in a distributed environment.