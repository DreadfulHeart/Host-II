import discord
from discord import app_commands
import asyncio
from discord.ui import Button, View, Modal, TextInput
import logging
from utils import setup_logging
import os
import random
import requests
from typing import Dict, List

# Setup logging
logger = setup_logging()

# Store active fights and bets
active_fights: Dict[int, Dict] = {}  # message_id -> fight info
active_bets: Dict[int, List[Dict]] = {}  # message_id -> list of bets

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

async def update_money(guild_id, user_id, amount, api_key):
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
        logger.error(f"Error updating money: {response.text}")
        return None

class BetModal(Modal):
    def __init__(self, message_id: int, fighter: discord.Member):
        super().__init__(title=f"Place bet on {fighter.display_name}")
        self.message_id = message_id
        self.fighter = fighter
        
        self.amount = TextInput(
            label="Bet Amount",
            placeholder="Enter amount to bet...",
            min_length=1,
            max_length=10,
            required=True
        )
        self.add_item(self.amount)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            amount = int(self.amount.value)
            if amount <= 0:
                await interaction.response.send_message("Bet amount must be positive!", ephemeral=True)
                return
                
            api_key = os.getenv('UNBELIEVABOAT_API_KEY')
            guild_id = str(interaction.guild_id)
            user_id = str(interaction.user.id)
            
            # Check user balance
            balance = await get_user_balance(guild_id, user_id, api_key)
            if balance is None or balance < amount:
                await interaction.response.send_message("You don't have enough money for this bet!", ephemeral=True)
                return
                
            # Remove bet amount
            if not await update_money(guild_id, user_id, -amount, api_key):
                await interaction.response.send_message("Failed to process bet!", ephemeral=True)
                return
                
            # Record bet
            if self.message_id not in active_bets:
                active_bets[self.message_id] = []
            
            active_bets[self.message_id].append({
                'user': interaction.user,
                'amount': amount,
                'fighter': self.fighter
            })
            
            await interaction.response.send_message(
                f"💰 {interaction.user.mention} has bet ${amount:,} on {self.fighter.mention}!",
                ephemeral=False
            )
            
        except ValueError:
            await interaction.response.send_message("Please enter a valid number!", ephemeral=True)

