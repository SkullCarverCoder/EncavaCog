from enum import Enum
from pathlib import Path
from typing import List
import discord.ext.commands
import lavalink
from lavalink import NodeNotFound
import discord
from redbot.cogs.audio.core import Audio
from redbot.cogs.audio.apis.interface import AudioAPIInterface
from redbot.core import app_commands, commands
from redbot.cogs.audio.audio_dataclasses import Query
from redbot.core.i18n import Translator

import discord.ext

_ = Translator("Audio", Path(__file__))


class Platform(Enum):
    Youtube = "youtube"
    Soundcloud = "soundcloud"


class EncavaCog(
        Audio):

    def __init__(self, bot) -> None:
        super().__init__(bot)
        self.bot = bot

    @app_commands.command(name="play",
        description="Query a song to be played in a voice channel from a platform you choose"
    )
    @app_commands.guild_only
    @app_commands.describe(platform="Platform to lookup song/video")
    @app_commands.describe(query="Name of song/video")
    async def play(self, interaction: discord.Interaction, platform: Platform,  query: str):
        ctx: app_commands.AppCommandContext = interaction.context
        actual_context = await commands.Context.from_interaction(interaction)
        author = interaction.user
        guild = interaction.guild
        if guild is None or isinstance(guild, bool):
            return await interaction.response.send_message(
                content="You can only run this command only inside a server"
            )
        channel = interaction.channel
        guild_data = await self.config.guild(guild).all()
        actual_query: Query = Query.process_input(query, self.local_folder_current_path)
        if not await self.is_query_allowed(self.config, 
                        channel, f"{actual_query}", query_obj=actual_query):
            return await self.send_embed_msg(
                ctx, title=_("Unable To Play Tracks"), description=_("That track is not allowed.")
            )
        if guild_data["dj_enabled"]:
            return await self.send_embed_msg(
                actual_context,
                title=_("Unable To Play Tracks"),
                description=_("You need the DJ role to queue tracks."),
            )
        if not self._player_check(actual_context):
            if self.lavalink_connection_aborted:
                msg = _("Connection to Lavalink node has failed")
                desc = None
                if await self.bot.is_owner(author):
                    desc = _("Please check your console or logs for details.")
                return await self.send_embed_msg(actual_context, title=msg, description=desc)
        try:
            if (
                not self.can_join_and_speak(author.voice.channel)
                or not author.voice.channel.permissions_for(actual_context.me).move_members
                and self.is_vc_full(author.voice.channel)
            ):
                return await self.send_embed_msg(
                    actual_context,
                    title=_("Unable To Play Tracks"),
                    description=_(
                        "I don't have permission to connect and speak in your channel."
                    ),
                )
            await lavalink.connect(
                channel=interaction.user.voice.channel,
                self_deaf=True,
            )
        except AttributeError as e:
            return await self.send_embed_msg(
                actual_context,
                title=_("Unable To Play Tracks"),
                description=_("Connect to a voice channel first."),
            )
        except NodeNotFound as e:
            return await self.send_embed_msg(
                actual_context,
                title=_("Unable To Play Tracks"),
                description=_(
                    "Connection to Lavalink node has not yet been established."),
            )
        except Exception as e:
            raise e
        player = lavalink.get_player(guild.id)
        player.store("notify_channel", interaction.channel.id)
        await self._eq_check(actual_context, player)
        await self.set_player_settings(actual_context)
        can_skip = await self._can_instaskip(actual_context, author)
        if platform == Platform.Youtube:
            tracks = await self.api_interface.fetch_track(
                ctx=actual_context,
                player=player,
                query=actual_query
            )
            return await interaction.response.send_message(f"Tracks found were the following \n: {tracks}", ephemeral=True)
        if (not author.voice or author.voice.channel != player.channel) and not can_skip:
            return await self.send_embed_msg(
                actual_context,
                title=_("Unable To Play Tracks"),
                description=_(
                    "You must be in the voice channel to use the play command."),
            )
        return await self.send_embed_msg(
            actual_context,
            title=_("Unable To Play Tracks"),
            description=_("Platform not supported "),
        )
