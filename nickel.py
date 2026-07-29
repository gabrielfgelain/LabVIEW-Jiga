"""
Nidec Inverter Communication Kernel and Enumeration Library
"""

import dataclasses
import enum
#from pymodbus.client import ModbusSerialClient
try:
    from pymodbus.client import ModbusSerialClient
except ImportError:
    from pymodbus.client.sync import ModbusSerialClient
# from pymodbus.exceptions import ModbusException
try:
    from pymodbus.pdu import ReadDeviceInformationRequest
except ImportError:
    # Cria uma classe substituta vazia caso a versão antiga do pymodbus não tenha esse import
    class ReadDeviceInformationRequest:
        def __init__(self, *args, **kwargs):
            pass
#from pymodbus.pdu import ReadDeviceInformationRequest
import nipple


@enum.unique
class ErrorCode(enum.IntEnum):
    NO_ERROR = 0
    OVER_TEMPERATURE = enum.auto()
    MOTOR_CABLE = enum.auto()
    STARTUP = enum.auto()
    OVERVOLTAGE = enum.auto()
    OVERLOAD = enum.auto()
    WRONG_ROTOR_POSITION = enum.auto()


@enum.unique
class NumberFormat(enum.Enum):
    INT8 = 0
    UINT8 = enum.auto()
    INT16 = enum.auto()
    UINT16 = enum.auto()
    INT32 = enum.auto()
    UINT32 = enum.auto()
    INT64 = enum.auto()
    UINT64 = enum.auto()
    FLOAT = enum.auto()
    DOUBLE = enum.auto()


@enum.unique
class VariableType(enum.Enum):
    COIL_RW = 1
    COIL_RO = 2
    REGISTER_RW = 3
    REGISTER_RO = 4


@dataclasses.dataclass
class Address:
    addr: int
    gain: float = 1
    variabletype: VariableType = VariableType.COIL_RW
    numberformat: NumberFormat = NumberFormat.INT16
    name: str = ""


class Modbus:
    def __init__(self, port, slave_id = 1, verbose = True,
                 timeout = 1, baudrate = 9600,
                 parity = 'E'):
        self.port_open = False
        self.slave_id = slave_id
        try:
            self.client = ModbusSerialClient(port=port, baudrate=baudrate, parity=parity, timeout=timeout)
            self.client.connect()
            self.verbose = verbose
            self.port_open = True
        except Exception as e:
            print(f"Error opening serial port: {e}")

    def __del__(self):
        if self.port_open:
            self.close()

    def close(self):
        if self.port_open:
            try:
                self.write(SET_SPEED, 0)
                self.write(ENABLE_MOTOR, 0)
                self.client.close()
                print("Serial connection closed.")
            except Exception as e:
                print(f"Error during close: {e}")
            self.port_open = False
        else:
            print("Serial connection already closed.")


    def read(self, addr: Address, n: int = 1):
        if self.port_open == False:
            raise Exception("Port not open")

        _addr = addr.addr & 0xFFFF

        if addr.variabletype == VariableType.REGISTER_RO or \
            addr.variabletype == VariableType.REGISTER_RW:
            if addr.variabletype == VariableType.REGISTER_RW:
                rr = self.client.read_holding_registers(address=_addr, count=n,
                                                        device_id=self.slave_id)
            else: # REGISTER_RO
                rr = self.client.read_input_registers(address=_addr, count=n,
                                                      device_id=self.slave_id)
            if rr.isError():
                raise Exception(f"Modbus Error reading register {_addr}: {rr}")
            raw_buffer = rr.registers
        elif addr.variabletype == VariableType.COIL_RO or \
            addr.variabletype == VariableType.COIL_RW:
            rr = self.client.read_coils(address=_addr, count=n,
                                        device_id=self.slave_id)
            if rr.isError():
                raise Exception(f"Modbus Error reading coil {_addr}: {rr}")
            raw_buffer = rr.bits[0]
        else:
            raise Exception("It must be a read operation")

        if addr.numberformat == NumberFormat.FLOAT or \
           addr.numberformat == NumberFormat.DOUBLE:
           buffer = [float(x) * addr.gain for x in raw_buffer]
           return buffer
        else:
           buffer = [int(x) * addr.gain for x in raw_buffer]
           return buffer

    def write(self, addr: Address, value) -> None:
        if self.port_open == False:
            raise Exception("Port not open")

        if addr.variabletype == VariableType.REGISTER_RW:
            val_to_write = int(value / addr.gain)
            rr = self.client.write_register(address=addr.addr,
                                            value=val_to_write,
                                            device_id=self.slave_id)
            if rr.isError():
                raise Exception(f"Modbus Error writing register {addr.addr}: {rr}")
        elif addr.variabletype == VariableType.COIL_RW:
            rr = self.client.write_coil(address=addr.addr,
                                        value=int(value / addr.gain),
                                        device_id=self.slave_id)
            if rr.isError():
                raise Exception(f"Modbus Error writing coil {addr.addr}: {rr}")
        else:
            raise Exception("It must be a write operation")

    def read_device_info(self):
        # Standard object IDs for Read Device Identification
        object_id_to_name = {
            0x00: "VendorName",
            0x01: "ProductCode",
            0x02: "MajorMinorRevision",
        }

        # The ReadDeviceIdentificationRequest builds the 0x2B request frame.
        # We need to specify the "Read Device ID code" and the starting "Object ID".
        #
        # Read Device ID codes:
        # 0x01: Basic (VendorName, ProductCode, MajorMinorRevision)
        # 0x02: Regular (adds ModelName, UserAppName)
        # 0x03: Extended (adds more objects)
        #
        # We will use 0x01 to read the basic device information.
        # The object_id=0x00 tells the device to start reading from the first object (VendorName).
        
        request = ReadDeviceInformationRequest(read_code=0x01, object_id=0x00,
                                               dev_id=self.slave_id)
        response = self.client.execute(no_response_expected=False, request=request)

                # Check if the response is valid and not an error
        if response.isError():
            print(f"Modbus Error Response: {response}")
        elif not hasattr(response, 'information'):
            print(f"Invalid response received: {response}")
        else:
            print("\n--- Device Information ---")
            # The response.information is a dictionary where keys are object names
            # (integers) and values are the corresponding byte strings.
            for object_id, value in response.information.items():
                # We decode from bytes to a readable string
                try:
                    # Look up the name from the object ID, default to the ID if not found
                    name_str = object_id_to_name.get(object_id, f"ObjectID {object_id}")
                    decoded_value = value.decode('ascii')
                    print(f"{name_str:<20}: {decoded_value}")
                except UnicodeDecodeError:
                    print(f"{name_str:<20}: {value!r} (could not decode as ascii)")
            print("--------------------------\n")


