# Command Compatibility between PAMC204 and Newport Model8742

## Command Comparison Table

> **Disclaimer:** This document provides a command compatibility reference between PAMC204 and Newport Model8742. While the commands are designed to be compatible, **100% compatibility cannot be guaranteed** due to differences in hardware implementation, firmware behavior, and device-specific features. Users should thoroughly test all commands in their specific application environment before deployment.

### Basic Concept Correspondence

- **Frequency (PAMC204) [pulses/sec] = Velocity (Model8742) [steps/sec]**
- **Pulse Count (PAMC204) [pulses] = Step Count (Model8742) [steps]**

### Main Command Comparison

| Function | PAMC204 | Newport Model8742 | Notes |
|----------|---------|-------------------|-------|
| **1. Firmware Version Check** | `ExxINF` | `VE?` or `*IDN?` | PAMC204: Displays firmware version and baud rate<br>Model8742: Two commands available |
| **2. Address Check** | `Exx` | `SA?` | PAMC204: xx=01-32, response=`ExxOK`<br>Model8742: 1-31 |
| **3. Address Setting** | `SETADDRxx` | `SA nn` | PAMC204: Only available for single connection<br>Both for RS-485 network |
| **4. Output Voltage Adjustment** | `ExxDACnnnn` | - | PAMC204-specific feature (70-150V)<br>nnnn: 1900-4095 (9 levels) |
| **5. Forward Rotation Drive** | `ExxNRnnnnyyyyz`<br>`ExxNRnnnnXyyyyyyz` | `xxPA nn`<br>`xxPR nn`<br>`xxMV+` | PAMC204: Frequency(1-1500Hz)+Pulse count(0-9999 or 0-999999) specification<br>yyyy=0000 for continuous drive<br>Model8742: Absolute position/Relative move/Continuous |
| **6. Reverse Rotation Drive** | `ExxRRnnnnyyyyz`<br>`ExxRRnnnnXyyyyyyz` | `xxPA nn`<br>`xxPR nn`<br>`xxMV-` | Same as above (reverse direction) |
| **7. Stop** | `ExxS` | `xxST`<br>`AB` | PAMC204: Stops continuous drive, response=`ExxFINnnnn`(displays driven pulse count)<br>Model8742: ST=decelerated stop, AB=immediate stop |
| **8. Motion Stop** | `ExxAB` | `AB` | PAMC204: Immediate stop all CH<br>Model8742: Immediate stop all axes |
| **9. Velocity Setting** | `ExxmVAnnnn` | `xxVA nn` | PAMC204: 1-1500 steps/sec, m=1-4 (CH specification)<br>Model8742: 1-2000 steps/sec |
| **10. Velocity Query** | `ExxmVA?` | `xxVA?` | PAMC204: m=1-4 (CH specification) |
| **11. Home Position Setting** | `ExxmDHnnnn` | `xxDH nn` | PAMC204: m=1-4 (CH specification), nnnn=-2147483648~+2147483647<br>Model8742: Absolute position setting |
| **12. Home Position Query** | `ExxmDH?` | `xxDH?` | PAMC204: m=1-4 (CH specification) |
| **13. Absolute Position Move** | `ExxmPAnnnn` | `xxPA nn` | PAMC204: m=1-4 (CH specification), nnnn=-2147483648~+2147483647 |
| **14. Absolute Position Query** | `ExxmPA?` | `xxPA?` | PAMC204: m=1-4 (CH specification), returns target position when moving, actual position when stopped |
| **15. Relative Position Move** | `ExxmPRnnnn` | `xxPR nn` | PAMC204: m=1-4 (CH specification), nnnn=-2147483648~+2147483647 |
| **16. Relative Position Query** | `ExxmPR?` | `xxPR?` | PAMC204: m=1-4 (CH specification), returns target position when moving, actual position when stopped |
| **17. Actual Position Query** | `ExxmTP?` | `xxTP?` | PAMC204: m=1-4 (CH specification), returns current actual position |
| **18. Motion Status Check** | `ExxmMD?` | `xxMD?` | PAMC204: m=1-4 (CH specification), 0=moving, 1=stopped<br>Model8742: 0=moving, 1=stopped |
| **19. Infinite Move** | `ExxmMVn` | `xxMV+/-` | PAMC204: m=1-4 (CH specification), n=+/- (direction specification) |
| **20. Move Direction Query** | `ExxmMV?` | - | PAMC204-specific, m=1-4 (CH specification), 0=moving, 1=stopped |
| **21. Motion Stop** | `ExxmST` | `xxST` | PAMC204: m=1-4 (CH specification), decelerated stop<br>Model8742: Decelerated stop |
| **Acceleration Setting** | - | `xxAC nn` | Model8742-specific: 1-200000 steps/sec² |
| **Motor Type Setting** | - | `xxQM nn` | Model8742-specific feature |

### Parameter Details Comparison

#### PAMC204 Command Parameters

