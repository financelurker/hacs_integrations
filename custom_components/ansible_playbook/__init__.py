"""The ansible_runner component."""
import os
from .switch import AnsiblePlaybookSwitch
import logging
from .const import DOMAIN as CONST_DOMAIN
from .const import (
    CONF_PLAYBOOKS,
    CONF_PLAYBOOK_PATH,
    CONF_INVENTORY_PATH,
    CONF_SWITCH_NAME,
    CONF_VAULT_PASSWORD_FILE,
    CONF_EXTRA_VARS,
)

_LOGGER = logging.getLogger(__name__)

_LOGGER.info("ansible_playbook __init__ loaded.")

DOMAIN = CONST_DOMAIN
