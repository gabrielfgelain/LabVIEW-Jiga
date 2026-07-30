"""
Script de diagnóstico para leitura de corrente via Modbus.

Objetivo: descobrir por que main_read_current() falha, já que não temos
acesso ao mapa de registradores oficial da Nidec.

Estratégias testadas:
  1. Ler o endereço CURRENT (5000) via read_holding_registers (RW/03) e
     read_input_registers (RO/04), mostrando o erro exato de cada tentativa.
  2. Varrer uma faixa de endereços próximos de 5000 com as duas funções,
     reportando quais respondem sem erro (mesmo que o valor pareça sem sentido).
  3. Testar outros slave IDs, caso o registrador de corrente esteja em
     outro dispositivo/endereço no barramento RS-485.

IMPORTANTE:
  - Ajuste PORT, BAUDRATE, PARITY e TIMEOUT conforme sua configuração real.
  - Rode com o motor LIGADO e DESLIGADO para comparar se o valor de corrente
    muda (isso ajuda a confirmar se achou o registrador certo).
  - Esse script só LÊ registradores. Não escreve em nada, então é seguro
    rodar para exploração.
"""

import sys
import os
import time

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from pymodbus.client import ModbusSerialClient
except ImportError:
    from pymodbus.client.sync import ModbusSerialClient

# ==============================================================================
# CONFIGURAÇÃO — AJUSTE AQUI
# ==============================================================================

PORT = "COM3"
BAUDRATE = 9600
PARITY = "E"
TIMEOUT = 1
SLAVE_ID = 1

# Faixa de endereços a varrer em torno do 5000 (ajuste se quiser mais/menos range)
SCAN_START = 4990
SCAN_END = 5010

# Outros slave IDs a testar (além do SLAVE_ID acima), caso a corrente esteja
# em outro dispositivo do barramento
OUTROS_SLAVE_IDS = [1, 2, 3]

# ==============================================================================
# FUNÇÕES DE TESTE
# ==============================================================================

def conectar():
    client = ModbusSerialClient(port=PORT, baudrate=BAUDRATE, parity=PARITY, timeout=TIMEOUT)
    ok = client.connect()
    if not ok:
        print(f"[ERRO] Não foi possível abrir a porta {PORT}")
        sys.exit(1)
    print(f"[OK] Porta {PORT} aberta (baud={BAUDRATE}, parity={PARITY})\n")
    return client


def tentar_leitura(client, address, slave_id, count=1, label=""):
    """Tenta ler um endereço via holding (03) e input (04) registers.
    Retorna um dict com os resultados de cada tentativa."""
    resultado = {}

    # --- Holding registers (function code 03) ---
    try:
        rr = client.read_holding_registers(address=address, count=count, device_id=slave_id)
        if rr.isError():
            resultado["holding"] = f"ERRO: {rr}"
        else:
            resultado["holding"] = f"OK -> {rr.registers}"
    except Exception as e:
        resultado["holding"] = f"EXCEÇÃO: {e}"

    # --- Input registers (function code 04) ---
    try:
        rr = client.read_input_registers(address=address, count=count, device_id=slave_id)
        if rr.isError():
            resultado["input"] = f"ERRO: {rr}"
        else:
            resultado["input"] = f"OK -> {rr.registers}"
    except Exception as e:
        resultado["input"] = f"EXCEÇÃO: {e}"

    print(f"[addr={address:>5} slave={slave_id} {label}]")
    print(f"    holding(03): {resultado['holding']}")
    print(f"    input  (04): {resultado['input']}")

    return resultado


def teste_1_endereco_atual(client):
    print("=" * 70)
    print("TESTE 1: Endereço atual usado para CURRENT (5000), slave =", SLAVE_ID)
    print("=" * 70)
    tentar_leitura(client, 5000, SLAVE_ID, label="(CURRENT atual)")
    print()


def teste_2_varredura(client):
    print("=" * 70)
    print(f"TESTE 2: Varredura de {SCAN_START} até {SCAN_END}, slave = {SLAVE_ID}")
    print("=" * 70)
    sucesso = []
    for addr in range(SCAN_START, SCAN_END + 1):
        r = tentar_leitura(client, addr, SLAVE_ID)
        if "OK" in r["holding"] or "OK" in r["input"]:
            sucesso.append(addr)
        time.sleep(0.05)  # evita sobrecarregar o barramento
    print()
    print(f"--> Endereços que responderam sem erro: {sucesso}")
    print()


def teste_3_outros_slaves(client):
    print("=" * 70)
    print(f"TESTE 3: Testando endereço 5000 em outros slave IDs {OUTROS_SLAVE_IDS}")
    print("=" * 70)
    for sid in OUTROS_SLAVE_IDS:
        tentar_leitura(client, 5000, sid, label="(testando slave)")
        time.sleep(0.05)
    print()


def teste_4_comparar_motor(client):
    print("=" * 70)
    print("TESTE 4: Comparar valor do(s) endereço(s) candidato(s) com motor LIGADO/DESLIGADO")
    print("=" * 70)
    print("Esse teste é manual: depois de identificar endereços candidatos nos")
    print("testes 2/3, ligue e desligue o motor manualmente e rode:")
    print()
    print("    tentar_leitura(client, <endereco_candidato>, <slave_id>)")
    print()
    print("Se o valor mudar de forma consistente com o motor ligando/desligando,")
    print("é um forte indício de que esse é o registrador de corrente correto.")
    print()


# ==============================================================================
# EXECUÇÃO
# ==============================================================================

if __name__ == "__main__":
    client = conectar()

    try:
        teste_1_endereco_atual(client)
        teste_2_varredura(client)
        teste_3_outros_slaves(client)
        teste_4_comparar_motor(client)
    finally:
        client.close()
        print("[OK] Conexão fechada.")