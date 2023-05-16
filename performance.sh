#!/bin/bash
set -x

spawn_processes(){ 
  num_worker=${1} 
  num_proc=${2} 
  mode=${3} 
  port=${4} 

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

# testTypes=(strong_scaling weak_scaling latency)
testTypes=(strong_scaling)

numTasks=(1 2 3 4 5 6 7 8)
numWorkers=(1 2 3 4 5 6 7 8)
numProcs=1
modes=(pull push)
paramPayload=2

rm result_local_strong.csv
echo "NumWorkers,Time" >> result_local_strong.csv
for i in {1..8};
  do
    spawn_processes ${i} ${numProcs} local 5500
    time="$(python3 scaling.py $(( i )) $paramPayload 2>&1)"
    echo ${i},${time} >> result_local_strong.csv
    kill_processes
  done


