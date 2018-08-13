import json
import datetime
import re, sys, os, logging

# level=logging.INFO for more information
logging.basicConfig(level=logging.WARNING, format='%(asctime)s:%(levelname)s: %(message)s',
	datefmt='%Y-%m-%d %H:%M:%S')
logger = logging.getLogger(__file__)

class Diary:
	# .json file containing a JSON array. Each element of this array is a dictionary representing an event.
	# Each event dictionary has key-value pairs describing event title,  date, time and location.
	# This file should be present in script directory else a relative path specified here (same applies for 
	# MAN_NAME and SAVE_FILE).
	EVENTS_FILE_RELATIVE = 'events.json'
	# Name of text file to which events should be saved; will be created if non-existent.
	# This file will never be overwritten. Instead, a digit will be appended in the case of duplicates (e.g. saved_diary5).
	SAVE_FILE_RELATIVE = 'saved_diary'
	# List of entries required for an event (may be empty strings). The time & date must also have correct formatting.
	# Additional entries are ignored
	REQUIRED_KEYS = ['title', 'ISO']
	# Version of program
	VERSION = 1.3
	# Formats used when entering a date.
	DATE_FORMAT = '%Y-%m-%d'
	TIME_FORMAT = '%H:%M'
	# Formats used when presenting a date.
	LONG_DATE_FORMAT = '%a, %b %d'
	LONG_TIME_FORMAT = '%H:%M'

	ALLOWED_OPTIONS = {
		'help':False,
		'add-event':False,
		'version': False,
		'save-diary':False
	}
	ALLOWED_OPTIONS_WITH_PARAMETER = {
		'delete': None,
		'present': None
	}
	OPTION_ABBREVIATIONS = {
		'h':'help',
		'd':'delete',
		'a':'add-event',
		's':'save-diary',
		'v':'version'
	}
	OPTION_FUNCTION_NAMES = {
		'help': 'print_usage',
		'version': 'print_version',
		'present': 'present_diary',
		'add-event': 'add_event',
		'delete': 'delete_events',
		'save-diary': 'save_diary'
	}
	USAGE = """Todo"""

	@staticmethod
	def check_int(str_to_check):
		"""Static method to check whether a string str is an integer (non-negative or negative). Called in main().
		:return: .isdigit() : boolean
		"""
		if str_to_check[0] in ('-', '+'):
			return str_to_check[1:].isdigit()
		return str_to_check.isdigit()


	def __init__(self, option):
		# Dictionary containing a single key-value pair describing the option passed as a command line argument.
		self.option = option
		# Absolute path to events file.
		self.events_file_path = os.path.abspath(os.path.join(os.path.dirname(__file__), self.EVENTS_FILE_RELATIVE))
		# Datetime format used to present or add events. Datetimes are always stored as an ISO formatted string.
		self.datetime_format = ' '.join([self.DATE_FORMAT, self.TIME_FORMAT])
		# List of dictionaries obtained from self.events_file_path. Each dictionary represents an event.
		self.events = []
		# List of events to remove from self.events, if the --delete option was specified
		self.events_to_delete = []
		# Deserialize EVENTS_FILE_RELATIVE: JSON array --> python list == self.events
		self.read_events_file()
		# Check each event in EVENTS_FILE_RELATIVE has the keys in REQUIRED_KEYS.
		if not self.check_event_keys():
			# Exit if event is missing a key (fatal).
			return
		# Sort self.events according to the 'ISO' key.
		self.sort_events_list()
		# Current date and time (equivalent to now()).
		self.now = datetime.datetime.today()
		# Based the chosen option in self.option, call an appropriate function.
		self.choose_and_execute_function()

	def read_events_file(self):
		"""Deserialise EVENTS_FILE_RELATIVE. JSON array --> Python list (self.events) 

		self.events is a list of dicts whose key-values are strings describing the title,
		 date, time and location of an event.
		"""
		# Firstly check self.events_file_path isn't a directory.
		if os.path.isdir(self.events_file_path):
			logger.error('{} is a directory. Aborting.'.format(self.events_file_path))
			sys.exit(1)
		# If no events file exists, create it.
		if not os.path.isfile(self.events_file_path):
			logger.info('{} does not exist. Creating file.'.format(self.events_file_path))
			# An empty file is not a valid JSON document, so insert an empty JSON array.
			with open(self.events_file_path, 'w') as events_file:
				json.dump([], events_file)
			return
		# Open .json for reading and deserialise using json.load
		with open(self.events_file_path, 'r') as events_file:
			try:
				self.events = json.load(events_file)
			except json.JSONDecodeError as e:
				logger.error('{} is not a valid JSON document. No events loaded.'.format(self.events_file_path))
				logger.info('Note: an empty file is not valid (minimum is a file containing an empty JSON array \'[]\'.')
				# Could sys.exit(1) here but not necessary; self.events is just left empty

	def check_event_keys(self):
		"""Check each event in self.events_file_path at least has the keys set out in self.REQUIRED_KEYS.
		:return: boolean
		"""
		for event_dict in self.events:
			for required_key in self.REQUIRED_KEYS:
				if required_key not in event_dict:
					logger.error('Event {} in {} is missing a {}. Exiting.'.format(event_dict, self.EVENTS_FILE, required_key))
					# Don't just remove event and continue as add_event() may be called, and this overwrites EVENTS_FILE
					# with contents of self.events (could allow program to continue if not self.new_event_dict).
					return False
		return True
	
	def sort_events_list(self):
		"""Sort self.events according to the value of the 'ISO' key. This is a string representing a datetime in ISO
		format (earlier events appear nearer the start of the list).
		"""
		# No need to make a datetime.datetime object - ISO formatted strings can be compared/sorted directly.
		# self.events = sorted(self.events, key=lambda k: self.make_datetime_using_iso_format(k))
		self.events = sorted(self.events, key=lambda k: k['ISO'])

	def choose_and_execute_function(self):
		"""Call the function associated with the first key in self.option."""
		try:			
			# Get the first (and only) key from self.option (StopIteration is self.option is empty).
			option_key = next(iter(self.option))
			# Get the function name associated with that key (KeyError if option_key not in self.OPTION_FUNCTION_NAMES).
			function_name = self.OPTION_FUNCTION_NAMES[option_key]
			# Could just use getattr (AttributeError if doesn't exist) but AttributeError may also occur in function_name().
			if hasattr(self, function_name):
				# Get and call the function
				getattr(self, function_name)()
			else:
				logger.error('Function {} is missing from {}.'.format(function_name, self.__class__.__name__))
		except StopIteration:
			logger.error('No option passed to constructor.')
		except KeyError:
			logger.error('No functionality is associated with the option \'{}\'.'.format(option_key))

	def print_usage(self):
		"""Print usage (help) message."""
		print(self.USAGE)

	def print_version(self):
		"""Print script name (minus extension) and version number."""
		print('{} {}'.format(os.path.splitext(os.path.basename(__file__))[0], self.VERSION))

	def present_diary(self):
		"""Print diary entries from today to today + self.option['present'] in a nice format.
		N.B. self.option['present'] may be negative (events in the past)."""
		try:
			# Currently handling of sys.argv in main() means self.option['present'] is actually type(int) already. 
			num_days = int(self.option['present'])
		except ValueError:
			print('Number of days must be an integer.')
			return
		# Truncate self.events according to events that occur from today until today + num_days.
		self.truncate_event_lists(num_days=num_days)
		# Construct string to format diary, depending on the number of days and the remaining number of events.
		num_events = len(self.events)
		str_to_print = 'You have {} event'.format(num_events)
		if num_events not in {-1,1}:
			str_to_print += 's'
		special_day_strings = {
			0: ' remaining today.', 
			1: ' between now and the end of tomorrow.',
			7: ' in the coming week.',
			30: ' in the coming month.',
			365: ' in the coming year.',
			-1: ' in your diary from today and yesterday.'
			}
		if num_days in special_day_strings:
			str_to_print += special_day_strings[num_days]
		elif num_days > 0:
			str_to_print += ' in the next {} days.'.format(num_days)
		else:
			str_to_print += ' in your diary from the previous {} days.'.format(abs(num_days))
		if num_events > 0:
			str_to_print += '\n\n'
		# Add formatted string describing event, for each remaining event
		for event_dict in self.events:
			str_to_print += self.generate_event_string(event_dict, escape_codes=True)
		# Print constructed string to console (escape codes are used to underline the date).
		print(str_to_print)

	def truncate_event_lists(self, num_days, delete=False):
			"""Truncate self.events according to events that fall from NOW to the END of today + num_days if num_days 
			is positive, and from the beginning of today - |num_days| to NOW if num_days is negative.

			So num_days = 0 gives events occurring for the REMAINDER of today only, while num_days = 1 gives events
			occurring in the remainder of today or ANYTIME tomorrow. Similarly, num_days = -1 gives events that occurred
			earlier today or ANYTIME yesterday (and have not been deleted form the library).

			If delete=True, instead truncate self.events_to_delete (set in self.delete_events) AND assign self.events
			to those events being excluded.
			"""
			# 00:00 on the current day.
			start_of_today = datetime.datetime(self.now.year, self.now.month, self.now.day)
			# Lists to populate
			truncated_event_list = []
			excluded_event_list = []
			try:
				if num_days >= 0:
					# To calculate max_datetime, remove hours/mins from self.now and add one day (which gives the end 
					# of today), and then add num_days. Hrs, Mins, Secs each default to 0.
					max_datetime = start_of_today + datetime.timedelta(days=(num_days+1))
					min_datetime = self.now
				else:
					# To calculate min_datetime, simply remove the hours/mins from self.today and then add num_days (<0)
					min_datetime = start_of_today + datetime.timedelta(days=(num_days))
					max_datetime = self.now
			except (ValueError,OverflowError) as e:
				# OverflowError occurs if |num_days| exceeds 999999999 (max timedelta).
				# Value error occurs if max_datetime would have a year >9999 or <0 (restriction of datetime object).
				logger.info(e)
				logger.error('Range of days is too large. Aborting.')
				sys.exit(1)
			for event_dict in self.events:
				# For each event, generate a datetime object (which itself cannot be serialised). Although ISO strings 
				# can be directly compared, using datetime objects is convenient to add dates (timedeltas above).
				event_datetime = self.get_datetime_from_event_dict(event_dict)
				# The 'truncated' list contains those events falling between min_datetime and max_datetime.
				if event_datetime > min_datetime and event_datetime < max_datetime:
					truncated_event_list.append(event_dict)
				else:
					# Other events are added to the excluded list.
					excluded_event_list.append(event_dict)
			# In 'delete' mode, the 'truncated' list of events are to be removed from self.events. This is achieved
			# by assigning self.events to the excluded events list and saving this to the events file.
			if delete:
				self.events = excluded_event_list
				# Record events to be deleted so user can check them.
				self.events_to_delete = truncated_event_list
			else:
				# Otherwise, in 'present' mode the truncated list is to be presented to the user. We assign the
				# truncated list to self.events just so we can just iterate through self.events in self.present_diary()
				self.events = truncated_event_list
				# No events to delete - leave self.events_to_delete empty.

	def get_datetime_from_event_dict(self, event_dict):
		"""Construct a datetime object from the value of the 'ISO' key in event_dict, an iso-formatted string.
		
		positional arguments
		event_dict : dictionary

		returns
		datetime object
		False if 'ISO' key doesn't exist, or its value is incorrectly formatted
		"""
		try:
			return datetime.datetime.fromisoformat(event_dict.get('ISO'))
		except ValueError as e:
			# .get returns None if key is missing (None is not a valid iso string!)
			logger.error('Date for event {} in {} is missing or non-iso format (yyyy-mm-dd).'.format(
				event_dict.get('title'), self.events_file_path))
			return False

	def add_event(self):
		"""Get input from user to create a new event dictionary, and add this to the diary by appending the new event
		to self.events and saving this to self.events_file_path."""
		# Title can be any non-empty string.
		title = self.get_non_empty_input('Event title:')
		# User must input a valid date & time.
		new_datetime_object = self.get_datetime_from_user()
		if not new_datetime_object:
			# self.get_datetime_from_user returns False if user wishes to abort adding an event.
			return
		# Convert datetime obj into an iso-formatted string, so it can be serialised (single space between date & time).
		new_datetime_iso = new_datetime_object.isoformat(sep=' ')
		# Add title and ISO string to event dictionary - title and ISO are the only required keys.
		new_event_dict = {'title':title, 'ISO': new_datetime_iso}
		# Location is an optional field for events (could add a series of optional fields e.g. company, description).
		location = input('Location (Optional): ')
		if location:
			# Only add the key if user enters a location.
			new_event_dict['location'] = location
		# Check user wants to add the event.
		if not self.user_wants_to_add_event(event_dict=new_event_dict):
			# If not just return to caller (__init__()); functionality ends.
			return
		# Backup self.events_file_path before making changes.
		self.backup_events_file()
		# Add new event to list of events.
		self.events.append(new_event_dict)
		# Write updated self.events to events file.
		self.write_to_events_file()
		# Remove backup as write performed successfully.
		self.remove_backup_events_file()

	def get_non_empty_input(self, prompt=' '):
		"""Prompts user until a non-trivial input is entered."""
		user_input = ''
		while not user_input:
			print(prompt, end=' ')
			user_input = input()
		return user_input

	def get_datetime_from_user(self):
		"""Prompts user for date and time in format specified by self.DATE_FORMAT and self.TIME_FORMAT. 
		self.get_datetime_object_from_date_and_time is called to get a datetime object from this.

		returns
		new_datetime : datetime.datetime
		False if user chooses to quit
		"""
		while True:
			date = self.get_non_empty_input('Date ({}):'.format(self.DATE_FORMAT))
			if date == 'q':
				return False
			time = self.get_non_empty_input('Time ({}):'.format(self.TIME_FORMAT))
			if time == 'q':
				return False
			new_datetime = self.get_datetime_object_from_date_and_time(date=date, time=time)
			# selfget_datetime_object_from_date_and_time returns False if date and time do no represent a real date.
			if not new_datetime:
				# Option to quit just in case user doesn't understand format, or the format itself is invalid.
				print('Invalid date or time. Please try again (Enter q to quit).')
				continue
			else:
				return new_datetime

	def get_datetime_object_from_date_and_time(self, date, time):
		"""Make a datetime object from date and time, using the datetime.datetime.strptime method.

		positional arguments
   		date : str -- Should be in the format of self.DATE_FORMAT
   		time : str -- Should be in the format of self.TIME_FORMAT

    	returns
    	datetime object
    	False if date & time do not represent a real date in the given format
		"""
		try:
			# Join user's date and time with a single space, to match format of self.datetime_format.
			datetime_str = ' '.join([date,time])
			# Return a datetime corresponding to datetime_str, according to self.datetime_format (see __init__()).
			return datetime.datetime.strptime(datetime_str, self.datetime_format)
		except ValueError as e:
			# 'bad directive' appears in error message if one of self.DATE_FORMAT or self.TIME_FORMAT is itself invalid.
			# This is important to log as it will be impossible to construct a datetime unless this is fixed.
			if 'bad directive' in str(e):
				logger.error('Date or time format specified in {} is invalid: {}.'.format(os.path.basename(__file__), e))
			else:
				logger.info(e)
			# Signals caller that date was invalid.
			return False

	def get_bool_from_yn_input(self, prompt=' '):
		"""Get response to a yes/no question as a boolean (True/False)."""
		user_input = ''
		while user_input not in ['y','Y','n','N']:
			print(prompt, end=' ')
			user_input = input()
		if user_input in ['y', 'Y']:
			return True
		return False

	def user_wants_to_add_event(self, event_dict):
		"""Present event_dict to the user in a human readable format and return True if the user wants to add it."""
		print('\nPlease check your event\'s details:\n{}'.format(
			self.generate_event_string(event_dict=event_dict, escape_codes=True)),
			end='')
		return self.get_bool_from_yn_input('Would you like to add this event to the diary (y/n)?')

	def generate_event_string(self, event_dict, escape_codes=True):
		"""Return a nicely formatted string for the event described by event_dict. self.LONG_DATE_FORMAT and 
		self.LONG_TIME_FORMAT are used to format the date and time, respectively. In addition, if escape_codes is
		True, ANSI code for an underline is added to the date.

		position arguments
		event_dict : dictionary
		keyword arguments
		event_datetime : datetime object corresponding to event_dict['ISO'] (default: None)
		escape_codes : boolean

		returns
		event_str : str
		"""
		# String to be returned.
		event_str = ''
		# Create a datetime object for the event (allows creation of date strings with different formats).
		# Small inefficiency: When adding an event a datetime object is created twice (once before to create iso str).
		event_datetime =self.get_datetime_from_event_dict(event_dict)
		long_date_str = datetime.datetime.strftime(event_datetime, self.LONG_DATE_FORMAT)
		long_time_str= datetime.datetime.strftime(event_datetime, self.LONG_TIME_FORMAT)
		if escape_codes:
			# \033[4m is ANSI code for underlining - could make this a class variable (and add other options).
			event_str +=  '\033[4m' + long_date_str + '\033[0m\n' + long_time_str + '\t'
		else:
			# Date and time are separated by a newline
			event_str +=   long_date_str + '\n' + long_time_str + '\t'
		# Capitalise title, and add the location after the comma, if the event has one.
		event_str += event_dict['title'].capitalize()
		location = event_dict.get('location')
		if location is not None:
			event_str += ', ' + location
		# Add newline (separates events when presenting the diary).
		event_str += '\n'
		return event_str

	def backup_events_file(self):
		"""Copy self.events_file_path to self.events_file_path + '.bak'"""
		# Construct full path to a backup file 
		backup_file_path = self.events_file_path + '.bak'
		with open(self.events_file_path, 'r') as events_file:
			lines = events_file.read()
		with open(backup_file_path, 'w') as backup_file:
			logger.info('Creating backup file {}'.format(backup_file_path))
			backup_file.write(lines)

	def write_to_events_file(self):
		"""Serialise self.events to self.events_file_path in JSON."""
		with open(self.events_file_path, 'w') as events_file:
			# separators=(',',':') to ensure all whitespace is eliminated.
			json.dump(self.events, events_file, separators=(',', ':'))
			# Remove backup given serialization successful (possibly leave backup (?))
			logger.info('Write to {} successful. Removing backup file.'.format(events_file))

	def remove_backup_events_file(self):
		"""Remove the backup file at  self.events_file_path + '.bak'."""
		os.remove(self.events_file_path + '.bak')

	def delete_events(self):
		"""Remove events from the diary which occur from now to now + self.option['delete'] days (may be negative)."""
		try:
			# So far, no validation has been performed on self.option['delete']
			num_days = int(self.option['delete'])
		except ValueError:
			print('Number of days must be an integer.')
			return
		# Remove events to be deleted from self.events while adding them to self.events_to_delete.
		self.truncate_event_lists(num_days=num_days, delete=True)
		# if no events to delete, just exit
		if self.events_to_delete == []:
			logger.info('No events in diary within {} days of now.'.format(num_days))
			print('No events to remove.')
			return
		# Remove events, if confirmed by user.
		if self.user_wants_removal():
			# Backup self.events_file_path
			self.backup_events_file()
			# Write self.events to events file.
			self.write_to_events_file()
			# This time (cf self.add_event) we don't remove the backup
			print('Events deleted. A backup of the old events file can be found at {}.'.format(
				self.events_file_path + '.bak'))

	def user_wants_removal(self):
		"""Display events to be removed from the diary and make user confirm their deletion."""
		str_to_print =  'Events to be removed from the diary:\n\n'
		for event_dict in self.events_to_delete:
			str_to_print += self.generate_event_string(event_dict, escape_codes=True)
		print(str_to_print)
		return self.get_bool_from_yn_input('Confirm removal (y/n)')

	def save_diary(self):
			"""Save diary's events to a text file in a human readable format."""
			# Absolute path to the save file.
			save_file_path = os.path.join(os.path.dirname(__file__), self.SAVE_FILE_RELATIVE)		
			# Header written to file before events - simpy timestamp
			str_to_write = ('Diary saved on ' + datetime.datetime.strftime(self.now, self.DATE_FORMAT)	
				+ ' at ' + datetime.datetime.strftime(self.now, self.TIME_FORMAT) + '\n\n')
			# Copy of the self.events to be mutated (in case want to use self.events later - not current used).
			copy_events = list(self.events)
			# To construct str_to_write, get the year of the first (earliest - events have been sorted) event, 
			# then iterate through copy_events gathering all the events occurring in the same year. 
			# These are to be grouped together (same 'section') in the text file.
			while copy_events: # Until copy_events is empty.
				# Year of earliest event in the remaining list.
				year = self.get_datetime_from_event_dict(copy_events[0]).year
				# Sub heading, for all events occurring in the same year.
				str_to_write += str(year) + '\n' + '----' + '\n'
				# Add string representation of all events in the same year.
				for index, event_dict in enumerate(copy_events):
					if self.get_datetime_from_event_dict(event_dict).year == year:
						# Do not use console escape codes; just want plain text.
						str_to_write += self.generate_event_string(event_dict, escape_codes=False)
					else:
						# As we know list is sorted, once an event in the next calendar year is found, we can stop 
						# AND remove all prior events (do not remove events as we go along; this mutates copy_events).
						# If index=length-1, then this will return an empty list (tested)
						copy_events = copy_events[index+1:] # Position of colon is essential!
						# N.B. Previously was deleting events and breaking, but this was dangerous as if all events 
						# were deleted, copy_events would not exist, and an exception would be thrown when the 
						# while condition was checked.
						break # Exit for loop.
					# If all remaining events in copy_events have the same year, the above else will never occur.
					# In this case we are completely done; so set copy_events = [] to exit the while loop.
					if index == (len(copy_events)-1):
						copy_events = []
				# Some white space before next year's events (still inside while loop)
				str_to_write += '\n'
			# If save file already exists (or there is a dir with this name), do not overwrite it. Instead append digits
			# onto the file number until a non-existing file path is created (could alternatively append onto one file).
			digit = 1
			while os.path.exists(save_file_path):
				logger.info('{} exists. Adding \'{}\' to filename.'.format(save_file_path, digit))
				# Reset path name
				save_file_path = os.path.join(os.path.dirname(__file__), self.SAVE_FILE_RELATIVE)
				# Add digit to path name
				save_file_path += str(digit)
				# Increment digit in case next loop is run
				digit += 1
			# Now that we have a new file name, create this file and write to it.
			with open(save_file_path, 'w') as write_file:
				write_file.write(str_to_write)
			str_to_print = 'Diary successfully written to {}.'.format(save_file_path)
			print(str_to_print)

