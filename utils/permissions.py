import discord
from discord.ext import commands

# Твои ID сервера и ролей
GUILD_ID = 993041244706066552
ADMIN_ROLES = [1195144951546265675, 766767256742526996, 1078693283695448064, 1138140772097597472, 691904643181314078]
MODERATOR_ROLES = [1167093102868172911, 1360243534946373672, 993043931342319636, 1338611327022923910, 1338609155203661915, 1365798715930968244, 1188261847850299514]

def is_admin():
    async def predicate(interaction: discord.Interaction):
        if interaction.guild.id != GUILD_ID:
            return False
        user_roles = [role.id for role in interaction.user.roles]
        return any(role in ADMIN_ROLES for role in user_roles)
    return commands.check(predicate)

def is_moderator():
    async def predicate(interaction: discord.Interaction):
        if interaction.guild.id != GUILD_ID:
            return False
        user_roles = [role.id for role in interaction.user.roles]
        return any(role in MODERATOR_ROLES + ADMIN_ROLES for role in user_roles)
    return commands.check(predicate)

def is_user():
    async def predicate(interaction: discord.Interaction):
        return interaction.guild.id == GUILD_ID
    return commands.check(predicate)

def check_economic_ban():
    async def predicate(interaction: discord.Interaction):
        # Проверка экономического бана
        return True
    return commands.check(predicate)
