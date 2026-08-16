def login(payload):
    email = payload.get('email')
    password = payload.get('password')
    if not email or not password:
        raise ValueError('missing field')
    return True
