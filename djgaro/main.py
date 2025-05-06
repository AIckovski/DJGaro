from discord import Intents
from discord.ext import commands
from dotenv import load_dotenv
import logging.config
import os
from pathlib import Path
from json import loads as json_loads


load_dotenv()

TOKEN = os.environ["BOT_TOKEN"]
PROJECT_DIR = Path(__file__).parent.parent


def AllowOnlyWarrnings(record: logging.LogRecord) -> bool:
    return record.levelno == logging.WARNING


def setup_logger():
    config_file_path = PROJECT_DIR / "logger_config.json"
    with open(config_file_path, "r") as config:
        dict_config = json_loads(config.read())
        logging.config.dictConfig(dict_config)
        LOGGER = logging.getLogger("dj_garo")

        for handler in LOGGER.handlers:
            if handler.name == "stdout":
                handler.addFilter(AllowOnlyWarrnings)
                break
        return LOGGER


def main() -> int:
    LOGGER = setup_logger()

    intents = Intents().default()
    intents.messages = True
    intents.message_content = True

    bot = commands.Bot(command_prefix="!", intents=intents)

    @bot.event
    async def on_ready():
        LOGGER.info("Loading Music cog...")
        await bot.load_extension("djgaro.cogs.music")
        LOGGER.info(f"Music cog loaded successfully!")

    @bot.command()
    async def hello(ctx: commands.Context):
        await ctx.send(f"Hello there {ctx.author.name}")

    try:
        bot.run(TOKEN)
    except KeyboardInterrupt as exc:
        LOGGER.info(f"Stopping the bot...")
        bot.loop.stop()
    return 0


if __name__ == "__main__":
    exit(main())
