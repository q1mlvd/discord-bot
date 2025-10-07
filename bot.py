import os
import discord
from discord import app_commands
from discord.ext import commands, tasks
from discord.ui import Button, View, Select
import json
import random
import datetime
import traceback
import asyncio

# Импорт PostgreSQL
try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
    print("✅ psycopg2 импортирован успешно")
except ImportError:
    print("❌ psycopg2 не установлен, устанавливаем...")
    import subprocess
    subprocess.check_call(["pip", "install", "psycopg2-binary"])
    import psycopg2
    from psycopg2.extras import RealDictCursor

# Класс CustomBot должен быть определен ПЕРВЫМ
class CustomBot(commands.Bot):
    async def setup_hook(self):
        # Задержка перед началом работы
        await asyncio.sleep(5)
        
        # Предварительная синхронизация
        try:
            print("🔄 Начинаем предварительную синхронизацию команд...")
            synced = await self.tree.sync()
            print(f"✅ Предварительно синхронизировано {len(synced)} команд")
        except Exception as e:
            print(f"❌ Ошибка предварительной синхронизации: {e}")
        
    async def on_ready(self):
        print(f'✅ Бот {self.user.name} успешно запущен!')
        print(f'🔗 ID бота: {self.user.id}')
        print(f'👥 Бот находится на {len(self.guilds)} серверах')

        # Финальная синхронизация команд
        try:
            await asyncio.sleep(2)
            synced = await self.tree.sync()
            print(f"✅ Финально синхронизировано {len(synced)} команд")
            
            # Отладочная информация
            if synced:
                print("📋 Список синхронизированных команд:")
                for cmd in synced:
                    print(f"   - {cmd.name}: {cmd.description}")
            else:
                print("⚠️  Внимание: синхронизировано 0 команд")
                print("🔍 Проверка зарегистрированных команд...")
                commands = self.tree.get_commands()
                print(f"🔍 Команд в дереве: {len(commands)}")
                for cmd in commands:
                    print(f"   - {cmd.name}: {cmd.description}")
                
        except Exception as e:
            print(f"❌ Ошибка синхронизации: {e}")
            traceback.print_exc()

# Получение переменных окружения
def get_database_url():
    """Получаем DATABASE_URL разными способами"""
    database_url = os.environ.get('DATABASE_URL')
    if database_url:
        print("✅ DATABASE_URL найден в переменных окружения")
        return database_url
    
    alternative_names = ['POSTGRES_URL', 'POSTGRESQL_URL', 'RAILWAY_DATABASE_URL']
    for name in alternative_names:
        database_url = os.environ.get(name)
        if database_url:
            print(f"✅ DATABASE_URL найден как {name}")
            return database_url
    
    db_user = os.environ.get('PGUSER')
    db_password = os.environ.get('PGPASSWORD')
    db_host = os.environ.get('PGHOST')
    db_port = os.environ.get('PGPORT')
    db_name = os.environ.get('PGDATABASE')
    
    if all([db_user, db_password, db_host, db_port, db_name]):
        database_url = f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
        print("✅ DATABASE_URL собран из отдельных переменных")
        return database_url
    
    print("❌ DATABASE_URL не найден ни в одной переменной окружения")
    return None

# Получаем переменные
DATABASE_URL = get_database_url()
BOT_TOKEN = os.environ.get('DISCORD_BOT_TOKEN')

# Проверка токена
if not BOT_TOKEN or BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
    print("❌ КРИТИЧЕСКАЯ ОШИБКА: Неверный токен бота!")
    exit(1)

if not DATABASE_URL:
    print("❌ КРИТИЧЕСКАЯ ОШИБКА: DATABASE_URL не установлен!")
    exit(1)

# Настройки бота
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.guilds = True

# СОЗДАЕМ ЭКЗЕМПЛЯР БОТА ЗДЕСЬ
bot = CustomBot(command_prefix='!', intents=intents, help_command=None)

# Конфигурация
LOG_CHANNEL_ID = 1423377881047896207
ADMIN_IDS = [766767256742526996, 1195144951546265675, 691904643181314078, 1078693283695448064, 1138140772097597472]
ADMIN_USER_ID = 1188261847850299514

# Эмодзи для оформления
EMOJIS = {
    'coin': '🪙',
    'daily': '📅',
    'case': '🎁',
    'win': '🎉',
    'lose': '💀',
    'steal': '🦹',
    'market': '🏪',
    'quest': '🗺️',
    'dice': '🎲',
    'duel': '⚔️',
    'admin': '⚙️',
    'slot': '🎰',
    'coinflip': '🪙',
    'blackjack': '🃏',
    'work': '💼'
}

# Система бафов от предметов
ITEM_BUFFS = {
    'Золотой амулет': {'type': 'daily_bonus', 'value': 1.2, 'description': '+20% к ежедневной награде'},
    'Серебряный амулет': {'type': 'daily_bonus', 'value': 1.1, 'description': '+10% к ежедневной награде'},
    'Кольцо удачи': {'type': 'case_bonus', 'value': 1.15, 'description': '+15% к наградам из кейсов'},
    'Браслет везения': {'type': 'game_bonus', 'value': 1.1, 'description': '+10% к выигрышам в играх'},
    'Защитный талисман': {'type': 'steal_protection', 'value': 0.5, 'description': '-50% к шансу кражи у вас'},
    'Перчатка вора': {'type': 'steal_bonus', 'value': 1.2, 'description': '+20% к шансу успешной кражи'},
    'Магический свиток': {'type': 'roulette_bonus', 'value': 1.25, 'description': '+25% к выигрышу в рулетке'},
    'Кристалл маны': {'type': 'multiplier', 'value': 1.3, 'description': 'x1.3 к любым наградам'},
    'Древний артефакт': {'type': 'multiplier', 'value': 1.5, 'description': 'x1.5 к любым наградам'},
    'Мифический предмет': {'type': 'multiplier', 'value': 2.0, 'description': 'x2.0 к любым наградам'},
    'Счастливая монета': {'type': 'coinflip_bonus', 'value': 1.2, 'description': '+20% к выигрышу в coinflip'},
    'Карточный шулер': {'type': 'blackjack_bonus', 'value': 1.15, 'description': '+15% к выигрышу в блэкджеке'},
    'Слот-мастер': {'type': 'slot_bonus', 'value': 1.25, 'description': '+25% к выигрышу в слотах'},
    'Щит богатства': {'type': 'loss_protection', 'value': 0.8, 'description': '-20% к проигрышам'},
    'Флакон зелья': {'type': 'quest_bonus', 'value': 1.2, 'description': '+20% к наградам за квесты'},
    'Зелье удачи': {'type': 'all_bonus', 'value': 1.1, 'description': '+10% ко всем наградам'},
    'Руна богатства': {'type': 'transfer_bonus', 'value': 0.9, 'description': '-10% к комиссии переводов'},
    'Тотем защиты': {'type': 'duel_bonus', 'value': 1.2, 'description': '+20% к шансу победы в дуэлях'},
    'Ожерелье мудрости': {'type': 'xp_bonus', 'value': 1.15, 'description': '+15% к опыту'},
    'Плащ тени': {'type': 'steal_chance', 'value': 1.15, 'description': '+15% к шансу кражи'},
    # НОВЫЕ ПРЕДМЕТЫ:
    'Железный щит': {'type': 'steal_protection', 'value': 0.8, 'description': '-20% к шансу кражи у вас'},
    'Бронзовый медальон': {'type': 'game_bonus', 'value': 1.05, 'description': '+5% к выигрышам в играх'},
    'Серебряный кулон': {'type': 'roulette_bonus', 'value': 1.1, 'description': '+10% к выигрышу в рулетке'},
    'Золотой перстень': {'type': 'slot_bonus', 'value': 1.15, 'description': '+15% к выигрышу в слотах'},
    'Изумрудный амулет': {'type': 'blackjack_bonus', 'value': 1.1, 'description': '+10% к выигрышу в блэкджеке'},
    'Рубиновый талисман': {'type': 'case_bonus', 'value': 1.1, 'description': '+10% к наградам из кейсов'},
    'Сапфировый оберег': {'type': 'loss_protection', 'value': 0.9, 'description': '-10% к проигрышам'},
    'Аметистовый жезл': {'type': 'transfer_bonus', 'value': 0.95, 'description': '-5% к комиссии переводов'},
    'Топазный скипетр': {'type': 'duel_bonus', 'value': 1.1, 'description': '+10% к шансу победы в дуэлях'},
    'Опаловый артефакт': {'type': 'multiplier', 'value': 1.1, 'description': 'x1.1 к любым наградам'},
    'Алмазная корона': {'type': 'steal_protection', 'value': 0.3, 'description': '-70% к шансу кражи у вас'},
    'Платиновый диск': {'type': 'game_bonus', 'value': 1.2, 'description': '+20% к выигрышам в играх'},
    'Титановый щит': {'type': 'loss_protection', 'value': 0.5, 'description': '-50% к проигрышам'}
}

# Улучшенная система достижений
ACHIEVEMENTS = {
    'first_daily': {'name': 'Первый шаг', 'description': 'Получите первую ежедневную награду', 'reward': 100},
    'rich': {'name': 'Богач', 'description': 'Накопите 10,000 монет', 'reward': 500},
    'millionaire': {'name': 'Миллионер', 'description': 'Накопите 100,000 монет', 'reward': 5000},
    'gambler': {'name': 'Азартный игрок', 'description': 'Выиграйте в рулетку 10 раз', 'reward': 1000},
    'thief': {'name': 'Вор', 'description': 'Успешно украдите монеты 10 раз', 'reward': 800},
    'case_opener': {'name': 'Коллекционер', 'description': 'Откройте 25 кейсов', 'reward': 1500},
    'case_master': {'name': 'Мастер кейсов', 'description': 'Откройте 100 кейсов', 'reward': 5000},
    'duel_master': {'name': 'Мастер дуэлей', 'description': 'Выиграйте 15 дуэлей', 'reward': 1200},
    'slot_king': {'name': 'Король слотов', 'description': 'Выиграйте джекпот в слотах 1 раз', 'reward': 3000},
    'blackjack_pro': {'name': 'Профи в блэкджеке', 'description': 'Выиграйте 5 раз в блэкджек', 'reward': 2000},
    'coinflip_champ': {'name': 'Чемпион монетки', 'description': 'Выиграйте 15 раз в подбрасывание монеты', 'reward': 1500},
    'trader': {'name': 'Торговец', 'description': 'Продайте 5 предметов на маркетплейсе', 'reward': 800},
    'gifter': {'name': 'Щедрый', 'description': 'Подарите 5 кейсов', 'reward': 1000},
    'veteran': {'name': 'Ветеран', 'description': 'Получите ежедневную награду 15 дней подряд', 'reward': 3000},
    'lucky': {'name': 'Везунчик', 'description': 'Выиграйте 3 раза подряд в любую игру', 'reward': 2000},
    'item_collector': {'name': 'Коллекционер предметов', 'description': 'Соберите 5 разных предметов', 'reward': 1500},
    'buff_master': {'name': 'Мастер бафов', 'description': 'Активируйте 3 разных бафа одновременно', 'reward': 2000},
    # НОВЫЕ ДОСТИЖЕНИЯ:
    'workaholic': {'name': 'Трудоголик', 'description': 'Выполните 10 работ', 'reward': 2000},
    'rich_af': {'name': 'Олигарх', 'description': 'Накопите 1,000,000 монет', 'reward': 20000},
    'case_addict': {'name': 'Кейсозависимый', 'description': 'Откройте 500 кейсов', 'reward': 15000},
    'perfect_thief': {'name': 'Идеальный вор', 'description': 'Успешно украдите 50 раз', 'reward': 5000},
    'gambling_legend': {'name': 'Легенда азарта', 'description': 'Выиграйте 50 раз в каждой игре', 'reward': 10000}
}

# Улучшенная система работ - ТОЛЬКО 3 КОНКРЕТНЫХ РАБОТЫ
WORKS = {
    'miner': {
        'name': '⛏️ Шахтер', 
        'description': 'Добыть 10 единиц руды в шахте',
        'task': 'Найдите и добыйте 10 едицин редкой руды',
        'reward': 800,
        'cooldown': 3600
    },
    'hunter': {
        'name': '🏹 Охотник', 
        'description': 'Охотиться на диких зверей в лесу',
        'task': 'Поймайте 3 редких зверя в глубинах леса',
        'reward': 1200,
        'cooldown': 3600
    },
    'fisherman': {
        'name': '🎣 Рыбак', 
        'description': 'Рыбачить на озере',
        'task': 'Поймайте 5 крупных рыб в горном озере',
        'reward': 1500,
        'cooldown': 3600
    }
}

