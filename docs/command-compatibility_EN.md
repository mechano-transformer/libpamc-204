# Command Compatibility between PAMC204 and Newport Model8742

## Command Comparison Table

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
| **Velocity Setting** | - | `xxVA nn` | Model8742-specific: 1-2000 steps/sec |
| **Acceleration Setting** | - | `xxAC nn` | Model8742-specific: 1-200000 steps/sec² |
| **Home Position Setting** | - | `xxDH nn` | Model8742-specific feature |
| **Position Check** | - | `xxTP?` | Model8742-specific feature |
| **Motor Type Setting** | - | `xxQM nn` | Model8742-specific feature |
| **Motion Status Check** | - | `xxMD?` | Model8742-specific: 0=moving, 1=stopped |

### Parameter Details Comparison

#### PAMC204 Command Parameters

| Parameter | Range | Description |
|-----------|-------|-------------|
| `xx` | 01-32 | Driver address |
| `nnnn` | 0001-1500 | Drive frequency (Hz) |
| `yyyy` | 0000-9999 | Pulse count (0000=continuous drive) |
| `yyyyyy` | 000001-999999 | Extended pulse count (with X) |
| `z` | A-D | Drive axis (A=CH1, B=CH2, C=CH3, D=CH4) |
| `nnnn` (DAC) | 1900-4095 | Output voltage setting value |

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
   - PAMC204: Specifies frequency and pulse count simultaneously in one command
   - Model8742: Separates velocity setting and movement commands

2. **Voltage Control**
   - PAMC204: Output voltage adjustable from 70-150V
   - Model8742: No voltage control feature

3. **Position Management**
   - PAMC204: Pulse count-based control
   - Model8742: Has concepts of absolute/relative position, home position setting available

4. **Network**
   - PAMC204: Address range 01-32
   - Model8742: Address range 1-31, Ethernet support

5. **Motor Management**
   - PAMC204: 4 axes, only 1 axis can be driven at a time
   - Model8742: 4 axes, motor type auto-detection feature available

### Migration Considerations

1. **Command Conversion Required**
   - One PAMC204 command needs to be split into multiple Model8742 commands

2. **Voltage Control Alternative**
   - Model8742 has no voltage control feature, adjust using velocity parameters instead

3. **Position Management Differences**
   - Model8742 has enhanced position feedback features, enabling more precise control

4. **Error Handling**
   - Error code systems differ, requiring review of error handling logic
