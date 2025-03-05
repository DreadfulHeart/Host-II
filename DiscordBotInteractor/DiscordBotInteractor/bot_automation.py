import discord
from discord import app_commands
import asyncio
import logging
import random
import os
from discord.ext import commands
from config import load_config
from utils import setup_logging
from keep_alive import start_server
import requests
from fist_fight import setup_fight_commands
import aiohttp
import aiohttp.web

# Setup logging
logger = setup_logging()

# Define your functions here
async def get_user_balance(guild_id, user_id, api_key):
    url = f"https://unbelievaboat.com/api/v1/guilds/{guild_id}/users/{user_id}"
    headers = {
        "accept": "application/json",
        "Authorization": api_key
    }
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.json().get('cash', None)
    else:
        logger.error(f"Error getting user balance: {response.text}")
        return None
async def remove_money(guild_id, user_id, amount, api_key):
    url = f"https://unbelievaboat.com/api/v1/guilds/{guild_id}/users/{user_id}"
    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "Authorization": api_key
    }
    data = {
        "cash": -amount
    }
    response = requests.patch(url, headers=headers, json=data)
    if response.status_code == 200:
        return response.json()
    else:
        logger.error(f"Error removing money: {response.text}")
        return None

async def add_money(guild_id, user_id, amount, api_key):
    url = f"https://unbelievaboat.com/api/v1/guilds/{guild_id}/users/{user_id}"
    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "Authorization": api_key
    }
    data = {
        "cash": amount
    }
    response = requests.patch(url, headers=headers, json=data)
    if response.status_code == 200:
        return response.json()
    else:
        logger.error(f"Error adding money: {response.text}")
        return None
class AutomationBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        intents.guilds = True
        super().__init__(command_prefix="!", intents=intents)
        self.config = load_config()
        self.is_active = True  # Bot state flag

    async def setup_hook(self):
        logger.info("Bot is setting up...")
        await setup_fight_commands(self)
        
        # Add admin commands
        @self.tree.command(name="shutdown", description="[ADMIN] Put the bot in sleep mode")
        @app_commands.default_permissions(administrator=True)  # Only visible to admins
        @app_commands.checks.has_permissions(administrator=True)  # Double-check permissions
        async def shutdown(interaction: discord.Interaction):
            if not interaction.user.guild_permissions.administrator:
                await interaction.response.send_message("❌ This command requires administrator permissions!", ephemeral=True)
                return
                
            self.is_active = False
            await interaction.response.send_message("💤 Bot is now in sleep mode. Use `/active` to wake it up.", ephemeral=True)
            await self.change_presence(status=discord.Status.idle, activity=discord.Game(name="Sleeping..."))
            
        @self.tree.command(name="active", description="[ADMIN] Wake up the bot from sleep mode")
        @app_commands.default_permissions(administrator=True)  # Only visible to admins
        @app_commands.checks.has_permissions(administrator=True)  # Double-check permissions
        async def activate(interaction: discord.Interaction):
            if not interaction.user.guild_permissions.administrator:
                await interaction.response.send_message("❌ This command requires administrator permissions!", ephemeral=True)
                return
                
            self.is_active = True
            await interaction.response.send_message("✅ Bot is now active!", ephemeral=True)
            await self.change_presence(status=discord.Status.online, activity=discord.Game(name="Ready to serve!"))
            
        # Add check for bot state to all commands
        @self.tree.error
        async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
            if isinstance(error, app_commands.errors.CheckFailure):
                if not self.is_active and interaction.command and interaction.command.name not in ['shutdown', 'active']:
                    await interaction.response.send_message("💤 Bot is currently in sleep mode. An administrator must use `/active` to wake it up.", ephemeral=True)
                else:
                    await interaction.response.send_message("❌ You don't have permission to use this command!", ephemeral=True)
            else:
                await interaction.response.send_message("❌ An error occurred while processing the command.", ephemeral=True)
                logger.error(f"Command error: {str(error)}")
                
        # Add the sleep mode check to all non-admin commands
        async def is_bot_active(interaction: discord.Interaction) -> bool:
            command = interaction.command
            if command and command.name in ['shutdown', 'active']:
                return True
            return self.is_active
            
        for cmd in self.tree.get_commands():
            if cmd.name not in ['shutdown', 'active']:
                cmd.add_check(is_bot_active)
                
        await self.tree.sync()  # Sync commands with Discord

    async def on_ready(self):
        logger.info(f"Logged in as {self.user}")
