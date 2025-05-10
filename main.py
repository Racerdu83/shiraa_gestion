import discord
from discord.ext import commands
from discord import app_commands
from discord.ui import View, Button
import datetime
import json
import asyncio
import os

intents = discord.Intents.default()
intents.messages = True
intents.guilds = True
intents.message_content = True
intents.members = True
intents.presences = True
intents.voice_states = True

bot = commands.Bot(command_prefix="/", intents=intents)

# Chargement et sauvegarde
def load_vocal_channel():
    try:
        with open("vocal_channel_config.json", "r") as f:
            config = json.load(f)
            return config.get("vocal_channel_id", None)
    except FileNotFoundError:
        return None

def save_vocal_channel(channel_id):
    with open("vocal_channel_config.json", "w") as f:
        json.dump({"vocal_channel_id": channel_id}, f)

CREATE_VOCAL_CHANNEL_ID = load_vocal_channel()

ticket_config = {
    "category_id": None,
    "support_role_id": None
}

log_config = {
    "logs_channel_id": None
}

def load_warns():
    try:
        with open("warns.json", "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def save_warns(warns):
    with open("warns.json", "w") as f:
        json.dump(warns, f, indent=4)

warns_data = load_warns()

# Utilitaires
async def send_log(guild, title: str, description: str, color=discord.Color.blurple()):
    if log_config["logs_channel_id"]:
        logs_channel = guild.get_channel(log_config["logs_channel_id"])
        if logs_channel:
            embed = discord.Embed(
                title=title,
                description=description,
                color=color,
                timestamp=datetime.datetime.utcnow()
            )
            embed.set_footer(text="Système de logs")
            await logs_channel.send(embed=embed)

# --- EVENTS ---

@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"Connecté en tant que {bot.user}.")

@bot.event
async def on_message_delete(message):
    if message.guild:
        await send_log(message.guild, "🗑️ Message Supprimé", f"Message de {message.author.mention} supprimé dans {message.channel.mention}:\n```{message.content}```")

@bot.event
async def on_message_edit(before, after):
    if before.guild and before.content != after.content:
        await send_log(before.guild, "✏️ Message Modifié", f"Avant:\n```{before.content}```\nAprès:\n```{after.content}``` dans {before.channel.mention}")

@bot.event
async def on_voice_state_update(member, before, after):
    if CREATE_VOCAL_CHANNEL_ID is None:
        return
    if after.channel and after.channel.id == CREATE_VOCAL_CHANNEL_ID:
        await create_temp_voice_channel(member)

async def create_temp_voice_channel(member):
    guild = member.guild
    create_channel = guild.get_channel(CREATE_VOCAL_CHANNEL_ID)
    if not create_channel:
        return

    category = create_channel.category
    if not category:
        return

    new_channel = await guild.create_voice_channel(
        name=f"Salon de {member.display_name}",
        category=category,
        user_limit=5
    )

    await member.move_to(new_channel)

    def check_empty_channel(m, b, a):
        return b.channel == new_channel and a.channel is None and len(new_channel.members) == 0

    try:
        await bot.wait_for('voice_state_update', check=check_empty_channel, timeout=300)
        await new_channel.delete()
    except asyncio.TimeoutError:
        await new_channel.delete()

