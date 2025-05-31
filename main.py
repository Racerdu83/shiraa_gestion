import discord
from discord.ext import commands
from discord import app_commands
from discord.ui import View, Button
import datetime
import asyncio
import os  # déjà présent

intents = discord.Intents.default()
intents.messages = True
intents.guilds = True
intents.message_content = True
intents.members = True
intents.presences = True
intents.voice_states = True

bot = commands.Bot(command_prefix="/", intents=intents)

# Garde les autres valeurs en dur
DATABASE_GUILD_ID = 1310729822204465152
STORAGE_CHANNELS = {
    "warns": "warns",
    "vocaux": "config-vocaux",
    "logs": "config-logs",
    "tickets": "config-tickets"
}
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

# Dictionnaires de configuration en mémoire
warns_data = {}
ticket_config = {}
log_config = {}
vocal_config = {}

@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"Connecté en tant que {bot.user}")

    # Charger les données depuis les salons de stockage
    import json
    global warns_data, ticket_config, log_config, vocal_config
    warns_text = await load_data("warns")
    warns_data = json.loads(warns_text) if warns_text else {}
    ticket_text = await load_data("tickets")
    ticket_config = json.loads(ticket_text) if ticket_text else {}
    log_text = await load_data("logs")
    log_config = json.loads(log_text) if log_text else {}
    vocal_text = await load_data("vocaux")
    vocal_config = json.loads(vocal_text) if vocal_text else {}

async def send_log(guild, title: str, description: str, color=discord.Color.blurple()):
    if "logs_channel_id" in log_config:
        channel = guild.get_channel(log_config["logs_channel_id"])
        if channel:
            embed = discord.Embed(title=title, description=description, color=color, timestamp=datetime.datetime.utcnow())
            embed.set_footer(text="Système de logs")
            await channel.send(embed=embed)

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

