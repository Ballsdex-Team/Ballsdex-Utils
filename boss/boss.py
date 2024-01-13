import logging
import random
import sys
from typing import TYPE_CHECKING

import discord
from redbot.core import commands, app_commands

from ballsdex import __version__ as ballsdex_version
from ballsdex.core.models import Ball, BallInstance
from ballsdex.core.models import balls as countryballs
from ballsdex.core.utils.tortoise import row_count_estimate
from ballsdex.settings import settings
from discord.ui import Button, View
from io import BytesIO


if TYPE_CHECKING:
    from ballsdex.core.bot import BallsDexBot

log = logging.getLogger("ballsdex.packages.boss")


class BossView(View):
    def __init__(self, interaction: discord.Interaction, entry_list, dead_list):
        super().__init__(timeout=300)
        self.value = None
        self.interaction = interaction
        self.entry_list = entry_list
        self.dead_list = dead_list

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True  # type: ignore
        try:
            await self.interaction.followup.edit_message("@original", view=self)  # type: ignore
        except discord.NotFound:
            pass

    @discord.ui.button(
        style=discord.ButtonStyle.success, label="Join"
    )
    async def join_button(self, interaction: discord.Interaction, button: Button):
        if (interaction.user.id, interaction.user.display_name) in self.dead_list:
            await interaction.followup.send(f"{interaction.user.mention} is dead and cannot rejoin.", ephemeral=True)
            return
        if (interaction.user.id, interaction.user.display_name) in self.entry_list:
            self.entry_list.remove((interaction.user.id, interaction.user.display_name) )
            # reply to interaction
            await interaction.followup.send(f"{interaction.user.mention} has left the boss battle.", ephemeral=True)
        else:
            self.entry_list.append((interaction.user.id, interaction.user.display_name) )
            # reply to interaction
            await interaction.followup.send(f"{interaction.user.mention} has joined the boss battle.", ephemeral=True)
        
        

class Boss(commands.Cog):
    """
    Boss commandss.
    """

    def __init__(self, bot: "BallsDexBot"):
        self.bot = bot
        self.boss = None
        self.boss_hp = 0
        self.boss_max_hp = 0
        self.boss_entries = []
        self.boss_dead = []


    boss = app_commands.Group(name="boss", description="Boss management", guild_ids=[1049118743101452329])

    @boss.command()
    @app_commands.checks.has_any_role(*settings.root_role_ids)
    async def start(self, interaction: discord.Interaction):
        """
        Start a boss.
        """
        # Create a message with a button that when pressed, adds you to boss_entries
        view = BossView(interaction, self.boss_entries, self.boss_dead)
        await interaction.response.send_message("Boss battle started!", ephemeral=True, view=view)
    
    @boss.command()
    @app_commands.checks.has_any_role(*settings.root_role_ids)
    async def choose(self, interaction: discord.Interaction):
        """
        Choose a boss.
        """
        # Choose a boss from the the following list
        bosses = ["Reichtangle",
        "Russian empire",
        "Scandinavia",
        "German empire",
        "Antarctica",
        "Austria-Hungary ",
        "United States",
        "Vatican",
        "Russia",
        "Greenland",
        "Soviet union",
        "Roman Empire",
        "Qin",
        "Hunnic Empire",
        "British Empire",
        "Republic of China",
        "Japanese Empire"]
        
        # Choose a random boss
        boss = random.choice(bosses)
        #choose a random hp
        hp = random.randint(75000, 25000)
        # Set the boss
        self.boss = boss
        # Set the boss hp
        self.boss_hp = hp
        # Set the boss max hp
        self.boss_max_hp = hp

        # Send a message saying the boss has been chosen
        
        await interaction.response.send_message(f"The boss has been chosen! It is {boss}")

    def get_bonus(self, item):
        base = item.attack
        if item.special_id in [4, 6, 8, 9, 10, 11, 14, 15]:
            base += 250
        if item.special_id in [5, 13, 12]:
            base += 750
        if item.shiny:
            base += 1000
        if item.special_id == 7:
            base += 1500
        return base

    @boss.command()
    @app_commands.checks.has_any_role(*settings.root_role_ids)
    async def endround(self, interaction: discord.Interaction):
        """
        End the round.
        """
        await interaction.response.defer(thinking=True, ephemeral=True)
        # loop through the entries and pick a random ball from each entry to attack the boss
        attack_msg = "The boss has been attacked! The following balls have attacked the boss: \n"
        for entry in self.boss_entries:
            # Choose a random ball from the entry
            balls = await BallInstance.filter(player__discord_id=entry)
            ball = random.choice(balls)
            # Get the ball's attack
            attack = self.get_bonus(ball)
            # Subtract the attack from the boss hp
            self.boss_hp -= attack
            # Add the ball to the attack message
            attack_msg += f"{ball.name} attacked the boss for {attack} damage!\n"
            if self.boss_hp <= 0:
                attack_msg += f"The boss has been defeated! {ball.name} has won the boss battle, this ball was played by <@{entry}>!"
                break
        # Send the attack message
        file = BytesIO(attack_msg.encode("utf-8"))
        await interaction.response.followup(file=discord.File(file, "attack.txt"))

        
            


