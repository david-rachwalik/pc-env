#!/usr/bin/python
"""Testing logic for multiprocessing"""

import multiprocessing
import queue  # imported for using queue.Empty exception
import random
import time
from typing import Tuple

# ------------------------ Classes ------------------------


def do_job(tasks_to_accomplish, tasks_that_are_done):
    while True:
        try:
            '''
                try to get task from the queue. get_nowait() function will 
                raise queue.Empty exception if the queue is empty. 
                queue(False) function would do the same task also.
            '''
            task = tasks_to_accomplish.get_nowait()
        except queue.Empty:

            break
        else:
            '''
                if no exception has been raised, add the task completion 
                message to task_that_are_done queue
            '''
            print(task)
            proc_name = multiprocessing.current_process().name
            tasks_that_are_done.put(task + ' is done by ' + proc_name)
            time.sleep(.5)
    return True


def main():
    number_of_task = 10
    number_of_processes = 4
    tasks_to_accomplish = multiprocessing.Queue()
    tasks_that_are_done = multiprocessing.Queue()
    processes = []

    for i in range(number_of_task):
        tasks_to_accomplish.put("Task no " + str(i))

    # creating processes
    for w in range(number_of_processes):
        p = multiprocessing.Process(target=do_job, args=(tasks_to_accomplish, tasks_that_are_done))
        processes.append(p)
        p.start()

    # completing process
    for p in processes:
        p.join()

    # print the output
    while not tasks_that_are_done.empty():
        print(tasks_that_are_done.get())

    return True


def rando(args: Tuple):
    print("rando init")
    (num, tester) = args
    proc_name = multiprocessing.current_process().name
    print(f"'{tester}' num {num} for {proc_name}")
    results = dict()
    results[num] = random.random()
    return results


def main_async():
    # Create pool and args enumerable
    pool = multiprocessing.Pool()
    args_list = []
    for i in range(5):
        args_list.append((i, "test"))
    # Run async processes, close pool, await (join), gather results
    processes = pool.map_async(rando, args_list)
    pool.close()
    pool.join()
    results = processes.get()
    # Display results
    print(f"results: {results}")


if __name__ == '__main__':
    # start_time = time.time()
    # main()
    # end_time = time.time() - start_time
    # print(f"timer: {end_time}")
    # print("")

    start_time = time.time()
    main_async()
    end_time = time.time() - start_time
    print(f"Timer: {end_time}")

# sudo python3 ~/pc-env/ansible_playbooks/roles/python/user_modules/files/test_process.py
