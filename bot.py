import discord
from discord.ext import commands, tasks
import json
import os
from datetime import datetime
import aiohttp
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load configuration
with open('config.json', 'r') as f:
    config = json.load(f)

# Bot setup
intents = discord.Intents.default()
intents.members = True
intents.message_content = True
intents.reactions = True
bot = commands.Bot(command_prefix=config['prefix'], intents=intents)

# Storage for custom commands and verified users
custom_commands = {}
verified_users = set()

@bot.event
async def on_ready():
    logger.info(f'{bot.user} has connected to Discord!')
    load_custom_commands()
    load_verified_users()
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name="Roblox games"))

# Load custom commands from storage
def load_custom_commands():
    global custom_commands
    if os.path.exists('custom_commands.json'):
        with open('custom_commands.json', 'r') as f:
            custom_commands = json.load(f)

# Save custom commands to storage
def save_custom_commands():
    with open('custom_commands.json', 'w') as f:
        json.dump(custom_commands, f, indent=2)

# Load verified users from storage
def load_verified_users():
    global verified_users
    if os.path.exists('verified_users.json'):
        with open('verified_users.json', 'r') as f:
            verified_users = set(json.load(f))

# Save verified users to storage
def save_verified_users():
    with open('verified_users.json', 'w') as f:
        json.dump(list(verified_users), f)

# ========== MODERATION COMMANDS ==========

@bot.command(name='ban')
@commands.has_permissions(ban_members=True)
async def ban_user(ctx, member: discord.Member, *, reason=None):
    """Ban a user from the server"""
    try:
        await member.ban(reason=reason)
        embed = discord.Embed(
            title="User Banned",
            description=f"{member.mention} has been banned",
            color=int(config['colors']['primary'], 16),
            timestamp=datetime.now()
        )
        embed.add_field(name="Reason", value=reason or "No reason provided", inline=False)
        embed.set_footer(text=f"Banned by {ctx.author}")
        await ctx.send(embed=embed)
    except Exception as e:
        await ctx.send(f"Error banning user: {e}")

@bot.command(name='kick')
@commands.has_permissions(kick_members=True)
async def kick_user(ctx, member: discord.Member, *, reason=None):
    """Kick a user from the server"""
    try:
        await member.kick(reason=reason)
        embed = discord.Embed(
            title="User Kicked",
            description=f"{member.mention} has been kicked",
            color=int(config['colors']['primary'], 16),
            timestamp=datetime.now()
        )
        embed.add_field(name="Reason", value=reason or "No reason provided", inline=False)
        embed.set_footer(text=f"Kicked by {ctx.author}")
        await ctx.send(embed=embed)
    except Exception as e:
        await ctx.send(f"Error kicking user: {e}")

@bot.command(name='mute')
@commands.has_permissions(manage_roles=True)
async def mute_user(ctx, member: discord.Member, *, reason=None):
    """Mute a user"""
    try:
        mute_role = discord.utils.get(ctx.guild.roles, name=config['mute_role'])
        if not mute_role:
            await ctx.send("Mute role not found. Please create a role named 'Muted'")
            return
        
        await member.add_roles(mute_role, reason=reason)
        embed = discord.Embed(
            title="User Muted",
            description=f"{member.mention} has been muted",
            color=int(config['colors']['primary'], 16),
            timestamp=datetime.now()
        )
        embed.add_field(name="Reason", value=reason or "No reason provided", inline=False)
        await ctx.send(embed=embed)
    except Exception as e:
        await ctx.send(f"Error muting user: {e}")

@bot.command(name='unmute')
@commands.has_permissions(manage_roles=True)
async def unmute_user(ctx, member: discord.Member):
    """Unmute a user"""
    try:
        mute_role = discord.utils.get(ctx.guild.roles, name=config['mute_role'])
        if not mute_role:
            await ctx.send("Mute role not found")
            return
        
        await member.remove_roles(mute_role)
        embed = discord.Embed(
            title="User Unmuted",
            description=f"{member.mention} has been unmuted",
            color=int(config['colors']['success'], 16),
            timestamp=datetime.now()
        )
        await ctx.send(embed=embed)
    except Exception as e:
        await ctx.send(f"Error unmuting user: {e}")

