import json
import datetime
import re, sys, os, logging

# level=logging.INFO for more information
logging.basicConfig(level=logging.WARNING, format='%(asctime)s:%(name)s:%(levelname)s: %(message)s',
	datefmt='%d/%m/%Y %H:%M:%S')
logger = logging.getLogger(__name__)

class Diary:
	# Path to directory containing script, .json and the .txt
	# ~~~~~~ TO EDIT ~~~~~~~~ #
	SCRIPT_DIR = '/home/pip/python_projects/diary/'
	# ~~~~~~ TO EDIT ~~~~~~~~ #
	# .json file containing a JSON array. Each element of this array is a dictionary representing an event.
	# Each event dictionary has key-value pairs describing event title,  date, time and location.
	# This file should be present in script directory or a full path specified here.
	EVENTS_FILE = 'events.json' # Relative path
	# Name of this script (no extension)
	SCRIPT_NAME = 'diary'
	# Name of help .txt in script directory
	MAN_NAME = 'usage'
	# List of entries required for an event (may be empty strings). The time & date must also have correct formatting.
	REQUIRED_KEYS = ['title', 'date', 'time', 'location']

	@staticmethod
	def get_non_empty_input(prompt):
		"""Static method to prompt user until a non-trivial input is entered. Called in main().

		:return: user_input : str
		"""
		user_input = ''
		while not user_input:
			print(prompt, end=' ')
			user_input = input()
		return user_input

	def __init__(self, num_days=7, **kwargs):
		# Number of days to print events for, including today. Default 7 (one week).
		self.num_days = num_days
		# Dictionary of events obtained from .json. Each event is itself a dictionary.
		self.events = []
		# If not empty, kwargs is a dictionary describing an event and must be syntax checked.
		# (see call in main())
		self.new_event_dict = kwargs
		# Deserialize .json: JSON object -> python dictionary self.events
		self.read_events_file()
		# Total number of events found in .json (possibly 0). Currently unused.
		self.total_number_of_events = len(self.events)
		# Today's date and time (datetime struc).
		self.today = datetime.datetime.today()

		# Check each event has the required keys
		for event_obj in self.events:
			for required_key in self.REQUIRED_KEYS:
				if required_key not in event_obj:
					logger.error('Formatting error in event {} of {}, exiting.'.format(event_obj, self.EVENTS_FILE))
					# Don't just remove event and continue as add_event() may be called, which overwrites
					# .json with self.events. Could allow program to continue if not self.new_event_dict
					sys.exit(1)					
		# If kwargs were passed, then program is to add a new event to .json. 
		if self.new_event_dict:
			logger.info('Functionality to run: Add new event to {}'.format(self.EVENTS_FILE))
			# Add event to self.events as a dictionary, and then serialize the extended list.
			self.add_event()
		# Otherwise the functionality is to print any required events.
		# In future may have to remove all this from __init__ as add new options - instead have them as methods
		# and call from main, of have a method which takes command line arguments and decides appropriate action.
		else:
			logger.info('Functionality to run: Present next {} days of diary.'.format(self.num_days))
 			# Generate a datetime key-value pair for each event in self.events (key = 'event_datetime').
			self.make_all_date_time()
			# Sort the list according to this new 'event_datetime' key.
			self.sort_diary()
			# Print the diary in a human readable format.
			self.present_diary()

	def read_events_file(self):
		"""Deserialise EVENTS_FILE. JSON array -> Python list (self.events) 

		self.events is a list whose key-values strings describing the title, date, time and
		location of an event.
		"""
		# Full path of EVENTS_FILE
		events_file_path = os.path.join(self.SCRIPT_DIR, self.EVENTS_FILE)
		# If no events file exists, create it 
		if not os.path.isfile(events_file_path):
			string_to_print = '{} does not exist. Creating file.'.format(self.EVENTS_FILE)
			# if self.new_event_dict:
			# 	str_to_print += ' Creating file.'
			print(str_to_print)
			logger.info(string_to_print)

		# Open .json for reading and deserialise using json.load
		with open(events_file_path, 'r') as events_file:
			try:
				self.events = json.load(events_file)
			# except thrown if not a valid JSON document (i.e. formatting error)
			except json.JSONDecodeError as e:
				logger.error('{} is not a valid JSON document. No events loaded'.format(events_file_path))
				logger.debug('Note that a file with no events is not valid.')
				# Could sys.exit(1) here but not necessary; self.events is just left empty

	def make_all_date_time(self):
		"""Make a datetime object for each event in self.events."""
		for event_dict in self.events:
			# N.B. dictionaries are mutable so event_dict is altered by place (like passing by reference).
			self.make_date_time(event_dict)

	def make_date_time(self, event_dict):
		"""Make a datetime object for a single event of the required format.

		This datetime object is constructed using the 'time' and 'date' keys known to be present (See __init__)
		in the dictionary describing each event and is stored as the value of the key 'event_datetime' in the same
		dictionary.
		"""
		# Error string to show if event_dict has an invalid date or time.
		error_string = ''
		try:
			# Split 'data' and 'time' values of event on any NON-digit and construct a list from a result
			# This will send 2018-06-08 and 15:00 to ['2018', '06', '08'] and ['15','00'], respectively.
			date_list=[int(i) for i in re.split('\D',event_dict['date'])]
			time_list=[int(i) for i in re.split('\D',event_dict['time'])]
			# The constructor from datetime module is used to make the corresponding datetime object
			event_dict['event_datetime'] = datetime.datetime(
				date_list[0], date_list[1], date_list[2], hour=time_list[0], minute=time_list[1])
			logger.info('Making datetime for event with title \'{}\''.format(event_dict['title']))
			logger.info('Date \'{}\' and time \'{}\' used to create \'event_datetime\' value of {}'.format(
				event_dict['date'],event_dict['time'],event_dict['event_datetime']))
		# An exception is raised if, for example, event has a month value exceeding 12.
		except (ValueError, IndexError) as e:
			# As in __init__, don't just delete event as self.events may be written to EVENTS_FILE.
			# del self.events[event_number] # Remove incorrect event and continue 
			logger.info(e)
			# For logging - check whether event is in event list. If it isn't, we are in --add mode, so could use
			# if not self.new_event_dict (equivalently could just pass a flag to this method). This is a bit ugly!
			if event_dict in self.events:
				error_string = 'Incorrect date format for {} in {}, exiting.'.format(event_dict['title'], self.EVENTS_FILE)
			else:
				error_string = 'Incorrect data format.'
		except OverflowError as e:
			logger.info(e)
			if event_dict in self.events:
				error_string = 'Date for {} in {} is unreasonable, exiting.'.format(event_dict['title'], self.EVENTS_FILE)
			else:
				error_string = 'Date for {} is not valid.'.format(event_dict['title'])
		if error_string:
			logger.error(error_string)
			sys.exit(1)

	def sort_diary(self):
		"""Sort self.events according to datetime object of each element (dictionary representing an event).
		"""
		self.events = sorted(self.events, key=lambda k: k['event_datetime'])

	def present_diary(self):
		"""Print diary entries from today to today + num_days in a nice format."""

		# Truncate self.events according to events that occur from today until today + num_days
		self.truncate_diary()
		# Construct string to format diary, depending on num_days
		num_events = len(self.events)
		if num_events == 1:
			str_to_print = '\nYou have {} event'.format(num_events)
		else:
			str_to_print = '\nYou have {} events'.format(num_events)
		if self.num_days == 0:
			str_to_print += ' remaining today.\n\n'
		elif self.num_days == 1:
			str_to_print += ' between now and the end of tomorrow.\n\n'
		elif self.num_days == 7:
			str_to_print += ' in the coming week.\n\n'
		elif self.num_days == 30:
			str_to_print += ' in the coming month.\n\n'
		elif self.num_days == 365:
			str_to_print += ' in the coming year.\n\n'
		else:
			str_to_print += ' in the next {} days.\n\n'.format(self.num_days)

		for event_obj in self.events:
			long_date = datetime.datetime.strftime(event_obj['event_datetime'], "%a, %b %d")
			time = datetime.datetime.strftime(event_obj['event_datetime'], "%H:%M")
			# '\033[4m' escape code gives underlining in terminal (bash)
			str_to_print += '\033[4m' + long_date + '\033[0m\n' + time + '\t'
			str_to_print += event_obj['title'].capitalize()
			# If there is a location (i.e. a NON-empty string), display it too
			if event_obj['location']:
				str_to_print +=  ', ' + event_obj['location'].capitalize() + '\n'
		# Print constructed string
		print(str_to_print)

		# Functionality ~ END ~

	def truncate_diary(self):
		"""Truncate self.events according to events that fall from NOW to the END of today + num_days

		So num_days = 0 gives events occurring for the REMAINDER of today only, while num_days = 1 gives events
		occurring in the remainder of today or ANYTIME tomorrow.
		"""

		# To calculate the max_datetime, remove hours/mins from self.today and add one day (which gives the end of 
		# today), and then add num_days. Hrs, Mins, Secs each default to 0.
		try:			
			start_of_today = datetime.datetime(self.today.year,self.today.month,self.today.day)
			max_datetime = start_of_today + datetime.timedelta(days=(self.num_days+1))
			# List comprehension; datetime of event must be greater than current time/date but less than the maximum
			truncated_event_list = [event_obj for event_obj in self.events if 
				event_obj['event_datetime'] > self.today and event_obj['event_datetime'] < max_datetime]
			self.events = truncated_event_list
		except (ValueError,OverflowError) as e:
			# OverflowError occurs if num_days exceeds 999999999 (max timedelta)
			# Value error occurs if max_datetime would have a year exceeding 9999 (a maximum for datetime objects)
			logger.info(e)
			logger.error('Number of days to generate diary for is too large, exiting.')
			sys.exit(1)

	def add_event(self):
		"""Check user entries for new event object. Add to self.events. Serialise (--> EVENTS_FILE)."""

		# Create datetime object for purposes of allowing user to check correctness. 
		self.make_date_time(self.new_event_dict)
		# Generate string with formatting of event as given in a normal call to diary
		str_to_print = 'Please check your event\'s details:\n'
		long_date = datetime.datetime.strftime(self.new_event_dict['event_datetime'], "%a, %b %d")
		time = datetime.datetime.strftime(self.new_event_dict['event_datetime'], " %H:%M")
		str_to_print += '\nEvent for ' + long_date + time
		str_to_print += '\nEvent Title: ' + self.new_event_dict['title'].capitalize() 
		str_to_print += '\nLocation: ' + self.new_event_dict['location'].capitalize() 
		# str_to_print += '\nDescription: ' + self.new_event_dict['desc'].capitalize() 
		# str_to_print += '\nCompany: ' + self.new_event_dict['company'].capitalize()

		str_to_print += "\nWould you like to add this event to the diary (y/n)? "
		if self.new_event_dict['event_datetime'] < self.today:
			str_to_print += "Note: The event is in the past. "
		# Prompt user
		print(str_to_print)

		# Delete added event_datetime entry (CANNOT be serialized)
		del self.new_event_dict['event_datetime']

		# Loop to get y/n response from user
		while True:
			user_input = input()
			if user_input == 'y' or user_input == 'Y':
				# Construct full path to .json and a backup
				events_file_path = os.path.join(self.SCRIPT_DIR, self.EVENTS_FILE)
				backup_file_path = os.path.splitext(events_file_path)[0] + '.bak.json'
				# Backup events file to a temporary file
				with open(events_file_path, 'r') as events_file:
					lines = events_file.readlines()
				with open(backup_file_path, 'w') as backup_file:
					logger.info('Creating backup file {}'.format(backup_file_path))
					for line in lines:
						backup_file.write(line)
				# Old events file is overwritten
				with open(events_file_path, 'w') as events_file:
					# Add new event to list of events.
					self.events.append(self.new_event_dict)
					# Serialize events
					json.dump(self.events,events_file)
					# Remove backup given serialization successful (possibly leave backup (?))
					logger.info('Write to {} successful. Removing backup file.'.format(events_file))
					os.remove(backup_file_path)
				# Break from loop
				break
			elif user_input == 'n' or user_input == 'N':
				break
			else:
				print('Invalid input. Please try again: ')
				logger.info('User entered {}. \'y\' or \'n\' expected'.format(user_input))

		# Functionality ~ END ~

