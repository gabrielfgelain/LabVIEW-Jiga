import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from nickel import *
import nipple
import time
import enum

@enum.unique
class Freq(enum.IntEnum):
    _40_khz = 1
    _20_khz = 2
    _13_3_khz = 3
    _10_khz = 4

# ==============================================================================
# FUNÇÕES AUXILIARES E LEITURAS DE PARÂMETROS
# ==============================================================================

def read_all(inv: Modbus):
    test_mode = inv.read(TEST_MODE)
    test_mode_timeout = inv.read(TEST_MODE_TIMEOUT)
    state = inv.read(COMPRESSOR_STATE)
    error_code = inv.read(ERROR_CODE)
    gio3 = inv.read(GIO3_FUNCTION)
    power = inv.read(POWER)
    enable_motor = inv.read(ENABLE_MOTOR)
    set_speed = inv.read(SET_SPEED)
    voltage = inv.read(BUS_VOLTAGE)
    speed = inv.read(SPEED)
    temp_pcb = inv.read(TEMPERATURE_PCB)
    temp_hs = inv.read(TEMPERATURE_HEATSINK)
    unlock = inv.read(UNLOCK)

    print(f"Test Mode: {test_mode}")
    print(f"Test Mode Timeout: {test_mode_timeout}")
    print(f"State: {state}")
    print(f"Error code: {ErrorCode(error_code).name}")
    print(f"GIO: {gio3}")
    print(f"Power: {power}")
    print(f"Enable Motor: {enable_motor}")
    print(f"Set Speed: {set_speed}")
    print(f"Temp PCB: {temp_pcb}")
    print(f"Temp HS: {temp_hs}")
    print(f"Bus Voltage: {voltage}")
    print(f"Speed: {speed}")
    print(f"Unlock: {unlock}")

def read_parameters(inv: Modbus):
    data = []
    for param in PARAMETERS:
        addr = PARAMETERS[param]
        val = inv.read(addr)

        catg = PARAMETER_LIST[param]
        if PARAMETER_LIST[param] == nipple.Type.INT:
            print(f"{param}:\n\t{val}, 0x{val:04x}")
        elif PARAMETER_LIST[param] == nipple.Type.BOOL:
            val_b = True if val != 0 else False
            print(f"{param}:\n\t{val_b}")
        elif catg != None:
            repr = catg(val).name
            print(f"{param}:\n\t{repr}")
        else:
            print(f"{param}:\n\t{val}, 0x{val:04x}")
            repr = ""
        data.append({'name': param, 'value': val, 'repr': repr})

BUFFER_SIZE = 500
def get_voltage(inv: Modbus):
    voltage = []
    addr = VOLTAGE
    N_READS = 20
    OFFSET = int(BUFFER_SIZE / N_READS)
    assert(OFFSET < 126)
    assert(BUFFER_SIZE % N_READS == 0)

    for i in range(N_READS):
        voltage_read = inv.read(addr, OFFSET)
        voltage.extend(voltage_read)
        addr.addr += OFFSET

    ADC_GAIN = 5. / 1023.
    VOLT_DIV_GAIN = 1880. / 18
    voltage = [(x >> 6)*ADC_GAIN*VOLT_DIV_GAIN for x in voltage]
    return voltage

def get_speed(inv: Modbus):
    rpm = inv.read(SPEED)
    return rpm

def turn_on_motor(inv: Modbus, velocidade_rpm: int):
    inv.write(SET_SPEED, velocidade_rpm)
    inv.write(ENABLE_MOTOR, 256)

def turn_off_motor(inv: Modbus):
    inv.write(SET_SPEED, 0)
    inv.write(ENABLE_MOTOR, 0)

def read_voltage(inv: Modbus):
    return inv.read(BUS_VOLTAGE)

def read_current(inv: Modbus):
    return inv.read(CURRENT)



# funcoes labview


# ==============================================================================
# FUNÇÕES DE INTERFACE DIRETAS PARA O LABVIEW
# ==============================================================================

PORT_LV = "COM3"  
ID_LV = 1         

_global_inv = None

def _get_connection():
    """Mantém a porta aberta globalmente de forma segura."""
    global _global_inv
    if _global_inv is None:
        try:
            _global_inv = Modbus(port=PORT_LV, slave_id=ID_LV, verbose=False, timeout=3)
        except Exception as e:
            _global_inv = None
    return _global_inv

