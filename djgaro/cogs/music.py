from enum import Enum
from typing import Any, Dict, Optional, List
from aiohttp import request
from attr import dataclass
from discord import Embed, FFmpegOpusAudio, Member, VoiceState
from discord.colour import Colour
from discord.ext.commands import Cog, Bot, command, Context
from discord.utils import get
from asyncio import to_thread as async_to_thread
import os
from urllib import parse
from validators import url as is_url
from isoduration import parse_duration
from logging import getLogger

from yt_dlp import YoutubeDL
from djgaro.utils.constants import (
    YT_API_PLAYLISTITEMS_BASE_URL,
    YT_API_VIDEODATA_URL,
    YT_API_PLAYLISTITEMS_MAX_RESULTS,
    YT_API_VIDEO_BASE_URL,
    YT_WEB_VIDEO_BASE_URL,
)


LOGGER = getLogger("dj_garo")


class LoopMode(Enum):
    NO_REPEAT = 1
    REPEAT_ONE = 2
    REPEAT_ALL = 3


@dataclass
class PlaylistItem(object):
    video_id: str = ""
    yt_url: str = ""
    raw_url: str = ""
    title: str = ""
    duration: str = ""

    def __str__(self) -> str:
        return f"{self.title} - [{self.duration}] - {self.yt_url}"


