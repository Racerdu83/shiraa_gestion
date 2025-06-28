import discord
from discord.ext import commands
from discord import app_commands
import datetime
import asyncio
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

async def save_data(name: str, data: str):
    channel = await get_storage_channel(name)
    if not channel:
        return
    async for message in channel.history(limit=1):
        await message.edit(content=data)
        return
    await channel.send(data)

async def load_data(name: str):
    channel = await get_storage_channel(name)
    if not channel:
        return ""
    async for message in channel.history(limit=1):
        return message.content
    return ""

# --- EN MÉMOIRE ---
warns_data = {}
ticket_config = {}
log_config = {}
vocal_config = {}

# --- AUTORISATION ---
def is_authorized():
    def check(interaction: discord.Interaction) -> bool:
        return any(role.id in AUTHORIZED_ROLE_IDS for role in interaction.user.roles)
    return app_commands.check(check)

# --- BOT READY ---
@bot.event
async def on_ready():
    print(f"Connecté en tant que {bot.user}")
    global warns_data, ticket_config, log_config, vocal_config
    warns_text = await load_data("warns")
    warns_data = json.loads(warns_text) if warns_text else {}
    ticket_text = await load_data("tickets")
    ticket_config = json.loads(ticket_text) if ticket_text else {}
    log_text = await load_data("logs")
    log_config = json.loads(log_text) if log_text else {}
    vocal_text = await load_data("vocaux")
    vocal_config = json.loads(vocal_text) if vocal_text else {}

    # Synchronisation slash commands uniquement sur un serveur de test (optionnel)
    # await bot.tree.sync(guild=discord.Object(id=YOUR_TEST_GUILD_ID))  
    # ou global sync (peut prendre jusqu'à 1h pour apparaître)
    await bot.tree.sync()  
    print("Slash commands synchronisées.")

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

# --- UTILITAIRE FUN ---
gif_dict = {
    "kill": ["https://media0.giphy.com/media/v1.Y2lkPTc5MGI3NjExdHdrbXprcG91enkxaThlMDU5c3djcTBjeWo5dGlnbGViZjgzNWoyMSZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/PnhOSPReBR4F5NT5so/giphy.gif",
             "https://media4.giphy.com/media/v1.Y2lkPTc5MGI3NjExNXl2cTJ0b2FiYTUwanhja3ZjMXVjcmFwemMxNXJhMTVtMG84cW1uayZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/l4nlWhecm3qN6cYtO9/giphy.gif"],
    "slap": ["https://media.giphy.com/media/jLeyZWgtwgr2U/giphy.gif",
             "https://media.giphy.com/media/RXGNsyRb1hDJm/giphy.gif"],
    "hug": ["https://media.giphy.com/media/l2QDM9Jnim1YVILXa/giphy.gif",
            "https://media.giphy.com/media/od5H3PmEG5EVq/giphy.gif"],
    "kiss": ["https://media.giphy.com/media/G3va31oEEnIkM/giphy.gif",
             "https://media.giphy.com/media/bGm9FuBCGg4SY/giphy.gif"],
    "wanted": ["https://media4.giphy.com/media/v1.Y2lkPTc5MGI3NjExOHQzcDJ5aWYyNTNqdnVobjAxY2M0dXBzaDZrdnc1ejVia29vaXNkbyZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/l7qIhbi7amlSrLvzqk/giphy.gif",
               "https://media1.giphy.com/media/v1.Y2lkPTc5MGI3NjExeTI4N2t4cnZxZ2g2eWtlNDJ1d2YxYTBpeG5majZhcTZ1MTFkdzJhOCZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/FlQQRZL4N3N64EXzHd/giphy.gif"],
    "lucario": ["https://media1.giphy.com/media/v1.Y2lkPTc5MGI3NjExZnBwZXFscWswd3FueTR3OWZndzF3NGQ3aDY2YTRwNDZmeXloMTRuMSZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/3BwNcKOTAVWBa/giphy.gif",
                "https://media3.giphy.com/media/v1.Y2lkPTc5MGI3NjExN3NwNnozanB5djQ5a3g5anNmdGoxOHpnbjF2ZHc2MDJ0bDFtaHhhOSZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/CAMxTEYfTIIJDFZqbG/giphy.gif"]
}

def get_random_gif(action: str):
    return random.choice(gif_dict.get(action, []))

# --- COMMANDES SLASH ---

# Ping
@bot.tree.command(name="ping", description="Affiche la latence du bot")
async def ping(interaction: discord.Interaction):
    latency = round(bot.latency * 1000)
    embed = discord.Embed(title="🏓 Pong !", description=f"**Latence :** `{latency} ms`", color=0x000000)
    await interaction.response.send_message(embed=embed)

