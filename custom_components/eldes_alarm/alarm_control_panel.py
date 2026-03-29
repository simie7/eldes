"""Support for Eldes control panels."""
import logging

from homeassistant.components.alarm_control_panel import (
    AlarmControlPanelEntity,
    AlarmControlPanelEntityFeature,
    AlarmControlPanelState,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.event import async_call_later

from .const import (
    DATA_CLIENT,
    DATA_COORDINATOR,
    DOMAIN,
    ALARM_MODES,
    EVENT_ARM_FAILED,
    ARM_CHECK_DELAY_SECONDS,
)
from . import EldesDeviceEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities):
    """Set up the Eldes alarm control panel platform."""
    client = hass.data[DOMAIN][entry.entry_id][DATA_CLIENT]
    coordinator = hass.data[DOMAIN][entry.entry_id][DATA_COORDINATOR]
    entities = []

    for device_index, device in enumerate(coordinator.data):
        for partition_index in range(len(device["partitions"])):
            entity = EldesAlarmPanel(client, coordinator, device_index, partition_index)
            entity._attr_alarm_state = entity.partition["state"]
            entities.append(entity)

    async_add_entities(entities)


class EldesAlarmPanel(EldesDeviceEntity, AlarmControlPanelEntity):
    """Class for the Eldes alarm control panel."""

    _attr_supported_features = (
            AlarmControlPanelEntityFeature.ARM_AWAY
            | AlarmControlPanelEntityFeature.ARM_HOME
    )
    _attr_code_arm_required = False

    def __init__(self, client, coordinator, device_index, partition_index):
        super().__init__(client, coordinator, device_index, partition_index)
        self._previous_state = None
        self._pending_arm_mode = None
        self._arm_check_unsub = None

    @property
    def partition(self):
        return self.data["partitions"][self.entity_index]

    @property
    def unique_id(self):
        return f"{self.imei}_zone_{self.partition['internalId']}"

    @property
    def name(self):
        return self.partition["name"]

    @property
    def extra_state_attributes(self):
        return {
            "armed": self.partition["armed"],
            "armStay": self.partition["armStay"],
            "state": self.partition["state"],
            "hasUnacceptedPartitionAlarms": self.partition["hasUnacceptedPartitionAlarms"],
        }

    @property
    def alarm_state(self) -> AlarmControlPanelState:
        return self.partition["state"]

    async def _async_set_alarm(
        self,
        mode: str,
        transition_state: AlarmControlPanelState,
        zones_to_bypass: list | None = None,
    ) -> None:
        self._previous_state = self.partition["state"]
        self.partition["state"] = transition_state
        self.async_write_ha_state()

        try:
            await self.client.set_alarm(
                mode,
                self.imei,
                self.partition["internalId"],
                zones_to_bypass=zones_to_bypass,
            )
        except Exception as ex:
            _LOGGER.error("Failed to set alarm (%s): %s", mode, ex)
            self.partition["state"] = self._previous_state
            self.async_write_ha_state()
            raise

        if mode in (ALARM_MODES["ARM_AWAY"], ALARM_MODES["ARM_HOME"]):
            self._pending_arm_mode = mode
            if self._arm_check_unsub:
                self._arm_check_unsub()
            self._arm_check_unsub = async_call_later(
                self.hass, ARM_CHECK_DELAY_SECONDS, self._check_arm_result
            )

    async def _check_arm_result(self, _now=None):
        """Re-fetch partition status; fire event if arming failed."""
        self._arm_check_unsub = None
        mode = self._pending_arm_mode
        self._pending_arm_mode = None

        try:
            partitions = await self.client.get_device_partitions(self.imei)
        except Exception as ex:
            _LOGGER.warning("Failed to check arm result: %s", ex)
            return

        for partition in partitions:
            if partition.get("internalId") == self.partition["internalId"]:
                current_state = partition.get("state", AlarmControlPanelState.DISARMED)
                if current_state == AlarmControlPanelState.DISARMED:
                    _LOGGER.info(
                        "Arming failed for partition %s - still disarmed after %ds",
                        self.partition["name"],
                        ARM_CHECK_DELAY_SECONDS,
                    )
                    self.partition["state"] = AlarmControlPanelState.DISARMED
                    self.async_write_ha_state()

                    zones = self.data.get("zones", [])
                    zone_info = [
                        {"zone_id": z.get("zoneId"), "zone_name": z.get("zoneName", "")}
                        for z in zones
                        if not z.get("disabled", False)
                    ]

                    self.hass.bus.async_fire(EVENT_ARM_FAILED, {
                        "entity_id": self.entity_id,
                        "partition_name": self.partition["name"],
                        "partition_id": self.partition["internalId"],
                        "mode": mode,
                        "zones": zone_info,
                    })
                else:
                    self.partition["state"] = current_state
                    self.async_write_ha_state()
                break

    async def async_alarm_disarm(self, code=None) -> None:
        await self._async_set_alarm(
            ALARM_MODES["DISARM"],
            AlarmControlPanelState.DISARMING
        )

    async def async_alarm_arm_away(self, code=None) -> None:
        await self._async_set_alarm(
            ALARM_MODES["ARM_AWAY"],
            AlarmControlPanelState.ARMING
        )

    async def async_alarm_arm_home(self, code=None) -> None:
        await self._async_set_alarm(
            ALARM_MODES["ARM_HOME"],
            AlarmControlPanelState.ARMING
        )

    async def async_arm_with_bypass(self, mode: str, zones_to_bypass: list | None = None) -> None:
        """Arm with optional zone bypass, called from service handler."""
        await self._async_set_alarm(
            mode,
            AlarmControlPanelState.ARMING,
            zones_to_bypass=zones_to_bypass,
        )
