###############################################################################
# IMPORT LIBRARIES
# This section loads external Python libraries for use in this program
###############################################################################

# Import Discord 
import discord
from discord.ext import commands
from discord.ui import Button, View

# Import the bot token from our config file
from config import TOKEN

# Import the event system
from modules.event_manager import EventManager 
from datetime import datetime

# Import for timeout/cancel support
import asyncio

# Import json and Division 2 activities list
import json
with open("activities.json", "r") as f:
    ACTIVITY_DATA = json.load(f)

# Import for easy schedule time/day entry
import dateparser


###############################################################################
# EVENT UI COMPONENTS
# These classes define interactive UI elements such as buttons
###############################################################################

# Embed view and buttons for events
class EventView(View):

    def __init__(self, event, bot):
        super().__init__(timeout=None)

        self.event = event
        self.bot = bot

    # Join operations button
    @discord.ui.button(label="Join Operation", style=discord.ButtonStyle.success)
    async def join_button(self, interaction: discord.Interaction, button: Button):

        player = interaction.user.display_name
        result = self.event.add_player(player)

        if result == "joined":
            response = f"{player} joined the operation."
        elif result == "reserve":
            response = f"{player} added to reserve."
        elif result == "exists":
            response = "You are already part of this operation."
        else:
            response = "Unable to join."

        await interaction.response.send_message(response, ephemeral=True)
        await self.update_event_message()

    #Leave operations button
    @discord.ui.button(label="Leave Operation", style=discord.ButtonStyle.danger)
    async def leave_button(self, interaction: discord.Interaction, button: Button):

        player = interaction.user.display_name
        result = self.event.remove_player(player)

        if result == "promoted":
            response = f"You left the operation. A reserve agent was promoted."
        elif result == "removed":
            response = f"You left the operation."
        elif result == "removed_reserve":
            response = "You were removed from reserve."
        else:
            response = "You are not part of this operation."

        await interaction.response.send_message(response, ephemeral=True)
        await self.update_event_message()

    #Update event message
    async def update_event_message(self):

        channel = self.bot.get_channel(self.event.channel_id)
        
        if channel is None:
            return

        message = await channel.fetch_message(self.event.message_id)

        await message.edit(
            embed=self.event.format_event_embed(),
            view=self
        )

# Dynamic join/leave buttons for event list
class EventsListView(View):

    def __init__(self, bot, events):
        super().__init__(timeout=None)
        self.bot = bot

        for event in events:

            join_button = Button(
                label=f"Join {event.event_id}",
                style=discord.ButtonStyle.success,
                row=events.index(event)
            )

            leave_button = Button(
                label=f"Leave {event.event_id}",
                style=discord.ButtonStyle.danger,
                row=events.index(event)
            )

            join_button.callback = self.make_join_callback(event)
            leave_button.callback = self.make_leave_callback(event)

            self.add_item(join_button)
            self.add_item(leave_button)


    def make_join_callback(self, event):

        async def callback(interaction: discord.Interaction):

            player = interaction.user.display_name
            result = event.add_player(player)

            if result == "joined":
                response = f"{player} joined the operation."
            elif result == "reserve":
                response = f"{player} added to reserve."
            elif result == "exists":
                response = "You are already part of this operation."
            else:
                response = "Unable to join."

            await interaction.response.send_message(response, ephemeral=True)

            await self.update_event_message(event)

        return callback


    def make_leave_callback(self, event):

        async def callback(interaction: discord.Interaction):

            player = interaction.user.display_name
            result = event.remove_player(player)

            if result == "promoted":
                response = "You left the operation. A reserve agent was promoted."
            elif result == "removed":
                response = "You left the operation."
            elif result == "removed_reserve":
                response = "You were removed from reserve."
            else:
                response = "You are not part of this operation."

            await interaction.response.send_message(response, ephemeral=True)

            await self.update_event_message(event)

        return callback


    async def update_event_message(self, event):

        if event.message_id and event.channel_id:

            channel = self.bot.get_channel(event.channel_id)

            if channel:

                message = await channel.fetch_message(event.message_id)

                await message.edit(
                    embed=event.format_event_embed(),
                    view=EventView(event, self.bot)
                )

class CategorySelectView(View):

    def __init__(self, bot):
        super().__init__(timeout=120)

        self.bot = bot

        for category in ACTIVITY_DATA.keys():

            button = Button(
                label=category,
                style=discord.ButtonStyle.primary
            )

            async def callback(interaction: discord.Interaction, cat=category):

                user_id = interaction.user.id

                creation_sessions[user_id] = {
                    "category": cat
                }

                embed = discord.Embed(
                    title="Create Operation",
                    description=f"{cat} Activities",
                    color=0xF39C12
                )

                view = ActivitySelectView(self.bot, cat)

                await interaction.response.edit_message(
                    embed=embed,
                    view=view
                )

            button.callback = callback

            self.add_item(button)

