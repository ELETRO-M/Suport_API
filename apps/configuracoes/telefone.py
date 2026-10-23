import re

CODIGO_PAIS = "244"  # Angola


def normalizar_numero(numero: str) -> str:
    """
    Deixa apenas dígitos e garante o código do país (Angola) no início.

    Aceita, por exemplo: "+244 923 456 789", "923456789", "0923456789",
    "00244923456789" e devolve sempre "244923456789".
    """
    numero = re.sub(r"\D", "", str(numero or ""))
    if not numero:
        return ""

    if numero.startswith("00"):
        numero = numero[2:]

    if numero.startswith(CODIGO_PAIS):
        return numero

    if numero.startswith("0"):
        numero = numero.lstrip("0")

    if len(numero) == 9:
        return CODIGO_PAIS + numero

    return numero
