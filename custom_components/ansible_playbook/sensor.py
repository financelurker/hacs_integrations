import logging
from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant, callback
from homeassistant.components.sensor import ENTITY_ID_FORMAT, SensorEntity
import homeassistant.helpers.dispatcher as dispatcher
from process_manager import get_task_state, AnsibleTaskState, collect_result
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
        # Register a callback for the custom event
        dispatcher.async_dispatcher_connect(
            self.hass, self._button_id + "_executed", self._handle_playbook_executed_event
        )

    @callback
    def _handle_playbook_executed_event(self, event):
        """Handle the custom event and update the entity state."""
        _LOGGER.debug("Received custom event")
        self._should_poll = True
        self.async_schedule_update_ha_state()

    async def async_update(self):
        task_state = get_task_state(self._button_unique_id)
        if task_state == AnsibleTaskState.RUNNING:
            if self._state == False:
                self._state = True
                self._should_poll = True
        elif task_state == AnsibleTaskState.NOT_RUNNING:
            if self._state == True:
                collect_result(self._button_unique_id)
                self._state = False
                self._should_poll = False
        await self.async_write_ha_state()        


class AnsiblePlaybookHostExecutionResultSensorEntity(SensorEntity):
    def __init__(self):
        super()
