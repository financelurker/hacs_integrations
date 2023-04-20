import logging
from .process_manager import get_task_state, AnsibleTaskState, collect_result
from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant, callback
from homeassistant.components.sensor import ENTITY_ID_FORMAT, SensorEntity
import homeassistant.helpers.dispatcher as dispatcher
from datetime import timedelta


_LOGGER = logging.getLogger(__name__)


class AnsiblePlaybookSensorEntity(SensorEntity):
    SCAN_INTERVAL = timedelta(seconds=5)

    def __init__(self, name: str, button_unique_id: str, button_id: str, unique_id: str):
        self._name = name
        self._state = False
        self._button_unique_id = button_unique_id
        self._unique_id = unique_id
        self.entity_id = ENTITY_ID_FORMAT.format(self._unique_id)
        self._button_id = button_id
        self._should_poll = False

    @property
    def name(self):
        return self._name

    @property
    def state(self):
        return self._state
    
    @property
    def unique_id(self):
        return self._unique_id
    
    @property
    def device(self):
        return self._button_id
    
    @property
    def should_poll(self):
        return self._should_poll

    async def async_added_to_hass(self):
        """Run when the entity is added to the registry."""
        _LOGGER.debug("AnsiblePlaybookSensorEntity.async_added_to_hass enter")
        # Register a callback for the custom event
        dispatcher.async_dispatcher_connect(self.hass, self._button_id + "_executed", self._handle_playbook_executed_event)
        _LOGGER.debug("AnsiblePlaybookSensorEntity.async_added_to_hass exit")

    @callback
    def _handle_playbook_executed_event(self, event):
        """Handle the custom event and update the entity state."""
        _LOGGER.debug("AnsiblePlaybookSensorEntity._handle_playbook_executed_event enter")
        self.hass.async_add_executor_job(self._run_playbook)
        _LOGGER.debug("AnsiblePlaybookSensorEntity._handle_playbook_executed_event exit")
    
    async def init_playbook_execution_listening(self):
        _LOGGER.debug("AnsiblePlaybookSensorEntity.init_playbook_execution_listening enter")
        self._should_poll = True
        self._state = True
        await self.async_write_ha_state()
        _LOGGER.debug("AnsiblePlaybookSensorEntity.init_playbook_execution_listening exit")

    async def async_update(self):
        _LOGGER.debug("AnsiblePlaybookSensorEntity.async_update enter")
        task_state = get_task_state(self._button_unique_id)
        if task_state == AnsibleTaskState.NOT_RUNNING:
            _LOGGER.debug("AnsiblePlaybookSensorEntity.async_update playbook NOT_RUNNING: turning off sensor")
            if self._state == True:
                result = collect_result(self._button_unique_id)
                _LOGGER.debug(result)
                self._state = False
                self._should_poll = False
                await self.async_write_ha_state()
        _LOGGER.debug("AnsiblePlaybookSensorEntity.async_update exit")


class AnsiblePlaybookHostExecutionResultSensorEntity(SensorEntity):
    def __init__(self):
        super()
