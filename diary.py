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

	ALLOWED_OPTIONS = {'help':False, 'add-event':False, 'version': False, 'save-diary':False}
	ALLOWED_OPTIONS_WITH_PARAMETER = {'delete': None, 'present': None}
	OPTION_ABBREVIATIONS = {'h':'help', 'd':'delete', 'a':'add-event', 's':'save-diary', 'v':'version'}

	USAGE = """Todo"""

	@staticmethod
	def check_int(str_to_check):
		"""Static method to check whether a string str is an integer (non-negative or negative).
		:return: .isdigit() : boolean
		"""
		if str_to_check[0] in ('-', '+'):
		    return str_to_check[1:].isdigit()
		return str_to_check.isdigit()


	def __init__(self, options):
		# Dictionary of options passed as command line arguments
		self.options = options
		# self.unset_options_to_defaults()
		# if self.had_to_print_help_or_version():
		# 	return
		# Full path to events file.
		self.events_file_path = os.path.abspath(os.path.join(os.path.dirname(__file__), self.EVENTS_FILE_RELATIVE))
		# Datetime format used when user adds events. Datetimes are always stored in ISO format.
		self.datetime_format = ' '.join([self.DATE_FORMAT, self.TIME_FORMAT])
		# List of dictionaries obtained from EVENTS_FILE. Each dictionary represents an event.
		self.events = []
		# List of events to remove from self.events, if the --delete option was specified
		self.events_to_delete = []
		# Deserialize EVENTS_FILE: JSON array --> python list == self.events
		self.read_events_file()
		# Check each event in EVENTS_FILE has the required keys
		if not self.check_event_keys():
			return
		self.sort_events_list()
		# Today's date and time (datetime structure).
		self.today = datetime.datetime.today()
		self.choose_and_execute_function()

	def choose_and_execute_function(self):
		option_functions = {
			'help': self.print_usage,
			'version': self.print_version,
			'present': self.present_diary,
			'add-event': self.add_event,
			'save-diary': self.save_diary,
			'delete': self.delete_events
		}
		for option, func in option_functions.items():
			if option in self.options:
				func()
				return

	def print_usage(self):
		print(self.USAGE)

	def print_version(self):
		print('{} {}'.format(os.path.splitext(os.path.basename(__file__))[0], self.VERSION))

	def unset_options_to_defaults(self):
		"""Option values in self.options that were NOT provided by command line arguments are set to the default values
		given in self.ALLOWED_OPTIONS and self.ALLOWED_OPTIONS_WITH_PARAMTER.
		"""
		for option_name, default_value in self.ALLOWED_OPTIONS.items():
			if option_name not in self.options:
				self.options[option_name] = default_value
		for option_name, default_value in self.ALLOWED_OPTIONS_WITH_PARAMETER.items():
			if option_name not in self.options:
				self.options[option_name] = default_value

	def had_to_print_help_or_version(self):
		if self.options['help']:
			print(self.USAGE)
			return True
		if self.options['version']:
			print('{} {}'.format(os.path.splitext(os.path.basename(__file__))[0], self.VERSION))
			return True
		return False

	def able_to_convert_option_str_to_int(self, option_key):
		try:
			self.options[option_key] = int(self.options[option_key])
			return True
		except ValueError:
			logger.error('Number of days must be an integer.')
			return False

	def read_events_file(self):
		"""Deserialise EVENTS_FILE. JSON array --> Python list (self.events) 

		self.events is a list of dicts whose key-values are strings describing the title,
		 date, time and location of an event.
		"""
		# If no events file exists, create it 
		if os.path.isdir(self.events_file_path):
			logger.error('{} is a directory. Aborting.'.format(self.events_file_path))
			sys.exit(1)
		if not os.path.isfile(self.events_file_path):
			logger.info('{} does not exist. Creating file.'.format(self.events_file_path))
			with open(self.events_file_path, 'w') as events_file:
				json.dump([], events_file)
			return
		# Open .json for reading and deserialise using json.load
		with open(self.events_file_path, 'r') as events_file:
			try:
				self.events = json.load(events_file)
			# except thrown if not a valid JSON document (i.e. formatting error)
			except json.JSONDecodeError as e:
				logger.error('{} is not a valid JSON document. No events loaded'.format(self.events_file_path))
				logger.info('Note: an empty file is not valid (minimum is a file containing an empty JSON array \'[]\'.')
				# Could sys.exit(1) here but not necessary; self.events is just left empty

	def check_event_keys(self):
		# Check each event in EVENTS_FILE has the required keys
		for event_dict in self.events:
			for required_key in self.REQUIRED_KEYS:
				if required_key not in event_dict:
					logger.error('Event {} in {} is missing a {}. Exiting.'.format(event_dict, self.EVENTS_FILE, required_key))
					# Don't just remove event and continue as add_event() may be called, and this overwrites EVENTS_FILE
					# with contents of self.events (could allow program to continue if not self.new_event_dict).
					return False
		return True

	def sort_events_list(self):
		"""Sort self.events according to the datetime object of each event (earlier events appear nearer the start of the list).
		"""
		self.events = sorted(self.events, key=lambda k: k['ISO']) # Can directly sort by datetime string as in ISO format.
		# self.events = sorted(self.events, key=lambda k: self.make_datetime_using_iso_format(k))

	def add_event(self):
		title = self.get_non_empty_input('Event title:')
		while True:
			date = self.get_non_empty_input('Date ({}):'.format(self.DATE_FORMAT))
			if date == 'q':
				return
			time = self.get_non_empty_input('Time ({}):'.format(self.TIME_FORMAT))
			if time == 'q':
				return
			new_datetime = self.get_datetime_from_user_date_time(date=date, time=time)
			if not new_datetime:
				print('Invalid date or time. Please try again (Enter q to quit).')
				continue
			else:
				break
		new_datetime_iso = new_datetime.isoformat(sep=' ')
		new_event_dict = {'title':title, 'ISO': new_datetime_iso}
		# May be empty
		location = input('Location (Optional): ')
		if location:
			new_event_dict['location'] = location
		if not self.user_wants_event(event_dict=new_event_dict, event_datetime=new_datetime):
			return
		self.backup_events_file()
		# Add new event to list of events.
		self.events.append(new_event_dict)
		# Write self.events to events file.
		self.write_to_events_file()
		# Remove backup
		self.remove_backup_events_file()

	def get_non_empty_input(self, prompt=' '):
		"""Static method to prompt user until a non-trivial input is entered. Called in main().

		:return: user_input : str
		"""
		user_input = ''
		while not user_input:
			print(prompt, end=' ')
			user_input = input()
		return user_input

	def get_datetime_from_user_date_time(self, date, time):
		try:
			datetime_str = ' '.join([date,time])
			return datetime.datetime.strptime(datetime_str, self.datetime_format)
		except ValueError as e:
			if 'bad directive' in e:
				logger.error('Date or time format specified in {} is invalid: {}.'.format(os.path.basename(__file__), e))
			else:
				logger.info(e)
			return False

	def get_datetime_from_event_dict(self, event_dict):
		try:
			return datetime.datetime.fromisoformat(event_dict.get('ISO'))
		except ValueError as e:
			logger.error('Date for event {} in {} is missing or non-iso format (yyyy-mm-dd).'.format(
				event_dict.get('title'), self.events_file_path))
			return False

	def get_bool_from_yn_input(self, prompt=' '):
		user_input = ''
		while user_input not in ['y','Y','n','N']:
			print(prompt, end=' ')
			user_input = input()
		if user_input in ['y', 'Y']:
			return True
		return False

	def user_wants_event(self, event_dict, event_datetime=None):
		print('\nPlease check your event\'s details:\n{}'.format(
			self.generate_event_string(event_dict=event_dict, event_datetime=event_datetime, escape_codes=True)),
			end='')
		return self.get_bool_from_yn_input('Would you like to add this event to the diary (y/n)?')

	def generate_event_string(self, event_dict, event_datetime=None, escape_codes=True):
		event_str = ''
		if event_datetime is None:
			event_datetime = datetime.datetime.fromisoformat(event_dict['ISO'])
		long_date_str = datetime.datetime.strftime(event_datetime, self.LONG_DATE_FORMAT)
		long_time_str= datetime.datetime.strftime(event_datetime, self.LONG_TIME_FORMAT)
		if escape_codes:
			event_str +=  '\033[4m' + long_date_str + '\033[0m\n' + long_time_str + '\t'
		else:
			event_str +=   long_date_str + '\n' + long_time_str + '\t'
		event_str += event_dict['title'].capitalize()
		location = event_dict.get('location')
		if location is not None:
			event_str += ', ' + location
		# Add newline before next event/end of output.
		event_str += '\n'
		return event_str

	def backup_events_file(self):
		# Construct full path to a backup file 
		backup_file_path = self.events_file_path + '.bak'
		with open(self.events_file_path, 'r') as events_file:
			lines = events_file.read()
			# or lines = events_file.read()
		with open(backup_file_path, 'w') as backup_file:
			logger.info('Creating backup file {}'.format(backup_file_path))
			backup_file.write(lines)

	def write_to_events_file(self):
		with open(self.events_file_path, 'w') as events_file:
			# Serialize events - catch exception here?
			json.dump(self.events, events_file, separators=(',', ':'))
			# Remove backup given serialization successful (possibly leave backup (?))
			logger.info('Write to {} successful. Removing backup file.'.format(events_file))

	def remove_backup_events_file(self):
		backup_file_path = self.events_file_path + '.bak'
		os.remove(backup_file_path)

	def truncate_diary(self, num_days, delete=False):
		"""Truncate self.events according to events that fall from NOW to the END of today + num_days if num_days 
		is positive, and from the beginning of today - |num_days| to NOW if num_days is negative.

		So num_days = 0 gives events occurring for the REMAINDER of today only, while num_days = 1 gives events
		occurring in the remainder of today or ANYTIME tomorrow. Similarly, num_days = -1 gives events that occurred
		earlier today or ANYTIME yesterday (and have not been deleted form the library).

		If delete=True, instead truncate self.events_to_delete (set in self.delete_events) AND assign self.events
		to those events being excluded.
		"""
		start_of_today = datetime.datetime(self.today.year, self.today.month, self.today.day)
		truncated_event_list = []
		excluded_event_list = []
		try:
			if num_days >= 0:
			# To calculate the max_datetime, remove hours/mins from self.today and add one day (which gives the end 
			# of today), and then add num_days. Hrs, Mins, Secs each default to 0.
				max_datetime = start_of_today + datetime.timedelta(days=(num_days+1))
				min_datetime = self.today
			else:
				max_datetime = self.today
				min_datetime = start_of_today + datetime.timedelta(days=(num_days))
		except (ValueError,OverflowError) as e:
			# OverflowError occurs if |num_days| exceeds 999999999 (max timedelta).
			# Value error occurs if max_datetime would have a year exceeding 9999 (a maximum for datetime objects).
			# Or if min_datetime would have a negative year (?).
			logger.info(e)
			logger.error('Range of days is too large. Aborting.')
			sys.exit(1)

		for event_dict in self.events:
			event_datetime = self.get_datetime_from_event_dict(event_dict)
			# List comprehension; datetime must be greater than current time/date but less than max_datetime.
			if event_datetime > min_datetime and event_datetime < max_datetime:
				truncated_event_list.append(event_dict)
			else:
				excluded_event_list.append(event_dict)
		if delete:
			self.events_to_delete = truncated_event_list
			self.events = excluded_event_list
		else:
			self.events = truncated_event_list

	def delete_events(self):
		# Truncate self.events according to events that occur with num_days (see self.truncate_diary for implementation)
		if not self.able_to_convert_option_str_to_int('delete'):
			return
		self.truncate_diary(num_days=self.options['delete'], delete=True)
		# if no events to delete, just exit
		if (len(self.events_to_delete) == 0):
			logger.info('No in diary within {} days of now.'.format(self.options['delete']))
			print('Nothing to delete.')
			return
		if self.user_wants_removal():
			self.backup_events_file()
			# Write self.events to events file.
			self.write_to_events_file()
			# Remove backup
			# self.remove_backup_events_file()
			print('Events deleted. A backup of the old events file can be found at {}.'.format(self.events_file_path + '.bak'))

	def user_wants_removal(self):
		str_to_print =  'Events to be removed from the diary:\n\n'
		for event_dict in self.events_to_delete:
			str_to_print += self.generate_event_string(event_dict, escape_codes=True)
		# Prompt user to confirm events to be removed from the diary
		print(str_to_print)
		return self.get_bool_from_yn_input('Confirm removal (y/n)')

	def present_diary(self):
		"""Print diary entries from today to today + num_days in a nice format."""
		# Truncate self.events according to events that occur from today until today + num_days (see self.truncate_diary
		# for details when num_days is negative).
		if not self.able_to_convert_option_str_to_int('present'):
			return
		self.truncate_diary(num_days=self.options['present'])
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
		if self.options['present'] in special_day_strings:
			str_to_print += special_day_strings[self.options['present']]
		elif self.options['present'] > 0:
			str_to_print += ' in the next {} days.'.format(self.options['present'])
		else:
			str_to_print += ' in your diary from the previous {} days.'.format(abs(self.options['present']))
		if num_events > 0:
			str_to_print += '\n\n'
		# Add formatted string describing event, for each remaining event
		for event_dict in self.events:
			str_to_print += self.generate_event_string(event_dict, escape_codes=True)
		# Print constructed string to console (escape codes are used to underline the date).
		print(str_to_print)

	def save_diary(self):
			"""Save diary to SAVE_FILE (possibly with an appended digit) in a human readable format"""
			# Starting full path of SAVE_FILE N.B. SAVE_FILE has no .txt extension
			save_file_path = os.path.join(os.path.dirname(__file__), self.SAVE_FILE_RELATIVE)		
			# Construct string to write to file
			str_to_write = ('Diary saved on ' + datetime.datetime.strftime(self.today, self.DATE_FORMAT)	
				+ ' at ' + datetime.datetime.strftime(self.today, self.TIME_FORMAT) + '\n\n')
			# Copy of the self.events to be mutated (in case want to use self.events later)
			copy_events = list(self.events) # COPY NOT JUST ASSIGMENT (otherwise both refer to same list!)
			# To construct str_to_write, we get the year of the first (earliest) event, then iterate through
			# copy_events gathering all the events occurring in the same year. These are be written together.
			# Perform the following until copy_events is empty
			while copy_events:
				# Year of earliest event in remaining list
				year = self.get_datetime_from_event_dict(copy_events[0]).year
				# 'Header' for all events occurring in the same year
				str_to_write += str(year) + '\n' + '----' + '\n'
				# Add string representation of all events in the same year
				for index, event_dict in enumerate(copy_events):
					if self.get_datetime_from_event_dict(event_dict).year == year:
						# Do not use console escape codes; just want plain text
						str_to_write += self.generate_event_string(event_dict, escape_codes=False)
					else:
						# As we know list is sorted, once an event in the next calendar year is found, we can stop 
						# AND remove all prior events (do not remove events as we go along; this mutates copy_events).
						# If index=length-1, then this will return an empty string (tested)
						copy_events = copy_events[index+1:] # Position of colon is essential!
						# N.B. Previously was deleting events and breaking, but this was dangerous as if all events 
						# were deleted, copy_events would not exist, and an exception would be thrown when the 
						# while condition was checked.
						# del copy_events[:index]
						break # Can exit for loop as done
					# If all remaining events in copy_events have the same year, the above else will never be run
					# In this case we are done; so set copy_events = [] to exit the loop
					if index == (len(copy_events)-1):
						copy_events = []
				# Some white space before next year's events (still inside while loop)
				str_to_write += '\n'
			# If save file already exists (or there is a dir with this name), do not overwrite it
			# Instead append digits onto the file number until a non-existing file path is created
			# (alternatively I could always write to self.SAVE_FILE_RELATIVE, only in append mode)
			digit = 1
			while os.path.exists(save_file_path):
				logger.info('{} exists. Adding \'{}\' to filename.'.format(save_file_path, digit))
				# Reset path name
				save_file_path = os.path.join(os.path.dirname(__file__), self.SAVE_FILE_RELATIVE)
				# Add digit to path name
				save_file_path += str(digit)
				# Increment digit in case next loop is run
				digit += 1

			# Now we have a file name that does not already exists, create this file and write to it
			with open(save_file_path, 'w') as write_file:
				write_file.write(str_to_write)
				# Again could iterate through using for loop (perhaps safer if str_to_write is huge).
			str_to_print = 'Diary successfully written to {}.'.format(save_file_path)
			print(str_to_print)

