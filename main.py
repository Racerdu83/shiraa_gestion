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
        else:
            print("Erreur : Le salon des logs n'a pas été trouvé.")
    else:
        print("Erreur : Aucun salon de logs configuré.")

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

# --- Gestion des Vocaux Temporaires ---
@bot.event
async def on_voice_state_update(member, before, after):
    if not CREATE_VOCAL_CHANNEL_ID:
        return

    # Lorsque l'utilisateur rejoint le salon de création
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

    # Attendre que le salon soit vide mais avec un timeout de 5 minutes pour éviter un blocage
    try:
        await bot.wait_for('voice_state_update', check=check_empty_channel, timeout=300)
        await new_channel.delete()
    except asyncio.TimeoutError:
        print(f"Le salon vocal {new_channel.name} n'a pas été vidé dans les 5 minutes. Suppression forcée.")
        await new_channel.delete()

# --- Commandes de Modération ---
@bot.tree.command(name="mute", description="Muet un membre")
@app_commands.describe(member="Membre à mute")
async def mute(interaction: discord.Interaction, member: discord.Member):
    if not interaction.user.guild_permissions.moderate_members:
        await interaction.response.send_message("Tu n'as pas la permission.", ephemeral=True)
        return
    await member.edit(mute=True)
    await interaction.response.send_message(f"{member.mention} a été mis en sourdine.", ephemeral=True)
    await send_log(interaction.guild, "🔇 Mute", f"{member.mention} a été muet par {interaction.user.mention}", color=discord.Color.orange())

@bot.tree.command(name="unmute", description="Démute un membre")
@app_commands.describe(member="Membre à démute")
async def unmute(interaction: discord.Interaction, member: discord.Member):
    if not interaction.user.guild_permissions.moderate_members:
        await interaction.response.send_message("Tu n'as pas la permission.", ephemeral=True)
        return
    await member.edit(mute=False)
    await interaction.response.send_message(f"{member.mention} a été démute.", ephemeral=True)
    await send_log(interaction.guild, "🔊 Unmute", f"{member.mention} a été démute par {interaction.user.mention}", color=discord.Color.green())

@bot.tree.command(name="kick", description="Expulse un membre")
@app_commands.describe(member="Membre à expulser", reason="Raison de l'expulsion")
async def kick(interaction: discord.Interaction, member: discord.Member, reason: str = "Aucune raison"):
    if interaction.user.guild_permissions.kick_members:
        await member.kick(reason=reason)
        await interaction.response.send_message(f"{member.mention} a été expulsé.", ephemeral=True)
        await send_log(interaction.guild, "👢 Expulsion", f"{member.mention} expulsé par {interaction.user.mention} pour : {reason}", color=discord.Color.red())
    else:
        await interaction.response.send_message("Tu n'as pas la permission.", ephemeral=True)

@bot.tree.command(name="ban", description="Bannir un membre")
@app_commands.describe(member="Membre à bannir", reason="Raison du bannissement")
async def ban(interaction: discord.Interaction, member: discord.Member, reason: str = "Aucune raison"):
    if interaction.user.guild_permissions.ban_members:
        await member.ban(reason=reason)
        await interaction.response.send_message(f"{member.mention} a été banni.", ephemeral=True)
        await send_log(interaction.guild, "🔨 Bannissement", f"{member.mention} banni par {interaction.user.mention} pour : {reason}", color=discord.Color.red())
    else:
        await interaction.response.send_message("Tu n'as pas la permission.", ephemeral=True)

# Lancement du bot
bot.run("MTM2NTcwOTU1MTU0NTg3NjU0MA.GQDSFZ.-sAXnp31-vjnxWnVRF5AP-V3Rmfk5XaGDvmSJA")