class ActivitySelectView(View):

    def __init__(self, bot, category):
        super().__init__(timeout=120)

        self.bot = bot
        self.category = category

        activities = ACTIVITY_DATA[category]

        for activity in activities:

            button = Button(
                label=activity,
                style=discord.ButtonStyle.secondary
            )

            button.callback = self.make_callback(activity)

            self.add_item(button)

    def make_callback(self, activity):

        async def callback(interaction: discord.Interaction):

            user_id = interaction.user.id
            session = creation_sessions.get(user_id)

            if not session:
                await interaction.response.send_message(
                    "Session expired. Please run !create again.",
                    ephemeral=True
                )
                return

            activity_data = ACTIVITY_DATA[self.category][activity]

            session["activity"] = activity
            session["max_players"] = activity_data["max_players"]

            if "options" in activity_data:

                embed = discord.Embed(
                    title="Create Operation",
                    description=f"Select {activity}",
                    color=0xF39C12
                )

                view = OptionSelectView(self.bot, self.category, activity)

                await interaction.response.edit_message(
                    embed=embed,
                    view=view
                )

            else:
                await interaction.response.send_message(
                    f"Activity **{activity}** stored.",
                    ephemeral=True
                )

                prompt = activity_data.get(
                    "description_prompt",
                    "Describe the activity."
                )

                description = await ask_question(
                    interaction.channel,
                    interaction.user,
                    prompt
                )

                if not description:
                    return

                session["description"] = description

                time_input = await ask_question(
                    interaction.channel,
                    interaction.user,
                    "When is the operation? (Example: Friday 8pm, Tomorrow 7, Next Monday 6pm)"
                )

                if not time_input:
                    return

                event_time = dateparser.parse(time_input)

                if not event_time:
                    await interaction.channel.send(
                        "Could not understand the time. Try something like: Friday 8pm"
                    )
                    return

                host = interaction.user.display_name

                activity_name = session["activity"]
                description = session["description"]
                max_players = session["max_players"]

                final_title = f"{activity_name}: {description}"

                event = event_manager.create_event(
                    final_title,
                    host,
                    event_time,
                    max_players
                )

                event.add_player(host)

                embed = event.format_event_embed()
                view = EventView(event, self.bot)

                sent_message = await interaction.channel.send(
                    embed=embed,
                    view=view
                )

                event.message_id = sent_message.id
                event.channel_id = interaction.channel.id

                del creation_sessions[user_id]

        return callback 

class OptionSelectView(View):

    def __init__(self, bot, category, activity):
        super().__init__(timeout=120)

        self.bot = bot
        self.category = category
        self.activity = activity

        options = ACTIVITY_DATA[category][activity]["options"]

        for option in options:

            button = Button(
                label=option,
                style=discord.ButtonStyle.primary
            )

            button.callback = self.make_callback(option)

            self.add_item(button)

    def make_callback(self, option):

        async def callback(interaction: discord.Interaction):

            user_id = interaction.user.id
            session = creation_sessions.get(user_id)

            if not session:
                await interaction.response.send_message(
                    "Session expired. Please run !create again.",
                    ephemeral=True
                )
                return

            session["option"] = option

            await interaction.response.send_message(
                f"Option **{option}** stored.",
                ephemeral=True
            )

            activity_data = ACTIVITY_DATA[self.category][self.activity]

            prompt = activity_data.get(
                "description_prompt",
                "Describe the activity."
            )

            description = await ask_question(
                interaction.channel,
                interaction.user,
                prompt
            )

            if not description:
                return

            session["description"] = description

            time_input = await ask_question(
                interaction.channel,
                interaction.user,
                "When is the operation? (Example: Friday 8pm, Tomorrow 7, Next Monday 6pm)"
            )

            if not time_input:
                return

            event_time = dateparser.parse(time_input)

            if not event_time:
                await interaction.channel.send(
                    "Could not understand the time. Try something like: Friday 8pm"
                )
                return

            host = interaction.user.display_name

            activity_name = session["activity"]
            option_name = session.get("option")
            description = session["description"]
            max_players = session["max_players"]

            activity_title = f"{activity_name} - {option_name}"
            final_title = f"{activity_title}: {description}"

            event = event_manager.create_event(
                final_title,
                host,
                event_time,
                max_players
            )

            event.add_player(host)

            embed = event.format_event_embed()
            view = EventView(event, self.bot)

            sent_message = await interaction.channel.send(
                embed=embed,
                view=view
            )

            event.message_id = sent_message.id
            event.channel_id = interaction.channel.id

            del creation_sessions[user_id]

        return callback


