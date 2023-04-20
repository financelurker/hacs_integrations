import logging
from .process_manager import get_task_state, AnsibleTaskState, collect_result
from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant, callback
from homeassistant.components.sensor import ENTITY_ID_FORMAT, SensorEntity
import homeassistant.helpers.dispatcher as dispatcher
from datetime import timedelta
import asyncio


_LOGGER = logging.getLogger(__name__)


class AnsiblePlaybookSensorEntity(SensorEntity):
    SCAN_INTERVAL = timedelta(seconds=10)

    def __init__(self, name: str, button_unique_id: str, button_id: str, unique_id: str):
        self._name = name
        self._state = False
        self._button_unique_id = button_unique_id
        self._unique_id = unique_id
        self.entity_id = ENTITY_ID_FORMAT.format(self._unique_id)
        self._button_id = button_id
        self._should_poll = True

    @property
    def name(self):
        _LOGGER.debug("AnsiblePlaybookSensorEntity.name: " + self._name)
        return self._name

    @property
    def state(self):
        _LOGGER.debug("AnsiblePlaybookSensorEntity.state: " + str(self._state))
        return self._state
    
    @property
    def unique_id(self):
        _LOGGER.debug("AnsiblePlaybookSensorEntity.unique_id: " + str(self._unique_id))
        return self._unique_id
    
    @property
    def device(self):
        _LOGGER.debug("AnsiblePlaybookSensorEntity.device: " + str(self._button_id))
        return self._button_id
    
    @property
    def should_poll(self):
        _LOGGER.debug("AnsiblePlaybookSensorEntity.should_poll: " + str(self._should_poll))
        return self._should_poll

    async def async_added_to_hass(self):
        """Run when the entity is added to the registry."""
        _LOGGER.debug("AnsiblePlaybookSensorEntity.async_added_to_hass enter")
        # Register a callback for the custom event
        dispatcher.async_dispatcher_connect(self.hass, self._button_id + "_executed", self._handle_playbook_executed_event)
        _LOGGER.debug("AnsiblePlaybookSensorEntity.async_added_to_hass exit")

    @callback
    async def _handle_playbook_executed_event(self, event):
        """Handle the custom event and update the entity state."""
        _LOGGER.debug("AnsiblePlaybookSensorEntity._handle_playbook_executed_event enter")
        self._state = True
        self.async_write_ha_state()
        _LOGGER.debug("AnsiblePlaybookSensorEntity._handle_playbook_executed_event exit")
    
    async def async_update(self):
        _LOGGER.debug("AnsiblePlaybookSensorEntity.async_update enter")
        future = self.hass.async_add_executor_job(get_task_state, self._button_unique_id)
        when_done_lambda = lambda task_state: self._update_with_state(task_state.result())
        future.add_done_callback(when_done_lambda)
        _LOGGER.debug("AnsiblePlaybookSensorEntity.async_update exit")

    def _update_with_state(self, task_state: AnsibleTaskState):
        if task_state == None:
            _LOGGER.debug("AnsiblePlaybookSensorEntity._update_with_state enter - the state is None")
        else:
            _LOGGER.debug("AnsiblePlaybookSensorEntity._update_with_state enter - the state is " + task_state.name)
            if task_state == AnsibleTaskState.NOT_RUNNING and self._state == True:
                _LOGGER.debug("AnsiblePlaybookSensorEntity._update_with_state playbook NOT_RUNNING: turning off sensor")
                result = collect_result(self._button_unique_id)
                _LOGGER.debug(result)
                self._state = False
                self.async_write_ha_state()
            _LOGGER.debug("AnsiblePlaybookSensorEntity._update_with_state exit")

class AnsiblePlaybookHostExecutionResultSensorEntity(SensorEntity):
    def __init__(self):
        super()
