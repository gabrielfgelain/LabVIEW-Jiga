import sys
import os
import time
import enum

# Adiciona o diretório atual ao path para importar nickel e nipple
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from nickel import *
import nipple

@enum.unique
class Freq(enum.IntEnum):
    _40_khz = 1
    _20_khz = 2
    _13_3_khz = 3
    _10_khz = 4

# ==============================================================================
# CONFIGURAÇÃO E CONEXÃO PERSISTENTE
# ==============================================================================
PORT_LV = "COM3"  
ID_LV = 1         
_global_inv = None

def _get_connection():
    """Mantém a porta aberta globalmente de forma segura."""
    global _global_inv
    if _global_inv is None:
        try:
            # Timeout de 0.5s para comandos e leituras seguras
            _global_inv = Modbus(port=PORT_LV, slave_id=ID_LV, verbose=False, timeout=0.5)
        except Exception:
            _global_inv = None
    return _global_inv

# ==============================================================================
# FUNÇÃO DE LEITURA PARA O LABVIEW (Ultra-Rápida - Sem Corrente)
# ==============================================================================

def main_read_all_fast():
    """
    Lê apenas as variáveis que respondem rápido.
    A corrente (Reg 5000) foi removida para não travar o loop de 50ms.
    """
    inv = _get_connection()
    # [0]Speed, [1]TempHS, [2]TempPCB, [3]Voltage, [4]Current (Fixo)
    data_out = [0.0] * 5
    
    if inv is None:
        return [-1.0] * 5

    # 1. Velocidade (SPEED)
    try:
        res = inv.read(SPEED)
        data_out[0] = float(res[0]) if isinstance(res, list) else float(res)
    except: data_out[0] = -1.0
    
    # 2. Temp Heatsink
    try:
        res = inv.read(TEMPERATURE_HEATSINK)
        data_out[1] = float(res[0]) if isinstance(res, list) else float(res)
    except: data_out[1] = -1.0
    
    # 3. Temp PCB
    try:
        res = inv.read(TEMPERATURE_PCB)
        data_out[2] = float(res[0]) if isinstance(res, list) else float(res)
    except: data_out[2] = -1.0
    
    # 4. Tensão (BUS_VOLTAGE)
    try:
        res = inv.read(BUS_VOLTAGE)
        data_out[3] = float(res[0]) if isinstance(res, list) else float(res)
    except: data_out[3] = -1.0
    
    # 5. Corrente (Removida por performance)
    # Retorna 0.0 fixo para manter o tamanho do array no LabVIEW
    data_out[4] = -1.0
        
    return data_out

# ==============================================================================
# FUNÇÕES DE COMANDO
# ==============================================================================

def main_turn_on_motor():
    try:
        inv = _get_connection()
        if inv is None: return 0
        inv.write(SET_SPEED, 3000)      
        inv.write(ENABLE_MOTOR, 256)    
        return 1
    except Exception: return 0

def main_turn_off_motor():
    try:
        inv = _get_connection()
        if inv is None: return 0
        inv.write(SET_SPEED, 0)        
        inv.write(ENABLE_MOTOR, 0)      
        return 1
    except Exception: return 0

def main_set_speed(speed_val):
    try:
        inv = _get_connection()
        if inv is None: return -1.0
        valor_real = speed_val[0] if isinstance(speed_val, list) else speed_val
        inv.write(SET_SPEED, int(valor_real))
        return float(valor_real)
    except Exception: return -1.0

# ==============================================================================
# FUNÇÕES DE COMPATIBILIDADE
# ==============================================================================

def main_read_speed():
    res = main_read_all_fast()
    return res[0]

def main_read_temperature():
    res = main_read_all_fast()
    return res[2]

def main_read_voltage():
    res = main_read_all_fast()
    return res[3]

def main_read_current():
    # Retorna 0.0 para não travar o Case de corrente se for chamado individualmente
    return 0.0
	

