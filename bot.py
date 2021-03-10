from discord.ext import commands
import discord
import mcstatus
import json
import asyncio
import socket
import datetime
import sys
import logging.handlers
import traceback
"""https://discord.com/api/oauth2/authorize?client_id=800421396597047326&permissions=116800&scope=bot"""
# TODO: Allow re-run of monitor_server() via command


# TODO: JUST OVERWRITE sys.stdout and sys.stderr genius
def log_exception(exc_type, value, tb):
    logger.error("", exc_info=(exc_type, value, tb))
    sys.stderr.write("Traceback (most recent call last):")
    traceback.print_tb(tb)
    sys.stderr.write(f"{str(exc_type)}: {value}")


async def dpy_log_exception(event):
    exc_info = sys.exc_info()
    logger.error("", exc_info=exc_info)
    traceback.print_exc()
    sys.stderr.write(f"{str(exc_info[0])}: {exc_info[1]}")


logger = logging.getLogger("")
logger.setLevel(logging.INFO)

file_handler = logging.handlers.TimedRotatingFileHandler("logs/bot_log.log", when="H", interval=10)
file_handler.setFormatter(logging.Formatter("[%(asctime)s] [%(levelname)s]:  %(message)s",
                                            datefmt="%m-%d-%Y %I:%M:%S %p"))
file_handler.suffix = "%m-%d-%Y.log"

stdout_handler = logging.StreamHandler(sys.stdout)
stdout_handler.setFormatter(logging.Formatter("[%(asctime)s] [%(levelname)s]:  %(message)s",
                                              datefmt="%m-%d-%Y %I:%M:%S %p"))
logger.addHandler(stdout_handler)
logger.addHandler(file_handler)

sys.excepthook = log_exception

bot = commands.Bot(command_prefix="!", activity=discord.Game(name='Prefix is =, built by Boredly!'))

bot.on_error = dpy_log_exception

with open("config.json", "r") as config_file:
    bot_config = json.load(config_file)


def get_server_status(server_ip_port):
    mc_server = mcstatus.MinecraftServer.lookup(server_ip_port)
    try:
        return mc_server.status()
    except (ConnectionRefusedError, IOError) as e:
        logger.info(e)
        return None


def get_server_query(server_ip_port):
    mc_server = mcstatus.MinecraftServer.lookup(server_ip_port)
    try:
        return mc_server.query()
    except (ConnectionResetError, socket.timeout) as e:
        logger.info(e)
        return None


@bot.event
async def on_ready():
    global monitor_task
    logger.info(f"Running as {bot.user.name}#{bot.user.discriminator}\n")
    monitor_task = bot.loop.create_task(monitor_server(True))


server_monitor_enabled = True


async def monitor_server(startup):
    logger.info(f"Monitoring server: {bot_config['monitor_server_ip']}, pinging every {bot_config['ping_interval']} "
                f"seconds.\n")

    minecraft_server_online = False
    while server_monitor_enabled:
        if bot_config["monitor_server_ip"] is None:
            logger.warning("No server to monitor, quitting monitor task\n")
            return
        else:
            try:
                # Grab the server online or offline
                server = get_server_status(bot_config["monitor_server_ip"])
                # Offline
                if server is None:
                    if minecraft_server_online is True:
                        announcement_channel = bot.get_channel(bot_config["server_monitor_channel_id"])

                        server_online_embed = discord.Embed(title="Server Offline", description=f"{bot_config['monitor_server_ip']} is now offline", color=discord.Color.red())
                        server_online_embed.add_field(name="Time", value=datetime.datetime.now().strftime("%m-%d-%Y | %I:%M:%S %p") , inline=False)

                        if not startup:
                            logger.info(f"Sending announcement for {bot_config['monitor_server_ip']} | OFFLINE")
                            await announcement_channel.send(embed=server_online_embed)
                        else:
                            logger.info(f"Skipping announcement for {bot_config['monitor_server_ip']}")

                    minecraft_server_online = False
                    logger.info(f" {bot_config['monitor_server_ip']} | OFFLINE | "
                                 f"{bot_config['ping_interval']} second intervals")

                # Online
                else:
                    server_ping = server.latency
                    logger.info(f" {bot_config['monitor_server_ip']} | ONLINE | {server_ping}ms |"
                                f"{bot_config['ping_interval']} second intervals")
                    if minecraft_server_online is False:
                        minecraft_server_online = True
                        announcement_channel = bot.get_channel(bot_config["server_monitor_channel_id"])

                        server_online_embed = discord.Embed(title="Server Online!", description=f"{bot_config['monitor_server_ip']} is online!", color=discord.Color.green())
                        server_online_embed.add_field(name="Time", value=datetime.datetime.now().strftime("%m-%d-%Y | %I:%M:%S %p"), inline=False)

                        if not startup:
                            logger.info(f"Sending announcement for {bot_config['monitor_server_ip']} | ONLINE")
                            await announcement_channel.send(embed=server_online_embed)
                        else:
                            logger.info(f"Skipping announcement for {bot_config['monitor_server_ip']}")

                # Used to ensure seamless transition on bot restart, so bot won't announce server once it is restarted
                startup = False

            except socket.gaierror:
                logger.warning(f"Invalid IP to monitor: {bot_config['monitor_server_ip']}, quitting monitor task")
                return

        await asyncio.sleep(bot_config["ping_interval"])
    logger.warning("Monitor has been disabled, ending monitor task")


