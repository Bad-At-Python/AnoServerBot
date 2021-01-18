from discord.ext import commands
import discord
import mcstatus
import json
import asyncio
import socket
import datetime
"""https://discord.com/api/oauth2/authorize?client_id=800421396597047326&permissions=116800&scope=bot"""

bot = commands.Bot(command_prefix="=", activity=discord.Game(name='Prefix is =, built by Boredly!'))

with open("config.json", "r") as config_file:
    bot_config = json.load(config_file)


def get_server_status(server_ip_port):
    mc_server = mcstatus.MinecraftServer.lookup(server_ip_port)

    try:
        return mc_server.status()

    except (ConnectionRefusedError, IOError):
        return False


def get_server_query(server_ip_port):
    mc_server = mcstatus.MinecraftServer.lookup(server_ip_port)

    try:
        return mc_server.query()

    except (ConnectionResetError, socket.timeout):
        return None


@bot.event
async def on_ready():
    print(f"Running as {bot.user.name}#{bot.user.discriminator}")
    startup = True
    await monitor_server(startup)


async def monitor_server(startup):
    print(f"Monitoring server: {bot_config['monitor_server_ip']}, pinging every {bot_config['ping_interval']} seconds.")

    minecraft_server_online = False
    while True:
        if bot_config["monitor_server_ip"] is None:
            print("No server to monitor, quitting monitor task")
            return
        else:
            try:
                server = get_server_status(bot_config["monitor_server_ip"])
                if server is False:
                    if minecraft_server_online is True:
                        minecraft_server_online = False
                        announcement_channel = bot.get_channel(bot_config["server_monitor_channel_id"])

                        server_online_embed = discord.Embed(title="Server Online!",
                                                            description=f"{bot_config['monitor_server_ip']} is now offline",
                                                            color=discord.Color.red())
                        server_online_embed.add_field(name="Time", value=str(datetime.datetime.now()), inline=False)

                        if not startup:
                            await announcement_channel.send(f"{bot.get_guild(bot_config['server_id']).get_role(bot_config['mention_role_id']).mention}", embed=server_online_embed)
                        else:
                            print("Skipping announcement")
                            startup = False

                    minecraft_server_online = False
                    print("offline")
                else:
                    server_ping = server.latency
                    print("online")
                    if minecraft_server_online is False:
                        minecraft_server_online = True
                        announcement_channel = bot.get_channel(bot_config["server_monitor_channel_id"])

                        server_online_embed = discord.Embed(title="Server Online!",
                                                            description=f"{bot_config['monitor_server_ip']} is online!",
                                                            color=discord.Color.green())
                        server_online_embed.add_field(name="Time", value=str(datetime.datetime.now()), inline=False)

                        if not startup:
                            await announcement_channel.send(f"{bot.get_guild(bot_config['server_id']).get_role(bot_config['mention_role_id']).mention}", embed=server_online_embed)
                        else:
                            print("Skipping announcement")
                            startup = False

            except socket.gaierror:
                print(f"Invalid IP to monitor: {bot_config['monitor_server_ip']}, quitting monitor task")
                return

        await asyncio.sleep(bot_config["ping_interval"])


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
        info_embed.add_field(name="Online Players:", value=player_online_string)
        plugin_string = ""
        for plugin in query.software.plugins:
            plugin_string += f"{plugin}\n"
        info_embed.add_field(name="Plugins:", value=plugin_string, inline=False)

    await ctx.send(embed=info_embed)


@bot.command()
async def ping(ctx):
    await ctx.send("Pong!")


@bot.command()
@commands.has_permissions(manage_guild=True)
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
                print(bot_config)

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


bot.run("ODAwNDIxMzk2NTk3MDQ3MzI2.YAR4hA._ffEIA6SQ8fJ8sWCq1LGf3MZtso")