class FightButton(Button):
    def __init__(self, custom_id: str, label: str, style: discord.ButtonStyle):
        super().__init__(style=style, label=label, custom_id=custom_id)

    async def callback(self, interaction: discord.Interaction):
        if self.custom_id.startswith('accept_'):
            message_id = int(self.custom_id.split('_')[1])
            fight_info = active_fights.get(message_id)
            
            if not fight_info:
                await interaction.response.send_message("This fight is no longer active!", ephemeral=True)
                return
                
            if interaction.user.id != fight_info['target'].id:
                await interaction.response.send_message("You are not the challenged player!", ephemeral=True)
                return
                
            # Start the fight
            fight_info['accepted'] = True
            for item in self.view.children:
                item.disabled = True
            await interaction.message.edit(view=self.view)
            
            # Fight sequence
            challenger = fight_info['challenger']
            target = fight_info['target']
            
            await interaction.response.send_message(f"🥊 The fight between {challenger.mention} and {target.mention} begins!")
            
            # Fight mechanics
            challenger_hp = 100
            target_hp = 100
            
            moves = [
                ("throws a devastating haymaker", "barely dodges the punch", "CONNECTS WITH BRUTAL FORCE!", 40),
                ("goes for a flying knee", "blocks with their arms", "SMASHES INTO THEIR FACE!", 45),
                ("attempts a spinning back kick", "tries to step away", "LANDS PERFECTLY ON THE JAW!", 50),
                ("launches a brutal combo", "covers up defensively", "BREAKS THROUGH THE GUARD!", 35),
                ("charges with a superman punch", "attempts to counter", "LANDS CLEAN!", 45),
                ("goes for a takedown", "sprawls to defend", "SLAMS THEM TO THE GROUND!", 30),
                ("attempts an elbow strike", "tries to parry", "SLICES THROUGH THEIR DEFENSE!", 40),
                ("throws a liver shot", "tightens their core", "FINDS ITS MARK!", 45),
                ("goes for a head kick", "ducks under", "CONNECTS WITH DEVASTATING IMPACT!", 55)
            ]
            
            critical_hits = [
                "💥 CRITICAL HIT! The strike hits a vital point!",
                "💫 SUPER EFFECTIVE! That's going to leave a mark!",
                "⚡ PERFECT TIMING! Couldn't have landed better!",
                "🌟 DEVASTATING BLOW! The crowd goes wild!",
                "💢 MASSIVE DAMAGE! That might be a fight-ender!"
            ]
            
            while challenger_hp > 0 and target_hp > 0:
                await asyncio.sleep(2)  # Delay between rounds
                
                # Randomly determine attacker and defender
                if random.random() < 0.5:
                    attacker, defender = challenger, target
                    hp_to_reduce = target_hp
                else:
                    attacker, defender = target, challenger
                    hp_to_reduce = challenger_hp
                
                # Pick a random move
                move, dodge, hit, base_damage = random.choice(moves)
                
                # 70% chance to hit, with possibility of critical hits
                if random.random() < 0.7:
                    # 20% chance for critical hit (1.5x damage)
                    is_critical = random.random() < 0.2
                    damage = round(base_damage * 1.5) if is_critical else base_damage
                    
                    if attacker == challenger:
                        target_hp -= damage
                    else:
                        challenger_hp -= damage
                    
                    round_msg = f"💥 {attacker.mention} {move} and {hit} (-{damage} HP)"
                    if is_critical:
                        round_msg = f"{random.choice(critical_hits)}\n{round_msg}"
                else:
                    round_msg = f"💨 {attacker.mention} {move} but {defender.mention} {dodge}!"
                
                # Ensure HP doesn't go below 0
                challenger_hp = max(0, challenger_hp)
                target_hp = max(0, target_hp)
                
                # Show HP bars
                challenger_bar = "❤" * (challenger_hp // 10) + "🖤" * ((100 - challenger_hp) // 10)
                target_bar = "❤" * (target_hp // 10) + "🖤" * ((100 - target_hp) // 10)
                
                await interaction.followup.send(
                    f"{round_msg}\n\n"
                    f"{challenger.display_name}: {challenger_hp}HP\n{challenger_bar}\n\n"
                    f"{target.display_name}: {target_hp}HP\n{target_bar}"
                )
            
            # Determine winner
            winner = challenger if target_hp <= 0 else target
            loser = target if target_hp <= 0 else challenger
            
            # Process bets
            if message_id in active_bets:
                api_key = os.getenv('UNBELIEVABOAT_API_KEY')
                guild_id = str(interaction.guild_id)
                
                for bet in active_bets[message_id]:
                    if bet['fighter'].id == winner.id:
                        # Winner gets double their bet
                        winnings = bet['amount'] * 2
                        await update_money(guild_id, str(bet['user'].id), winnings, api_key)
                        await interaction.followup.send(f"💰 {bet['user'].mention} won ${winnings:,} from their bet!")
                
                del active_bets[message_id]
            
            await interaction.followup.send(
                f"🏆 {winner.mention} has won the fight against {loser.mention} in an epic battle!\n"
                f"{'💀 It was a KNOCKOUT!' if abs(challenger_hp - target_hp) > 50 else '👊 What a close fight!'}"
            )
            del active_fights[message_id]

class BetButton(Button):
    def __init__(self, fighter: discord.Member):
        super().__init__(
            style=discord.ButtonStyle.secondary,
            label=f"Bet on {fighter.display_name}",
            custom_id=f'temp_bet_{fighter.id}'  # Temporary ID, will be updated
        )
        self.fighter = fighter
        self.message_id = None  # Will be set after message is sent

    async def callback(self, interaction: discord.Interaction):
        if not self.message_id:
            await interaction.response.send_message("Error: Fight not properly initialized", ephemeral=True)
            return

        fight_info = active_fights.get(self.message_id)
        
        if not fight_info:
            await interaction.response.send_message("This fight is no longer active!", ephemeral=True)
            return
            
        # Allow betting before the fight is accepted
        await interaction.response.send_modal(BetModal(self.message_id, self.fighter))

class FightView(View):
    def __init__(self, challenger: discord.Member, target: discord.Member, timeout: float = 180):
        super().__init__(timeout=timeout)
        self.message_id = None  # Will be set after the message is sent
        self.challenger = challenger
        self.target = target
        self.accept_button = FightButton('accept', "Accept Fight", discord.ButtonStyle.success)
        self.add_item(self.accept_button)
        self.add_item(BetButton(challenger))
        self.add_item(BetButton(target))

    async def set_message_id(self, message_id: int):
        self.message_id = message_id
        self.accept_button.custom_id = f'accept_{message_id}'
        for item in self.children:
            if isinstance(item, BetButton):
                item.message_id = message_id

async def setup_fight_commands(bot):
    @bot.tree.command(name="fight", description="Challenge another player to a fist fight")
    @app_commands.describe(target="The player you want to challenge")
    async def fight(interaction: discord.Interaction, target: discord.Member):
        if target.bot:
            await interaction.response.send_message("You can't fight a bot!", ephemeral=True)
            return
            
        if target == interaction.user:
            await interaction.response.send_message("You can't fight yourself!", ephemeral=True)
            return

        # Create the view
        view = FightView(interaction.user, target)
        
        # Send the challenge message
        response = await interaction.response.send_message(
            f"🥊 {interaction.user.mention} has challenged {target.mention} to a fight!\n"
            f"Place your bets now! The challenged player has 3 minutes to accept!",
            view=view
        )
        
        # Get the message from the response
        message = await interaction.original_response()
        await view.set_message_id(message.id)
        
        # Store fight information
        active_fights[message.id] = {
            'challenger': interaction.user,
            'target': target,
            'accepted': False,
        }
        
        # Set up timeout to clean up if fight not accepted
        await asyncio.sleep(180)  # 3 minutes
        if message.id in active_fights and not active_fights[message.id]['accepted']:
            # Return money to betters if fight wasn't accepted
            if message.id in active_bets:
                api_key = os.getenv('UNBELIEVABOAT_API_KEY')
                guild_id = str(interaction.guild_id)
                
                for bet in active_bets[message.id]:
                    # Return the bet amount
                    await update_money(guild_id, str(bet['user'].id), bet['amount'], api_key)
                    try:
                        await interaction.followup.send(f"💰 Returning ${bet['amount']:,} to {bet['user'].mention} as the fight was not accepted.")
                    except:
                        pass
                
                del active_bets[message.id]
            
            del active_fights[message.id]
            try:
                await interaction.edit_original_response(content="⏰ Challenge has expired! All bets have been returned.", view=None)
            except:
                pass  # Message might have been deleted
