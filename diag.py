import main

inv = main._get_connection()

if inv is None:
    print("Erro: sem conexão")
    exit()

print("===== LEITURA ENDEREÇO 1000 =====")

try:
    valor = inv.read(main.VOLTAGE)

    print("Valor:")
    print(valor)

    print("Tipo:")
    print(type(valor))

    print("Quantidade:")
    print(len(valor))

except Exception as e:
    print("Erro:")
    print(e)