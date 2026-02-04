from enum import Enum


class RoleType(str, Enum):
    admin = "admin"
    regular = "regular"


class EmailType(str, Enum):
    create_user = "create_user"
    reset_password = "reset_password"


class RoadDirection(str, Enum):
    ascendente = "ascendente"
    descendente = "descendente"
    bidireccional = "bidireccional"


class AssetStatus(str, Enum):
    nuevo = "nuevo"
    existente = "existente"
    retirado = "retirado"


class BarcodePosition(str, Enum):
    no_aplica = "no_aplica"
    lado_izquierdo = "lado_izquierdo"
    lado_derecho = "lado_derecho"
    mediana_altura = "mediana_altura"
    lado_izquierdo_y_lado_derecho = "lado_izquierdo_y_lado_derecho"
    lado_derecho_y_mediana_altura = "lado_derecho_y_mediana_altura"
    lado_izquierdo_y_mediana_altura = "lado_izquierdo_y_mediana_altura"
    cada_200_metros = "cada_200_metros"
    a_nivel_de_piso = "a_nivel_de_piso"
