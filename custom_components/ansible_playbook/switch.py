import logging
import os
import json
from datetime import datetime
from typing import List

from ansible import context
from ansible.inventory.manager import InventoryManager
from ansible.parsing.dataloader import DataLoader
from ansible.playbook.play import Play
from ansible.plugins.callback import CallbackBase
from ansible.plugins.loader import callback_loader
from ansible.vars.manager import VariableManager
from ansible.executor.playbook_executor import PlaybookExecutor

import time
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.dispatcher import async_dispatcher_send
import voluptuous as vol
from homeassistant.components.switch import PLATFORM_SCHEMA, SwitchEntity
from homeassistant.const import (
    CONF_NAME,
    CONF_HOST,
    CONF_PORT,
    CONF_USERNAME,
    CONF_PASSWORD,
)
from homeassistant.core import HomeAssistant
from .const import DOMAIN as CONST_DOMAIN
from .const import (
    CONF_PLAYBOOKS,
    CONF_PLAYBOOK_PATH,
    CONF_INVENTORY_PATH,
    CONF_SWITCH_NAME,
    CONF_VAULT_PASSWORD_FILE,
    CONF_EXTRA_VARS,
    ATTR_HOSTS_COUNT,
    ATTR_STEPS_COUNT,
    ATTR_PLAYBOOK,
)

_LOGGER = logging.getLogger(__name__)

DOMAIN = CONST_DOMAIN

DEFAULT_NAME = "Ansible Playbook Switch"

PLAYBOOK_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_PLAYBOOK_PATH): str,
        vol.Optional(CONF_SWITCH_NAME): str,
        vol.Optional(CONF_INVENTORY_PATH): str,
        vol.Optional(CONF_EXTRA_VARS): dict,
        vol.Optional(CONF_VAULT_PASSWORD_FILE): str,
    }
)

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_PLAYBOOKS): vol.All(
            [PLAYBOOK_SCHEMA], vol.Length(min=1)
        ),
    }
)


class AnsiblePlaybookSwitch(SwitchEntity):
    def __init__(self, name: str, playbook_path: str, inventory_path: str, extra_vars: dict, vault_password_file: str):
        self._name = name if name is not None else DEFAULT_NAME
        self._playbook_path = playbook_path
        self._inventory_path = inventory_path
        self._extra_vars = extra_vars
        self._vault_password_file = vault_password_file
        self._state = False
        self._host_count = 0
        self._step_count = 0
        self._callback = AnsiblePlaybookCallback(self)

    @property
    def name(self) -> str:
        return self._name
    
    @property
    def is_on(self) -> bool:
        """Return true if the switch is currently turned on."""
        _is_on = self._callback._state in ["running", "starting", "waiting"]
        self._state = _is_on
        return _is_on

    def turn_on(self, **kwargs) -> None:
        self._run_playbook()
        self._state = True
        self.schedule_update_ha_state()

    def turn_off(self, **kwargs) -> None:
        # self._state = False
        self.schedule_update_ha_state()
    
    @property
    def hosts_count(self):
        return self._host_count
    
    @property
    def steps_count(self):
        return self._step_count
    
    @property
    def playbook_path(self) -> str:
        return self._playbook_path
    
    @property
    def inventory_path(self) -> str | None:
        return self._inventory_path
    
    @property
    def vault_password_file(self) -> str | None:
        return self._vault_password_file

    @property
    def device_state_attributes(self) -> dict:
        return {
            ATTR_HOSTS_COUNT: self._host_count,
            ATTR_STEPS_COUNT: self._step_count,
            ATTR_PLAYBOOK: self._playbook_path,
        }

    def _run_playbook(self) -> None:
        # Load inventory and variables
        loader = DataLoader()
        inventory = InventoryManager(
            loader=loader, sources=self._inventory_path)
        variable_manager = VariableManager(loader=loader, inventory=inventory)

        # Set up callback
        results_callback = PlaybookResultCallback()
        results_callback.playbook_path = self._playbook_path

        options = {
            'extra_vars': self._extra_vars,
            'vault_password_file': self._vault_password_file
        }

        # Set up playbook
        playbook = PlaybookExecutor(
            playbooks=[self._playbook_path],
            inventory=inventory,
            variable_manager=variable_manager,
            loader=loader,
            passwords={},
            options=options,
            callbacks=[results_callback],
            stdout_callback=self._callback,
        )

        # Run playbook
        self._callback._state = "starting"
        playbook.run()

        # Update state
        self._host_count = results_callback.host_count
        self._step_count = results_callback.step_count
        self.schedule_update_ha_state()


class PlaybookResultCallback(CallbackBase):
    def __init__(self):
        super().__init__()
        self._host_count = 0
        self._step_count = 0
        self._start_time = datetime.now()

    @property
    def host_count(self) -> int:
        return self._host_count

    @property
    def step_count(self) -> int:
        return self._step_count

    def v2_playbook_on_start(self, playbook: Play) -> None:
        self._host_count = len(playbook.get_variable_manager().get_hosts())

    def v2_runner_on_ok(self, result):
        self._step_count += 1

    def v2_runner_on_failed(self, result, ignore_errors=False):
        self._step_count += 1

    def v2_runner_on_skipped(self, result):
        self._step_count += 1

    def v2_playbook_on_stats(self, stats):
        self._step_count = stats.processed

        end_time = datetime.now()
        elapsed_time = end_time - self._start_time

        results = {
            ATTR_HOSTS_COUNT: self._host_count,
            ATTR_STEPS_COUNT: self._step_count,
            "elapsed_time": str(elapsed_time),
        }

        _LOGGER.info(json.dumps(results))


class AnsiblePlaybookCallback(CallbackBase):
    """A callback class that updates the state of the switch."""

    def __init__(self, hass, switch):
        super(AnsiblePlaybookCallback, self).__init__()
        self.hass = hass
        self.switch = switch
        self._state = "idle"

    def _update_switch_state(self, new_state):
        self._state = new_state
        async_dispatcher_send(self.hass, self.switch.entity_id)

    def v2_playbook_on_start(self, playbook):
        """Called when the playbook starts."""
        self._update_switch_state("starting")

    def v2_playbook_on_task_start(self, task, is_conditional):
        """Called when a task starts."""
        self._update_switch_state("running")

    def v2_playbook_on_stats(self, stats):
        """Called when the playbook completes."""
        self._update_switch_state("finished")

    def v2_playbook_on_no_hosts_matched(self):
        """Called when no hosts matched the pattern."""
        self._update_switch_state("failed")

    def v2_playbook_on_play_start(self, play):
        """Called when a play starts."""
        self._update_switch_state("running")

    def v2_playbook_on_handler_task_start(self, task):
        """Called when a handler task starts."""
        self._update_switch_state("running")

    def v2_playbook_on_include(self, included_file):
        """Called when an include file is encountered."""
        self._update_switch_state("running")

    def v2_playbook_on_import_for_host(self, result, included_file):
        """Called when an import file is encountered."""
        self._update_switch_state("running")

    def v2_playbook_on_not_import_for_host(self, result, missing_file):
        """Called when an import file is missing."""
        self._update_switch_state("failed")
