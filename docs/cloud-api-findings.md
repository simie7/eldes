# Eldes Cloud API Findings

Discovered via APK decompilation (JADX) of the Eldes Security Android app and
live testing against `cloud.eldesalarms.com:8083`.

## Base URL

```
https://cloud.eldesalarms.com:8083/api/
```

## Authentication

| Endpoint | Method | Body |
|---|---|---|
| `auth/login` | POST | `{ "email", "password", "hostDeviceId" }` |
| `auth/token` | GET | Bearer refresh-token in `Authorization` header |

Login returns `{ "token", "refreshToken" }`. Tokens expire after ~5 minutes.

## REST Endpoints

### Device Management

| Endpoint | Method | Notes |
|---|---|---|
| `device/list` | GET | Returns `{ "deviceListEntries": [...] }` |
| `device/info?imei={imei}` | GET | Device model, firmware, online status |
| `device/partition/list?imei={imei}` | POST | Body: `{ "imei", "pin" }`. Returns `{ "partitions": [...] }` |
| `device/list-outputs/{imei}` | POST | Body: `{ "imei", "pin" }`. Returns `{ "deviceOutputs": [...] }` |
| `device/temperatures?imei={imei}` | POST | Body: `{ "pin" }`. Returns `{ "temperatureDetailsList": [...] }` |
| `device/event/list` | POST | Body: `{ "imei", "size", "start", "pin" }`. Returns `{ "eventDetails": [...] }` |

### Zone List (NEW - discovered via APK decompilation)

| Endpoint | Method | Notes |
|---|---|---|
| `device/list-zones/{imei}` | GET | Returns array of zone objects |

Each zone object:
```json
{
  "zoneId": 7,
  "zoneName": "Terasos durys",
  "disabled": false,
  "selected": true
}
```

Tested on ESIM364 - returns all 72 configured zones.

### System Faults (NEW - discovered via APK decompilation)

| Endpoint | Method | Notes |
|---|---|---|
| `device/system-fault/list/{imei}` | POST | Body: `{ "pin" }`. Returns active system faults |

### Arm/Disarm Actions

| Endpoint | Method | Notes |
|---|---|---|
| `device/action/arm` | POST | Arm away |
| `device/action/armstay` | POST | Arm home/stay |
| `device/action/disarm` | POST | Disarm |

Standard body:
```json
{
  "imei": "...",
  "partitionIndex": 0,
  "pin": "1234"
}
```

### Zone Bypass (NEW - confirmed via live testing)

Add `zonesToBypass` to the arm/armstay request body:

```json
{
  "imei": "...",
  "partitionIndex": 0,
  "pin": "1234",
  "zonesToBypass": [7, 12]
}
```

- `zonesToBypass` is an `ArrayList<Long>` of internal zone IDs
- Discovered from APK class `ActionPartitionRequest` (`sources/I3/c.java`)
- Successfully tested: bypassing zone 7 ("Terasos durys") during armstay with an open door

### Output Control

| Endpoint | Method | Notes |
|---|---|---|
| `device/control/enable/{imei}/{outputId}` | PUT | Body: `{ "pin" }` |
| `device/control/disable/{imei}/{outputId}` | PUT | Body: `{ "pin" }` |

**Note:** Original upstream code sends `{"": "", "pin": "..."}` in some request
bodies. The empty key-value pair `"": ""` is unnecessary and should be removed.

## WebSocket / STOMP Protocol

### Connection

```
wss://cloud.eldesalarms.com:8083/eldes/websocket
```

Uses STOMP over WebSocket. Discovered from APK class `sources/z3/f.java`.

### Subscription Topics

| Topic | Purpose |
|---|---|
| `/user/queue/device/response` | Responses to commands (arm/disarm results) |
| `/user/queue/device/event` | Real-time event notifications |
| `/user/queue/device/sync/progress` | Sync progress updates |

### Response Message Structure

From APK class `ResponseMessage.java`:

```json
{
  "activeZones": [{"internalId": 7, "name": "Terasos durys"}],
  "activeTampers": [...],
  "activeFaults": [...],
  "partitionStatus": "ARMED|DISARMED|ARMSTAY",
  "commandType": "ARM|DISARM|ARMSTAY"
}
```

### Active Zones Behavior

- `activeZones` are returned in the WebSocket response **only** when an arm
  command is attempted while zones are violated (open doors/windows, triggered
  PIR sensors)
- Each entry is an `ActiveZoneOrTamper` object with `internalId` (Long) and
  `name` (String)
- **No unsolicited zone status updates** are sent when doors open/close - the
  WebSocket only reports zone violations in response to arm commands
- This means continuous real-time zone monitoring is **not available** via the
  cloud API alone

## Limitations

- Zone status (open/closed) is only available as a side-effect of arm commands
- No endpoint found for querying real-time zone status directly
- WebSocket does not push zone state changes proactively
- For real-time sensor monitoring, local integration (USB/RS485) is needed
