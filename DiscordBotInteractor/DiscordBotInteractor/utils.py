import logging
import asyncio
import random
from datetime import datetime
import discord
from discord import app_commands
import sys
import traceback
import os

def setup_logging():
    """Setup logging configuration"""
    # Create logs directory if it doesn't exist
    log_dir = 'logs'
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    # Generate log filename with timestamp
    log_file = os.path.join(log_dir, f'bot_automation_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log')
    
    # Configure root logger
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            # Console handler with color formatting
            logging.StreamHandler(sys.stdout),
            # File handler for persistent logs
            logging.FileHandler(log_file, encoding='utf-8')
        ]
    )
    
    # Create logger for our application
    logger = logging.getLogger('BotAutomation')
    logger.setLevel(logging.DEBUG)  # Capture all levels of logs
    
    # Add exception hook to log unhandled exceptions
    def handle_exception(exc_type, exc_value, exc_traceback):
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return
        
        logger.critical("Uncaught exception:", exc_info=(exc_type, exc_value, exc_traceback))
    
    sys.excepthook = handle_exception
    
    # Log startup information
    logger.info("=== Bot Starting Up ===")
    logger.info(f"Log file: {log_file}")
    logger.info(f"Python version: {sys.version}")
    logger.info(f"Discord.py version: {discord.__version__}")
    
    return logger

class CommandExecutor:
    def __init__(self, bot):
        self.bot = bot
        self.logger = logging.getLogger('BotAutomation.CommandExecutor')

    async def execute_slash_command(self, channel, command, options=None, delay=None):
        """Execute a command using Discord's slash command system"""
        if delay is None:
            delay = float(self.bot.config['DEFAULT_DELAY'])

        try:
            self.logger.info(f"Starting command execution in channel: {channel.name} ({channel.id})")

            if command == "remove-money":
                try:
                    # Get target bot member
                    target_bot = channel.guild.get_member(int(self.bot.config['TARGET_BOT_ID']))
                    if not target_bot:
                        self.logger.error("Could not find target bot in the guild")
                        return False

                    # Format target user and amount
                    target = options['target']
                    amount = options['amount']

                    # Get the command tree for the target bot
                    try:
                        # Create a slash command interaction
                        command = await app_commands.CommandTree(self.bot).get_command("remove-money")
                        if command:
                            self.logger.info(f"Found remove-money command: {command}")

                            # Create the interaction
                            interaction = discord.Interaction(
                                data={
                                    "application_id": target_bot.id,
                                    "type": 2,  # APPLICATION_COMMAND
                                    "data": {
                                        "name": "remove-money",
                                        "options": [
                                            {"name": "user", "value": target.id if isinstance(target, discord.Member) else target},
                                            {"name": "amount", "value": int(amount)}
                                        ]
                                    }
                                },
                                state=channel._state
                            )

                            # Execute the command
                            await command.callback(interaction)
                            self.logger.info("Successfully executed remove-money command")
                            return True
                        else:
                            self.logger.error("Could not find remove-money command in target bot's command tree")
                            return False

                    except Exception as e:
                        self.logger.error(f"Error executing slash command: {str(e)}")
                        return False

                except KeyError as e:
                    self.logger.error(f"Missing required option: {str(e)}")
                    return False
                except Exception as e:
                    self.logger.error(f"Unexpected error in remove-money command: {str(e)}")
                    return False
            else:
                self.logger.error(f"Unknown command: {command}")
                return False

        except Exception as e:
            self.logger.error(f"Failed to execute command {command}: {str(e)}")
            return False

    async def wait_for_response(self, channel, timeout=None):
        """Wait for a response from the target bot"""
        if timeout is None:
            timeout = int(self.bot.config['COMMAND_TIMEOUT'])

        try:
            def check(message):
                return (
                    message.channel.id == channel.id and
                    message.author.id == int(self.bot.config['TARGET_BOT_ID'])
                )

            response = await self.bot.wait_for(
                'message',
                check=check,
                timeout=timeout
            )
            return response

        except asyncio.TimeoutError:
            self.logger.warning(f"Timeout waiting for response in channel {channel.id}")
            return None
