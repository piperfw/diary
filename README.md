# diary
Small diary/calendar script for the Bash shell. Written in python3.

#### Description
- Calendar events are stored as a JSON array in `events.json`
- Each event has a title, date, time and a location (optional)
- Run `diary -a` from the command line to add a new event to the events file
- `diary X` prints events in the diary occurring within `X` days (default 7)
- `diary -d X` May be used to remove events in the diary occurring within `X` days
- `diary -h` prints a summary of the usage and set-up
- `diary -s` saves _all_ events in the diary to a text file in a nice format

#### Set-up
- Ensure `diary.py`, `events.json` and `usage` are in the same directory
- Create an alias in your `~/.bashrc` with the following line (otherwise the script must be run with `python full_path_to_diary.py`)
```sh
alias diary="python full_path_to_diary.py"
```
For example, `alias diary="python /home/username/diary-folder/diary.py"` 
(here `python` is your python 3 executable - `python3` on some systems). 

Notes: 
- The `events.json` file _must_ exist and contain _at least_ an empty JSON array, '`[]`'
#### Possible Future Features
- Ability to edit events in the diary
- 'Repeat' field to have events automatically repeat after a certain number of hours/days
- Option to use different date formats
- Additional fields such as event description, duration and company

#### Changelog
##### V1.0 (2018-06-08)
##### V1.1 (2018-06-17)
- Events now stored as a JSON array instead of a JSON object
- Can now have arbitrary many events with the same title (or time, date etc.)
- No longer breaks if `event.json` contains an empty JSON array (i.e. user has no events).
##### V1.2 (2018-06-22)
- Added `-s` option to saved events to `saved_events` in a human readable format. Events are grouped by year.
##### V1.3 (2018-07-14)
- Added `-d` option to remove events from the diary within a certian number of days
- Number of events may now be negative (view/delete events in the past)
- `-v` option to display version number
