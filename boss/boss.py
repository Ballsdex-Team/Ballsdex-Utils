import logging
import random
import asyncio
import sys
from typing import TYPE_CHECKING

import discord
from redbot.core import commands, app_commands

from ballsdex import __version__ as ballsdex_version
from ballsdex.core.models import Ball, BallInstance, BlacklistedID
from ballsdex.core.models import balls as countryballs
from ballsdex.core.utils.tortoise import row_count_estimate
from ballsdex.settings import settings
from discord.ui import Button, View
from io import BytesIO


if TYPE_CHECKING:
    from ballsdex.core.bot import BallsDexBot

log = logging.getLogger("ballsdex.packages.boss")

roles = [1049119446372986921]
class BossView(View):
    def __init__(self, interaction: discord.Interaction, entry_list, dead_list, joinable):
        super().__init__(timeout=300)
        self.value = None
        self.interaction = interaction
        self.entry_list = entry_list
        self.dead_list = dead_list
        self.joinable = joinable

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True  # type: ignore
        try:
            await self.interaction.response.send_message("@original", view=self)  # type: ignore
        except discord.NotFound:
            pass

    @discord.ui.button(
        style=discord.ButtonStyle.success, label="Join"
    )
    async def join_button(self, interaction: discord.Interaction, button: Button):
        if not self.joinable:
            await interaction.response.send_message("The boss battle is not joinable.", ephemeral=True)
            return
        if await BlacklistedID.filter(discord_id=interaction.user.id).exists():
            await interaction.response.send_message("You are blacklisted and cannot join the boss battle.", ephemeral=True)
            return
        if (interaction.user.id, interaction.user.display_name) in self.dead_list:
            await interaction.response.send_message(f"{interaction.user.mention} is dead and cannot rejoin.", ephemeral=True)
            return
        if (interaction.user.id, interaction.user.display_name) in self.entry_list:
            self.entry_list.remove((interaction.user.id, interaction.user.display_name) )
            # reply to interaction
            await interaction.response.send_message(f"{interaction.user.mention} has left the boss battle.", ephemeral=True)
        else:
            self.entry_list.append((interaction.user.id, interaction.user.display_name) )
            # reply to interaction
            await interaction.response.send_message(f"{interaction.user.mention} has joined the boss battle.", ephemeral=True)
        
        

class Boss(commands.Cog):
    """
    Boss commandss.
    """

    def __init__(self, bot: "BallsDexBot"):
        self.bot = bot
        self.joinable = False
        self.boss = None
        self.boss_hp = 0
        self.boss_max_hp = 0
        self.boss_entries = []
        self.boss_dead = []
        self.message = None


    boss = app_commands.Group(name="boss", description="Boss management", guild_ids=[1049118743101452329])

    @boss.command()
    @app_commands.checks.has_any_role(*roles)
    async def start(self, interaction: discord.Interaction):
        """
        Start a boss.
        """
        # Create a message with a button that when pressed, adds you to boss_entries
        if self.boss is None:
            await interaction.response.send_message("There is no boss chosen.", ephemeral=True)
            return
        channel = interaction.guild.get_channel(1053050428683714642)
        while self.boss_hp > 0:
            self.joinable = True
            view = BossView(interaction, self.boss_entries, self.boss_dead, self.joinable)
            message = await channel.send("Boss round started!", view=view)
            self.message = message
            await asyncio.sleep(300)
            self.joinable = False
            await message.delete()
            if random.randint(0, 100) < 90:
                # 20 of boss entries die
                await self.end_round(interaction, channel, random.randint(0, len(self.boss_entries) / 5))
            else:
                await self.end_round(interaction, channel)
            await asyncio.sleep(5)
            

    
    @boss.command()
    @app_commands.checks.has_any_role(*roles)
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
        hp = random.randint(75000, 250000)
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
    @app_commands.checks.has_any_role(*roles)
    async def endround(self, interaction: discord.Interaction, killed: int = 0):
        """
        End the round.
        """
        # End the round
        await self.end_round(interaction, killed)

    async def end_round(self, interaction: discord.Interaction, channel, killed: int = 0):
        self.joinable = False
        await interaction.response.defer(thinking=True)
        defeated = False
        # loop through the entries and pick a random ball from each entry to attack the boss
        attack_msg = "The boss has been attacked! The following balls have attacked the boss: \n"
        for entry in self.boss_entries:
            # Choose a random ball from the entry
            balls = await BallInstance.filter(player__discord_id=entry[0]).prefetch_related("ball")
            ball = random.choice(balls)
            user = interaction.guild.get_member(entry[0])
            if user is None:
                user = await self.bot.fetch_user(entry[0])
            # Get the ball's attack
            attack = self.get_bonus(ball)
            # Subtract the attack from the boss hp
            self.boss_hp -= attack
            # Add the ball to the attack message
            attack_msg += f"{user.display_name}'s {ball.ball} attacked the boss for {attack} damage!\n"
            if self.boss_hp <= 0:
                defeated = user
                attack_msg += f"The boss has been defeated! {ball.ball} has won the boss battle, this ball was played by {user.display_name} ({entry[0]})!"
                break
        # Send the attack message
        file = BytesIO(attack_msg.encode("utf-8"))
        if defeated:
            await channel.send(file=discord.File(file, "attack.txt"), content=f"{defeated.mention} has won the boss battle!")
        else:
            content = ""
            if killed > 0:
                # random from entries, add to dead list
                dead_list = []
                for i in range(killed):
                    dead = random.choice(self.boss_entries)
                    self.boss_entries.remove(dead)
                    self.boss_dead.append(dead)
                    dead_list.append(dead)
                # add to content for each dead
                content += f"{killed} people have died!\n"
                content += "The following people have died:\n"
                for dead in dead_list:
                    content += f"<@{dead[0]}>\n"
            await channel.send(content=content, file=discord.File(file, "attack.txt"))
            # reset entries
            self.boss_entries = []
            self.joinable = True


    @boss.command()
    @app_commands.checks.has_any_role(*roles)
    async def stats(self, interaction: discord.Interaction):
        """
        Get the stats of the boss.
        """
        await interaction.response.defer(thinking=True, ephemeral=True)
        # Send a message with the boss's stats
        await interaction.followup.send(f"The boss is {self.boss} and has {self.boss_hp}/{self.boss_max_hp} hp left.")
    
    @boss.command()
    @app_commands.checks.has_any_role(*roles)
    async def info(self, interaction: discord.Interaction):
        """
        Get the stats of the boss.
        """
        await interaction.response.defer(thinking=True, ephemeral=True)
        # Send a message with the how many are enterted and how many are dead
        await interaction.followup.send(f"There are {len(self.boss_entries)} balls entered and {len(self.boss_dead)} balls dead.")

    @boss.command()
    @app_commands.checks.has_any_role(*roles)
    async def reset(self, interaction: discord.Interaction):
        """
        Reset the boss.
        """
        await interaction.response.defer(thinking=True, ephemeral=True)
        # Reset the boss
        self.boss = None
        self.boss_hp = 0
        self.boss_max_hp = 0
        self.boss_entries = []
        self.boss_dead = []
        self.joinable = False
        # Send a message saying the boss has been reset
        await interaction.followup.send(f"The boss has been reset.")
            