@bot.command()
async def server_info(ctx, ip):
    status = get_server_status(ip)
    query = get_server_query(ip)

    info_embed = discord.Embed(title=f"Server Info for {ip}")
    info_embed.add_field(name="Player Count:", value=f"{status.players.online}")
    if query is not None:
        player_online_string = ""
        for player in query.players.names:
            player_online_string += f"{player}\n"
        if player_online_string == "":
            player_online_string = "\u200b"

        info_embed.add_field(name="Online Players:", value=player_online_string)

        plugin_string = ""
        for plugin in query.software.plugins:
            plugin_string += f"{plugin}\n"
        if plugin_string == "":
            plugin_string = "\u200b"
        info_embed.add_field(name="Plugins:", value=plugin_string, inline=False)

    await ctx.send(embed=info_embed)


@bot.command()
async def ping(ctx):
    await ctx.send(f"Pong! {ctx.message.author.mention}")


@bot.command()
@commands.is_owner()
async def config(ctx, *args):
    global bot_config
    write_args = True
    if len(args) == 0:
        write_args = False
    try:
        if args[0] not in [item for item, value in bot_config.items()]:
            await ctx.send("Invalid argument(s)!")
            write_args = False
    except IndexError:
        pass
    if len(args) == 1:
        await ctx.send("Missing argument(s)!")
        write_args = False
    elif len(args) > 2:
        await ctx.send("Too many arguments!")
        write_args = False
    else:
        if write_args:
            try:
                bot_config[args[0]] = args[1]

                bot_config["ping_interval"] = int(bot_config["ping_interval"])
                bot_config["server_monitor_channel_id"] = int(bot_config["server_monitor_channel_id"])
                bot_config["mention_role_id"] = int(bot_config["mention_role_id"])
                bot_config["server_id"] = int(bot_config["server_id"])
                logger.warning(f"Bot config changed | {bot_config}")

                with open("config.json", "w") as config_file:
                    json.dump(bot_config, config_file, indent=4)

                with open("config.json", "r") as config_file:
                    bot_config = json.load(config_file)

            except KeyError:
                await ctx.send("Invalid setting selected")

    config_embed = discord.Embed(
        title="Bot Configuration",
        description="Change mentions n' stuff"
    )
    for setting, value in bot_config.items():
        config_embed.add_field(name=str(setting), value=str(value), inline=False)
    await ctx.send(embed=config_embed)


@bot.command()
async def get_logs(ctx):
    log_file = discord.File("logs/bot_log.log", "bot_log.log")
    await ctx.send(file=log_file)


@bot.group(invoke_without_command=True)
async def server_monitor(ctx):
    await ctx.send(f"Please append one of the following: {*[command.name for command in server_monitor.commands],} to "
                   f"your command to select an option".replace("'", '"').replace("(", "").replace(")", ""))


@server_monitor.command()
async def end(ctx):
    global server_monitor_enabled
    if server_monitor_enabled is True:
        server_monitor_enabled = False
        monitor_task.cancel()
        await ctx.send(f"Ending task!")
    else:
        await ctx.send("The task has already been ended or never started.")


@server_monitor.command()
async def start(ctx):
    global server_monitor_enabled, monitor_task
    if server_monitor_enabled is False:
        server_monitor_enabled = True
        monitor_task = bot.loop.create_task(monitor_server(False))
        await ctx.send("Starting task.")
    else:
        await ctx.send("The task is already running.")


with open("token.json") as token_file:
    token = json.load(token_file)
    bot.run(token[0])
