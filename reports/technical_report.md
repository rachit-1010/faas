**Technical Report**

**Overview of the System**

MPCSFaaS, is a Function-as-a-Service (FaaS) platform, that allows users to run Python functions in a serverless environment. It is a distributed systems implemented in Python using the FastAPI framework for the REST API and ZMQ for communication between components.

The main components of the system are :

- **The MPCSFaaS service** : This is the client-facing component of the system. It exposes a REST API that allows users to register functions, execute functions, retrieve task status and retrieve the results of functions. It is also responsible for connecting to Redis and storing functions and tasks in the database
- **The task dispatcher** : It listens to task IDs published by the service through Redis.pubsub. Upon receiving a task ID, it obtains the function body and input arguments from Redis, and dispatches the task for execution on available workers, or run it locally (depending on the mode of execution).
- **The worker pool** : This component is responsible for executing tasks. It consists of a set of worker processes, each of which can execute a function.
- **Redis:** It is utilized to store registered functions, task metadata, and task payloads.

**MPCSFaaS Service (main.py)**

The server is implemented using the FastAPI framework for registering, executing, and retrieving the status and results of functions. The code defines 4 FastAPI endpoints to handle HTTP requests:

_/register\_function_ =\> This endpoint is used to register a function by sending a POST request with the function's name and payload in the request body as JSON.

_/execute\_function_ =\> This endpoint is used to execute a registered function by sending a POST request with the function\_id and payload in the request body as JSON.

_/status/{task\_id}_ =\> This endpoint is used to retrieve the status of a task by sending a GET request with the task\_id as a path parameter

_/result/{task\_id}_ =\> This endpoint is used to retrieve the result of a task by sending a GET request with the task\_id as a path parameter.

**Server class**

The Server class is defined to encapsulate the functionality related to the Redis database and provides methods for registering functions, executing functions, and retrieving the status and results of function execution.

Additionally, it publishes tasks to the Redis pubsub functionality in order to announce availability of new tasks to the Task Dispatcher.

**Task Dispatcher (task\_dispatcher.py)**

Task dispatcher manages the distribution and execution of tasks in our distributed computing environment. It utilizes Redis, ZeroMQ for task coordination and communication, and various Python libraries for multiprocessing and threading.

The run method starts the execution of the task dispatcher by creating two threads - one for listening tasks from Redis (redis\_subscriber\_thread) and another for either executing the tasks locally (_local)_ or delegating the tasks to workers (_push or pull)_ (execute\_task\_thread).

1. The first thread listens for tasks on published on the topic by the MPCSFaaS service and pushes it to a **thread-safe** queue.
2. The second thread pops available tasks from the thread-safe queue and either start executing locally (local) or send it to the workers for execution (push or pull)
  1. In case of local worker, the task is popped and ran immediately
  2. In case of Pull worker, the task dispatcher is assigned 'REP' role and it waits for the pull worker to request for work
  3. In case of Push worker, the task dispatcher is assigned the role of 'ROUTER'. The design involves having two threads again, where
    1. The first thread is responsible for listening to the results coming back from the workers or registers new workers along with tracking number of available processors for each worker
    2. The second thread is responsible for popping new tasks from the queue and choosing the best worker to send the task to, based on the availability of processors with the worker.

**Note** that since two different threads are being used for the Pull worker, it is important to acquire a lock before making communication, else it may result in unwanted consequences. And since locks are used, it is necessary to use non-blocking receives else there is a potential for a thread to hold a lock while waiting to receive next response, which in essence prevents the other thread from functioning.

**Pull Woker (pull\_worker.py)**

The Pull worder assumes the role of 'REQ' in the REQ-REP pattern. Here, the worker itself is responsible for maintaining the number of available processors with the worker. In case the worker has available processors, it will ask the task dispatcher for a task by sending a request. If any tasks are available with the task dispatcher, it receives a task and hands it over to the multiprocessing pool for asynchronous execution. In case the task dispatcher does not have any tasks, the worker will wait for some time and request for new tasks again. Callback functions are used to send result or error back to the task dispatcher. Again, since the functions are run asynchronously, it is necessary to the protect the communication using locks.

**Push Worker (push\_worker.py)**

The push worker implements the DEALER component of the DEALER-ROUTER communication mechanism.

The logic flow of the push worker is as follows:

1. It send a registration message to the dispatcher announcing the num procs available with that worker
2. It listens to the dispatcher continuously and executes any task that is receives using python's multiprocessing pool
3. Once a task is completed, the pool raises the relevant callback/error\_callback which is then responsible for sending out the serialized result to the task\_dispatcher along with the task\_id corresponding to the result

Few salient design aspects of push worker:

1. We use non-blocking receive in order to yield the socket connection if no data is available to be consumed. This allows socket access to both the execute\_task thread as well as the callback function to communicate asynchronously
2. We use locks to ensure mutual exclusion in access to the shared socket instance
3. No disconnect happens throughout the lifetime of the push\_worker (unlike the pull\_worker) since we are using the asynchronous DEALER-ROUTER model here.