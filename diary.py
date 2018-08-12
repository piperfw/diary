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
	EVENTS_FILE = 'events.json'
	# Name of help text file.
	MAN_NAME = 'usage'
	# Name of text file to which events should be saved; will be created if non-existent.
	# This file will never be overwritten. Instead, a digit will be appended in the case of duplicates (e.g. saved_diary5).
	SAVE_FILE = 'saved_diary'
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


	def __init__(self, options):
		# Full path to events file.
		self.events_file_path = os.path.abspath(os.path.join(os.path.dirname(__file__), self.EVENTS_FILE))
		# Datetime format used when user adds events. Datetimes are always stored in ISO format.
		self.datetime_format = ' '.join([self.DATE_FORMAT, self.TIME_FORMAT])
		# Number of days to print events for, including today, if applicable. Default 7 (one week).
		self.num_days = options['days']
		# List of dictionaries obtained from EVENTS_FILE. Each dictionary represents an event.
		self.events = []
		# List of events to remove from self.events, if the --delete option was specified
		self.events_to_delete = []
		# Deserialize EVENTS_FILE: JSON array --> python list == self.events
		self.read_events_file()
		# Check each event in EVENTS_FILE has the required keys
		if not self.check_event_keys():
			return
		# Total number of events found in EVENTS_FILE (possibly 0). Currently unused.
		self.total_number_of_events = len(self.events)
		# Today's date and time (datetime structure).
		self.today = datetime.datetime.today()
		if options['add-event']:
			self.add_event()
			return
		if options['delete']:
			return
		self.present_diary()


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
		for event_obj in self.events:
			for required_key in self.REQUIRED_KEYS:
				if required_key not in event_obj:
					logger.error('Event {} in {} is missing a {}. Exiting.'.format(event_obj, self.EVENTS_FILE, required_key))
					# Don't just remove event and continue as add_event() may be called, and this overwrites EVENTS_FILE
					# with contents of self.events (could allow program to continue if not self.new_event_dict).
					return False
		return True

	def add_event(self):
		title = self.get_non_empty_input('Event title:')
		while True:
			date = self.get_non_empty_input('Date ({}):'.format(self.DATE_FORMAT))
			if date == 'q':
				return
			time = self.get_non_empty_input('Time ({}):'.format(self.TIME_FORMAT))
			if time == 'q':
				return
			new_datetime = self.make_dateime_using_class_format(date=date, time=time)
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

	def make_dateime_using_class_format(self, date, time):
		try:
			datetime_str = ' '.join([date,time])
			return datetime.datetime.strptime(datetime_str, self.datetime_format)
		except ValueError as e:
			if 'bad directive' in e:
				logger.error('Date or time format specified in {} is invalid: {}.'.format(os.path.basename(__file__), e))
			else:
				logger.info(e)
			return False

	def make_datetime_using_iso_format(self, event_dict):
		try:
			return datetime.datetime.fromisoformat(event_dict.get('ISO'))
		except ValueError as e:
			logger.error('Date for event {} in {} is missing or non-iso format (yyyy-mm-dd).'.format(
				event_dict.get('title'), self.events_file_path))
			return False

	def get_yn_input(self, prompt=' '):
		user_input = ''
		while user_input not in ['y','Y','n','N']:
			print(prompt, end=' ')
			user_input = input()
		return user_input.lower()

	def user_wants_event(self, event_dict, event_datetime=None):
		print('\nPlease check your event\'s details:\n{}'.format(
			self.generate_event_string(event_dict=event_dict, event_datetime=event_datetime, escape_codes=True)),
			end='')
		return True if self.get_yn_input('Would you like to add this event to the diary (y/n)?') == 'y' else False

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

	def truncate_diary(self, delete=False):
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
			if self.num_days >= 0:
			# To calculate the max_datetime, remove hours/mins from self.today and add one day (which gives the end 
			# of today), and then add num_days. Hrs, Mins, Secs each default to 0.
				max_datetime = start_of_today + datetime.timedelta(days=(self.num_days+1))
				min_datetime = self.today
			else:
				max_datetime = self.today
				min_datetime = start_of_today + datetime.timedelta(days=(self.num_days))
		except (ValueError,OverflowError) as e:
			# OverflowError occurs if |num_days| exceeds 999999999 (max timedelta).
			# Value error occurs if max_datetime would have a year exceeding 9999 (a maximum for datetime objects).
			# Or if min_datetime would have a negative year (?).
			logger.info(e)
			logger.error('Number of days to generate diary for is too large, exiting.')
			sys.exit(1)

		for event_dict in self.events:
			event_datetime = self.make_datetime_using_iso_format(event_dict)
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

	def present_diary(self):
		"""Print diary entries from today to today + num_days in a nice format."""
		# Truncate self.events according to events that occur from today until today + num_days (see self.truncate_diary
		# for details when num_days is negative).
		self.truncate_diary()
		# Construct string to format diary, depending on the number of days and the remaining number of events.
		num_events = len(self.events)
		str_to_print = '\nYou have {} event'.format(num_events)
		if num_events not in {-1,1}:
			str_to_print += 's'
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
		elif self.num_days > 0:
			str_to_print += ' in the next {} days.\n\n'.format(self.num_days)
		elif self.num_days == -1:
			str_to_print += ' remaining in your diary from today and yesterday.\n\n'.format(self.num_days)
		else:
			str_to_print += ' remaining in your diary from the previous {} days.\n\n'.format(abs(self.num_days))
		if num_events == 0:
			# Remove the newline characters if there are no events.
			str_to_print = str_to_print[1:-2]
		# Add formatted string describing event, for each remaining event
		for event_dict in self.events:
			str_to_print += self.generate_event_string(event_dict, escape_codes=True)
		# Print constructed string to console (escape codes are used to underline the date).
		print(str_to_print)

def main():
	Diary({'add-event':False, 'days':7, 'delete':False})

if __name__ == '__main__':
	main()