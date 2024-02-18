import discord

from redbot.core import commands, app_commands, Config

from discord.ui import Button, Modal, TextInput, View



class DragonTools(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=1234567890)
        default = {
            "moderation": {}
        }
        self.config.register_global(**default)

    @commands.command()
    @commands.is_owner()
    async def modstats(self, ctx):
        modstats = await self.config.moderation()
        stats = ""
        for mod in modstats:
            stats += f"**{mod}**\n"
            for key, value in mod.items():
                stats += f"{key}: {value}\n"
        await ctx.send(modstats)


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
        channel = interaction.guild.get_channel(1199046017635602533)  
        role = interaction.guild.get_role(1073775485840003102)	
        await channel.send(role.mention, embed=embed, allowed_mentions=discord.AllowedMentions(roles=True))
        await interaction.response.send_message("Report sent!", ephemeral=True)


@app_commands.context_menu(name="Report a Message")
async def report(interaction: discord.Interaction, message: discord.Message):
    await interaction.response.send_modal(ReportModal(interaction, "message", message))

@app_commands.context_menu(name="Report a User")
async def report_user(interaction: discord.Interaction, user: discord.Member):
    await interaction.response.send_modal(ReportModal(interaction, "user", user))