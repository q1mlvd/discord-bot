# Добавляем команду help в конец файла (перед on_ready и запуском бота)

@bot.tree.command(name="help", description="Показать информацию о боте и список команд")
async def help_command(interaction: discord.Interaction):
    embed = discord.Embed(
        title="🎮 Экономический Бот - Помощь",
        description="Добро пожаловать в экономическую игру! Этот бот предоставляет полную систему экономики с кейсами, мини-играми, маркетплейсом и достижениями.",
        color=0x3498db
    )
    
    # Основная информация о боте
    embed.add_field(
        name="📊 О боте",
        value="• Внутренняя валюта: монеты 🪙\n• Ежедневные бонусы 📅\n• Система кейсов 🎁\n• Маркетплейс 🏪\n• Мини-игры 🎰\n• Достижения 🏅",
        inline=False
    )
    
    # Экономические команды
    embed.add_field(
        name="💰 Экономические команды",
        value="""**/balance** [пользователь] - Показать баланс
**/daily** - Получить ежедневную награду
**/pay** @пользователь сумма - Перевести монеты
**/inventory** - Показать инвентарь""",
        inline=False
    )
    
    # Команды кейсов
    embed.add_field(
        name="🎁 Команды кейсов",
        value="""**/cases** - Список доступных кейсов
**/opencase** ID_кейса - Купить и открыть кейс
**/openmycase** ID_кейса - Открыть кейс из инвентаря
**/giftcase** @пользователь ID_кейса - Подарить кейс""",
        inline=False
    )
    
    # Маркетплейс
    embed.add_field(
        name="🏪 Маркетплейс",
        value="""**/market** list - Список товаров
**/market** sell название_предмета цена - Продать предмет
**/market** buy ID_товара - Купить товар""",
        inline=False
    )
    
    # Мини-игры
    embed.add_field(
        name="🎮 Мини-игры",
        value="""**/roulette** ставка - Игра в рулетку
**/dice** ставка - Игра в кости
**/duel** @пользователь ставка - Дуэль с игроком
**/quest** - Получить случайный квест
**/steal** @пользователь сумма - Попытаться украсть монеты""",
        inline=False
    )
    
    # Достижения и лидерборды
    embed.add_field(
        name="🏅 Достижения и лидерборды",
        value="""**/leaderboard** balance - Лидеры по балансу
**/leaderboard** wins - Лидеры по победам
**/leaderboard** steals - Лидеры по кражам
**/achievements** - Ваши достижения""",
        inline=False
    )
    
    # Админ-команды (только для админов)
    if any(role.name in ADMIN_ROLES for role in interaction.user.roles):
        embed.add_field(
            name="⚙️ Админ-команды",
            value="""**/admin_addcoins** @пользователь сумма - Добавить монеты
**/admin_removecoins** @пользователь сумма - Забрать монеты
**/admin_giveitem** @пользователь предмет - Выдать предмет
**/admin_removeitem** @пользователь предмет - Забрать предмет
**/admin_createcase** название цена JSON_наград - Создать кейс
**/admin_editcase** ID_кейса [название] [цена] [JSON_наград] - Редактировать кейс
**/admin_deletecase** ID_кейса - Удалить кейс
**/admin_viewtransactions** [@пользователь] - Просмотр транзакций
**/admin_broadcast** сообщение - Отправить объявление""",
            inline=False
        )
    
    # Полезные советы
    embed.add_field(
        name="💡 Советы",
        value="""• Используйте **/daily** каждый день для увеличения серии
• Открывайте кейсы для получения редких предметов и ролей
• Торгуйте предметами на маркетплейсе
• Соревнуйтесь за место в лидербордах""",
        inline=False
    )
    
    embed.set_footer(text="Для подробной информации о команде используйте /команда")
    
    await interaction.response.send_message(embed=embed)

# Синхронизация команд при запуске
@bot.event
async def on_ready():
    print(f'Бот {bot.user.name} запущен!')
    
    # Синхронизация слеш-команд
    try:
        synced = await bot.tree.sync()
        print(f"Синхронизировано {len(synced)} команд")
    except Exception as e:
        print(f"Ошибка синхронизации команд: {e}")
    
    await bot.change_presence(activity=discord.Game(name="Экономическую игру | /help"))

if __name__ == "__main__":
    bot.run(BOT_TOKEN)
