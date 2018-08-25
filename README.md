# diary
Small diary/calendar script for the Bash shell. Written in python3 (3.7+).

### Description
- Calendar events are stored as a JSON array in `events.json`
- Each event has a title, date and location (optional)
- Run `diary -a` from the command line to add a new event to the events file
- `diary X` prints events in the diary occurring within `X` days (default 7)
- `diary -d X` May be used to remove events in the diary occurring within `X` days
- `diary -h` prints a summary of the usage and set-up
- `diary -s` saves _all_ events in the diary to a text file in a nice format

### Bash Alias (Optional)
- Create an alias in your `~/.bashrc` with the following line
```sh
alias diary="python full_path_to_diary.py"
```
For example, `alias diary="python /home/username/diary-folder/diary.py"` (here `python` is your python 3 executable - `python3` on some systems).

Otherwise, the script must always be run with `python full_path_to_diary.py`.

### Changing date formats
In order to change the formats used when entering a date and time for an event (`-a`), edit the `DATE_FORMAT` and `TIME_FORMAT` class variables near the top of the `Diary` class in `diary.py`. To change the formatting used when printing time and dates to the console instead edit the `LONG_DATE_FORMAT` and `LONG_TIME_FORMAT`variables (details found in the class docstring). Each of these variables must be a valid directive for the `strftime` directive from the `datetime` module. THe official docs provide a reference for the accepted format codes: [8.1.8. strftime() and strptime() Behavior.](https://docs.python.org/3/library/datetime.html#strftime-and-strptime-behavior)
### Feature ideas
- Ability to edit events in the diary
- 'Repeat' field to have events automatically repeat after a certain number of hours/days
- Additional fields such as event description, duration and company

### Changelog
##### v1.0 (2018-06-08)
##### v1.1 (2018-06-17)
- Events now stored as a JSON array instead of a JSON object
- Can now have arbitrary many events with the same title (or time, date etc.)
- No longer breaks if `event.json` contains an empty JSON array (i.e. user has no events).
##### v1.2 (2018-06-22)
- Added `-s` option to saved events to `saved_events` in a human readable format. Events are grouped by year.
##### v1.3 (2018-07-14)
- Added `-d` option to remove events from the diary within a certain number of days
- Number of events may now be negative (view/delete events in the past)
- `-v` option to display version number
##### v1.4 (2018-08-13)
- Re-write of script to improve structure and extensibility
- Events now have a single 'ISO' field - an iso-formatted string - instead of separate date and time fields
- `event.json` is now created automatically on first run of the script
- Better handling of command line options (only one allowed per time)
- Usage message moved into main class; `diary.py` is the only file required now
- Ability to use different date/time formats via class variables
##### v1.5 (2018-08-25)
- Events can now be set to repeat after a certain number of days