@bot.command(name='warn')
@commands.has_permissions(moderate_members=True)
async def warn_user(ctx, member: discord.Member, *, reason=None):
    """Warn a user"""
    embed = discord.Embed(
        title="User Warned",
        description=f"{member.mention} has been warned",
        color=int(config['colors']['warning'], 16),
        timestamp=datetime.now()
    )
    embed.add_field(name="Reason", value=reason or "No reason provided", inline=False)
    embed.set_footer(text=f"Warned by {ctx.author}")
    await ctx.send(embed=embed)
    
    try:
        await member.send(embed=embed)
    except:
        pass

# ========== CUSTOM COMMAND SYSTEM ==========

@bot.command(name='addcommand')
@commands.has_permissions(manage_messages=True)
async def add_command(ctx, name: str, *, response: str):
    """Add a custom command"""
    if name.lower() in [cmd.name for cmd in bot.commands]:
        await ctx.send("❌ This command name is already in use!")
        return
    
    custom_commands[name.lower()] = {
        'response': response,
        'created_by': ctx.author.id,
        'created_at': str(datetime.now()),
        'uses': 0
    }
    save_custom_commands()
    
    embed = discord.Embed(
        title="✅ Custom Command Added",
        description=f"Command `/{name}` has been created!",
        color=int(config['colors']['success'], 16)
    )
    embed.add_field(name="Response", value=response, inline=False)
    await ctx.send(embed=embed)

@bot.command(name='delcommand')
@commands.has_permissions(manage_messages=True)
async def delete_command(ctx, name: str):
    """Delete a custom command"""
    if name.lower() in custom_commands:
        del custom_commands[name.lower()]
        save_custom_commands()
        await ctx.send(f"✅ Command `/{name}` has been deleted!")
    else:
        await ctx.send(f"❌ Command `/{name}` not found!")

@bot.command(name='listcommands')
async def list_commands(ctx):
    """List all custom commands"""
    if not custom_commands:
        await ctx.send("No custom commands found!")
        return
    
    embed = discord.Embed(
        title="Custom Commands",
        color=int(config['colors']['primary'], 16)
    )
    
    for cmd_name, cmd_data in custom_commands.items():
        embed.add_field(
            name=f"/{cmd_name}",
            value=f"Uses: {cmd_data.get('uses', 0)}",
            inline=True
        )
    
    await ctx.send(embed=embed)

# Handle custom commands
@bot.event
async def on_message(message):
    if message.author == bot.user:
        return
    
    # Check if message starts with the bot prefix and is a custom command
    if message.content.startswith(config['prefix']):
        cmd_name = message.content[len(config['prefix']):].split()[0].lower()
        
        if cmd_name in custom_commands:
            cmd_data = custom_commands[cmd_name]
            embed = discord.Embed(
                description=cmd_data['response'],
                color=int(config['colors']['primary'], 16)
            )
            await message.channel.send(embed=embed)
            
            # Update usage count
            cmd_data['uses'] = cmd_data.get('uses', 0) + 1
            save_custom_commands()
    
    await bot.process_commands(message)

# ========== VERIFICATION SYSTEM ==========

@bot.command(name='verify')
async def setup_verification(ctx):
    """Setup verification message with emoji reaction"""
    embed = discord.Embed(
        title="✅ Verification Required",
        description="React with 🔥 to verify your account and gain access to the server!",
        color=int(config['colors']['primary'], 16)
    )
    embed.add_field(name="Why verify?", value="This helps us keep the server safe and secure.", inline=False)
    embed.set_thumbnail(url=ctx.guild.icon.url if ctx.guild.icon else "")
    
    msg = await ctx.send(embed=embed)
    await msg.add_reaction('🔥')

