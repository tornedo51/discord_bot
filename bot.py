import discord
from discord.ext import commands
from discord.ui import Button, View, Select
import os
import sqlite3
import time
import asyncio

intents = discord.Intents.all()
bot = commands.Bot(command_prefix='!', intents=intents)

TOKEN = os.environ['DISCORD_BOT_TOKEN']

def get_database_connection():
    conn = sqlite3.connect('discord_bot.db')
    return conn

@bot.event
async def on_ready():
    print('Bot is ready.')
    create_tables()
    await update_database()
    print(f'Logged in as {bot.user}')

@bot.event
async def on_member_join(member):
    role_name = "مفصول من إدارة | IQD"
    role = discord.utils.get(member.guild.roles, name=role_name)
    if role:
        await asyncio.sleep(1)  
        try:
            await member.add_roles(role)
            print(f"Gave {member.name} the {role_name} role.")
            add_user(member.name, member.discriminator)
        except discord.HTTPException as e:
            print(f"Failed to add role: {e}")
    else:
        print(f"Role {role_name} not found.")


@bot.command()
@commands.has_permissions(manage_roles=True)
async def role_stats(ctx):
    role_name = "مفصول من إدارة | IQD"
    role = discord.utils.get(ctx.guild.roles, name=role_name)
    if role:
        members_with_role = [member.name for member in ctx.guild.members if role in member.roles]
        await ctx.send(f"The following members have been granted the {role_name} role: {', '.join(members_with_role)}")
    else:
        await ctx.send("Role not found.")

@bot.command()
async def test(ctx):
    await ctx.send("# hi")

def create_tables():
    try:
        conn = get_database_connection()
        cursor = conn.cursor()
        cursor.execute('''CREATE TABLE IF NOT EXISTS users (
                            id INTEGER PRIMARY KEY,
                            username TEXT,
                            discriminator TEXT
                        )''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS user_presses (
                            user_id INTEGER PRIMARY KEY,
                            last_press_time REAL
                        )''')
        conn.commit()
    except sqlite3.Error as e:
        print(f"Error creating table: {e}")
    finally:
        conn.close()

def add_user(username, discriminator=None):
    try:
        conn = get_database_connection()
        cursor = conn.cursor()
        if discriminator is None:
            discriminator = "0000"
        cursor.execute('''INSERT INTO users (username, discriminator) VALUES (?,?)''', (username, discriminator))
        conn.commit()
    except sqlite3.Error as e:
        print(f"Error adding user: {e}")
    finally:
        conn.close()

async def update_database():
    guild = bot.get_guild(1090472218619813988)
    if not guild:
        print("Guild not found!")
        return
    role_name = "مفصول من إدارة | IQD"
    role = discord.utils.get(guild.roles, name=role_name)
    if role:
        for member in guild.members:
            if role in member.roles:
                add_user(member.name, member.discriminator)

button_label = "1000"
credit_amount = 1000

class MyView(View):
    def __init__(self):
        super().__init__(timeout=None)
        self.button = Button(label=button_label, style=discord.ButtonStyle.primary)
        self.button.callback = self.button_callback
        self.add_item(self.button)

    async def button_callback(self, interaction: discord.Interaction):
        user_id = interaction.user.id
        current_time = time.time()
        conn = get_database_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT last_press_time FROM user_presses WHERE user_id = ?', (user_id,))
        result = cursor.fetchone()
        
        if result:
            last_press_time = result[0]
            elapsed_time = current_time - last_press_time
            if elapsed_time < 2 * 60 * 60:  # 2 hours in seconds
                await interaction.response.send_message("يمكنك الضغط على هذا الزر مرة واحدة كل ساعتين.", ephemeral=True)
                conn.close()
                return
        
        cursor.execute('INSERT OR REPLACE INTO user_presses (user_id, last_press_time) VALUES (?, ?)', (user_id, current_time))
        conn.commit()
        conn.close()
        
        channel = discord.utils.get(interaction.guild.text_channels, name="💵┊تعويض・كريدت")
        if channel:
            await channel.send(f" ` c {interaction.user.id} {credit_amount} ` ")
        else:
            await interaction.response.send_message("القناة المحددة غير موجودة.", ephemeral=True)

        await interaction.response.send_message(f"انتظر 5 دقائق {interaction.user.name}!", ephemeral=True)

