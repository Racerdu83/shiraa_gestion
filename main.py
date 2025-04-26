import discord
from discord.ext import commands
from discord import app_commands
from discord.ui import View, Button
import datetime
import json
import asyncio

intents = discord.Intents.default()
intents.messages = True
intents.guilds = True
intents.message_content = True
intents.members = True
intents.presences = True
intents.voice_states = True

bot = commands.Bot(command_prefix="/", intents=intents)

# Chargement et sauvegarde de la configuration des vocaux temporaires
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

# Configurations
ticket_config = {
    "category_id": None,
    "support_role_id": None
}

log_config = {
    "logs_channel_id": None
}

# Chargement et sauvegarde des warns
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

# --- Fonctions Utiles ---
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

# --- Système de Tickets ---
class CloseTicketView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Fermer le ticket", style=discord.ButtonStyle.danger)
    async def close(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.channel.name.startswith("ticket-"):
            await send_log(interaction.guild, f"🎟️ Fermeture de ticket", f"Ticket **{interaction.channel.name}** fermé par {interaction.user.mention}", color=discord.Color.red())
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
        await interaction.response.send_message("Le système de tickets n'est pas encore configuré.", ephemeral=True)
        return

    category = interaction.guild.get_channel(ticket_config["category_id"])
    overwrites = {
        interaction.guild.default_role: discord.PermissionOverwrite(read_messages=False),
        interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
        interaction.guild.get_role(ticket_config["support_role_id"]): discord.PermissionOverwrite(read_messages=True, send_messages=True)
    }
    ticket_channel = await category.create_text_channel(name=f"ticket-{interaction.user.name}", overwrites=overwrites)

    embed = discord.Embed(
        title="🎛️ Ticket de Support",
        description=f"Bonjour {interaction.user.mention}, un membre de notre équipe va bientôt vous aider.\n\nUtilisez le bouton ci-dessous pour **fermer** votre ticket lorsque votre problème est résolu.",
        color=discord.Color.blurple()
    )
    embed.set_footer(text="Système de tickets")

    view = CloseTicketView()
    await ticket_channel.send(embed=embed, view=view)

    await send_log(interaction.guild, f"🎛️ Création de ticket", f"Ticket **{ticket_channel.name}** créé par {interaction.user.mention}", color=discord.Color.green())
    await interaction.response.send_message(f"Votre ticket a été créé : {ticket_channel.mention}", ephemeral=True)

# --- Commandes ---

@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"Connecté en tant que {bot.user}")

# Configuration des vocaux temporaires
@bot.tree.command(name="setup-vocaux", description="Configurer le salon de création des vocaux temporaires")
@app_commands.describe(channel="Salon vocal pour la création des vocaux temporaires")
async def setup_vocaux(interaction: discord.Interaction, channel: discord.VoiceChannel):
    global CREATE_VOCAL_CHANNEL_ID
    CREATE_VOCAL_CHANNEL_ID = channel.id
    save_vocal_channel(CREATE_VOCAL_CHANNEL_ID)
    await interaction.response.send_message(f"Le salon vocal de création des vocaux temporaires est maintenant {channel.mention}.", ephemeral=True)

# Fonction pour créer un salon vocal temporaire
@bot.event
async def on_voice_state_update(member, before, after):
    if not CREATE_VOCAL_CHANNEL_ID:
        return

    if after.channel and after.channel.id == CREATE_VOCAL_CHANNEL_ID:
        await create_temp_voice_channel(member)

async def create_temp_voice_channel(member):
    guild = member.guild
    category = member.guild.get_channel(CREATE_VOCAL_CHANNEL_ID).category

    new_channel = await guild.create_voice_channel(
        name=f"Salon de {member.display_name}",
        category=category,
        user_limit=5
    )

    await member.move_to(new_channel)

    def check_empty_channel(before, after):
        return before.channel == new_channel and after.channel is None and len(new_channel.members) == 0

    await bot.wait_for('voice_state_update', check=check_empty_channel)
    await new_channel.delete()

# --- Commandes Admin ---
@bot.tree.command(name="config", description="Configurer le système de tickets")
@app_commands.describe(category="Catégorie pour les tickets", support_role="Rôle support")
async def config(interaction: discord.Interaction, category: discord.CategoryChannel, support_role: discord.Role):
    if interaction.user.guild_permissions.administrator:
        ticket_config["category_id"] = category.id
        ticket_config["support_role_id"] = support_role.id
        await interaction.response.send_message("Configuration mise à jour avec succès !", ephemeral=True)
    else:
        await interaction.response.send_message("Tu n'as pas la permission.", ephemeral=True)

@bot.tree.command(name="config-logs", description="Configurer le salon de logs")
@app_commands.describe(channel="Salon de logs")
async def config_logs(interaction: discord.Interaction, channel: discord.TextChannel):
    if interaction.user.guild_permissions.administrator:
        log_config["logs_channel_id"] = channel.id
        await interaction.response.send_message(f"Salon de logs configuré : {channel.mention}", ephemeral=True)
    else:
        await interaction.response.send_message("Tu n'as pas la permission.", ephemeral=True)

@bot.tree.command(name="ticket", description="Créer un ticket manuellement")
async def ticket(interaction: discord.Interaction):
    await open_ticket(interaction)

@bot.tree.command(name="setup-ticket", description="Envoyer un panneau pour créer des tickets")
@app_commands.describe(channel="Salon", message="Message personnalisé")
async def setup_ticket(interaction: discord.Interaction, channel: discord.TextChannel, message: str):
    if interaction.user.guild_permissions.administrator:
        embed = discord.Embed(
            title="🎟️ Support Tickets",
            description=message,
            color=discord.Color.green()
        )
        embed.set_footer(text="Cliquez sur le bouton pour ouvrir un ticket.")

        view = CreateTicketView()

        await channel.send(embed=embed, view=view)
        await interaction.response.send_message(f"Panneau envoyé dans {channel.mention} ✅", ephemeral=True)
    else:
        await interaction.response.send_message("Tu n'as pas la permission.", ephemeral=True)

