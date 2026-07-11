import asyncio
import aiohttp
from pathlib import Path
from typing import Dict, List
import logging

logger = logging.getLogger(__name__)

VOICES_DIR = Path(__file__).parent
CONFIG_FILE = VOICES_DIR / "voice_config.json"


async def download_file(session: aiohttp.ClientSession, url: str, dest: Path) -> bool:
    try:
        dest.parent.mkdir(parents=True, exist_ok=True)
        async with session.get(url) as response:
            if response.status == 200:
                content = await response.read()
                dest.write_bytes(content)
                logger.info(f"Downloaded: {dest.name}")
                return True
            else:
                logger.error(f"Failed to download {url}: HTTP {response.status}")
                return False
    except Exception as e:
        logger.error(f"Error downloading {url}: {e}")
        return False


async def download_all_voices() -> Dict[str, bool]:
    import json
    
    if not CONFIG_FILE.exists():
        logger.error(f"Voice config not found: {CONFIG_FILE}")
        return {}
    
    with open(CONFIG_FILE) as f:
        config = json.load(f)
    
    download_urls = config.get("download_urls", {})
    results = {}
    
    async with aiohttp.ClientSession() as session:
        tasks = []
        for filename, url in download_urls.items():
            dest = VOICES_DIR / filename
            if dest.exists():
                logger.info(f"Already exists: {filename}")
                results[filename] = True
            else:
                tasks.append(download_file(session, url, dest))
        
        if tasks:
            downloaded = await asyncio.gather(*tasks)
            for (filename, _), success in zip(download_urls.items(), downloaded):
                results[filename] = success
    
    return results


def list_downloaded_voices() -> Dict[str, str]:
    import json
    
    if not CONFIG_FILE.exists():
        return {}
    
    with open(CONFIG_FILE) as f:
        config = json.load(f)
    
    voices = config.get("voices", {})
    downloaded = {}
    
    for profile, info in voices.items():
        filename = info["filename"]
        path = VOICES_DIR / filename
        if path.exists():
            downloaded[profile] = filename
    
    return downloaded


def get_voice_path(profile: str) -> Path:
    import json
    
    with open(CONFIG_FILE) as f:
        config = json.load(f)
    
    voices = config.get("voices", {})
    if profile in voices:
        return VOICES_DIR / voices[profile]["filename"]
    
    default_profile = config.get("default", "clear")
    return VOICES_DIR / voices[default_profile]["filename"]


async def ensure_voices_downloaded() -> bool:
    downloaded = list_downloaded_voices()
    config_file = VOICES_DIR / "voice_config.json"
    
    if not config_file.exists():
        return False
    
    import json
    with open(config_file) as f:
        config = json.load(f)
    
    all_profiles = set(config.get("voices", {}).keys())
    missing = all_profiles - set(downloaded.keys())
    
    if missing:
        logger.info(f"Downloading missing voices: {missing}")
        results = await download_all_voices()
        return all(results.values())
    
    return True


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(download_all_voices())