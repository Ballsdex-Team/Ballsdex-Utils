import discord

from redbot.core import commands, app_commands

from discord.ui import Button, Modal, TextInput, View



class DragonTools(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

class ReportModal(Modal, title=f"Unban Appeal"):
    reason = TextInput(
        label="Reason",
        style=discord.TextStyle.short,
        placeholder="Reason for report, be as detailed as possible.",
    )

    def __init__(self, interaction, type, reported):
        super().__init__()
        self.interaction = interaction
        self.type = type
        self.reported = reported

    async def on_submit(self, interaction):
        if self.type == "message":
            embed = discord.Embed(
                title="Message Report",
                description=f"Reported by {interaction.user.mention}",
                color=discord.Color.red(),
            )
            embed.add_field(name="Reason", value=self.reason.value)
            embed.add_field(name="Reported Message", value=self.reported.jump_url, inline=False)
        else:
            embed = discord.Embed(
                title="User Report",
                description=f"Reported by {interaction.user.mention}",
                color=discord.Color.red(),
            )
            embed.add_field(name="Reason", value=self.reason.value)
            embed.add_field(name="Reported User", value=f"{self.reported.mention} ({self.reported.id})", inline=False)
        channel = interaction.guild.get_channel(519604238150664202)  
        role = interaction.guild.get_role(574008098579152918)	
        await channel.send(role.mention, embed=embed, allowed_mentions=discord.AllowedMentions(roles=True))
        await interaction.response.send_message("Report sent!", ephemeral=True)


@app_commands.context_menu(name="Report a Message")
async def report(interaction: discord.Interaction, message: discord.Message):
    await interaction.response.send_modal(ReportModal(interaction, "message", message))

@app_commands.context_menu(name="Report a User")
async def report_user(interaction: discord.Interaction, user: discord.Member):
    await interaction.response.send_modal(ReportModal(interaction, "user", user))