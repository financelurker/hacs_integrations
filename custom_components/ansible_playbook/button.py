import logging
import os
from datetime import timedelta

from .ansible_playbook_runner import async_execute_playbook
from .sensor import AnsiblePlaybookSensorEntity
from .process_manager import run_task
import homeassistant.helpers.config_validation as cv
import homeassistant.helpers.dispatcher as dispatcher
import voluptuous as vol
from homeassistant.components.button import ENTITY_ID_FORMAT, PLATFORM_SCHEMA, ButtonEntity
from homeassistant.const import (
    CONF_NAME,
    CONF_HOST,
    CONF_PORT,
    CONF_USERNAME,
    CONF_PASSWORD,
    EVENT_HOMEASSISTANT_START,
)
from homeassistant import core
from homeassistant.core import HomeAssistant
from .const import DOMAIN as CONST_DOMAIN
from .const import (
    CONF_PLAYBOOKS,
    CONF_PLAYBOOK_DIRECTORY,
    CONF_PLAYBOOK_FILE,
    CONF_BUTTON_NAME,
    CONF_BUTTON_ID,
    CONF_VAULT_PASSWORD_FILE,
    CONF_EXTRA_VARS,
    ATTR_OK_COUNT,
    ATTR_FAILURE_COUNT,
    ATTR_CHANGED_COUNT,
    ATTR_SKIPPED_COUNT,
    ATTR_IGNORED_COUNT,
    ATTR_PLAYBOOK,
)

_LOGGER = logging.getLogger(__name__)

DOMAIN = CONST_DOMAIN

DEFAULT_NAME = "Ansible Playbook Button"

PLAYBOOK_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_PLAYBOOK_DIRECTORY): str,
        vol.Required(CONF_PLAYBOOK_FILE): str,
        vol.Required(CONF_BUTTON_ID): str,
        vol.Required(CONF_BUTTON_NAME): str,
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


class AnsiblePlaybookButton(ButtonEntity):
    def __init__(self, hass, name: str, button_id: str, private_data_dir: str, playbook_file: str, extra_vars: dict, vault_password_file: str, unique_id: str):
        self._name = name if name is not None else DEFAULT_NAME
        self._private_data_dir = private_data_dir
        self._playbook_file = playbook_file
        self._unique_id = unique_id
        self._extra_vars = extra_vars
        self._vault_password_file = vault_password_file
        self.entity_id = ENTITY_ID_FORMAT.format(self._unique_id)
        self.hass = hass
        self._button_id = button_id

    @property
    def name(self) -> str:
        return self._name
    
    @property
    def device_class(self) -> str:
        return "update"

    @property
    def unique_id(self):
        return self._unique_id
    
    @property
    def device(self):
        return self._button_id

    async def async_press(self, **kwargs) -> None:
        _LOGGER.warn("ansible_playbook turned on")
        await self._run_playbook()

    async def _run_playbook(self) -> None:
        # Run playbook
        _LOGGER.warn("invoking async_execute_playbook")

        try:
            run_task(
                entity_id=self._unique_id,
                private_data_dir=get_absolute_path(self.hass.config.path(), self._private_data_dir),
                playbook=self._playbook_file,
                vault_password_file=self._vault_password_file
            )
            _LOGGER.debug("Sending custom event")
            dispatcher.async_dispatcher_send(self.hass, self._button_id + "_executed", None)
        except Exception as e:
            _LOGGER.error("Error while executing the ansible playbook", e)


# Home Assistant will call this method automatically when setting up the platform.
# It creates the button entities and returns True if everything was set up correctly.
async def async_setup_platform(hass: core.HomeAssistant, config, async_add_entities, discovery_info=None):
    """Set up the Ansible playbook button platform."""

    _LOGGER.warn("Setting up ansible_playbook integration")

    # Validate the configuration for the platform
    if not config.get(CONF_PLAYBOOKS):
        _LOGGER.error("Missing required variable: playbooks")
        return False

    # Get the list of Ansible playbooks
    playbooks = config.get(CONF_PLAYBOOKS)

    # Create a list to store the button entities
    entities = []

    # Loop through the list of playbooks and create a button entity for each one
    for playbook in playbooks:
        button_name = playbook.get(CONF_BUTTON_NAME)
        button_id = playbook.get(CONF_BUTTON_ID)
        playbook_directory = playbook.get(CONF_PLAYBOOK_DIRECTORY)
        playbook_file = playbook.get(CONF_PLAYBOOK_FILE)
        extra_vars = playbook.get(CONF_EXTRA_VARS)
        vault_password_file = playbook.get(CONF_VAULT_PASSWORD_FILE)

        button_unique_id = "ansible_playbook_" + button_id
        sensor_unique_id = "ansible_playbook_" + button_id + "_button_sensor"

        # Create a button entity for the playbook
        button = AnsiblePlaybookButton(
            hass=hass,
            name=button_name,
            button_id=button_id,
            private_data_dir=playbook_directory,
            playbook_file=playbook_file,
            extra_vars=extra_vars,
            vault_password_file=vault_password_file,
            unique_id=button_unique_id
        )
        entities.append(button)

        sensor = AnsiblePlaybookSensorEntity(
            name=button_name + " Sensor",
            button_unique_id=button_unique_id,
            unique_id=sensor_unique_id,
            button_id=button_id
        )
        entities.append(sensor)


    # Add the button entities to Home Assistant
    async_add_entities(entities)

    # Return True to indicate that the platform was successfully set up
    return True


def check_location_exists(hass, path: str):
    hass_config_location = hass.config.path()
    absolute_path = get_absolute_path(hass_config_location, path)
    return os.path.exists(absolute_path)


def get_absolute_path(hass_config_location: str, path: str) -> str:
    return os.path.join(hass_config_location, DOMAIN, path)
