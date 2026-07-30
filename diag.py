import sys
import time
try:
    from pymodbus.client import ModbusSerialClient
except ImportError:
    from pymodbus.client.sync import ModbusSerialClient

# ==============================================================================
# CONFIGURAÇÃO OTIMIZADA
# ==============================================================================
PORT = "COM3"
BAUDRATE = 9600
PARITY = "E"
TIMEOUT = 0.3  # Reduzido para resposta rápida
RETRIES = 0    # Não reverte em caso de falha para ganhar tempo
SLAVE_ID = 1
ADDR_CURRENT = 5000

def test_current():
    client = ModbusSerialClient(
        port=PORT, 
        baudrate=BAUDRATE, 
        parity=PARITY, 
        timeout=TIMEOUT,
        retries=RETRIES
    )
    
    print(f"\n--- Testando Endereço {ADDR_CURRENT} (Timeout: {TIMEOUT}s) ---")
    
    if not client.connect():
        print(f"[ERRO] Falha ao abrir a porta {PORT}")
        return

    # Tenta ler como Holding Register (03)
    print("Tentando Holding Register (03)...", end=" ", flush=True)
    start = time.time()
    rr = client.read_holding_registers(address=ADDR_CURRENT, count=1, slave=SLAVE_ID)
    end = time.time()
    if rr.isError():
        print(f"FALHA ({end-start:.2f}s) -> {rr}")
    else:
        print(f"SUCESSO ({end-start:.2f}s) -> Valor: {rr.registers}")

    # Tenta ler como Input Register (04)
    print("Tentando Input Register (04)...", end=" ", flush=True)
    start = time.time()
    ir = client.read_input_registers(address=ADDR_CURRENT, count=1, slave=SLAVE_ID)
    end = time.time()
    if ir.isError():
        print(f"FALHA ({end-start:.2f}s) -> {ir}")
    else:
        print(f"SUCESSO ({end-start:.2f}s) -> Valor: {ir.registers}")

    client.close()
    print("-" * 45)

if __name__ == "__main__":
    test_current()
