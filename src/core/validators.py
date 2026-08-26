"""
Fonctions utilitaires de validation et normalisation réutilisables
à travers tous les modules de l'application.
"""

def uppercase_string(value: str) -> str:
    """Normalise une chaîne en majuscules."""
    return value.upper()

def prevent_none_value(value, field_name: str):
    if value is None:
        raise ValueError(f"Le champ '{field_name}' ne peut pas être null")
    return value