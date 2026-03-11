###############################################################################
# Imports
# Import the Even class so the manager can create/control Event objects
###############################################################################

from modules.events import Event

###############################################################################
# EVENT MANAGER
# This class manages all active events in the bot
###############################################################################

class EventManager:

	###########################################################################
	#  INITIALIZE EVENT MANAGER
	# Creates storage for all events and sets up automatic event ID counter
	###########################################################################

	def __init__(self):

		# Dictionary storing all active events
		self.events = {}

		# Next available event ID
		self.next_event_id = 1

	###########################################################################
	# CREATE EVENT
	# Creates a new event and stores it in the manager
	###########################################################################
	
	def create_event(self, activity, host, event_time, max_players):

		# Generate a new event ID
		event_id = self.next_event_id
		self.next_event_id += 1

		# Create the Event object
		event = Event(event_id, activity, host, event_time, max_players)

		# Store the event
		self.events[event_id] = event 

		return event

	###########################################################################
	# LIST EVENTS
	# Returns a list of all active events
	###########################################################################

	def list_events(self):
		return list(self.events.values())

	###########################################################################
	# GET EVENT
	# Retrieves a specific event by its event ID
	###########################################################################
	
	def get_event(self, event_id):
		return self.events.get(event_id)

	###########################################################################
	# REMOVE EVENT 
	# Delets an event from the manager
	###########################################################################

	def remove_event(self, event_id):

		if event_id in self.events:
			del self.events[event_id]
			return True

		return False