# --- VIEWS ---
class CloseTicketView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Fermer le ticket", style=discord.ButtonStyle.danger)
    async def close(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.channel.name.startswith("ticket-"):
            await send_log(interaction.guild, "🎟️ Ticket Fermé", f"{interaction.user.mention} a fermé {interaction.channel.name}")
            await interaction.channel.delete()
        else:
            await interaction.response.send_message("Ceci n'est pas un ticket.", ephemeral=True)

class CreateTicketView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Créer un Ticket 🎟️", style=discord.ButtonStyle.primary)
    async def create_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        await open_ticket(interaction)

async def open_ticket(interaction: discord.Interaction):
    if ticket_config["category_id"] is None or ticket_config["support_role_id"] is None:
        await interaction.response.send_message("Le système de tickets n'est pas configuré.", ephemeral=True)
        return

    category = interaction.guild.get_channel(ticket_config["category_id"])
    if not category:
        await interaction.response.send_message("Catégorie introuvable.", ephemeral=True)
        return

    overwrites = {
        interaction.guild.default_role: discord.PermissionOverwrite(read_messages=False),
        interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
        interaction.guild.get_role(ticket_config["support_role_id"]): discord.PermissionOverwrite(read_messages=True, send_messages=True)
    }

    ticket_channel = await category.create_text_channel(name=f"ticket-{interaction.user.name}", overwrites=overwrites)
    embed = discord.Embed(
        title="🎛️ Ticket de Support",
        description="Merci d'avoir ouvert un ticket, un staff va vous répondre !",
        color=discord.Color.blurple()
    )
    await ticket_channel.send(embed=embed, view=CloseTicketView())

    await interaction.response.send_message(f"Votre ticket a été créé : {ticket_channel.mention}", ephemeral=True)
    await send_log(interaction.guild, "🎟️ Ticket Créé", f"{interaction.user.mention} a ouvert {ticket_channel.mention}")

# --- COMMANDES ADMIN ---

@bot.tree.command(name="setup-vocaux", description="Configurer le salon de création vocale")
async def setup_vocaux(interaction: discord.Interaction, channel: discord.VoiceChannel):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("Permission refusée.", ephemeral=True)
        return
    save_vocal_channel(channel.id)
    global CREATE_VOCAL_CHANNEL_ID
    CREATE_VOCAL_CHANNEL_ID = channel.id
    await interaction.response.send_message(f"Salon vocal de création configuré: {channel.name}", ephemeral=True)

@bot.tree.command(name="setup-logs", description="Configurer le salon de logs")
async def setup_logs(interaction: discord.Interaction, channel: discord.TextChannel):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("Permission refusée.", ephemeral=True)
        return
    log_config["logs_channel_id"] = channel.id
    await interaction.response.send_message(f"Salon de logs configuré: {channel.mention}", ephemeral=True)

@bot.tree.command(name="setup-tickets", description="Configurer les tickets")
async def setup_tickets(interaction: discord.Interaction, category: discord.CategoryChannel, support_role: discord.Role):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("Permission refusée.", ephemeral=True)
        return
    ticket_config["category_id"] = category.id
    ticket_config["support_role_id"] = support_role.id
    await interaction.response.send_message(f"Tickets configurés pour la catégorie {category.name} et le rôle {support_role.name}.", ephemeral=True)

@bot.tree.command(name="create-ticket-panel", description="Créer le panneau de création de tickets")
async def create_ticket_panel(interaction: discord.Interaction, channel: discord.TextChannel):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("Permission refusée.", ephemeral=True)
        return
    embed = discord.Embed(
        title="Besoin d'aide ? 🎟️",
        description="Clique sur le bouton ci-dessous pour créer un ticket.",
        color=discord.Color.blurple()
    )
    await channel.send(embed=embed, view=CreateTicketView())
    await interaction.response.send_message(f"Panneau envoyé dans {channel.mention}.", ephemeral=True)

# --- COMMANDES MODERATION ---

@bot.tree.command(name="mute", description="Mute un membre")
async def mute(interaction: discord.Interaction, member: discord.Member, reason: str = "Non spécifiée"):
    if not interaction.user.guild_permissions.moderate_members:
        await interaction.response.send_message("Tu n'as pas la permission.", ephemeral=True)
        return
    await member.edit(mute=True)
    await send_log(interaction.guild, "🔇 Mute", f"{member.mention} mute par {interaction.user.mention} pour: {reason}")
    await interaction.response.send_message(f"{member.mention} est mute.")

@bot.tree.command(name="kick", description="Expulser un membre")
async def kick(interaction: discord.Interaction, member: discord.Member, reason: str = "Non spécifiée"):
    if not interaction.user.guild_permissions.kick_members:
        await interaction.response.send_message("Tu n'as pas la permission.", ephemeral=True)
        return
    await member.kick(reason=reason)
    await send_log(interaction.guild, "👢 Kick", f"{member.mention} kické par {interaction.user.mention} pour: {reason}")
    await interaction.response.send_message(f"{member.mention} a été expulsé.")

@bot.tree.command(name="ban", description="Bannir un membre")
async def ban(interaction: discord.Interaction, member: discord.Member, reason: str = "Non spécifiée"):
    if not interaction.user.guild_permissions.ban_members:
        await interaction.response.send_message("Tu n'as pas la permission.", ephemeral=True)
        return
    await member.ban(reason=reason)
    await send_log(interaction.guild, "🔨 Ban", f"{member.mention} banni par {interaction.user.mention} pour: {reason}")
    await interaction.response.send_message(f"{member.mention} a été banni.")
    # --- WARN SYSTEM --- (stockage dans un salon texte unique)

@bot.tree.command(name="warn", description="Avertir un membre")
async def warn(interaction: discord.Interaction, member: discord.Member, reason: str = "Non spécifiée"):
    if not interaction.user.guild_permissions.moderate_members:
        await interaction.response.send_message("Tu n'as pas la permission.", ephemeral=True)
        return

    guild = interaction.guild
    category_id = 1370696386785443843
    category = guild.get_channel(category_id)

    if not category:
        await interaction.response.send_message("Catégorie de stockage introuvable.", ephemeral=True)
        return

    # Vérifie ou crée le salon "warn-logs"
    warn_log_channel = discord.utils.get(category.text_channels, name="warn-logs")
    if not warn_log_channel:
        warn_log_channel = await guild.create_text_channel(
            name="warn-logs",
            category=category,
            overwrites={
                guild.default_role: discord.PermissionOverwrite(read_messages=False)
            }
        )

    embed = discord.Embed(
        title="⚠️ Avertissement",
        description=f"**Membre :** {member.mention} ({member.id})\n"
                    f"**Modérateur :** {interaction.user.mention}\n"
                    f"**Raison :** {reason}",
        color=discord.Color.orange(),
        timestamp=datetime.datetime.utcnow()
    )
    await warn_log_channel.send(embed=embed)
    await interaction.response.send_message(f"{member.mention} a été averti pour : {reason}", ephemeral=True)

@bot.tree.command(name="warns", description="Voir les avertissements d'un membre")
async def warns(interaction: discord.Interaction, member: discord.Member):
    if not interaction.user.guild_permissions.moderate_members:
        await interaction.response.send_message("Tu n'as pas la permission.", ephemeral=True)
        return

    guild = interaction.guild
    category = guild.get_channel(1370696386785443843)
    if not category:
        await interaction.response.send_message("Catégorie de stockage introuvable.", ephemeral=True)
        return

    warn_log_channel = discord.utils.get(category.text_channels, name="warn-logs")
    if not warn_log_channel:
        await interaction.response.send_message("Aucun avertissement trouvé pour ce membre.", ephemeral=True)
        return

    # Récupérer les messages du salon et filtrer ceux concernant le membre
    messages = [msg async for msg in warn_log_channel.history(limit=100)]
    warns = []

    for msg in messages:
        if msg.embeds:
            embed = msg.embeds[0]
            if f"{member.id}" in embed.description:
                warns.append(embed)

    if not warns:
        await interaction.response.send_message(f"Aucun avertissement trouvé pour {member.mention}.", ephemeral=True)
        return

    response = ""
    for i, warn in enumerate(warns[:5], start=1):  # Affiche jusqu'à 5 warns
        mod = next((line for line in warn.description.split('\n') if "Modérateur" in line), "Modérateur inconnu")
        reason = next((line for line in warn.description.split('\n') if "Raison" in line), "Raison inconnue")
        response += f"**{i}.** {mod}\n{reason}\n\n"

    await interaction.response.send_message(
        embed=discord.Embed(
            title=f"📄 Avertissements pour {member}",
            description=response,
            color=discord.Color.orange()
        ),
        ephemeral=True
    )

# --- LANCEMENT ---

bot.run(os.getenv("TOKEN"))