PARAMETER_ADDR = 300
PARAMETER_LIST = {"LAYOUT_CFG": nipple.Layout,
                  "CLOCK_SOURCE_CFG": nipple.ClockSource,
                  "CLOCK_FREQ_CFG": nipple.ClockFreq,
                  "LOW_POWER_MODE_CFG": nipple.Type.BOOL,
                  "OPERATION_MODE_CFG": nipple.OperationMode,
                  "DEBUGGING_ENVIRONMENT": nipple.DebuggingEnvironment,
                  "SERIAL_CURVE": nipple.SerialCurve,
                  "SPEED_CURVE": nipple.FrequencyCurve,
                  "THERMOSTAT_INPUT_LOGIC_CFG": nipple.ThermostatInputLogic,
                  "THERMOSTAT_CFG": nipple.ThermostatConfig,
                  "STARTUP_PROCEDURE_CONFIG": nipple.StartupProcedure,
                  "STARTUP_TIME_CONFIG": nipple.StartTime,
                  "RUNNING_STRATEGY_CFG": nipple.RunningStrategy,
                  "OVERDRIVE_ESTRATEGY_CFG": nipple.Type.BOOL,
                  "POWER_PROTECTION_CFG": nipple.Type.BOOL,
                  "SUBSPEED_PROTECTION_CFG": nipple.Type.BOOL,
                  "CURRENT_WAVEFORM_MATCHING_DRIVE_CFG": nipple.Type.BOOL,
                  "DROP_IN_CUSTOM_CFG": nipple.DropInCustomConfig,
                  "LED_BLINK_IN_NORMAL_OPERATION": nipple.Type.BOOL,
                  "COMPRESSOR_MODEL": nipple.CompressorModel,
                  "MAX_MOTOR_SPEED": None,
                  "MIN_MOTOR_SPEED": None,
                  "ENABLE_CHECKSUM_VERIFICATION": nipple.Type.BOOL,
                  "CHECKSUM_CALC": None,
                  "CHECKSUM_REF": None,
                  "FIRMWARE_END_ADDRESS_1": None,
                  "FIRMWARE_END_ADDRESS_2": None,
                  "VES_POWER_CURVE_50C": nipple.Type.BOOL,
                  "OVERDRIVE_SWITCHING_PATTERN": 
                  nipple.OverdriveSwitchingPattern,
                  "TEMPERATURE_LIMITATION_CFG": nipple.Type.BOOL,
                  "TEMPERATURE_SHUTDOWN_CFG": nipple.Type.BOOL,
                  "PWM_JITTER_STRATEGY_CFG": nipple.Type.BOOL,
                  "KNOCKING_NOISE_PROTECTION": nipple.KnockingNoise,
                  "MOTOR_CURRENT_PROTECT_RANGE": 
                  nipple.MotorCurrentProtectRange,
                  "ADJUST_H_PARAMETER": nipple.Type.BOOL,
                  "H_PARAMETER": nipple.HParameterApplicationLevel,
                  "EXTENDED_FORBIDDEN_SPEEDS_CFG": nipple.ExtendedForbiddenSpeeds,
                  "SERIAL_BROKEN_CABLE_MODE": nipple.Type.BOOL,
                  "ENABLE_FREQ_DOUBLE_INSULATION": nipple.Type.BOOL,
                  "PEC_RESET_ENABLED": nipple.Type.BOOL,
                  "DOUBLER_LOGIC_CFG": nipple.DoublerLogic,
                  "RELAY_DRIVER_ENABLED": nipple.Type.BOOL,
                  "FAN_RELAY_ENABLED": nipple.Type.BOOL,
                  "THERMO_INC_LIMIT_PER_SEC": None,
                  "THERMO_DEC_LIMIT_PER_SEC": None,
                  "USE_NEW_DIAGNOSE_MODULE": nipple.Type.BOOL,
                  "PRODUCT_CFG": nipple.ProductConfig,
                  "PFC_INPUT_CFG": nipple.PFCInputConfig,
                  "OVERHEATING_PROTECTION_CFG": nipple.Type.BOOL,
                  "STARTUP_HARMONICS_REDUCTION": nipple.Type.BOOL,
                  "USE_MODIFIED_POWER_LIM_CFG": nipple.Type.BOOL,
                  "MICROPROCESSOR_CFG": nipple.Microprocessor,
                  "STALL_LIMITATION_CFG": nipple.Type.BOOL,
                  "USE_UNDERVOLTAGE_PROTECTION": nipple.Type.BOOL,
                  "ENABLE_BOOTLOADER": nipple.Type.BOOL,
                  "PUMP_OUT_PROT_ENABLE": nipple.Type.BOOL,
                  "FIXED_SPEED": None,
                  "SMART_DROPIN_CFG": nipple.SmartDropIn,
                  "MAINSTAINS_WAIT_TIME_EVEN_WITH_THERM_SHUTDOWN": 
                  nipple.Type.BOOL,
                  "OPTIMIZED_ALIGNMENT": nipple.Type.BOOL,
                  "USE_OVERVOLTAGE_PROTECTION": nipple.Type.BOOL,
                  "SWITCHING_FREQUENCY_MODE": nipple.SwitchingFrequencyMode,
                  "USE_AD_POISTION_SENSOR": nipple.Type.BOOL,
                  "ACTIVE_VIBRATION_CFG": nipple.ActiveVibration,
                  "COMPILATION_MODE_CFG": nipple.CompilationMode,
                  "USE_VOLTAGE_SPIKE_PROTECTION_CFG": nipple.Type.BOOL,
                  }
                    
