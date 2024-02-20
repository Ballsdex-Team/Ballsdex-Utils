import discord

from redbot.core import commands, app_commands, Config
from redbot.core.utils.chat_formatting import pagify
from redbot.core.utils.menus import menu, DEFAULT_CONTROLS

from discord.ui import Button, Modal, TextInput, View

from datetime import datetime



class DragonTools(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=1234567890)
        default = {
            "moderation": {},
            "log_channel": None
        }
        default_guild = {"verbalwarning": {}}
        self.config.register_global(**default)
        self.config.register_guild(**default_guild)

    async def maybe_send_logs(
        self,
        guild: discord.Guild,
        mod: Union[discord.User, discord.Member],
        event: str,
        reason: str,
    ) -> None:
        """Sends a message to the log channel if it exists."""
        log_channel_id = await self.config.guild(guild).log_channel()
        if log_channel_id is None:
            return
        log_channel = guild.get_channel(log_channel_id)
        if log_channel is None:
            return
        embed = discord.Embed(
            title=f"{event}",
            description=f"{reason}",
        )
        embed.set_author(name=str(mod), icon_url=mod.avatar.url)
        await log_channel.send(embed=embed)

    @commands.admin_or_permissions(manage_guild=True)
    @commands.guild_only()
    @commands.group(name="dragonset")
    async def dragonset_group(self, ctx):
        pass

    @commands.admin_or_permissions(manage_guild=True)
    @commands.guild_only()
    @dragonset_group.command(name="logchannel")
    async def dragonset_logchannel(
        self, ctx: commands.Context, channel: discord.TextChannel
    ):
        """Set the log channel for the server."""
        await self.config.guild(ctx.guild).log_channel.set(channel.id)
        await ctx.send(f"Log channel has been set to {channel.mention}.")

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

    @commands.command(aliases=["verbalwarn"])
    @commands.mod()
    async def vwarn(self, ctx, user: discord.Member, *, reason):
        """Issue a verbal warning to a user."""
        msg = f"**{user}** has been given a verbal warning for {reason}."
        try:
            await user.send(f"You have been given a verbal warning in {ctx.guild.name} for {reason}.\nPlease take this as a warning and ensure you follow the rules in the future. If you have any questions or concerns, please reach out to a moderator or admin. Thank you.")
        except discord.Forbidden:
            msg += " (User has DMs disabled/blocked)"
        async with self.config.guild(ctx.guild).verbalwarning() as verbalwarning:
            if str(user.id) not in verbalwarning:
                verbalwarning[str(user.id)] = []
            case = {"reason": reason, "mod": ctx.author.id, "time": ctx.message.created_at.timestamp()}
            verbalwarning[str(user.id)].append(case)
        await self.maybe_send_logs(
            guild=ctx.guild,
            mod=ctx.author,
            event="Verbal Warning",
            reason=f"{user.mention} ({ctx.author.id}) has been given a verbal warning for following reason:\n{reason}"
        )
        await ctx.send(msg)

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
            warnings += f"**{datetime.fromtimestamp(case['time'])}** - {case['reason']} - {mod.mention}\n"
        embeds = []
        for page in pagify(warnings):
            embed = discord.Embed(title=f"Verbal Warnings for {user}", description=page, color=discord.Color.red())
            embeds.append(embed)

        await menu(ctx, embeds, DEFAULT_CONTROLS)
        


class ReportModal(Modal, title=f"Report User"):
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
