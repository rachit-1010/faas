import sys

class PullWorker():
  def __init__(self, num_procs, dispatcher_url):
    self.num_procs = num_procs
    self.dispatcher_url = dispatcher_url

  def run():
    pass


  
if __name__ == '__main__':
  if (len(sys.argv) != 3):
    print("usage: python3 pull_worker.py <num_worker_processors> <dispatcher url>")
    sys.exit()
  
  num_procs = int(sys.argv[1])
  dispatcher_url = sys.argv[2]

  worker = PullWorker(num_procs, dispatcher_url)
  worker.run()

