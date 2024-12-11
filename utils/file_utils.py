import asyncio
import aiofiles

from pathlib import Path
from models import ModuleType, OperationResult, StatisticData
from aiocsv import AsyncWriter



class FileOperations:
    def __init__(self, base_path: str = "./results"):
        self.base_path = Path(base_path)
        self.lock = asyncio.Lock()
        self.module_paths: dict[ModuleType, dict[str, Path]] = {
            "register": {
                "success": self.base_path / "registration_success.txt",
                "failed": self.base_path / "registration_failed.txt",
            },
            "bind_twitter": {
                "success": self.base_path / "bind_twitter_success.txt",
                "failed": self.base_path / "bind_twitter_failed.txt",
            },
            "stats": {
                "base": self.base_path / "accounts_stats.csv",
            },
        }

    async def setup_files(self):
        self.base_path.mkdir(exist_ok=True)
        for module_paths in self.module_paths.values():
            for path in module_paths.values():
                path.touch(exist_ok=True)


        async with aiofiles.open(self.module_paths["stats"]["base"], "w") as f:
            writer = AsyncWriter(f)
            await writer.writerow(
                [
                    "Email",
                    "Points",
                    "Referral Url",
                ]
            )

    async def export_result(self, result: OperationResult, module: ModuleType):
        if module not in self.module_paths:
            raise ValueError(f"Unknown module: {module}")

        file_path = self.module_paths[module][
            "success" if result["status"] else "failed"
        ]
        async with self.lock:
            try:
                async with aiofiles.open(file_path, "a") as file:
                    await file.write(f"{result['identifier']}:{result['data']}\n")
            except IOError as e:
                print(f"Error writing to file: {e}")


    async def export_stats(self, data: StatisticData):
        file_path = self.module_paths["stats"]["base"]
        async with self.lock:
            try:
                async with aiofiles.open(file_path, mode="a", newline="") as f:
                    writer = AsyncWriter(f)

                    if not data["status"]:
                        await writer.writerow(
                            [
                                data["identifier"],
                                "N/A",
                                "N/A",
                            ]
                        )

                    await writer.writerow(
                        [
                            data["identifier"],
                            data["points"],
                            data["referral_url"],
                        ]
                    )

            except IOError as e:
                print(f"Error writing to file: {e}")
