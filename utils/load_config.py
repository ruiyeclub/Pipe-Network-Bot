import os
from itertools import cycle
from pathlib import Path
from typing import Dict, List, Optional, Union, Literal

import yaml
from loguru import logger
from better_proxy import Proxy

from models import Account, Config


class ConfigurationError(Exception):
    """Base exception for configuration-related errors"""
    pass


class ConfigLoader:
    REQUIRED_PARAMS = frozenset({
        "threads",
        "delay_before_start",
        "referral_codes",
        "keepalive_interval"
    })

    def __init__(self, base_path: Union[str, Path] = None):
        self.base_path = Path(base_path or os.getcwd())
        self.config_path = self.base_path / "config"
        self.data_path = self.config_path / "data"
        self.settings_path = self.config_path / "settings.yaml"

    @staticmethod
    def _read_file(file_path: Path, allow_empty: bool = False) -> List[str]:
        if not file_path.exists():
            raise ConfigurationError(f"File not found: {file_path}")

        content = file_path.read_text(encoding='utf-8').strip()

        if not allow_empty and not content:
            raise ConfigurationError(f"File is empty: {file_path}")

        return [line.strip() for line in content.splitlines() if line.strip()]

    def _load_yaml(self) -> Dict:
        try:
            config = yaml.safe_load(self.settings_path.read_text(encoding='utf-8'))
            missing_fields = self.REQUIRED_PARAMS - set(config.keys())

            if missing_fields:
                raise ConfigurationError(
                    f"Missing required fields: {', '.join(missing_fields)}"
                )
            return config

        except yaml.YAMLError as e:
            raise ConfigurationError(f"Invalid YAML format: {e}")

    def _parse_proxies(self) -> Optional[List[Proxy]]:
        try:
            proxy_lines = self._read_file(self.data_path / "proxies.txt", allow_empty=True)
            if not proxy_lines:
                raise ConfigurationError("No proxies found")

            return [Proxy.from_str(line) for line in proxy_lines] if proxy_lines else None
        except Exception as e:
            raise ConfigurationError(f"Failed to parse proxies: {e}")

    def _parse_accounts(self, filename: str, mode: Literal["farm", "register", "bind_twitter"], proxies: Optional[List[Proxy]] = None) -> List[Account]:
        proxy_cycle = cycle(proxies) if proxies else None
        accounts = []

        try:
            for line in self._read_file(self.data_path / filename, allow_empty=True):
                try:
                    if mode in ("register", "farm"):
                        email, password = line.split(':', 1)
                        accounts.append(Account(
                            email=email.strip(),
                            password=password.strip(),
                            proxy=next(proxy_cycle) if proxy_cycle else None
                        ))

                    elif mode == "bind_twitter":
                        email, password, twitter_token = line.split(':', 2)
                        accounts.append(Account(
                            email=email.strip(),
                            password=password.strip(),
                            twitter_token=twitter_token.strip(),
                            proxy=next(proxy_cycle) if proxy_cycle else None
                        ))

                except ValueError:
                    logger.warning(f"Skipping invalid account format: {line}")
                    continue

        except Exception as e:
            logger.error(f"Error processing {filename}: {e}")

        return accounts


    def load(self) -> Config:
        try:
            params = self._load_yaml()
            proxies = self._parse_proxies()

            reg_accounts = self._parse_accounts("register.txt", "register", proxies)
            farm_accounts = self._parse_accounts("farm.txt", "farm", proxies)

            if not (reg_accounts or farm_accounts):
                raise ConfigurationError("No valid accounts found")

            return Config(
                **params,
                accounts_to_farm=farm_accounts,
                accounts_to_register=reg_accounts,
            )

        except Exception as e:
            logger.error(f"Configuration loading failed: {e}")
            raise SystemExit(1)


# Usage
def load_config() -> Config:
    return ConfigLoader().load()