###############################################################################
# DISCORD INTENTS
# Intents tell Discord what types of events the bot wants to receive 
###############################################################################

intents = discord.Intents.default()

#Allows bot to read message content
intents.message_content = True


###############################################################################
# CREATE THE BOT
# This creates the bot object and sets commands to start with !
# Example: !ping
###############################################################################

bot = commands.Bot(command_prefix="!", intents=intents)

# Initialize the event manager
event_manager = EventManager()


###############################################################################
# CREATION SESSIONS
# Tracks users currently building events
###############################################################################

creation_sessions = {}


###############################################################################
# BOT EVENT: on_ready
# This functions runs automatically when the bot is successfully connected
###############################################################################

@bot.event
async def on_ready():
    print(f"Bot connected as {bot.user}")

async def ask_question(channel, user, question):

    await channel.send(question)

    def check(message):
        return (
            message.author == user and
            message.channel == channel
        )

    try:
        msg = await bot.wait_for(
            "message",
            check=check,
            timeout=60
        )

    except asyncio.TimeoutError:
        await channel.send("Event creation timed out.")
        return None

    if msg.content.lower() == "cancel":
        await channel.send("Event creation cancelled.")
        return None

    return msg.content 


###############################################################################
# COMMANDS 
###############################################################################

# !ping - Creates a simple ping command
@bot.command()
async def ping(ctx):
    await ctx.send("Pong!")

# !testevent - Creates a test event to verify the event system works
@bot.command()
async def testevent(ctx):

    host = ctx.author.display_name
    event_time = datetime.now()

    event = event_manager.create_event(
        "Test Raid",
        host,
        event_time,
        8
    )

    event.add_player(host)
    embed = event.format_event_embed()
    
    view = EventView(event, bot)
    sent_message = await ctx.send(
        embed=embed,
        view=view
    )

    # Store message tracking info for updates
    event.message_id = sent_message.id 
    event.channel_id = ctx.channel.id 

# !events - Lists all active events
@bot.command()
async def events(ctx):

    active_events = event_manager.list_events() 

    if not active_events:
        await ctx.send("No active events.")
        return

    embed = discord.Embed(
        title="Active Operations",
        color=0xF39C12
    )

    for event in active_events:

        time_string = event.event_time.strftime("%a %I:%M %p")

        embed.add_field(
            name=f"Event {event.event_id} — {event.activity}",
            value=f"Time: {time_string}\nAgents: {event.player_count()} / {event.max_players}",
            inline=False
        )

    view = EventsListView(bot, active_events)

    await ctx.send(embed=embed, view=view)  

# !join - Allows players to join an event by event ID
@bot.command()
async def join(ctx, event_id: int):

    event = event_manager.get_event(event_id)

    if not event:
        await ctx.send("Event not found.")
        return

    player = ctx.author.display_name
    result = event.add_player(player)

    if result == "joined":
        await ctx.send(f"{player} joined event {event_id}.")
    elif result == "reserve":
        await ctx.send(f"{player} added to reserve list for event {event_id}.")
    elif result == "exists":
        await ctx.send(f"{player} is already in this event.")
    else:
        await ctx.send("Unable to join event.")

    # Update event message if it exists
    if event.message_id and event.channel_id:
        channel = bot.get_channel(event.channel_id)
        message = await channel.fetch_message(event.message_id)
        await message.edit(embed=event.format_event_embed())

# !leave - Allows a player to leave an event by event ID
@bot.command()
async def leave(ctx, event_id: int):

    event = event_manager.get_event(event_id)

    if not event:
        await ctx.send("Event not found.")
        return

    player = ctx.author.display_name
    result = event.remove_player(player)

    if result == "promoted":
        await ctx.send(f"{player} left event {event_id}. A reserve player has been promoted.")
    elif result == "removed":
        await ctx.send(f"{player} left event {event_id}.")
    elif result == "removed_reserve":
        await ctx.send(f"{player} removed from reserve for event {event_id}.")
    elif result == "not_found":
        await ctx.send(f"{player} is not part of event {event_id}.")
    else:
        await ctx.send("Unable to leave event.")

    # Update event message if it exists
    if event.message_id and event.channel_id:
        channel = bot.get_channel(event.channel_id)
        message = await channel.fetch_message(event.message_id)
        await message.edit(embed=event.format_event_embed())

# !create - Creates and event
@bot.command()
async def create(ctx):

    embed = discord.Embed(
        title="Create Operation",
        description="Select a category",
        color=0xF39C12
    )

    view = CategorySelectView(bot)

    await ctx.send(embed=embed, view=view)


###############################################################################
# START THE BOT
# This line logs the bot into Discord using the token retrieved from config.py 
# and starts listeninug for commands
###############################################################################

bot.run(TOKEN)