def main():
	# Remove first sys.argv, which is always pwmgr.py.
	del sys.argv[0]
	# List to hold options (command line arguments) provided by user.
	options = {}
	if len(sys.argv) == 0:
		sys.argv.append('7')
	if Diary.check_int(sys.argv[0]):
		options['present'] = sys.argv[0]
		del sys.argv[0]
	while sys.argv:
		arg = sys.argv.pop(0)
		stripped_arg = arg.strip('-')
		if arg.startswith('-') and stripped_arg in Diary.OPTION_ABBREVIATIONS:
			arg = '-' + arg
			stripped_arg = Diary.OPTION_ABBREVIATIONS[stripped_arg]
		if arg.startswith('--') and stripped_arg in Diary.ALLOWED_OPTIONS:
			options[stripped_arg] = True
		elif arg.startswith('--') and stripped_arg in Diary.ALLOWED_OPTIONS_WITH_PARAMETER:
			try:
				options[stripped_arg] = sys.argv.pop(0)
			except IndexError:
				print('The {} option requires a parameter.'.format(arg.strip('-')))
				sys.exit(1)
		else:
			print('Invalid argument. See --help for usage.')
			sys.exit(1)
	if len(options) > 1:
		print('Please specify one option only.')
	else:
		Diary(options)

if __name__ == '__main__':
	main()