PARAMETERS = {name: Address(i + PARAMETER_ADDR, 1,
                            VariableType.REGISTER_RO, NumberFormat.INT8,
                            name) for i, name in enumerate(PARAMETER_LIST)}


TEST_MODE = Address(30876, 1, VariableType.REGISTER_RW,
                    NumberFormat.INT8, "Test Mode")
TEST_MODE_TIMEOUT = Address(30888, 1, VariableType.REGISTER_RW,
                            NumberFormat.INT8, "Test Mode Timeout")
COMPRESSOR_STATE = Address(30918, 1, VariableType.REGISTER_RW,
                           NumberFormat.INT8, "Compressor State")
ERROR_CODE = Address(31009, 1, VariableType.REGISTER_RW,
                     NumberFormat.INT8, "Error code")
GIO3_FUNCTION = Address(31084, 1, VariableType.REGISTER_RW,
                        NumberFormat.INT8, "GIO3 Function")
POWER = Address(33773, 0.1, VariableType.REGISTER_RW,
                NumberFormat.FLOAT, "Power")
ENABLE_MOTOR = Address(35008, 1, VariableType.REGISTER_RW,
                       NumberFormat.INT8, "Enable Motor")
SET_SPEED = Address(35009, 1, VariableType.REGISTER_RW,
                    NumberFormat.INT16, "Set Speed")
TEMPERATURE_HEATSINK = Address(35096, 0.01, VariableType.REGISTER_RW,
                               NumberFormat.FLOAT, "Temperature Heatsink")
TEMPERATURE_PCB = Address(35098, 0.01, VariableType.REGISTER_RW,
                          NumberFormat.FLOAT, "Temperature PCB")
BUS_VOLTAGE = Address(35116, 0.1, VariableType.REGISTER_RW,
                      NumberFormat.FLOAT, "Bus Voltage")
SPEED = Address(35097, 1, VariableType.REGISTER_RW,
                NumberFormat.INT16, "Speed")
UNLOCK = Address(60035, 1, VariableType.REGISTER_RW,
                 NumberFormat.INT8, "Unlock")


VOLTAGE= Address(1000, 1, VariableType.REGISTER_RO,
                 NumberFormat.INT16, "Voltage")
CURRENT = Address(5000, 1 / 100, VariableType.REGISTER_RO,
                 NumberFormat.FLOAT, "Current")
FINISHED_SAVE = Address(0x0c, 1, VariableType.REGISTER_RO,
                 NumberFormat.INT16, "finished")


CAN_START_SAVE = Address(0x0b, 1, VariableType.REGISTER_RW,
                 NumberFormat.INT16, "can_start_save")
DECIMATION = Address(0x0d, 1, VariableType.REGISTER_RW,
                     NumberFormat.INT16, "decimation")