# --- Commandes de Modération ---

@bot.tree.command(name="warn", description="Avertir un membre")
@app_commands.describe(member="Membre à avertir", reason="Raison de l'avertissement")
async def warn(interaction: discord.Interaction, member: discord.Member, reason: str):
    if not interaction.user.guild_permissions.moderate_members:
        await interaction.response.send_message("Tu n'as pas la permission.", ephemeral=True)
        return
    warns_data.setdefault(str(member.id), []).append({"reason": reason, "moderator": str(interaction.user)})
    save_warns(warns_data)
    await interaction.response.send_message(f"{member.mention} a été averti pour : {reason}", ephemeral=True)
    await send_log(interaction.guild, "⚠️ Avertissement", f"{member.mention} averti par {interaction.user.mention} pour : {reason}")

@bot.tree.command(name="warnings", description="Voir les avertissements d'un membre")
@app_commands.describe(member="Membre à consulter")
async def warnings(interaction: discord.Interaction, member: discord.Member):
    user_warns = warns_data.get(str(member.id), [])
    if not user_warns:
        await interaction.response.send_message(f"{member.mention} n'a aucun avertissement.", ephemeral=True)
        return
    embed = discord.Embed(title=f"Avertissements de {member.display_name}", color=discord.Color.orange())
    for i, warn in enumerate(user_warns, 1):
        embed.add_field(name=f"Avertissement {i}", value=f"Raison : {warn['reason']}\nModérateur : {warn['moderator']}", inline=False)
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="unwarn", description="Retirer un avertissement")
@app_commands.describe(member="Membre", index="Numéro de l'avertissement (1, 2, etc.)")
async def unwarn(interaction: discord.Interaction, member: discord.Member, index: int):
    if not interaction.user.guild_permissions.moderate_members:
        await interaction.response.send_message("Tu n'as pas la permission.", ephemeral=True)
        return
    user_warns = warns_data.get(str(member.id), [])
    if 0 < index <= len(user_warns):
        user_warns.pop(index - 1)
        save_warns(warns_data)
        await interaction.response.send_message(f"Avertissement {index} retiré pour {member.mention}.", ephemeral=True)
    else:
        await interaction.response.send_message("Indice invalide.", ephemeral=True)

@bot.tree.command(name="ban", description="Bannir un membre")
@app_commands.describe(member="Membre à bannir", reason="Raison du bannissement")
async def ban(interaction: discord.Interaction, member: discord.Member, reason: str = "Aucune raison"):
    if interaction.user.guild_permissions.ban_members:
        await member.ban(reason=reason)
        await interaction.response.send_message(f"{member.mention} a été banni.", ephemeral=True)
        await send_log(interaction.guild, "🔨 Bannissement", f"{member.mention} banni par {interaction.user.mention} pour : {reason}")
    else:
        await interaction.response.send_message("Tu n'as pas la permission.", ephemeral=True)

@bot.tree.command(name="kick", description="Expulser un membre")
@app_commands.describe(member="Membre à expulser", reason="Raison de l'expulsion")
async def kick(interaction: discord.Interaction, member: discord.Member, reason: str = "Aucune raison"):
    if interaction.user.guild_permissions.kick_members:
        await member.kick(reason=reason)
        await interaction.response.send_message(f"{member.mention} a été expulsé.", ephemeral=True)
        await send_log(interaction.guild, "🥾 Expulsion", f"{member.mention} expulsé par {interaction.user.mention} pour : {reason}")
    else:
        await interaction.response.send_message("Tu n'as pas la permission.", ephemeral=True)

@bot.tree.command(name="mute", description="Rendre muet un membre temporairement")
@app_commands.describe(member="Membre à mute", duration="Durée en secondes", reason="Raison")
async def mute(interaction: discord.Interaction, member: discord.Member, duration: int, reason: str = "Aucune raison"):
    if interaction.user.guild_permissions.moderate_members:
        await member.timeout(duration=datetime.timedelta(seconds=duration), reason=reason)
        await interaction.response.send_message(f"{member.mention} a été mute pendant {duration} secondes.", ephemeral=True)
    else:
        await interaction.response.send_message("Tu n'as pas la permission.", ephemeral=True)

@bot.tree.command(name="unmute", description="Unmute un membre")
@app_commands.describe(member="Membre à unmute")
async def unmute(interaction: discord.Interaction, member: discord.Member):
    if interaction.user.guild_permissions.moderate_members:
        await member.timeout(None)
        await interaction.response.send_message(f"{member.mention} a été unmute.", ephemeral=True)
    else:
        await interaction.response.send_message("Tu n'as pas la permission.", ephemeral=True)

@bot.tree.command(name="clear", description="Supprimer des messages")
@app_commands.describe(amount="Nombre de messages à supprimer")
async def clear(interaction: discord.Interaction, amount: int):
    if interaction.user.guild_permissions.manage_messages:
        deleted = await interaction.channel.purge(limit=amount)
        await interaction.response.send_message(f"{len(deleted)} messages supprimés.", ephemeral=True)
    else:
        await interaction.response.send_message("Tu n'as pas la permission.", ephemeral=True)

# --- Lancer le bot ---
bot.run("MTM2NTcwOTU1MTU0NTg3NjU0MA.GQDSFZ.-sAXnp31-vjnxWnVRF5AP-V3Rmfk5XaGDvmSJA")
