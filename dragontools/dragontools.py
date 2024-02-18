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
        default_guild = {"verbalwarning": {}}
        self.config.register_global(**default)
        self.config.register_guild(**default_guild)

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

    @commands.command(alias=["verbalwarn"])
    @commands.mod()
    async def vwarn(self, ctx, user: discord.Member, *, reason):
        """Issue a verbal warning to a user."""
        await ctx.send(f"{user.mention} has been issued a verbal warning for {reason}")
        await user.send(f"You have been given a verbal warning in {ctx.guild.name} for {reason}.\nPlease take this as a warning and ensure you follow the rules in the future. If you have any questions or concerns, please reach out to a moderator or admin. Thank you.")
        async with self.config.guild(ctx.guild).verbalwarning() as verbalwarning:
            if str(user.id) not in verbalwarning:
                verbalwarning[str(user.id)] = []
            case = {"reason": reason, "mod": ctx.author.id, "time": ctx.message.created_at}
            verbalwarning[str(user.id)].append(case)

    @commands.command()
    @commands.mod()
    async def listvwarns(self, ctx, user: discord.Member):
        """List all verbal warnings for a user."""
        verbalwarning = await self.config.guild(ctx.guild).verbalwarning()
        if str(user.id) not in verbalwarning:
            return await ctx.send(f"{user.mention} has no verbal warnings.")
        warnings = ""
        for case in verbalwarning[str(user.id)]:
            mod = ctx.guild.get_member(case["mod"])
            warnings += f"**{case['time']}** - {case['reason']} - {mod.mention}\n"
        await ctx.send(warnings)
        


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