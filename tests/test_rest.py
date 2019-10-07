import json
import os
import sys
import requests
import pytest

# export a API_URL environment varialble to be something like:
# API_URL="https://something.execute-api.us-west-2.amazonaws.com/dev/"
API_URL = os.environ.get("API_URL", None)
AUTH0_URL = os.environ.get(
    "AUTH0_URL", "https://auth-dev.mozilla.auth0.com/oauth/token"
)
CLIENT_ID = os.environ.get("CLIENT_ID", None)
CLIENT_SECRET = os.environ.get("CLIENT_SECRET", None)

if API_URL is None:
    pytest.fail("Missing API_URL environment variable")

if CLIENT_ID is None:
    pytest.fail("Missing CLIENT_ID environment variable")

if CLIENT_SECRET is None:
    pytest.fail("Missing CLIENT_SECRET environment variable")


@pytest.mark.incremental
class TestEnvironment(object):
    def test_api_url_environtment_variable(self):
        assert API_URL is not None

    def test_client_id_environment_variable(self):
        assert CLIENT_ID is not None

    def test_client_secret_environment_variable(self):
        assert CLIENT_SECRET is not None


if not API_URL.endswith("/"):
    API_URL = API_URL + "/"

# get api key:
r = requests.post(
    AUTH0_URL,
    headers={"content-type": "application/json"},
    data=json.dumps(
        {
            "grant_type": "client_credentials",
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "audience": API_URL,
        }
    ),
)
access_token = r.json()["access_token"]


class TestStatus(object):
    def test_api_status(self):
        r = requests.get("{}status".format(API_URL))
        assert r.json()["message"] == "Qapla'!"

    def test_asset_status(self):
        r = requests.get("{}api/v1/asset/status".format(API_URL))
        assert r.json()["message"] == "Qapla'!"

    def test_indicator_status(self):
        r = requests.get("{}api/v1/indicator/status".format(API_URL))
        assert r.json()["message"] == "Qapla'!"

    def test_asset_group_status(self):
        r = requests.get("{}api/v1/asset-group/status".format(API_URL))
        assert r.json()["message"] == "Qapla'!"

    def test_service_status(self):
        r = requests.get(
            "{}api/v1/service/status".format(API_URL),
            headers={"Authorization": "Bearer {}".format(access_token)},
        )
        assert r.json()["message"] == "Qapla'!"


class TestMissing(object):
    def test_nonexistent_asset(self):
        r = requests.get(
            "{}api/v1/assets/hereisathingthatshouldnotexist".format(API_URL),
            headers={"Authorization": "Bearer {}".format(access_token)},
        )
        result = json.loads(r.json())
        assert len(result) == 0

    def test_nonexistent_indicator(self):
        r = requests.get(
            "{}api/v1/indicators/hereisathingthatshouldnotexist".format(API_URL),
            headers={"Authorization": "Bearer {}".format(access_token)},
        )
        result = json.loads(r.json())
        assert len(result) == 0

    def test_nonexistent_asset_group(self):
        r = requests.get(
            "{}api/v1/asset-group/hereisathingthatshouldnotexist".format(API_URL),
            headers={"Authorization": "Bearer {}".format(access_token)},
        )
        result = json.loads(r.json())
        assert len(result) == 0

