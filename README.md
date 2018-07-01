# diary (in development)
Small diary/calendar script for the Bash shell. Written in python3.

#### Description
- Calendar events are stored as a JSON array in `events.json`
- Each event has a title, date, time and a location (optional)
- Run `diary -a` from the command line to add a new event to the events file
- `diary X` prints events in the diary occurring in the next `X` days (default 7)
- `diary -h` prints a summary of the usage and set-up
- `diary -s` saves _all_ events in the diary to a text file in a nice format

#### Set-up
- Ensure `diary.py`, `events.json` and `usage` are in the same directory
- Change the `SCRIPT_DIR` class variable at the top of the **Diary** class in `diary.py` to the full path of this directory
- Create an alias in your `~/.bashrc` with the following line (otherwise the script must be run with `python full_path_to_diary.py`)
```sh
alias diary="python full_path_to_diary.py"
```
For example, `alias diary="python /home/username/diary-folder/diary.py"` 
(here `python` is your python 3 executable - `python3` on some systems). 

Notes: 
- There is currently no way to delete events using the script, but a call to `diary` will never display events in the past.
- The `events.json` file _must_ exist and contain _at least_ an empty JSON array, '`[]`'
#### Planned Features
- `-d` option to delete events (for example, all events in the past)
- `-v` option to display version
- Use a configuration file to set `SCRIPT_DIR` 
- Option to use different date formats when in `-a` mode

#### Changelog
##### V1.0 (2018-06-08)
##### V1.1 (2018-06-17)
- Events now stored as a JSON array instead of a JSON object
- Can now have arbitrary many events with the same title (or time, date etc.)
- No longer breaks if `event.json` contains an empty JSON array (i.e. user has no events).
##### V1.2 (2018-06-22)
- Added `-s` option to saved events to `saved_events` in a human readable format. Events are grouped by year.
