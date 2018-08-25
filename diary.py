import json
import datetime
import re, sys, os, logging

# level=logging.INFO for more information
logging.basicConfig(level=logging.WARNING, format='%(asctime)s:%(levelname)s: %(message)s',
	datefmt='%Y-%m-%d %H:%M:%S')
logger = logging.getLogger(__file__)

class Diary:
	"""
	Class Variables
	---------------
	ALLOWED_OPTIONS : dictionary
		Each key is the full name of a possible command line option as: --key, and its value is the default for
		that option.
	ALLOWED_OPTIONS_WITH_PARAMETER : dictionary
		Each key is the full name of a possible command line option which must be followed by a single parameter as:
		--key parameter. Its value defines the default value of the parameter.
	OPTION_ABBREVIATIONS : dictionary
		Each key is a possible short command line option; -key, and its value is the key of the option in 
		ALLOWED_OPTIONS or ALLOWED_OPTIONS_WITH_PARAMETER that key is an abbreviation of.
	OPTION_FUNCTION_NAMES : dictionary
		Dictionary to act as a look-up table for functions. Each key is an option, and the value the name of the
		function to be called if that option is chosen (implemented in Diary.choose_and_execute_function).
	REQUIRED_KEYS : list
		Keys every event dictionary must have to be valid.
	EVENTS_FILE_RELATIVE : string
		Path to the JSON document used to store events (python list of dictionaries -> JSON array of objects), relative
		to this script.
	SAVE_FILE_RELATIVE : string
		Relative path of text file to save diary events to when using the --save-diary option. If this file already
		exists, a digit will be appended to the file name (see Diary.save_diary).
	DATE_FORMAT : string (datetime.datetime.strftime directive)
		Directive used to parse the DATE field entered by user following use of the -a option. 
		See the official docs for accepted format codes (e.g. '2018-08-13' would be valid for directive %Y-%m-%d').
	TIME_FORMAT : string (datetime.datetime.strftime directive)
		Directive used to parse the TIME field entered by user following use of the -a option.
		(e.g. '11:00' would be valid for directive %H:%M').
	LONG_DATE_FORMAT : string (datetime.datetime.strftime directive)
		Directive used when printing a date to the console (or saving to file). Currently, this date is underlined
		(see Diary.generate_event_string).
	LONG_TIME_FORMAT : string (datetime.datetime.strftime directive)
		Directive used when printing a time to the console (or saving to file). Currently, the time is printed below
		the date (see Diary.generate_event_string).
	LONG_DATE_ADDITIONAL_YEAR_FORMAT : string (datetime.datetime.strftime directive)
		Directive used to append a string to the date when printing to the console, if the year is different from 
		the current year (set this to an empty string if you don't want anything here).
	VERSION : float
		Current version of this program.
	USAGE : string
		Message displayed with the --help option.
	"""
	ALLOWED_OPTIONS = {
		'help':False,
		'add-event':False,
		'version': False,
		'save-diary':False
	}
	ALLOWED_OPTIONS_WITH_PARAMETER = {
		'delete': None,
		'print': None
	}
	OPTION_ABBREVIATIONS = {
		'h':'help',
		'd':'delete',
		'p':'print',
		'a':'add-event',
		's':'save-diary',
		'v':'version'
	}
	OPTION_FUNCTION_NAMES = {
		'help': 'print_usage',
		'version': 'print_version',
		'print': 'present_diary',
		'add-event': 'add_event',
		'delete': 'delete_events',
		'save-diary': 'save_diary'
	}
	REQUIRED_KEYS = ['title', 'ISO']
	EVENTS_FILE_RELATIVE = 'events.json'
	SAVE_FILE_RELATIVE = 'saved_diary'
	DATE_FORMAT = '%Y-%m-%d'
	TIME_FORMAT = '%H:%M'
	LONG_DATE_FORMAT = '%a, %b %d'
	LONG_TIME_FORMAT = '%H:%M'
	LONG_DATE_ADDITIONAL_YEAR_FORMAT = ' (%Y)'
	VERSION = 1.5
	USAGE = """\u001b[1mDIARY\u001b[21m

\u001b[1mNAME\u001b[21m
	diary - print events from diary in the coming week

\u001b[1mSYNOPSIS\u001b[21m
	diary OPTION [ARGUMENT]

\u001b[1mOPTIONS\u001b[21m
	-a, --add-event
		Enter an interactive mode to add a new event to the diary.

	-d, --delete \x1B[3mnum\x1B[23m
		Remove events from the diary within \x1B[3mnum\x1B[23m days of today's date. \x1B[3mnum\x1B[23m must be an integer (0 for events occurring
		today). A confirmation dialogue will be shown with the events to be deleted.

		\u001b[1mN.B.\u001b[21m Events which are repeats of an earlier event will \x1B[3mnot\x1B[23m be removed and so will still be displayed when
		using --print. In order to prevent such repeats from appearing, the original event must be deleted.

	\x1B[3mnum\x1B[23m
		Same as --print \x1B[3mnum\x1B[23m

	-p, --print \x1B[3mnum\x1B[23m
		Print events from diary within \x1B[3mnum\x1B[23m days of today's date.
	 	\x1B[3mnum\x1B[23m must be an integer (0 for events occurring today).

	-h, --help
		Display this message.

	-s, --save-diary
		Save diary events to a text file in a human readable format.

		For an events set to repeat after a certain number of days, only the original event is written to the file.

	-v, --version
		Display version information.
"""
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
		"""Print diary entries from today to today + self.option['print'] in a nice format.
		N.B. self.option['print'] may be negative (events in the past)."""
		# Currently handling of sys.argv in main() means self.option['print'] is actually type(int) already. 
		num_days = self.return_int_or_false_from_str(self.option['print'])
		if not num_days:
			return
		# Set min and max dates from num_days
		self.set_min_max_datetimes(num_days=num_days)
		# See if we need to generate any events based on 'repeat' key and num_days.
		self.generate_repeat_events(num_days=num_days)
		# Sort self.events according to the 'ISO' key.
		self.sort_events_list()
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
			-1: ' in your diary from yesterday to now.'
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

	def set_min_max_datetimes(self, num_days):
		"""Set self.max_datetime and self.min_datetime which define the period of the diary to be inspected.
		These instance variables are used by self.genereate_repeat_events, self.remove_events and 
		self.truncate_events_list.
		(see self.truncate_event_lists 	docstring for an explanation of the expected behaviour that must result 
		from self.max/min_datetime)."""
		# Only need to generate these once
		if hasattr(self, 'max_datetime') and hasattr(self, 'min_datetime'):
			return
		# 00:00 on the current day.
		start_of_today = datetime.datetime(self.now.year, self.now.month, self.now.day)
		try:
			if num_days >= 0:
				# To calculate max_datetime, remove hours/mins from self.now and add one day (which gives the end 
				# of today), and then add num_days. Hrs, Mins, Secs each default to 0.
				self.max_datetime = start_of_today + datetime.timedelta(days=(num_days+1))
				self.min_datetime = self.now
			else:
				# To calculate min_datetime, simply remove the hours/mins from self.today and then add num_days (<0)
				self.min_datetime = start_of_today + datetime.timedelta(days=(num_days))
				self.max_datetime = self.now
		except (ValueError,OverflowError) as e:
			# OverflowError occurs if |num_days| exceeds 999999999 (max timedelta).
			# Value error occurs if max_datetime would have a year >9999 or <0 (restriction of datetime object).
			logger.info(e)
			logger.error('Range of days is too large. Aborting.')
			sys.exit(1)

	def generate_repeat_events(self, num_days):
		"""If any event in the diary is set to repeat, add any of its repeats that would occur in the interval
		of the diary to be presented to the user ([self.min_datetime, self.max_datetime]) to self.events."""
		for event_dict in self.events:
			event_repeats = event_dict.get('repeat', False)
			if not event_repeats:
				continue
			event_datetime = self.get_datetime_from_event_dict(event_dict)
			# First date the event is set to repeat on.
			date_to_check = event_datetime + datetime.timedelta(days=event_repeats)
			# Check whether any of the repeats (event_datetime + n * event_repeats where n is an integer) fall
			# between self.min_datetime and self.max_datetime.
			while date_to_check < self.max_datetime:
				if self.min_datetime < date_to_check:
					# Add a 'repeat' event to self.events (only temporarily - self.events is not written to file).
					self.add_repeat_event(event_dict, new_datetime=date_to_check)
				# Calculate the next date the event is set to repeat on.
				date_to_check += datetime.timedelta(days=event_repeats)

	def add_repeat_event(self, event_dict, new_datetime):
		"""Add a 'repeat entry for event_dict to the list self.events. This entry has the same title (and location),
		but a different iso string (new_datetime is used) and no 'repeat' key.
		The addition of repeat entries is only meant to be temporary in the sense that self.events is never written
		to file after this function has been run (there is little point in having repeat events in the events file;
		moreover, duplicates would be difficult to handle).
		"""
		# Make a copy of event_dict. N.B. All the fields of event_dict are immutable (strings) so a shallow copy is 
		# sufficient here (else if a mutable value in repeat_event was changed it would also be changed in event_dict).
		repeat_event = dict(event_dict)
		# Edit its ISO string according to new_datetime.
		repeat_event['ISO'] = new_datetime.isoformat(sep=' ')
		# Delete the repeat key - we only want the first (often original) event to have this key.
		del repeat_event['repeat']
		# Add the repeat_event to self.events. N.B. self.events should NOT be written to file (no point having 
		# duplications in events.json).
		self.events.append(repeat_event)

	def truncate_event_lists(self, num_days, delete=False):
			"""Truncate self.events according to events that fall from NOW to the END of today + num_days if num_days 
			is positive, and from the beginning of today - |num_days| to NOW if num_days is negative.

			So num_days = 0 gives events occurring for the REMAINDER of today only, while num_days = 1 gives events
			occurring in the remainder of today or ANYTIME tomorrow. Similarly, num_days = -1 gives events that occurred
			earlier today or ANYTIME yesterday (and have not been deleted form the library).

			If delete=True, instead truncate self.events_to_delete (set in self.delete_events) AND assign self.events
			to those events being excluded.
			"""
			# Set self.min/max_datetime if they haven't been already.
			self.set_min_max_datetimes(num_days=num_days)
			# Lists to populate
			truncated_event_list = []
			excluded_event_list = []
			for event_dict in self.events:
				# For each event, generate a datetime object (which itself cannot be serialised). Although ISO strings 
				# can be directly compared, using datetime objects is convenient to add dates (timedeltas above).
				event_datetime = self.get_datetime_from_event_dict(event_dict)
				# The 'truncated' list contains those events falling between self.min_datetime and self.max_datetime.
				if event_datetime > self.min_datetime and event_datetime < self.max_datetime:
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
				# Otherwise, in 'print' mode the truncated list is to be presented to the user. We assign the
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
		new_datetime = self.get_datetime_from_user()
		if not new_datetime:
			# self.get_datetime_from_user returns False if user wishes to abort adding an event.
			return
		# Convert datetime obj into an iso-formatted string, so it can be serialised (single space between date & time).
		new_datetime_iso = new_datetime.isoformat(sep=' ')
		# Add title and ISO string to event dictionary - title and ISO are the only required keys.
		new_event_dict = {'title':title, 'ISO': new_datetime_iso}
		# Location is an optional field for events (could add a series of optional fields e.g. company, description).
		location = input('Location (Optional): ')
		if location:
			# Only add the key if user enters a location.
			new_event_dict['location'] = location
		# Ask if event should repeat after a set number of days
		if self.get_bool_from_yn_input('Event repeats (y/n)?'):
			self.add_repeat_key_value(new_event_dict)
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

	def add_repeat_key_value(self, event_dict):
		"""Add a key 'repeat' to event_dict whose value is the number of days after which the event should repeat
		(specified by user)."""
		while True:
			user_input = self.get_non_empty_input('Repeat after how many days?')
			if user_input == 'q':
				print('No repeat key added.')
				return
			repeat_after = self.return_int_or_false_from_str(user_input, must_be_positive=True)
			if not repeat_after:
				continue
			event_dict['repeat'] = repeat_after
			return

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
		event_datetime = self.get_datetime_from_event_dict(event_dict)
		long_date_str = datetime.datetime.strftime(event_datetime, self.LONG_DATE_FORMAT)
		long_time_str= datetime.datetime.strftime(event_datetime, self.LONG_TIME_FORMAT)
		# Add year to long_date_str if event does not occur in current year (could do similar grouping to that in 
		# saved_diary but think would be distracting/superfluous here). Could add parameter last_year and check to
		# see if event is in a 'new year' (return str, year from this function) but not sure if worth it (bit ugly).
		# Only do this when using escape codes (i.e. printing to code - should possibly rename this argument).
		if event_datetime.year != self.now.year and escape_codes:
			long_date_str += datetime.datetime.strftime(event_datetime, self.LONG_DATE_ADDITIONAL_YEAR_FORMAT)
		# Make a note if the event is set to repeat (N.B. Only the first event will have the 'repeat' key, not
		# the repeats themselves, so only the original event will have this additional string). I think this
		# is fine behaviour (the only slight improvement possibly would be to always have the first PRINTED
		# repeat event to have this flag -- but I think this is unnecessary/less clear [user has no way
		# of telling which event they actually created].
		event_repeats = event_dict.get('repeat')
		# event_repeats is known to be int as this script handled it's creation 
		# (provided events file was has not been # manually edited).
		repeat_str = ''
		if event_repeats is not None:
			if repeat_str == 1:
				repeat_str = ' (repeats every day)'
			else:
				repeat_str = ' (repeats every {} days)'.format(event_repeats)
		if escape_codes:
			# \033[4m is ANSI code for underlining - could make this a class variable (and add other options).
			event_str +=  '\033[4m' + long_date_str + '\033[0m' + repeat_str + '\n' + long_time_str + '\t'
		else:
			# Date and time are separated by a newline
			event_str +=   long_date_str + repeat_str + '\n' + long_time_str + '\t'
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
			logger.info('Write to {} successful. Removing backup file.'.format(self.events_file_path))

	def remove_backup_events_file(self):
		"""Remove the backup file at  self.events_file_path + '.bak'."""
		os.remove(self.events_file_path + '.bak')

	def delete_events(self):
		"""Remove events from the diary which occur from now to now + self.option['delete'] days (may be negative)."""
		# Notification for  user that the repeats of events outside the 'deletion scope' which are set to repeat in the 
		# future will still be printed when examining the diary in the very same deletion scope.
		# A system to work around this (e.g. prompt user to remove events OUTSIDE of the deletion scope which
		# would have one or more repeats inside the deletion scope) would probably be challenging to implement
		# given the current set-up.
		notification = ('Please note that past events in the diary which are set to repeat will still be displayed ' 
						+ '(see N.B. for the -d option in --help).')
		# So far, no validation has been performed on self.option['delete']
		num_days = self.return_int_or_false_from_str(self.option['delete'])
		if not num_days:
			return
		# Extra string appended onto removal message.
		self.extra_removal_message_str = ''
		# Sort self.events according to the 'ISO' key.
		self.sort_events_list()
		# Remove events to be deleted from self.events while adding them to self.events_to_delete.
		self.truncate_event_lists(num_days=num_days, delete=True)
		# if no events to delete, just exit
		if self.events_to_delete == []:
			logger.info('No events in diary within {} days of now.'.format(num_days))
			print('No events to remove.')
			print(notification)
			return
		# Check whether user wants any repeating events to continue repeating.
		self.add_new_repeat_for_event_to_be_deleted_if_user_desires()
		# Remove events, if confirmed by user.
		if self.user_wants_removal():
			# Backup self.events_file_path
			self.backup_events_file()
			# Write self.events to events file.
			self.write_to_events_file()
			# This time (cf self.add_event) we don't remove the backup.
			print('Events deleted. A backup of the old events file can be found at {}.'.format(
				self.events_file_path + '.bak'))

			print(notification)

	def get_short_date_str_from_datetime(self, datetime_to_convert):
		"""Return a string representation of datetime according to the formats specified by the variables
		self.DATE_FORMAT and self.TIME_FORMAT (separated by a single space).
		"""
		return (datetime.datetime.strftime(datetime_to_convert, self.DATE_FORMAT) + ' '
				+ datetime.datetime.strftime(datetime_to_convert, self.TIME_FORMAT))

	def return_int_or_false_from_str(self, str_to_check, must_be_positive=False):
		"""Returns int(str_to_check) if str_to_check has an integer representation and False otherwise.
		If must_be_positive, only return int(str_to_check) if it is positive.
		"""
		try:
			user_int = int(str_to_check)
			if must_be_positive and user_int < 1:
				print('Number of days must be a positive integer.')
				return False
			return user_int
		except ValueError:
			print('Number of days must be an integer.')
			return False

	def add_new_repeat_for_event_to_be_deleted_if_user_desires(self):
		"""If an event to be removed from the diary is marked to repeat the user is prompted (for that individual event)
		whether they want it to repeat in the future. If so, add a new event to self.events that after self.max_datetime.
		"""
		for event_dict in self.events_to_delete:
			event_repeats = event_dict.get('repeat', False)
			if not event_repeats:
				continue
			event_datetime = self.get_datetime_from_event_dict(event_dict)
			# Get string representation of datetime (date and time are separated by a single space).
			event_datetime_str = self.get_short_date_str_from_datetime(event_datetime)
			print('The event \'{}\' on {} is set to repeat every {} days.'.format(
				event_dict['title'], event_datetime_str, event_repeats))
			# Date on which event will start repeating again (this must be greater than self.max_datetime >= self.now)
			next_repeat_datetime = event_datetime + datetime.timedelta(event_repeats)
			# Possibly an edge case issue here when equality occurs? Not going to worry about it.
			while next_repeat_datetime < self.max_datetime:
				next_repeat_datetime += datetime.timedelta(event_repeats)
			next_repeat_datetime_str = self.get_short_date_str_from_datetime(next_repeat_datetime)
			prompt = ('Would you like it to continue repeating in the future (y/n)?' 
					  + ' (event will begin repeating again from {})'.format(next_repeat_datetime_str))
			if self.get_bool_from_yn_input(prompt):
				# Extra message shown to user when asked to confirm removal
				self.extra_removal_message_str += '- The event \'{}\' will continue to repeat starting {}.\n'.format(
					event_dict['title'], next_repeat_datetime_str)
				# Make a new repeating event on next_repeat_datetime, 
				new_event_dict = dict(event_dict)
				# Note how we do NOT remove the 'repeat' key (cf. self.add_repeat_event).
				new_event_dict['ISO'] = next_repeat_datetime.isoformat(sep=' ')
				# Add to self.events (the 'excluded events' - see self.truncate_event_lists).
				self.events.append(new_event_dict)
				# N.B. self.events will be saved (written to self.events_file) soon.
			else:
				# Otherwise do nothing (event will be removed and never repeat in the future).
				self.extra_removal_message_str += '- The event \'{}\' will no longer be repeated.\n'.format(
					event_dict['title'])

	def user_wants_removal(self):
		"""Display events to be removed from the diary and make user confirm their deletion. Additionally, """
		str_to_print =  'Events to be removed from the diary:\n\n'
		for event_dict in self.events_to_delete:
			str_to_print += self.generate_event_string(event_dict, escape_codes=True)
		str_to_print += '\n' + self.extra_removal_message_str
		print(str_to_print)
		return self.get_bool_from_yn_input('Confirm removal (y/n)')

	def save_diary(self):
			"""Save diary's events to a text file in a human readable format."""
			# Sort self.events according to the 'ISO' key.
			self.sort_events_list()
			# Absolute path to the save file.
			save_file_path = os.path.join(os.path.dirname(__file__), self.SAVE_FILE_RELATIVE)		
			# Header written to file before events - simpy timestamp
			str_to_write = ('Diary saved on ' + datetime.datetime.strftime(self.now, self.DATE_FORMAT)	
				+ ' at ' + datetime.datetime.strftime(self.now, self.TIME_FORMAT) + '\n\n')
			# Copy of the self.events to be mutated (in case want to use self.events later - not current used).
			# N.B. Although the objects in self.events are mutable (dictionaries), we never edit them, only
			# the list itself. Consequently, a shallow copy is sufficient here.
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
						copy_events = copy_events[index:] # Position of colon is essential!
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
	# Default behaviour (no option passed) is option 'print' with a value of 7.
	if len(sys.argv) == 0:
		option['print'] = 7
	# If first argument may be interpreted as an integer, option is 'print' with that value
	elif Diary.check_int(sys.argv[0]):
		option['print'] = int(sys.argv[0]) # Could pass string (validation occurs in Diary.present_diary)
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