class MusicCog(Cog):

    ACODECS = ["opus"]
    ITEM_LISTING_COUNT = 5
    loop_modes = {
        "all": LoopMode.REPEAT_ALL,
        "one": LoopMode.REPEAT_ONE,
        "none": LoopMode.NO_REPEAT,
    }

    def __init__(self, bot: Bot) -> None:
        self._bot = bot
        self._dlp = YoutubeDL()
        self.stopped = False
        self.dlp_options = {}
        self.song_idx = 0
        self.playlist: List[PlaylistItem] = []
        self.voice_client = None
        self.repeat_mode = LoopMode.REPEAT_ALL

    ############################################# Event Listeners #############################################
    @Cog.listener(name="on_voice_state_update")
    async def voice_state_change(
        self, member: Member, state_before: VoiceState, state_after: VoiceState
    ) -> None:

        voice_client = get(self._bot.voice_clients, guild=member.guild)
        if voice_client:
            try:
                members = voice_client.channel.members
                if len(members) == 1 and members[0].bot == True:
                    await voice_client.disconnect(force=False)
                    self.voice_client = None
            except AttributeError:
                pass
            except Exception as error:
                LOGGER.error(f"{error}")

    ############################################# Commands ####################################################
    @command(name="join", aliases=["j", "jn"])
    async def join_voice(self, ctx: Context):
        voice_state = ctx.author.voice

        if voice_state and not ctx.voice_client:
            voice_client = await voice_state.channel.connect()
            self.voice_client = voice_client
            LOGGER.info(f"[Voice Join] - BOT connected to {voice_client.channel.name}")
        else:
            author = ctx.author.display_name
            await ctx.send(f"{author} - you are not currenty in a voice channel.")

    @command(name="leave", aliases=["lve"])
    async def leave_voice(self, ctx: Context):
        if ctx.voice_client:
            LOGGER.info(
                f"[Voice Leave] - Leaving channel {ctx.voice_client.channel.name}"
            )
            await ctx.voice_client.disconnect(force=False)
        else:
            await ctx.send(f"Not currenty in a voice channel.")

    @command(name="play", aliases=["paly"])
    async def play_audio(self, ctx: Context, *, query: str = ""):

        if not query:
            await ctx.reply(
                "Please provide search query or a youtube video url or playlist url"
            )
            return None

        voice_state = ctx.author.voice
        voice_client = ctx.voice_client
        if not voice_state:
            await ctx.reply(
                f"{ctx.author} - you must be in voice channel to use this command!"
            )
            return None

        if not voice_client:
            voice_client = await voice_state.channel.connect()

        self.voice_client = voice_client
        if voice_client.is_playing():
            self.stopped = True
            voice_client.stop()

        self.song_idx = 0
        self.stopped = False
        self.playlist = []

        def handle_finished_stream(e):
            if e:
                LOGGER.error(f"AudioStream Player Error: {e}")
            if not self.stopped:
                self._bot.loop.create_task(self._play_next_song(ctx))

            self.stopped = False

        async with ctx.channel.typing() as t:
            yt_video_ids = await self._video_ids(query=query)
            await self._init_internal_playlist(yt_video_ids)

            self.playlist[self.song_idx].raw_url = await async_to_thread(
                self._extract_raw_url, self.playlist[self.song_idx].yt_url
            )
            if not self.playlist[self.song_idx].raw_url:
                await ctx.reply(f"Sorry, no such song can be found.")
                return None

            audio_source = await FFmpegOpusAudio.from_probe(
                self.playlist[self.song_idx].raw_url
            )
            voice_client.play(audio_source, after=handle_finished_stream)

        if (self.song_idx + 1) < len(self.playlist):
            await self._fetch_next_song_url()

    @command(name="pause", aliases=["p"])
    async def pause_voice(self, ctx: Context):
        voice_state = ctx.author.voice
        voice_client = ctx.voice_client
        if not voice_state:
            await ctx.reply(
                f"{ctx.author} - you must be in voice channel to use this command!"
            )
        elif not voice_client:
            await ctx.reply(f"The bot is not in a voice channel!")
        elif not voice_client.is_playing():
            await ctx.reply(f"There's nothing to pause!")
        else:
            voice_client.pause()

    @command(name="resume", aliases=["continue", "cont", "res"])
    async def resume_voice(self, ctx: Context):
        voice_state = ctx.author.voice
        voice_client = ctx.voice_client
        if not voice_state:
            await ctx.reply(
                f"{ctx.author} - you must be in voice channel to use this command!"
            )
        elif voice_client and voice_client.is_paused():
            voice_client.resume()

    @command(name="stop", aliases=["stp", "s"])
    async def stop_voice(self, ctx: Context):
        voice_state = ctx.author.voice
        voice_client = ctx.voice_client
        if not voice_state:
            await ctx.reply(
                f"{ctx.author} - you must be in voice channel to use this command!"
            )
        elif voice_client is not None:
            LOGGER.info(
                f'[Voice Stop] - Stopping the voice streaming in voice channel "{voice_state.channel}"...'
            )
            self.stopped = True
            voice_client.stop()

    @command(name="next", aliases=["nxt", "nt"])
    async def next_song(self, ctx: Context):

        voice_client = ctx.voice_client
        if not voice_client:
            await ctx.reply("Not in a voice channel or nothing is playing!")
            return None

        if voice_client.is_playing():
            self.stopped = True
            voice_client.stop()

        await self._play_next_song(ctx, invoked_by_cmd=True)

    @command(name="previous", aliases=["prev"])
    async def previous_song(self, ctx: Context):

        voice_client = ctx.voice_client
        if not voice_client:
            await ctx.reply("Not in a voice channel or nothing is playing!")
            return None

        def handle_finished_stream(e):
            if e:
                LOGGER.error(f"AudioStream Player Error: {e}")
            if not self.stopped:
                self._bot.loop.create_task(self._play_next_song(ctx))

            self.stopped = False

        if self.song_idx > 0:
            self.song_idx -= 1
            while not self.playlist[self.song_idx].raw_url and self.song_idx > 0:
                self.song_idx -= 1
        else:
            await ctx.reply(
                f"There is no previous song, the currently playing song is first"
            )
            return None

        if voice_client.is_playing():
            self.stopped = True
            voice_client.stop()

        source_url = self.playlist[self.song_idx].raw_url
        audio_source = await FFmpegOpusAudio.from_probe(source_url)
        voice_client.play(audio_source, after=handle_finished_stream)

    @command(name="rewind", aliases=["rw", "re"])
    async def rewind_current_song(self, ctx: Context):

        voice_client = ctx.voice_client
        if not voice_client or not self.playlist:
            await ctx.reply("Not in a voice channel or nothing is playing!")
            return None

        def handle_finished_stream(e):
            if e:
                LOGGER.error(f"AudioStream Player Error: {e}")
            if not self.stopped:
                self._bot.loop.create_task(self._play_next_song(ctx))

            self.stopped = False

        if voice_client.is_playing():
            self.stopped = True
            voice_client.stop()

        source_url = self.playlist[self.song_idx].raw_url
        audio_source = await FFmpegOpusAudio.from_probe(source_url)
        voice_client.play(audio_source, after=handle_finished_stream)

    @command(name="repeat", aliases=["rpt", "rep"])
    async def set_repeat_mode(self, ctx: Context, *, repeat_mode: str = ""):
        if repeat_mode.strip().lower() not in self.loop_modes.keys():
            reply = Embed(color=0x1DC337, title="Invalid repeat mode")
            reply.add_field(name="Available modes:", value="", inline=False)
            reply.add_field(name="all", value="")
            reply.add_field(name="one", value="")
            reply.add_field(name="none", value="")
            await ctx.reply(embed=reply)
            return None

        self.repeat_mode = self.loop_modes[repeat_mode]

    @command(name="reload")
    async def reload_ext(self, ctx: Context, extension_name: str):
        extensions = [key.split(".")[-1] for key in self._bot.extensions.keys()]

        if extension_name.strip().lower() in extensions:
            LOGGER.info(f"Reloading {extension_name}...")
            await self._bot.reload_extension(f"djgaro.cogs.{extension_name}")
            LOGGER.info(f"Done reloading {extension_name}.")
            await ctx.reply("Extention successfully reloaded!")
        else:
            await ctx.reply(f"Extension with name {extension_name} cannot be found!")

    @command(name="listsongs", aliases=["ls"])
    async def list_current_song_queue(self, ctx: Context):

        if not ctx.voice_client or not self.playlist:
            await ctx.reply("Not in a voice channel or empty playlist")

        reply_embed = Embed(color=Colour.blue(), title="Playlist")
        song_count = len(self.playlist)
        song_list_cnt, half_song_cnt = (
            min(self.ITEM_LISTING_COUNT, song_count),
            min(self.ITEM_LISTING_COUNT, song_count) // 2,
        )

        for i, j in zip(range(song_list_cnt), range(-half_song_cnt, half_song_cnt + 1)):
            index = (
                max(self.song_idx + j, i)
                if self.song_idx < (song_count - half_song_cnt)
                else (song_count + i - song_list_cnt)
            )
            reply_embed.add_field(
                name=f'{'\u27a1 ' if self.song_idx == index else ''} [{index + 1}] : {self.playlist[index].title}  [{self.playlist[index].duration}]',
                value="",
                inline=False,
            )

        await ctx.send(embed=reply_embed)

    @command(name="currentsong", aliases=["cs", "lcs"])
    async def list_current_song(self, ctx: Context):
        if not ctx.voice_client or not self.playlist:
            await ctx.reply("Not in a voice channel or empty playlist!")
            return None

        reply_embed = Embed(color=Colour.blue(), title="Currently playing:")
        reply_embed.add_field(
            name=f"[{self.song_idx + 1}]: {self.playlist[self.song_idx].title}  [{self.playlist[self.song_idx].duration}]",
            value="",
        )
        await ctx.send(embed=reply_embed)

    async def _fetch_next_song_url(self):

        next_index = self.song_idx + 1
        raw_url = ""
        while True:
            raw_url = await async_to_thread(
                self._extract_raw_url, self.playlist[next_index].yt_url
            )
            if raw_url:
                break

            next_index += 1

        self.playlist[next_index].raw_url = raw_url

    async def _play_next_song(self, ctx: Context, *, invoked_by_cmd: bool = False):

        if not ctx.voice_client:
            await ctx.send("Not connected to a voice channel!")
            return None

        def handle_finished_stream(e):
            if e:
                LOGGER.error(f"AudioStream Player Error: {e}")
            if not self.stopped:
                self._bot.loop.create_task(self._play_next_song(ctx))

            self.stopped = False

        source_url = ""
        song_count = len(self.playlist)
        next_index = self.song_idx + 1

        match (self.repeat_mode):
            case LoopMode.NO_REPEAT:
                if next_index < song_count:
                    if not self.playlist[next_index].raw_url:
                        while not self.playlist[next_index].raw_url:
                            next_index += 1

                    source_url = self.playlist[next_index].raw_url
                    self.song_idx = next_index
            case LoopMode.REPEAT_ONE:
                if not invoked_by_cmd:
                    source_url = self.playlist[self.song_idx].raw_url
                elif next_index < song_count:
                    if not self.playlist[next_index].raw_url:
                        while not self.playlist[next_index].raw_url:
                            next_index += 1

                    source_url = self.playlist[next_index].raw_url
                    self.song_idx = next_index
                else:
                    self.song_idx = 0
                    source_url = self.playlist[self.song_idx].raw_url
            case LoopMode.REPEAT_ALL:
                if next_index < song_count:
                    if not self.playlist[next_index].raw_url:
                        while not self.playlist[next_index].raw_url:
                            next_index += 1

                    source_url = self.playlist[next_index].raw_url
                    self.song_idx = next_index
                else:
                    self.song_idx = 0
                    source_url = self.playlist[self.song_idx].raw_url
            case _:
                LOGGER.warning(f"Invalid LoopMode value: {self.repeat_mode}")

        if source_url:
            audio_source = await FFmpegOpusAudio.from_probe(source_url)
            ctx.voice_client.play(audio_source, after=handle_finished_stream)

        # Fetch the 'raw audio resource URL' for the next song in the list if there's none
        if (
            self.song_idx + 1 < song_count
            and not self.playlist[self.song_idx + 1].raw_url
        ):
            await self._fetch_next_song_url()

    async def _video_ids(self, query: str = "") -> list[Optional[str]]:

        video_ids = []
        if is_url(query):
            parsed_url = parse.urlparse(query)
            hostname, query_params = parsed_url.hostname, parse.parse_qs(
                parsed_url.query
            )

            if not hostname or ("youtube" not in hostname.lower()):
                LOGGER.warning(f"The provided url is not a youtube url")
                return video_ids

            if "list" in query_params:
                return await self._extract_video_ids_from_list(query_params["list"][0])
            elif "v" in query_params and not "list" in query_params:
                video_ids.append(query_params["v"][0])
                return video_ids
        else:
            json_data = await self._yt_query_results(query)

            try:
                item_id = json_data["items"][0]["id"]
                if item_id["kind"].split("#")[-1] == "video":
                    video_ids.append(item_id["videoId"])
                elif item_id["kind"].split("#")[-1] == "playlist":
                    playlist_id = item_id["playlistId"]
                    video_ids_from_list = await self._extract_video_ids_from_list(
                        playlist_id
                    )
                    video_ids.extend(video_ids_from_list)

            except AttributeError as e:
                LOGGER.error(
                    f"Attribute error while fetching data from search query: {e}"
                )
            except ValueError as e:
                LOGGER.error(f"Value error while fetching data from search query: {e}")
            except Exception as e:
                LOGGER.error(f"Error error while fetching data from search query: {e}")
                raise e

        return video_ids

    async def _yt_query_results(self, query: str):
        query_params = {
            "key": os.environ.get("YT_API_KEY"),
            "part": "snippet",
            "type": "video,playlist",
            "q": query,
            "maxResults": 5,
        }

        async with request("GET", YT_API_VIDEO_BASE_URL, params=query_params) as resp:
            if 400 <= resp.status < 600:
                LOGGER.error(f"[Fetching error]: {resp.text()}")
                return None
            return await resp.json()

    async def _extract_video_ids_from_list(
        self, yt_list_id: str = ""
    ) -> list[Optional[str]]:
        """Given a youtube playlistId, returns at most 50 video IDs from that playlist"""

        if not yt_list_id:
            return []

        params = {
            "key": os.environ.get("YT_API_KEY"),
            "playlistId": yt_list_id,
            "part": "snippet",
            "maxResults": YT_API_PLAYLISTITEMS_MAX_RESULTS,
        }

        video_ids = []
        async with request(
            "GET", url=YT_API_PLAYLISTITEMS_BASE_URL, params=params
        ) as resp:
            if 400 <= resp.status < 600:
                LOGGER.error(f"[Fetching error]: {resp.text()}")
                return []

            resp_json = await resp.json()
            try:
                for item in resp_json["items"]:
                    video_id = item["snippet"]["resourceId"]["videoId"]
                    video_ids.append(video_id)
            except AttributeError as exc:
                LOGGER.error(f"[Error while fetching videos from playlist]: {exc}")
            except Exception as exc:
                LOGGER.error(f"[Fetching error]: {exc}")

        return video_ids

    async def _fetch_video_metadata(self, yt_video_ids: List[str] = []) -> Dict | None:
        """Fetches particular data for a given sequence of youtube video IDs and returns the response as a Dict"""

        query_params = {
            "key": os.environ.get("YT_API_KEY"),
            "part": "snippet,contentDetails",
            "id": ",".join(yt_video_ids),
            "maxResults": YT_API_PLAYLISTITEMS_MAX_RESULTS,
        }

        async with request(
            "GET", url=YT_API_VIDEODATA_URL, params=query_params
        ) as resp:
            if 400 <= resp.status < 600:
                LOGGER.error(f"[Fetching error]: {resp.text()}")
                return None
            return await resp.json()

    async def _init_internal_playlist(
        self, yt_video_ids: List[str | None] = []
    ) -> None:

        video_metadata_response = await self._fetch_video_metadata(
            yt_video_ids=yt_video_ids
        )

        if video_metadata_response:
            for item in video_metadata_response["items"]:
                playlist_item = PlaylistItem()
                try:
                    playlist_item.video_id = item["id"]
                    playlist_item.yt_url = YT_WEB_VIDEO_BASE_URL + item["id"]
                    playlist_item.title = item["snippet"]["title"]
                    playlist_item.duration = await self._format_yt_duration(
                        parse_duration(item["contentDetails"]["duration"])
                    )
                    self.playlist.append(playlist_item)
                except AttributeError as e:
                    LOGGER.error(f"Attribute error while fetching video metadata: {e}")
                except Exception as e:
                    LOGGER.error(f"Error while fetching video metadata: {e}")
                    raise

    def _extract_raw_url(self, video_url: str) -> str:
        """Extracts the raw audio source URL with opus encoding given the youtube video URL"""

        LOGGER.info(f"Downloading raw url for : {video_url}")
        raw_url = ""
        with self._dlp as info_extractor:
            try:
                info = info_extractor.extract_info(video_url, download=False)
                format_list = info.get("formats", None)
                if format_list:
                    for item in format_list:
                        acodec = item.get("acodec")
                        url = item.get("url")
                        if (
                            acodec in self.ACODECS
                            and url != "none"
                            and url.strip() != ""
                        ):
                            raw_url = url
                            break
            except Exception as exc:
                # yt_dlp logs the error so no need to log anything here
                # LOGGER.error(f'Error while extracting video info: {exc}')
                pass

        return raw_url

    async def _format_yt_duration(self, duration: Any) -> str:
        duration_string = ""
        time_dur = duration.time
        if time_dur.hours:
            duration_string += f"{time_dur.hours}h "
        if time_dur.minutes:
            duration_string += f"{time_dur.minutes}m "
        if time_dur.seconds:
            duration_string += f"{time_dur.seconds}s"

        return duration_string


async def setup(bot: Bot):
    await bot.add_cog(MusicCog(bot))