@bot.command()
@commands.has_permissions(administrator=True)
async def set_amount(ctx, label: str, amount: int):
    global button_label, credit_amount
    button_label = label
    credit_amount = amount

    view = MyView()
    for child in view.children:
        if isinstance(child, Button):
            child.label = button_label

    await ctx.send(f"تم تعيين نص الزر إلى '{button_label}' والمبلغ إلى {credit_amount}")

    channel = discord.utils.get(ctx.guild.text_channels, name='💵┊credits・كريدت')
    if channel:
        await channel.purge(limit=100)
        await channel.send("احصل على كريدت: ", view=view)
   
    log_channel = discord.utils.get(ctx.guild.text_channels, name='👀┊اللوقات')
    if log_channel:
        await log_channel.send(f"تم تغيير إعدادات الزر إلى: نص الزر = '{button_label}', المبلغ = {credit_amount} بواسطة {ctx.author.mention}")

@bot.command()
@commands.has_permissions(administrator=True)
async def clear_data(ctx):
    conn = get_database_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM user_presses')
    conn.commit()
    conn.close()
    try:
        await ctx.author.send("تم مسح جميع البيانات من قاعدة البيانات.")
    except discord.Forbidden:
        await ctx.send("` لم أتمكن من إرسال رسالة خاصة إليك. يرجى التحقق من إعدادات الخصوصية الخاصة بك. ولاكن تم حذف البيانات `")

    log_channel = discord.utils.get(ctx.guild.text_channels, name='👀┊اللوقات')
    if log_channel:
        await log_channel.send(f"تم مسح جميع البيانات من قاعدة البيانات بواسطة {ctx.author.mention}")

@bot.command()
@commands.has_permissions(kick_members=True)
async def kick(ctx, member: discord.Member, *, reason=None):
    try:
        await member.kick(reason=reason)
        await ctx.send(f"تم طرد {member.mention} من السيرفر. السبب: {reason}")

        log_channel = discord.utils.get(ctx.guild.text_channels, name='👀┊اللوقات')
        if log_channel:
            await log_channel.send(f"تم طرد {member.mention} من السيرفر بواسطة {ctx.author.mention}. السبب: {reason}")

    except discord.Forbidden:
        await ctx.send("ليس لدي الأذونات اللازمة لطرد هذا العضو.")
    except discord.HTTPException:
        await ctx.send("حدث خطأ أثناء محاولة طرد هذا العضو.")

async def send_message_to_member(member, author_name, content):
    try:
        await member.send(f" {content}")
    except discord.Forbidden:
        print(f"Could not send message to {member.name}")

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return
    
    guild = message.guild
    if not guild:
        return

    channel_name_to_monitor = "🔔・برودكاست・" 
    channel_to_monitor = discord.utils.get(guild.text_channels, name=channel_name_to_monitor)
    
    if channel_to_monitor and message.channel == channel_to_monitor:
        for member in guild.members:
            if member.bot:
                continue
            await send_message_to_member(member, message.author.name, message.content)
            await asyncio.sleep(1)  

    await bot.process_commands(message)

class CommandPicker(View):
    def __init__(self):
        super().__init__()
        options = [
            discord.SelectOption(label="!test", description="just test if bot run"),
            discord.SelectOption(label="!role_stats", description="check how many member have role"),
            discord.SelectOption(label="!kick", description="Kick a member"),
            discord.SelectOption(label="!set_amount", description="set amount for label"),
            discord.SelectOption(label="!clear_data", description="clear data on databes"),
        ]
        select = discord.ui.Select(placeholder="اختار امر ...", options=options)
        select.callback = self.select_callback
        self.add_item(select)

    async def select_callback(self, interaction: discord.Interaction):
        command = interaction.data['values'][0]
        await interaction.response.send_message(f"You chose the command: {command}")

@bot.command()
async def command_picker(ctx):
    view = CommandPicker()
    await ctx.send("اختار امر من القائمة .. :", view=view)

bot.run(TOKEN)
