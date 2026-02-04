import random
import string


def generate_temporary_password() -> str:
    """
    Genera un string aleatorio de 10 caracteres:
    - 6 caracteres son letras (mayúsculas o minúsculas)
    - 4 caracteres son números y/o símbolos (mínimo 1 número y 1 símbolo)

    Returns:
        str: String aleatorio de 10 caracteres
    """

    letters = string.ascii_letters  # a-z, A-Z
    digits = string.digits  # 0-9
    symbols = "!@#$%&*+-=?_"  # Símbolos permitidos

    random_letters = random.choices(letters, k=6)

    required_chars = [random.choice(digits), random.choice(symbols)]

    remaining_chars = random.choices(digits + symbols, k=2)

    special_chars = required_chars + remaining_chars

    all_chars = random_letters + special_chars

    random.shuffle(all_chars)

    return "".join(all_chars)
