from nickel import Address, VariableType, NumberFormat
import main

inv = main._get_connection()

for tipo in [VariableType.REGISTER_RO, VariableType.REGISTER_RW]:
    print("\nTIPO:", tipo)

    for addr in range(4950, 5050):
        teste = Address(
            addr,
            1,
            tipo,
            NumberFormat.INT16,
            "teste"
        )

        try:
            r = inv.read(teste)
            print("RESPONDE:", addr, r)

        except:
            pass