from core.database import hash_password, verify_password

def test_password_hash():
    hashed = hash_password("Strong-Example-Password!")
    assert verify_password("Strong-Example-Password!", hashed)
    assert not verify_password("wrong", hashed)