async def main():
    bot = AutomationBot()

    @bot.tree.command(name="woozie", description="Rob someone at gunpoint (requires Woozie role)")
    @app_commands.describe(target="The user to rob (optional, random if not specified)")
    async def woozie(interaction: discord.Interaction, target: discord.Member = None):
        try:
            # Check if user has the Woozie role
            woozie_role = discord.utils.get(interaction.guild.roles, name="Woozie")
            if not woozie_role or woozie_role not in interaction.user.roles:
                await interaction.response.send_message("❌ You need the Woozie role to use this command!", ephemeral=True)
                return

            # If no target specified, randomly select one
            if not target:
                members = interaction.guild.members
                valid_targets = [member for member in members if not member.bot and member != interaction.user]

                if not valid_targets:
                    await interaction.response.send_message("❌ No valid targets found!", ephemeral=True)
                    return

                target = random.choice(valid_targets)
            elif target == interaction.user:
                await interaction.response.send_message("❌ You can't rob yourself!", ephemeral=True)
                return
            elif target.bot:
                await interaction.response.send_message("❌ You can't rob a bot!", ephemeral=True)
                return

            # Check for roles
            shotgun_role = discord.utils.find(
                lambda r: r.name.lower() == "shotgun",
                interaction.guild.roles
            )

            woozie_role = discord.utils.get(interaction.guild.roles, name="Woozie")

            logger.info(f"Checking if {target.display_name} has shotgun/woozie roles")
            if shotgun_role:
                logger.info(f"Found shotgun role: {shotgun_role.name}")
                logger.info(f"Target roles: {[role.name for role in target.roles]}")
            else:
                logger.info(f"No shotgun role found in the server")

            if woozie_role in target.roles:
                logger.info(f"Gunfight scenario: both {interaction.user.display_name} and {target.display_name} have Woozie role")
                penalty1 = random.randint(5000, 15000)
                penalty2 = random.randint(5000, 15000)

                await interaction.response.send_message(
                    f"🔫 You try to rob {target.mention}, but they pull out their piece too!"
                )

                gunfight_options = [
                    [
                        f"💥 **BANG!** {interaction.user.display_name} fires first but misses!",
                        f"💨 \"LOCK IN BLUD!!\" {target.display_name} yells, returning fire!",
                        f"💢 {interaction.user.display_name} gets hit! (-${penalty1:,})",
                        f"💥 Your bullet grazes {target.display_name}! (-${penalty2:,})"
                    ],
                    [
                        f"🔫 **BANG! BANG!** Bullets fly everywhere!",
                        f"💥 \"ALL I SEE IS GREEN!!!\" {interaction.user.display_name} shouts!",
                        f"💢 You both get hit in the crossfire! (-${penalty1:,})",
                        f"🚓 Police sirens in the distance force you both to flee! (-${penalty2:,})"
                    ],
                    [
                        f"🔫 {target.display_name} draws faster than expected!",
                        f"💥 You trade shots in the street!",
                        f"💢 Blood spills on both sides! (-${penalty1:,}) (-${penalty2:,})",
                        f"🏃‍♂️ You both limp away before anyone sees you!"
                    ]
                ]
                gunfight_messages = random.choice(gunfight_options)

                for i, message in enumerate(gunfight_messages):
                    if i == 0:
                        await asyncio.sleep(1.5)
                    else:
                        await asyncio.sleep(1.5)
                        await interaction.followup.send(message)

                positive_gain_chance = random.randint(1, 100)
                gain_amount = 0

                if positive_gain_chance <= 5:
                    gain_participant = random.choice([interaction.user, target])
                    if gain_participant == interaction.user:
                        gain_amount = round(penalty1 * 0.20)
                        penalty1 = 0
                    else:
                        gain_amount = round(penalty2 * 0.20)
                        penalty2 = 0

                guild_id = str(interaction.guild_id)
                robber_user_id = str(interaction.user.id)
                target_user_id = str(target.id)
                api_key = os.getenv('UNBELIEVABOAT_API_TOKEN')

                await remove_money(guild_id, robber_user_id, penalty1, api_key)
                await remove_money(guild_id, target_user_id, penalty2, api_key)

                if gain_amount > 0:
                    if gain_participant == interaction.user:
                        await interaction.followup.send(
                            f"💸 **Gunfight Aftermath:**\n"
                            f"{interaction.user.mention}: +${gain_amount:,}\n"
                            f"{target.mention}: -${penalty2:,}"
                        )
                    else:
                        await interaction.followup.send(
                            f"💸 **Gunfight Aftermath:**\n"
                            f"{interaction.user.mention}: -${penalty1:,}\n"
                            f"{target.mention}: +${gain_amount:,}"
                        )
                else:
                    await interaction.followup.send(
                        f"💸 **Gunfight Aftermath:**\n"
                        f"{interaction.user.mention}: -${penalty1:,}\n"
                        f"{target.mention}: -${penalty2:,}"
                    )

                return
            elif shotgun_role and shotgun_role in target.roles:
                penalty = random.randint(10000, 15000)
                logger.info(f"{target.display_name} has shotgun role, preventing robbery and penalizing robber {penalty}")

                await interaction.response.send_message(
                    f"🔫 You try to rob {target.mention}, but wait... what's that they're reaching for?"
                )

                shotgun_options = [
                    [
                        f"💥 **BOOM!** {target.display_name} pulls out a shotgun!",
                        f"😱 \"LOCK IN BLUD!!\" {target.display_name} shouts as they fire!",
                        f"💢 The blast catches you! (-${penalty:,})",
                        f"🩸 You escape, badly wounded!"
                    ],
                    [
                        f"💥 {target.display_name} reveals a sawed-off shotgun!",
                        f"😱 You freeze in place seeing the barrel!",
                        f"💢 The shot rings out! (-${penalty:,})",
                        f"🏥 You'll need stitches after this one!"
                    ],
                    [
                        f"💥 \"{target.display_name}'s strapped with a shotty!\" someone yells!",
                        f"😱 You try to escape but stumble!",
                        f"💢 **BOOM!** You take the blast! (-${penalty:,})",
                        f"🚑 That's a hospital trip for sure!"
                    ]
                ]
                shotgun_messages = random.choice(shotgun_options)

                for message in shotgun_messages:
                    await asyncio.sleep(1.5)
                    await interaction.followup.send(message)

                guild_id = str(interaction.guild_id)
                robber_user_id = str(interaction.user.id)
                api_key = os.getenv('UNBELIEVABOAT_API_TOKEN')

                await remove_money(guild_id, robber_user_id, penalty, api_key)
                return

            guild_id = str(interaction.guild_id)
            target_user_id = str(target.id)
            robber_user_id = str(interaction.user.id)
            api_key = os.getenv('UNBELIEVABOAT_API_TOKEN')

            target_balance = await get_user_balance(guild_id, target_user_id, api_key)
            if not target_balance or target_balance <= 0:
                await interaction.response.send_message(
                    f"❌ {target.mention} is broke! No money to rob.",
                    ephemeral=True
                )
                return

            amount = random.randint(25000, 50000)
            if target_balance < amount:
                amount = target_balance
                logger.info(f"Limiting robbery amount to {amount} to prevent negative balance")

            await interaction.response.send_message(f"🔫 You're robbing {target.mention}!")

            result = await remove_money(guild_id, target_user_id, amount, api_key)

            if result:
                target_new_balance = result.get('cash', 'unknown')

                logger.info(f"Attempting to add {amount} to user {robber_user_id} in guild {guild_id}")
                add_result = await add_money(guild_id, robber_user_id, amount, api_key)

                if add_result:
                    robber_new_balance = add_result.get('cash', 'unknown')
                    await interaction.followup.send(
                        f"💰 Successfully robbed ${amount:,} from {target.mention}!\n"
                        f"Their new balance is ${target_new_balance:,}\n"
                        f"Your new balance is ${robber_new_balance:,}"
                    )
                else:
                    await interaction.followup.send(
                        f"💰 Successfully robbed ${amount:,} from {target.mention}, but failed to add it to your account.\n"
                        f"Their new balance is ${target_new_balance:,}"
                    )
            else:
                await interaction.followup.send(
                    "❌ Failed to rob the target. They might be broke or protected!\n"
                    "Make sure you have permissions to use economy commands."
                )

        except Exception as e:
            logger.error(f"Error in gunpoint command: {str(e)}")

    @bot.tree.command(name="plock", description="Rob someone with a pistol (requires Glock role)")
    @app_commands.describe(target="The user to rob (optional, random if not specified)")
    async def plock(interaction: discord.Interaction, target: discord.Member = None):
        try:
            glock_role = discord.utils.get(interaction.guild.roles, name="Glock")
            if not glock_role or glock_role not in interaction.user.roles:
                await interaction.response.send_message("❌ You need the Glock role to use this command!", ephemeral=True)
                return

            if not target:
                members = interaction.guild.members
                valid_targets = [member for member in members if not member.bot and member != interaction.user]

                if not valid_targets:
                    await interaction.response.send_message("❌ No valid targets found!", ephemeral=True)
                    return

                target = random.choice(valid_targets)
            elif target == interaction.user:
                await interaction.response.send_message("❌ You can't rob yourself!", ephemeral=True)
                return
            elif target.bot:
                await interaction.response.send_message("❌ You can't rob a bot!", ephemeral=True)
                return

            shotgun_role = discord.utils.find(
                lambda r: r.name.lower() == "shotgun",
                interaction.guild.roles
            )

            woozie_role = discord.utils.get(interaction.guild.roles, name="Woozie")
            uzi_role = discord.utils.find(
                lambda r: r.name.lower() == "uzi",
                interaction.guild.roles
            )

            logger.info(f"Plock command: Checking if {target.display_name} has shotgun/woozie/uzi/plock roles")

            if uzi_role and uzi_role in target.roles:
                penalty = random.randint(5000, 10000)
                logger.info(f"{target.display_name} has Uzi role, overpowering plock user with penalty {penalty}")

                uzi_intros = [
                    f"🔫 Your plock is no match for {target.mention}'s UZI!",
                    f"🔫 {target.mention} pulls out an UZI when you show your plock!",
                    f"🔫 You brought a plock to an UZI fight with {target.mention}!"
                ]
                await interaction.response.send_message(random.choice(uzi_intros))

                uzi_options = [
                    [f"💥 UZI fires!", f"💢 You're hit! (-${penalty:,})"],
                    [f"💥 \"ALL I SEE IS GREEN!!!\" Someone nearby yells!", f"💢 Multiple hits! (-${penalty:,})"],
                    [f"💥 UZI wins!", f"💢 You're wounded! (-${penalty:,})"]
                ]
                uzi_messages = random.choice(uzi_options)

                for message in uzi_messages:
                    await asyncio.sleep(1.5)
                    await interaction.followup.send(message)

                guild_id = str(interaction.guild_id)
                robber_user_id = str(interaction.user.id)
                api_key = os.getenv('UNBELIEVABOAT_API_TOKEN')

                await remove_money(guild_id, robber_user_id, penalty, api_key)

                return

            elif shotgun_role and shotgun_role in target.roles:
                logger.info(f"{target.display_name} has shotgun role, scaring away plock user")

                await interaction.response.send_message(
                    f"🔫 You pull out your pistol to rob {target.mention}, but freeze when you see their shotgun!"
                )

                shotgun_options = [
                    [
                        f"💥 **CLICK!** {target.display_name} cocks their shotgun!",
                        f"😱 The sight of that barrel makes you freeze!",
                        f"🏃 You quickly put away your plock...",
                        f"💨 You back away slowly, grateful to be alive!"
                    ],
                    [
                        f"💥 {target.display_name} reveals a shotgun!",
                        f"😱 \"You picked the wrong one today!\" they shout!",
                        f"🏃 Your plock feels useless now...",
                        f"💨 You decide this isn't worth it and flee!"
                    ],
                    [
                        f"💥 {target.display_name}'s shotgun makes your plock look like a toy!",
                        f"😱 \"LOCK IN BLUD!!\" they shout, aiming at you!",
                        f"🏃 That plock won't help you now...",
                        f"💨 You wisely choose to run away!"
                    ]
                ]
                shotgun_messages = random.choice(shotgun_options)

                for message in shotgun_messages:
                    await asyncio.sleep(1.5)
                    await interaction.followup.send(message)

                await interaction.followup.send(
                    f"😅 You escaped without losing any money, but your pride is severely wounded!"
                )

                return
            elif glock_role in target.roles:
                logger.info(f"Pistol standoff: both {interaction.user.display_name} and {target.display_name} have Glock role")

                penalty1 = random.randint(1000, 5000)
                penalty2 = random.randint(1000, 5000)

                await interaction.response.send_message(
                    f"🔫 You pull your pistol on {target.mention}, but they draw their pistol too!"
                )

                standoff_options = [
                    [
                        f"🔫 You're both pointing plocks at each other!",
                        f"😠 \"Drop it!\" you both shout at the same time!",
                        f"💥 {interaction.user.display_name} takes a graze! (-${penalty1:,})",
                        f"💢 {target.display_name} gets hit too! (-${penalty2:,})"
                    ],
                    [
                        f"🔫 Two plocks drawn in a standoff!",
                        f"💥 \"ALL I SEE IS GREEN!!!\" Someone nearby yells!",
                        f"😠 Shots ring out in the panic! (-${penalty1:,})",
                        f"💢 Both of you are hit! (-${penalty2:,})"
                    ],
                    [
                        f"🔫 Your plocks are locked on each other!",
                        f"💥 Fingers twitch and bullets fly!",
                        f"💢 You both take hits! (-${penalty1:,}) (-${penalty2:,})",
                        f"🚓 A police siren sends you both running!"
                    ]
                ]
                standoff_messages = random.choice(standoff_options)

                for i, message in enumerate(standoff_messages):
                    if i == 0:
                        await asyncio.sleep(1.5)
                    else:
                        await asyncio.sleep(1.5)
                        await interaction.followup.send(message)

                guild_id = str(interaction.guild_id)
                robber_user_id = str(interaction.user.id)
                target_user_id = str(target.id)
                api_key = os.getenv('UNBELIEVABOAT_API_TOKEN')

                await remove_money(guild_id, robber_user_id, penalty1, api_key)
                await remove_money(guild_id, target_user_id, penalty2, api_key)

                if result1 and result2:
                    robber_new_balance = result1.get('cash', 'unknown')
                    target_new_balance = result2.get('cash', 'unknown')
                    await interaction.followup.send(
                        f"💸 **Pistol Fight Aftermath:**\n"
                        f"{interaction.user.mention}: ${robber_new_balance:,} (-${penalty1:,})\n"
                        f"{target.mention}: ${target_new_balance:,} (-${penalty2:,})"
                    )

                return

            guild_id = str(interaction.guild_id)
            target_user_id = str(target.id)
            robber_user_id = str(interaction.user.id)
            api_key = os.getenv('UNBELIEVABOAT_API_TOKEN')

            target_balance = await get_user_balance(guild_id, target_user_id, api_key)
            if not target_balance or target_balance <= 0:
                await interaction.response.send_message(
                    f"❌ {target.mention} is broke! No money to rob.",
                    ephemeral=True
                )
                return

            amount = random.randint(500, 10000)
            if target_balance < amount:
                amount = target_balance
                logger.info(f"Limiting robbery amount to {amount} to prevent negative balance")

            await interaction.response.send_message(f"🔫 You're robbing {target.mention} with your plock!")

            result = await remove_money(guild_id, target_user_id, amount, api_key)

            if result:
                target_new_balance = result.get('cash', 'unknown')

                logger.info(f"Plock robbery: Attempting to add {amount} to user {robber_user_id} in guild {guild_id}")
                add_result = await add_money(guild_id, robber_user_id, amount, api_key)

                if add_result:
                    robber_new_balance = add_result.get('cash', 'unknown')
                    await interaction.followup.send(
                        f"💰 Successfully robbed ${amount:,} from {target.mention}!\n"
                        f"Their new balance is ${target_new_balance:,}\n"
                        f"Your new balance is ${robber_new_balance:,}"
                    )
                else:
                    await interaction.followup.send(
                        f"💰 Successfully robbed ${amount:,} from {target.mention}, but failed to add it to your account.\n"
                        f"Their new balance is ${target_new_balance:,}"
                    )
            else:
                await interaction.followup.send(
                    "❌ Failed to rob the target. They might be broke or protected!\n"
                    "Make sure you have permissions to use economy commands."
                )

        except Exception as e:
            logger.error(f"Error in plock command: {str(e)}")

    @bot.tree.command(name="geturl", description="Get the bot's Replit URL for uptime monitoring (Admin only)")
    @app_commands.check(lambda interaction: interaction.user.guild_permissions.administrator)
    async def geturl(interaction: discord.Interaction):
        try:
            if not interaction.user.guild_permissions.administrator:
                await interaction.response.send_message("❌ You need administrator permissions to use this command!", ephemeral=True)
                return

            repl_slug = os.getenv('REPL_SLUG', 'unknown')
            repl_owner = os.getenv('REPL_OWNER', 'unknown')

            if repl_slug != 'unknown' and repl_owner != 'unknown':
                deployment_url = f"https://{repl_slug}-{repl_owner}.replit.app"

                await interaction.response.send_message(
                    f"🔗 **Bot URL for UptimeRobot:**\n"
                    f"Use this URL: {deployment_url}\n\n"
                    f"**Setup Instructions:**\n"
                    f"1. Make sure you've deployed your bot using Replit's Deployment feature\n"
                    f"2. Go to UptimeRobot.com and create an account if you don't have one\n"
                    f"3. Add a new monitor (HTTP(s) type)\n"
                    f"4. Paste this URL: {deployment_url}\n"
                    f"5. Set monitoring interval to 5 minutes\n"
                    f"6. Save and your bot will stay online 24/7",
                    ephemeral=True
                )
            else:
                await interaction.response.send_message(
                    "❌ Could not determine the Replit URL. Make sure this is running on Replit.",
                    ephemeral=True
                )

        except Exception as e:
            logger.error(f"Error in geturl command: {str(e)}")
            await interaction.response.send_message(
                "❌ An error occurred while getting the URL.",
                ephemeral=True
            )
    try:
        async with bot:
            await bot.start(bot.config['TOKEN'])
    except Exception as e:
        logger.error(f"Failed to start bot: {str(e)}")

async def run_web_server():
    app = aiohttp.web.Application()
    
    async def handle_health_check(request):
        return aiohttp.web.Response(text="Bot is running!", status=200)
        
    app.router.add_get('/', handle_health_check)
    app.router.add_get('/health', handle_health_check)
    
    port = int(os.environ.get('PORT', 10000))
    runner = aiohttp.web.AppRunner(app)
    await runner.setup()
    site = aiohttp.web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    logger.info(f"Web server started on port {port}")

async def main():
    await asyncio.gather(
        run_web_server(),
        asyncio.run(main())
    )

if __name__ == "__main__":
    start_server()
    logger.info("Started Python HTTP server for UptimeRobot")

    logger.info("Starting Discord bot")
    asyncio.run(main())
