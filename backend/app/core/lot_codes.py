import secrets

LOT_CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
LOT_CODE_LENGTH = 12


def generate_lot_code() -> str:
    """Generate a short code without easily confused characters."""
    return "".join(secrets.choice(LOT_CODE_ALPHABET) for _ in range(LOT_CODE_LENGTH))
