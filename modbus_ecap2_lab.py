import time
import minimalmodbus
from enum import Enum

class Freq(Enum):
    _40_khz = 1
    _20_khz = 2
    _13_3_khz = 3
    _10_khz = 4


class MaiaInverter(minimalmodbus.Instrument):
    """Maia Inverter process controller.

    Args:
        * portname (str): port name
        * slaveaddress (int): slave address in the range 1 to 247
    """

    # Endereços
    bus_voltage_addr = 4  # R
    temperature_addr = 5  # R
    temperature_bridge_addr = 6  # R
    enable_motor_addr = 7  # RW
    reference_speed_addr = 8  # RW
    motor_real_speed_addr = 9  # R
    real_power_addr = 10  # R
    can_start_save_addr = 11  # RW
    has_finished_save_addr = 12
    read_freq_addr = 13  # RW
    bus_voltage_addr = 1000
    bus_current_addr = 2000

    # Ganhos
    temperature_gain = 0.1
    BUS_VOLTAGE_QBASE = 2048
    INTERNAL_BUS_VOLTAGE_TO_VOLTS = 1031
    BUS_CURRENT_AX100_MCH_Q14 = 31397
    Q14 = 16384
    DEFAULT_CURRENT_OFFSET = 2576  # Offset equivalente a 13,44 A

    def __init__(self, portname, slaveaddress, verbose=True, debug=True):
        minimalmodbus.Instrument.__init__(self, portname, slaveaddress, debug=debug)
        self.serial.parity = minimalmodbus.serial.PARITY_EVEN
        self.serial.timeout = 1
        self.verbose = verbose
        self.serial.baudrate = 9600
        #
        self.serial.bytesize = 8 #eu
        self.serial.stopbits = 1 #eu

    def close(self):
        self.serial.close()

    def set_enable(self, value):
        try:
            self.write_register(self.enable_motor_addr, value, functioncode=6)
            self.log(f"Motor Enable set to: {value}")
        except:
            self.log(f"Error to set enable")

    def log(self, message):
        """Logs a message if verbose mode is enabled."""
        if self.verbose:
            print(f"[LOG] {message}")

    def read_temperature(self):
        temperature = self.read_register(self.temperature_addr)
        temperature = temperature * self.temperature_gain
        if self.verbose:
            print(temperature)
        return temperature

    def read_temperature_bridge(self):
        temperature = self.read_register(self.temperature_bridge_addr)
        temperature = temperature * self.temperature_gain
        if self.verbose:
            print(temperature)
        return temperature

    def read_rpm(self):
        rpm = self.read_register(self.motor_real_speed_addr)
        #if self.verbose:
            #print(rpm)
        return rpm

    def read_avg_bus_voltage(self):
        voltage = self.read_register(self.bus_voltage_addr)
        if self.verbose:
            print(voltage)
        return voltage

    def read_avg_power(self):
        power = self.read_register(self.real_power_addr)
        if self.verbose:
            print(power)
        return power

    def set_speed(self, value):
        try:
            self.write_register(self.reference_speed_addr, value, functioncode=6)
            self.log(f"Motor Speed set to: {value}")
        except:
            self.log(f"Error to set speed")

    def get_set_speed(self):
        speed = self.read_register(self.reference_speed_addr)
        if self.verbose:
            print(speed)
        return speed

    def get_set_enable(self):
        enable = self.read_register(self.enable_motor_addr)
        if self.verbose:
            print(enable)
        return enable

    def get_save_data(self):
        save = self.read_register(self.can_start_save_addr)
        if self.verbose:
            print(save)
        return save

    def start_save_data(self):
        self.write_register(self.can_start_save_addr, 1, functioncode=6)

    def stop_save_data(self):
        self.write_register(self.can_start_save_addr, 0, functioncode=6)

    def has_finished_save(self):
        finished = self.read_register(self.has_finished_save_addr)
        if self.verbose:
            res_str = "Has" if finished else "Has not"
            print(f"{res_str} Finished!")
        return finished

    def set_read_frequency(self, freq: Freq):
        self.write_register(self.read_freq_addr, freq.value, functioncode=6)

    def get_bus_voltage(self):
        self.voltage = []
        self.voltage_raw = []

        for i in range(15):  # Buffer size on MCU is 360
            bus_voltage = self.read_registers(self.bus_voltage_addr, 24)
            self.voltage_raw.extend(bus_voltage)

        for value in self.voltage_raw:
            self.voltage.append(self.convert_voltage_to_float(value))

        #if self.verbose: #Edição ao código original
            ## print(self.voltage) #Edição ao código original
        
        return self.voltage #Edição ao código original

    def get_bus_current(self):
        self.current = []
        self.current_raw = []

        for i in range(15):  # Buffer size on MCU is 360
            bus_current = self.read_registers(self.bus_current_addr, 24)
            self.current_raw.extend(bus_current)

        for value in self.current_raw:
            self.current.append(self.convert_current_to_float(value))

        #if self.verbose:
            #print(self.current)
        
        return self.current #Edição ao código original

    def convert_voltage_to_float(self, value):
        return (value * self.INTERNAL_BUS_VOLTAGE_TO_VOLTS) / self.BUS_VOLTAGE_QBASE

    def convert_current_to_float(self, value):
        return ((value - self.DEFAULT_CURRENT_OFFSET) * self.Q14) / self.BUS_CURRENT_AX100_MCH_Q14


