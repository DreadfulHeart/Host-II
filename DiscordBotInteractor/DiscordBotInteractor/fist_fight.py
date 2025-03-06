import discord
from discord import app_commands
import asyncio
from discord.ui import Button, View, Modal, TextInput
import logging
from utils import setup_logging
import os
import random
from typing import Dict, List, Optional
from config import load_config
from api_client import UnbelievaBoatAPI

# Setup logging
logger = setup_logging()

# Load configuration and initialize API client
config = load_config()
api_client = UnbelievaBoatAPI()

# Store active fights and bets
active_fights: Dict[int, Dict] = {}  # message_id -> fight info
active_bets: Dict[int, List[Dict]] = {}  # message_id -> list of bets

def get_hearts_display(current_hp: int, max_hp: int = 100) -> str:
    """Return a string of hearts based on percentage of health remaining"""
    heart_count = 6  # Total hearts to show
    hearts_remaining = round((current_hp / max_hp) * heart_count)
    return "❤️" * hearts_remaining + "🖤" * (heart_count - hearts_remaining)

async def get_user_balance(guild_id: str, user_id: str) -> Optional[int]:
    """Get user balance using UnbelievaBoat API"""
    return await api_client.get_balance(guild_id, user_id)

async def update_money(guild_id: str, user_id: str, amount: int) -> Optional[Dict]:
    """Update user balance using UnbelievaBoat API"""
    if amount > 0:
        return await api_client.add_money(guild_id, user_id, amount)
    else:
        return await api_client.remove_money(guild_id, user_id, abs(amount))

