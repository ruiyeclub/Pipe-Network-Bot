import random
import time
from datetime import datetime, timedelta
from typing import Any, Optional, Dict

import pytz
from loguru import logger
from loader import config
from models import Account, OperationResult, StatisticData
from utils import error_handler

from .api import PipeNetworkAPI
from database import Accounts


class Bot(PipeNetworkAPI):
    def __init__(self, account: Account):
        super().__init__(account)
        self.account_data = account


    @error_handler(return_operation_result=True)
    async def process_registration(self) -> OperationResult:
        referral_code = random.choice(config.referral_codes)
        await self.register(referral_code=referral_code)

        logger.success(f"账户: {self.account_data.email} | 注册功能")
        return OperationResult(
            identifier=self.account_data.email,
            data=self.account_data.password,
            status=True
        )

    @error_handler(return_operation_result=False)
    async def process_farming_actions(self) -> None:
        if not await self._prepare_account():
            return

        node_data = await self.get_node_data()
        if not node_data:
            return

        await self._process_node(node_data)
        await self._update_sleep_time()
        await self._process_heartbeat()

        if config.show_points_stats:
            response = await self.points_in_extension()
            logger.info(f"账户: {self.account_data.email} | 总积分: {response['points']}")


    @error_handler(return_operation_result=True)
    async def process_export_stats(self) -> StatisticData:
        if not await self._prepare_account(verify_sleep=False):
            return StatisticData(
                identifier=self.account_data.email,
                points=0,
                referral_url="",
                status=False
            )

        logger.info(f"账户: {self.account_data.email} | 导出统计中...")
        points = (await self.points_in_extension())["points"]

        referral_url = await self.generate_referral_link()
        logger.success(f"账户: {self.account_data.email} | 统计数据已导出")

        return StatisticData(
            identifier=self.account_data.email,
            points=int(points),
            referral_url=referral_url,
            status=True
        )



    @error_handler(return_operation_result=False)
    async def process_twitter_status(self) -> bool:
        follow_status = await self.twitter_follow_status()
        if follow_status.get("status") == "User already verified":
            logger.success(f"账户: {self.account_data.email} | Twitter 用户名: {follow_status['user']['username']} | 奖励: {follow_status['user']['reward']} points")
            return True

        logger.error(f"账户: {self.account_data.email} | Twitter 关注状态: {follow_status}")
        return False

    async def _prepare_account(self, verify_sleep: bool = True) -> bool:
        account = await Accounts.get_account(email=self.account_data.email)
        if not account:
            return await self.login_new_account()

        if verify_sleep:
            if await self.handle_sleep(account.sleep_until):
                return False

        self.session.headers = account.headers
        return True

    @error_handler(return_operation_result=False)
    async def _process_node(self, node_data: Dict[str, Any]) -> None:
        node_id = str(node_data["node_id"])
        node_ip = str(node_data["ip"])

        node_latency = await self.test_node_latency(node_ip)
        if node_latency is None:
            logger.error(f"账户: {self.account_data.email} | 链接测试节点失败")
            return

        response = await self.test_ping(
            node_id=node_id,
            ip=node_ip,
            latency=str(node_latency)
        )

        logger.success(
            f"账户: {self.account_data.email} | "
            f"测试节点 | 获得积分: {response['points']}"
        )


    @error_handler(return_operation_result=False)
    async def _process_heartbeat(self) -> None:
        account = await Accounts.get_account(email=self.account_data.email)
        if await self.handle_heartbeat(account.next_heartbeat_in):
            return

        logger.info(f"账户: {self.account_data.email} | 发送心跳中...")
        geo_location = await self.get_geo_location()

        await self.heartbeat(ip=geo_location["ip"], location=geo_location["location"], timestamp=int(time.time() * 1000))
        await self._update_sleep_time(heartbeat=True)

        logger.success(f"账户: {self.account_data.email} | 心跳已发送")

    async def _update_sleep_time(self, heartbeat: bool = False) -> None:
        if heartbeat:
            sleep_until = self.get_next_heartbeat_time()
            await Accounts.set_next_heartbeat_in(self.account_data.email, sleep_until)
            logger.debug(
                f"账户: {self.account_data.email} | "
                f"下一次心跳时间更新为 {sleep_until}"
            )

        else:
            sleep_until = self.get_sleep_until()
            await Accounts.set_sleep_until(self.account_data.email, sleep_until)
            logger.debug(
                f"账户: {self.account_data.email} | "
                f"休眠时间已更新为 {sleep_until}"
            )

    @error_handler(return_operation_result=False)
    async def get_node_data(self) -> Optional[Dict[str, Any]]:
        response = await self.nodes()
        if not response or not response.text:
            return None

        node_data = response.json()
        if not node_data:
            return None

        node = node_data[0]
        if not self._validate_node_data(node):
            return None

        return node

    @staticmethod
    def _validate_node_data(node: Dict[str, Any]) -> bool:
        required_fields = {'node_id', 'ip'}
        return all(field in node for field in required_fields)

    @error_handler(return_operation_result=False)
    async def login_new_account(self) -> bool:
        logger.info(f"账户: {self.account_data.email} | 通过扩展程序登录...")
        await self.login_in_extension()

        await Accounts.create_account(
            email=self.account_data.email,
            headers=self.session.headers
        )
        logger.success(f"账户: {self.account_data.email} | 已登录 | Session 已保存")
        return True

    @staticmethod
    def get_sleep_until() -> datetime:
        duration = timedelta(seconds=config.keepalive_interval)
        return datetime.now(pytz.UTC) + duration

    @staticmethod
    def get_next_heartbeat_time() -> datetime:
        duration = timedelta(hours=config.heartbeat_interval)
        return datetime.now(pytz.UTC) + duration

    async def handle_sleep(self, sleep_until: datetime) -> bool:
        if not sleep_until:
            return False

        current_time = datetime.now(pytz.UTC)
        sleep_until = sleep_until.replace(tzinfo=pytz.UTC)

        if sleep_until > current_time:
            sleep_duration = (sleep_until - current_time).total_seconds()
            logger.debug(
                f"账户: {self.account_data.email} | "
                f"下一个节点测试 {sleep_until} "
                f"(时间: {sleep_duration:.2f} 秒)"
            )
            return True

        return False


    async def handle_heartbeat(self, next_heartbeat_in: datetime) -> bool:
        if not next_heartbeat_in:
            return False

        current_time = datetime.now(pytz.UTC)
        next_heartbeat_in = next_heartbeat_in.replace(tzinfo=pytz.UTC)

        if next_heartbeat_in > current_time:
            heartbeat_duration = (next_heartbeat_in - current_time).total_seconds() / 3600
            logger.debug(
                f"账户: {self.account_data.email} | "
                f"下一次心跳 {next_heartbeat_in} "
                f"(时间: {heartbeat_duration:.2f} 小时)"
            )
            return True

        return False