@bot.event
async def on_reaction_add(reaction, user):
    """Handle verification reaction"""
    if user.bot:
        return
    
    if str(reaction.emoji) == '🔥':
        verified_users.add(user.id)
        save_verified_users()
        
        # Send to webhook
        await send_to_webhook({
            'type': 'verification',
            'user_id': user.id,
            'username': str(user),
            'timestamp': str(datetime.now()),
            'guild_id': reaction.message.guild.id
        })
        
        try:
            await user.send(
                embed=discord.Embed(
                    title="✅ Verification Complete",
                    description="You have been verified! You can now access the server.",
                    color=int(config['colors']['success'], 16)
                )
            )
        except:
            pass

# ========== MOONSTONE TICKET SYSTEM ==========

@bot.command(name='moonstone')
async def moonstone_win(ctx, amount: int):
    """Create a ticket for Moonstone winner (Use this when someone wins)"""
    # Create ticket category if it doesn't exist
    guild = ctx.guild
    ticket_category = discord.utils.get(guild.categories, name=config.get('ticket_category', 'Tickets'))
    
    if not ticket_category:
        ticket_category = await guild.create_category(config.get('ticket_category', 'Tickets'))
    
    # Create ticket channel
    ticket_channel = await guild.create_text_channel(
        name=f"moonstone-{ctx.author.name}",
        category=ticket_category,
        reason=f"Moonstone ticket for {ctx.author}"
    )
    
    # Restrict permissions
    await ticket_channel.set_permissions(
        guild.default_role,
        view_channel=False
    )
    await ticket_channel.set_permissions(
        ctx.author,
        view_channel=True,
        send_messages=True
    )
    
    # Create embed
    embed = discord.Embed(
        title="🌙 Moonstone Prize Claim",
        description=f"{ctx.author.mention} has won **{amount} Moonstones**!",
        color=int(config['colors']['primary'], 16),
        timestamp=datetime.now()
    )
    embed.add_field(
        name="📝 What to do next:",
        value="""
Please wait for a staff member to assist you.

1️⃣ Type your **Roblox username** below
2️⃣ Wait patiently for a staff member to process your claim
3️⃣ **DO NOT PING** staff members

⚠️ Spamming or pinging will result in losing your prize!
        """,
        inline=False
    )
    embed.set_footer(text="Ticket ID: " + ticket_channel.name)
    
    msg = await ticket_channel.send(embed=embed)
    
    # Send to webhook
    await send_to_webhook({
        'type': 'moonstone_ticket',
        'winner': str(ctx.author),
        'amount': amount,
        'channel_id': ticket_channel.id,
        'timestamp': str(datetime.now()),
        'guild_id': guild.id
    })
    
    await ctx.send(f"✅ Ticket created! {ticket_channel.mention}")

@bot.command(name='closeticket')
@commands.has_permissions(manage_channels=True)
async def close_ticket(ctx):
    """Close a Moonstone ticket"""
    if not ctx.channel.name.startswith('moonstone-'):
        await ctx.send("This command can only be used in ticket channels!")
        return
    
    embed = discord.Embed(
        title="🎫 Ticket Closed",
        description="This ticket has been closed by a staff member.",
        color=int(config['colors']['warning'], 16)
    )
    
    await ctx.send(embed=embed)
    await asyncio.sleep(2)
    await ctx.channel.delete()

# ========== WEBHOOK FUNCTION ==========

async def send_to_webhook(data):
    """Send data to webhook"""
    webhook_url = config.get('webhook_url')
    if not webhook_url:
        logger.warning("No webhook URL configured")
        return
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(webhook_url, json=data) as response:
                if response.status == 200:
                    logger.info(f"Data sent to webhook successfully: {data['type']}")
                else:
                    logger.error(f"Webhook error: {response.status}")
    except Exception as e:
        logger.error(f"Error sending to webhook: {e}")

# ========== ERROR HANDLING ==========

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("❌ You don't have permission to use this command!")
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(f"❌ Missing required argument: {error.param}")
    elif isinstance(error, commands.BadArgument):
        await ctx.send("❌ Invalid argument provided!")
    else:
        await ctx.send(f"❌ An error occurred: {error}")
        logger.error(f"Command error: {error}")

# Run the bot
import asyncio
bot.run(config['token'])