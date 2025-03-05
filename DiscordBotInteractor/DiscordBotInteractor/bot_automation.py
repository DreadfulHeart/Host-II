import os
import logging
import aiohttp
from typing import Optional, Dict, Any

logger = logging.getLogger('BotAutomation.APIClient')

class UnbelievaBoatAPI:
    BASE_URL = "https://unbelievaboat.com/api"
    API_VERSION = "v1"

    def __init__(self):
        self.api_token = os.getenv('UNBELIEVABOAT_API_TOKEN')
        if not self.api_token:
            raise ValueError("UNBELIEVABOAT_API_TOKEN environment variable is required")

        self.headers = {
            "Authorization": self.api_token,
            "Accept": "application/json"
        }

    async def remove_money(self, guild_id: str, user_id: str, amount: int) -> Optional[Dict[str, Any]]:
        """
        Remove money from a user's balance using UnbelievaBoat API

        Args:
            guild_id (str): Discord guild ID
            user_id (str): Discord user ID
            amount (int): Amount to remove (positive integer)

        Returns:
            Optional[Dict[str, Any]]: API response data or None if failed
        """
        try:
            endpoint = f"{self.BASE_URL}/{self.API_VERSION}/guilds/{guild_id}/users/{user_id}"

            logger.info(f"Making API request to endpoint: {endpoint}")
            logger.info(f"Attempting to remove {amount} from user {user_id} in guild {guild_id}")

            async with aiohttp.ClientSession(headers=self.headers) as session:
                async with session.patch(endpoint, json={"cash": -abs(amount)}) as response:
                    if response.status == 200:
                        data = await response.json()
                        logger.info(f"Successfully removed {amount} from user {user_id}")
                        logger.info(f"New balance: {data.get('cash', 'unknown')}")
                        return data
                    elif response.status == 429:  # Rate limit
                        retry_after = response.headers.get('Retry-After', 60)
                        logger.warning(f"Rate limited. Retry after {retry_after} seconds")
                        return None
                    elif response.status == 401:
                        logger.error("Unauthorized. Please check your API token")
                        return None
                    elif response.status == 403:
                        logger.error("Forbidden. Bot lacks necessary permissions")
                        return None
                    else:
                        error_data = await response.text()
                        logger.error(f"API request failed with status {response.status}: {error_data}")
                        return None

        except aiohttp.ClientError as e:
            logger.error(f"Network error in remove_money API call: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error in remove_money API call: {str(e)}")
            return None
            
    async def add_money(self, guild_id: str, user_id: str, amount: int) -> Optional[Dict[str, Any]]:
        """
        Add money to a user's balance using UnbelievaBoat API

        Args:
            guild_id (str): Discord guild ID
            user_id (str): Discord user ID
            amount (int): Amount to add (positive integer)

        Returns:
            Optional[Dict[str, Any]]: API response data or None if failed
        """
        try:
            endpoint = f"{self.BASE_URL}/{self.API_VERSION}/guilds/{guild_id}/users/{user_id}"

            logger.info(f"Making API request to endpoint: {endpoint}")
            logger.info(f"Attempting to add {amount} to user {user_id} in guild {guild_id}")

            async with aiohttp.ClientSession(headers=self.headers) as session:
                async with session.patch(endpoint, json={"cash": abs(amount)}) as response:
                    if response.status == 200:
                        data = await response.json()
                        logger.info(f"Successfully added {amount} to user {user_id}")
                        logger.info(f"New balance: {data.get('cash', 'unknown')}")
                        return data
                    elif response.status == 429:  # Rate limit
                        retry_after = response.headers.get('Retry-After', 60)
                        logger.warning(f"Rate limited. Retry after {retry_after} seconds")
                        return None
                    elif response.status == 401:
                        logger.error("Unauthorized. Please check your API token")
                        return None
                    elif response.status == 403:
                        logger.error("Forbidden. Bot lacks necessary permissions")
                        return None
                    else:
                        error_data = await response.text()
                        logger.error(f"API request failed with status {response.status}: {error_data}")
                        return None

        except aiohttp.ClientError as e:
            logger.error(f"Network error in add_money API call: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error in add_money API call: {str(e)}")
            return None
            
    async def get_balance(self, guild_id: str, user_id: str) -> Optional[int]:
        """
        Get a user's balance using UnbelievaBoat API

        Args:
            guild_id (str): Discord guild ID
            user_id (str): Discord user ID

        Returns:
            Optional[int]: User's cash balance or None if failed
        """
        try:
            endpoint = f"{self.BASE_URL}/{self.API_VERSION}/guilds/{guild_id}/users/{user_id}"

            logger.info(f"Making API request to endpoint: {endpoint}")
            logger.info(f"Getting balance for user {user_id} in guild {guild_id}")

            async with aiohttp.ClientSession(headers=self.headers) as session:
                async with session.get(endpoint) as response:
                    if response.status == 200:
                        data = await response.json()
                        balance = data.get('cash', 0)
                        logger.info(f"Successfully got balance for user {user_id}: {balance}")
                        return balance
                    elif response.status == 429:  # Rate limit
                        retry_after = response.headers.get('Retry-After', 60)
                        logger.warning(f"Rate limited. Retry after {retry_after} seconds")
                        return None
                    elif response.status == 401:
                        logger.error("Unauthorized. Please check your API token")
                        return None
                    elif response.status == 403:
                        logger.error("Forbidden. Bot lacks necessary permissions")
                        return None
                    else:
                        error_data = await response.text()
                        logger.error(f"API request failed with status {response.status}: {error_data}")
                        return None

        except aiohttp.ClientError as e:
            logger.error(f"Network error in get_balance API call: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error in get_balance API call: {str(e)}")
            return None