# Fun commands (kill, slap, hug, kiss, wanted, lucario)
async def action_command(interaction: discord.Interaction, action_name: str, default_msg: str, self_msg: str, no_target_msg: str, member: discord.Member = None):
    gif = get_random_gif(action_name)
    embed = discord.Embed(color=0x000000)
    if member:
        if member == interaction.user:
            embed.description = self_msg.format(user=interaction.user.mention)
        else:
            embed.description = f"{interaction.user.mention} {default_msg} {member.mention}!"
    else:
        embed.description = no_target_msg.format(user=interaction.user.mention)
    if gif:
        embed.set_image(url=gif)
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="kill", description="Commande fun : tuer quelqu'un")
@app_commands.describe(member="La personne à tuer")
async def kill(interaction: discord.Interaction, member: discord.Member = None):
    await action_command(interaction, "kill", "vient de tuer", "{user} se suicide... triste.", "{user} se sent agressif mais ne vise personne...", member)

@bot.tree.command(name="slap", description="Commande fun : gifler quelqu'un")
@app_commands.describe(member="La personne à gifler")
async def slap(interaction: discord.Interaction, member: discord.Member = None):
    await action_command(interaction, "slap", "vient de gifler", "{user} se gifle lui-même...", "{user} cherche quelqu'un à gifler...", member)

@bot.tree.command(name="hug", description="Commande fun : faire un câlin")
@app_commands.describe(member="La personne à câliner")
async def hug(interaction: discord.Interaction, member: discord.Member = None):
    await action_command(interaction, "hug", "fait un câlin à", "{user} se fait un câlin...", "{user} a besoin d'un câlin...", member)

@bot.tree.command(name="kiss", description="Commande fun : embrasser quelqu'un")
@app_commands.describe(member="La personne à embrasser")
async def kiss(interaction: discord.Interaction, member: discord.Member = None):
    await action_command(interaction, "kiss", "embrasse", "{user} s'embrasse...", "{user} veut un bisou...", member)

@bot.tree.command(name="wanted", description="Commande fun : chercher quelqu'un")
@app_commands.describe(member="La personne recherchée")
async def wanted(interaction: discord.Interaction, member: discord.Member = None):
    await action_command(interaction, "wanted", "cherche à capturer", "{user} est recherché!", "{user} est recherché...", member)

@bot.tree.command(name="lucario", description="Invoquer Lucario")
async def lucario(interaction: discord.Interaction):
    gif = get_random_gif("lucario")
    embed = discord.Embed(description=f"{interaction.user.mention} invoque Lucario!⚡", color=0x000000)
    if gif:
        embed.set_image(url=gif)
    await interaction.response.send_message(embed=embed)