def main():
	# Remove first sys.argv, which is always pwmgr.py.
	del sys.argv[0]
	# Dictionary to hold option (command line arguments) provided by user - only one option (+ parameter) is accepted.
	option = {}
	# Default behaviour (no option passed) is option 'present' with a value of 7.
	if len(sys.argv) == 0:
		option['present'] = 7
	# If first argument may be interpreted as an integer, option is 'present' with that value
	elif Diary.check_int(sys.argv[0]):
		option['present'] = int(sys.argv[0]) # Could pass string (validation occurs in Diary.present_diary)
	# Otherwise option is prefixed by - (short option) or -- (long option).
	else:
		arg = sys.argv.pop(0)
		option_name = arg.strip('-')
		if arg.startswith('-') and option_name in Diary.OPTION_ABBREVIATIONS:
			# Make into long option (prefix of '--').
			arg = '-' + arg
			# Look up option name in dictionary of abbreviations.
			option_name = Diary.OPTION_ABBREVIATIONS[option_name]
		if arg.startswith('--') and option_name in Diary.ALLOWED_OPTIONS:
			# ALLOWED_OPTIONS are simply True or False.
			option[option_name] = True
		elif arg.startswith('--') and option_name in Diary.ALLOWED_OPTIONS_WITH_PARAMETER:
			# OPTIONS_WITH_PARAMETER must be followed by a parameter (another string).
			try:
				option[option_name] = sys.argv.pop(0)
			except IndexError:
				print('The {} option requires a parameter.'.format(arg.strip('-')))
				return
		else:
			print('Invalid argument. See --help for usage.')
			return
	# Create anonymous Diary object with option dict. All functionality for this script is initiated from __init__().
	Diary(option)

if __name__ == '__main__':
	main()