class BetModal(Modal):
    def __init__(self, message_id: int, fighter: discord.Member):
        super().__init__(title=f"Place bet on {fighter.display_name}")
        self.message_id = message_id
        self.fighter = fighter
        
        self.amount = TextInput(
            label="Bet Amount (minimum: $1)",
            placeholder="Enter amount to bet (minimum: $1)...",
            min_length=1,
            max_length=10,
            required=True
        )
        self.add_item(self.amount)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            amount = int(self.amount.value)
            if amount < 1:
                await interaction.response.send_message("Minimum bet amount is $1!", ephemeral=True)
                return
                
            guild_id = str(interaction.guild_id)
            user_id = str(interaction.user.id)
            
            # Check user balance
            balance = await get_user_balance(guild_id, user_id)
            if balance is None:
                await interaction.response.send_message("Error checking balance. Please try again.", ephemeral=True)
                return
                
            logger.info(f"User {user_id} balance: ${balance:,}, trying to bet: ${amount:,}")
            if balance < amount:
                await interaction.response.send_message(f"You don't have enough money! Your balance: ${balance:,}", ephemeral=True)
                return
                
            # Remove bet amount (use negative amount to remove money)
            result = await update_money(guild_id, user_id, -amount)
            if not result:
                await interaction.response.send_message("Failed to process bet! Please try again.", ephemeral=True)
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
            self.disabled = True
            await interaction.message.edit(view=self.view)
            
            # Fight sequence
            challenger = fight_info['challenger']
            target = fight_info['target']
            
            await interaction.response.send_message(f"🥊 The fight between {challenger.mention} and {target.mention} begins!")
            
            # Fight mechanics with hearts system
            rounds = []
            challenger_hp = 100
            target_hp = 100
            
            moves = [
                ("throws a quick jab", "dodges the jab", "lands a solid hit", 25, "💫"),
                ("goes for an uppercut", "steps back", "connects with devastating force", 35, "💥"),
                ("attempts a roundhouse kick", "blocks the kick", "lands perfectly", 40, "🦶"),
                ("tries a body shot", "guards their body", "hits the mark", 30, "👊"),
                ("launches a haymaker", "ducks under", "catches them off guard", 45, "⚡")
            ]
            
            # Special moves that can only be used once per fighter
            special_moves = {
                challenger.id: True,  # True means special move is available
                target.id: True
            }
            
            while challenger_hp > 0 and target_hp > 0:
                await asyncio.sleep(3)  # Delay between rounds
                
                # Randomly determine attacker and defender
                if random.random() < 0.5:
                    attacker, defender = challenger, target
                    hp_to_reduce = 'target_hp'
                else:
                    attacker, defender = target, challenger
                    hp_to_reduce = 'challenger_hp'
                
                # 15% chance for special move if available
                if random.random() < 0.15 and special_moves[attacker.id]:
                    special_moves[attacker.id] = False  # Use up special move
                    damage = random.randint(50, 60)  # Special move does big damage
                    if hp_to_reduce == 'target_hp':
                        target_hp -= damage
                    else:
                        challenger_hp -= damage
                    round_msg = f"⭐ SPECIAL MOVE! {attacker.mention} unleashes a devastating combo! (-{damage} HP)"
                else:
                    # Regular moves
                    move, dodge, hit, damage, emoji = random.choice(moves)
                    
                    # 70% chance to hit
                    if random.random() < 0.7:
                        # 20% chance for critical hit (1.5x damage)
                        if random.random() < 0.2:
                            damage = int(damage * 1.5)
                            hit = "CRITICAL HIT! " + hit
                            emoji = "🌟"
                        
                        if hp_to_reduce == 'target_hp':
                            target_hp -= damage
                        else:
                            challenger_hp -= damage
                        round_msg = f"{emoji} {attacker.mention} {move} and {hit}! (-{damage} HP)"
                    else:
                        round_msg = f"💨 {attacker.mention} {move} but {defender.mention} {dodge}!"
                
                rounds.append(round_msg)
                # Show current HP and hearts status
                hearts_display = {
                    challenger.display_name: get_hearts_display(challenger_hp),
                    target.display_name: get_hearts_display(target_hp)
                }
                status = f"\n{challenger.display_name}: {challenger_hp}HP {hearts_display[challenger.display_name]}\n{target.display_name}: {target_hp}HP {hearts_display[target.display_name]}"
                await interaction.followup.send(f"{round_msg}{status}")
            
            # Determine winner
            winner = challenger if target_hp <= 0 else target
            loser = target if target_hp <= 0 else challenger
            
            # Process bets with multipliers based on remaining health
            if message_id in active_bets:
                guild_id = str(interaction.guild_id)
                winner_hp = challenger_hp if winner == challenger else target_hp
                
                # Higher multiplier for more health remaining
                multiplier = 1.5 + (winner_hp / 100)  # Scales from 1.5x to 2.5x based on remaining HP
                
                for bet in active_bets[message_id]:
                    if bet['fighter'].id == winner.id:
                        winnings = int(bet['amount'] * multiplier)
                        await update_money(guild_id, str(bet['user'].id), winnings)
                        await interaction.followup.send(f"💰 {bet['user'].mention} won ${winnings:,} from their bet! ({multiplier:.1f}x multiplier)")
                
                del active_bets[message_id]
            
            # Victory message
            if winner_hp > 75:
                await interaction.followup.send(f"🏆 DOMINANT VICTORY! {winner.mention} crushes {loser.mention} with {winner_hp}HP remaining!")
            elif winner_hp > 50:
                await interaction.followup.send(f"🏆 SOLID WIN! {winner.mention} defeats {loser.mention} with {winner_hp}HP remaining!")
            else:
                await interaction.followup.send(f"🏆 CLOSE FIGHT! {winner.mention} barely defeats {loser.mention} with {winner_hp}HP remaining!")
            
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
            
        # Show betting modal - removed acceptance check to allow pre-fight betting
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

    async def on_timeout(self):
        """Handle timeout - refund all bets if fight wasn't accepted"""
        if self.message_id in active_fights and not active_fights[self.message_id]['accepted']:
            if self.message_id in active_bets:
                guild_id = str(self.message.guild.id)
                for bet in active_bets[self.message_id]:
                    # Refund the bet amount
                    await update_money(guild_id, str(bet['user'].id), bet['amount'])
                    try:
                        await self.message.channel.send(f"💰 Refunded ${bet['amount']:,} to {bet['user'].mention} as the fight was not accepted.")
                    except:
                        pass  # Message might fail to send
                del active_bets[self.message_id]
            del active_fights[self.message_id]
            try:
                await self.message.edit(content="⏰ Challenge has expired!", view=None)
            except:
                pass  # Message might have been deleted

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
            f"Place your bets now! The challenged player has 3 minutes to accept.\n"
            f"If the fight is not accepted, all bets will be refunded.",
            view=view
        )
        
        # Get the message from the response
        message = await interaction.original_response()
        view.message = message  # Store message for timeout handling
        await view.set_message_id(message.id)
        
        # Store fight information
        active_fights[message.id] = {
            'challenger': interaction.user,
            'target': target,
            'accepted': False,
        }
