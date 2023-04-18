import datetime
from datetime import timedelta
import multiprocessing
import enum
from multiprocessing.connection import Connection
from typing import Dict, List
import pprint
import math
from .ansible_playbook_runner import execute_playbook


class AnsiblePlaybookResult(dict):
    def __init__(
        self,
        changed: int = 0, 
        dark: int = 0, 
        failures: int = 0,
        ignored: int = 0,
        ok: int = 0,
        processed: int = 0,
        rescued: int = 0,
        skipped: int = 0,
    ):
        self["changed"] = changed
        self["dark"] = dark
        self["failures"] = failures
        self["ignored"] = ignored
        self["ok"] = ok
        self["processed"] = processed
        self["rescued"] = rescued
        self["skipped"] = skipped
    
    @property
    def host(self):
        return self._host

    @property
    def changed(self):
        return self["changed"]
    
    @property
    def dark(self):
        return self["dark"]
    
    @property
    def failures(self):
        return self["failures"]
    
    @property
    def ignored(self):
        return self["ignored"]
    
    @property
    def ok(self):
        return self["ok"]
    
    @property
    def processed(self):
        return self["processed"]
    
    @property
    def rescued(self):
        return self["rescued"]
    
    @property
    def skipped(self):
        return self["skipped"]


class AnsiblePlaybookExecution(dict):
    def __init__(self, entity_id: str, base_dir: str, playbook_file: str, vault_password_file: str):
        super()
        self._base_dir = base_dir
        self._playbook_file = playbook_file
        self._vault_password_file = vault_password_file
        self._running = False
        self._parent_pipe: Connection = None
        self._result_data: dict = None
        self._entity_id = entity_id
        self._last_result = None
    
    def is_running(self) -> bool:
        if self._running:
            if self._parent_pipe.poll():
                data = self._parent_pipe.recv()
                self.handle_finished_process(data) # TODO
                return False
            else:
                return True
        else:
            return False
    
    def handle_finished_process(self, data: dict) -> None:
        self._parent_pipe.close()
        self._parent_pipe = None
        self._running = False
        self._last_result = transformStatsToPlaybookResult(data)
    
    def collect_last_result(self) -> AnsiblePlaybookResult | None:
        last_result = self._last_result
        self._last_result = None
        return last_result
    
    def run(self) -> None:
        child_conn: Connection = None
        self._parent_pipe, child_conn = multiprocessing.Pipe()
        p = multiprocessing.Process(target=self.worker, args=(child_conn,))
        p.start()
        print("Sub-Process started...")
        self._result_data = None
        self._running = True
    
    def worker(self, conn: Connection) -> None:
        begin_timestamp = datetime.datetime.now()
        print("------ within sub-process")
        runner = execute_playbook(private_data_dir=self._base_dir, playbook=self._playbook_file, vault_password_file=self._vault_password_file)
        end_timestamp = datetime.datetime.now()
        duration = end_timestamp - begin_timestamp
        print("Duration = " + str(math.ceil(duration.total_seconds())) + " seconds")
        conn.send(runner.stats)
        conn.close()


class AnsibleTaskState(enum.Enum):
    RUNNING = 1
    NOT_RUNNING = 2


class AnsibleProcessManager:
    """
    This process manager keeps track of base_dir/playbook_file jobs.
    There's only one AnsiblePlaybookExecution for each base_dir/playbook_file combination.

    It can run a task (sub process) for a given base_dir/playbook_file pair using "run_task", or retrieve the running state using "get_task_state".
    """
    def __init__(self):
        self._sub_processes = {}

    def run_task(self, entity_id: str, base_dir: str, playbook_file: str, vault_password_file: str) -> None:
        if self._sub_processes.get(entity_id) is None:
            task = AnsiblePlaybookExecution(entity_id=entity_id, base_dir=base_dir, playbook_file=playbook_file, vault_password_file=vault_password_file)
            self._sub_processes[entity_id] = task
            task.run()
        else:
            if self.get_task_state(base_dir=base_dir, playbook_file=playbook_file) == AnsibleTaskState.RUNNING:
                pass
            else:
                self._sub_processes[entity_id].run()
    
    def get_task_state(self, entity_id: str) -> AnsibleTaskState:
        if self._sub_processes.get(entity_id) is None:
            return AnsibleTaskState.NOT_RUNNING
        else:
            return AnsibleTaskState.RUNNING if self._sub_processes[entity_id].is_running() else AnsibleTaskState.NOT_RUNNING
    
    def collect_result(self, entity_id: str) -> AnsiblePlaybookResult | None:
        if self._sub_processes.get(entity_id) is None:
            return None
        else:
            return self._sub_processes[entity_id].collect_last_result()

def transformStatsToPlaybookResult(runner_stats: dict) -> dict:
    hosts = set()
    for high_level_key in runner_stats.keys():
        for host_name in runner_stats[high_level_key].keys():
            hosts.add(host_name)
    result = {}
    for host in hosts:
        ansible_playbook_result = AnsiblePlaybookResult(
            changed=runner_stats["changed"][host] if runner_stats["changed"].get(host) is not None else 0,
            dark=runner_stats["dark"][host] if runner_stats["dark"].get(host) is not None else 0,
            failures=runner_stats["failures"][host] if runner_stats["failures"].get(host) is not None else 0,
            ignored=runner_stats["ignored"][host] if runner_stats["ignored"].get(host) is not None else 0,
            ok=runner_stats["ok"][host] if runner_stats["ok"].get(host) is not None else 0,
            processed=runner_stats["processed"][host] if runner_stats["processed"].get(host) is not None else 0,
            rescued=runner_stats["rescued"][host] if runner_stats["rescued"].get(host) is not None else 0,
            skipped=runner_stats["skipped"][host] if runner_stats["skipped"].get(host) is not None else 0,
        )
        result[host] = (ansible_playbook_result)
    return result

def process_result(execution_result: dict):
    pprint.pprint(execution_result)


process_manager = AnsibleProcessManager()

def run_task(entity_id: str, base_dir: str, playbook_file: str, vault_password_file: str):
    process_manager.run_task(entity_id, base_dir, playbook_file, vault_password_file)

def get_task_state(entity_id: str) -> AnsibleTaskState:
    process_manager.get_task_state(entity_id)

def collect_result(entity_id: str) -> AnsiblePlaybookResult:
    process_manager.collect_result(entity_id)


if __name__ == "__main__":
    import time

    base_dir = "./custom_components/ansible_playbook/test"
    playbook_file = "main.yaml"
    vault_password_file = "vault.txt"
    entity_id = "entity-id"
    process_manager.run_task(entity_id=entity_id, base_dir=base_dir, playbook_file=playbook_file, vault_password_file=vault_password_file)
    while process_manager.get_task_state(entity_id=entity_id) == AnsibleTaskState.RUNNING:
        time.sleep(1)
    pprint.pprint(process_manager.collect_result(entity_id=entity_id))