class CloseTicketView(View):
    @discord.ui.button(label="Fermer le ticket", style=discord.ButtonStyle.danger)
    async def close(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.channel.name.startswith("ticket-"):
            await send_log(interaction.guild, "🎟️ Ticket Fermé", f"{interaction.user.mention} a fermé {interaction.channel.name}")
            await interaction.channel.delete()
        else:
            await interaction.response.send_message("Ceci n'est pas un ticket.", ephemeral=True)

class CreateTicketView(View):
    @discord.ui.button(label="Créer un Ticket 🎟️", style=discord.ButtonStyle.primary)
    async def create_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        await open_ticket(interaction)

async def open_ticket(interaction: discord.Interaction):
    if not ticket_config:
        await interaction.response.send_message("Le système de ticket n'est pas configuré.", ephemeral=True)
        return
    category = interaction.guild.get_channel(ticket_config["category_id"])
    role = interaction.guild.get_role(ticket_config["support_role_id"])
    overwrites = {
        interaction.guild.default_role: discord.PermissionOverwrite(read_messages=False),
        interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
        role: discord.PermissionOverwrite(read_messages=True, send_messages=True)
    }
    channel = await category.create_text_channel(f"ticket-{interaction.user.name}", overwrites=overwrites)
    embed = discord.Embed(title="🎛️ Ticket de Support", description="Merci d'avoir ouvert un ticket !", color=discord.Color.blurple())
    await channel.send(embed=embed, view=CloseTicketView())
    await interaction.response.send_message(f"Ticket créé : {channel.mention}", ephemeral=True)
    await send_log(interaction.guild, "🎟️ Ticket Créé", f"{interaction.user.mention} a ouvert {channel.mention}")

# --- COMMANDES ADMIN ---

@bot.tree.command(name="setup-logs")
async def setup_logs(interaction: discord.Interaction, channel: discord.TextChannel):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("Permission refusée.", ephemeral=True)
        return
    log_config["logs_channel_id"] = channel.id
    import json
    await save_data("logs", json.dumps(log_config))
    await interaction.response.send_message(f"Salon de logs configuré : {channel.mention}", ephemeral=True)

@bot.tree.command(name="setup-tickets")
async def setup_tickets(interaction: discord.Interaction, category: discord.CategoryChannel, support_role: discord.Role):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("Permission refusée.", ephemeral=True)
        return
    ticket_config["category_id"] = category.id
    ticket_config["support_role_id"] = support_role.id
    import json
    await save_data("tickets", json.dumps(ticket_config))
    await interaction.response.send_message("Tickets configurés.", ephemeral=True)

@bot.tree.command(name="create-ticket-panel")
async def create_ticket_panel(interaction: discord.Interaction, channel: discord.TextChannel):
    await channel.send(embed=discord.Embed(title="Besoin d'aide ? 🎟️", description="Clique sur le bouton pour créer un ticket."), view=CreateTicketView())
    await interaction.response.send_message("Panneau envoyé.", ephemeral=True)

@bot.tree.command(name="créer-vocaux")
async def créer_vocaux(interaction: discord.Interaction, category: discord.CategoryChannel):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("Permission refusée.", ephemeral=True)
        return
    channel = await category.create_voice_channel("➕ Créer un salon")
    vocal_config["hub_channel_id"] = channel.id
    import json
    await save_data("vocaux", json.dumps(vocal_config))
    await interaction.response.send_message(f"Salon hub créé : {channel.mention}", ephemeral=True)

# --- COMMANDES MODÉRATION ---

@bot.tree.command(name="warn")
async def warn(interaction: discord.Interaction, member: discord.Member, reason: str):
    if not interaction.user.guild_permissions.moderate_members:
        await interaction.response.send_message("Tu n'as pas la permission.", ephemeral=True)
        return
    warns_data.setdefault(str(member.id), []).append({"reason": reason, "by": interaction.user.id, "timestamp": str(datetime.datetime.utcnow())})
    import json
    await save_data("warns", json.dumps(warns_data))
    await member.send(embed=discord.Embed(title=f"⚠️ Avertissement sur {interaction.guild.name}", description=f"Raison : {reason}", color=discord.Color.orange()))
    await interaction.response.send_message(f"{member.mention} a été averti.")
    await send_log(interaction.guild, "⚠️ Warn", f"{member.mention} warn pour : {reason}")

@bot.tree.command(name="unwarn")
async def unwarn(interaction: discord.Interaction, member: discord.Member, index: int):
    if not interaction.user.guild_permissions.moderate_members:
        await interaction.response.send_message("Tu n'as pas la permission.", ephemeral=True)
        return
    warns = warns_data.get(str(member.id), [])
    if 0 <= index < len(warns):
        warns.pop(index)
        import json
        await save_data("warns", json.dumps(warns_data))
        await interaction.response.send_message("Warn supprimé.")
    else:
        await interaction.response.send_message("Index invalide.", ephemeral=True)

@bot.tree.command(name="warn-list")
async def warn_list(interaction: discord.Interaction, member: discord.Member):
    warns = warns_data.get(str(member.id), [])
    if not warns:
        await interaction.response.send_message("Aucun avertissement.")
        return
    embed = discord.Embed(title=f"⚠️ Warns de {member.display_name}", color=discord.Color.orange())
    for i, warn in enumerate(warns):
        embed.add_field(name=f"Warn {i}", value=f"Raison : {warn['reason']}\nPar : <@{warn['by']}>\nDate : {warn['timestamp']}", inline=False)
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="kick")
async def kick(interaction: discord.Interaction, member: discord.Member, reason: str = "Non spécifiée"):
    if not interaction.user.guild_permissions.kick_members:
        await interaction.response.send_message("Permission refusée.", ephemeral=True)
        return
    await member.kick(reason=reason)
    await send_log(interaction.guild, "👢 Kick", f"{member.mention} kické pour : {reason}")
    await interaction.response.send_message(f"{member.mention} a été expulsé.")

@bot.tree.command(name="ban")
async def ban(interaction: discord.Interaction, member: discord.Member, reason: str = "Non spécifiée"):
    if not interaction.user.guild_permissions.ban_members:
        await interaction.response.send_message("Permission refusée.", ephemeral=True)
        return
    await member.ban(reason=reason)
    await send_log(interaction.guild, "🔨 Ban", f"{member.mention} banni pour : {reason}")
    await interaction.response.send_message(f"{member.mention} a été banni.")

# Lancement du bot avec le token depuis variable d’environnement
TOKEN = os.getenv("TOKEN")
if not TOKEN:
    print("Erreur : la variable d'environnement TOKEN n'est pas définie.")
    exit(1)

bot.run(TOKEN)
