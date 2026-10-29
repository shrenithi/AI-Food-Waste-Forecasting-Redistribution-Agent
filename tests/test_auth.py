def test_valid_login(client, seed_data):
    response = client.post('/login', data={
        'email': 'chef@test.com',
        'password': 'Pass@123'
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b'Welcome back' in response.data

def test_invalid_login(client, seed_data):
    response = client.post('/login', data={
        'email': 'chef@test.com',
        'password': 'WrongPassword'
    }, follow_redirects=True)
    assert b'Invalid email address or password' in response.data

def test_registration_volunteer(client):
    response = client.post('/register', data={
        'role': 'volunteer',
        'name': 'Sam Volunteer',
        'email': 'sam@volunteer.com',
        'phone': '9999999999',
        'password': 'Password123',
        'confirm_password': 'Password123'
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b'Registration successful' in response.data