# Função principal para ser chamada pelo LabVIEW
def main():
    maia = MaiaInverter("COM3", 1)  # Porta e endereço do escravo

    try:
        #maia.set_read_frequency(Freq._40_khz)
        #maia.start_save_data()

        # Exemplo de leitura de temperatura
        # temperature = maia.read_temperature()

        #maia.set_speed(5000)    # Para setar a velocidade do inversor
        # maia.set_enable(1)    # Para ligar o inversor

        #maia.set_speed(0)    # Para setar a velocidade do inversor
        #maia.set_enable(0)    # Para desligar o inversor   

        # maia.get_set_enable()


        # maia.get_bus_voltage()

        # maia.get_bus_current()

        # Fechar a conexão ao final
        maia.close()

        #return temperature  # Retorna um valor para LabVIEW se necessário
    except Exception as e:
        print(f"Erro: {e}")
        maia.close()
        return None  # Retorno para indicar erro
    
def main_read_temperature():
    maia = MaiaInverter("COM3", 1)  # Porta e endereço do escravo
    try:
        maia.set_read_frequency(Freq._40_khz)
        maia.start_save_data()
        # Exemplo de leitura de temperatura
        temperature = maia.read_temperature()
        # Fechar a conexão ao final
        maia.close()
        # Retorna um valor para LabVIEW
        print(type(temperature))
        return temperature
    except Exception as e:
        print(f"Erro: {e}")
        maia.close()
        return None  # Retorno para indicar erro

def main_turn_on_motor():
    maia = MaiaInverter("COM3", 1)  # Porta e endereco do escravo
    try:
        maia.set_read_frequency(Freq._40_khz)
        maia.start_save_data()
        # Para definir a velocidade do inversor
        #maia.set_speed(3300)
        # Para ligar o inversor
        maia.set_enable(1)
        return "On"
    except Exception as e:
        print(f"Erro: {e}")
        maia.close()
        return None  # Retorno para indicar erro

def main_turn_off_motor():
    maia = MaiaInverter("COM3", 1)  # Porta e endereço do escravo
    try:
        maia.set_read_frequency(Freq._40_khz)
        maia.start_save_data()
        # Para setar a velocidade do inversor
        maia.set_speed(0)
        # Para ligar o inversor
        maia.set_enable(0)
        return "Off"
    except Exception as e:
        print(f"Erro: {e}")
        maia.close()
        return None  # Retorno para indicar erro

def main_read_voltage():
    maia = MaiaInverter("COM3", 1)  # Porta e endereço do escravo
    try:
        maia.set_read_frequency(Freq._40_khz)
        maia.start_save_data()
        # Exemplo de leitura de tensão
        voltage = maia.get_bus_voltage()
        # Fechar a conexão ao final
        maia.close()
        # Retorna um valor para LabVIEW
        print(voltage)
        return voltage
    except Exception as e:
        print(f"Erro: {e}")
        maia.close()
        return None  # Retorno para indicar erro

def main_read_current():
    maia = MaiaInverter("COM3", 1)  # Porta e endereço do escravo
    try:
        maia.set_read_frequency(Freq._40_khz)
        maia.start_save_data()
        # Exemplo de leitura de corrente
        current = maia.get_bus_current()
        # Fechar a conexão ao final
        maia.close()
        # Retorna um valor para LabVIEW
        print(current)
        return current
    except Exception as e:
        print(f"Erro: {e}")
        maia.close()
        return None  # Retorno para indicar erro
    
def main_read_speed():
    maia = MaiaInverter("COM3", 1)
    try: 
        maia.set_read_frequency(Freq._40_khz)
        maia.start_save_data()
        speed = maia.read_rpm()
        maia.close()
        print(speed)
        return speed
    except Exception as e:
        print(f"Erro: {e}")
        maia.close()
        return None  # Retorno para indicar erro

def main_set_speed(spd):
    maia = MaiaInverter("COM3", 1)  # Porta e endereco do escravo
    try:
        # Para definir a velocidade do inversor
        maia.set_speed(spd)
        # Para ligar o inversor
        maia.close()
        return spd;
    except Exception as e:
        print(f"Erro: {e}")
        maia.close()
        return None;  # Retorno para indicar erro