# Love meter
@bot.tree.command(name="love", description="Calcule le pourcentage d'amour entre deux membres")
@app_commands.describe(member1="Premier membre", member2="Deuxième membre (optionnel)")
async def love(interaction: discord.Interaction, member1: discord.Member, member2: discord.Member = None):
    member2 = member2 or interaction.user
    percent = random.randint(0, 100)
    hearts = '❤️' * (percent // 10) + '🤍' * (10 - percent // 10)
    embed = discord.Embed(title="💖 Love Meter 💖", description=f"{member1.mention} + {member2.mention}: **{percent}%**", color=0x000000)
    embed.add_field(name="Score", value=hearts)
    await interaction.response.send_message(embed=embed)

# Embed personnalisé (restreint aux rôles autorisés)
@bot.tree.command(name="embed", description="Créer un message embed personnalisé")
@is_authorized()
@app_commands.describe(args="Texte au format Titre | Description | URL de l'image")
async def embed_cmd(interaction: discord.Interaction, *, args: str):
    parts = [p.strip() for p in args.split('|')]
    em = discord.Embed(color=0x000000)
    if len(parts) > 0:
        em.title = parts[0]
    if len(parts) > 1:
        em.description = parts[1]
    if len(parts) > 2:
        em.set_image(url=parts[2])
    await interaction.response.send_message(embed=em)

# Warn system

@bot.tree.command(name="warn", description="Warn un membre")
@is_authorized()
@app_commands.describe(member="Membre à warn", reason="Raison du warn")
async def warn(interaction: discord.Interaction, member: discord.Member, reason: str = None):
    global warns_data
    warns_data.setdefault(str(member.id), []).append(reason or "No reason")
    await save_data("warns", json.dumps(warns_data))
    await interaction.response.send_message(f"⚠️ {member.mention} warned: {reason or 'No reason'}")

@bot.tree.command(name="checkwarn", description="Voir les warns d'un membre")
@is_authorized()
@app_commands.describe(member="Membre à vérifier")
async def checkwarn(interaction: discord.Interaction, member: discord.Member):
    global warns_data
    lst = warns_data.get(str(member.id), [])
    if not lst:
        await interaction.response.send_message(f"{member.mention} n'a aucun warn.")
        return
    em = discord.Embed(title=f"Warns de {member}", color=0x000000)
    for i, w in enumerate(lst, 1):
        em.add_field(name=f"{i}", value=w, inline=False)
    await interaction.response.send_message(embed=em)

@bot.tree.command(name="clearwarn", description="Effacer les warns d'un membre")
@is_authorized()
@app_commands.describe(member="Membre dont on efface les warns")
async def clearwarn(interaction: discord.Interaction, member: discord.Member):
    global warns_data
    warns_data.pop(str(member.id), None)
    await save_data("warns", json.dumps(warns_data))
    await interaction.response.send_message(f"Warns effacés pour {member.mention}.")

# Moderation commands (clear, ban, unban, slowmode, nuke)

@bot.tree.command(name="clear", description="Supprimer un nombre de messages")
@is_authorized()
@app_commands.describe(amount="Nombre de messages à supprimer")
async def clear(interaction: discord.Interaction, amount: int):
    if not interaction.channel.permissions_for(interaction.user).manage_messages:
        await interaction.response.send_message("❌ Tu n'as pas la permission de supprimer des messages.", ephemeral=True)
        return
    deleted = await interaction.channel.purge(limit=amount)
    await interaction.response.send_message(f"🧹 {len(deleted)} messages supprimés.", ephemeral=True)

@bot.tree.command(name="ban", description="Bannir un membre")
@is_authorized()
@app_commands.describe(member="Membre à bannir", reason="Raison du ban")
async def ban(interaction: discord.Interaction, member: discord.Member, reason: str = None):
    if not interaction.guild.me.guild_permissions.ban_members:
        await interaction.response.send_message("❌ Je n'ai pas la permission de bannir.", ephemeral=True)
        return
    await member.ban(reason=reason)
    await interaction.response.send_message(f"🔨 {member.mention} banni.")

@bot.tree.command(name="unban", description="Unban un membre")
@is_authorized()
@app_commands.describe(user="Nom#0000 du membre à unban")
async def unban(interaction: discord.Interaction, user: str):
    try:
        username, discrim = user.split("#")
    except:
        await interaction.response.send_message("❗ Format incorrect, utilise Nom#0000", ephemeral=True)
        return
    banned_users = await interaction.guild.bans()
    for ban_entry in banned_users:
        if (ban_entry.user.name, ban_entry.user.discriminator) == (username, discrim):
            await interaction.guild.unban(ban_entry.user)
            await interaction.response.send_message(f"✅ Unban de {ban_entry.user.mention} effectué.")
            return
    await interaction.response.send_message("Utilisateur non trouvé en ban list.", ephemeral=True)

@bot.tree.command(name="slowmode", description="Configurer le slowmode du channel")
@is_authorized()
@app_commands.describe(seconds="Temps en secondes, 0 pour désactiver")
async def slowmode(interaction: discord.Interaction, seconds: int = 0):
    if not interaction.channel.permissions_for(interaction.user).manage_channels:
        await interaction.response.send_message("❌ Tu n'as pas la permission de modifier ce salon.", ephemeral=True)
        return
    if seconds < 0 or seconds > 21600:
        await interaction.response.send_message("❗ Le slowmode doit être entre 0 et 21600 secondes.", ephemeral=True)
        return
    await interaction.channel.edit(slowmode_delay=seconds)
    if seconds == 0:
        desc = "Slowmode désactivé"
    else:
        desc = f"Slowmode activé : {seconds} secondes entre chaque message"
    await interaction.response.send_message(desc)

@bot.tree.command(name="nuke", description="Supprimer tous les messages du salon")
@is_authorized()
async def nuke(interaction: discord.Interaction):
    if not interaction.channel.permissions_for(interaction.user).manage_channels:
        await interaction.response.send_message("❌ Tu n'as pas la permission de nuker ce salon.", ephemeral=True)
        return
    channel = interaction.channel
    new_channel = await channel.clone()
    await channel.delete()
    await new_channel.send("💥 Salon nuké !")

# Config commands (changer les salons de stockage) - restreint aux rôles autorisés

@bot.tree.command(name="setstorage", description="Définir un salon de stockage (warns, vocaux, logs, tickets)")
@is_authorized()
@app_commands.describe(type_storage="Type de stockage", channel="Salon à définir")
async def setstorage(interaction: discord.Interaction, type_storage: str, channel: discord.TextChannel):
    type_storage = type_storage.lower()
    if type_storage not in STORAGE_CHANNELS:
        await interaction.response.send_message(f"❌ Type invalide. Choisis parmi : {', '.join(STORAGE_CHANNELS.keys())}", ephemeral=True)
        return
    STORAGE_CHANNELS[type_storage] = channel.name
    # Sauvegarder la config vocaux, logs, tickets en BDD
    global vocal_config, log_config, ticket_config

    if type_storage == "vocaux":
        vocal_config["hub_channel_id"] = channel.id
        await save_data("vocaux", json.dumps(vocal_config))
    elif type_storage == "logs":
        log_config["logs_channel_id"] = channel.id
        await save_data("logs", json.dumps(log_config))
    elif type_storage == "tickets":
        ticket_config["tickets_channel_id"] = channel.id
        await save_data("tickets", json.dumps(ticket_config))

    await interaction.response.send_message(f"✅ Stockage `{type_storage}` défini sur {channel.mention}")

# --- Lancement du bot ---
bot.run(os.getenv("DISCORD_TOKEN"))
