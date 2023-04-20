import pprint
import ansible_runner
import logging
from ansible_runner import Runner
import threading

_LOGGER = logging.getLogger(__name__)

runner_status = None


def finished_callback(runner: Runner):
    _LOGGER.debug(threading.current_thread().name + " - " + runner.status)
    global runner_status
    runner_status = runner.status


async def async_execute_playbook(private_data_dir: str, playbook: str, vault_password_file: str | None) -> Runner:
    return execute_playbook(
        private_data_dir=private_data_dir,
        playbook=playbook,
        vault_password_file=vault_password_file
    )


def execute_playbook(private_data_dir: str, playbook: str, vault_password_file: str | None) -> Runner:
    global runner_status
    runner_status = None

    _LOGGER.debug(threading.current_thread().name + " - Starting ansible_runner.run_async")
    (thread, runner) = ansible_runner.run_async(
        private_data_dir=private_data_dir,
        playbook=playbook,
        finished_callback=finished_callback,
        cmdline='--vault-password-file ' + vault_password_file if vault_password_file is not None else None,
        quiet=True,
    )

    thread.join()
    # print(threading.current_thread().name + " - Finished ansible_runner.run_async - Status was: " + runner_status)
    # print()
    # pprint.pprint(runner.stats)
    return runner


if __name__ == "__main__":
    execute_playbook(
        "./custom_components/ansible_playbook/test",
        "main.yaml",
        "vault.txt"
    )
