import app as app_module


def test_home_serves_the_page():
    response = app_module.app.test_client().get("/")
    assert response.status_code == 200
    assert "text/html" in response.content_type
    assert b"StudyMate" in response.data


def test_oversized_request_is_rejected():
    response = app_module.app.test_client().post(
        "/login", data=b"x" * (2 * 1024 * 1024), content_type="application/json"
    )
    assert response.status_code == 413