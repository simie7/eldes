"""Support for Eldes binary sensors."""
import logging

from homeassistant.components.binary_sensor import (
    BinarySensorEntity,
    BinarySensorDeviceClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import (
    DATA_CLIENT,
    DATA_COORDINATOR,
    DOMAIN,
    ZONE_NAME_DEVICE_CLASS_MAP,
)
from . import EldesDeviceEntity

_LOGGER = logging.getLogger(__name__)

DEVICE_CLASS_LOOKUP = {
    "door": BinarySensorDeviceClass.DOOR,
    "window": BinarySensorDeviceClass.WINDOW,
    "motion": BinarySensorDeviceClass.MOTION,
    "smoke": BinarySensorDeviceClass.SMOKE,
    "gas": BinarySensorDeviceClass.GAS,
    "moisture": BinarySensorDeviceClass.MOISTURE,
    "tamper": BinarySensorDeviceClass.TAMPER,
}


def _detect_device_class(zone_name: str) -> BinarySensorDeviceClass | None:
    """Auto-detect device class from zone name keywords."""
    name_lower = zone_name.lower()
    for keyword, class_key in ZONE_NAME_DEVICE_CLASS_MAP.items():
        if keyword in name_lower:
            return DEVICE_CLASS_LOOKUP.get(class_key)
    return None


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities):
    """Set up the Eldes binary sensor platform."""
    client = hass.data[DOMAIN][entry.entry_id][DATA_CLIENT]
    coordinator = hass.data[DOMAIN][entry.entry_id][DATA_COORDINATOR]
    entities = []

    for index in range(len(coordinator.data)):
        entities.append(EldesConnectionStatusBinarySensor(client, coordinator, index))

        for zone_index, zone in enumerate(coordinator.data[index].get("zones", [])):
            if not zone.get("disabled", False):
                entities.append(EldesZoneSensor(client, coordinator, index, zone_index))

    async_add_entities(entities)


class EldesConnectionStatusBinarySensor(EldesDeviceEntity, BinarySensorEntity):
    """Class for the Eldes connection status sensor."""

    @property
    def unique_id(self):
        return f"{self.imei}_connection_status"

    @property
    def name(self):
        return f"{self.data['info']['model']} Connection Status"

    @property
    def is_on(self):
        return self.data["info"].get("online", False)

    @property
    def device_class(self):
        return BinarySensorDeviceClass.CONNECTIVITY


class EldesZoneSensor(EldesDeviceEntity, BinarySensorEntity):
    """Binary sensor for an individual Eldes alarm zone."""

    def __init__(self, client, coordinator, device_index, zone_index):
        super().__init__(client, coordinator, device_index, zone_index)
        zone = self.data["zones"][zone_index]
        self._zone_id = zone.get("zoneId")
        self._zone_name = zone.get("zoneName", f"Zone {self._zone_id}")
        self._detected_class = _detect_device_class(self._zone_name)

    @property
    def zone(self):
        return self.data["zones"][self.entity_index]

    @property
    def unique_id(self):
        return f"{self.imei}_zone_{self._zone_id}"

    @property
    def name(self):
        return self._zone_name

    @property
    def is_on(self):
        """Zone is 'on' when violated (open door, detected motion, etc.)."""
        active_zones = self.data.get("active_zones", [])
        return any(
            az.get("internalId") == self._zone_id
            for az in active_zones
        )

    @property
    def device_class(self):
        return self._detected_class

    @property
    def extra_state_attributes(self):
        return {
            "zone_id": self._zone_id,
            "disabled": self.zone.get("disabled", False),
            "selected": self.zone.get("selected", True),
        }

    @property
    def icon(self):
        if self._detected_class:
            return None
        return "mdi:shield-alert-outline" if self.is_on else "mdi:shield-check-outline"
