"""The ansible_runner component."""
import os
from .switch import AnsiblePlaybookSwitch
import logging
from homeassistant import core
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

# Home Assistant will call this method automatically when setting up the platform.
# It creates the switch entities and returns True if everything was set up correctly.
def setup_platform(hass: core.HomeAssistant, config, add_entities, discovery_info=None):
    """Set up the Ansible playbook switch platform."""

    _LOGGER.info("Setting up ansible_playbook integration")

    # Validate the configuration for the platform
    if not config.get(CONF_PLAYBOOKS):
        _LOGGER.error("Missing required variable: playbooks")
        return False

    # Get the list of Ansible playbooks
    playbooks = config.get(CONF_PLAYBOOKS)

    # Create a list to store the switch entities
    switches = []

    # Loop through the list of playbooks and create a switch entity for each one
    for playbook in playbooks:
        # Get the path to the Ansible playbook
        switch_name = playbook.get(CONF_SWITCH_NAME)
        playbook_path = playbook.get(CONF_PLAYBOOK_PATH)
        inventory_path = playbook.get(CONF_INVENTORY_PATH)
        extra_vars = playbook.get(CONF_EXTRA_VARS)
        vault_password_file = playbook.get(CONF_VAULT_PASSWORD_FILE)

        #if not check_location_exists(hass, playbook_path) or not check_location_exists(hass, inventory_path):
        #    return False
        
        #if vault_password_file is not None and not check_location_exists(hass, vault_password_file):
        #    return False

        # Create a switch entity for the playbook
        switch = AnsiblePlaybookSwitch(
            name=switch_name,
            playbook_path=playbook_path,
            inventory_path=inventory_path,
            extra_vars=extra_vars,
            vault_password_file=vault_password_file
        )

        # Add the switch entity to the list of switches
        switches.append(switch)

    # Add the switch entities to Home Assistant
    add_entities(switches)

    # Return True to indicate that the platform was successfully set up
    return True


def check_location_exists(hass, path: str):
    hass_config_location = hass.config.path()
    absolute_path = os.path.join(hass_config_location, DOMAIN, path)
    return os.path.exists(absolute_path)
