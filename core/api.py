import asyncio
import json
import time

from typing import Literal, Any
from curl_cffi.requests import AsyncSession, Response, RequestsError

from models import Account
from .exceptions.base import APIError, SessionRateLimited, ServerError


class PipeNetworkAPI:
    SITE_API_URL = "https://api.pipecdn.app/api"
    EXTENSION_API_URL = "https://pipe-network-backend.pipecanary.workers.dev/api"

    def __init__(self, account: Account):
        self.account_data = account
        self.wallet_data: dict[str, Any] = {}
        self.session = self.setup_session()

    def setup_session(self) -> AsyncSession:
        session = AsyncSession(impersonate="chrome124", verify=False, timeout=30)
        session.headers = {
            'accept': '*/*',
            'accept-language': 'en-US,en;q=0.9',
            'content-type': 'application/json',
            'origin': 'https://pipecdn.app',
            'priority': 'u=1, i',
            'referer': 'https://pipecdn.app/',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
        }

        if self.account_data.proxy:
            session.proxies = {
                "http": self.account_data.proxy.as_url,
                "https": self.account_data.proxy.as_url,
            }

        return session

    async def clear_request(self, url: str, headers: dict = None, cookies: dict = None) -> Response:
        session = AsyncSession(impersonate="chrome124", verify=False, timeout=15)
        session.proxies = self.session.proxies

        response = await session.get(url, headers=headers, cookies=cookies)
        return response

    async def send_request(
            self,
            request_type: Literal["POST", "GET", "OPTIONS"] = "POST",
            api_type: Literal["SITE", "EXTENSION"] = "SITE",
            method: str = None,
            json_data: dict = None,
            params: dict = None,
            url: str = None,
            headers: dict = None,
            cookies: dict = None,
            verify: bool = True,
            max_retries: int = 3,
            retry_delay: float = 3.0,
    ):
        def verify_response(response_data: dict | list) -> dict | list:
            if isinstance(response_data, dict):

                if response_data.get("message") == "Heartbeat recorded successfully.":
                    return response_data

                if "status" in str(response_data) and not response_data.get("status"):
                    raise APIError(f"API returned an error: {response_data}", response_data)
                if "success" in str(response_data) and not response_data.get("success"):
                    raise APIError(f"API returned an error: {response_data}", response_data)
                if "error" in str(response_data) and response_data.get("error"):
                    raise APIError(f"API returned an error: {response_data}", response_data)

            return response_data

        url = url or f"{self.SITE_API_URL if api_type == 'SITE' else self.EXTENSION_API_URL}{method}"
        headers = headers or self.session.headers

        for attempt in range(max_retries):
            try:
                if request_type == "POST":
                    response = await self.session.post(url, json=json_data, params=params, headers=headers, cookies=cookies)
                elif request_type == "OPTIONS":
                    response = await self.session.options(url, headers=headers, cookies=cookies)
                else:
                    response = await self.session.get(url, params=params, headers=headers, cookies=cookies)

                if verify:
                    if response.status_code == 403:
                        raise SessionRateLimited("Session is rate limited")
                    if response.status_code in (500, 502, 503, 504):
                        raise ServerError(f"Server error - {response.status_code}")

                    try:
                        return verify_response(response.json())
                    except json.JSONDecodeError:
                        return response.text

                return response.text

            except (ServerError, APIError, SessionRateLimited):
                if attempt == max_retries - 1:
                    raise
                await asyncio.sleep(retry_delay)

            except Exception as error:
                if attempt == max_retries - 1:
                    raise ServerError(f"Failed to send request after {max_retries} attempts: {error}")
                await asyncio.sleep(retry_delay)

        raise ServerError(f"Failed to send request after {max_retries} attempts")


    async def register(self, referral_code: str) -> str:
        json_data = {
            'email': self.account_data.email,
            'password': self.account_data.password,
            'referralCode': referral_code,
        }

        response = await self.send_request(method="/signup", json_data=json_data, verify=False)
        if response == "User registered successfully":
            return response

        raise APIError(f"Failed to register account: {response}")

    async def login(self) -> dict[str, Any]:
        json_data = {
            'email': self.account_data.email,
            'password': self.account_data.password,
        }

        response = await self.send_request(method="/login", json_data=json_data)
        if "token" in response:
            self.session.headers.update({"authorization": f"Bearer {response['token']}"})
            return response

        raise APIError(f"Failed to login account: {response}")


    async def login_in_extension(self):
        json_data = {
            'email': self.account_data.email,
            'password': self.account_data.password,
        }

        response = await self.send_request(method="/login", api_type="EXTENSION", json_data=json_data)
        if "token" in response:
            self.session.headers.update({"authorization": f"Bearer {response['token']}"})
            return response

        raise APIError(f"Failed to login account via extension: {response}")


    async def points(self) -> dict[str, Any]:
        response = await self.send_request(method="/points", request_type="GET")
        return response

    async def points_in_extension(self) -> dict[str, Any]:
        response = await self.send_request(method="/points", request_type="GET", api_type="EXTENSION")
        return response

    async def nodes(self) -> Response:
        headers = {
            'accept': '*/*',
            'accept-language': 'en-US,en;q=0.9',
            'priority': 'u=1, i',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'none',
            'user-agent': self.session.headers['user-agent'],
        }

        return await self.clear_request("https://api.pipecdn.app/api/nodes", headers=headers)

    async def test_ping(self, node_id: str, ip: str, latency: str, status: str = "online") -> dict[str, Any]:
        headers = {
            'accept': '*/*',
            'accept-language': 'en-US,en;q=0.9',
            'authorization': self.session.headers['authorization'],
            'content-type': 'application/json',
            'origin': 'chrome-extension://gelgmmdfajpefjbiaedgjkpekijhkgbe',
            'priority': 'u=1, i',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'none',
            'user-agent': self.session.headers['user-agent'],
        }

        json_data = {
            'node_id': node_id,
            'ip': ip,
            'latency': int(latency),
            'status': status,
        }

        response = await self.send_request(method="/test", request_type="POST", api_type="SITE", json_data=json_data, headers=headers)
        if "message" in response:
            if response["message"] == "Test result saved":
                return response

        raise APIError(f"Failed to test node: {response}")


    async def heartbeat(self, ip: str, location: str, timestamp: int):
        headers = {
            'accept': '*/*',
            'accept-language': 'en-US,en;q=0.9',
            'authorization': self.session.headers['authorization'],
            'content-type': 'application/json',
            'origin': 'chrome-extension://gelgmmdfajpefjbiaedgjkpekijhkgbe',
            'priority': 'u=1, i',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'none',
            'user-agent': self.session.headers['user-agent'],
        }

        json_data = {
            'ip': ip,
            'location': location,
            'timestamp': timestamp,
        }

        response = await self.send_request(method="/heartbeat", request_type="POST", api_type="SITE", json_data=json_data, headers=headers)
        if "message" in response and response["message"] == "Heartbeat recorded successfully.":
            return response

        raise APIError(f"Failed to send heartbeat: {response}")


    async def get_twitter_bind_params(self) -> dict[str, str]:
        return await self.send_request(method="/twitter-login", request_type="GET", api_type="SITE")

    async def twitter_follow_status(self) -> dict[str, Any]:
        return await self.send_request(method="/follow-status", request_type="GET", api_type="SITE")

    async def generate_referral_link(self) -> str:
        json_data = {
            'email': self.account_data.email,
        }

        response = await self.send_request(method="/generate-referral", request_type="POST", json_data=json_data)
        if "referralLink" in response:
            return response["referralLink"]

        raise APIError(f"Failed to generate referral link: {response}")


    async def bind_twitter(self, state: str, approved_code: str):
        json_data = {
            'code': approved_code,
            'state': state,
        }

        return await self.send_request(method="/twitter/callback", request_type="POST", api_type="EXTENSION", json_data=json_data)

    async def test_node_latency(self, ip: str) -> int:
        try:
            start_time = time.time()
            await self.clear_request(f"http://{ip}")
            latency = int((time.time() - start_time) * 1000)
        except RequestsError:
            latency = -1

        return latency


    async def get_geo_location(self) -> dict[str, str]:
        response = await self.clear_request(url="https://ipapi.co/json/")
        if response.status_code == 200:
            data = response.json()
            return {"ip": data["ip"], "location": f"{data['city']}, {data['region']}, {data['country_name']}"}

        raise APIError(f"Failed to get geo location: {response.text}")