def main():
	help_file_path = os.path.join(Diary.SCRIPT_DIR, Diary.MAN_NAME)
	with open(help_file_path, 'r') as man_page:
		# usage_message = repr("\n".join(man_page.readlines())) # Investigate why escape codes to underline aren't working
		# It appears that python is escaping the backslashes, so these are escaped in the shell too.
		# Solution:  use the 'string-escape' code to decode the string.
		usage_message = '\n'
		for line in man_page:
			usage_message += bytes(line, 'utf-8').decode('unicode_escape')
		# usage_message = "\n".join(man_page.readlines())

	# N.B. First element of sys.argv is always 'diary.py'
	# No additional arguments -> default behaviour (events in coming week)
	if len(sys.argv) == 1:
		option = '7'
	else:
		option = sys.argv[1]
	# Check whether additional argument is a string consisting of digits ONLY
	if option.isdigit():
		# If so, convert to int & create anon. Diary object (.present_diary will be called)
		Diary(num_days=int(option))
	elif option == '-h' or option == '--help':
		# Print message in DIARY(1).txt
		print(usage_message)
	elif option == '-a' or option == '--add-event':
		# 'Interactive mode' - add an event to the diary
		title = Diary.get_non_empty_input('Event title:')
		date = Diary.get_non_empty_input('Date (yyyy-mm-dd):')
		time = Diary.get_non_empty_input('Time (HH:MM):')
		loc = input('Location (Optional): ') # May be empty
		# desc = input('Description (Optional): ')
		# company = input('Company (Optional): ')
		desc = ''
		company = ''
		# Description and Company parameters are currently unused while location is optional.
		Diary(title=title,date=date,time=time,location=loc,description=desc,company=company)
	# If incorrect option notify user. Note: Any extra arguments are ignored.
	else:
		print('Incorrect option. See --help for usage.')
		sys.exit(1)

if __name__ == '__main__':
	main()