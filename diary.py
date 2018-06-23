import json
import datetime
import re, sys, os, logging

# TODO:
# Additional fields: Duration, description and company
# Delete functionality
# Configuration file; option for different date formats

# level=logging.INFO for more information
logging.basicConfig(level=logging.WARNING, format='%(asctime)s:%(name)s:%(levelname)s: %(message)s',
	datefmt='%d/%m/%Y %H:%M:%S')
logger = logging.getLogger(__name__)

class Diary:
	# Path to directory containing diary.py, EVENTS_FILE, MAN_NAME
	# ~~~~~~ TO EDIT ~~~~~~~~ #
	SCRIPT_DIR = '/home/user/example_directory/'
	# ~~~~~~ TO EDIT ~~~~~~~~ #
	# .json file containing a JSON array. Each element of this array is a dictionary representing an event.
	# Each event dictionary has key-value pairs describing event title,  date, time and location.
	# This file should be present in script directory else a full path specified here (same applies for 
	# SCRIPT_NAME, MAN_NAME and SAVE_FILE).
	EVENTS_FILE = 'events.json'
	# Name of this script minus .py extension.
	SCRIPT_NAME = 'diary'
	# Name of help text file.
	MAN_NAME = 'usage'
	# Name of text file to which events should be saved; will be created if non-existent.
	# This file will never be overwritten. Instead, a digit will be appended in the case of duplicates (e.g. saved_diary5).
	SAVE_FILE = 'saved_diary'
	# List of entries required for an event (may be empty strings). The time & date must also have correct formatting.
	# Additional entries are ignored
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
		# Number of days to print events for, including today, if applicable. Default 7 (one week).
		self.num_days = num_days
		# List of dictionaries obtained from EVENTS_FILE. Each dictionary represents an event.
		self.events = []
		# If not empty, kwargs is a dictionary describing an event to be added to EVENTS_FILE. This must be syntax checked.
		self.new_event_dict = kwargs
		# Deserialize EVENTS_FILE: JSON array --> python list == self.events
		self.read_events_file()
		# Total number of events found in EVENTS_FILE (possibly 0). Currently unused.
		self.total_number_of_events = len(self.events)
		# Today's date and time (datetime structure).
		self.today = datetime.datetime.today()

		# Check each event in EVENTS_FILE has the required keys
		for event_obj in self.events:
			for required_key in self.REQUIRED_KEYS:
				if required_key not in event_obj:
					logger.error('Formatting error in event {} of {}, exiting.'.format(event_obj, self.EVENTS_FILE))
					# Don't just remove event and continue as add_event() may be called, and this overwrites EVENTS_FILE
					# with contents of self.events (could allow program to continue if not self.new_event_dict).
					sys.exit(1)					

	def present_or_save_diary(self, present=False, save=False):
		"""Master function to invoke other member functions on current instantiation. Called from main().

		If save is True, save diary in a human readable format; save_diary() called.
		If present is True, print diary to terminal in a human readable format; present_diary() called.

		In either case, the events must firstly be sorted via calls to make_all_date_time() and sort_diary().
		"""
		# Generate a datetime key-value pair for each event in self.events (key = 'event_datetime').
		self.make_all_date_time()
		# Sort the list according to this new 'event_datetime' key.
		self.sort_diary()

		if present:
			logger.info('Functionality to run: Present next {} days of diary.'.format(self.num_days))
			# Print the diary in a human readable format.
			self.present_diary()
		if save:
			logger.info('Functionality to run: Save diary to text file.')
			# Save diary to a text file in a human readable format.
			self.save_diary()


	def read_events_file(self):
		"""Deserialise EVENTS_FILE. JSON array --> Python list (self.events) 

		self.events is a list of dicts whose key-values are strings describing the title,
		 date, time and location of an event.
		"""
		# Full path of EVENTS_FILE
		events_file_path = os.path.join(self.SCRIPT_DIR, self.EVENTS_FILE)
		# If no events file exists, create it 
		if not os.path.isfile(events_file_path):
			string_to_print = '{} not a file in {}. '.format(self.EVENTS_FILE, self.SCRIPT_DIR)
			# Extra: check that it's not a directory! (An exception would probably be thrown if tried to open a dir)
			if os.path.isdir(events_file_path):
				str_to_print += 'It is a directory. Please correct this.'
				logger.error(string_to_print)
				sys.exit(1)
			else:
				str_to_print += 'Creating file.'
				print(str_to_print)
				logger.info(string_to_print)
		# Open .json for reading and deserialise using json.load
		with open(events_file_path, 'r') as events_file:
			try:
				self.events = json.load(events_file)
			# except thrown if not a valid JSON document (i.e. formatting error)
			except json.JSONDecodeError as e:
				logger.error('{} is not a valid JSON document. No events loaded'.format(events_file_path))
				logger.info('Note: an empty file is not valid (minimum is a file containing an empty JSON array \'[]\'.')
				# Could sys.exit(1) here but not necessary; self.events is just left empty

	def make_all_date_time(self):
		"""Make a datetime object for each event in self.events."""
		for event_dict in self.events:
			# N.B. dictionaries are mutable so event_dict is altered by place (like passing by reference).
			self.make_date_time(event_dict)

	def make_date_time(self, event_dict):
		"""Make a datetime object for a single event.

		This datetime object is constructed using the 'time' and 'date' keys known to be present (see __init__) in the 
		dictionary describing each event and is stored as the value of the key 'event_datetime' in the same dictionary.
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
		# An exception is raised if, for example, event_dict['date'] has a month value exceeding 12.
		except (ValueError, IndexError) as e:
			# As in __init__, don't just delete event (del self.events[event_index] where event_index is determined using a
			# search) as self.events may be written to EVENTS_FILE.
			logger.info(e)
			# For logging: Check whether event is in event list. If it isn't, we are in --add mode, so could use
			# if not self.new_event_dict (equivalently could just pass a flag to this method). This is a bit ugly!
			if event_dict in self.events:
				error_string = 'Incorrect date format for {} in {}, exiting.'.format(event_dict['title'], self.EVENTS_FILE)
			else:
				error_string = 'Incorrect data format.' # (for event specified by user following --add)
		except OverflowError as e:
			# Could group OverflowError with other exceptions and just exit from that except block.
			logger.info(e)
			if event_dict in self.events:
				error_string = 'Date for {} in {} is unreasonable, exiting.'.format(event_dict['title'], self.EVENTS_FILE)
			else:
				error_string = 'Date is unreasonable.'
		if error_string:
			logger.error(error_string)
			sys.exit(1)

	def sort_diary(self):
		"""Sort self.events according to the datetime object of each event (earlier events appear nearer the start of the list).
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
		# Add formatted string describing event, for each remaining event
		for event_obj in self.events:
			str_to_print += self.generate_event_string(event_obj, escape_codes=True)
		# Print constructed string to console (escape codes are used to underline the date).
		print(str_to_print)

		# Functionality ~ END ~ (unless save was also True in save_or_print_diary())

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
			# List comprehension; datetime of event must be greater than current time/date but less than the maximum.
			truncated_event_list = [event_obj for event_obj in self.events if 
				event_obj['event_datetime'] > self.today and event_obj['event_datetime'] < max_datetime]
			self.events = truncated_event_list
		except (ValueError,OverflowError) as e:
			# OverflowError occurs if num_days exceeds 999999999 (max timedelta).
			# Value error occurs if max_datetime would have a year exceeding 9999 (a maximum for datetime objects).
			logger.info(e)
			logger.error('Number of days to generate diary for is too large, exiting.')
			sys.exit(1)

	def generate_event_string(self, event_obj, escape_codes=False):
		"""Return a nicely formatted string for an event with a datatime key

		return : event_string : str
		"""
		event_string = ''
		# Check  event_datetime key exists (it should as make_all_date_time() has been called)
		if 'event_datetime' not in event_obj:
			event_string += 'No valid datetime.' + '\t'
			logger.warning('No event_datetime key has been generated for the event with title {}'.format(event_obj['title']))
		else:
			# Use datetime object to make a nicely formatted date and time
			long_date = datetime.datetime.strftime(event_obj['event_datetime'], "%a, %b %d")
			time = datetime.datetime.strftime(event_obj['event_datetime'], "%H:%M")
			# If printing to console, underline date
			if escape_codes:
				event_string += '\033[4m' + long_date + '\033[0m\n' + time + '\t'
			else:
				event_string += long_date  +  '\n' + time + '\t'
		if event_obj['title']:
			title_str = event_obj['title']
			event_string += title_str[0].upper() + title_str[1:]
		if event_obj['location']:
			loc_string = event_obj['location']
			event_string += ', ' + loc_string[0].upper() + loc_string[1:]
		# Add newline before next event/end of output.
		event_string += '\n'
		return event_string

	def add_event(self):
		"""Check user entries for new event object. Add to self.events. Serialise (--> EVENTS_FILE).
	
		Note: This method was previously called from __init__ if kwargs** were passed (if self.new_event_dict)
		N.B. Using .readlines() and .write() to create backup file appears to disrupt original format by 
		adding in newlines However, if the backup is saved as a .json in Sublime Text 3, the original format is restored
		(Hopefully this is not a ST3 peculiarity).
		"""
		logger.info('Functionality to run: Add new event to {}'.format(self.EVENTS_FILE))
		# Create datetime object for purposes of allowing user to check correctness. 
		self.make_date_time(self.new_event_dict)
		# Generate string with formatting of event as given in a normal call to diary.
		str_to_print = 'Please check your event\'s details:\n'
		str_to_print += self.generate_event_string(self.new_event_dict, escape_codes=True)
		str_to_print += "\nWould you like to add this event to the diary (y/n)? "
		if self.new_event_dict['event_datetime'] < self.today:
			str_to_print += "Note: The event is in the past. "
		# Prompt user
		print(str_to_print, end='')

		# Delete added event_datetime entry (CANNOT be serialized)
		del self.new_event_dict['event_datetime']

		# Loop to get y/n response from user. Put in separate method if needed elsewhere.
		while True:
			user_input = input()
			if user_input == 'y' or user_input == 'Y':
				# Construct full path to EVENTS_FILE, and a backup file 
				# (overwrite back up if already exists - consider checking this)
				events_file_path = os.path.join(self.SCRIPT_DIR, self.EVENTS_FILE)
				backup_file_path = os.path.splitext(events_file_path)[0] + '.bak.json'
				# Backup events file to a temporary file
				with open(events_file_path, 'r') as events_file:
					lines = events_file.readlines()
					# or lines = events_file.read()
				with open(backup_file_path, 'w') as backup_file:
					logger.info('Creating backup file {}'.format(backup_file_path))
					for line in lines:
						backup_file.write(line)
					# or backup_file.write(lines)
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

	def save_diary(self):
		"""Save diary to SAVE_FILE (possibly with an appended digit) in a human readable format"""

		# Starting full path of SAVE_FILE N.B. SAVE_FILE has no .txt extension
		save_file_path = os.path.join(self.SCRIPT_DIR, self.SAVE_FILE)		
		# Construct string to write to file
		str_to_write = ('Diary saved on ' + datetime.datetime.strftime(self.today, "%Y-%m-%d")	
		+ ' at ' + datetime.datetime.strftime(self.today, "%H:%M:%S") + '\n\n')

		# Copy of the self.events to be mutated (in case want to use self.events later)
		copy_events = list(self.events) # COPY NOT JUST ASSIGMENT (otherwise both refer to same list!)
		# To construct str_to_write, we get the year of the first (earliest) event, then iterate through
		# copy_events gathering all the events occurring in the same year. These are be written together.
		# Perform the following until copy_events is empty
		while copy_events:
			# Year of earliest event in remaining list
			year = copy_events[0]['event_datetime'].year
			# 'Header' for all events occurring in the same year
			str_to_write += str(year) + '\n' + '----' + '\n'
			# Add string representation of all events in the same year
			for index,event_obj in enumerate(copy_events):
				if event_obj['event_datetime'].year == year:
					# Do not use console escape codes; just want plain text
					str_to_write += self.generate_event_string(event_obj, escape_codes=False)
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
		# (alternatively I could always write to self.SAVE_FILE, only in append mode)
		digit = 1
		while os.path.exists(save_file_path):
			logger.info('{} exists. Adding {}.'.format(save_file_path,digit))
			# Reset path name
			save_file_path = os.path.join(self.SCRIPT_DIR, self.SAVE_FILE)
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

	# N.B. First element of sys.argv is always 'diary.py'
	# No additional arguments --> execute default behaviour (events in coming week)
	if len(sys.argv) == 1:
		option = '7'
	else:
		option = sys.argv[1]
	# Check whether additional argument is a string consisting of digits ONLY
	if option.isdigit():
		# If so, convert to int & create anonymous Diary() object and call present diary()
		# Could make present flag a member variable (would just move it into Diary() argument)
		Diary(num_days=int(option)).present_or_save_diary(present=True)
	elif option == '-h' or option == '--help':
		# Print message in usage
		print(usage_message)
	elif option == '-s' or option == '--save':
		Diary().present_or_save_diary(save=True)
	elif option == '-a' or option == '--add':
		# 'Interactive mode' - add an event to the diary
		title = Diary.get_non_empty_input('Event title:')
		date = Diary.get_non_empty_input('Date (yyyy-mm-dd):')
		time = Diary.get_non_empty_input('Time (HH:MM):')
		loc = input('Location (Optional): ') # May be empty
		# Possibly add 'description' and 'company' fields in a future release. Also: DURATION
		# desc = input('Description (Optional): ')
		# company = input('Company (Optional): ')
		desc = ''
		company = ''
		# Description and Company parameters are currently unused while location is optional.
		Diary(title=title,date=date,time=time,location=loc,description=desc,company=company).add_event();
	# If incorrect option notify user. Note: Any extra arguments are ignored.
	else:
		print('Incorrect option. See --help for usage.')
		sys.exit(1)

if __name__ == '__main__':
	main()