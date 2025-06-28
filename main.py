import discord
from discord.ext import commands
import asyncio
import datetime
import json
import random
import os

# --- CONFIG ---
DATABASE_GUILD_ID = 1310729822204465152
STORAGE_CHANNELS = {
    "warns": "warns",
    "vocaux": "config-vocaux",
    "logs": "config-logs",
    "tickets": "config-tickets"
}
AUTHORIZED_ROLE_IDS = [
    1381024798175658086,
    1381024895361876089,
    1381026002846617732,
    1381025267983712327,
    1381751348617547828,
]

intents = discord.Intents.default()
intents.messages = True
intents.guilds = True
intents.message_content = True
intents.members = True
intents.presences = True
intents.voice_states = True

bot = commands.Bot(command_prefix="+", intents=intents)

# --- STOCKAGE ---
async def get_storage_channel(name: str):
    db_guild = bot.get_guild(DATABASE_GUILD_ID)
    if not db_guild:
        return None
    for channel in db_guild.text_channels:
        if channel.name == STORAGE_CHANNELS[name]:
            return channel
    return await db_guild.create_text_channel(STORAGE_CHANNELS[name])

async def save_data(name: str, data: dict):
    channel = await get_storage_channel(name)
    if not channel:
        return
    json_data = json.dumps(data, ensure_ascii=False)
    async for message in channel.history(limit=1):
        await message.edit(content=json_data)
        return
    await channel.send(json_data)

async def load_data(name: str):
    channel = await get_storage_channel(name)
    if not channel:
        return {}
    async for message in channel.history(limit=1):
        try:
            return json.loads(message.content)
        except:
            return {}
    return {}

# --- EN MÉMOIRE ---
warns_data = {}
ticket_config = {}
log_config = {}
vocal_config = {}

# --- AUTORISATION ---
def is_authorized():
    async def predicate(ctx):
        if any(role.id in AUTHORIZED_ROLE_IDS for role in ctx.author.roles):
            return True
        await ctx.send("❌ Tu n’as pas la permission d’utiliser cette commande.")
        return False
    return commands.check(predicate)

# --- BOT READY ---
@bot.event
async def on_ready():
    print(f"✅ Connecté en tant que {bot.user}")
    global warns_data, ticket_config, log_config, vocal_config
    warns_data = await load_data("warns") or {}
    ticket_config = await load_data("tickets") or {}
    log_config = await load_data("logs") or {}
    vocal_config = await load_data("vocaux") or {}

# --- LOG SYSTEM ---
async def send_log(guild, title: str, description: str, color=discord.Color.blurple()):
    if "logs_channel_id" in log_config:
        channel = guild.get_channel(log_config["logs_channel_id"])
        if channel:
            embed = discord.Embed(title=title, description=description, color=color, timestamp=datetime.datetime.utcnow())
            embed.set_footer(text="Système de logs")
            await channel.send(embed=embed)

# --- EVENTS ---
@bot.event
async def on_message_delete(message):
    if message.guild:
        await send_log(message.guild, "🗑️ Message Supprimé", f"Message de {message.author.mention} supprimé dans {message.channel.mention} :\n```{message.content}```")

@bot.event
async def on_message_edit(before, after):
    if before.guild and before.content != after.content:
        await send_log(before.guild, "✏️ Message Modifié", f"Avant :\n```{before.content}```\nAprès :\n```{after.content}``` dans {before.channel.mention}")

@bot.event
async def on_voice_state_update(member, before, after):
    if "hub_channel_id" not in vocal_config:
        return
    if after.channel and after.channel.id == vocal_config["hub_channel_id"]:
        await create_temp_voice_channel(member)

async def create_temp_voice_channel(member):
    guild = member.guild
    hub_channel = guild.get_channel(vocal_config["hub_channel_id"])
    if not hub_channel:
        return
    category = hub_channel.category
    new_channel = await guild.create_voice_channel(f"Salon de {member.display_name}", category=category, user_limit=5)
    await member.move_to(new_channel)

    def check(m, b, a):
        return b.channel == new_channel and a.channel is None and len(new_channel.members) == 0

    try:
        await bot.wait_for('voice_state_update', check=check, timeout=300)
    finally:
        await new_channel.delete()

# --- COMMANDES ---

# Ping
@bot.command()
async def ping(ctx):
    latency = round(bot.latency * 1000)
    embed = discord.Embed(title="🏓 Pong !", description=f"**Latence :** `{latency} ms`", color=0x000000)
    await ctx.send(embed=embed)

