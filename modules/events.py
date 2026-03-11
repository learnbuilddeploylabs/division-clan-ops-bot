################################################################################
# Imports
# Importing datetime so events can store specific date and time.
################################################################################

from datetime import datetime
import discord

###############################################################################
# EVENT CLASS
# This class represents a single clan event (raid, summit, descent, etc.)
###############################################################################

class Event:
	###########################################################################
	# INITIALIZE EVENT
	# This function runs when a new event is created.
	# It sets up core information that defines the event.
	###########################################################################

	def __init__(self, event_id, activity, host, event_time, max_players):
		self.event_id = event_id
		self.activity = activity
		self.host = host
		self.event_time = event_time
		self.max_players = max_players

		#######################################################################
		# PLAYER LIST
		# players -> active roster
		# reserve -> waitlist for full events
		#######################################################################
		
		self.players = []
		self.reserve = []

		#######################################################################
		# DISCORD MESSAGE TRACKING
		# These store event post location to edit when players join/leave
		#######################################################################

		self.message_id = None
		self.channel_id = None

	###########################################################################
	# ADD PLAYER 
	# Attempts to add a player to an event
	###########################################################################
			
	def add_player(self, player):
		# Prevent duplicate joins
		if player in self.players or player in self.reserve:
			return "exists"

		# Add player if event has room
		if len(self.players) < self.max_players:
			self.players.append(player)
			return "joined"

		# Add player to reserve list if event is full
		else:
			self.reserve.append(player)
			return "reserve"

	###########################################################################
	# REMOVE PLAYER
	# Removes player from the event, fills with reserve players if available
	###########################################################################
	
	def remove_player(self, player):

		# Player leaves the active roster
		if player in self.players:
			self.players.remove(player)

			# Promote first reserve player if available
			if self.reserve:
				promoted = self.reserve.pop(0)
				self.players.append(promoted)
				return "promoted"

			return "removed"

		# Player leaves the reserve list
		elif player in self.reserve:
			self.reserve.remove(player)
			return "removed_reserve"

		else:
			return "not_found"

	###########################################################################
	# PLAYER COUNT
	# Returns current roster player count. Does not include reserve list
	###########################################################################

	def player_count(self):
		return len(self.players)

	###########################################################################
	# CHECK IF EVENT IS FULL
	# Returns True if roster is full, False if not
	###########################################################################

	def is_full(self):
		return len(self.players) >= self.max_players

	###########################################################################
	# FORMAT EVENT
	# Creates a formatted text block representing the event
	###########################################################################

	def format_event(self):
		output = ""

		output += f"{self.activity}\n"
		output += f"Host: {self.host}\n"
		output += f"Agents: {len(self.players)} / {self.max_players}\n\n"

		# Active roster
		if self.players:
			output += "Roster\n"
			for player in self.players:
				output += f"{player}\n"

		return output

	###########################################################################
	# FORMAT EVENT EMBED
	# Creates a Discord embed for the event
	###########################################################################

	def format_event_embed(self):

		# Event title
		embed = discord.Embed(
			title=f"Operation Briefing: {self.activity}",
			color=0xF39C12
		)

		# Event ID
		embed.add_field(
			name="Event ID",
			value=str(self.event_id),
			inline=True
		)

		# Event host
		embed.add_field(
			name="Host",
			value=self.host,
			inline=True
		)

		# Event time
		time_string = self.event_time.strftime("%a %I:%M %p")
		embed.add_field(
			name="Time",
			value=time_string,
			inline=True
		)

		# Event agent count
		embed.add_field(
			name="Agents",
			value=f"{len(self.players)} / {self.max_players}",
			inline=False
		)

		# Event roster
		roster_text = "\n".join(self.players) if self.players else "None"
		embed.add_field(
			name="Roster",
			value=roster_text,
			inline=False
		)

		#Event reserve roster
		if self.reserve:
			reserve_text = "\n".join(self.reserve)
			embed.add_field(
				name="Reserve",
				value=reserve_text,
				inline=False
			)

		return embed 