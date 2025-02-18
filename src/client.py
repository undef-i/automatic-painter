import requests
from typing import Dict, Any

class PainterClient:
    def __init__(self, base_url: str):
        self.base_url = base_url

    def _make_request(self, endpoint: str, data: Dict[str, Any]) -> Dict[str, Any]:
        url = f"{self.base_url}{endpoint}"
        headers = {"Cookie": "gp-necessary=true; gp-analytical=true; gitpod-marketing-website-visited=true; gp-targeting=true; ajs_anonymous_id=80fd0863-6e49-41ca-9f89-e5362b18b35c; gitpod_hashed_user_id=68ffda2650694ad7f528be1da829ccbf; gitpod-user=true; _gitpod_io_ws_ea815c66-9f35-4a22-ac3b-6c3b9c36bb98_owner_=.aEj8syisqn1J94uiP-r0pj8djXLgMcV; _gitpod_io_ws_8470d824-86e8-4c5c-bf8b-b20de4e7b806_owner_=DcFTMIeXUTvuhfQXiwoiSQii84zk9H7n; _gitpod_io_ws_7f0e3896-6d56-41b9-9d0a-7581194d7c06_owner_=LqXZ453ZkU2iMeqfck3SNk5YiRYYWmjD"}
        try:
            response = requests.post(url, data=data, headers=headers)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            raise RuntimeError(f"HTTP request failed: {e}")

    def pixel_get(self, x: int, y: int) -> Dict[str, int]:
        endpoint = "/pixel/get"
        data = {"x": x, "y": y}
        return self._make_request(endpoint, data)

    def pixel_set(self, x: int, y: int, token: str) -> Dict[str, str]:
        endpoint = "/pixel/set"
        data = {"x": x, "y": y, "token": token}
        return self._make_request(endpoint, data)

    def job_get(self) -> Dict[str, str]:
        endpoint = "/job/get"
        return self._make_request(endpoint, {})

    def job_submit(self, r: str, g: str, b: str, jobid: str) -> Dict[str, str]:
        endpoint = "/job/submit"
        data = {"r": r, "g": g, "b": b, "jobid": jobid}
        return self._make_request(endpoint, data) 