# --- FUN COMMANDS ---

gif_kill = [
    "https://media0.giphy.com/media/v1.Y2lkPTc5MGI3NjExdHdrbXprcG91enkxaThlMDU5c3djcTBjeWo5dGlnbGViZjgzNWoyMSZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/PnhOSPReBR4F5NT5so/giphy.gif",
    "https://media4.giphy.com/media/v1.Y2lkPTc5MGI3NjExNXl2cTJ0b2FiYTUwanhja3ZjMXVjcmFwemMxNXJhMTVtMG84cW1uayZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/l4nlWhecm3qN6cYtO9/giphy.gif"
]
gif_slap = [
    "https://media.giphy.com/media/jLeyZWgtwgr2U/giphy.gif",
    "https://media.giphy.com/media/RXGNsyRb1hDJm/giphy.gif"
]
gif_hug = [
    "https://media.giphy.com/media/l2QDM9Jnim1YVILXa/giphy.gif",
    "https://media.giphy.com/media/od5H3PmEG5EVq/giphy.gif"
]
gif_kiss = [
    "https://media.giphy.com/media/G3va31oEEnIkM/giphy.gif",
    "https://media.giphy.com/media/bGm9FuBCGg4SY/giphy.gif"
]
gif_wanted = [
    "https://media4.giphy.com/media/v1.Y2lkPTc5MGI3NjExOHQzcDJ5aWYyNTNqdnVobjAxY2M0dXBzaDZrdnc1ejVia29vaXNkbyZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/l7qIhbi7amlSrLvzqk/giphy.gif",
    "https://media1.giphy.com/media/v1.Y2lkPTc5MGI3NjExeTI4N2t4cnZxZ2g2eWtlNDJ1d2YxYTBpeG5majZhcTZ1MTFkdzJhOCZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/FlQQRZL4N3N64EXzHd/giphy.gif"
]
gif_lucario = [
    "https://media1.giphy.com/media/v1.Y2lkPTc5MGI3NjExZnBwZXFscWswd3FueTR3OWZndzF3NGQ3aDY2YTRwNDZmeXloMTRuMSZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/3BwNcKOTAVWBa/giphy.gif",
    "https://media3.giphy.com/media/v1.Y2lkPTc5MGI3NjExN3NwNnozanB5djQ5a3g5anNmdGoxOHpnbjF2ZHc2MDJ0bDFtaHhhOSZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/CAMxTEYfTIIJDFZqbG/giphy.gif"
]

def get_random_gif(action):
    return random.choice({
        "kill": gif_kill,
        "slap": gif_slap,
        "hug": gif_hug,
        "kiss": gif_kiss,
        "wanted": gif_wanted,
        "lucario": gif_lucario,
    }[action])

async def action_command(ctx, action_name, default_msg, self_msg, no_target_msg):
    member = ctx.message.mentions[0] if ctx.message.mentions else None
    gif = get_random_gif(action_name)
    embed = discord.Embed(color=0x000000)
    if member:
        embed.description = self_msg.format(user=ctx.author.mention) if member == ctx.author else f"{ctx.author.mention} {default_msg} {member.mention}!"
    else:
        embed.description = no_target_msg.format(user=ctx.author.mention)
    embed.set_image(url=gif)
    await ctx.send(embed=embed)

@bot.command()
async def kill(ctx):
    await action_command(ctx, "kill", "vient de tuer", "{user} se suicide... triste.", "{user} se sent agressif mais ne vise personne...")

@bot.command()
async def slap(ctx):
    await action_command(ctx, "slap", "vient de gifler", "{user} se gifle lui-même...", "{user} cherche quelqu'un à gifler...")

@bot.command()
async def hug(ctx):
    await action_command(ctx, "hug", "fait un câlin à", "{user} se fait un câlin...", "{user} a besoin d'un câlin...")

@bot.command()
async def kiss(ctx):
    await action_command(ctx, "kiss", "embrasse", "{user} s'embrasse...", "{user} veut un bisou...")

@bot.command()
async def wanted(ctx):
    await action_command(ctx, "wanted", "cherche à capturer", "{user} est recherché!", "{user} est recherché...")

@bot.command()
async def kaze(ctx):
    embed = discord.Embed(title="/KAZE ON TOP", color=0x000000)
    await ctx.send(embed=embed)

