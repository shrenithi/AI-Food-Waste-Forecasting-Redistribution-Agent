def test_unauthenticated_access_redirects(client):
    res = client.get('/restaurant/dashboard')
    assert res.status_code == 302
    assert '/login' in res.headers['Location']

def test_restaurant_accessing_admin_forbidden(client, seed_data):
    # Log in as restaurant
    client.post('/login', data={'email': 'chef@test.com', 'password': 'Pass@123'})
    res = client.get('/admin/dashboard', follow_redirects=True)
    assert b'You do not have permission to access that page' in res.data