# Класс для работы с заданиями
class WorkView(View):
    def __init__(self, user_id, work_type):
        super().__init__(timeout=300)  # 5 минут на выполнение
        self.user_id = user_id
        self.work_type = work_type
        self.work_data = WORKS[work_type]

    @discord.ui.button(label='✅ Выполнить задание', style=discord.ButtonStyle.success)
    async def complete_work(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Это не ваша работа!", ephemeral=True)
            return
        
        # Проверяем кулдаун
        cursor = db.conn.cursor()
        cursor.execute('SELECT last_completed FROM user_works WHERE user_id = %s AND work_type = %s', 
                      (interaction.user.id, self.work_type))
        result = cursor.fetchone()
        
        if result and result[0]:
            last_completed = result[0]
            cooldown_seconds = self.work_data['cooldown']
            if (datetime.datetime.now() - last_completed).total_seconds() < cooldown_seconds:
                remaining = cooldown_seconds - (datetime.datetime.now() - last_completed).total_seconds()
                minutes = int(remaining // 60)
                seconds = int(remaining % 60)
                await interaction.response.send_message(
                    f"⏰ Эту работу можно выполнить again через {minutes} минут {seconds} секунд!",
                    ephemeral=True
                )
                return
        
        # Выполняем работу
        reward = self.work_data['reward']
        
        # Применяем бафы
        final_reward = db.apply_buff_to_amount(interaction.user.id, reward, 'multiplier')
        final_reward = db.apply_buff_to_amount(interaction.user.id, final_reward, 'all_bonus')
        
        # Обновляем базу данных
        db.complete_work(interaction.user.id, self.work_type, final_reward)
        
        embed = discord.Embed(
            title=f"💼 {self.work_data['name']} - Задание выполнено!",
            description=f"**Задание:** {self.work_data['task']}\n\n🎉 Вы успешно выполнили работу!",
            color=0x00ff00
        )
        embed.add_field(name="💰 Заработок", value=f"{final_reward} {EMOJIS['coin']}", inline=True)
        embed.add_field(name="⏰ Следующее выполнение", value="Через 1 час", inline=True)
        embed.set_footer(text="Используйте /works для просмотра статистики")
        
        await interaction.response.edit_message(embed=embed, view=None)

    @discord.ui.button(label='❌ Отменить', style=discord.ButtonStyle.danger)
    async def cancel_work(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Это не ваша работа!", ephemeral=True)
            return
        
        await interaction.response.edit_message(
            content="❌ Работа отменена.",
            embed=None,
            view=None
        )

# Команда для начала работы
@bot.tree.command(name="work", description="Начать работу и заработать монеты")
@app_commands.describe(work_type="Тип работы")
@app_commands.choices(work_type=[
    app_commands.Choice(name="⛏️ Шахтер (800 монет)", value="miner"),
    app_commands.Choice(name="🏹 Охотник (1200 монет)", value="hunter"),
    app_commands.Choice(name="🎣 Рыбак (1500 монет)", value="fisherman")
])
async def work_command(interaction: discord.Interaction, work_type: app_commands.Choice[str]):
    try:
        work_data = WORKS[work_type.value]
        
        # Проверяем кулдаун
        cursor = db.conn.cursor()
        cursor.execute('SELECT last_completed FROM user_works WHERE user_id = %s AND work_type = %s', 
                      (interaction.user.id, work_type.value))
        result = cursor.fetchone()
        
        if result and result[0]:
            last_completed = result[0]
            cooldown_seconds = work_data['cooldown']
            if (datetime.datetime.now() - last_completed).total_seconds() < cooldown_seconds:
                remaining = cooldown_seconds - (datetime.datetime.now() - last_completed).total_seconds()
                minutes = int(remaining // 60)
                seconds = int(remaining % 60)
                await interaction.response.send_message(
                    f"⏰ Эту работу можно выполнить again через {minutes} минут {seconds} секунд!",
                    ephemeral=True
                )
                return
        
        # Создаем embed с информацией о работе
        embed = discord.Embed(
            title=f"💼 {work_data['name']}",
            description=work_data['description'],
            color=0x3498db
        )
        embed.add_field(name="📝 Задание", value=work_data['task'], inline=False)
        embed.add_field(name="💰 Награда", value=f"{work_data['reward']} {EMOJIS['coin']}", inline=True)
        embed.add_field(name="⏰ Время выполнения", value="Мгновенно", inline=True)
        embed.add_field(name="⏱️ Кулдаун", value="1 час", inline=True)
        embed.set_footer(text="Нажмите кнопку ниже чтобы выполнить задание")
        
        view = WorkView(interaction.user.id, work_type.value)
        await interaction.response.send_message(embed=embed, view=view)
        
    except Exception as e:
        print(f"❌ Ошибка в команде work: {e}")
        error_embed = discord.Embed(
            title="❌ Ошибка начала работы",
            description="Произошла ошибка при начале работы. Попробуйте позже.",
            color=0xff0000
        )
        await interaction.response.send_message(embed=error_embed, ephemeral=True)

# Команда для просмотра статистики работ
@bot.tree.command(name="works", description="Показать статистику выполненных работ")
async def works_stats(interaction: discord.Interaction):
    try:
        user_works = db.get_user_works(interaction.user.id)
        
        embed = discord.Embed(title="💼 Статистика работ", color=0x3498db)
        
        # Показываем доступные работы
        works_info = ""
        for work_id, work_data in WORKS.items():
            # Проверяем кулдаун
            cursor = db.conn.cursor()
            cursor.execute('SELECT last_completed FROM user_works WHERE user_id = %s AND work_type = %s', 
                          (interaction.user.id, work_id))
            result = cursor.fetchone()
            
            status = "✅ Доступно"
            if result and result[0]:
                last_completed = result[0]
                cooldown_seconds = work_data['cooldown']
                if (datetime.datetime.now() - last_completed).total_seconds() < cooldown_seconds:
                    remaining = cooldown_seconds - (datetime.datetime.now() - last_completed).total_seconds()
                    minutes = int(remaining // 60)
                    seconds = int(remaining % 60)
                    status = f"⏰ Через {minutes}м {seconds}с"
            
            works_info += f"**{work_data['name']}** - {work_data['reward']} {EMOJIS['coin']} - {status}\n"
        
        embed.add_field(name="📊 Доступные работы", value=works_info, inline=False)
        
        # Показываем статистику выполненных работ
        if user_works:
            stats_text = ""
            total_earned = 0
            total_works = 0
            
            for work in user_works:
                work_type = work[0]
                count = work[1]
                total_works += count
                
                if work_type in WORKS:
                    work_name = WORKS[work_type]['name']
                    work_reward = WORKS[work_type]['reward']
                    earned = count * work_reward
                    total_earned += earned
                    
                    stats_text += f"**{work_name}:** {count} раз ({earned} {EMOJIS['coin']})\n"
            
            embed.add_field(name="📈 Выполненные работы", value=stats_text, inline=False)
            embed.add_field(name="🔢 Всего работ", value=f"{total_works} выполненных заданий", inline=True)
            embed.add_field(name="💰 Всего заработано", value=f"{total_earned} {EMOJIS['coin']}", inline=True)
        else:
            embed.add_field(name="📈 Выполненные работы", value="Вы еще не выполнили ни одной работы", inline=False)
        
        await interaction.response.send_message(embed=embed)
        
    except Exception as e:
        print(f"❌ Ошибка в команде works: {e}")
        error_embed = discord.Embed(
            title="❌ Ошибка загрузки статистики",
            description="Произошла ошибка при загрузке статистики работ.",
            color=0xff0000
        )
        await interaction.response.send_message(embed=error_embed, ephemeral=True)

# Команда для просмотра статистики работ
@bot.tree.command(name="works", description="Показать статистику выполненных работ")
async def works_stats(interaction: discord.Interaction):
    try:
        user_works = db.get_user_works(interaction.user.id)
        
        embed = discord.Embed(title="💼 Статистика работ", color=0x3498db)
        
        # Показываем доступные работы
        works_info = ""
        for work_id, work_data in WORKS.items():
            # Проверяем кулдаун
            cursor = db.conn.cursor()
            cursor.execute('SELECT last_completed FROM user_works WHERE user_id = %s AND work_type = %s', 
                          (interaction.user.id, work_id))
            result = cursor.fetchone()
            
            status = "✅ Доступно"
            if result and result[0]:
                last_completed = result[0]
                cooldown_seconds = work_data['cooldown']
                if (datetime.datetime.now() - last_completed).total_seconds() < cooldown_seconds:
                    remaining = cooldown_seconds - (datetime.datetime.now() - last_completed).total_seconds()
                    minutes = int(remaining // 60)
                    seconds = int(remaining % 60)
                    status = f"⏰ Через {minutes}м {seconds}с"
            
            works_info += f"**{work_data['name']}** - {work_data['reward']} {EMOJIS['coin']} - {status}\n"
        
        embed.add_field(name="📊 Доступные работы", value=works_info, inline=False)
        
        # Показываем статистику выполненных работ
        if user_works:
            stats_text = ""
            total_earned = 0
            total_works = 0
            
            for work in user_works:
                work_type = work[0]
                count = work[1]
                total_works += count
                
                if work_type in WORKS:
                    work_name = WORKS[work_type]['name']
                    work_reward = WORKS[work_type]['reward']
                    earned = count * work_reward
                    total_earned += earned
                    
                    stats_text += f"**{work_name}:** {count} раз ({earned} {EMOJIS['coin']})\n"
            
            embed.add_field(name="📈 Выполненные работы", value=stats_text, inline=False)
            embed.add_field(name="🔢 Всего работ", value=f"{total_works} выполненных заданий", inline=True)
            embed.add_field(name="💰 Всего заработано", value=f"{total_earned} {EMOJIS['coin']}", inline=True)
        else:
            embed.add_field(name="📈 Выполненные работы", value="Вы еще не выполнили ни одной работы", inline=False)
        
        await interaction.response.send_message(embed=embed)
        
    except Exception as e:
        print(f"❌ Ошибка в команде works: {e}")
        error_embed = discord.Embed(
            title="❌ Ошибка загрузки статистики",
            description="Произошла ошибка при загрузке статистики работ.",
            color=0xff0000
        )
        await interaction.response.send_message(embed=error_embed, ephemeral=True)

# Исправленный класс Database для PostgreSQL
class Database:
    def __init__(self):
        self.conn = None
        self.connect()
        self.create_tables()
    
    def connect(self):
        """Подключение к базе данных с повторными попытками"""
        max_retries = 3
        for attempt in range(max_retries):
            try:
                self.conn = psycopg2.connect(DATABASE_URL, sslmode='require')
                print("✅ Успешное подключение к PostgreSQL!")
                return
            except Exception as e:
                print(f"❌ Попытка {attempt + 1}/{max_retries} не удалась: {e}")
                if attempt < max_retries - 1:
                    print("🔄 Повторная попытка через 5 секунд...")
                    import time
                    time.sleep(5)
                else:
                    print("💥 Не удалось подключиться к базе данных после нескольких попыток")
                    raise

    def create_tables(self):
        """Создание таблиц с улучшенной обработкой ошибок"""
        try:
            cursor = self.conn.cursor()
            
            print("🔄 Создание таблиц...")
            
            # Таблица пользователей
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    user_id BIGINT PRIMARY KEY,
                    balance INTEGER DEFAULT 100,
                    daily_streak INTEGER DEFAULT 0,
                    last_daily TEXT,
                    inventory TEXT DEFAULT '{}',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Таблица транзакций
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS transactions (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT,
                    type TEXT,
                    amount INTEGER,
                    target_user_id BIGINT,
                    description TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Таблица кейсов
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS cases (
                    id SERIAL PRIMARY KEY,
                    name TEXT,
                    price INTEGER,
                    rewards TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Таблица маркета
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS market (
                    id SERIAL PRIMARY KEY,
                    seller_id BIGINT,
                    item_name TEXT,
                    price INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Таблица достижений
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS achievements (
                    user_id BIGINT,
                    achievement_id TEXT,
                    unlocked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (user_id, achievement_id)
                )
            ''')
            
            # Таблица дуэлей
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS duels (
                    id SERIAL PRIMARY KEY,
                    challenger_id BIGINT,
                    target_id BIGINT,
                    bet INTEGER,
                    status TEXT DEFAULT 'pending',
                    winner_id BIGINT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Таблица предметов
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS items (
                    id SERIAL PRIMARY KEY,
                    name TEXT,
                    description TEXT,
                    value INTEGER,
                    rarity TEXT,
                    buff_type TEXT,
                    buff_value REAL,
                    buff_description TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Таблица статистики пользователей
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS user_stats (
                    user_id BIGINT PRIMARY KEY,
                    cases_opened INTEGER DEFAULT 0,
                    duels_won INTEGER DEFAULT 0,
                    steals_successful INTEGER DEFAULT 0,
                    steals_failed INTEGER DEFAULT 0,
                    roulette_wins INTEGER DEFAULT 0,
                    slot_wins INTEGER DEFAULT 0,
                    blackjack_wins INTEGER DEFAULT 0,
                    coinflip_wins INTEGER DEFAULT 0,
                    daily_claimed INTEGER DEFAULT 0,
                    total_earned INTEGER DEFAULT 0,
                    market_sales INTEGER DEFAULT 0,
                    gifts_sent INTEGER DEFAULT 0,
                    consecutive_wins INTEGER DEFAULT 0,
                    items_collected INTEGER DEFAULT 0,
                    work_completed INTEGER DEFAULT 0,
                    last_win_time TIMESTAMP
                )
            ''')
            
            # Таблица работ пользователей
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS user_works (
                    user_id BIGINT,
                    work_type TEXT,
                    completed_count INTEGER DEFAULT 0,
                    last_completed TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (user_id, work_type)
                )
            ''')
            
            self.conn.commit()
            print("✅ Все таблицы успешно созданы!")
            
            # Инициализация начальных данных
            self.initialize_default_data()
            
        except Exception as e:
            print(f"❌ Ошибка при создании таблиц: {e}")
            self.conn.rollback()
            raise

def initialize_default_data(self):
    """Инициализация начальных данных с правильными отступами"""
    try:
        cursor = self.conn.cursor()
        
        # Проверяем текущее количество кейсов
        cursor.execute('SELECT COUNT(*) FROM cases')
        current_count = cursor.fetchone()[0]
        print(f"🔍 Текущее количество кейсов в базе: {current_count}")
        
        # Если кейсов нет, добавляем их
        if current_count == 0:
            print("🔄 Добавление кейсов...")
            
            # ВСЕ 15 КЕЙСОВ С УЛУЧШЕННЫМИ ШАНСАМИ
            balanced_cases = [
                # 📦 Малый кейс — 50 🪙 (ID: 1)
                ('📦 Малый кейс', 50, json.dumps([
                    {'type': 'coins', 'amount': [10, 40], 'chance': 0.8, 'description': 'Небольшая сумма монет'},
                    {'type': 'coins', 'amount': [41, 100], 'chance': 0.15, 'description': 'Средняя сумма монет'},
                    {'type': 'coins', 'amount': [101, 300], 'chance': 0.05, 'description': 'Хорошая сумма монет'}
                ])),
                
                # 📦 Средний кейс — 150 🪙 (ID: 2)
                ('📦 Средний кейс', 150, json.dumps([
                    {'type': 'coins', 'amount': [50, 120], 'chance': 0.7, 'description': 'Стандартные монеты'},
                    {'type': 'coins', 'amount': [121, 300], 'chance': 0.2, 'description': 'Улучшенные монеты'},
                    {'type': 'special_item', 'name': 'Магический свиток', 'chance': 0.05, 'description': 'Бонус к рулетке'},
                    {'type': 'coins', 'amount': [301, 800], 'chance': 0.05, 'description': 'Премиум монеты'}
                ])),
                
                # 💎 Большой кейс — 500 🪙 (ID: 3)
                ('💎 Большой кейс', 500, json.dumps([
                    {'type': 'coins', 'amount': [200, 400], 'chance': 0.6, 'description': 'Стандартные монеты'},
                    {'type': 'coins', 'amount': [401, 1000], 'chance': 0.25, 'description': 'Улучшенные монеты'},
                    {'type': 'special_item', 'name': 'Золотой амулет', 'chance': 0.08, 'description': 'Бонус к ежедневным'},
                    {'type': 'bonus', 'multiplier': 1.5, 'chance': 0.07, 'description': 'Бонус множитель'}
                ])),
                
                # 👑 Элитный кейс — 1000 🪙 (ID: 4)
                ('👑 Элитный кейс', 1000, json.dumps([
                    {'type': 'coins', 'amount': [500, 1000], 'chance': 0.3, 'description': 'Элитные монеты'},
                    {'type': 'loss', 'amount': [100, 300], 'chance': 0.2, 'description': 'Риск потери'},
                    {'type': 'special_item', 'name': 'Древний артефакт', 'chance': 0.15, 'description': 'Мощный множитель'},
                    {'type': 'bonus', 'multiplier': 2.0, 'chance': 0.1, 'description': 'Большой бонус'},
                    {'type': 'coins', 'amount': [1001, 3000], 'chance': 0.15, 'description': 'Премиум монеты'},
                    {'type': 'coins', 'amount': [3001, 6000], 'chance': 0.1, 'description': 'Элитные монеты'}
                ])),
                
                # 🔮 Секретный кейс — 2000 🪙 (ID: 5)
                ('🔮 Секретный кейс', 2000, json.dumps([
                    {'type': 'coins', 'amount': [800, 1500], 'chance': 0.3, 'description': 'Секретные монеты'},
                    {'type': 'loss', 'amount': [500, 1000], 'chance': 0.15, 'description': 'Высокий риск'},
                    {'type': 'special_item', 'name': 'Мифический предмет', 'chance': 0.15, 'description': 'Легендарный предмет'},
                    {'type': 'bonus', 'multiplier': 3.0, 'chance': 0.1, 'description': 'Огромный бонус'},
                    {'type': 'coins', 'amount': [1501, 3000], 'chance': 0.15, 'description': 'Бонусные монеты'},
                    {'type': 'coins', 'amount': [4001, 7000], 'chance': 0.15, 'description': 'Максимальные монеты'}
                ])),
                
                # ⚔️ Боевой кейс — 3 500 🪙 (ID: 6)
                ('⚔️ Боевой кейс', 3500, json.dumps([
                    {'type': 'coins', 'amount': [1000, 3000], 'chance': 0.4, 'description': 'Боевые монеты'},
                    {'type': 'loss', 'amount': [500, 1000], 'chance': 0.1, 'description': 'Тактический риск'},
                    {'type': 'special_item', 'name': 'Перчатка вора', 'chance': 0.15, 'description': 'Бонус к кражам'},
                    {'type': 'bonus', 'multiplier': 2.5, 'chance': 0.1, 'description': 'Боевой бонус'},
                    {'type': 'coins', 'amount': [3001, 6000], 'chance': 0.15, 'description': 'Победные монеты'},
                    {'type': 'special_item', 'name': 'Тотем защиты', 'chance': 0.1, 'description': 'Защита в дуэлях'}
                ])),
                
                # 💎 Премиум кейс — 5 000 🪙 (ID: 7)
                ('💎 Премиум кейс', 5000, json.dumps([
                    {'type': 'coins', 'amount': [2000, 4000], 'chance': 0.4, 'description': 'Премиум монеты'},
                    {'type': 'special_item', 'name': 'Золотой амулет', 'chance': 0.2, 'description': 'Элитный амулет'},
                    {'type': 'bonus', 'multiplier': 3.0, 'chance': 0.1, 'description': 'Премиум бонус'},
                    {'type': 'loss', 'amount': [1000, 2000], 'chance': 0.1, 'description': 'Премиум риск'},
                    {'type': 'coins', 'amount': [5001, 8000], 'chance': 0.1, 'description': 'Эксклюзивные монеты'},
                    {'type': 'special_item', 'name': 'Кристалл маны', 'chance': 0.1, 'description': 'Мощный множитель'}
                ])),
                
                # 🔥 Адский кейс — 7 500 🪙 (ID: 8)
                ('🔥 Адский кейс', 7500, json.dumps([
                    {'type': 'coins', 'amount': [3000, 6000], 'chance': 0.35, 'description': 'Адские монеты'},
                    {'type': 'loss', 'amount': [2000, 3000], 'chance': 0.15, 'description': 'Адский риск'},
                    {'type': 'special_item', 'name': 'Плащ тени', 'chance': 0.2, 'description': 'Бонус к кражам'},
                    {'type': 'bonus', 'multiplier': 3.5, 'chance': 0.1, 'description': 'Огненный бонус'},
                    {'type': 'coins', 'amount': [6001, 10000], 'chance': 0.1, 'description': 'Демонические монеты'},
                    {'type': 'special_item', 'name': 'Древний артефакт', 'chance': 0.1, 'description': 'Древняя сила'}
                ])),
                
                # ⚡ Легендарный кейс — 10 000 🪙 (ID: 9)
                ('⚡ Легендарный кейс', 10000, json.dumps([
                    {'type': 'coins', 'amount': [5000, 8000], 'chance': 0.3, 'description': 'Легендарные монеты'},
                    {'type': 'special_item', 'name': 'Кольцо удачи', 'chance': 0.2, 'description': 'Удача в кейсах'},
                    {'type': 'bonus', 'multiplier': 4.0, 'chance': 0.1, 'description': 'Легендарный бонус'},
                    {'type': 'loss', 'amount': [2000, 4000], 'chance': 0.1, 'description': 'Легендарный риск'},
                    {'type': 'coins', 'amount': [8001, 15000], 'chance': 0.15, 'description': 'Мифические монеты'},
                    {'type': 'special_item', 'name': 'Карточный шулер', 'chance': 0.15, 'description': 'Бонус к блэкджеку'}
                ])),
                
                # 🌌 Космический кейс — 15 000 🪙 (ID: 10)
                ('🌌 Космический кейс', 15000, json.dumps([
                    {'type': 'coins', 'amount': [8000, 15000], 'chance': 0.3, 'description': 'Космические монеты'},
                    {'type': 'special_item', 'name': 'Ожерелье мудрости', 'chance': 0.2, 'description': 'Мудрость и опыт'},
                    {'type': 'bonus', 'multiplier': 4.5, 'chance': 0.1, 'description': 'Космический бонус'},
                    {'type': 'loss', 'amount': [4000, 6000], 'chance': 0.1, 'description': 'Космический риск'},
                    {'type': 'coins', 'amount': [15001, 25000], 'chance': 0.15, 'description': 'Галактические монеты'},
                    {'type': 'special_item', 'name': 'Руна богатства', 'chance': 0.15, 'description': 'Богатство и удача'}
                ])),
                
                # 💠 Кристальный кейс — 20 000 🪙 (ID: 11)
                ('💠 Кристальный кейс', 20000, json.dumps([
                    {'type': 'coins', 'amount': [10000, 20000], 'chance': 0.3, 'description': 'Кристальные монеты'},
                    {'type': 'special_item', 'name': 'Кристалл маны', 'chance': 0.15, 'description': 'Магическая сила'},
                    {'type': 'bonus', 'multiplier': 5.0, 'chance': 0.1, 'description': 'Кристальный бонус'},
                    {'type': 'loss', 'amount': [5000, 8000], 'chance': 0.1, 'description': 'Кристальный риск'},
                    {'type': 'coins', 'amount': [20001, 30000], 'chance': 0.15, 'description': 'Изумрудные монеты'},
                    {'type': 'special_item', 'name': 'Зелье удачи', 'chance': 0.2, 'description': 'Удача во всем'}
                ])),
                
                # 👁️ Теневой кейс — 25 000 🪙 (ID: 12)
                ('👁️ Теневой кейс', 25000, json.dumps([
                    {'type': 'coins', 'amount': [12000, 22000], 'chance': 0.3, 'description': 'Теневые монеты'},
                    {'type': 'special_item', 'name': 'Плащ тени', 'chance': 0.15, 'description': 'Теневая мощь'},
                    {'type': 'bonus', 'multiplier': 5.5, 'chance': 0.1, 'description': 'Теневой бонус'},
                    {'type': 'loss', 'amount': [6000, 10000], 'chance': 0.1, 'description': 'Теневой риск'},
                    {'type': 'coins', 'amount': [22001, 35000], 'chance': 0.15, 'description': 'Призрачные монеты'},
                    {'type': 'special_item', 'name': 'Защитный талисман', 'chance': 0.2, 'description': 'Абсолютная защита'}
                ])),
                
                # 🌈 Радужный кейс — 30 000 🪙 (ID: 13)
                ('🌈 Радужный кейс', 30000, json.dumps([
                    {'type': 'coins', 'amount': [15000, 25000], 'chance': 0.25, 'description': 'Радужные монеты'},
                    {'type': 'special_item', 'name': 'Слот-мастер', 'chance': 0.2, 'description': 'Мастер слотов'},
                    {'type': 'bonus', 'multiplier': 6.0, 'chance': 0.1, 'description': 'Радужный бонус'},
                    {'type': 'loss', 'amount': [8000, 12000], 'chance': 0.1, 'description': 'Радужный риск'},
                    {'type': 'coins', 'amount': [25001, 40000], 'chance': 0.15, 'description': 'Разноцветные монеты'},
                    {'type': 'special_item', 'name': 'Счастливая монета', 'chance': 0.2, 'description': 'Удача в coinflip'}
                ])),
                
                # 🩸 Кровавый кейс — 40 000 🪙 (ID: 14)
                ('🩸 Кровавый кейс', 40000, json.dumps([
                    {'type': 'coins', 'amount': [18000, 30000], 'chance': 0.25, 'description': 'Кровавые монеты'},
                    {'type': 'special_item', 'name': 'Флакон зелья', 'chance': 0.2, 'description': 'Магическое зелье'},
                    {'type': 'bonus', 'multiplier': 7.0, 'chance': 0.1, 'description': 'Кровавый бонус'},
                    {'type': 'loss', 'amount': [10000, 15000], 'chance': 0.1, 'description': 'Кровавый риск'},
                    {'type': 'coins', 'amount': [30001, 45000], 'chance': 0.15, 'description': 'Драконьи монеты'},
                    {'type': 'special_item', 'name': 'Щит богатства', 'chance': 0.2, 'description': 'Защита богатства'}
                ])),
                
                # 🌟 Божественный кейс — 50 000 🪙 (ID: 15)
                ('🌟 Божественный кейс', 50000, json.dumps([
                    {'type': 'coins', 'amount': [25000, 50000], 'chance': 0.2, 'description': 'Божественные монеты'},
                    {'type': 'special_item', 'name': 'Зелье удачи', 'chance': 0.2, 'description': 'Божественная удача'},
                    {'type': 'bonus', 'multiplier': 8.0, 'chance': 0.1, 'description': 'Божественный бонус'},
                    {'type': 'loss', 'amount': [12000, 20000], 'chance': 0.1, 'description': 'Божественный риск'},
                    {'type': 'coins', 'amount': [50001, 80000], 'chance': 0.15, 'description': 'Небесные монеты'},
                    {'type': 'special_item', 'name': 'Древний артефакт', 'chance': 0.25, 'description': 'Власть богов'}
                ]))
            ]
            
            for case in balanced_cases:
                cursor.execute('INSERT INTO cases (name, price, rewards) VALUES (%s, %s, %s)', 
                             (case[0], case[1], case[2]))
            
            print(f"✅ Добавлено {len(balanced_cases)} кейсов!")
        
        # Проверяем и добавляем предметы если нужно
        cursor.execute('SELECT COUNT(*) FROM items')
        items_count = cursor.fetchone()[0]
        
        if items_count == 0:
            print("🔄 Добавление ВСЕХ стандартных предметов...")
            
            # ИСПРАВЛЕННЫЙ СПИСОК ПРЕДМЕТОВ
            default_items = [
                ('Золотой амулет', 'Увеличивает ежедневную награду', 500, 'rare', 'daily_bonus', 1.2, '+20% к ежедневной награде'),
                ('Серебряный амулет', 'Небольшой бонус к ежедневной награде', 250, 'common', 'daily_bonus', 1.1, '+10% к ежедневной награде'),
                ('Кольцо удачи', 'Увеличивает награды из кейсов', 600, 'rare', 'case_bonus', 1.15, '+15% к наградам из кейсов'),
                ('Браслет везения', 'Увеличивает выигрыши в играх', 450, 'uncommon', 'game_bonus', 1.1, '+10% к выигрышам в играх'),
                ('Защитный талисман', 'Защищает от краж', 800, 'epic', 'steal_protection', 0.5, '-50% к шансу кражи у вас'),
                ('Перчатка вора', 'Увеличивает шанс успешной кражи', 700, 'rare', 'steal_bonus', 1.2, '+20% к шансу успешной кражи'),
                ('Магический свиток', 'Увеличивает выигрыш в рулетке', 550, 'rare', 'roulette_bonus', 1.25, '+25% к выигрышу в рулетке'),
                ('Кристалл маны', 'Умножает все награды', 1000, 'epic', 'multiplier', 1.3, 'x1.3 к любым наградам'),
                ('Древний артефакт', 'Мощный множитель наград', 2000, 'legendary', 'multiplier', 1.5, 'x1.5 к любым наградам'),
                ('Мифический предмет', 'Легендарный множитель наград', 5000, 'mythic', 'multiplier', 2.0, 'x2.0 к любым наградам'),
                ('Счастливая монета', 'Увеличивает выигрыш в coinflip', 300, 'uncommon', 'coinflip_bonus', 1.2, '+20% к выигрышу в coinflip'),
                ('Карточный шулер', 'Увеличивает выигрыш в блэкджеке', 400, 'rare', 'blackjack_bonus', 1.15, '+15% к выигрышу в блэкджеке'),
                ('Слот-мастер', 'Увеличивает выигрыш в слотах', 600, 'rare', 'slot_bonus', 1.25, '+25% к выигрышу в слотах'),
                ('Щит богатства', 'Уменьшает проигрыши', 900, 'epic', 'loss_protection', 0.8, '-20% к проигрышам'),
                ('Флакон зелья', 'Увеличивает награды за квесты', 350, 'uncommon', 'quest_bonus', 1.2, '+20% к наградам за квесты'),
                ('Зелье удачи', 'Увеличивает все награды', 800, 'epic', 'all_bonus', 1.1, '+10% ко всем наградам'),
                ('Руна богатства', 'Уменьшает комиссию переводов', 700, 'rare', 'transfer_bonus', 0.9, '-10% к комиссии переводов'),
                ('Тотем защиты', 'Увеличивает шанс победы в дуэлях', 500, 'rare', 'duel_bonus', 1.2, '+20% к шансу победы в дуэлях'),
                ('Ожерелье мудрости', 'Увеличивает получаемый опыт', 450, 'uncommon', 'xp_bonus', 1.15, '+15% к опыту'),
                ('Плащ тени', 'Увеличивает шанс кражи', 550, 'rare', 'steal_chance', 1.15, '+15% к шансу кражи'),
                ('Железный щит', 'Базовая защита от краж', 200, 'common', 'steal_protection', 0.8, '-20% к шансу кражи у вас'),
                ('Бронзовый медальон', 'Небольшой бонус к играм', 150, 'common', 'game_bonus', 1.05, '+5% к выигрышам в играх'),
                ('Серебряный кулон', 'Бонус к рулетке', 300, 'uncommon', 'roulette_bonus', 1.1, '+10% к выигрышу в рулетке'),
                ('Золотой перстень', 'Бонус к слотам', 400, 'uncommon', 'slot_bonus', 1.15, '+15% к выигрышу в слотах'),
                ('Изумрудный амулет', 'Бонус к блэкджеку', 350, 'uncommon', 'blackjack_bonus', 1.1, '+10% к выигрышу в блэкджеке'),
                ('Рубиновый талисман', 'Бонус к кейсам', 500, 'rare', 'case_bonus', 1.1, '+10% к наградам из кейсов'),
                ('Сапфировый оберег', 'Защита от потерь', 600, 'rare', 'loss_protection', 0.9, '-10% к проигрышам'),
                ('Аметистовый жезл', 'Бонус к переводам', 400, 'uncommon', 'transfer_bonus', 0.95, '-5% к комиссии переводов'),
                ('Топазный скипетр', 'Бонус к дуэлям', 450, 'uncommon', 'duel_bonus', 1.1, '+10% к шансу победы в дуэлях'),
                ('Опаловый артефакт', 'Небольшой множитель', 800, 'rare', 'multiplier', 1.1, 'x1.1 к любым наградам'),
                ('Алмазная корона', 'Улучшенная защита', 1200, 'epic', 'steal_protection', 0.3, '-70% к шансу кражи у вас'),
                ('Платиновый диск', 'Улучшенный бонус к играм', 900, 'epic', 'game_bonus', 1.2, '+20% к выигрышам в играх'),
                ('Титановый щит', 'Максимальная защита', 2000, 'legendary', 'loss_protection', 0.5, '-50% к проигрышам')
            ]
            
            for item in default_items:
                cursor.execute('INSERT INTO items (name, description, value, rarity, buff_type, buff_value, buff_description) VALUES (%s, %s, %s, %s, %s, %s, %s)', item)
            
            print(f"✅ Добавлено {len(default_items)} стандартных предметов!")
        else:
            print(f"✅ В базе уже есть {items_count} предметов, пропускаем инициализацию")
        
        self.conn.commit()
        print("✅ Начальные данные успешно инициализированы!")
        
    except Exception as e:
        print(f"❌ Ошибка при инициализации данных: {e}")
        self.conn.rollback()
            
            # Проверяем и добавляем предметы если нужно
            cursor.execute('SELECT COUNT(*) FROM items')
            items_count = cursor.fetchone()[0]
            
            if items_count == 0:
                print("🔄 Добавление ВСЕХ стандартных предметов...")
                
                # ИСПРАВЛЕННЫЙ СПИСОК ПРЕДМЕТОВ - правильный синтаксис
                default_items = [
                    ('Золотой амулет', 'Увеличивает ежедневную награду', 500, 'rare', 'daily_bonus', 1.2, '+20% к ежедневной награде'),
                    ('Серебряный амулет', 'Небольшой бонус к ежедневной награде', 250, 'common', 'daily_bonus', 1.1, '+10% к ежедневной награде'),
                    ('Кольцо удачи', 'Увеличивает награды из кейсов', 600, 'rare', 'case_bonus', 1.15, '+15% к наградам из кейсов'),
                    ('Браслет везения', 'Увеличивает выигрыши в играх', 450, 'uncommon', 'game_bonus', 1.1, '+10% к выигрышам в играх'),
                    ('Защитный талисман', 'Защищает от краж', 800, 'epic', 'steal_protection', 0.5, '-50% к шансу кражи у вас'),
                    ('Перчатка вора', 'Увеличивает шанс успешной кражи', 700, 'rare', 'steal_bonus', 1.2, '+20% к шансу успешной кражи'),
                    ('Магический свиток', 'Увеличивает выигрыш в рулетке', 550, 'rare', 'roulette_bonus', 1.25, '+25% к выигрышу в рулетке'),
                    ('Кристалл маны', 'Умножает все награды', 1000, 'epic', 'multiplier', 1.3, 'x1.3 к любым наградам'),
                    ('Древний артефакт', 'Мощный множитель наград', 2000, 'legendary', 'multiplier', 1.5, 'x1.5 к любым наградам'),
                    ('Мифический предмет', 'Легендарный множитель наград', 5000, 'mythic', 'multiplier', 2.0, 'x2.0 к любым наградам'),
                    ('Счастливая монета', 'Увеличивает выигрыш в coinflip', 300, 'uncommon', 'coinflip_bonus', 1.2, '+20% к выигрышу в coinflip'),
                    ('Карточный шулер', 'Увеличивает выигрыш в блэкджеке', 400, 'rare', 'blackjack_bonus', 1.15, '+15% к выигрышу в блэкджеке'),
                    ('Слот-мастер', 'Увеличивает выигрыш в слотах', 600, 'rare', 'slot_bonus', 1.25, '+25% к выигрышу в слотах'),
                    ('Щит богатства', 'Уменьшает проигрыши', 900, 'epic', 'loss_protection', 0.8, '-20% к проигрышам'),
                    ('Флакон зелья', 'Увеличивает награды за квесты', 350, 'uncommon', 'quest_bonus', 1.2, '+20% к наградам за квесты'),
                    ('Зелье удачи', 'Увеличивает все награды', 800, 'epic', 'all_bonus', 1.1, '+10% ко всем наградам'),
                    ('Руна богатства', 'Уменьшает комиссию переводов', 700, 'rare', 'transfer_bonus', 0.9, '-10% к комиссии переводов'),
                    ('Тотем защиты', 'Увеличивает шанс победы в дуэлях', 500, 'rare', 'duel_bonus', 1.2, '+20% к шансу победы в дуэлях'),
                    ('Ожерелье мудрости', 'Увеличивает получаемый опыт', 450, 'uncommon', 'xp_bonus', 1.15, '+15% к опыту'),
                    ('Плащ тени', 'Увеличивает шанс кражи', 550, 'rare', 'steal_chance', 1.15, '+15% к шансу кражи'),
                    # ДОБАВЛЕННЫЕ ПРЕДМЕТЫ:
                    ('Железный щит', 'Базовая защита от краж', 200, 'common', 'steal_protection', 0.8, '-20% к шансу кражи у вас'),
                    ('Бронзовый медальон', 'Небольшой бонус к играм', 150, 'common', 'game_bonus', 1.05, '+5% к выигрышам в играх'),
                    ('Серебряный кулон', 'Бонус к рулетке', 300, 'uncommon', 'roulette_bonus', 1.1, '+10% к выигрышу в рулетке'),
                    ('Золотой перстень', 'Бонус к слотам', 400, 'uncommon', 'slot_bonus', 1.15, '+15% к выигрышу в слотах'),
                    ('Изумрудный амулет', 'Бонус к блэкджеку', 350, 'uncommon', 'blackjack_bonus', 1.1, '+10% к выигрышу в блэкджеке'),
                    ('Рубиновый талисман', 'Бонус к кейсам', 500, 'rare', 'case_bonus', 1.1, '+10% к наградам из кейсов'),
                    ('Сапфировый оберег', 'Защита от потерь', 600, 'rare', 'loss_protection', 0.9, '-10% к проигрышам'),
                    ('Аметистовый жезл', 'Бонус к переводам', 400, 'uncommon', 'transfer_bonus', 0.95, '-5% к комиссии переводов'),
                    ('Топазный скипетр', 'Бонус к дуэлям', 450, 'uncommon', 'duel_bonus', 1.1, '+10% к шансу победы в дуэлях'),
                    ('Опаловый артефакт', 'Небольшой множитель', 800, 'rare', 'multiplier', 1.1, 'x1.1 к любым наградам'),
                    ('Алмазная корона', 'Улучшенная защита', 1200, 'epic', 'steal_protection', 0.3, '-70% к шансу кражи у вас'),
                    ('Платиновый диск', 'Улучшенный бонус к играм', 900, 'epic', 'game_bonus', 1.2, '+20% к выигрышам в играш'),
                    ('Титановый щит', 'Максимальная защита', 2000, 'legendary', 'loss_protection', 0.5, '-50% к проигрышам')
                ]
                
                for item in default_items:
                    cursor.execute('INSERT INTO items (name, description, value, rarity, buff_type, buff_value, buff_description) VALUES (%s, %s, %s, %s, %s, %s, %s)', item)
                
                print(f"✅ Добавлено {len(default_items)} стандартных предметов!")
            else:
                print(f"✅ В базе уже есть {items_count} предметов, пропускаем инициализацию")
            
            self.conn.commit()
            print("✅ Начальные данные успешно инициализированы!")
            
        except Exception as e:
            print(f"❌ Ошибка при инициализации данных: {e}")
            self.conn.rollback()

    # Остальные методы класса Database...
    def get_user(self, user_id):
        """Безопасное получение пользователя"""
        try:
            cursor = self.conn.cursor()
            cursor.execute('SELECT * FROM users WHERE user_id = %s', (user_id,))
            user = cursor.fetchone()
            
            if not user:
                # Создаем нового пользователя
                cursor.execute('''
                    INSERT INTO users (user_id, balance, inventory) 
                    VALUES (%s, %s, %s)
                ''', (user_id, 100, json.dumps({"cases": {}, "items": {}})))
                self.conn.commit()
                
                # Получаем созданного пользователя
                cursor.execute('SELECT * FROM users WHERE user_id = %s', (user_id,))
                user = cursor.fetchone()
            
            return user
            
        except Exception as e:
            print(f"❌ Ошибка в get_user для {user_id}: {e}")
            return (user_id, 100, 0, None, json.dumps({"cases": {}, "items": {}}), datetime.datetime.now())

    def get_user_safe(self, user_id):
        """Алиас для get_user для совместимости"""
        return self.get_user(user_id)
    
    def update_balance(self, user_id, amount):
        cursor = self.conn.cursor()
        cursor.execute('UPDATE users SET balance = balance + %s WHERE user_id = %s', (amount, user_id))
        self.conn.commit()
    
    def log_transaction(self, user_id, transaction_type, amount, target_user_id=None, description=""):
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO transactions (user_id, type, amount, target_user_id, description)
            VALUES (%s, %s, %s, %s, %s)
        ''', (user_id, transaction_type, amount, target_user_id, description))
        self.conn.commit()
    
    def get_cases(self):
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM cases ORDER BY price ASC')
        return cursor.fetchall()
    
    def get_case(self, case_id):
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM cases WHERE id = %s', (case_id,))
        return cursor.fetchone()
    
    def get_items(self):
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM items')
        return cursor.fetchall()
    
    def get_item(self, item_id):
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM items WHERE id = %s', (item_id,))
        return cursor.fetchone()
    
    def get_item_by_name(self, item_name):
        """Безопасное получение предмета по имени"""
        try:
            cursor = self.conn.cursor()
            cursor.execute('SELECT * FROM items WHERE name = %s', (item_name,))
            item = cursor.fetchone()
            return item
        except Exception as e:
            print(f"❌ Ошибка в get_item_by_name для {item_name}: {e}")
            return None
    
    def add_item_to_inventory(self, user_id, item_name):
        cursor = self.conn.cursor()
        
        cursor.execute('SELECT id FROM items WHERE name = %s', (item_name,))
        item_result = cursor.fetchone()
        
        if not item_result:
            # Если предмет не найден, создаем его без бафа
            cursor.execute('INSERT INTO items (name, description, value, rarity) VALUES (%s, %s, %s, %s) RETURNING id', 
                          (item_name, 'Автоматически созданный предмет', 100, 'common'))
            item_id = cursor.fetchone()[0]
        else:
            item_id = item_result[0]
        
        cursor.execute('SELECT inventory FROM users WHERE user_id = %s', (user_id,))
        result = cursor.fetchone()
        
        if result and result[0]:
            inventory_data = json.loads(result[0])
        else:
            inventory_data = {"cases": {}, "items": {}}
            
        if "items" not in inventory_data:
            inventory_data["items"] = {}
            
        item_key = str(item_id)
        if item_key in inventory_data["items"]:
            inventory_data["items"][item_key] += 1
        else:
            inventory_data["items"][item_key] = 1
        
        cursor.execute('UPDATE users SET inventory = %s WHERE user_id = %s', 
                      (json.dumps(inventory_data), user_id))
        self.conn.commit()
        
        # Обновляем статистику собранных предметов
        self.update_user_stat(user_id, 'items_collected')
    
    def remove_item_from_inventory(self, user_id, item_name):
        cursor = self.conn.cursor()
        
        cursor.execute('SELECT id FROM items WHERE name = %s', (item_name,))
        item_result = cursor.fetchone()
        
        if not item_result:
            return False
            
        item_id = str(item_result[0])
        
        cursor.execute('SELECT inventory FROM users WHERE user_id = %s', (user_id,))
        result = cursor.fetchone()
        
        if not result or not result[0]:
            return False
            
        inventory_data = json.loads(result[0])
        
        if item_id in inventory_data.get("items", {}):
            if inventory_data["items"][item_id] > 1:
                inventory_data["items"][item_id] -= 1
            else:
                del inventory_data["items"][item_id]
            
            cursor.execute('UPDATE users SET inventory = %s WHERE user_id = %s', 
                          (json.dumps(inventory_data), user_id))
            self.conn.commit()
            return True
        return False

    def add_case_to_inventory(self, user_id, case_id, case_name, source="gifted"):
        cursor = self.conn.cursor()
        cursor.execute('SELECT inventory FROM users WHERE user_id = %s', (user_id,))
        result = cursor.fetchone()
        
        if result and result[0]:
            inventory = json.loads(result[0])
        else:
            inventory = {"cases": {}, "items": {}}
        
        if "cases" not in inventory:
            inventory["cases"] = {}
        
        case_key = f"case_{case_id}"
        if case_key in inventory["cases"]:
            inventory["cases"][case_key]["count"] += 1
        else:
            inventory["cases"][case_key] = {
                "name": case_name,
                "count": 1,
                "source": source
            }
        
        cursor.execute('UPDATE users SET inventory = %s WHERE user_id = %s', (json.dumps(inventory), user_id))
        self.conn.commit()
    
    def get_user_inventory(self, user_id):
        """Безопасное получение инвентаря пользователя"""
        try:
            cursor = self.conn.cursor()
            cursor.execute('SELECT inventory FROM users WHERE user_id = %s', (user_id,))
            result = cursor.fetchone()
            
            if result and result[0]:
                try:
                    return json.loads(result[0])
                except json.JSONDecodeError:
                    return {"cases": {}, "items": {}}
            return {"cases": {}, "items": {}}
        except Exception as e:
            print(f"❌ Ошибка в get_user_inventory для {user_id}: {e}")
            return {"cases": {}, "items": {}}

    def get_user_inventory_safe(self, user_id):
        """Безопасное получение инвентаря с обработкой ошибок"""
        try:
            cursor = self.conn.cursor()
            cursor.execute('SELECT inventory FROM users WHERE user_id = %s', (user_id,))
            result = cursor.fetchone()
            
            if result and result[0]:
                try:
                    inventory_data = json.loads(result[0])
                    if not isinstance(inventory_data, dict):
                        inventory_data = {"cases": {}, "items": {}}
                    if "cases" not in inventory_data:
                        inventory_data["cases"] = {}
                    if "items" not in inventory_data:
                        inventory_data["items"] = {}
                    return inventory_data
                except json.JSONDecodeError:
                    return {"cases": {}, "items": {}}
            return {"cases": {}, "items": {}}
        except Exception as e:
            print(f"❌ Ошибка в get_user_inventory_safe: {e}")
            return {"cases": {}, "items": {}}
    
    def get_all_items_safe(self):
        """Безопасное получение всех предметов"""
        try:
            cursor = self.conn.cursor()
            cursor.execute('SELECT * FROM items')
            return cursor.fetchall()
        except Exception as e:
            print(f"❌ Ошибка в get_all_items_safe: {e}")
            return []
    
    def remove_case_from_inventory(self, user_id, case_id):
        cursor = self.conn.cursor()
        cursor.execute('SELECT inventory FROM users WHERE user_id = %s', (user_id,))
        result = cursor.fetchone()
        
        if not result or not result[0]:
            return False
            
        inventory = json.loads(result[0])
        
        case_key = f"case_{case_id}"
        if case_key in inventory.get("cases", {}):
            if inventory["cases"][case_key]["count"] > 1:
                inventory["cases"][case_key]["count"] -= 1
            else:
                del inventory["cases"][case_key]
            
            cursor.execute('UPDATE users SET inventory = %s WHERE user_id = %s', (json.dumps(inventory), user_id))
            self.conn.commit()
            return True
        return False

    def update_user_stat(self, user_id, stat_name, increment=1):
        """Обновляет статистику пользователя и проверяет достижения"""
        try:
            cursor = self.conn.cursor()
            
            cursor.execute('SELECT 1 FROM user_stats WHERE user_id = %s', (user_id,))
            if not cursor.fetchone():
                cursor.execute('INSERT INTO user_stats (user_id) VALUES (%s)', (user_id,))
            
            cursor.execute(f'''
                UPDATE user_stats SET {stat_name} = {stat_name} + %s 
                WHERE user_id = %s
            ''', (increment, user_id))
            
            self.conn.commit()
            
            return self.check_achievements(user_id)
        except Exception as e:
            print(f"❌ Ошибка в update_user_stat: {e}")
            return []
    
    def check_achievements(self, user_id):
        """Проверяет и выдает достижения пользователю"""
        try:
            cursor = self.conn.cursor()
            
            cursor.execute('SELECT * FROM user_stats WHERE user_id = %s', (user_id,))
            stats = cursor.fetchone()
            
            if not stats:
                return []
            
            user_data = self.get_user(user_id)
            balance = user_data[1] if len(user_data) > 1 else 0
            
            inventory = self.get_user_inventory(user_id)
            unique_items = len(inventory.get("items", {}))
            
            cursor.execute('SELECT achievement_id FROM achievements WHERE user_id = %s', (user_id,))
            user_achievements = [row[0] for row in cursor.fetchall()]
            
            achievements_to_add = []
            
            # Достижения по балансу
            if 'first_daily' not in user_achievements and stats[9] >= 1:  # daily_claimed
                achievements_to_add.append('first_daily')
            if 'rich' not in user_achievements and balance >= 10000:
                achievements_to_add.append('rich')
            if 'millionaire' not in user_achievements and balance >= 100000:
                achievements_to_add.append('millionaire')
            if 'rich_af' not in user_achievements and balance >= 1000000:
                achievements_to_add.append('rich_af')
            
            # Достижения по кейсам
            if 'case_opener' not in user_achievements and stats[1] >= 25:  # cases_opened
                achievements_to_add.append('case_opener')
            if 'case_master' not in user_achievements and stats[1] >= 100:
                achievements_to_add.append('case_master')
            if 'case_addict' not in user_achievements and stats[1] >= 500:
                achievements_to_add.append('case_addict')
            
            # Достижения по играм
            if 'gambler' not in user_achievements and stats[5] >= 10:  # roulette_wins
                achievements_to_add.append('gambler')
            if 'thief' not in user_achievements and stats[3] >= 10:  # steals_successful
                achievements_to_add.append('thief')
            if 'perfect_thief' not in user_achievements and stats[3] >= 50:
                achievements_to_add.append('perfect_thief')
            if 'duel_master' not in user_achievements and stats[2] >= 15:  # duels_won
                achievements_to_add.append('duel_master')
            if 'slot_king' not in user_achievements and stats[6] >= 1:  # slot_wins (джекпот)
                achievements_to_add.append('slot_king')
            if 'blackjack_pro' not in user_achievements and stats[7] >= 5:  # blackjack_wins
                achievements_to_add.append('blackjack_pro')
            if 'coinflip_champ' not in user_achievements and stats[8] >= 15:  # coinflip_wins
                achievements_to_add.append('coinflip_champ')
            
            # Проверка достижения "Легенда азарта"
            if ('gambling_legend' not in user_achievements and 
                stats[5] >= 50 and stats[6] >= 50 and stats[7] >= 50 and stats[8] >= 50):
                achievements_to_add.append('gambling_legend')
            
            # Другие достижения
            if 'trader' not in user_achievements and stats[11] >= 5:  # market_sales
                achievements_to_add.append('trader')
            if 'gifter' not in user_achievements and stats[12] >= 5:  # gifts_sent
                achievements_to_add.append('gifter')
            if 'veteran' not in user_achievements and stats[9] >= 15:  # daily_claimed
                achievements_to_add.append('veteran')
            if 'lucky' not in user_achievements and stats[13] >= 3:  # consecutive_wins
                achievements_to_add.append('lucky')
            if 'item_collector' not in user_achievements and unique_items >= 5:
                achievements_to_add.append('item_collector')
            if 'buff_master' not in user_achievements and self.get_active_buffs_count(user_id) >= 3:
                achievements_to_add.append('buff_master')
            if 'workaholic' not in user_achievements and stats[15] >= 10:  # work_completed
                achievements_to_add.append('workaholic')
            
            # Добавляем новые достижения и выдаем награды
            for achievement_id in achievements_to_add:
                cursor.execute('INSERT INTO achievements (user_id, achievement_id) VALUES (%s, %s)', 
                              (user_id, achievement_id))
                
                reward = ACHIEVEMENTS[achievement_id]['reward']
                self.update_balance(user_id, reward)
                self.log_transaction(user_id, 'achievement_reward', reward, description=f"Достижение: {ACHIEVEMENTS[achievement_id]['name']}")
            
            self.conn.commit()
            
            return achievements_to_add
        except Exception as e:
            print(f"❌ Ошибка в check_achievements: {e}")
            return []

    def get_item_name_by_id(self, item_id):
        """Получить название предмета по ID"""
        try:
            if not item_id or not str(item_id).isdigit():
                return f"Предмет ID:{item_id}"
                
            item_data = self.get_item(int(item_id))
            if item_data and len(item_data) > 1 and item_data[1]:
                return item_data[1]
            return f"Предмет ID:{item_id}"
        except Exception as e:
            print(f"❌ Ошибка получения названия предмета {item_id}: {e}")
            return f"Предмет ID:{item_id}"

    def update_consecutive_wins(self, user_id, win=True):
        """Обновляет счетчик последовательных побед"""
        cursor = self.conn.cursor()
        
        if win:
            cursor.execute('''
                UPDATE user_stats 
                SET consecutive_wins = consecutive_wins + 1, last_win_time = CURRENT_TIMESTAMP
                WHERE user_id = %s
            ''', (user_id,))
        else:
            cursor.execute('''
                UPDATE user_stats 
                SET consecutive_wins = 0
                WHERE user_id = %s
            ''', (user_id,))
        
        self.conn.commit()
    
    def get_user_buffs(self, user_id):
        """Безопасное получение бафов пользователя"""
        try:
            inventory = self.get_user_inventory(user_id)
            buffs = {}
            
            for item_id, count in inventory.get("items", {}).items():
                try:
                    if not str(item_id).isdigit():
                        continue
                        
                    item_data = self.get_item(int(item_id))
                    if item_data and len(item_data) > 6 and item_data[5]:
                        buff_type = item_data[5]
                        buff_value = item_data[6] if len(item_data) > 6 else 1.0
                        
                        if buff_type not in buffs or buff_value > buffs[buff_type]['value']:
                            buffs[buff_type] = {
                                'value': float(buff_value),
                                'description': item_data[7] if len(item_data) > 7 and item_data[7] else "Бонус",
                                'item_name': item_data[1] if len(item_data) > 1 and item_data[1] else "Предмет"
                            }
                except (ValueError, IndexError, TypeError) as e:
                    print(f"⚠️ Ошибка обработки предмета {item_id}: {e}")
                    continue
            
            return buffs
        except Exception as e:
            print(f"❌ Ошибка в get_user_buffs для {user_id}: {e}")
            return {}
    
    def get_active_buffs_count(self, user_id):
        """Возвращает количество активных уникальных бафов"""
        buffs = self.get_user_buffs(user_id)
        return len(buffs)
    
    def apply_buff_to_amount(self, user_id, base_amount, buff_type):
        """Применяет баф к сумме, если он есть у пользователя"""
        buffs = self.get_user_buffs(user_id)
        if buff_type in buffs:
            return int(base_amount * buffs[buff_type]['value'])
        return base_amount
    
    def apply_buff_to_chance(self, user_id, base_chance, buff_type):
        """Применяет баф к шансу, если он есть у пользователя"""
        buffs = self.get_user_buffs(user_id)
        if buff_type in buffs:
            return base_chance * buffs[buff_type]['value']
        return base_chance
    
    def get_all_users(self):
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM users ORDER BY balance DESC')
        return cursor.fetchall()
    
    def get_all_transactions(self, limit=50):
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM transactions ORDER BY timestamp DESC LIMIT %s', (limit,))
        return cursor.fetchall()
    
    def get_all_items(self):
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM items')
        return cursor.fetchall()

    def update_items_collected_stat(self, user_id):
        """Обновляет статистику собранных предметов на основе инвентаря"""
        try:
            inventory = self.get_user_inventory_safe(user_id)
            unique_items_count = len(inventory.get("items", {}))
            
            cursor = self.conn.cursor()
            cursor.execute('UPDATE user_stats SET items_collected = %s WHERE user_id = %s', 
                          (unique_items_count, user_id))
            self.conn.commit()
            return unique_items_count
        except Exception as e:
            print(f"❌ Ошибка в update_items_collected_stat: {e}")
            return 0

    def get_user_works(self, user_id):
        """Получить выполненные работы пользователя"""
        try:
            cursor = self.conn.cursor()
            cursor.execute('SELECT work_type, completed_count, last_completed FROM user_works WHERE user_id = %s', (user_id,))
            return cursor.fetchall()
        except Exception as e:
            print(f"❌ Ошибка в get_user_works: {e}")
            return []

    def complete_work(self, user_id, work_type, reward):
        """Зарегистрировать выполнение работы"""
        try:
            cursor = self.conn.cursor()
            
            cursor.execute('SELECT 1 FROM user_works WHERE user_id = %s AND work_type = %s', (user_id, work_type))
            if cursor.fetchone():
                cursor.execute('''
                    UPDATE user_works SET completed_count = completed_count + 1, last_completed = CURRENT_TIMESTAMP 
                    WHERE user_id = %s AND work_type = %s
                ''', (user_id, work_type))
            else:
                cursor.execute('''
                    INSERT INTO user_works (user_id, work_type, completed_count) 
                    VALUES (%s, %s, 1)
                ''', (user_id, work_type))
            
            self.update_balance(user_id, reward)
            self.log_transaction(user_id, 'work', reward, description=f"Работа: {work_type}")
            
            cursor.execute('SELECT work_completed FROM user_stats WHERE user_id = %s', (user_id,))
            if cursor.fetchone():
                cursor.execute('UPDATE user_stats SET work_completed = work_completed + 1 WHERE user_id = %s', (user_id,))
            else:
                cursor.execute('INSERT INTO user_stats (user_id, work_completed) VALUES (%s, 1)', (user_id,))
            
            self.conn.commit()
            return True
        except Exception as e:
            print(f"❌ Ошибка в complete_work: {e}")
            self.conn.rollback()
            return False

# Создаем экземпляр базы данных
try:
    db = Database()
    print("✅ База данных успешно инициализирована!")
    
    test_cases = db.get_cases()
    print(f"🔍 Тест: загружено {len(test_cases)} кейсов после инициализации")
    
except Exception as e:
    print(f"💥 Критическая ошибка при инициализации базы данных: {e}")
    traceback.print_exc()
    exit(1)

# Событие подключения для отладки
@bot.event
async def on_connect():
    print(f"🔗 Бот подключился к Discord")
    commands_count = len(bot.tree.get_commands())
    print(f"📊 Зарегистрировано команд в коде: {commands_count}")
    
    if commands_count == 0:
        print("❌ КРИТИЧЕСКАЯ ОШИБКА: Нет зарегистрированных команд!")
        print("🔍 Проверьте:")
        print("   - Декораторы @bot.tree.command")
        print("   - Отсутствие ошибок в определении команд")
        print("   - Правильность импортов")

# Простая тестовая команда для проверки
@bot.tree.command(name="test", description="Тестовая команда для проверки работы")
async def test_command(interaction: discord.Interaction):
    """Простая тестовая команда для проверки синхронизации"""
    embed = discord.Embed(
        title="✅ Тестовая команда работает!",
        description="Если вы видите это сообщение, значит команды синхронизированы правильно!",
        color=0x00ff00
    )
    await interaction.response.send_message(embed=embed, ephemeral=True)

# Улучшенная функция проверки прав администратора
def is_admin():
    async def predicate(interaction: discord.Interaction) -> bool:
        is_admin = interaction.user.id in ADMIN_IDS
        if not is_admin:
            await interaction.response.send_message(
                "❌ У вас нет прав для использования этой команды!",
                ephemeral=True
            )
        return is_admin
    return app_commands.check(predicate)

# Обработчик ошибок для команд
@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    if isinstance(error, app_commands.CheckFailure):
        return
    elif isinstance(error, app_commands.CommandNotFound):
        await interaction.response.send_message("❌ Команда не найдена!", ephemeral=True)
    elif isinstance(error, app_commands.MissingPermissions):
        await interaction.response.send_message("❌ Недостаточно прав!", ephemeral=True)
    elif isinstance(error, IndexError):
        print(f"🔴 IndexError в команде: {error}")
        error_embed = discord.Embed(
            title="❌ Ошибка данных",
            description="Произошла ошибка при обработке данных. Администратор уведомлен.",
            color=0xff0000
        )
        try:
            await interaction.response.send_message(embed=error_embed, ephemeral=True)
        except:
            await interaction.followup.send(embed=error_embed, ephemeral=True)
    else:
        print(f"🔴 Необработанная ошибка: {error}")
        try:
            await interaction.response.send_message(
                "❌ Произошла неизвестная ошибка при выполнении команды!",
                ephemeral=True
            )
        except:
            try:
                await interaction.followup.send(
                    "❌ Произошла неизвестная ошибка при выполнении команды!",
                    ephemeral=True
                )
            except:
                pass

# Классы View для различных команд
class ImprovedCasesView(View):
    def __init__(self, pages, author_id):
        super().__init__(timeout=120)
        self.pages = pages
        self.current_page = 0
        self.total_pages = len(pages)
        self.author_id = author_id
        self.update_buttons()

    def update_buttons(self):
        self.previous_button.disabled = (self.current_page == 0)
        self.next_button.disabled = (self.current_page >= self.total_pages - 1)

    @discord.ui.button(label='⬅️ Назад', style=discord.ButtonStyle.secondary)
    async def previous_button(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.author_id:
            await interaction.response.send_message("❌ Это не ваша пагинация!", ephemeral=True)
            return
        
        if self.current_page > 0:
            self.current_page -= 1
            self.update_buttons()
            embed = self.create_embed()
            await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label='➡️ Вперед', style=discord.ButtonStyle.secondary)
    async def next_button(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.author_id:
            await interaction.response.send_message("❌ Это не ваша пагинация!", ephemeral=True)
            return
        
        if self.current_page < self.total_pages - 1:
            self.current_page += 1
            self.update_buttons()
            embed = self.create_embed()
            await interaction.response.edit_message(embed=embed, view=self)

    def create_embed(self):
        page_cases = self.pages[self.current_page]
        embed = discord.Embed(
            title=f"📦 Список кейсов (Страница {self.current_page + 1}/{self.total_pages})",
            color=0xff69b4
        )

        for case in page_cases:
            case_id = case[0]
            case_name = case[1]
            case_price = case[2]
            case_rewards = json.loads(case[3])

            embed.add_field(
                name=f"{case_name} (ID: {case_id})",
                value=f"Цена: {case_price} {EMOJIS['coin']}",
                inline=False
            )

        return embed

class CaseView(View):
    def __init__(self, case_id, user_id):
        super().__init__(timeout=60)
        self.case_id = case_id
        self.user_id = user_id

    @discord.ui.button(label='Открыть кейс', style=discord.ButtonStyle.primary)
    async def open_button(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Это не ваш кейс!", ephemeral=True)
            return

        case_data = db.get_case(self.case_id)
        if not case_data:
            await interaction.response.send_message("❌ Кейс не найден!", ephemeral=True)
            return

        user_data = db.get_user(interaction.user.id)
        user_safe = get_user_data_safe(user_data)

        case_price = case_data[2]
        if user_safe['balance'] < case_price:
            await interaction.response.send_message("❌ Недостаточно монет!", ephemeral=True)
            return

        # Спин анимация
        embed = discord.Embed(title="🎰 Открытие кейса...", color=0xffd700)
        await interaction.response.edit_message(embed=embed, view=None)

        for i in range(3):
            await asyncio.sleep(1)
            embed.description = "🎁" * (i + 1)
            await interaction.edit_original_response(embed=embed)

        # Определение награды
        case = {
            'name': case_data[1],
            'price': case_data[2],
            'rewards': json.loads(case_data[3])
        }
        
        # Функции для работы с наградами
        def get_reward(case):
            rewards = case['rewards']
            rand = random.random()
            current = 0
            for reward in rewards:
                current += reward['chance']
                if rand <= current:
                    return reward
            return rewards[0]

async def process_reward(user, reward, case):
    user_id = user.id
    if reward['type'] == 'coins':
        amount = random.randint(reward['amount'][0], reward['amount'][1])
        # Применяем бафы
        amount = db.apply_buff_to_amount(user_id, amount, 'case_bonus')
        amount = db.apply_buff_to_amount(user_id, amount, 'multiplier')
        amount = db.apply_buff_to_amount(user_id, amount, 'all_bonus')
        db.update_balance(user_id, amount)
        db.log_transaction(user_id, 'case_reward', amount, description=f"Кейс: {case['name']}")
        return f"💰 Монеты: {amount} {EMOJIS['coin']}"

    elif reward['type'] == 'special_item':
        item_name = reward['name']
        db.add_item_to_inventory(user_id, item_name)
        return f"🎁 Предмет: {item_name}"

    elif reward['type'] == 'bonus':
        amount = case['price'] * reward['multiplier']
        db.update_balance(user_id, amount)
        db.log_transaction(user_id, 'case_bonus', amount, description=f"Бонус из кейса: {case['name']}")
        return f"⭐ Бонус: {amount} {EMOJIS['coin']} (x{reward['multiplier']})"

    elif reward['type'] == 'loss':
        amount = random.randint(reward['amount'][0], reward['amount'][1])
        # Применяем защиту от потерь
        actual_loss = db.apply_buff_to_amount(user_id, amount, 'loss_protection')
        db.update_balance(user_id, -actual_loss)
        db.log_transaction(user_id, 'case_loss', -actual_loss, description=f"Потеря из кейса: {case['name']}")
        return f"💀 Потеря: {actual_loss} {EMOJIS['coin']}"

    else:
        return "Ничего"

        reward = get_reward(case)
        reward_text = await process_reward(interaction.user, reward, case)

        # Списание средств
        db.update_balance(interaction.user.id, -case_price)
        db.log_transaction(interaction.user.id, 'case_purchase', -case_price, description=case['name'])

        # Обновляем статистику открытия кейсов
        db.update_user_stat(interaction.user.id, 'cases_opened')

        embed = discord.Embed(
            title=f"🎉 {case['name']} открыт!",
            description=reward_text,
            color=0x00ff00
        )
        embed.add_field(name="Стоимость", value=f"{case_price} {EMOJIS['coin']}", inline=True)
        await interaction.edit_original_response(embed=embed)

class CoinFlipView(View):
    def __init__(self, user_id, bet):
        super().__init__(timeout=60)
        self.user_id = user_id
        self.bet = bet

    @discord.ui.button(label='Орёл', style=discord.ButtonStyle.primary)
    async def heads(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Это не ваша игра!", ephemeral=True)
            return
        
        await self.process_coinflip(interaction, 'heads')

    @discord.ui.button(label='Решка', style=discord.ButtonStyle.primary)
    async def tails(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Это не ваша игра!", ephemeral=True)
            return
        
        await self.process_coinflip(interaction, 'tails')

    async def process_coinflip(self, interaction: discord.Interaction, choice):
        # Анимация подбрасывания
        embed = discord.Embed(title="🪙 Монета подбрасывается...", color=0xffd700)
        await interaction.response.edit_message(embed=embed, view=None)
        
        for i in range(3):
            await asyncio.sleep(1)
            embed.description = "⏳" * (i + 1)
            await interaction.edit_original_response(embed=embed)
        
        await asyncio.sleep(1)
        
        # Результат
        result = random.choice(['heads', 'tails'])
        if choice == result:
            base_winnings = self.bet * 2
            winnings = db.apply_buff_to_amount(interaction.user.id, base_winnings, 'coinflip_bonus')
            winnings = db.apply_buff_to_amount(interaction.user.id, winnings, 'game_bonus')
            winnings = db.apply_buff_to_amount(interaction.user.id, winnings, 'multiplier')
            winnings = db.apply_buff_to_amount(interaction.user.id, winnings, 'all_bonus')
            
            db.update_balance(interaction.user.id, winnings - self.bet)  # Чистый выигрыш
            db.log_transaction(interaction.user.id, 'coinflip_win', winnings - self.bet)
            db.update_user_stat(interaction.user.id, 'coinflip_wins')
            db.update_consecutive_wins(interaction.user.id, True)
            
            result_text = f"🎉 Победа! Вы выиграли {winnings - self.bet} {EMOJIS['coin']} (чистыми)"
            color = 0x00ff00
        else:
            # Применяем баф защиты от проигрышей
            loss = db.apply_buff_to_amount(interaction.user.id, self.bet, 'loss_protection')
            db.update_balance(interaction.user.id, -loss)
            db.log_transaction(interaction.user.id, 'coinflip_loss', -loss)
            db.update_consecutive_wins(interaction.user.id, False)
            
            result_text = f"❌ Проигрыш! Вы потеряли {loss} {EMOJIS['coin']}"
            color = 0xff0000
        
        embed = discord.Embed(
            title=f"🪙 CoinFlip - Ставка: {self.bet} {EMOJIS['coin']}",
            description=f"Ваш выбор: {choice}\nРезультат: {result}\n\n{result_text}",
            color=color
        )
        await interaction.edit_original_response(embed=embed)

class BlackjackView(View):
    def __init__(self, user_id, bet):
        super().__init__(timeout=60)
        self.user_id = user_id
        self.bet = bet
        self.player_cards = []
        self.dealer_cards = []
        self.game_over = False
        
        # Начальная раздача
        self.player_cards = [self.draw_card(), self.draw_card()]
        self.dealer_cards = [self.draw_card(), self.draw_card()]

    def draw_card(self):
        return random.randint(1, 11)

    def calculate_score(self, cards):
        score = sum(cards)
        # Обработка тузов
        if score > 21 and 11 in cards:
            cards[cards.index(11)] = 1
            score = sum(cards)
        return score

def create_embed(self):
    page_cases = self.pages[self.current_page]
    embed = discord.Embed(
        title=f"🎁 Доступные кейсы (Страница {self.current_page + 1}/{self.total_pages})",
        color=0xff69b4
    )

    for case in page_cases:
        case_id = case[0]
        case_name = case[1]
        case_price = case[2]
        case_rewards = json.loads(case[3])

        # Формируем описание наград с правильными процентами
        rewards_text = ""
        for reward in case_rewards:
            chance_percent = reward['chance'] * 100
            if reward['type'] == 'coins':
                min_amount = reward['amount'][0]
                max_amount = reward['amount'][1]
                rewards_text += f"• 💰 Монеты: {min_amount}–{max_amount} ({chance_percent:.0f}%)\n"
            elif reward['type'] == 'special_item':
                item_name = reward['name']
                rewards_text += f"• 🎁 {item_name} ({chance_percent:.0f}%)\n"
            elif reward['type'] == 'bonus':
                multiplier = reward['multiplier']
                rewards_text += f"• ⭐ Бонус x{multiplier} ({chance_percent:.0f}%)\n"
            elif reward['type'] == 'loss':
                min_loss = reward['amount'][0]
                max_loss = reward['amount'][1]
                rewards_text += f"• 💀 Потеря: {min_loss}–{max_loss} монет ({chance_percent:.0f}%)\n"

        embed.add_field(
            name=f"{case_name} — {case_price} {EMOJIS['coin']} (ID: {case_id})",
            value=rewards_text,
            inline=False
        )

    return embed

    @discord.ui.button(label='Взять карту', style=discord.ButtonStyle.primary)
    async def hit(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Это не ваша игра!", ephemeral=True)
            return
        
        if self.game_over:
            await interaction.response.send_message("❌ Игра уже завершена!", ephemeral=True)
            return
        
        self.player_cards.append(self.draw_card())
        player_score = self.calculate_score(self.player_cards)
        
        if player_score > 21:
            self.game_over = True
            # Применяем баф защиты от проигрышей
            loss = db.apply_buff_to_amount(interaction.user.id, self.bet, 'loss_protection')
            db.update_balance(interaction.user.id, -loss)
            db.log_transaction(interaction.user.id, 'blackjack_loss', -loss)
            db.update_consecutive_wins(interaction.user.id, False)
        
        embed = self.create_embed()
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label='Остановиться', style=discord.ButtonStyle.secondary)
    async def stand(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Это не ваша игра!", ephemeral=True)
            return
        
        if self.game_over:
            await interaction.response.send_message("❌ Игра уже завершена!", ephemeral=True)
            return
        
        # Ход дилера
        while self.calculate_score(self.dealer_cards) < 17:
            self.dealer_cards.append(self.draw_card())
        
        self.game_over = True
        player_score = self.calculate_score(self.player_cards)
        dealer_score = self.calculate_score(self.dealer_cards)
        
        # Определение победителя
        if player_score > 21:
            # Уже обработано в hit
            pass
        elif dealer_score > 21 or player_score > dealer_score:
            base_winnings = self.bet * 2
            winnings = db.apply_buff_to_amount(interaction.user.id, base_winnings, 'blackjack_bonus')
            winnings = db.apply_buff_to_amount(interaction.user.id, winnings, 'game_bonus')
            winnings = db.apply_buff_to_amount(interaction.user.id, winnings, 'multiplier')
            winnings = db.apply_buff_to_amount(interaction.user.id, winnings, 'all_bonus')
            
            db.update_balance(interaction.user.id, winnings - self.bet)
            db.log_transaction(interaction.user.id, 'blackjack_win', winnings - self.bet)
            db.update_user_stat(interaction.user.id, 'blackjack_wins')
            db.update_consecutive_wins(interaction.user.id, True)
        elif player_score < dealer_score:
            loss = db.apply_buff_to_amount(interaction.user.id, self.bet, 'loss_protection')
            db.update_balance(interaction.user.id, -loss)
            db.log_transaction(interaction.user.id, 'blackjack_loss', -loss)
            db.update_consecutive_wins(interaction.user.id, False)
        # Ничья - деньги возвращаются
        
        embed = self.create_embed()
        await interaction.response.edit_message(embed=embed, view=self)

class DuelView(View):
    def __init__(self, challenger_id, target_id, bet):
        super().__init__(timeout=30)
        self.challenger_id = challenger_id
        self.target_id = target_id
        self.bet = bet

    @discord.ui.button(label='Принять дуэль', style=discord.ButtonStyle.success)
    async def accept(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.target_id:
            await interaction.response.send_message("❌ Это не ваш вызов на дуэль!", ephemeral=True)
            return
        
        # Проверяем балансы еще раз
        challenger_data = db.get_user(self.challenger_id)
        challenger_safe = get_user_data_safe(challenger_data)
        target_data = db.get_user(self.target_id)
        target_safe = get_user_data_safe(target_data)
        
        if challenger_safe['balance'] < self.bet or target_safe['balance'] < self.bet:
            await interaction.response.send_message("❌ У одного из участников недостаточно монет!", ephemeral=True)
            return
        
        # Определяем победителя с учетом бафов
        challenger_buffs = db.get_user_buffs(self.challenger_id)
        target_buffs = db.get_user_buffs(self.target_id)
        
        challenger_win_chance = 0.5
        target_win_chance = 0.5
        
        # Применяем бафы дуэлей
        if 'duel_bonus' in challenger_buffs:
            challenger_win_chance *= challenger_buffs['duel_bonus']['value']
        if 'duel_bonus' in target_buffs:
            target_win_chance *= target_buffs['duel_bonus']['value']
        
        # Нормализуем шансы
        total = challenger_win_chance + target_win_chance
        challenger_win_chance /= total
        target_win_chance /= total
        
        # Определяем победителя
        if random.random() < challenger_win_chance:
            winner_id = self.challenger_id
            loser_id = self.target_id
        else:
            winner_id = self.target_id
            loser_id = self.challenger_id
        
        # Передача монет
        base_winnings = self.bet * 2
        winnings = db.apply_buff_to_amount(winner_id, base_winnings, 'game_bonus')
        winnings = db.apply_buff_to_amount(winner_id, winnings, 'multiplier')
        winnings = db.apply_buff_to_amount(winner_id, winnings, 'all_bonus')
        
        db.update_balance(winner_id, winnings - self.bet)  # Чистый выигрыш
        db.update_balance(loser_id, -self.bet)
        
        db.log_transaction(winner_id, 'duel_win', winnings - self.bet, loser_id, "Победа в дуэли")
        db.log_transaction(loser_id, 'duel_loss', -self.bet, winner_id, "Поражение в дуэли")
        
        db.update_user_stat(winner_id, 'duels_won')
        db.update_consecutive_wins(winner_id, True)
        db.update_consecutive_wins(loser_id, False)
        
        winner = bot.get_user(winner_id)
        loser = bot.get_user(loser_id)
        
        embed = discord.Embed(
            title="⚔️ Дуэль завершена!",
            description=f"Победитель: {winner.mention}\nПроигравший: {loser.mention}",
            color=0x00ff00
        )
        embed.add_field(name="Ставка", value=f"{self.bet} {EMOJIS['coin']}", inline=True)
        embed.add_field(name="Выигрыш", value=f"{winnings - self.bet} {EMOJIS['coin']} (чистыми)", inline=True)
        
        # Показываем влияние бафов
        buffs_info = ""
        if challenger_buffs or target_buffs:
            if challenger_buffs:
                buffs_info += f"**{bot.get_user(self.challenger_id).display_name}**: " + ", ".join([f"{buff['item_name']}" for buff in challenger_buffs.values()]) + "\n"
            if target_buffs:
                buffs_info += f"**{bot.get_user(self.target_id).display_name}**: " + ", ".join([f"{buff['item_name']}" for buff in target_buffs.values()])
            embed.add_field(name="🎯 Влияние бафов", value=buffs_info, inline=False)
        
        await interaction.response.edit_message(embed=embed, view=None)

    @discord.ui.button(label='Отклонить дуэль', style=discord.ButtonStyle.danger)
    async def decline(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.target_id:
            await interaction.response.send_message("❌ Это не ваш вызов на дуэль!", ephemeral=True)
            return
        
        challenger = bot.get_user(self.challenger_id)
        embed = discord.Embed(
            title="⚔️ Дуэль отклонена",
            description=f"{interaction.user.mention} отклонил вызов от {challenger.mention}",
            color=0xff0000
        )
        await interaction.response.edit_message(embed=embed, view=None)

# Классы для пагинации
class ItemsPaginatedView(View):
    def __init__(self, pages, author_id):
        super().__init__(timeout=120)
        self.pages = pages
        self.current_page = 0
        self.total_pages = len(pages)
        self.author_id = author_id
        self.update_buttons()

    def update_buttons(self):
        self.previous_button.disabled = (self.current_page == 0)
        self.next_button.disabled = (self.current_page >= self.total_pages - 1)

    @discord.ui.button(label='⬅️ Назад', style=discord.ButtonStyle.secondary)
    async def previous_button(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.author_id:
            await interaction.response.send_message("❌ Это не ваша пагинация!", ephemeral=True)
            return
        
        if self.current_page > 0:
            self.current_page -= 1
            self.update_buttons()
            embed = self.create_embed()
            await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label='➡️ Вперед', style=discord.ButtonStyle.secondary)
    async def next_button(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.author_id:
            await interaction.response.send_message("❌ Это не ваша пагинация!", ephemeral=True)
            return
        
        if self.current_page < self.total_pages - 1:
            self.current_page += 1
            self.update_buttons()
            embed = self.create_embed()
            await interaction.response.edit_message(embed=embed, view=self)

    def create_embed(self):
        page_items = self.pages[self.current_page]
        embed = discord.Embed(
            title=f"📦 Все доступные предметы (Страница {self.current_page + 1}/{self.total_pages})",
            description="**Предметы автоматически активируются при получении и дают постоянные баффы!**",
            color=0x3498db
        )
        
        for item in page_items:
            try:
                item_id = item[0] if len(item) > 0 else "N/A"
                item_name = item[1] if len(item) > 1 else "Неизвестный предмет"
                item_description = item[2] if len(item) > 2 else "Описание отсутствует"
                item_value = item[3] if len(item) > 3 else 0
                item_rarity = item[4] if len(item) > 4 else "common"
                buff_type = item[5] if len(item) > 5 else None
                buff_value = item[6] if len(item) > 6 else 1.0
                buff_description = item[7] if len(item) > 7 else "Без особого эффекта"
                
                rarity_emoji = {
                    'common': '⚪',
                    'uncommon': '🟢', 
                    'rare': '🔵',
                    'epic': '🟣',
                    'legendary': '🟠',
                    'mythic': '🟡'
                }.get(item_rarity, '⚪')
                
                effect_details = self.get_effect_details(buff_type, buff_value, buff_description)
                
                field_value = f"**Описание:** {item_description}\n"
                field_value += f"**Эффект:** {effect_details}\n"
                field_value += f"**Ценность:** {item_value} {EMOJIS['coin']}\n"
                field_value += f"**Редкость:** {rarity_emoji} {item_rarity.capitalize()}"
                
                embed.add_field(
                    name=f"{item_name} (ID: {item_id})",
                    value=field_value,
                    inline=False
                )
                
            except Exception as e:
                print(f"⚠️ Ошибка обработки предмета {item}: {e}")
                continue
        
        embed.set_footer(text="💡 Предметы можно получить из кейсов или купить на маркетплейсе")
        return embed

    def get_effect_details(self, buff_type, buff_value, buff_description):
        if not buff_type:
            return "Без особого эффекта"
        
        effect_map = {
            'daily_bonus': f"📅 Увеличивает ежедневную награду в {buff_value}x раза",
            'case_bonus': f"🎁 Увеличивает награды из кейсов в {buff_value}x раза", 
            'game_bonus': f"🎮 Увеличивает выигрыши в играх в {buff_value}x раза",
            'steal_protection': f"🛡️ Уменьшает шанс кражи у вас в {buff_value}x раза",
            'steal_bonus': f"🦹 Увеличивает шанс успешной кражи в {buff_value}x раза",
            'roulette_bonus': f"🎰 Увеличивает выигрыш в рулетке в {buff_value}x раза",
            'multiplier': f"✨ Умножает все награды в {buff_value}x раза",
            'coinflip_bonus': f"🪙 Увеличивает выигрыш в coinflip в {buff_value}x раза",
            'blackjack_bonus': f"🃏 Увеличивает выигрыш в блэкджеке в {buff_value}x раза",
            'slot_bonus': f"🎰 Увеличивает выигрыш в слотах в {buff_value}x раза",
            'loss_protection': f"💎 Уменьшает проигрыши в {buff_value}x раза",
            'quest_bonus': f"🗺️ Увеличивает награды за квесты в {buff_value}x раза",
            'all_bonus': f"🌟 Увеличивает все награды в {buff_value}x раза",
            'transfer_bonus': f"💸 Уменьшает комиссию переводов в {buff_value}x раза",
            'duel_bonus': f"⚔️ Увеличивает шанс победы в дуэлях в {buff_value}x раза",
            'xp_bonus': f"📚 Увеличивает получаемый опыт в {buff_value}x раза",
            'steal_chance': f"🎯 Увеличивает шанс кражи в {buff_value}x раза"
        }
        
        return effect_map.get(buff_type, buff_description)

class MyItemsPaginatedView(View):
    def __init__(self, pages, author_id):
        super().__init__(timeout=120)
        self.pages = pages
        self.current_page = 0
        self.total_pages = len(pages)
        self.author_id = author_id
        self.author_name = "Пользователь"
        self.update_buttons()
        
        try:
            user = bot.get_user(author_id)
            if user:
                self.author_name = user.display_name
        except:
            pass

    def update_buttons(self):
        self.previous_button.disabled = (self.current_page == 0)
        self.next_button.disabled = (self.current_page >= self.total_pages - 1)

    @discord.ui.button(label='⬅️ Назад', style=discord.ButtonStyle.secondary)
    async def previous_button(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.author_id:
            await interaction.response.send_message("❌ Это не ваша пагинация!", ephemeral=True)
            return
        
        if self.current_page > 0:
            self.current_page -= 1
            self.update_buttons()
            embed = self.create_embed()
            await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label='➡️ Вперед', style=discord.ButtonStyle.secondary)
    async def next_button(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.author_id:
            await interaction.response.send_message("❌ Это не ваша пагинация!", ephemeral=True)
            return
        
        if self.current_page < self.total_pages - 1:
            self.current_page += 1
            self.update_buttons()
            embed = self.create_embed()
            await interaction.response.edit_message(embed=embed, view=self)

    def create_embed(self):
        page_items = self.pages[self.current_page]
        embed = discord.Embed(
            title=f"🎒 Инвентарь {self.author_name} (Страница {self.current_page + 1}/{self.total_pages})",
            description="**Активные предметы автоматически дают бонусы! Самый сильный предмет каждого типа действует.**",
            color=0x3498db
        )
        
        user = bot.get_user(self.author_id)
        self.author_name = user.display_name if user else "Пользователь"
        
        for item_data, count in page_items:
            try:
                item_name = item_data[1] if len(item_data) > 1 else "Неизвестный предмет"
                item_description = item_data[2] if len(item_data) > 2 else "Описание отсутствует"
                item_rarity = item_data[4] if len(item_data) > 4 else "common"
                buff_description = item_data[7] if len(item_data) > 7 else "Без особого эффекта"
                
                rarity_emoji = {
                    'common': '⚪',
                    'uncommon': '🟢', 
                    'rare': '🔵',
                    'epic': '🟣',
                    'legendary': '🟠',
                    'mythic': '🟡'
                }.get(item_rarity, '⚪')
                
                field_value = f"**Количество:** ×{count}\n"
                field_value += f"**Описание:** {item_description}\n"
                field_value += f"**Эффект:** {buff_description}\n"
                field_value += f"**Редкость:** {rarity_emoji} {item_rarity.capitalize()}"
                
                embed.add_field(
                    name=f"{item_name}",
                    value=field_value,
                    inline=False
                )
                
            except Exception as e:
                print(f"⚠️ Ошибка обработки предмета в инвентаре: {e}")
                continue
        
        try:
            buffs = db.get_user_buffs(self.author_id)
            if buffs:
                buffs_text = "\n".join([f"• **{buff['item_name']}**: {buff['description']}" for buff in buffs.values()])
                embed.add_field(
                    name="🎯 Активные бафы (самые сильные)",
                    value=buffs_text,
                    inline=False
                )
        except Exception as e:
            print(f"⚠️ Ошибка получения бафов: {e}")
        
        embed.set_footer(text="💡 Предметы можно продать на маркетплейсе или использовать для улучшения")
        return embed

# КОМАНДЫ БОТА

# Экономические команды
@bot.tree.command(name="balance", description="Показать ваш баланс")
@app_commands.describe(user="Пользователь, чей баланс показать (опционально)")
async def balance(interaction: discord.Interaction, user: discord.Member = None):
    try:
        user = user or interaction.user
        
        db.get_user(user.id)
        user_data = db.get_user(user.id)
        user_safe = get_user_data_safe(user_data)
        
        cursor = db.conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM achievements WHERE user_id = %s', (user.id,))
        achievements_result = cursor.fetchone()
        achievements_count = achievements_result[0] if achievements_result else 0
        
        buffs = {}
        try:
            buffs = db.get_user_buffs(user.id)
        except Exception as e:
            print(f"⚠️ Ошибка получения бафов для пользователя {user.id}: {e}")
        
        embed = discord.Embed(
            title=f"{EMOJIS['coin']} Баланс {user.display_name}",
            color=0xffd700
        )
        embed.add_field(name="Баланс", value=f"{user_safe['balance']} {EMOJIS['coin']}", inline=True)
        embed.add_field(name="Ежедневная серия", value=f"{user_safe['daily_streak']} дней", inline=True)
        embed.add_field(name="Достижения", value=f"{achievements_count}/{len(ACHIEVEMENTS)}", inline=True)
        
        if buffs:
            buffs_text = "\n".join([f"• {buff['item_name']}: {buff['description']}" for buff in buffs.values()])
            embed.add_field(name="🎯 Активные бафы", value=buffs_text, inline=False)
        
        if user.avatar:
            embed.set_thumbnail(url=user.avatar.url)
        
        await interaction.response.send_message(embed=embed)
        
    except Exception as e:
        print(f"❌ Критическая ошибка в команде balance: {e}")
        error_embed = discord.Embed(
            title="❌ Ошибка",
            description="Произошла ошибка при получении данных. Попробуйте позже.",
            color=0xff0000
        )
        await interaction.response.send_message(embed=error_embed, ephemeral=True)

@bot.tree.command(name="daily", description="Получить ежедневную награду")
async def daily(interaction: discord.Interaction):
    try:
        user_data = db.get_user_safe(interaction.user.id)
        user_safe = get_user_data_safe(user_data)
        
        last_daily_str = user_safe['last_daily']
        daily_streak = user_safe['daily_streak']
        
        last_daily = None
        if last_daily_str:
            try:
                last_daily = datetime.datetime.fromisoformat(last_daily_str)
            except (ValueError, TypeError):
                last_daily = None
        
        now = datetime.datetime.now()
        
        if last_daily and (now - last_daily).days < 1:
            await interaction.response.send_message("Вы уже получали ежедневную награду сегодня!", ephemeral=True)
            return
        
        streak = daily_streak + 1 if last_daily and (now - last_daily).days == 1 else 1
        base_reward = 100
        streak_bonus = streak * 10
        reward = base_reward + streak_bonus
        
        reward = db.apply_buff_to_amount(interaction.user.id, reward, 'daily_bonus')
        reward = db.apply_buff_to_amount(interaction.user.id, reward, 'multiplier')
        reward = db.apply_buff_to_amount(interaction.user.id, reward, 'all_bonus')
        
        db.update_balance(interaction.user.id, reward)
        cursor = db.conn.cursor()
        cursor.execute('UPDATE users SET daily_streak = %s, last_daily = %s WHERE user_id = %s', 
                       (streak, now.isoformat(), interaction.user.id))
        db.conn.commit()
        db.log_transaction(interaction.user.id, 'daily', reward)
        db.update_user_stat(interaction.user.id, 'daily_claimed')
        
        # Принудительная проверка достижений
        new_achievements = db.check_achievements(interaction.user.id)
        
        embed = discord.Embed(
            title=f"{EMOJIS['daily']} Ежедневная награда",
            description=f"Награда: {reward} {EMOJIS['coin']}\nСерия: {streak} дней\nБонус за серию: +{streak_bonus} {EMOJIS['coin']}",
            color=0x00ff00
        )
        
        if new_achievements:
            achievements_text = "\n".join([f"🎉 {ACHIEVEMENTS[ach_id]['name']} (+{ACHIEVEMENTS[ach_id]['reward']} {EMOJIS['coin']})" for ach_id in new_achievements])
            embed.add_field(name="Новые достижения!", value=achievements_text, inline=False)
        
        await interaction.response.send_message(embed=embed)
        
    except Exception as e:
        print(f"❌ Ошибка в команде daily: {e}")
        error_embed = discord.Embed(
            title="❌ Ошибка",
            description="Не удалось получить ежедневную награду. Попробуйте позже.",
            color=0xff0000
        )
        await interaction.response.send_message(embed=error_embed, ephemeral=True)

# Команды кейсов
@bot.tree.command(name="cases", description="Показать список доступных кейсов")
async def cases_list(interaction: discord.Interaction):
    try:
        cases = db.get_cases()
        
        if not cases:
            await interaction.response.send_message("Кейсы не найдены!", ephemeral=True)
            return
        
        pages = []
        current_page = []
        
        for i, case in enumerate(cases):
            if i > 0 and i % 3 == 0:
                pages.append(current_page)
                current_page = []
            current_page.append(case)
        
        if current_page:
            pages.append(current_page)
        
        view = ImprovedCasesView(pages, interaction.user.id)
        embed = view.create_embed()
        await interaction.response.send_message(embed=embed, view=view)
        
    except Exception as e:
        print(f"❌ Ошибка в команде cases: {e}")
        await interaction.response.send_message("❌ Произошла ошибка при загрузке кейсов!", ephemeral=True)

@bot.tree.command(name="open_case", description="Открыть кейс")
@app_commands.describe(case_id="ID кейса для открытия")
async def open_case(interaction: discord.Interaction, case_id: int):
    try:
        case_data = db.get_case(case_id)
        if not case_data:
            await interaction.response.send_message("❌ Кейс с таким ID не найден!", ephemeral=True)
            return
        
        user_data = db.get_user(interaction.user.id)
        user_safe = get_user_data_safe(user_data)
        
        case_price = case_data[2]
        if user_safe['balance'] < case_price:
            await interaction.response.send_message("❌ Недостаточно монет для открытия этого кейса!", ephemeral=True)
            return
        
        view = CaseView(case_id, interaction.user.id)
        embed = discord.Embed(
            title=f"🎁 {case_data[1]}",
            description=f"Стоимость: {case_price} {EMOJIS['coin']}\n\nНажмите кнопку ниже чтобы открыть кейс!",
            color=0xff69b4
        )
        
        await interaction.response.send_message(embed=embed, view=view)
        
    except Exception as e:
        print(f"❌ Ошибка в команде open_case: {e}")
        await interaction.response.send_message("❌ Произошла ошибка при открытии кейса!", ephemeral=True)

@bot.tree.command(name="admin_boost_chances", description="Повысить шансы во всех кейсах на 3-5% (админ)")
@is_admin()
async def admin_boost_chances(interaction: discord.Interaction):
    try:
        cursor = db.conn.cursor()
        cursor.execute('DELETE FROM cases')
        
        boosted_cases = [
            ('📦 Малый кейс', 50, json.dumps([
                {'type': 'coins', 'amount': [10, 40], 'chance': 0.77, 'description': 'Небольшая сумма монет'},
                {'type': 'coins', 'amount': [41, 100], 'chance': 0.18, 'description': 'Средняя сумма монет'},
                {'type': 'coins', 'amount': [101, 300], 'chance': 0.05, 'description': 'Хорошая сумма монет'}
            ])),
            ('📦 Средний кейс', 150, json.dumps([
                {'type': 'coins', 'amount': [50, 120], 'chance': 0.66, 'description': 'Надежная сумма монет'},
                {'type': 'coins', 'amount': [121, 300], 'chance': 0.2, 'description': 'Отличная сумма монет'},
                {'type': 'special_item', 'name': 'Магический свиток', 'chance': 0.09, 'description': 'Увеличивает выигрыш в рулетке на 25%'},
                {'type': 'coins', 'amount': [301, 800], 'chance': 0.05, 'description': 'Отличный выигрыш'}
            ]))
        ]
        
        for case in boosted_cases:
            cursor.execute('INSERT INTO cases (name, price, rewards) VALUES (%s, %s, %s)', case)
        
        db.conn.commit()
        
        embed = discord.Embed(
            title="✅ Шансы увеличены!",
            description="Во всех кейсах шансы на хорошие награды увеличены на 3-5%, а на плохие уменьшены",
            color=0x00ff00
        )
        embed.add_field(
            name="📊 Основные изменения",
            value="• **Предметы**: +3-5% шанс\n• **Бонусы**: +3% шанс\n• **Минусы**: -3-5% шанс\n• **Монеты**: баланс смещен в сторону средних/больших сумм",
            inline=False
        )
        
        await interaction.response.send_message(embed=embed)
        
    except Exception as e:
        print(f"❌ Ошибка при увеличении шансов: {e}")
        error_embed = discord.Embed(
            title="❌ Ошибка",
            description=f"Не удалось увеличить шансы: {str(e)}",
            color=0xff0000
        )
        await interaction.response.send_message(embed=error_embed, ephemeral=True)

# МИНИ-ИГРЫ
@bot.tree.command(name="coinflip", description="Подбросить монету на ставку (50/50 шанс)")
@app_commands.describe(bet="Ставка в монетах")
async def coinflip(interaction: discord.Interaction, bet: int):
    user_data = db.get_user(interaction.user.id)
    user_safe = get_user_data_safe(user_data)
    
    if user_safe['balance'] < bet:
        await interaction.response.send_message("Недостаточно монет!", ephemeral=True)
        return
    
    embed = discord.Embed(
        title=f"🪙 Подбрасывание монеты",
        description=f"Ставка: {bet} {EMOJIS['coin']}\nВыберите сторону монеты:",
        color=0xffd700
    )
    
    view = CoinFlipView(interaction.user.id, bet)
    await interaction.response.send_message(embed=embed, view=view)

@bot.tree.command(name="blackjack", description="Сыграть в блэкджек")
@app_commands.describe(bet="Ставка в монетах")
async def blackjack(interaction: discord.Interaction, bet: int):
    user_data = db.get_user(interaction.user.id)
    user_safe = get_user_data_safe(user_data)
    
    if user_safe['balance'] < bet:
        await interaction.response.send_message("Недостаточно монет!", ephemeral=True)
        return
    
    if bet <= 0:
        await interaction.response.send_message("Ставка должна быть положительной!", ephemeral=True)
        return
    
    view = BlackjackView(interaction.user.id, bet)
    embed = view.create_embed()
    
    await interaction.response.send_message(embed=embed, view=view)

@bot.tree.command(name="slots", description="Играть в игровые автоматы")
@app_commands.describe(bet="Ставка в монетах")
async def slots(interaction: discord.Interaction, bet: int):
    try:
        user_data = db.get_user(interaction.user.id)
        user_safe = get_user_data_safe(user_data)
        
        if user_safe['balance'] < bet:
            await interaction.response.send_message("Недостаточно монет!", ephemeral=True)
            return
    
        symbols = ['🍒', '🍋', '🍊', '🍇', '🔔', '💎', '7️⃣']
        
        embed = discord.Embed(title="🎰 Игровые автоматы", description="Вращение...", color=0xff69b4)
        await interaction.response.send_message(embed=embed)
        
        for i in range(3):
            await asyncio.sleep(0.5)
            slot_result = [random.choice(symbols) for _ in range(3)]
            embed.description = f"🎰 | {' | '.join(slot_result)} | 🎰"
            await interaction.edit_original_response(embed=embed)
        
        await asyncio.sleep(1)
        
        final_result = []
        if random.random() < 0.4:
            winning_symbol = random.choice(symbols)
            if random.random() < 0.1:
                final_result = [winning_symbol, winning_symbol, winning_symbol]
            else:
                final_result = [winning_symbol, winning_symbol, random.choice(symbols)]
                random.shuffle(final_result)
        else:
            final_result = [random.choice(symbols) for _ in range(3)]
        
        embed.description = f"🎰 | {' | '.join(final_result)} | 🎰"
        
        if final_result[0] == final_result[1] == final_result[2]:
            if final_result[0] == '💎':
                multiplier = 50
                # ИСПРАВЛЕНИЕ: Обновляем статистику слотов при джекпоте
                db.update_user_stat(interaction.user.id, 'slot_wins')
            elif final_result[0] == '7️⃣':
                multiplier = 25
            elif final_result[0] == '🔔':
                multiplier = 15
            else:
                multiplier = 8
            
            base_winnings = bet * multiplier
            winnings = db.apply_buff_to_amount(interaction.user.id, base_winnings, 'slot_bonus')
            winnings = db.apply_buff_to_amount(interaction.user.id, winnings, 'game_bonus')
            winnings = db.apply_buff_to_amount(interaction.user.id, winnings, 'multiplier')
            winnings = db.apply_buff_to_amount(interaction.user.id, winnings, 'all_bonus')
            
            db.update_balance(interaction.user.id, winnings)
            db.log_transaction(interaction.user.id, 'slots_win', winnings, description=f"ДЖЕКПОТ в слотах x{multiplier}")
            db.update_consecutive_wins(interaction.user.id, True)
            
            result_text = f"🎉 ДЖЕКПОТ! x{multiplier}\nВыигрыш: {winnings} {EMOJIS['coin']}"
            color = 0x00ff00
        elif final_result[0] == final_result[1] or final_result[1] == final_result[2]:
            multiplier = 3
            base_winnings = bet * multiplier
            winnings = db.apply_buff_to_amount(interaction.user.id, base_winnings, 'slot_bonus')
            winnings = db.apply_buff_to_amount(interaction.user.id, winnings, 'game_bonus')
            winnings = db.apply_buff_to_amount(interaction.user.id, winnings, 'multiplier')
            winnings = db.apply_buff_to_amount(interaction.user.id, winnings, 'all_bonus')
            
            db.update_balance(interaction.user.id, winnings)
            db.log_transaction(interaction.user.id, 'slots_win', winnings, description=f"Победа в слотах x{multiplier}")
            db.update_consecutive_wins(interaction.user.id, True)
            
            result_text = f"✅ Два в ряд! x{multiplier}\nВыигрыш: {winnings} {EMOJIS['coin']}"
            color = 0x00ff00
        else:
            loss = db.apply_buff_to_amount(interaction.user.id, bet, 'loss_protection')
            db.update_balance(interaction.user.id, -loss)
            db.log_transaction(interaction.user.id, 'slots_loss', -loss, description="Проигрыш в слотах")
            db.update_consecutive_wins(interaction.user.id, False)
            
            result_text = f"❌ Повезет в следующий раз!\nПотеряно: {loss} {EMOJIS['coin']}"
            color = 0xff0000
        
        embed.add_field(name="Результат", value=result_text, inline=False)
        embed.add_field(name="Ставка", value=f"{bet} {EMOJIS['coin']}", inline=True)
        embed.color = color
        
        await interaction.edit_original_response(embed=embed)
        
    except Exception as e:
        print(f"❌ Ошибка в команде slots: {e}")
        await interaction.response.send_message("❌ Произошла ошибка в слотах!", ephemeral=True)

@bot.tree.command(name="roulette", description="Сыграть в рулетку")
@app_commands.describe(bet="Ставка в монетах")
async def roulette(interaction: discord.Interaction, bet: int):
    try:
        user_data = db.get_user(interaction.user.id)
        user_safe = get_user_data_safe(user_data)
        
        if user_safe['balance'] < bet:
            await interaction.response.send_message("Недостаточно монет!", ephemeral=True)
            return
        
        winning_number = random.randint(0, 36)
        user_number = random.randint(0, 36)
        
        embed = discord.Embed(title="🎰 Рулетка вращается...", color=0xffd700)
        await interaction.response.send_message(embed=embed)
        
        for i in range(3):
            await asyncio.sleep(1)
            embed.description = "⏳" * (i + 1)
            await interaction.edit_original_response(embed=embed)
        
        await asyncio.sleep(1)
        
        if user_number == winning_number:
            multiplier = 35
            base_winnings = bet * multiplier
            winnings = db.apply_buff_to_amount(interaction.user.id, base_winnings, 'roulette_bonus')
            winnings = db.apply_buff_to_amount(interaction.user.id, winnings, 'game_bonus')
            winnings = db.apply_buff_to_amount(interaction.user.id, winnings, 'multiplier')
            winnings = db.apply_buff_to_amount(interaction.user.id, winnings, 'all_bonus')
            
            db.update_balance(interaction.user.id, winnings)
            db.log_transaction(interaction.user.id, 'roulette_win', winnings, description="Победа в рулетке")
            db.update_user_stat(interaction.user.id, 'roulette_wins')
            db.update_consecutive_wins(interaction.user.id, True)
            
            result_text = f"🎉 ДЖЕКПОТ! Ваше число: {user_number}\nВыпало: {winning_number}\nВыигрыш: {winnings} {EMOJIS['coin']} (x{multiplier})"
            color = 0x00ff00
        else:
            loss = db.apply_buff_to_amount(interaction.user.id, bet, 'loss_protection')
            db.update_balance(interaction.user.id, -loss)
            db.log_transaction(interaction.user.id, 'roulette_loss', -loss, description="Проигрыш в рулетке")
            db.update_consecutive_wins(interaction.user.id, False)
            
            result_text = f"💀 Проигрыш! Ваше число: {user_number}\nВыпало: {winning_number}\nПотеряно: {loss} {EMOJIS['coin']}"
            color = 0xff0000
        
        embed = discord.Embed(
            title=f"🎰 Рулетка - Ставка: {bet} {EMOJIS['coin']}",
            description=result_text,
            color=color
        )
        await interaction.edit_original_response(embed=embed)
        
    except Exception as e:
        print(f"❌ Ошибка в команде roulette: {e}")
        await interaction.response.send_message("❌ Произошла ошибка в рулетке!", ephemeral=True)

# ДУЭЛЬ
@bot.tree.command(name="duel", description="Вызвать пользователя на дуэль")
@app_commands.describe(user="Пользователь для дуэли", bet="Ставка в монетах")
async def duel(interaction: discord.Interaction, user: discord.Member, bet: int):
    if user.id == interaction.user.id:
        await interaction.response.send_message("Нельзя вызвать на дуэль самого себя!", ephemeral=True)
        return
    
    if bet <= 0:
        await interaction.response.send_message("Ставка должна быть положительной!", ephemeral=True)
        return
    
    user_data = db.get_user(interaction.user.id)
    user_safe = get_user_data_safe(user_data)
    
    if user_safe['balance'] < bet:
        await interaction.response.send_message("У вас недостаточно монет для дуэли!", ephemeral=True)
        return
    
    target_data = db.get_user(user.id)
    target_safe = get_user_data_safe(target_data)
    
    if target_safe['balance'] < bet:
        await interaction.response.send_message(f"У {user.mention} недостаточно монет для дуэли!", ephemeral=True)
        return
    
    embed = discord.Embed(
        title=f"{EMOJIS['duel']} Вызов на дуэль!",
        description=f"{interaction.user.mention} вызывает {user.mention} на дуэль!",
        color=0xff0000
    )
    embed.add_field(name="Ставка", value=f"{bet} {EMOJIS['coin']}", inline=True)
    
    challenger_buffs = db.get_user_buffs(interaction.user.id)
    target_buffs = db.get_user_buffs(user.id)
    
    if challenger_buffs or target_buffs:
        buffs_text = ""
        if challenger_buffs:
            buffs_text += f"**{interaction.user.display_name}**: " + ", ".join([f"{buff['item_name']}" for buff in challenger_buffs.values()]) + "\n"
        if target_buffs:
            buffs_text += f"**{user.display_name}**: " + ", ".join([f"{buff['item_name']}" for buff in target_buffs.values()])
        embed.add_field(name="🎯 Активные бафы", value=buffs_text, inline=False)
    
    embed.add_field(name="Время на ответ", value="30 секунд", inline=True)
    embed.set_footer(text="Победитель забирает всю ставку!")
    
    view = DuelView(interaction.user.id, user.id, bet)
    await interaction.response.send_message(embed=embed, view=view)

# КРАЖА
# В команде steal исправляем базовый шанс и логику
@bot.tree.command(name="steal", description="Попытаться украсть монеты у другого пользователя (КД 30 мин)")
@app_commands.describe(user="Пользователь, у которого крадем")
@app_commands.checks.cooldown(1, 1800.0, key=lambda i: (i.guild_id, i.user.id))
async def steal(interaction: discord.Interaction, user: discord.Member):
    if user.id == interaction.user.id:
        await interaction.response.send_message("Нельзя красть у себя!", ephemeral=True)
        return
    
    thief_data = db.get_user(interaction.user.id)
    thief_safe = get_user_data_safe(thief_data)
    target_data = db.get_user(user.id)
    target_safe = get_user_data_safe(target_data)
    
    if thief_safe['balance'] < 10:
        await interaction.response.send_message("Нужно минимум 10 монет для кражи!", ephemeral=True)
        return
    
    if target_safe['balance'] < 10:
        await interaction.response.send_message("У цели недостаточно монет для кражи!", ephemeral=True)
        return
    
    max_steal = min(int(target_safe['balance'] * 0.2), 1000)
    min_steal = max(int(target_safe['balance'] * 0.05), 10)
    
    if max_steal < min_steal:
        amount = min_steal
    else:
        amount = random.randint(min_steal, max_steal)
    
    # ИСПРАВЛЕНИЕ: Увеличиваем базовый шанс и улучшаем логику бафов
    base_success_chance = 0.45  # Увеличили с 0.3 до 0.45
    
    # Применяем бафы вора
    success_chance = base_success_chance
    thief_buffs = db.get_user_buffs(interaction.user.id)
    
    if 'steal_chance' in thief_buffs:
        success_chance *= thief_buffs['steal_chance']['value']
    if 'steal_bonus' in thief_buffs:
        success_chance *= thief_buffs['steal_bonus']['value']
    
    # Применяем защиту цели
    target_buffs = db.get_user_buffs(user.id)
    if 'steal_protection' in target_buffs:
        success_chance *= (1 - (1 - target_buffs['steal_protection']['value']))
    
    # Гарантируем минимальный шанс 5% и максимальный 80%
    success_chance = max(0.05, min(0.8, success_chance))
    
    if random.random() <= success_chance:
        stolen_amount = db.apply_buff_to_amount(interaction.user.id, amount, 'multiplier')
        stolen_amount = db.apply_buff_to_amount(interaction.user.id, stolen_amount, 'all_bonus')
        
        db.update_balance(interaction.user.id, stolen_amount)
        db.update_balance(user.id, -amount)
        db.log_transaction(interaction.user.id, 'steal', stolen_amount, user.id, "Успешная кража")
        db.update_user_stat(interaction.user.id, 'steals_successful')
        db.update_consecutive_wins(interaction.user.id, True)
        
        embed = discord.Embed(
            title=f"{EMOJIS['steal']} Успешная кража!",
            description=f"{interaction.user.mention} украл {stolen_amount} {EMOJIS['coin']} у {user.mention}!",
            color=0x00ff00
        )
        embed.add_field(name="Шанс успеха", value=f"{success_chance*100:.1f}%", inline=True)
        embed.add_field(name="Исходная сумма", value=f"{amount} {EMOJIS['coin']}", inline=True)
    else:
        penalty = min(amount // 3, 50)  # Уменьшили штраф
        actual_penalty = db.apply_buff_to_amount(interaction.user.id, penalty, 'loss_protection')
        
        db.update_balance(interaction.user.id, -actual_penalty)
        db.log_transaction(interaction.user.id, 'steal_fail', -actual_penalty, user.id, "Неудачная кража")
        db.update_user_stat(interaction.user.id, 'steals_failed')
        db.update_consecutive_wins(interaction.user.id, False)
        
        embed = discord.Embed(
            title=f"{EMOJIS['lose']} Кража провалилась!",
            description=f"{interaction.user.mention} оштрафован на {actual_penalty} {EMOJIS['coin']}!",
            color=0xff0000
        )
        embed.add_field(name="Шанс успеха", value=f"{success_chance*100:.1f}%", inline=True)
    
    await interaction.response.send_message(embed=embed)

@steal.error
async def steal_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    if isinstance(error, app_commands.CommandOnCooldown):
        minutes = int(error.retry_after // 60)
        seconds = int(error.retry_after % 60)
        
        await interaction.response.send_message(
            f"❌ Следующую кражу можно совершить через {minutes} минут {seconds:02d} секунд",
            ephemeral=True
        )
    else:
        raise error

# ДОПОЛНИТЕЛЬНЫЕ КОМАНДЫ
@bot.tree.command(name="myitems", description="Показать ваши предметы с пагинацией")
async def myitems(interaction: discord.Interaction):
    try:
        inventory = db.get_user_inventory_safe(interaction.user.id)
        items = inventory.get("items", {})
        
        if not items:
            embed = discord.Embed(
                title="🎒 Ваш инвентарь",
                description="У вас пока нет предметов. Открывайте кейсы или покупайте предметы на маркетплейсе!",
                color=0x3498db
            )
            await interaction.response.send_message(embed=embed)
            return
        
        # Получаем информацию о предметах
        user_items = []
        for item_id, count in items.items():
            try:
                if not str(item_id).isdigit():
                    continue
                    
                item_data = db.get_item(int(item_id))
                if item_data:
                    user_items.append((item_data, count))
            except Exception as e:
                print(f"⚠️ Ошибка обработки предмета {item_id}: {e}")
                continue
        
        if not user_items:
            embed = discord.Embed(
                title="🎒 Ваш инвентарь",
                description="Не удалось загрузить информацию о предметах.",
                color=0xff0000
            )
            await interaction.response.send_message(embed=embed)
            return
        
        # Создаем страницы
        pages = []
        current_page = []
        
        for i, (item_data, count) in enumerate(user_items):
            if i > 0 and i % 3 == 0:
                pages.append(current_page)
                current_page = []
            current_page.append((item_data, count))
        
        if current_page:
            pages.append(current_page)
        
        view = MyItemsPaginatedView(pages, interaction.user.id)
        embed = view.create_embed()
        
        await interaction.response.send_message(embed=embed, view=view)
        
    except Exception as e:
        print(f"❌ Ошибка в команде myitems: {e}")
        error_embed = discord.Embed(
            title="❌ Ошибка загрузки инвентаря",
            description="Произошла ошибка при загрузке ваших предметов. Попробуйте позже.",
            color=0xff0000
        )
        await interaction.response.send_message(embed=error_embed, ephemeral=True)

@bot.tree.command(name="pay", description="Перевести монеты другому пользователю")
@app_commands.describe(user="Пользователь для перевода", amount="Количество монет")
async def pay(interaction: discord.Interaction, user: discord.Member, amount: int):
    if user.id == interaction.user.id:
        await interaction.response.send_message("Нельзя переводить самому себе!", ephemeral=True)
        return
    
    if amount <= 0:
        await interaction.response.send_message("Сумма перевода должна быть положительной!", ephemeral=True)
        return
    
    user_data = db.get_user(interaction.user.id)
    user_safe = get_user_data_safe(user_data)
    
    if user_safe['balance'] < amount:
        await interaction.response.send_message("Недостаточно монет для перевода!", ephemeral=True)
        return
    
    # Применяем комиссию за перевод (если есть баф)
    commission_rate = 0.1  # 10% комиссия по умолчанию
    user_buffs = db.get_user_buffs(interaction.user.id)
    if 'transfer_bonus' in user_buffs:
        commission_rate *= user_buffs['transfer_bonus']['value']
    
    commission = int(amount * commission_rate)
    final_amount = amount - commission
    
    db.update_balance(interaction.user.id, -amount)
    db.update_balance(user.id, final_amount)
    
    db.log_transaction(interaction.user.id, 'transfer', -amount, user.id, f"Перевод пользователю {user.name}")
    db.log_transaction(user.id, 'transfer_receive', final_amount, interaction.user.id, f"Получено от {interaction.user.name}")
    
    embed = discord.Embed(
        title="💸 Перевод выполнен!",
        description=f"{interaction.user.mention} перевел {user.mention} {final_amount} {EMOJIS['coin']}",
        color=0x00ff00
    )
    embed.add_field(name="Сумма перевода", value=f"{amount} {EMOJIS['coin']}", inline=True)
    embed.add_field(name="Комиссия", value=f"{commission} {EMOJIS['coin']}", inline=True)
    embed.add_field(name="Получено", value=f"{final_amount} {EMOJIS['coin']}", inline=True)
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="giftcase", description="Подарить кейс другому пользователю")
@app_commands.describe(user="Пользователь для подарка", case_id="ID кейса")
async def giftcase(interaction: discord.Interaction, user: discord.Member, case_id: int):
    if user.id == interaction.user.id:
        await interaction.response.send_message("Нельзя дарить самому себе!", ephemeral=True)
        return
    
    case_data = db.get_case(case_id)
    if not case_data:
        await interaction.response.send_message("❌ Кейс с таким ID не найден!", ephemeral=True)
        return
    
    user_data = db.get_user(interaction.user.id)
    user_safe = get_user_data_safe(user_data)
    
    case_price = case_data[2]
    if user_safe['balance'] < case_price:
        await interaction.response.send_message("❌ Недостаточно монет для покупки кейса в подарок!", ephemeral=True)
        return
    
    # Покупаем кейс и добавляем в инвентарь получателя
    db.update_balance(interaction.user.id, -case_price)
    db.add_case_to_inventory(user.id, case_id, case_data[1], source=f"gift from {interaction.user.name}")
    
    db.log_transaction(interaction.user.id, 'gift_case', -case_price, user.id, f"Подарок кейса: {case_data[1]}")
    db.update_user_stat(interaction.user.id, 'gifts_sent')
    
    embed = discord.Embed(
        title="🎁 Кейс подарен!",
        description=f"{interaction.user.mention} подарил {user.mention} кейс **{case_data[1]}**!",
        color=0x00ff00
    )
    embed.add_field(name="Стоимость", value=f"{case_price} {EMOJIS['coin']}", inline=True)
    embed.set_footer(text="Получатель может открыть кейс с помощью /openmycase")
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="openmycase", description="Открыть кейс из вашего инвентаря")
@app_commands.describe(case_id="ID кейса из инвентаря")
async def openmycase(interaction: discord.Interaction, case_id: int):
    db.get_user(interaction.user.id)
    
    inventory_data = db.get_user_inventory(interaction.user.id)
    case_key = f"case_{case_id}"
    
    if case_key not in inventory_data.get("cases", {}):
        await interaction.response.send_message("У вас нет такого кейса в инвентаре!", ephemeral=True)
        return
    
    case_data = db.get_case(case_id)
    if not case_data:
        await interaction.response.send_message("Кейс не найден в базе данных!", ephemeral=True)
        return
    
    db.remove_case_from_inventory(interaction.user.id, case_id)
    
    case = {
        'name': case_data[1],
        'price': case_data[2],
        'rewards': json.loads(case_data[3])
    }
    
    embed = discord.Embed(title="🎰 Открытие кейса...", color=0xffd700)
    await interaction.response.send_message(embed=embed)
    
    for i in range(3):
        await asyncio.sleep(1)
        embed.description = "🎁" * (i + 1)
        await interaction.edit_original_response(embed=embed)
    
    def get_reward(case):
        rewards = case['rewards']
        rand = random.random()
        current = 0
        for reward in rewards:
            current += reward['chance']
            if rand <= current:
                return reward
        return rewards[0]

    async def process_reward(user, reward, case):
        user_id = user.id
        if reward['type'] == 'coins':
            amount = random.randint(reward['amount'][0], reward['amount'][1])
            amount = db.apply_buff_to_amount(user_id, amount, 'case_bonus')
            amount = db.apply_buff_to_amount(user_id, amount, 'multiplier')
            amount = db.apply_buff_to_amount(user_id, amount, 'all_bonus')
            db.update_balance(user_id, amount)
            db.log_transaction(user_id, 'case_reward', amount, description=f"Кейс: {case['name']}")
            return f"Монеты: {amount} {EMOJIS['coin']}"

        elif reward['type'] == 'special_item':
            item_name = reward['name']
            db.add_item_to_inventory(user_id, item_name)
            return f"Предмет: {item_name}"

        elif reward['type'] == 'bonus':
            amount = case['price'] * reward['multiplier']
            db.update_balance(user_id, amount)
            db.log_transaction(user_id, 'case_bonus', amount, description=f"Бонус из кейса: {case['name']}")
            return f"Бонус: {amount} {EMOJIS['coin']} (x{reward['multiplier']})"

        else:
            return "Ничего"

    reward = get_reward(case)
    reward_text = await process_reward(interaction.user, reward, case)
    
    db.update_user_stat(interaction.user.id, 'cases_opened')
    
    embed = discord.Embed(
        title=f"🎉 {case['name']} открыт!",
        description=reward_text,
        color=0x00ff00
    )
    embed.set_footer(text="Кейс из инвентаря")
    
    await interaction.edit_original_response(embed=embed)

@bot.tree.command(name="market", description="Взаимодействие с маркетплейсом")
@app_commands.describe(action="Действие на маркетплейсе", item_id="ID товара (для покупки)", item_name="Название предмета (для продажи)", price="Цена")
@app_commands.choices(action=[
    app_commands.Choice(name="📋 Список товаров", value="list"),
    app_commands.Choice(name="💰 Продать предмет", value="sell"),
    app_commands.Choice(name="🛒 Купить товар", value="buy"),
    app_commands.Choice(name="❌ Удалить свой товар", value="remove")
])
async def market(interaction: discord.Interaction, action: app_commands.Choice[str], item_id: int = None, item_name: str = None, price: int = None):
    try:
        if action.value == "list":
            cursor = db.conn.cursor()
            cursor.execute('''
                SELECT m.id, m.seller_id, m.item_name, m.price, m.created_at, i.description 
                FROM market m 
                LEFT JOIN items i ON m.item_name = i.name 
                ORDER BY m.created_at DESC LIMIT 15
            ''')
            items = cursor.fetchall()
            
            embed = discord.Embed(title="🏪 Маркетплейс - Последние 15 товаров", color=0x00ff00)
            
            if not items:
                embed.description = "На маркетплейсе пока нет товаров."
            else:
                for item in items:
                    item_id = item[0]
                    seller_id = item[1]
                    item_name_db = item[2]
                    item_price = item[3]
                    created_at = item[4]
                    item_description = item[5] if item[5] else "Описание отсутствует"
                    
                    seller = bot.get_user(seller_id) if seller_id else None
                    
                    # Получаем информацию о бафе
                    buff_info = ""
                    try:
                        item_data = db.get_item_by_name(item_name_db)
                        if item_data and len(item_data) > 7 and item_data[7]:
                            buff_info = f"\n**Эффект:** {item_data[7]}"
                    except Exception as e:
                        print(f"⚠️ Ошибка получения информации о предмете {item_name_db}: {e}")
                    
                    embed.add_field(
                        name=f"🆔 #{item_id} | {item_name_db} | {item_price} {EMOJIS['coin']}",
                        value=f"**Продавец:** {seller.mention if seller else 'Неизвестно'}{buff_info}\n**Описание:** {item_description}",
                        inline=False
                    )
            
            embed.set_footer(text="Используйте /market buy [ID] чтобы купить товар")
            await interaction.response.send_message(embed=embed)
        
        elif action.value == "sell":
            if not item_name or not price:
                await interaction.response.send_message("❌ Укажите название предмета и цену!", ephemeral=True)
                return
            
            if price <= 0:
                await interaction.response.send_message("❌ Цена должна быть положительной!", ephemeral=True)
                return
            
            # Проверяем, есть ли предмет у пользователя
            if not db.remove_item_from_inventory(interaction.user.id, item_name):
                await interaction.response.send_message("❌ У вас нет этого предмета в инвентаре!", ephemeral=True)
                return
            
            cursor = db.conn.cursor()
            cursor.execute('INSERT INTO market (seller_id, item_name, price) VALUES (%s, %s, %s) RETURNING id', 
                          (interaction.user.id, item_name, price))
            new_item_id = cursor.fetchone()[0]
            db.conn.commit()
            db.update_user_stat(interaction.user.id, 'market_sales')
            
            embed = discord.Embed(
                title="✅ Предмет выставлен на продажу!",
                description=f"**Предмет:** {item_name}\n**Цена:** {price} {EMOJIS['coin']}\n**ID товара:** {new_item_id}",
                color=0x00ff00
            )
            embed.set_footer(text="Другие пользователи могут купить ваш товар по ID")
            await interaction.response.send_message(embed=embed)
        
        elif action.value == "buy":
            if item_id is None:
                await interaction.response.send_message("❌ Укажите ID товара для покупки! Используйте /market list чтобы посмотреть товары.", ephemeral=True)
                return
            
            cursor = db.conn.cursor()
            cursor.execute('SELECT id, seller_id, item_name, price FROM market WHERE id = %s', (item_id,))
            item = cursor.fetchone()
            
            if not item:
                await interaction.response.send_message("❌ Товар с таким ID не найден!", ephemeral=True)
                return
            
            market_item_id = item[0]
            seller_id = item[1]
            market_item_name = item[2]
            item_price = item[3]
            
            if not seller_id:
                await interaction.response.send_message("❌ Ошибка: продавец не найден!", ephemeral=True)
                return
            
            if seller_id == interaction.user.id:
                await interaction.response.send_message("❌ Нельзя купить свой же товар!", ephemeral=True)
                return
            
            user_data = db.get_user(interaction.user.id)
            user_safe = get_user_data_safe(user_data)
            
            if user_safe['balance'] < item_price:
                await interaction.response.send_message("❌ Недостаточно монет!", ephemeral=True)
                return
            
            # Совершаем покупку
            db.update_balance(interaction.user.id, -item_price)
            db.update_balance(seller_id, item_price)
            db.add_item_to_inventory(interaction.user.id, market_item_name)
            
            cursor.execute('DELETE FROM market WHERE id = %s', (market_item_id,))
            db.conn.commit()
            
            db.log_transaction(interaction.user.id, 'market_buy', -item_price, seller_id, f"Покупка: {market_item_name}")
            db.log_transaction(seller_id, 'market_sell', item_price, interaction.user.id, f"Продажа: {market_item_name}")
            
            seller_user = bot.get_user(seller_id)
            buff_info = ""
            try:
                item_data = db.get_item_by_name(market_item_name)
                if item_data and len(item_data) > 7 and item_data[7]:
                    buff_info = f"\n**Эффект:** {item_data[7]}"
            except Exception as e:
                print(f"⚠️ Ошибка получения бафа предмета {market_item_name}: {e}")
            
            embed = discord.Embed(
                title="✅ Покупка совершена!",
                description=f"**Товар:** {market_item_name}\n**Цена:** {item_price} {EMOJIS['coin']}\n**Продавец:** {seller_user.mention if seller_user else 'Неизвестно'}{buff_info}",
                color=0x00ff00
            )
            await interaction.response.send_message(embed=embed)
        
        elif action.value == "remove":
            if item_id is None:
                await interaction.response.send_message("❌ Укажите ID вашего товара для удаления!", ephemeral=True)
                return
            
            cursor = db.conn.cursor()
            cursor.execute('SELECT id, seller_id, item_name FROM market WHERE id = %s', (item_id,))
            item = cursor.fetchone()
            
            if not item:
                await interaction.response.send_message("❌ Товар с таким ID не найден!", ephemeral=True)
                return
            
            if item[1] != interaction.user.id:
                await interaction.response.send_message("❌ Вы можете удалять только свои товары!", ephemeral=True)
                return
            
            # Возвращаем предмет в инвентарь
            db.add_item_to_inventory(interaction.user.id, item[2])
            cursor.execute('DELETE FROM market WHERE id = %s', (item_id,))
            db.conn.commit()
            
            embed = discord.Embed(
                title="✅ Товар удален с маркетплейса",
                description=f"Товар **{item[2]}** возвращен в ваш инвентарь.",
                color=0x00ff00
            )
            await interaction.response.send_message(embed=embed)
    
    except Exception as e:
        print(f"❌ Критическая ошибка в команде market: {e}")
        error_embed = discord.Embed(
            title="❌ Ошибка маркетплейса",
            description="Произошла ошибка при выполнении команды. Попробуйте позже.",
            color=0xff0000
        )
        await interaction.response.send_message(embed=error_embed, ephemeral=True)

@bot.tree.command(name="work", description="Выполнить случайную работу")
@app_commands.checks.cooldown(1, 3600.0)  # 1 час КД
async def work_command(interaction: discord.Interaction):
    try:
        work_type = random.choice(list(WORKS.keys()))
        work_data = WORKS[work_type]
        
        base_reward = random.randint(work_data['min_reward'], work_data['max_reward'])
        reward = db.apply_buff_to_amount(interaction.user.id, base_reward, 'multiplier')
        reward = db.apply_buff_to_amount(interaction.user.id, reward, 'all_bonus')
        
        # Регистрируем выполнение работы
        db.complete_work(interaction.user.id, work_type, reward)
        
        embed = discord.Embed(
            title="💼 Работа выполнена!",
            description=f"**Профессия:** {work_data['name']}\n**Задача:** {work_data['description']}",
            color=0x00ff00
        )
        embed.add_field(name="Заработок", value=f"{reward} {EMOJIS['coin']}", inline=True)
        
        # Получаем статистику работ
        user_works = db.get_user_works(interaction.user.id)
        total_works = sum(work[1] for work in user_works) if user_works else 0
        
        embed.add_field(name="Всего работ выполнено", value=f"{total_works}", inline=True)
        embed.set_footer(text="Следующая работа через 1 час")
        
        await interaction.response.send_message(embed=embed)
        
    except Exception as e:
        print(f"❌ Ошибка в команде work: {e}")
        error_embed = discord.Embed(
            title="❌ Ошибка выполнения работы",
            description="Произошла ошибка при выполнении работы. Попробуйте позже.",
            color=0xff0000
        )
        await interaction.response.send_message(embed=error_embed, ephemeral=True)

@work_command.error
async def work_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    if isinstance(error, app_commands.CommandOnCooldown):
        minutes = int(error.retry_after // 60)
        seconds = int(error.retry_after % 60)
        
        await interaction.response.send_message(
            f"⏰ Следующую работу можно выполнить через {minutes} минут {seconds:02d} секунд",
            ephemeral=True
        )
    else:
        raise error

@bot.tree.command(name="works", description="Показать статистику выполненных работ")
async def works_stats(interaction: discord.Interaction):
    try:
        user_works = db.get_user_works(interaction.user.id)
        
        embed = discord.Embed(title="💼 Статистика работ", color=0x3498db)
        
        if not user_works:
            embed.description = "Вы еще не выполнили ни одной работы. Используйте `/work` чтобы начать!"
            await interaction.response.send_message(embed=embed)
            return
        
        works_info = {
            'programmer': '💻 Программист',
            'designer': '🎨 Дизайнер', 
            'writer': '📝 Копирайтер',
            'translator': '🌐 Переводчик',
            'tester': '🐛 Тестировщик',
            'manager': '📊 Менеджер',
            'security': '🛡️ Аналитик безопасности',
            'data_scientist': '📈 Data Scientist'
        }
        
        total_works = 0
        works_text = ""
        
        for work in user_works:
            work_type = work[0]
            count = work[1]
            total_works += count
            
            work_name = works_info.get(work_type, work_type)
            works_text += f"**{work_name}:** {count} раз\n"
        
        embed.add_field(name="📊 Выполненные работы", value=works_text, inline=False)
        embed.add_field(name="🔢 Всего работ", value=f"{total_works} выполненных заданий", inline=True)
        
        await interaction.response.send_message(embed=embed)
        
    except Exception as e:
        print(f"❌ Ошибка в команде works: {e}")
        error_embed = discord.Embed(
            title="❌ Ошибка загрузки статистики",
            description="Произошла ошибка при загрузке статистики работ.",
            color=0xff0000
        )
        await interaction.response.send_message(embed=error_embed, ephemeral=True)

@bot.tree.command(name="inventory", description="Показать ваш инвентарь")
async def inventory(interaction: discord.Interaction):
    try:
        inventory_data = db.get_user_inventory_safe(interaction.user.id)
        
        embed = discord.Embed(
            title=f"🎒 Инвентарь {interaction.user.display_name}",
            color=0x3498db
        )
        
        cases = inventory_data.get("cases", {})
        if cases:
            cases_text = ""
            for case_key, case_info in cases.items():
                try:
                    case_id = case_key.replace("case_", "")
                    cases_text += f"• {case_info.get('name', 'Неизвестный кейс')} (ID: {case_id}) ×{case_info.get('count', 1)}\n"
                except Exception as e:
                    print(f"⚠️ Ошибка обработки кейса {case_key}: {e}")
                    continue
            embed.add_field(name="🎁 Кейсы", value=cases_text, inline=False)
        else:
            embed.add_field(name="🎁 Кейсы", value="Пусто", inline=False)
        
        items = inventory_data.get("items", {})
        if items:
            items_text = ""
            for item_id, count in items.items():
                try:
                    item_name = db.get_item_name_by_id(item_id)
                    items_text += f"• {item_name} ×{count}\n"
                except Exception as e:
                    print(f"⚠️ Ошибка обработки предмета {item_id}: {e}")
                    items_text += f"• Предмет ID:{item_id} ×{count}\n"
            
            if items_text:
                embed.add_field(name="📦 Предметы", value=items_text, inline=False)
            else:
                embed.add_field(name="📦 Предметы", value="Пусто", inline=False)
        else:
            embed.add_field(name="📦 Предметы", value="Пусто", inline=False)
        
        buffs = db.get_user_buffs(interaction.user.id)
        if buffs:
            buffs_text = "\n".join([f"• **{buff['item_name']}**: {buff['description']}" for buff in buffs.values()])
            embed.add_field(name="🎯 Активные бафы", value=buffs_text, inline=False)
        
        await interaction.response.send_message(embed=embed)
        
    except Exception as e:
        print(f"❌ Ошибка в команде inventory: {e}")
        await interaction.response.send_message("❌ Произошла ошибка при загрузке инвентаря!", ephemeral=True)

@bot.tree.command(name="achievements", description="Показать ваши достижения")
async def show_achievements(interaction: discord.Interaction):
    try:
        cursor = db.conn.cursor()
        cursor.execute('SELECT achievement_id FROM achievements WHERE user_id = %s', (interaction.user.id,))
        user_achievements_result = cursor.fetchall()
        
        # Безопасное извлечение achievement_id
        user_achievements = []
        for row in user_achievements_result:
            if row and len(row) > 0 and row[0]:
                user_achievements.append(row[0])

        embed = discord.Embed(title="🏅 Ваши достижения", color=0xffd700)
        
        if not user_achievements:
            embed.description = "У вас пока нет достижений. Продолжайте играть, чтобы их получить!"
            embed.set_footer(text="Используйте команды бота для получения достижений")
            await interaction.response.send_message(embed=embed)
            return
        
        unlocked_count = len(user_achievements)
        achievements_list = []
        
        for achievement_id, achievement in ACHIEVEMENTS.items():
            status = "✅" if achievement_id in user_achievements else "❌"
            achievements_list.append(
                f"{status} **{achievement['name']}**\n{achievement['description']}\nНаграда: {achievement['reward']} {EMOJIS['coin']}\n"
            )
        
        # Разбиваем на страницы
        pages = []
        current_page = ""
        
        for achievement in achievements_list:
            if len(current_page) + len(achievement) > 2000:
                pages.append(current_page)
                current_page = achievement
            else:
                current_page += achievement
        
        if current_page:
            pages.append(current_page)
        
        if len(pages) == 1:
            embed.description = pages[0]
            embed.set_footer(text=f"Разблокировано: {unlocked_count}/{len(ACHIEVEMENTS)}")
            await interaction.response.send_message(embed=embed)
        else:
            class AchievementsPaginatedView(View):
                def __init__(self, pages, author_id, unlocked_count, total_count):
                    super().__init__(timeout=120)
                    self.pages = pages
                    self.current_page = 0
                    self.total_pages = len(pages)
                    self.author_id = author_id
                    self.unlocked_count = unlocked_count
                    self.total_count = total_count
                    self.update_buttons()

                def update_buttons(self):
                    self.previous_button.disabled = (self.current_page == 0)
                    self.next_button.disabled = (self.current_page >= self.total_pages - 1)

                @discord.ui.button(label='⬅️ Назад', style=discord.ButtonStyle.secondary)
                async def previous_button(self, interaction: discord.Interaction, button: Button):
                    if interaction.user.id != self.author_id:
                        await interaction.response.send_message("❌ Это не ваша пагинация!", ephemeral=True)
                        return
                    
                    if self.current_page > 0:
                        self.current_page -= 1
                        self.update_buttons()
                        embed = self.create_embed()
                        await interaction.response.edit_message(embed=embed, view=self)

                @discord.ui.button(label='➡️ Вперед', style=discord.ButtonStyle.secondary)
                async def next_button(self, interaction: discord.Interaction, button: Button):
                    if interaction.user.id != self.author_id:
                        await interaction.response.send_message("❌ Это не ваша пагинация!", ephemeral=True)
                        return
                    
                    if self.current_page < self.total_pages - 1:
                        self.current_page += 1
                        self.update_buttons()
                        embed = self.create_embed()
                        await interaction.response.edit_message(embed=embed, view=self)

                def create_embed(self):
                    embed = discord.Embed(
                        title=f"🏅 Ваши достижения (Страница {self.current_page + 1}/{self.total_pages})",
                        description=self.pages[self.current_page],
                        color=0xffd700
                    )
                    embed.set_footer(text=f"Разблокировано: {self.unlocked_count}/{self.total_count}")
                    return embed
            
            view = AchievementsPaginatedView(pages, interaction.user.id, unlocked_count, len(ACHIEVEMENTS))
            embed = view.create_embed()
            await interaction.response.send_message(embed=embed, view=view)
            
    except Exception as e:
        print(f"❌ Ошибка в команде achievements: {e}")
        error_embed = discord.Embed(
            title="❌ Ошибка загрузки достижений",
            description="Произошла ошибка при загрузке ваших достижений. Попробуйте позже.",
            color=0xff0000
        )
        await interaction.response.send_message(embed=error_embed, ephemeral=True)
        
@bot.tree.command(name="mystats", description="Показать вашу статистику")
async def mystats(interaction: discord.Interaction):
    try:
        # Обновляем статистику предметов
        db.update_items_collected_stat(interaction.user.id)
        
        cursor = db.conn.cursor()
        cursor.execute('SELECT * FROM user_stats WHERE user_id = %s', (interaction.user.id,))
        stats_data = cursor.fetchone()
        
        if not stats_data:
            cursor.execute('INSERT INTO user_stats (user_id) VALUES (%s)', (interaction.user.id,))
            db.conn.commit()
            cursor.execute('SELECT * FROM user_stats WHERE user_id = %s', (interaction.user.id,))
            stats_data = cursor.fetchone()
        
        buffs = db.get_user_buffs(interaction.user.id)
        
        embed = discord.Embed(title="📊 Ваша статистика", color=0x3498db)
        
        embed.add_field(
            name="🎮 Игровая статистика",
            value=f"**Кейсы открыто:** {stats_data[1]}\n"
                  f"**Дуэлей выиграно:** {stats_data[2]}\n"
                  f"**Успешных краж:** {stats_data[3]}\n"
                  f"**Неудачных краж:** {stats_data[4]}",
            inline=False
        )
        
        embed.add_field(
            name="🎰 Статистика игр",
            value=f"**Побед в рулетке:** {stats_data[5]}\n"
                  f"**Побед в слотах:** {stats_data[6]}\n"
                  f"**Побед в блэкджеке:** {stats_data[7]}\n"
                  f"**Побед в coinflip:** {stats_data[8]}",
            inline=False
        )
        
        # Получаем актуальное количество уникальных предметов
        inventory = db.get_user_inventory_safe(interaction.user.id)
        unique_items = len(inventory.get("items", {}))
        
        embed.add_field(
            name="📈 Другая статистика",
            value=f"**Ежедневных наград:** {stats_data[9]}\n"
                  f"**Всего заработано:** {stats_data[10]} {EMOJIS['coin']}\n"
                  f"**Продаж на маркете:** {stats_data[11]}\n"
                  f"**Подарков отправлено:** {stats_data[12]}\n"
                  f"**Предметов собрано:** {unique_items}\n"
                  f"**Работ выполнено:** {stats_data[15]}",
            inline=False
        )
        
        if buffs:
            buffs_text = "\n".join([f"• **{buff['item_name']}**: {buff['description']}" for buff in buffs.values()])
            embed.add_field(name="🎯 Активные бафы", value=buffs_text, inline=False)
        
        await interaction.response.send_message(embed=embed)
        
    except Exception as e:
        print(f"❌ Ошибка в команде mystats: {e}")
        error_embed = discord.Embed(
            title="❌ Ошибка загрузки статистики",
            description="Произошла ошибка при загрузке статистики.",
            color=0xff0000
        )
        await interaction.response.send_message(embed=error_embed, ephemeral=True)

# ЛИДЕРБОРДЫ
@bot.tree.command(name="leaderboard", description="Показать таблицу лидеров")
@app_commands.describe(type="Тип лидерборда")
@app_commands.choices(type=[
    app_commands.Choice(name="💰 Баланс", value="balance"),
    app_commands.Choice(name="🏆 Победы", value="wins"),
    app_commands.Choice(name="🦹 Кражи", value="steals"),
    app_commands.Choice(name="🎁 Кейсы", value="cases"),
    app_commands.Choice(name="🏅 Достижения", value="achievements"),
    app_commands.Choice(name="📦 Предметы", value="items"),
    app_commands.Choice(name="💼 Работы", value="works")
])
async def leaderboard(interaction: discord.Interaction, type: app_commands.Choice[str]):
    cursor = db.conn.cursor()
    
    if type.value == 'balance':
        cursor.execute('SELECT user_id, balance FROM users ORDER BY balance DESC LIMIT 10')
        title = "💰 Лидеры по балансу"
        
        embed = discord.Embed(title=title, color=0xffd700)
        
        for i, (user_id, balance) in enumerate(cursor.fetchall(), 1):
            user = bot.get_user(user_id)
            name = user.display_name if user else f"User#{user_id}"
            embed.add_field(
                name=f"{i}. {name}",
                value=f"{balance} {EMOJIS['coin']}",
                inline=False
            )
    
    elif type.value == 'wins':
        cursor.execute('''
            SELECT user_id, 
                   (COALESCE(roulette_wins, 0) + COALESCE(duels_won, 0) + COALESCE(slot_wins, 0) + 
                    COALESCE(blackjack_wins, 0) + COALESCE(coinflip_wins, 0)) as total_wins 
            FROM user_stats 
            ORDER BY total_wins DESC LIMIT 10
        ''')
        title = "🏆 Лидеры по победам"
        
        embed = discord.Embed(title=title, color=0xffd700)
        
        for i, (user_id, wins) in enumerate(cursor.fetchall(), 1):
            user = bot.get_user(user_id)
            name = user.display_name if user else f"User#{user_id}"
            embed.add_field(
                name=f"{i}. {name}",
                value=f"{wins} побед",
                inline=False
            )
    
    elif type.value == 'steals':
        cursor.execute('SELECT user_id, steals_successful FROM user_stats ORDER BY steals_successful DESC LIMIT 10')
        title = "🦹 Лидеры по кражам"
        
        embed = discord.Embed(title=title, color=0xffd700)
        
        for i, (user_id, steals) in enumerate(cursor.fetchall(), 1):
            user = bot.get_user(user_id)
            name = user.display_name if user else f"User#{user_id}"
            embed.add_field(
                name=f"{i}. {name}",
                value=f"{steals} краж",
                inline=False
            )
    
    elif type.value == 'cases':
        cursor.execute('SELECT user_id, cases_opened FROM user_stats ORDER BY cases_opened DESC LIMIT 10')
        title = "🎁 Лидеры по кейсам"
        
        embed = discord.Embed(title=title, color=0xffd700)
        
        for i, (user_id, cases) in enumerate(cursor.fetchall(), 1):
            user = bot.get_user(user_id)
            name = user.display_name if user else f"User#{user_id}"
            embed.add_field(
                name=f"{i}. {name}",
                value=f"{cases} кейсов",
                inline=False
            )
    
    elif type.value == 'achievements':
        cursor.execute('''
            SELECT user_id, COUNT(*) as achievement_count 
            FROM achievements 
            GROUP BY user_id 
            ORDER BY achievement_count DESC LIMIT 10
        ''')
        title = "🏅 Лидеры по достижениям"
        
        embed = discord.Embed(title=title, color=0xffd700)
        
        for i, (user_id, achievements_count) in enumerate(cursor.fetchall(), 1):
            user = bot.get_user(user_id)
            name = user.display_name if user else f"User#{user_id}"
            embed.add_field(
                name=f"{i}. {name}",
                value=f"{achievements_count} достижений",
                inline=False
            )
    
    elif type.value == 'items':
        # Исправленный запрос для лидерборда по предметам
        cursor.execute('''
            SELECT u.user_id, 
                   (SELECT COUNT(*) FROM jsonb_object_keys(u.inventory->'items')) as unique_items
            FROM users u
            WHERE u.inventory->'items' IS NOT NULL 
            ORDER BY unique_items DESC LIMIT 10
        ''')
        title = "📦 Лидеры по уникальным предметам"
        
        embed = discord.Embed(title=title, color=0xffd700)
        
        for i, (user_id, item_count) in enumerate(cursor.fetchall(), 1):
            user = bot.get_user(user_id)
            name = user.display_name if user else f"User#{user_id}"
            embed.add_field(
                name=f"{i}. {name}",
                value=f"{item_count} уникальных предметов",
                inline=False
            )
    
    elif type.value == 'works':
        cursor.execute('SELECT user_id, work_completed FROM user_stats ORDER BY work_completed DESC LIMIT 10')
        title = "💼 Лидеры по работам"
        
        embed = discord.Embed(title=title, color=0xffd700)
        
        for i, (user_id, works) in enumerate(cursor.fetchall(), 1):
            user = bot.get_user(user_id)
            name = user.display_name if user else f"User#{user_id}"
            embed.add_field(
                name=f"{i}. {name}",
                value=f"{works} работ",
                inline=False
            )
    
    await interaction.response.send_message(embed=embed)

# АДМИН-КОМАНДЫ
@bot.tree.command(name="admin_addcoins", description="Добавить монеты пользователю (админ)")
@app_commands.describe(user="Пользователь", amount="Количество монет")
@is_admin()
async def admin_addcoins(interaction: discord.Interaction, user: discord.Member, amount: int):
    try:
        db.update_balance(user.id, amount)
        db.log_transaction(interaction.user.id, 'admin_add', amount, user.id, f"Админ {interaction.user.name}")
        
        embed = discord.Embed(
            title="⚙️ Админ действие",
            description=f"Выдано {amount} {EMOJIS['coin']} пользователю {user.mention}",
            color=0x00ff00
        )
        await interaction.response.send_message(embed=embed)
    except Exception as e:
        await interaction.response.send_message(f"❌ Ошибка при выполнении команды: {e}", ephemeral=True)

@bot.tree.command(name="admin_removecoins", description="Забрать монеты у пользователя (админ)")
@app_commands.describe(user="Пользователь", amount="Количество монет")
@is_admin()
async def admin_removecoins(interaction: discord.Interaction, user: discord.Member, amount: int):
    try:
        db.update_balance(user.id, -amount)
        db.log_transaction(interaction.user.id, 'admin_remove', -amount, user.id, f"Админ {interaction.user.name}")
        
        embed = discord.Embed(
            title="⚙️ Админ действие",
            description=f"Забрано {amount} {EMOJIS['coin']} у пользователя {user.mention}",
            color=0xff0000
        )
        await interaction.response.send_message(embed=embed)
    except Exception as e:
        await interaction.response.send_message(f"❌ Ошибка при выполнении команды: {e}", ephemeral=True)

@bot.tree.command(name="admin_giveitem", description="Выдать предмет пользователю (админ)")
@app_commands.describe(user="Пользователь", item_name="Название предмета")
@is_admin()
async def admin_giveitem(interaction: discord.Interaction, user: discord.Member, item_name: str):
    try:
        item_data = db.get_item_by_name(item_name)
        if not item_data:
            all_items = db.get_all_items()
            item_list = "\n".join([f"• {item[1]}" for item in all_items[:10]])
            if len(all_items) > 10:
                item_list += f"\n• ... и ещё {len(all_items) - 10} предметов"
            
            embed = discord.Embed(
                title="❌ Предмет не найден",
                description=f"Доступные предметы:\n{item_list}",
                color=0xff0000
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        db.add_item_to_inventory(user.id, item_name)
        
        embed = discord.Embed(
            title="⚙️ Админ действие",
            description=f"Предмет '{item_name}' выдан пользователю {user.mention}",
            color=0x00ff00
        )
        buff_description = item_data[7] if len(item_data) > 7 and item_data[7] else "Нет бафа"
        embed.add_field(name="Эффект", value=buff_description)
        await interaction.response.send_message(embed=embed)
    except Exception as e:
        await interaction.response.send_message(f"❌ Ошибка при выполнении команды: {e}", ephemeral=True)

@bot.tree.command(name="admin_createcase", description="Создать новый кейс (админ)")
@app_commands.describe(name="Название кейса", price="Цена кейса", rewards_json="Награды в формате JSON")
@is_admin()
async def admin_createcase(interaction: discord.Interaction, name: str, price: int, rewards_json: str):
    try:
        rewards = json.loads(rewards_json)
        cursor = db.conn.cursor()
        cursor.execute('INSERT INTO cases (name, price, rewards) VALUES (%s, %s, %s) RETURNING id', 
                      (name, price, json.dumps(rewards)))
        case_id = cursor.fetchone()[0]
        db.conn.commit()
        
        embed = discord.Embed(
            title="⚙️ Админ действие",
            description=f"Создан новый кейс: {name}\nЦена: {price} {EMOJIS['coin']}\nID: {case_id}",
            color=0x00ff00
        )
        await interaction.response.send_message(embed=embed)
    except json.JSONDecodeError:
        await interaction.response.send_message("❌ Неверный формат JSON для наград", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"❌ Ошибка при выполнении команды: {e}", ephemeral=True)

@bot.tree.command(name="admin_viewtransactions", description="Просмотр транзакций (админ)")
@app_commands.describe(user="Пользователь (опционально)")
@is_admin()
async def admin_viewtransactions(interaction: discord.Interaction, user: discord.Member = None):
    try:
        cursor = db.conn.cursor()
        
        if user:
            cursor.execute('SELECT * FROM transactions WHERE user_id = %s OR target_user_id = %s ORDER BY timestamp DESC LIMIT 10', (user.id, user.id))
            title = f"📊 Транзакции пользователя {user.name}"
        else:
            cursor.execute('SELECT * FROM transactions ORDER BY timestamp DESC LIMIT 10')
            title = "📊 Последние транзакции"
        
        transactions = cursor.fetchall()
        
        embed = discord.Embed(title=title, color=0x3498db)
        
        for trans in transactions:
            trans_user = bot.get_user(trans[1])
            target_user = bot.get_user(trans[4]) if trans[4] else None
            
            embed.add_field(
                name=f"#{trans[0]} {trans[2]}",
                value=f"Сумма: {trans[3]} {EMOJIS['coin']}\nОт: {trans_user.name if trans_user else 'Система'}\nКому: {target_user.name if target_user else 'Нет'}\nОписание: {trans[5]}",
                inline=False
            )
        
        await interaction.response.send_message(embed=embed)
    except Exception as e:
        await interaction.response.send_message(f"❌ Ошибка при выполнении команды: {e}", ephemeral=True)

# КОМАНДА ПОМОЩИ
@bot.tree.command(name="help", description="Показать информацию о боте и список команд")
async def help_command(interaction: discord.Interaction):
    embed = discord.Embed(
        title="🎮 Экономический Бот - Помощь",
        description="Добро пожаловать в улучшенную экономическую игру! Исправлены баги, добавлены работы и сбалансирована экономика.",
        color=0x3498db
    )
    
    embed.add_field(
        name="🛠️ Основные исправления",
        value="""• ✅ Исправлена кража (шанс увеличен)
• ✅ Сбалансированы кейсы (лучшая окупаемость)
• ✅ Добавлены недостающие предметы
• ✅ Исправлены достижения
• ✅ Улучшен маркетплейс
• ✅ Добавлена система работ
• ✅ Исправлена статистика""",
        inline=False
    )
    
    embed.add_field(
        name="💰 Экономические команды",
        value="""**/balance** - Показать баланс и бафы
**/daily** - Ежедневная награда
**/pay** @user сумма - Перевод
**/inventory** - Инвентарь
**/mystats** - Статистика""",
        inline=False
    )
    
    embed.add_field(
        name="💼 Система работ",
        value="""**/work** - Выполнить работу (КД 1 час)
**/works** - Статистика работ
**Награда:** 300-2000 монет + бафы""",
        inline=False
    )
    
    embed.add_field(
        name="🎁 Кейсы и маркет",
        value="""**/cases** - Список кейсов
**/open_case** ID - Открыть кейс
**/market** list - Товары
**/market** sell название цена - Продать
**/market** buy ID - Купить по ID
**/market** remove ID - Удалить товар""",
        inline=False
    )
    
    embed.add_field(
        name="🎮 Игры и дуэли",
        value="""**/roulette** ставка
**/slots** ставка  
**/blackjack** ставка
**/coinflip** ставка
**/duel** @user ставка
**/steal** @user (КД 30 мин)""",
        inline=False
    )
    
    embed.add_field(
        name="🏅 Достижения и лидеры",
        value="""**/leaderboard** тип - Топ игроков
**/achievements** - Ваши достижения
**Типы:** баланс, победы, кражи, кейсы, достижения, предметы, работы""",
        inline=False
    )
    
    if interaction.user.id in ADMIN_IDS:
        embed.add_field(
            name="⚙️ Админ-команды",
            value="""**/admin_addcoins** @user сумма
**/admin_removecoins** @user сумма
**/admin_giveitem** @user предмет
**/admin_createcase** название цена JSON
**/admin_viewtransactions** [@user]""",
            inline=False
        )
    
    embed.set_footer(text="Используйте / для просмотра всех команд • Баги исправлены!")
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="buffs", description="Показать ваши активные бафы")
async def buffs(interaction: discord.Interaction):
    buffs = db.get_user_buffs(interaction.user.id)
    
    embed = discord.Embed(title="🎯 Ваши активные бафы", color=0x00ff00)
    
    if not buffs:
        embed.description = "У вас пока нет активных бафов. Приобретайте предметы в кейсах или на маркетплейсе!"
        await interaction.response.send_message(embed=embed)
        return
    
    for buff_type, buff_info in buffs.items():
        embed.add_field(
            name=f"✨ {buff_info['item_name']}",
            value=f"**Эффект:** {buff_info['description']}\n**Множитель:** x{buff_info['value']}",
            inline=False
        )
    
    embed.set_footer(text=f"Всего активных бафов: {len(buffs)}")
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="ping", description="Проверить пинг бота")
async def ping(interaction: discord.Interaction):
    embed = discord.Embed(
        title="🏓 Понг!",
        description=f"Задержка бота: {round(bot.latency * 1000)}мс",
        color=0x00ff00
    )
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="recover", description="Восстановить данные пользователя (если есть проблемы)")
async def recover_data(interaction: discord.Interaction):
    try:
        # Создаем запись пользователя если её нет
        user_data = db.get_user(interaction.user.id)
        user_safe = get_user_data_safe(user_data)
        
        # Восстанавливаем инвентарь если он поврежден
        inventory = db.get_user_inventory(interaction.user.id)
        if not isinstance(inventory, dict):
            cursor = db.conn.cursor()
            cursor.execute('UPDATE users SET inventory = %s WHERE user_id = %s', 
                          (json.dumps({"cases": {}, "items": {}}), interaction.user.id))
            db.conn.commit()
            print(f"🔧 Восстановлен инвентарь для пользователя {interaction.user.id}")
        
        # Восстанавливаем статистику если её нет
        cursor = db.conn.cursor()
        cursor.execute('SELECT 1 FROM user_stats WHERE user_id = %s', (interaction.user.id,))
        if not cursor.fetchone():
            cursor.execute('INSERT INTO user_stats (user_id) VALUES (%s)', (interaction.user.id,))
            db.conn.commit()
            print(f"🔧 Создана статистика для пользователя {interaction.user.id}")
        
        # Получаем обновленные данные
        user_data = db.get_user(interaction.user.id)
        user_safe = get_user_data_safe(user_data)
        
        embed = discord.Embed(
            title="🔧 Восстановление данных",
            description="Ваши данные были проверены и восстановлены при необходимости!",
            color=0x00ff00
        )
        embed.add_field(name="Баланс", value=f"{user_safe['balance']} {EMOJIS['coin']}", inline=True)
        embed.add_field(name="Ежедневная серия", value=f"{user_safe['daily_streak']} дней", inline=True)
        
        await interaction.response.send_message(embed=embed)
        
    except Exception as e:
        print(f"❌ Ошибка в команде recover: {e}")
        error_embed = discord.Embed(
            title="❌ Ошибка восстановления",
            description="Произошла ошибка при восстановлении данных. Попробуйте позже.",
            color=0xff0000
        )
        await interaction.response.send_message(embed=error_embed, ephemeral=True)

# AUTОCOMPLETE ДЛЯ ПРЕДМЕТОВ В МАРКЕТЕ
@market.autocomplete('item_name')
async def market_item_autocomplete(interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
    try:
        inventory = db.get_user_inventory_safe(interaction.user.id)
        items = inventory.get("items", {})
        item_choices = []
        
        for item_id, count in items.items():
            try:
                item_name = db.get_item_name_by_id(item_id)
                if current.lower() in item_name.lower():
                    item_choices.append(
                        app_commands.Choice(
                            name=f"{item_name} (x{count})",
                            value=item_name
                        )
                    )
            except Exception as e:
                continue
        
        return item_choices[:25]
    
    except Exception as e:
        print(f"❌ Ошибка в autocomplete: {e}")
        return []

# Команда для принудительной синхронизации
@bot.tree.command(name="sync", description="Синхронизировать команды (админ)")
@is_admin()
async def sync_commands(interaction: discord.Interaction):
    try:
        await interaction.response.defer(ephemeral=True)
        
        synced = await bot.tree.sync()
        
        embed = discord.Embed(
            title="✅ Синхронизация завершена",
            description=f"Синхронизировано {len(synced)} команд",
            color=0x00ff00
        )
        
        if synced:
            commands_list = "\n".join([f"• `/{cmd.name}`" for cmd in synced])
            embed.add_field(name="Синхронизированные команды:", value=commands_list, inline=False)
        
        await interaction.followup.send(embed=embed, ephemeral=True)
        
    except Exception as e:
        error_embed = discord.Embed(
            title="❌ Ошибка синхронизации",
            description=f"```{e}```",
            color=0xff0000
        )
        await interaction.followup.send(embed=error_embed, ephemeral=True)

# ЗАПУСК БОТА
if __name__ == "__main__":
    print("🚀 Запуск улучшенного экономического бота...")
    print(f"🔑 Токен: {'✅ Найден' if BOT_TOKEN else '❌ Отсутствует'}")
    print(f"🗄️ База данных: {'✅ Подключена' if DATABASE_URL else '❌ Ошибка'}")
    print(f"👑 Админы: {len(ADMIN_IDS)} пользователей")
    print("=" * 50)
    
    try:
        bot.run(BOT_TOKEN)
    except Exception as e:
        print(f"💥 Критическая ошибка при запуске бота: {e}")
        traceback.print_exc()