@bot.command()
async def lucario(ctx):
    gif = get_random_gif("lucario")
    embed = discord.Embed(description=f"{ctx.author.mention} invoque Lucario!⚡", color=0x000000)
    embed.set_image(url=gif)
    await ctx.send(embed=embed)

@bot.command()
async def love(ctx, member1: discord.Member, member2: discord.Member = None):
    member2 = member2 or ctx.author
    percent = random.randint(0, 100)
    hearts = '❤️' * (percent // 10) + '🤍' * (10 - percent // 10)
    embed = discord.Embed(title="💖 Love Meter 💖", description=f"{member1.mention} + {member2.mention}: **{percent}%**", color=0x000000)
    embed.add_field(name="Score", value=hearts)
    await ctx.send(embed=embed)

@bot.command()
async def roll(ctx, max: int = 6):
    result = random.randint(1, max)
    embed = discord.Embed(title="🎲 Lancer de dé", description=f"Tu as tiré : **{result}** sur {max}", color=0x000000)
    await ctx.send(embed=embed)

@bot.command()
async def randompp(ctx):
    members = [m for m in ctx.guild.members if not m.bot and m.avatar]
    if members:
        member = random.choice(members)
        embed = discord.Embed(title=f"🎯 Avatar aléatoire : {member.display_name}", color=0x000000)
        embed.set_image(url=member.avatar.url)
        await ctx.send(embed=embed)
    else:
        await ctx.send("Aucun membre avec un avatar trouvé.")

@bot.command()
async def avatar(ctx, member: discord.Member = None):
    member = member or ctx.author
    embed = discord.Embed(title=f"🖼️ Avatar de {member.display_name}", color=0x000000)
    embed.set_image(url=member.avatar.url)
    await ctx.send(embed=embed)

@bot.command()
async def cpl(ctx, member1: discord.Member = None, member2: discord.Member = None):
    if not member1 or not member2:
        await ctx.send("💔 Tu dois mentionner **deux personnes** pour les mettre en couple.")
        return
    name1 = member1.display_name
    name2 = member2.display_name
    fusion = name1[:len(name1)//2] + name2[len(name2)//2:]
    fusion = fusion.strip()
    embed = discord.Embed(
        title="💘 Nouveau couple formé !",
        description=(
            f"{member1.mention} ❤️ {member2.mention}\n\n"
            f"✨ Ils sont désormais inséparables !\n"
            f"👶 Nom de leur enfant : **{fusion}**"
        ),
        color=0x000000
    )
    embed.set_footer(text="C'est l'amour ~", icon_url=ctx.author.avatar.url)
    await ctx.send(embed=embed)

# --- MODERATION COMMANDS ---

@bot.command()
@is_authorized()
@commands.has_permissions(manage_messages=True)
async def warn(ctx, member: discord.Member, *, reason=None):
    global warns_data
    warns_data.setdefault(str(member.id), []).append(reason or "No reason")
    await save_data("warns", warns_data)
    await ctx.send(f"⚠️ {member.mention} warned: {reason or 'No reason'}")

@bot.command()
@is_authorized()
async def checkwarn(ctx, member: discord.Member):
    warns_list = warns_data.get(str(member.id), [])
    if not warns_list:
        await ctx.send(f"{member.mention} n'a aucun warn.")
        return
    embed = discord.Embed(title=f"Warns de {member}", color=0x000000)
    for i, w in enumerate(warns_list, 1):
        embed.add_field(name=f"{i}", value=w, inline=False)
    await ctx.send(embed=embed)

@bot.command()
@is_authorized()
@commands.has_permissions(manage_messages=True)
async def clearwarn(ctx, member: discord.Member):
    global warns_data
    if str(member.id) in warns_data:
        warns_data.pop(str(member.id))
        await save_data("warns", warns_data)
    await ctx.send(f"Warns de {member.mention} supprimés.")

@bot.command()
@is_authorized()
@commands.has_permissions(manage_messages=True)
async def clear(ctx, amount: int):
    deleted = await ctx.channel.purge(limit=amount + 1)
    await ctx.send(f"🧹 {len(deleted) - 1} messages supprimés.", delete_after=5)

@bot.command()
@is_authorized()
@commands.has_permissions(ban_members=True)
async def ban(ctx, member: discord.Member, *, reason=None):
    await member.ban(reason=reason)
    await ctx.send(f"🔨 {member.mention} banni.")

@bot.command()
@is_authorized()
@commands.has_permissions(ban_members=True)
async def unban(ctx, *, name):
    try:
        nm, disc = name.split('#')
    except:
        return await ctx.send("Format invalide. Utilise `Nom#1234`")
    bans = await ctx.guild.bans()
    for ban_entry in bans:
        if (ban_entry.user.name, ban_entry.user.discriminator) == (nm, disc):
            await ctx.guild.unban(ban_entry.user)
            return await ctx.send(f"✅ Unban de {ban_entry.user} effectué.")
    await ctx.send("Utilisateur non trouvé dans la liste des bans.")

@bot.command()
@is_authorized()
async def stats(ctx):
    guild = ctx.guild
    online = sum(1 for m in guild.members if m.status != discord.Status.offline)
    voice = sum(1 for m in guild.members if m.voice and m.voice.channel)
    offline = sum(1 for m in guild.members if m.status == discord.Status.offline)
    boosts = guild.premium_subscription_count or 0

    embed = discord.Embed(
        title=f"📊 Stats du serveur {guild.name}",
        color=0x000000
    )
    embed.add_field(name="En ligne", value=str(online), inline=True)
    embed.add_field(name="En vocal", value=str(voice), inline=True)
    embed.add_field(name="Hors ligne", value=str(offline), inline=True)
    embed.add_field(name="Boosts", value=str(boosts), inline=True)
    embed.set_image(url="https://media0.giphy.com/media/v1.Y2lkPTc5MGI3NjExMWUwaDdudm01d2FwMHBxZjJ6dndjemYydndndWR4N29kem03YW01OCZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/EY630Mn0rO1cQ/giphy.gif")

    await ctx.send(embed=embed)

@bot.command()
@is_authorized()
async def nuke(ctx):
    channel = ctx.channel
    name = channel.name
    await channel.delete()
    new_channel = await ctx.guild.create_text_channel(name)
    await new_channel.send(f"{ctx.author.mention} a nuké ce channel.")

# --- DROPS ---
@bot.command()
@is_authorized()
async def drops(ctx, *, args=None):
    if not args:
        return await ctx.send("Syntaxe : `+drops <message>`")
    await ctx.send(f"📦 Nouveau drop : {args}")

# --- TICKETS (exemple simple) ---
@bot.command()
@is_authorized()
async def createticket(ctx):
    category = discord.utils.get(ctx.guild.categories, name="Tickets")
    if not category:
        category = await ctx.guild.create_category("Tickets")
    ticket_channel = await ctx.guild.create_text_channel(f"ticket-{ctx.author.name}", category=category)
    await ticket_channel.set_permissions(ctx.guild.default_role, send_messages=False, read_messages=False)
    await ticket_channel.set_permissions(ctx.author, send_messages=True, read_messages=True)
    await ctx.send(f"Ticket créé: {ticket_channel.mention}")

# --- VOCAL HUB (création vocaux temporaires) ---

@bot.command()
@is_authorized()
async def creer_vocaux(ctx):
    category = discord.utils.get(ctx.guild.categories, name="Vocaux Temporaires")
    if not category:
        category = await ctx.guild.create_category("Vocaux Temporaires")
    hub_channel = await ctx.guild.create_voice_channel("🎙️ Crée ton vocal ici !", category=category)
    vocal_config["hub_channel_id"] = hub_channel.id
    await save_data("vocaux", vocal_config)
    await ctx.send(f"Salon vocal hub créé : {hub_channel.mention}")

# --- SET LOG CHANNEL ---

@bot.command()
@is_authorized()
async def setlogs(ctx, channel: discord.TextChannel):
    log_config["logs_channel_id"] = channel.id
    await save_data("logs", log_config)
    await ctx.send(f"Channel de logs défini sur {channel.mention}")

# --- SET TICKET CATEGORY ---

@bot.command()
@is_authorized()
async def setticketcategory(ctx, category: discord.CategoryChannel):
    ticket_config["ticket_category_id"] = category.id
    await save_data("tickets", ticket_config)
    await ctx.send(f"Catégorie des tickets définie : {category.name}")

# --- SET VOICE HUB (pour vocaux temporaires) ---

@bot.command()
@is_authorized()
async def setvoicehub(ctx, channel: discord.VoiceChannel):
    vocal_config["hub_channel_id"] = channel.id
    await save_data("vocaux", vocal_config)
    await ctx.send(f"Salon vocal hub défini : {channel.mention}")

# --- RUN BOT ---
bot.run(os.getenv("DISCORD_TOKEN"))
