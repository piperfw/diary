import json
import datetime
import re, sys, os, logging

# level=logging.INFO for more information
logging.basicConfig(level=logging.ERROR, format='%(asctime)s:%(name)s:%(levelname)s: %(message)s',
	datefmt='%d/%m/%Y %H:%M:%S')
logger = logging.getLogger(__name__)

class Diary:
	# Path to directory containing script, .json and the README
	# ~~~~~~~~~~~~~ TO EDIT ~~~~~~~~~~~~~~~ #
	SCRIPT_DIR = '/home/username/documents/diary/'
	# ~~~~~~~~~~~~~ TO EDIT ~~~~~~~~~~~~~~~ #
	# .json file containing a JSON object. Each key-value pair of this object represents an event; 
	# the key is the event title while the value is another JSON object containing key-values 
	# pairs describing date, time and location of the event.
	# This file should be present in script directory else a full path specified here.
	EVENTS_FILE = 'events.json'
	# Name of this script (no extension)
	SCRIPT_NAME = 'diary'
	# Name of help .txt in script directory
	MAN_NAME = 'usage'
	# List of entries required for an event (may be empty strings). The time/date must also have correct formatting.
	REQUIRED_KEYS = ['date', 'time', 'location']

	@staticmethod
	def get_non_empty_input(prompt):
		"""Static method to prompt user until a non-trivial input is entered. Called in main()

		:return: user_input : str
		"""
		user_input = ''
		while not user_input:
			print(prompt, end=' ')
			user_input = input()
		return user_input

	def __init__(self, num_days=7, title=None, **kwargs):
		# Number of days to print events for, including today. Default 7 (one week)
		self.num_days = num_days
		# Dictionary of events obtained from .json
		self.events = {}
		# Deserialize .json: JSON object -> python dictionary self.events
		self.read_events_file()
		# Today's date and time (datetime struc)
		self.today = datetime.datetime.today()

		# Check each event has the required keys
		for event_title, event_obj in self.events.items():
			for required_key in self.REQUIRED_KEYS:
				if required_key not in event_obj:
					logger.error('Formatting error in event {} of {}, exiting.'.format(event_obj, self.EVENTS_FILE))
					# Don't just remove event and continue as add_event() may be called, which overwrites
					# .json with self.events
					sys.exit(1)					

		self.new_title = title
		self.new_event_dict = {}
		# If title and kwargs are passed, then function of script is to add a new event to .json
		# This is a dictionary and must be syntax checked
		if self.new_title:
			logger.info('Functionality to run: Add new event to {}'.format(self.EVENTS_FILE))
			# kwargs given date, time and location key-values pairs of event dictionary (see call in main())
			self.new_event_dict = kwargs
			# Add event to self.events as a key-value pair: self.new_title - self.new_event_dict, to be serialized
			self.add_event()
		# Otherwise just print any required events
		else:
			logger.info('Functionality to run: Present next {} days of diary.'.format(self.num_days))
 			# Generate a datetime key-value pair for each event in self.events (key = 'event_datetime')
			self.make_date_time()
			# Sort the list according to the 'event_datetime' key
			self.event_list = []
			self.sort_diary()
			self.present_diary()

	def read_events_file(self):
		"""Deserialise EVENTS_FILE. JSON object -> Python dictionary (self.events) 

		self.events is a dictionary whose keys are event titles and values are dictionaries describing the
		date, time and location of the respective event (i.e. a 'dictionary of dictionaries').
		"""
		# Full path of EVENTS_FILE
		events_file_path = os.path.join(self.SCRIPT_DIR, self.EVENTS_FILE)
		# Open .json for reading and deserialise using json.load
		with open(events_file_path, 'r') as events_file:
			self.events = json.load(events_file)

	def make_date_time(self):
		"""Make a datetime object for each event in self.events

		This datetime object is constructed using the 'time' and 'date' keys known to be present (See __init__)
		in the dictionary describing each event and is stored as the value of the key 'event_datetime' in the same
		dictionary.
		"""
		for event_title, event_dict in self.events.items():
			try:
				# Split 'data' and 'time' values of event on any NON-digit and construct a list from a result
				# This will send 2018-06-08 and 15:00 to ['2018', '06', '08'] and ['15','00'], respectively.
				date_list=[int(i) for i in re.split('\D',event_dict['date'])]
				time_list=[int(i) for i in re.split('\D',event_dict['time'])]
				# The constructor from datetime module is used to make the corresponding datetime object
				self.events[event_title]['event_datetime'] = datetime.datetime(
					date_list[0], date_list[1], date_list[2], hour=time_list[0], minute=time_list[1])
				logger.info('Making datetime for event {}'.format(event_title))
				logger.info('Date \'{}\' and time \'{}\' used to create \'event_datetime\' value of {}'.format(
					event_dict['date'],event_dict['time'],self.events[event_title]['event_datetime']))
			# An exception is raised if, for example, event has month>12.
			except (ValueError, IndexError) as e:
				# Again, don't just delete event as self.events may be written to EVENTS_FILE
				logger.info(e)
				logger.error('Incorrect date format for {} in {}, exiting'.format(event_title, EVENTS_FILE))
				sys.exit(1)
				# print('Incorrect date format for {} in {}, ignoring event'.format(event_title, EVENTS_FILE))
				# # Remove incorrect event and continue 
				# del self.events[event_title]
			except OverflowError as e:
				logger.info(e)
				logger.error('Date for {} in {} is unreasonable, exiting'.format(event_title, EVENTS_FILE))

	def sort_diary(self):
		"""Convert self.events into a list, and sort this list according to datetime object of each event.

		self.event_list is a list of dictionaries. Each dictionary is the value of a key-value pair in self.events,
		with the addition of the key 'title' and its value, the title of the event which was originally a key in
		self.events. It's going to be very confusing reading this at a later date...

		It is necessary to convert to a list because a dictionary cannot be sorted (ordering of key-value pairs not
		dependable).
		"""
		for event_title, event_dict in self.events.items():
			event_dict['title'] = event_title
			self.event_list.append(event_dict)
		# Sort events according to their datetime object 
		# (datetime objects can be directly compared, objects later in time are larger)
		self.event_list = sorted(self.event_list, key=lambda k: k['event_datetime'])


	def present_diary(self):
		"""Print diary entries from today to today + num_days in a nice format
		"""

		# Truncate self.event_list according to events that occur from today until today + num_days
		self.truncate_diary()
		# Construct string to format diary, depending on num_days
		num_events = len(self.event_list)
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

		for event_obj in self.event_list:
			long_date = datetime.datetime.strftime(event_obj['event_datetime'], "%a, %b %d")
			time = datetime.datetime.strftime(event_obj['event_datetime'], "%H:%M")
			# '\033[4m' escape code gives underlining in terminal (bash)
			str_to_print += '\033[4m' + long_date + '\033[0m\n' + time + '\t'
			str_to_print += event_obj['title'].capitalize()
			# If there is a location (i.e. a NON-empty string), display it too
			if event_obj['location']:
				str_to_print +=  ', ' + event_obj['location'].capitalize() + '\n'

		print(str_to_print)

		# Functionality END

	def truncate_diary(self):
		"""Truncate self.event_list according to events that fall from NOW to the END of today + num_days

		So num_days = 0 gives events occurring for the REMAINDER of today only, while num_days = 1 gives events
		occurring in the remainder of today or ANYTIME tomorrow.
		"""

		# To calculate the max_datetime, remove hours/mins from self.today and add one day 
		# (Which gives the end of today), and then add num_days
		# Hrs, Mins, Secs default to 0
		try:			
			start_of_today = datetime.datetime(self.today.year,self.today.month,self.today.day)
			max_datetime = start_of_today + datetime.timedelta(days=(self.num_days+1))
			# List comprehension; datetime of event must be greater than current time/date but less than the maximum
			truncated_event_list = [event_obj for event_obj in self.event_list if 
				event_obj['event_datetime'] > self.today and event_obj['event_datetime'] < max_datetime]
			self.event_list = truncated_event_list
		except OverflowError as e:
			logger.info(e)
			logger.error('Time span is unreasonable, exiting.')
			sys.exit(1)

	def add_event(self):
		"""Check user entries for new event object. Add to self.events. Serialise (-> EVENTS_FILE)
		"""
		try:
			# Create datetime object for purposes of allowing user to check correctness. Code repeated from 
			# sellf.make_date_time() but easier to keep this way for now.
			date_list=[int(i) for i in re.split('\D',self.new_event_dict['date'])]
			time_list=[int(i) for i in re.split('\D',self.new_event_dict['time'])]
			self.new_event_dict['event_datetime'] = datetime.datetime(
				date_list[0], date_list[1], date_list[2], hour=time_list[0], minute=time_list[1])
			str_to_print = 'Please check your event\'s details:\n'
			long_date = datetime.datetime.strftime(self.new_event_dict['event_datetime'], "%a, %b %d")
			time = datetime.datetime.strftime(self.new_event_dict['event_datetime'], " %H:%M")
			str_to_print += '\nEvent for ' + long_date + time
			str_to_print += '\nEvent Title: ' + self.new_title.capitalize() 
			str_to_print += '\nLocation: ' + self.new_event_dict['location'].capitalize() 
			# str_to_print += '\nDescription: ' + self.new_event_dict['desc'].capitalize() 
			# str_to_print += '\nCompany: ' + self.new_event_dict['company'].capitalize()

			str_to_print += "\nWould you like to add this event to the diary (y/n)? "
			if self.new_event_dict['event_datetime'] < self.today:
				str_to_print += "Note: The event is in the past. "
			print(str_to_print)

			# Delete added event_datetime entry (cannot be serialized anyway)
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
						# Add new event to dictionary of events. Remember, in self.events each key is an event title
						# and the value a dictionary describing that event (it's date, time and location).
						self.events[self.new_title]  = self.new_event_dict
						# Serialize events
						json.dump(self.events,events_file)
						# Remove backup (given serialization successful) - possibly leave backup (?)
						logger.info('Write to {} successful. Removing backup file.'.format(events_file))
						os.remove(backup_file_path)
					# Break from loop
					break
				elif user_input == 'n' or user_input == 'N':
					break
				else:
					print('Invalid input. Please try again: ')
					logger.info('User entered {}. \'y\' or \'n\' expected'.format(user_input))
		except (ValueError, IndexError) as e:
			logger.info(e)
			logger.error('Incorrect date or time format.')
		except OverflowError as e:
			logger.info(e)
			logger.error('Date is unreasonable.')
		# Functionality END


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