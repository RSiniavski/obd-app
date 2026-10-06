import resource.users as users
import resource.endpoints.users as e_users

def api_request(method, endpoint, *args, **kwargs):
    return api_client.method(endpoint, payload)

def test_create_user(api_client):
    for i in users:
        assert response.api_request(method, e_users, users)

    assert response.status_code == 201