def main_turn_on_motor():
    """Aba [4]: Retorna estritamente 1 para sucesso ou 0 para falha (Integer no LV)."""
    try:
        inv = _get_connection()
        if inv is None:
            return 0
        inv.write(SET_SPEED, 3000)      
        inv.write(ENABLE_MOTOR, 256)    
        return 1
    except Exception:
        return 0

def main_turn_off_motor():
    """Aba [2]: Retorna estritamente 1 para sucesso ou 0 para falha (Integer no LV)."""
    try:
        inv = _get_connection()
        if inv is None:
            return 0
        inv.write(SET_SPEED, 0)        
        inv.write(ENABLE_MOTOR, 0)      
        return 1
    except Exception:
        return 0

def main_set_speed(speed_val):
    """Aba [1]: Altera a velocidade e retorna o valor definido em Float."""
    try:
        inv = _get_connection()
        if inv is None:
            return -1.0
        
        # Extrai o valor correto de dentro da lista enviada pelo Build Array do LabVIEW
        if isinstance(speed_val, list):
            valor_real = speed_val[0]
        else:
            valor_real = speed_val

        inv.write(SET_SPEED, int(valor_real))
        return float(valor_real)
    except Exception:
        return -1.0

def main_read_speed():
    """Aba [7]: Lê a velocidade real (RPM) e retorna em Float."""
    try:
        inv = _get_connection()
        if inv is None:
            return -1.0
        speed_list = inv.read(SPEED)
        return float(speed_list[0]) if isinstance(speed_list, list) else float(speed_list)
    except Exception:
        return -1.0

def main_read_temperature():
    """Aba [3]: Lê a temperatura da PCB e retorna em Float."""
    try:
        inv = _get_connection()
        if inv is None:
            return -1.0
        temp_list = inv.read(TEMPERATURE_PCB)
        return float(temp_list[0]) if isinstance(temp_list, list) else float(temp_list)
    except Exception:
        return -1.0

def main_read_voltage():
    """Aba [5]: Lê a tensão do barramento e retorna em Float."""
    try:
        inv = _get_connection()
        if inv is None:
            return -1.0
        volt_list = inv.read(BUS_VOLTAGE)
        return float(volt_list[0]) if isinstance(volt_list, list) else float(volt_list)
    except Exception:
        return -1.0

def main_read_current():
    """Aba [6]: Lê a corrente consumida e retorna em Float."""
    try:
        inv = _get_connection()
        if inv is None:
            return -1.0
        current_list = inv.read(CURRENT)
        return float(current_list[0]) if isinstance(current_list, list) else float(current_list)
    except Exception:
        return -1.0


# teste de o main ta funcionando



# if __name__ == '__main__':
#     print("--- INICIANDO TESTE DE CONEXÃO PERSISTENTE ---")
    
#     # 1. Testando a leitura inicial de velocidade (deve retornar 0.0 se parado)
#     print("\n[TESTE 1] Lendo velocidade inicial...")
#     vel_inicial = main_read_speed()
#     print(f"-> Retorno: {vel_inicial} RPM")
    
#     if vel_inicial == -1.0:
#         print("[ERRO] Não foi possível ler a velocidade. Verifique a fiação ou a porta COM.")
#     else:
#         # 2. Testando ligar o motor
#         print("\n[TESTE 2] Tentando ligar o motor...")
#         status_ligar = main_turn_on_motor()
#         print(f"-> Retorno: {status_ligar}")
        
#         if "Erro" not in status_ligar:
#             # 3. Aguarda 5 segundos com o motor rodando e monitora a velocidade
#             print("\n[TESTE 3] Monitorando velocidade por 5 segundos...")
#             for i in range(5):
#                 vel = main_read_speed()
#                 temp = main_read_temperature()
#                 print(f"   [{i+1}s] Velocidade: {vel} RPM | Temp: {temp} °C")
#                 time.sleep(1)
            
#             # 4. Desliga o motor
#             print("\n[TESTE 4] Desligando o motor...")
#             status_desligar = main_turn_off_motor()
#             print(f"-> Retorno: {status_desligar}")
            
#             # Confirmação final de parada
#             time.sleep(2)
#             print(f"-> Velocidade final: {main_read_speed()} RPM")
#         else:
#             print("[AVISO] Como houve erro ao ligar, os testes seguintes foram pulados.")

#     print("\n--- FIM DO TESTE ---")