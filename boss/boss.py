import logging
import random
import asyncio
import sys
from typing import TYPE_CHECKING

import discord
from redbot.core import commands, app_commands, Config

from ballsdex import __version__ as ballsdex_version
from ballsdex.core.models import Ball, BallInstance, BlacklistedID
from ballsdex.core.models import balls as countryballs
from ballsdex.core.utils.tortoise import row_count_estimate
from ballsdex.settings import settings
from discord.ui import Button, View
from datetime import datetime, timedelta
from discord.utils import utcnow
from io import BytesIO

from .phrases import battle_phrases


if TYPE_CHECKING:
    from ballsdex.core.bot import BallsDexBot

log = logging.getLogger("red.flare.boss")

roles = [1049119446372986921]

BOSSES = {
    "Reichtangle": {
        "attack_msg": "Reichtangle has attacked! The following players have been attacked: \n",
        "defence_msg": "Reichtangle was attacked! The following balls successfully attacked: \n",
        "attack_chance": 80,
        "defence_chance": 20,
        "kill_chance": 15,
    },
    "Russian Empire": {
        "attack_msg": "The Russian Empire has attacked! The following players have been attacked: \n",
        "defence_msg": "The Russian Empire was attacked! The following balls successfully attacked: \n",
        "attack_chance": 80,
        "defence_chance": 20,
        "kill_chance": 15,
    },
    "Kalmar Union": {
        "attack_msg": "The Kalmar Union has attacked! The following players have been attacked: \n",
        "defence_msg": "The Kalmar Union was attacked! The following balls successfully attacked: \n",
        "attack_chance": 80,
        "defence_chance": 20,
        "kill_chance": 15,
    },
    "German Empire": {
        "attack_msg": "The German Empire has attacked! The following players have been attacked: \n",
        "defence_msg": "The German Empire was attacked! The following balls successfully attacked: \n",
        "attack_chance": 80,
        "defence_chance": 20,
        "kill_chance": 15,
    },
    "Antarctica": {
        "attack_msg": "Antarctica has attacked! The following players have been attacked: \n",
        "defence_msg": "Antarctica was attacked! The following balls successfully attacked: \n",
        "attack_chance": 90,
        "defence_chance": 10,
        "kill_chance": 2,
    },
    "Austria-Hungary": {
        "attack_msg": "Austria-Hungary has attacked! The following players have been attacked: \n",
        "defence_msg": "Austria-Hungary was attacked! The following balls successfully attacked: \n",
        "attack_chance": 80,
        "defence_chance": 20,
        "kill_chance": 15,
    },
    "United States": {
        "attack_msg": "The United States has attacked! The following players have been attacked: \n",
        "defence_msg": "The United States was attacked! The following balls successfully attacked: \n",
        "attack_chance": 80,
        "defence_chance": 20,
        "kill_chance": 15,
    },
    "Vatican": {
        "attack_msg": "The Vatican has attacked! The following players have been attacked: \n",
        "defence_msg": "The Vatican was attacked! The following balls successfully attacked: \n",
        "attack_chance": 80,
        "defence_chance": 20,
        "kill_chance": 3,
    },
    "Russia": {
        "attack_msg": "Russia has attacked! The following players have been attacked: \n",
        "defence_msg": "Russia was attacked! The following balls successfully attacked: \n",
        "attack_chance": 80,
        "defence_chance": 20,
        "kill_chance": 15,
    },
    "Greenland": {
        "attack_msg": "Greenland has attacked! The following players have been attacked: \n",
        "defence_msg": "Greenland was attacked! The following balls successfully attacked: \n",
        "attack_chance": 80,
        "defence_chance": 20,
        "kill_chance": 5,
    },
    "Soviet Union": {
        "attack_msg": "The Soviet Union has attacked! The following players have been attacked: \n",
        "defence_msg": "The Soviet Union was attacked! The following balls successfully attacked: \n",
        "attack_chance": 80,
        "defence_chance": 20,
        "kill_chance": 20,
    },
    "Roman Empire": {
        "attack_msg": "The Roman Empire has attacked! The following players have been attacked: \n",
        "defence_msg": "The Roman Empire was attacked! The following balls successfully attacked: \n",
        "attack_chance": 80,
        "defence_chance": 20,
        "kill_chance": 5,
    },
    "Qin": {
        "attack_msg": "Qin has attacked! The following players have been attacked: \n",
        "defence_msg": "Qin was attacked! The following balls successfully attacked: \n",
        "attack_chance": 80,
        "defence_chance": 20,
        "kill_chance": 5,
    },
    "Hunnic Empire": {
        "attack_msg": "The Hunnic Empire has attacked! The following players have been attacked: \n",
        "defence_msg": "The Hunnic Empire was attacked! The following balls successfully attacked: \n",
        "attack_chance": 80,
        "defence_chance": 20,
        "kill_chance": 5,
    },
    "British Empire": {
        "attack_msg": "The British Empire has attacked! The following players have been attacked: \n",
        "defence_msg": "The British Empire was attacked! The following balls successfully attacked: \n",
        "attack_chance": 80,
        "defence_chance": 20,
        "kill_chance": 5,
    },
    "Republic of China": {
        "attack_msg": "The Republic of China has attacked! The following players have been attacked: \n",
        "defence_msg": "The Republic of China was attacked! The following balls successfully attacked: \n",
        "attack_chance": 80,
        "defence_chance": 20,
        "kill_chance": 5,
    },
    "Japanese Empire": {
        "attack_msg": "The Japanese Empire has attacked! The following players have been attacked: \n",
        "defence_msg": "The Japanese Empire was attacked! The following balls successfully attacked: \n",
        "attack_chance": 80,
        "defence_chance": 20,
        "kill_chance": 5,
    },
}


