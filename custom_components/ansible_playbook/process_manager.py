import logging
import datetime
from datetime import timedelta
import multiprocessing
import enum
from multiprocessing.connection import Connection
from typing import Dict, List
import pprint
import math
from .ansible_playbook_runner import execute_playbook


_LOGGER = logging.getLogger(__name__)


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
        _LOGGER.debug("AnsiblePlaybookExecution.__init__ enter")
        self._base_dir = base_dir
        self._playbook_file = playbook_file
        self._vault_password_file = vault_password_file
        self._running = False
        self._parent_pipe: Connection = None
        self._result_data: dict = None
        self._entity_id = entity_id
        self._last_result = None
        _LOGGER.debug("AnsiblePlaybookExecution.__init__ exit")
    
    def is_running(self) -> bool:
        _LOGGER.debug("AnsiblePlaybookExecution.is_running enter")
        if self._running:
            _LOGGER.debug("AnsiblePlaybookExecution.is_running checking _parent_pipe.poll()")
            if self._parent_pipe.poll():
                _LOGGER.debug("AnsiblePlaybookExecution.is_running checking _parent_pipe.recv()")
                data = self._parent_pipe.recv()
                self.handle_finished_process(data) # TODO
                _LOGGER.debug("AnsiblePlaybookExecution.is_running exit")
                return False
            else:
                _LOGGER.debug("AnsiblePlaybookExecution.is_running exit")
                return True
        else:
            _LOGGER.debug("AnsiblePlaybookExecution.is_running exit")
            return False
    
    def handle_finished_process(self, data: dict) -> None:
        _LOGGER.debug("AnsiblePlaybookExecution.handle_finished_process enter")
        self._parent_pipe.close()
        self._parent_pipe = None
        self._running = False
        self._last_result = transformStatsToPlaybookResult(data)
        _LOGGER.debug("AnsiblePlaybookExecution.handle_finished_process exit")
    
    def collect_last_result(self) -> AnsiblePlaybookResult | None:
        _LOGGER.debug("AnsiblePlaybookExecution.collect_last_result enter")
        last_result = self._last_result
        self._last_result = None
        _LOGGER.debug("AnsiblePlaybookExecution.collect_last_result exit")
        return last_result
    
    def run(self) -> None:
        _LOGGER.debug("AnsiblePlaybookExecution.run enter")
        child_conn: Connection = None
        self._parent_pipe, child_conn = multiprocessing.Pipe()
        p = multiprocessing.Process(target=self.worker, args=(child_conn,))
        p.start()
        _LOGGER.debug("AnsiblePlaybookExecution.run sub-process started")
        self._result_data = None
        self._running = True
        _LOGGER.debug("AnsiblePlaybookExecution.run exit")
    
    def worker(self, conn: Connection) -> None:
        _LOGGER.debug("AnsiblePlaybookExecution.worker enter")
        begin_timestamp = datetime.datetime.now()
        runner = execute_playbook(private_data_dir=self._base_dir, playbook=self._playbook_file, vault_password_file=self._vault_password_file)
        end_timestamp = datetime.datetime.now()
        duration = end_timestamp - begin_timestamp
        _LOGGER.debug("AnsiblePlaybookExecution.worker " + "Duration = " + str(math.ceil(duration.total_seconds())) + " seconds")
        conn.send(runner.stats)
        conn.close()
        _LOGGER.debug("AnsiblePlaybookExecution.worker exit")


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
        _LOGGER.debug("AnsibleProcessManager.__init__ enter")
        self._sub_processes = {}
        _LOGGER.debug("AnsibleProcessManager.__init__ exit")

    def run_task(self, entity_id: str, base_dir: str, playbook_file: str, vault_password_file: str) -> None:
        _LOGGER.debug("AnsibleProcessManager.run_task enter")
        if self._sub_processes.get(entity_id) is None:
            task = AnsiblePlaybookExecution(entity_id=entity_id, base_dir=base_dir, playbook_file=playbook_file, vault_password_file=vault_password_file)
            self._sub_processes[entity_id] = task
            task.run()
        else:
            if self.get_task_state(entity_id=entity_id) == AnsibleTaskState.RUNNING:
                pass
            else:
                self._sub_processes[entity_id].run()
        _LOGGER.debug("AnsibleProcessManager.run_task exit")
    
    def get_task_state(self, entity_id: str) -> AnsibleTaskState:
        _LOGGER.debug("AnsibleProcessManager.get_task_state enter")
        if self._sub_processes.get(entity_id) is None:
            _LOGGER.debug("AnsibleProcessManager.get_task_state exit")
            return AnsibleTaskState.NOT_RUNNING
        else:
            result = AnsibleTaskState.RUNNING if self._sub_processes[entity_id].is_running() else AnsibleTaskState.NOT_RUNNING
            _LOGGER.debug("AnsibleProcessManager.get_task_state exit")
            return result
    
    def collect_result(self, entity_id: str) -> AnsiblePlaybookResult | None:
        _LOGGER.debug("AnsibleProcessManager.collect_result enter")
        if self._sub_processes.get(entity_id) is None:
            _LOGGER.debug("AnsibleProcessManager.collect_result exit")
            return None
        else:
            last_result = self._sub_processes[entity_id].collect_last_result()
            _LOGGER.debug("AnsibleProcessManager.collect_result exit")
            return last_result

def transformStatsToPlaybookResult(runner_stats: dict) -> dict:
    _LOGGER.debug("process_manager.transformStatsToPlaybookResult enter")
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
    _LOGGER.debug("process_manager.transformStatsToPlaybookResult exit")
    return result


process_manager = AnsibleProcessManager()

def run_task(entity_id: str, base_dir: str, playbook_file: str, vault_password_file: str) -> None:
    _LOGGER.debug("process_manager.run_task enter")
    process_manager.run_task(entity_id, base_dir, playbook_file, vault_password_file)
    _LOGGER.debug("process_manager.run_task exit")

def get_task_state(entity_id: str) -> AnsibleTaskState:
    _LOGGER.debug("process_manager.get_task_state enter")
    task_state = process_manager.get_task_state(entity_id)
    _LOGGER.debug("process_manager.get_task_state return")
    return task_state

def collect_result(entity_id: str) -> AnsiblePlaybookResult:
    _LOGGER.debug("process_manager.collect_result enter")
    result = process_manager.collect_result(entity_id)
    _LOGGER.debug("process_manager.collect_result exit")
    return result


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
