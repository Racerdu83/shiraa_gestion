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

# Configuration du serveur dédié pour le stockage des warns
DATABASE_GUILD_ID = 1310729822204465152
CATEGORY_ID = 1370696386785443843
WARN_CHANNEL_NAME = "warn-logs"

# --- UTILES --- 

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

def get_warns_channel(guild):
    category = guild.get_channel(CATEGORY_ID)
    if not category or not isinstance(category, discord.CategoryChannel):
        return None
    warn_channel = discord.utils.get(category.text_channels, name=WARN_CHANNEL_NAME)
    return warn_channel

async def load_warns(guild):
    warn_channel = get_warns_channel(guild)
    if warn_channel is None:
        return []

    warns = []
    async for message in warn_channel.history(limit=200):
        if '|' in message.content:
            data = message.content.split('|')
            if len(data) >= 6:
                warns.append({
                    "member_id": int(data[1]),
                    "reason": data[4],
                    "warned_by": data[3],
                    "date": data[5]
                })
    return warns

async def save_warn(guild, member_id, reason, warned_by):
    warn_channel = get_warns_channel(guild)
    if warn_channel is None:
        return

    warn_message = f"Warn | {member_id} | {warned_by} | {reason} | {datetime.datetime.utcnow()}"
    await warn_channel.send(warn_message)

# --- COMMANDES --- 

@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"Connecté en tant que {bot.user}.")

# --- COMMANDES ADMIN ---
@bot.tree.command(name="warn", description="Donner un warn à un membre")
async def warn(interaction: discord.Interaction, member: discord.Member, reason: str = "Non spécifiée"):
    if not interaction.user.guild_permissions.moderate_members:
        await interaction.response.send_message("Tu n'as pas la permission.", ephemeral=True)
        return

    # Enregistrer le warn dans le salon dédié
    await save_warn(interaction.guild, member.id, reason, interaction.user.name)
    
    # MP le membre pour l'avertir
    try:
        await member.send(
            embed=discord.Embed(
                title="Avertissement reçu",
                description=f"Vous avez été warn sur {interaction.guild.name} pour la raison suivante :\n{reason}",
                color=discord.Color.red()
            )
        )
    except discord.Forbidden:
        await interaction.response.send_message(f"{member.mention} a désactivé les messages privés, avertissement non envoyé.", ephemeral=True)

    await send_log(interaction.guild, "📛 Warn", f"{member.mention} a été warné par {interaction.user.mention} pour: {reason}")
    await interaction.response.send_message(f"{member.mention} a été warné.")

@bot.tree.command(name="warn-list", description="Voir la liste des warns d’un membre")
async def warn_list(interaction: discord.Interaction, member: discord.Member):
    if not interaction.user.guild_permissions.moderate_members:
        await interaction.response.send_message("Tu n'as pas la permission.", ephemeral=True)
        return

    warns = await load_warns(interaction.guild)

    member_warns = [warn for warn in warns if warn['member_id'] == member.id]

    if not member_warns:
        await interaction.response.send_message(f"{member.mention} n'a aucun warn.", ephemeral=True)
        return

    embed = discord.Embed(
        title=f"Liste des warns de {member.name}",
        description="Voici la liste des warns reçus :",
        color=discord.Color.red(),
        timestamp=datetime.datetime.utcnow()
    )

    for warn in member_warns:
        embed.add_field(
            name=f"Raison : {warn['reason']}",
            value=f"Warné par {warn['warned_by']} le {warn['date']}",
            inline=False
        )

    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="unwarn", description="Retirer un warn d’un membre")
async def unwarn(interaction: discord.Interaction, member: discord.Member):
    if not interaction.user.guild_permissions.moderate_members:
        await interaction.response.send_message("Tu n'as pas la permission.", ephemeral=True)
        return

    # Charger les warns
    warns = await load_warns(interaction.guild)

    # Chercher un warn pour le membre
    member_warns = [warn for warn in warns if warn['member_id'] == member.id]

    if not member_warns:
        await interaction.response.send_message(f"{member.mention} n'a aucun warn à retirer.", ephemeral=True)
        return

    # Supprimer le premier warn trouvé
    warn = member_warns[0]
    warn_channel = get_warns_channel(interaction.guild)
    if warn_channel:
        # Supprimer le message du warn
        async for message in warn_channel.history(limit=200):
            if warn['reason'] in message.content:
                await message.delete()
                break

    await send_log(interaction.guild, "🎛️ Warn Retiré", f"{interaction.user.mention} a retiré un warn de {member.mention}")
    await interaction.response.send_message(f"Un warn a été retiré à {member.mention}.")

# --- LANCEMENT --- 
bot.run(os.getenv("TOKEN"))
