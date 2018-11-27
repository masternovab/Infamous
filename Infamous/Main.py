import asyncio
import datetime
import os
import sys
import traceback
import aiohttp
import asyncpg
import discord
import random
from discord.ext import commands


initial_extensions = (
    'cogs.Developer',
    'cogs.Utility',
    'cogs.Fun',
    'cogs.Community',
    'cogs.Events',
    'cogs.Original',
    'cogs.Moderation',
    'cogs.Rpg',
    'cogs.Imagem',
    'cogs.Settings'
)


async def run():
    credentials = os.getenv('DATABASE_URL')
    db = await asyncpg.create_pool(credentials)
    prefixes = {}
    for i in await db.fetch("SELECT * FROM settings"):
        prefixes[i[0]] = i[1]

    disabled = {}
    p = []
    for i in await db.fetch("SELECT * FROM disabled"):
        p.append(i[1])
        disabled[i[0]] = p

    blocked = {}
    for i in await db.fetch("SELECT * FROM blocked"):
        blocked[i[0]] = i[1]
        
    bot = Bot(description='A community bot for the server Fame', db=db, prefixes=prefixes, 
             disabled=disabled, blocked=blocked)
    try:
        await bot.start(os.getenv('TOKEN'))
    except KeyboardInterrupt:
        await db.close()
        await bot.logout()


class Bot(commands.Bot):
    def __init__(self, **kwargs):
        super().__init__(
            command_prefix=self.get_prefix_,
            description=kwargs.pop('description'),
            max_messages=1000000,
            case_insensitive=True
        )

        self.app_info = None
        self.loop.create_task(self.load_all_extensions())
        self.loop.create_task(self.playing_status())
        self.remove_command("help")
        self.add_check(self.check_if_disabled)
        self.path = os.path.dirname(os.path.realpath(__file__))
        self.launch_time = datetime.datetime.utcnow()
        self.db = kwargs.pop("db")
        self.prefixes = kwargs.pop("prefixes")
        self.disabled_commands = kwargs.pop("disabled")
        self.blocked = kwargs.pop("blocked")
        self.lines = self.lines_of_code()
        self.session = aiohttp.ClientSession(loop=self.loop)

    async def get_prefix_(self, bot, message):
        if self.prefixes[message.guild.id]:
            prefix = [self.prefixes[message.guild.id]]
        else:
            prefix = ['>']
        return commands.when_mentioned_or(*prefix)(bot, message)

    async def load_all_extensions(self):
        await self.wait_until_ready()
        await asyncio.sleep(1)
        for extension in initial_extensions:
            try:
                self.load_extension(extension)
            except Exception:
                print(f'Failed to load extension {extension}.', file=sys.stderr)
                traceback.print_exc()
    
    def lines_of_code(self):
        # From Scragly
        count_dict = {}
        total_count = 0
        for root, dirs, files in os.walk(os.path.join(self.path)):
            for file in files:
                if file.endswith(".py"):
                    with open(os.path.join(root, file)) as f:
                        file_name = f.name
                        for i, l in enumerate(f):
                            pass
                    count_dict[file_name] = i + 1
                    total_count += i

        return total_count

    async def playing_status(self):
        await self.wait_until_ready()
        while not self.is_closed():
            await self.change_presence(activity=discord.Game(
                name='>help'
            ))

    async def on_ready(self):
        self.app_info = await self.application_info()
        print(f'Bot Online\n'
              f'Name: {self.user.name}\n'
              f'ID: {self.user.id}\n'
              f'{discord.__version__}')

    async def on_message(self, message):
        if message.author.bot:
            return
        await self.process_commands(message)
    
    async def check_if_disabled(self, ctx):
        if ctx.command.qualified_name in self.disabled_commands[ctx.guild.id]:
            raise commands.CheckFailure("I'm sorry a server moderator has disabled this command.")

        elif ctx.author.id in self.blocked:
            raise commands.CheckFailure(f"You have been blocked for: {self.blocked[ctx.author.id]}")

        return True
  
loop = asyncio.get_event_loop()
loop.run_until_complete(run())