| Parameter | Range | Description |
|-----------|-------|-------------|
| `xx` | 01-32 | Driver address |
| `m` | 1-4 | Channel number (for position control commands) |
| `nnnn` | 0001-1500 | Drive frequency (Hz) or Velocity (steps/sec) |
| `yyyy` | 0000-9999 | Pulse count (0000=continuous drive) |
| `yyyyyy` | 000001-999999 | Extended pulse count (with X) |
| `z` | A-D | Drive axis (A=CH1, B=CH2, C=CH3, D=CH4) |
| `nnnn` (DAC) | 1900-4095 | Output voltage setting value |
| `nnnn` (position) | -2147483648 ~ +2147483647 | Absolute/Relative position |
| `n` (direction) | +/- | Move direction (+: forward, -: reverse) |

#### Model8742 Command Parameters

| Parameter | Range | Description |
|-----------|-------|-------------|
| `xx` | 1-4 | Axis number |
| `nn` (VA) | 1-2000 | Velocity (steps/sec) |
| `nn` (AC) | 1-200000 | Acceleration (steps/sec²) |
| `nn` (PA/PR) | -2147483648 ~ +2147483647 | Position (step count) |
| `nn` (QM) | 0-3 | Motor type |

### Output Voltage Correspondence Table (PAMC204 only)

| DAC Command Value | Output Voltage |
|-------------------|----------------|
| 4095 | 150V |
| 3750 | 140V |
| 3450 | 130V |
| 3200 | 120V |
| 3000 | 110V |
| 2700 | 100V |
| 2450 | 90V |
| 2200 | 80V |
| 1900 | 70V |

## Communication Specification Comparison

| Item | PAMC204 | Model8742 |
|------|---------|-----------|
| **Interface** | USB Serial/RS-485 | USB/Ethernet/RS-485 |
| **Baud Rate** | 115200 bps | 115200 bps |
| **Data Bits** | 8 Bit | 8 Bit |
| **Parity** | None | None |
| **Stop Bits** | 1 Bit | 1 Bit |
| **Delimiter** | CR + LF | CR + LF |

### Error Message Comparison

#### PAMC204 Errors

| Error | Description |
|-------|-------------|
| `Error Value Range` | Specified value is out of range during output voltage adjustment |
| `ERROR` | Rotation direction specification error/Frequency out of range/Channel specification out of range |
| `ERROR1` | Command not recognized |
| `ERROR4` | Pulse count out of range when specified in 6 digits |
| `ERROR5` | Pulse count out of range when specified in 4 digits |
| `BUSY` | Driver is in operation |

#### Model8742 Errors (Main ones)

| Error Code | Description |
|------------|-------------|
| 0 | No error |
| 3 | Over-temperature shutdown |
| 6 | Command does not exist |
| 7 | Parameter out of range |
| 9 | Axis number out of range |
| x08 | Motor not connected |
| x14 | In motion |

### Usage Example Comparison

#### Example 1: Rotate motor 1 forward at 1500Hz for 1500 pulses

**PAMC204:**

```
E01NR15001500A
```

**Model8742:**

```
1VA1500
1PR1500
```

#### Example 2: Continuous forward rotation of motor 2

**PAMC204:**

```
E01NR15000000B
```

**Model8742:**

```
2VA1500
2MV+
```

#### Example 3: Stop

**PAMC204:**

```
E01S
```

**Model8742:**

```
2ST    (decelerated stop)
AB     (immediate stop)
```

### Summary of Main Differences

1. **Command System**
   - PAMC204:
     - Pulse drive commands: Specifies frequency and pulse count simultaneously in one command (`ExxNR`/`ExxRR`)
     - Position control commands: Model8742-compatible position control commands supported
   - Model8742: Separates velocity setting and movement commands

2. **Voltage Control**
   - PAMC204: Output voltage adjustable from 70-150V (`ExxDACnnnn`)
   - Model8742: No voltage control feature

3. **Position Management**
   - PAMC204: Supports both pulse count-based control and position-based control
   - Model8742: Has concepts of absolute/relative position, home position setting available

4. **Network**
   - PAMC204: Address range 01-32
   - Model8742: Address range 1-31, Ethernet support

5. **Motor Management**
   - PAMC204: 4 axes, only 1 axis can be driven at a time
   - Model8742: 4 axes, motor type auto-detection feature available

### Migration Considerations

1. **Command System Selection**
   - Pulse drive commands: Specifies frequency and pulse count in one command (simple)
   - Position control commands: Model8742-compatible, position management available (advanced)

2. **Voltage Control**
   - PAMC204-specific `ExxDACnnnn` command for output voltage adjustment
   - Model8742 has no voltage control feature, adjust using velocity parameters instead

3. **Position Management**
   - PAMC204: Implements position feedback features similar to Model8742
   - Absolute position, relative position, and home position setting available

4. **Error Handling**
   - Error code systems differ, requiring review of error handling logic
   - PAMC204 uses string-based errors, Model8742 uses numeric codes

5. **Simultaneous Drive Limitation**
   - PAMC204: Only 1 CH can be driven at a time per unit
   - Driving another CH automatically stops the currently running motor