@pytest.mark.incremental
class TestAsset(object):
    def __init__(self):
        self.asset_id = None

    def test_adding_asset_through_scanapi_indicator(self):
        r = requests.post(
            "{}api/v1/indicator".format(API_URL),
            headers={"Authorization": "Bearer {}".format(access_token)},
            data=json.dumps(
                {
                    "asset_identifier": "pytest.testing.com",
                    "asset_type": "website",
                    "zone": "pytest",
                    "description": "scanapi vulnerability result",
                    "event_source_name": "scanapi",
                    "likelihood_indicator": "high",
                    "details": {
                        "coverage": True,
                        "maximum": 0,
                        "high": 1,
                        "medium": 6,
                        "low": 8,
                    },
                }
            ),
        )

        print(r.json())
        result = json.loads(r.json())
        self.asset_id = result["asset_id"]
        print("Test created asset_id: {}".format(self.asset_id))
        assert self.asset_id is not None

    def test_adding_ZAP_scan_indicator(self):
        r = requests.post(
            "{}api/v1/indicator".format(API_URL),
            headers={"Authorization": "Bearer {}".format(access_token)},
            data=json.dumps(
                {
                    "asset_type": "website",
                    "asset_identifier": "pytest.testing.com",
                    "zone": "pytest",
                    "description": "ZAP DAST scan",
                    "event_source_name": "ZAP DAST scan",
                    "likelihood_indicator": "medium",
                    "details": {
                        "findings": [
                            {
                                "name": "Cookie No HttpOnly Flag",
                                "site": "pytest.testing.com",
                                "likelihood_indicator": "low",
                            },
                            {
                                "name": "Cross-Domain Javascript Source File Inclusion",
                                "site": "pytest.testing.com",
                                "likelihood_indicator": "low",
                            },
                            {
                                "name": "CSP scanner: script-src unsafe-inline",
                                "site": "pytest.testing.com",
                                "likelihood_indicator": "medium",
                            },
                        ]
                    },
                }
            ),
        )
        print(r.json())
        result = json.loads(r.json())
        assert self.asset_id == result["asset_id"]

    def test_adding_observatory_indicator(self):
        r = requests.post(
            "{}api/v1/indicator".format(API_URL),
            headers={"Authorization": "Bearer {}".format(access_token)},
            data=json.dumps(
                {
                    "asset_type": "website",
                    "asset_identifier": "pytest.testing.com",
                    "zone": "pytest",
                    "description": "Mozilla Observatory scan",
                    "event_source_name": "Mozilla Observatory",
                    "likelihood_indicator": "medium",
                    "details": {
                        "grade": "F",
                        "tests": [
                            {"name": "Content security policy", "pass": False},
                            {"name": "Cookies", "pass": True},
                            {"name": "HTTP Public Key Pinning", "pass": True},
                            {"name": "X-Frame-Options", "pass": False},
                            {"name": "Cross-origin Resource Sharing", "pass": True},
                        ],
                    },
                }
            ),
        )
        print(r.json())
        result = json.loads(r.json())
        assert self.asset_id == result["asset_id"]

    def test_adding_observatory_api_indicator(self):
        # api endpoints can have troublesome data types (grade: null, pass;null)
        # Fields with None as the value aren't stored in the dynamo table:
        # https://github.com/NerdWalletOSS/dynamorm/issues/57
        # so the schema needs to be watching to add missing fields back in as null in json, None in python
        r = requests.post(
            "{}api/v1/indicator".format(API_URL),
            headers={"Authorization": "Bearer {}".format(access_token)},
            data=json.dumps(
                {
                    "asset_type": "website",
                    "asset_identifier": "pytest.testing.com",
                    "zone": "pytest",
                    "description": "Mozilla Observatory scan",
                    "event_source_name": "Mozilla Observatory",
                    "likelihood_indicator": "medium",
                    "details": {
                        "grade": None,
                        "tests": [
                            {"name": "Content security policy", "pass": None},
                            {"name": "Cookies", "pass": True},
                            {"name": "HTTP Public Key Pinning", "pass": True},
                            {"name": "X-Frame-Options", "pass": None},
                            {"name": "Cross-origin Resource Sharing", "pass": True},
                        ],
                    },
                }
            ),
        )
        print(r.json())
        result = json.loads(r.json())
        assert self.asset_id == result["asset_id"]
        assert result["details"]["grade"] is None

    def test_retrieving_asset(self):
        assert self.asset_id is not None
        print("retrieving asset with id: {}".format(self.asset_id))
        r = requests.get(
            "{}api/v1/asset/{}".format(API_URL, self.asset_id),
            headers={"Authorization": "Bearer {}".format(access_token)},
        )
        result = json.loads(r.json())
        print(r.json())
        assert result[0]["id"] == self.asset_id

    def test_removing_asset(self):
        assert self.asset_id is not None
        r = requests.delete(
            "{}api/v1/asset/{}".format(API_URL, self.asset_id),
            headers={"Authorization": "Bearer {}".format(access_token)},
        )
        print(r.json())
        assert len(r.json()) > 1
