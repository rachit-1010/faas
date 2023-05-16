#!/bin/bash
set -x

# testTypes=(strong_scaling weak_scaling latency)
testTypes=(strong_scaling)

numTasks=(1)
numWorkers=(1)
numProcs=1
modes=(pull push)
paramPayload=5

spawn_processes(){
  num_task=${1} 
  num_worker=${2} 
  num_proc=${3} 
  mode=${4} 
  port=${5} 

  nohup python3 task_dispatcher.py "-m" ${mode} "-p" ${port} "-w" ${num_worker} &

  if [ "$mode" != "local" ]; then
    for (( i=1; i<=$num_worker; i++ ))
    do
        nohup python3 ${mode}"_worker.py" ${num_proc} "tcp://localhost:"${port} &
    done
  fi
}

kill_processes(){
  pkill -f task_dispatcher
  pkill -f pull_worker
  pkill -f push_worker
}


spawn_processes 1 2 1 local 5500

python3 strong_scaling.py 1 $paramPayload

kill_processes
