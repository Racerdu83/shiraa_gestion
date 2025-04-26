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

# --- Chargement/Sauvegarde Configs ---
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

ticket_config = {"category_id": None, "support_role_id": None}
log_config = {"logs_channel_id": None}

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

# --- Logs ---
async def send_log(guild, title: str, description: str, color=discord.Color.blurple()):
    if log_config["logs_channel_id"]:
        logs_channel = guild.get_channel(log_config["logs_channel_id"])
        if logs_channel:
            embed = discord.Embed(title=title, description=description, color=color, timestamp=datetime.datetime.utcnow())
            embed.set_footer(text="Système de logs")
            await logs_channel.send(embed=embed)

# --- Système de Tickets ---
class CloseTicketView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Fermer le ticket", style=discord.ButtonStyle.danger)
    async def close(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.channel.name.startswith("ticket-"):
            await send_log(interaction.guild, "🎟️ Fermeture de ticket", f"Ticket {interaction.channel.name} fermé par {interaction.user.mention}", color=discord.Color.red())
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
    if not category:
        await interaction.response.send_message("La catégorie de tickets est introuvable.", ephemeral=True)
        return

    overwrites = {
        interaction.guild.default_role: discord.PermissionOverwrite(read_messages=False),
        interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
        interaction.guild.get_role(ticket_config["support_role_id"]): discord.PermissionOverwrite(read_messages=True, send_messages=True)
    }

    ticket_channel = await category.create_text_channel(name=f"ticket-{interaction.user.name}", overwrites=overwrites)

    embed = discord.Embed(
        title="🌛 Ticket de Support",
        description=f"Bonjour {interaction.user.mention}, un membre va bientôt vous aider.\nUtilisez le bouton pour fermer votre ticket.",
        color=discord.Color.blurple()
    )
    embed.set_footer(text="Système de tickets")

    view = CloseTicketView()
    await ticket_channel.send(embed=embed, view=view)

    await send_log(interaction.guild, "🌛 Nouveau Ticket", f"Ticket {ticket_channel.name} créé par {interaction.user.mention}", color=discord.Color.green())
    await interaction.response.send_message(f"Votre ticket a été créé : {ticket_channel.mention}", ephemeral=True)

# --- Vocaux Temporaires ---
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
    new_channel = await guild.create_voice_channel(name=f"Salon de {member.display_name}", category=category, user_limit=5)
    await member.move_to(new_channel)

    def check_empty_channel(m, b, a):
        return b.channel == new_channel and a.channel is None and len(new_channel.members) == 0

    try:
        await bot.wait_for('voice_state_update', check=check_empty_channel, timeout=300)
        await new_channel.delete()
    except asyncio.TimeoutError:
        await new_channel.delete()

# --- Commandes de Setup ---
@bot.tree.command(name="setup-vocaux", description="Configurer le salon pour créer les vocaux temporaires.")
@app_commands.describe(channel="Salon vocal")
async def setup_vocaux(interaction: discord.Interaction, channel: discord.VoiceChannel):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("Tu dois être administrateur.", ephemeral=True)
        return

    save_vocal_channel(channel.id)
    global CREATE_VOCAL_CHANNEL_ID
    CREATE_VOCAL_CHANNEL_ID = channel.id
    await interaction.response.send_message(f"Salon de création de vocaux configuré : {channel.mention}", ephemeral=True)

@bot.tree.command(name="setup-logs", description="Configurer le salon où les logs seront envoyés.")
@app_commands.describe(channel="Salon de logs")
async def setup_logs(interaction: discord.Interaction, channel: discord.TextChannel):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("Tu dois être administrateur.", ephemeral=True)
        return

    log_config["logs_channel_id"] = channel.id
    await interaction.response.send_message(f"Salon de logs configuré : {channel.mention}", ephemeral=True)

@bot.tree.command(name="setup-tickets", description="Configurer la catégorie et le rôle pour les tickets.")
@app_commands.describe(category="Catégorie pour les tickets", role="Rôle support")
async def setup_tickets(interaction: discord.Interaction, category: discord.CategoryChannel, role: discord.Role):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("Tu dois être administrateur.", ephemeral=True)
        return

    ticket_config["category_id"] = category.id
    ticket_config["support_role_id"] = role.id
    await interaction.response.send_message(f"Tickets configurés dans {category.name} avec {role.mention}.", ephemeral=True)

# --- Event Ready ---
@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"Connecté en tant que {bot.user} ✅")

# --- Lancement Bot ---
if __name__ == "__main__":
    TOKEN = os.getenv("TOKEN")
    if not TOKEN:
        print("Erreur: Token introuvable. As-tu mis la variable TOKEN dans Railway ?")
    else:
        bot.run(TOKEN)
