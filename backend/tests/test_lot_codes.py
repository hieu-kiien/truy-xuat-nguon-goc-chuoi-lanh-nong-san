from app.core.lot_codes import LOT_CODE_ALPHABET, LOT_CODE_LENGTH, generate_lot_code


def test_lot_codes_are_eight_characters_without_ambiguous_symbols():
    codes = [generate_lot_code() for _ in range(10_000)]

    assert LOT_CODE_LENGTH == 8
    assert len(set(codes)) == 10_000
    assert all(len(code) == LOT_CODE_LENGTH for code in codes)
    assert all(set(code) <= set(LOT_CODE_ALPHABET) for code in codes)
    assert not any(symbol in code for code in codes for symbol in "0O1IL")
