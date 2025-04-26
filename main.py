import discord
from discord.ext import commands
from discord import app_commands
from discord.ui import View, Button
import datetime

intents = discord.Intents.default()
intents.messages = True
intents.guilds = True
intents.message_content = True
intents.members = True
intents.presences = True

bot = commands.Bot(command_prefix="!", intents=intents)

# Configurations
ticket_config = {
    "category_id": None,
    "support_role_id": None
}

log_config = {
    "logs_channel_id": None
}

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

@bot.tree.command(name="ban", description="Bannir un membre")
@app_commands.describe(user="Membre à bannir", reason="Raison")
async def ban(interaction: discord.Interaction, user: discord.Member, reason: str = "Aucune raison"):
    if interaction.user.guild_permissions.ban_members:
        await user.ban(reason=reason)
        await interaction.response.send_message(f"{user.mention} a été banni !", ephemeral=True)
        await send_log(interaction.guild, "🔨 Bannissement", f"{interaction.user.mention} a **banni** {user.mention}\n**Raison :** {reason}", color=discord.Color.red())
    else:
        await interaction.response.send_message("Tu n'as pas la permission.", ephemeral=True)

@bot.tree.command(name="kick", description="Expulser un membre")
@app_commands.describe(user="Membre à expulser", reason="Raison")
async def kick(interaction: discord.Interaction, user: discord.Member, reason: str = "Aucune raison"):
    if interaction.user.guild_permissions.kick_members:
        await user.kick(reason=reason)
        await interaction.response.send_message(f"{user.mention} a été expulsé !", ephemeral=True)
        await send_log(interaction.guild, "👢 Expulsion", f"{interaction.user.mention} a **expulsé** {user.mention}\n**Raison :** {reason}", color=discord.Color.orange())
    else:
        await interaction.response.send_message("Tu n'as pas la permission.", ephemeral=True)

@bot.tree.command(name="send", description="Envoyer un message personnalisé via le bot")
@app_commands.describe(channel="Salon cible", message="Message à envoyer")
async def send(interaction: discord.Interaction, channel: discord.TextChannel, message: str):
    if interaction.user.guild_permissions.administrator:
        await channel.send(message)
        await interaction.response.send_message("Message envoyé !", ephemeral=True)
    else:
        await interaction.response.send_message("Tu n'as pas la permission.", ephemeral=True)

# --- Événements ---

@bot.event
async def on_message_edit(before, after):
    if before.author.bot:
        return
    if before.content != after.content:
        await send_log(
            before.guild,
            "✏️ Message édité",
            f"**Auteur :** {before.author.mention}\n**Salon :** {before.channel.mention}\n\n**Avant :** `{before.content}`\n**Après :** `{after.content}`",
            color=discord.Color.yellow()
        )

@bot.event
async def on_message_delete(message):
    if message.author.bot:
        return
    await send_log(
        message.guild,
        "🗑️ Message supprimé",
        f"**Auteur :** {message.author.mention}\n**Salon :** {message.channel.mention}\n\n**Contenu :** `{message.content}`",
        color=discord.Color.dark_red()
    )

# --- Lancer le bot ---

bot.run("TON_TOKEN_ICI")
