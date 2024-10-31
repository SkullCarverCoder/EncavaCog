from enum import Enum
from pathlib import Path
from typing import List
import lavalink
from lavalink import NodeNotFound
import discord
from redbot.cogs.audio.core import Audio
from redbot.core import app_commands
from redbot.cogs.audio.audio_dataclasses import Query
from redbot.core.i18n import Translator
from redbot.cogs.audio.apis.api_utils import LavalinkCacheFetchResult

_ = Translator("Audio", Path(__file__))

class Platform(Enum):
    Youtube = "youtube"
    Soundcloud = "soundcloud"

class EncavaCog(
    Audio):

    def __init__(self, bot):
        super().__init__(bot)
        self.bot = bot

    @app_commands.command(name="play",)
    @app_commands.guild_only()
    @app_commands.describe(platform="Platform to lookup song/video")
    @app_commands.describe(query="Name of song/video")
    async def play(self, interaction: discord.Interaction, platform: Platform,  query: str):
        ctx = interaction.context
        author = interaction.user
        guild = interaction.guild
        actual_query: Query = Query.process_input(query, self.local_folder_current_path)
        guild_data = await self.config.guild(guild).all()
        if not await self.is_query_allowed(self.config, ctx, f"{actual_query}", query_obj=actual_query):
            return await self.send_embed_msg(
                ctx, title=_("Unable To Play Tracks"), description=_("That track is not allowed.")
            )
        if guild_data["dj_enabled"]:
            return await self.send_embed_msg(
                ctx,
                title=_("Unable To Play Tracks"),
                description=_("You need the DJ role to queue tracks."),
            )
        if not self._player_check(ctx):
             if self.lavalink_connection_aborted:
                msg = _("Connection to Lavalink node has failed")
                desc = None
                if await self.bot.is_owner(author):
                    desc = _("Please check your console or logs for details.")
                return await self.send_embed_msg(ctx, title=msg, description=desc)
        try:
            if (
                not self.can_join_and_speak(author.voice.channel)
                or not author.voice.channel.permissions_for(self.bot).move_members
                and self.is_vc_full(author.voice.channel)
            ):
                return await self.send_embed_msg(
                    ctx,
                    title=_("Unable To Play Tracks"),
                    description=_(
                        "I don't have permission to connect and speak in your channel."
                    ),
                )
            await lavalink.connect(
                author.voice.channel,
                self_deaf=await self.config.guild_from_id(guild.id).auto_deafen(),
            )
        except AttributeError:
            return await self.send_embed_msg(
                ctx,
                title=_("Unable To Play Tracks"),
                description=_("Connect to a voice channel first."),
            )
        except NodeNotFound:
            return await self.send_embed_msg(
                ctx,
                title=_("Unable To Play Tracks"),
                description=_("Connection to Lavalink node has not yet been established."),
            )
        player = lavalink.get_player(guild.id)
        player.store("notify_channel", interaction.channel.id)
        await self._eq_check(ctx, player)
        await self.set_player_settings(ctx)
        can_skip = await self._can_instaskip(ctx, author)
        if (not author.voice or author.voice.channel != player.channel) and not can_skip:
            return await self.send_embed_msg(
                ctx,
                title=_("Unable To Play Tracks"),
                description=_("You must be in the voice channel to use the play command."),
            )
        if platform == "youtube":
            if actual_query.is_url and actual_query.is_youtube:
                query_raw_string = actual_query.uri
            tracks: List[LavalinkCacheFetchResult] = self.api_interface.local_cache_api.lavalink.fetch_all(
                {"query": query_raw_string}
            )
            return await self.send_embed_msg(
                ctx,
                title=_("Result"),
                description="```\n" + "".join([str(track.query) for track in tracks]) + "\n```"
            )
        else:
             return await self.send_embed_msg(
                ctx,
                title=_("Unable To Play Tracks"),
                description=_("Platform not supported "),
            )