class BossView(View):
    def __init__(
        self, interaction: discord.Interaction, entry_list, dead_list, joinable
    ):
        super().__init__(timeout=None)
        self.value = None
        self.interaction = interaction
        self.entry_list = entry_list
        self.dead_list = dead_list
        self.joinable = joinable
    

    @discord.ui.button(style=discord.ButtonStyle.success, label="Join", emoji="⚔️")
    async def join_button(self, interaction: discord.Interaction, button: Button):
        if await BlacklistedID.filter(discord_id=interaction.user.id).exists():
            await interaction.response.send_message(
                "You are blacklisted and cannot join the boss battle.", ephemeral=True
            )
            return
        # player1set = set()
        # player1balls = await BallInstance.filter(
        #     player__discord_id=interaction.user.id, ball__enbaled=True
        # ).prefetch_related("ball")
        # for ball in player1balls:
        #     player1set.add(ball.ball)
        # if len(player1set) == 0 or len(player1set) < 161:
        #     await interaction.response.send_message(
        #         "You do not have enough balls to join the boss battle.", ephemeral=True
        #     )
        #     return
        if (interaction.user.id, interaction.user.display_name) in self.dead_list:
            await interaction.response.send_message(
                f"{interaction.user.mention} is dead and cannot rejoin.", ephemeral=True
            )
            return
        if (interaction.user.id, interaction.user.display_name) in self.entry_list:
            self.entry_list.remove((interaction.user.id, interaction.user.display_name))
            # reply to interaction
            await interaction.response.send_message(
                f"{interaction.user.mention} has left the boss battle.", ephemeral=True
            )
        else:
            self.entry_list.append((interaction.user.id, interaction.user.display_name))
            # reply to interaction
            await interaction.response.send_message(
                f"{interaction.user.mention} has joined the boss battle.",
                ephemeral=True,
            )
        # edit button label


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
        self.stats = {}
        self.config = Config.get_conf(
            None, identifier=1049118743101452329, cog_name="boss"
        )
        self.config.register_user(entries=0, damage=0, kills=0, deaths=0)

    boss_management = app_commands.Group(
        name="bossadmin", description="Boss Management", guild_ids=[1049118743101452329]
    )

    boss = app_commands.Group(
        name="boss", description="Boss management", guild_ids=[1049118743101452329]
    )

    @boss_management.command()
    @app_commands.checks.has_any_role(*roles)
    async def start(self, interaction: discord.Interaction):
        """
        Start a boss.
        """
        # Create a message with a button that when pressed, adds you to boss_entries
        if self.boss is None:
            await interaction.response.send_message(
                "There is no boss chosen.", ephemeral=True
            )
            return
        await interaction.response.send_message(
            "Starting boss battle...", ephemeral=True
        )
        channel = interaction.guild.get_channel(1053050428683714642)
        log.info("Starting boss battle")
        view = BossView(interaction, self.boss_entries, self.boss_dead, self.joinable)
        role = interaction.guild.get_role(1053284063420620850)
        ten_mins = utcnow() + timedelta(minutes=10)
        relative_text = f"<t:{int(ten_mins.timestamp())}:R>"
        self.joinable = True
        message = await channel.send(
            f"{role.mention}\nA boss fight has begun, click below to join!\nThis fight will begin {relative_text}",
            view=view,
            allowed_mentions=discord.AllowedMentions(roles=True),
        )
        await asyncio.sleep(600)
        self.joinable = False
        await message.edit(content="The boss battle has begun!", view=None)
        for entry in self.boss_entries:
            boss_entries = await self.config.user_from_id(entry[0]).entries()
            await self.config.user_from_id(entry[0]).entries.set(boss_entries + 1)
        while self.boss_hp > 0:
            if len(self.boss_entries) == 0:
                await channel.send("The boss has no balls to attack, the boss has won!")
                return
            round_choice = "Defence" if random.randint(0, 100) < BOSSES[self.boss]["defence_chance"] else "Attack"
            phrase = self.send_random_phrase(round_choice)
            await channel.send(phrase)
            log.info("Starting round")
            await asyncio.sleep(15)
            loading_msg = await channel.send(
                "Round over, damage is being calculated..."
            )
            log.info("Round over, damage is being calculated...")
            # attack or defence round
            if round_choice == "Defence":
                log.info("defence round")
                await self.defence_round(interaction, channel)
            else:
                log.info("attack round")
                if random.randint(0, 100) > 80:
                    log.info("Killing entries")
                    amount = random.randint(1, int(len(self.boss_entries) / 5))
                    await self.attack_round(
                        interaction,
                        channel,
                        amount,
                    )
                else:
                    log.info("Not killing entries")
                    await self.attack_round(interaction, channel)
            await loading_msg.delete()
            ten_mins = utcnow() + timedelta(minutes=5)
            relative_text = f"<t:{int(ten_mins.timestamp())}:R>"
            await channel.send(f"\n*Next round starting in* {relative_text}")
            await asyncio.sleep(300)


    def send_random_phrase(self, type):
        phrases = battle_phrases[self.boss][type]
        return random.choice(phrases)

    @boss_management.command()
    @app_commands.checks.has_any_role(*roles)
    async def choose(self, interaction: discord.Interaction):
        """
        Choose a boss.
        """
        # Choose a boss from the the following list
        bosses = [
            "Reichtangle",
            "Russian Empire",
            "Kalmar Union",
            "German Empire",
            "Antarctica",
            "Austria-Hungary ",
            "United States",
            "Vatican",
            "Russia",
            "Greenland",
            "Soviet Union",
            "Roman Empire",
            "Qin",
            "Hunnic Empire",
            "British Empire",
            "Republic of China",
            "Japanese Empire",
        ]

        # Choose a random boss
        boss = random.choice(bosses)
        # choose a random hp
        hp = random.randint(250000, 1000000)
        # Set the boss
        self.boss = boss
        # Set the boss hp
        self.boss_hp = hp
        # Set the boss max hp
        self.boss_max_hp = hp

        # Send a message saying the boss has been chosen

        await interaction.response.send_message(
            f"The boss has been chosen! It is {boss}"
        )

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

    async def defence_round(self, interaction: discord.Interaction, channel):
        # the boss attacks back against the balls, on defence rounds a user has 20% chance to die
        # loop through the entries and pick a random ball from each entry to attack the boss
        attack_msg = BOSSES[self.boss]["attack_msg"]
        log.info("Attacking balls")

        to_die = []
        shuffled = self.boss_entries.copy()
        random.shuffle(shuffled)
        for entry in shuffled:
            if random.randint(0, 100) > BOSSES[self.boss]["kill_chance"]:
                continue
            to_die.append(entry)
            self.boss_dead.append(entry)
            user = interaction.guild.get_member(entry[0])
            if user is None:
                user = await self.bot.fetch_user(entry[0])
            attack_msg += f"{user.display_name} has died!\n"
            death_count = await self.config.user_from_id(entry[0]).deaths()
            await self.config.user_from_id(entry[0]).deaths.set(death_count + 1)
        for entry in to_die:
            self.boss_entries.remove(entry)
        io = BytesIO(attack_msg.encode("utf-8"))
        await channel.send(
            content=f"{len(to_die)} balls have died!",
            file=discord.File(io, "attack.txt"),
        )

    async def attack_round(
        self, interaction: discord.Interaction, channel, killed: int = 0
    ):
        # await interaction.response.defer(thinking=True)
        defeated = False
        # loop through the entries and pick a random ball from each entry to attack the boss
        attack_msg = BOSSES[self.boss]["defence_msg"]
        log.info("Attacking boss")
        total_atk = 0
        failed = []
        entry_list = self.boss_entries.copy()
        random.shuffle(entry_list)
        for entry in entry_list:
            user = interaction.guild.get_member(entry[0])
            if user is None:
                user = await self.bot.fetch_user(entry[0])
            # Choose a random ball from the entry
            balls = await BallInstance.filter(
                player__discord_id=entry[0]
            ).prefetch_related("ball")
            player1set = set()
            for ball in balls:
                player1set.add(ball.ball)
            if len(player1set) == 0 or len(player1set) < 161:
                attack_msg += f"{user.display_name} does not have enough balls to attack the boss!\n"
                failed.append(entry)
                continue
            ball = random.choice(balls)
            # Get the ball's attack
            attack = self.get_bonus(ball)
            # Subtract the attack from the boss hp
            self.boss_hp -= attack
            # Add the ball to the attack message
            attack_msg += f"{user.display_name}'s {ball} attacked the boss for {attack} damage!\n"
            if user.id not in self.stats:
                self.stats[user.id] = []
            self.stats[user.id].append((ball, attack))
            total_atk += attack
            if self.boss_hp <= 0:
                defeated = user
                attack_msg += f"The boss has been defeated! {ball} has won the boss battle, this ball was played by {user.display_name} ({entry[0]})!"
                break
        for entry in failed:
            self.boss_entries.remove(entry)
        attack_msg = (
            f"Your balls have attacked the boss for {total_atk} damage!\n" + attack_msg
        )
        log.info("Attacked boss")
        # Send the attack message
        file = BytesIO(attack_msg.encode("utf-8"))
        if defeated:
            await channel.send(
                file=discord.File(file, "attack.txt"),
                content=f"{defeated.mention} has won the boss battle!",
            )
            for entry in self.stats:
                total = 0
                for stat in self.stats[entry]:
                    total += stat[1]
                current = await self.config.user_from_id(entry).damage()
                await self.config.user_from_id(entry).damage.set(current + total)
            kill_count = await self.config.user_from_id(defeated.id).kills()
            await self.config.user_from_id(defeated.id).kills.set(kill_count + 1)
        else:
            content = ""
            if killed > 0:
                # random from entries, add to dead list
                dead_list = []
                for i in range(killed):
                    dead = random.choice(self.boss_entries)
                    if dead in dead_list:
                        continue
                    self.boss_entries.remove(dead)
                    self.boss_dead.append(dead)
                    dead_list.append(dead)
                    death_count = await self.config.user_from_id(dead[0]).deaths()
                    await self.config.user_from_id(dead[0]).deaths.set(death_count + 1)
                # add to content for each dead
                content += f"{killed} people have died!\n"
                content += "The following people have died while attacking the boss:\n"
                for dead in dead_list:
                    content += f"<@{dead[0]}>\n"
            log.info("Sending attack message")
            await channel.send(content=content, file=discord.File(file, "attack.txt"))

    @boss_management.command()
    @app_commands.checks.has_any_role(*roles)
    async def info(self, interaction: discord.Interaction):
        """
        Information on how many balls are entered and how many are dead.
        """
        await interaction.response.defer(thinking=True, ephemeral=True)
        # Send a message with the how many are enterted and how many are dead and boss hp
        await interaction.followup.send(
            f"There are {len(self.boss_entries)} players entered and {len(self.boss_dead)} players dead. The boss has {self.boss_hp}/{self.boss_max_hp} hp left."
        )

    @boss_management.command()
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

    @boss.command()
    async def stats(self, interaction: discord.Interaction):
        """Show your damage to the boss."""
        if interaction.user.id not in self.stats:
            await interaction.response.send_message(
                "You have not attacked the boss.", ephemeral=True
            )
            return
        stats = self.stats[interaction.user.id]
        total = 0
        damage_log = ""
        for stat in stats:
            total += stat[1]
            damage_log += f"{stat[0]}: {stat[1]}\n"
        io = BytesIO(damage_log.encode("utf-8"))
        file = discord.File(io, "damage.txt")
        await interaction.response.send_message(
            f"You have done {total} damage to the boss.", ephemeral=True, file=file
        )