import discord
from discord.ext import commands

# ID du salon où les gens doivent aller pour créer un vocal
CREATE_VOCAL_CHANNEL_ID = 123456789012345678  # Remplace par ton ID du salon "➕ Créer un vocal"

class VoiceChannelManager:
    def __init__(self, bot):
        self.bot = bot
        self.bot.event(self.on_voice_state_update)

    async def on_voice_state_update(self, member, before, after):
        # Si quelqu'un rejoint un salon
        if after.channel and after.channel.id == CREATE_VOCAL_CHANNEL_ID:
            await self.create_temp_voice_channel(member)

    async def create_temp_voice_channel(self, member):
        guild = member.guild
        category = member.guild.get_channel(CREATE_VOCAL_CHANNEL_ID).category  # Même catégorie que "Créer un vocal"

        # Crée un nouveau salon vocal
        new_channel = await guild.create_voice_channel(
            name=f"Salon de {member.display_name}",
            category=category,
            user_limit=5  # Tu peux ajuster la limite du nombre de personnes ici
        )

        # Déplace l'utilisateur dans le nouveau salon
        await member.move_to(new_channel)

        # Attendre que le salon soit vide pour le supprimer
        def check_empty_channel(before, after):
            return before.channel == new_channel and after.channel is None and len(new_channel.members) == 0

        await self.bot.wait_for('voice_state_update', check=check_empty_channel)
        await new_channel.delete()

# Cette fonction doit être appelée dans ton bot principal (main.py ou bot.py)
def setup(bot):
    VoiceChannelManager(bot)
