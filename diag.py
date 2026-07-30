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

# Faixa de endereços a varrer. O teste anterior mostrou SILÊNCIO TOTAL
# (timeout, não erro de endereço inválido) em toda a faixa 4990-5010,
# o que sugere que essa região não existe nesse device. Os outros
# parâmetros que funcionam (SPEED, BUS_VOLTAGE, etc.) estão todos entre
# 30000-60000, então focamos a varredura nessa vizinhança conhecida.
SCAN_START = 35000
SCAN_END = 35130

# Outros slave IDs a testar (além do SLAVE_ID acima), caso a corrente esteja
# em outro dispositivo do barramento
OUTROS_SLAVE_IDS = [1, 2, 3]

# Reconecta a cada tentativa, para evitar que o pymodbus feche a conexão
# sozinho após timeouts seguidos e invalide o restante do teste
RECONNECT_EVERY_TRY = True

# ==============================================================================
# FUNÇÕES DE TESTE
# ==============================================================================

def conectar():
    client = ModbusSerialClient(port=PORT, baudrate=BAUDRATE, parity=PARITY, timeout=TIMEOUT)
    ok = client.connect()
    if not ok:
        print(f"[ERRO] Não foi possível abrir a porta {PORT}")
        sys.exit(1)
    return client


def tentar_leitura(address, slave_id, count=1, label=""):
    """Abre uma conexão nova, tenta ler um endereço via holding (03) e
    input (04) registers, e fecha a conexão. Reconectar a cada tentativa
    evita que timeouts seguidos derrubem o client e invalidem os testes
    seguintes (foi o que aconteceu na primeira rodada)."""
    resultado = {}
    client = conectar()

    # --- Holding registers (function code 03) ---
    try:
        rr = client.read_holding_registers(address=address, count=count, device_id=slave_id)
        if rr.isError():
            resultado["holding"] = f"ERRO: {rr}"
        else:
            resultado["holding"] = f"OK -> {rr.registers}"
    except Exception as e:
        resultado["holding"] = f"EXCEÇÃO: {e}"

    try:
        client.close()
    except Exception:
        pass
    client = conectar()

    # --- Input registers (function code 04) ---
    try:
        rr = client.read_input_registers(address=address, count=count, device_id=slave_id)
        if rr.isError():
            resultado["input"] = f"ERRO: {rr}"
        else:
            resultado["input"] = f"OK -> {rr.registers}"
    except Exception as e:
        resultado["input"] = f"EXCEÇÃO: {e}"

    try:
        client.close()
    except Exception:
        pass

    print(f"[addr={address:>5} slave={slave_id} {label}]")
    print(f"    holding(03): {resultado['holding']}")
    print(f"    input  (04): {resultado['input']}")

    return resultado


def teste_0_sanity_check():
    """Confirma que a config básica (porta/baud/parity/slave) está correta,
    lendo um endereço que sabemos que funciona no main.py (SPEED = 35097)."""
    print("=" * 70)
    print("TESTE 0: Sanity check - lendo SPEED (35097), que já funciona no main.py")
    print("=" * 70)
    tentar_leitura(35097, SLAVE_ID, label="(SPEED, referência conhecida)")
    print()


def teste_1_endereco_atual():
    print("=" * 70)
    print("TESTE 1: Endereço atual usado para CURRENT (5000), slave =", SLAVE_ID)
    print("=" * 70)
    tentar_leitura(5000, SLAVE_ID, label="(CURRENT atual)")
    print()


def teste_2_varredura():
    print("=" * 70)
    print(f"TESTE 2: Varredura de {SCAN_START} até {SCAN_END}, slave = {SLAVE_ID}")
    print("=" * 70)
    sucesso = []
    for addr in range(SCAN_START, SCAN_END + 1):
        r = tentar_leitura(addr, SLAVE_ID)
        if "OK" in r["holding"] or "OK" in r["input"]:
            sucesso.append(addr)
        time.sleep(0.05)  # evita sobrecarregar o barramento
    print()
    print(f"--> Endereços que responderam sem erro: {sucesso}")
    print()
    return sucesso


def teste_3_outros_slaves():
    print("=" * 70)
    print(f"TESTE 3: Testando endereço 5000 em outros slave IDs {OUTROS_SLAVE_IDS}")
    print("=" * 70)
    for sid in OUTROS_SLAVE_IDS:
        tentar_leitura(5000, sid, label="(testando slave)")
        time.sleep(0.05)
    print()


def teste_4_comparar_motor(sucesso):
    print("=" * 70)
    print("TESTE 4: Comparar valor do(s) endereço(s) candidato(s) com motor LIGADO/DESLIGADO")
    print("=" * 70)
    if not sucesso:
        print("Nenhum endereço candidato encontrado no Teste 2 — nada para comparar.")
        print("Considere aumentar a faixa SCAN_START/SCAN_END.")
        print()
        return
    print("Esse teste é manual. Endereços candidatos encontrados:", sucesso)
    print("Ligue e desligue o motor manualmente e rode, para cada candidato:")
    print()
    print("    tentar_leitura(<endereco_candidato>, <slave_id>)")
    print()
    print("Se o valor mudar de forma consistente com o motor ligando/desligando,")
    print("é um forte indício de que esse é o registrador de corrente correto.")
    print()


# ==============================================================================
# EXECUÇÃO
# ==============================================================================

if __name__ == "__main__":
    teste_0_sanity_check()
    teste_1_endereco_atual()
    sucesso = teste_2_varredura()
    teste_3_outros_slaves()
    teste_4_comparar_motor(sucesso)
    print("[OK] Diagnóstico concluído.")