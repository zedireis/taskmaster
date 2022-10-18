import os
import signal
from discord import User

from dotenv import load_dotenv
import nextcord
from nextcord import Interaction, SlashOption, ButtonStyle
from nextcord.ui import Button, View
from nextcord.ext import commands, tasks as ntask
import asyncio
import aiosqlite
from datetime import datetime, date, timedelta
from urllib.request import urlopen
from icalendar.cal import Calendar, Event
from xml.sax.saxutils import unescape
from pytz import timezone
from operator import itemgetter

load_dotenv()

debugOn = os.getenv("DEBUG")

bot = commands.Bot()

def handler(signum, frame):
    print("Shutting down")
    clear_users.cancel()
    exit()
 
 
signal.signal(signal.SIGINT, handler)

@bot.event
async def on_ready():
    print("Bot is ready")
    bot.db = await aiosqlite.connect('calendars.db')
    await asyncio.sleep(3)
    async with bot.db.cursor() as cursor:
        await cursor.execute("CREATE TABLE IF NOT EXISTS calendars(name TEXT PRIMARY KEY, user INTEGER, url TEXT NOT NULL, guild INTEGER)")
    await bot.db.commit()
    print("Database ready")
    clear_users.start()

help_text = {
    "Presentation" : {
        "> What do I do?" : "Find a common timeslot between selected people",
        "> Can I select the people to include?" : ":white_check_mark:",
        "> Can I select the timeslot duration?" : ":white_check_mark:",
        "---------------------------" : "---------------------------",
        "> How can I input my schedule?" : "Add a calendar iCal url and all events will be synced (see next page)"
    },
    "Add a calendar" : {
        "> Add a calendar" : "/new_calendar",
        "> name" : "name of your calendar (must be unique)",
        "> url" : "url of your calendar in iCal format",
        "Test your url" : "copy the url and paste it in a new browser tab, if it prompts you to download a .ics file means it's working",
        "image":"https://i.imgur.com/gfkeiHk.png"
    },
    "How to run" : {
        "> How can I select the people?" : "/find_timeslot users add",
        "> And now what?" : "/find_timeslot calculate",
    }
}

def create_help_page(pageNum=0):
    pageNum = pageNum % len(list(help_text))
    pageTitle = list(help_text)[pageNum]
    msg = nextcord.Embed(title=pageTitle)
    for key, val in help_text[pageTitle].items():
        if key == "image":
            msg.set_image(val)
            continue
        msg.add_field(name=key,value=val, inline=False)
    msg.set_footer(text=f"Page {pageNum+1} of {len(list(help_text))}")
    return msg

@bot.slash_command()
async def help(interaction: nextcord.Interaction):
    """As we say in PT: O tio explica"""
    current_page = 0

    async def next_callback(interaction: nextcord.Interaction):
        nonlocal current_page
        current_page += 1
        await sent_msg.edit(embed=create_help_page(pageNum=current_page), view=myView)

    next_button = Button(label="Next page", style=ButtonStyle.blurple)
    next_button.callback = next_callback

    myView = View(timeout=180)
    myView.add_item(next_button)

    sent_msg = await interaction.response.send_message(embed=create_help_page(0), view=myView, ephemeral=True)

async def addcalendar(guild_id, name, url, user_id):
    async with bot.db.cursor() as cursor:
        try:
            await cursor.execute("INSERT INTO calendars(name, user, url, guild) VALUES (?,?,?,?)", (name, user_id, url, guild_id))
            await bot.db.commit()
        except Exception as e:
            print("Erro")
            print(e)
            return False
    return True

async def deletecalendar(guild_id, name, user_id):
    async with bot.db.cursor() as cursor:
        try:
            await cursor.execute("DELETE FROM calendars WHERE name = ? AND user = ? AND guild = ?", (name, user_id, guild_id))
            await bot.db.commit()
        except Exception as e:
            print("Erro")
            print(e)
            return False
    return True

async def listcalendars(guild_id, user_id):
    async with bot.db.cursor() as cursor:
        try:
            await cursor.execute("SELECT name FROM calendars WHERE user = ? AND guild = ?", (user_id, guild_id))
            rows = await cursor.fetchall()
            calendars = []
            for row in rows:
                calendars.append(row[0])
            return calendars
        except Exception as e:
            print("Erro")
            print(e)
            return []

async def getcalendars(guild_id, user_id):
    async with bot.db.cursor() as cursor:
        try:
            await cursor.execute("SELECT url FROM calendars WHERE user = ? AND guild = ?", (user_id, guild_id))
            rows = await cursor.fetchall()
            calendars = []
            for row in rows:
                calendars.append(row[0])
            return calendars
        except Exception as e:
            print("Erro")
            print(e)
            return []

@bot.slash_command()
async def new_calendar(interaction: nextcord.Interaction, name: str, url: str):
    """Add a new calendar

    Parameters
    ----------
    interaction: Interaction
        The interaction object
    name: str
        Name of the calendar
    url: str
        The iCal url
    """
    #Fetches the calendar data from an XML/.ics resource in preperation for parsing.
    cal_data = None
    try:
        cal_data = urlopen(url)
        cal_str = cal_data.read()
        cal_data.close()
        Calendar.from_ical(cal_str)
    except Exception as e:
        await interaction.response.send_message(f"Something went wrong :cry:\nCheck if the calendar is public and in .ics format", ephemeral=True)
        return
    
    success = await addcalendar(interaction.guild_id, name, url, interaction.user.id)
    if(success):
        calendars = await listcalendars(interaction.guild_id, interaction.user.id)
        await interaction.response.send_message(f"Success: {success} Current calendars:\n"+"\n".join(calendars), ephemeral=True)
    else:
        await interaction.response.send_message(f"Success: {success} Something went wrong :cry:", ephemeral=True)

@bot.slash_command()
async def list_calendars(interaction: nextcord.Interaction):
    """List added calendars"""
    success = await listcalendars(interaction.guild_id, interaction.user.id)
    if(len(success)!=0):
        await interaction.response.send_message(f"Hi {interaction.user}! These are your calendars:\n"+"\n".join(success), ephemeral=True)
    else:
        await interaction.response.send_message(f"Hi {interaction.user}! Something went wrong :cry: Maybe you've not added calendars", ephemeral=True)

@bot.slash_command()
async def delete_calendar(
    interaction: Interaction,
    calendar: str = SlashOption(
        name="calendar",
        description="Choose a calendar to delete!",
        autocomplete=True),
    ):
    """Delete calendar

    Parameters
    ----------
    interaction: Interaction
        The interaction object
    calendar: str
        Name of the calendar
    """
    success = await deletecalendar(interaction.guild_id, calendar, interaction.user.id)
    # sends the autocompleted result
    if(success):
        calendars = await listcalendars(interaction.guild_id, interaction.user.id)
        await interaction.response.send_message(f"Success: {success} Current calendars:\n"+"\n".join(calendars), ephemeral=True)
    else:
        await interaction.response.send_message(f"Success: {success} Something went wrong :cry:", ephemeral=True)


@delete_calendar.on_autocomplete("calendar")
async def choose_calendar(interaction: Interaction, calendar: str):
    list_of_calendars = await listcalendars(interaction.guild_id, interaction.user.id)
    await interaction.response.send_autocomplete(list_of_calendars)
    


IncludedUsers = {}

@bot.slash_command()
async def find_timeslot(interaction: nextcord.Interaction):
    """
    Choose the users and then calculate a free timeslot between all
    """
    pass

@find_timeslot.subcommand()
async def users(interaction: nextcord.Interaction):
    """
    Choose the users to include
    """
    pass

@users.subcommand()
async def add(interaction: nextcord.Interaction,
    user: User = SlashOption(
        name="user",
        description="Username"),
    ):
    """
    Add user to include

    Parameters
    ----------
    interaction: Interaction
        The interaction object
    username: str
        Name of the user
    """
    if(user.bot):
        await interaction.response.send_message(f"Selected user is a bot :sad:", ephemeral=True)
    else:
        key=str(interaction.user.id)
        if key in IncludedUsers:
            IncludedUsers[key].append(user)
        else:
            IncludedUsers[key]=[user]
        await interaction.response.send_message(f"Added User: {user.name}", ephemeral=True)

@users.subcommand()
async def delete(interaction: nextcord.Interaction, username: str = SlashOption(name="username", description="Username", autocomplete=True)):
    """Delete user

    Parameters
    ----------
    interaction: Interaction
        The interaction object
    username: str
        Name of the user
    """
    key=str(interaction.user.id)
    if(key in IncludedUsers):
        for user in IncludedUsers[key]:
            if(user.name == username):
                IncludedUsers[key].remove(user)
                if(len(IncludedUsers[key])==0):
                    IncludedUsers.pop(key)
                await interaction.response.send_message(f"Removed User: {username}", ephemeral=True)
                return
        else:
            await interaction.response.send_message(f"User wasn't in the list", ephemeral=True)
    else:
        await interaction.response.send_message(f"List was empty", ephemeral=True)

@delete.on_autocomplete("username")
async def user_to_del(interaction: Interaction, username: str):
    key=str(interaction.user.id)
    if key not in IncludedUsers:
        await interaction.response.send_autocomplete([])
    else:
        if not username:
            # send the full autocomplete list
            await interaction.response.send_autocomplete([user.name for user in IncludedUsers[key]])
            return
        # send a list of nearest matches
        get_near_user = [user for user in IncludedUsers[key] if user.name.lower().startswith(username.lower())]
        await interaction.response.send_autocomplete(get_near_user)


@users.subcommand()
async def list_selected(interaction: nextcord.Interaction):
    """
    Currently selected users
    """
    key=str(interaction.user.id)
    if key not in IncludedUsers:
        await interaction.response.send_message(f"No users selected", ephemeral=True)
    else:
        msg = nextcord.Embed(title="Current User List", description="Users chosen to calculate free time")
        for user in IncludedUsers[key]:
            msg.add_field(name="->", value=user.name, inline=True)
        await interaction.response.send_message(embed=msg)

working_hours=['9:00','20:00']

def free_time(x: datetime,bounds,time):
    new=[]
    b_start=datetime.strptime(bounds[0],"%H:%M")
    b_end=datetime.strptime(bounds[1],"%H:%M")
    start=x[0][0]
    end=x[len(x)-1][1]
    min_start=(b_start-start).seconds/60
    min_end=(b_end-end).seconds/60
    if min_start >= float(time):
        new.append([bounds[0],x[0][0].strftime("%H:%M")])
    for i in range(len(x)-1):
        if ((x[i+1][0]-x[i][1]).seconds/60) >=float(time):
            new.append([x[i][1].strftime("%H:%M"),x[i+1][0].strftime("%H:%M")])
    if min_end >= float(time):
        new.append([x[len(x)-1][1].strftime("%H:%M"),bounds[1]])
    
    return new

def unscramble_events(events):
    
    events = sorted(events, key=itemgetter(0))

    if debugOn:
        print("Antes ",events)

    if(len(events)==1):
        return events

    k=0
    j=1
    while((k<j)and(j<len(events))):
        #K Começa à mesma hora
        if(events[k][0] == events[j][0]):
            #e acaba à mesma hora
            if(events[k][1] == events[j][1]):
                events.remove(events[k])
            #e acaba antes
            elif(events[k][1] < events[j][1]):
                events.remove(events[k])
            #e acaba depois
            elif(events[k][1] > events[j][1]):
                events.remove(events[j])
        #K começa antes e coincide
        elif((events[k][0] < events[j][0]) and (events[j][0] < events[k][1])):
            #e acaba à mesma hora
            if(events[k][1] == events[j][1]):
                events.remove(events[j])
            #e acaba depois
            elif(events[k][1] > events[j][1]):
                events.remove(events[j])
            #e J acaba depois
            elif(events[j][1] > events[k][1]):
                events[k][1]=events[j][1]
                events.remove(events[j])
            # acaba antes
            else:
                k+=1
                j+=1
        #K começa depois e coincide
        elif((events[k][0] > events[j][0]) and (events[k][0] < events[j][1])):
            #e acaba à mesma hora
            if(events[k][1] == events[j][1]):
                events.remove(events[k])
            #e acaba antes
            elif(events[k][1] < events[j][1]):
                events.remove(events[k])
            #e acaba depois
            elif(events[k][0] < events[j][0]):
                events[j][1] = events[k][1]
                events.remove(events[k])
        else:
            k+=1
            j+=1

        if(j>=len(events)):
            break

    if debugOn:
        print("Depois ",events)
    return events

@find_timeslot.subcommand()
async def calculate(interaction: nextcord.Interaction,
    timeslot: str = SlashOption(
        name="timeslot",
        description="Choose duration!",),
    ):
    """Find common timeslot

    Parameters
    ----------
    interaction: Interaction
        The interaction object
    timeslot: str
        Duration in minutes or list of durations
    """
    running=True

    key=str(interaction.user.id)
    if key not in IncludedUsers:
        await interaction.response.send_message(f"No users selected :cry:", ephemeral=True)
        return

    await interaction.response.defer()
    
    # users = [user.id for user in interaction.guild.humans if role in user.roles]

    week = {}

    
    print("Calculating")

    today = date.today()
    for d in range(0,6):
        week[today.strftime("%Y-%m-%d")] = []
        today += timedelta(days=1)

    for user in IncludedUsers[key]:
        success = await getcalendars(interaction.guild_id, user.id)
        print("For user ",user.name)
        if(len(success)==0):
            continue
        for url in success:
            cal = CalendarParser(ics_url=url)
            cal.sort_by_latest(sort_in_place=True)
            for event in cal.parse_calendar():
                #print("Evento: ",event["name"],event["start_time"],event["end_time"])

                key = str(event["start_time"]).split(" ")[0]
                if key in week:
                    week[key].append([event["start_time"], event["end_time"]])
                else:
                    week[key] = [[event["start_time"], event["end_time"]]]

    msgs=[]

    for duration in timeslot.split(","):
        msg = nextcord.Embed(title="Compatible timeslots", description="Available timeslots between everyone to schedule a meeting of x minutes")
        # print(duration, " mins")
        msg.add_field(name="----------------------------------",value="___**%s mins**___"%(duration),inline=False)
        for day, events in week.items():
            if(len(events)==0):
                msg.add_field(name="Dia",value="%s"%(day),inline=False)
                msg.add_field(name=">    Slot 0",value=">  %s"%(str(working_hours)),inline=True)
                continue

            events = unscramble_events(events)

            free = free_time(events,working_hours,int(duration))
            msg.add_field(name="Dia",value="%s"%(day),inline=False)
            for s in range(0,len(free)):
                msg.add_field(name=">    Slot %d"%(s+1),value=">  %s"%(str(free[s])),inline=True)
        msgs.append(msg)

    IncludedUsers[str(interaction.user.id)].clear()

    for x in range(1,len(msgs)):
        #bot.get_guild(interaction.guild_id).get_channel(interaction.channel_id).send(embed=msgs[x])
        await interaction.channel.send(embed=msgs[x])

    running=False

    await interaction.followup.send(embed=msgs[0])

timeslot_options = ["15","30","60","15,30","30,60"]

running = False

@calculate.on_autocomplete("timeslot")
async def timeslot(interaction: Interaction, timeslot: str):
    await interaction.response.send_autocomplete(timeslot_options)

def _fix_timezone(datetime_obj, time_zone):
    """\
    Adjusts time relative to the calendar's timezone,
    then removes the datetime object's timezone property.
    """
    if type(datetime_obj) is datetime and datetime_obj.tzinfo is not None:
        return datetime_obj.astimezone(time_zone).replace(tzinfo=None)

    elif type(datetime_obj) is date:
        return datetime(datetime_obj.year, datetime_obj.month, datetime_obj.day)
    
    return datetime_obj

def _multi_replace(string, replace_dict):
    "Replaces multiple items in a string, where replace_dict consists of {value_to_be_removed: replced_by, etc...}"
    for key, value in replace_dict.items():
        string = string.replace(str(key), str(value))
    return string

def _normalize(data_string, convert_whitespace=False):
    "Removes various markup artifacts and returns a normal python string."
    new_string = unescape(data_string)
    new_string = _multi_replace(new_string, {
        '&nbsp;': ' ', '&quot;': '"', '&brvbar;': '|', "&#39;": "'", "\\": ""
    })
    new_string = new_string.strip()

    if convert_whitespace:
        return " ".join(new_string.split())
        
    return new_string

class CalendarEvent(dict):
    """
    A modified dictionary that allows accessing and modifying the main properties of a calendar event
    as both attributes, and dictionary keys; i.e. 'event["name"]' is the same as using 'event.name'
    Only the following event-specific properties may be accessed/modified as attributes:
    "name", "description", "location", "start_time", "end_time", "all_day",
    "repeats", "repeat_freq", "repeat_day", "repeat_month", "repeat_until"
    CalendarEvents may also be compared using the >, >=, <, <=, comparison operators, which compare
    the starting times of the events.
    """
    __slots__ = ( "name", "description", "location", "start_time", "end_time", "all_day",
                  "repeats", "repeat_freq", "repeat_day", "repeat_month", "repeat_until" )
    
    def __getattr__(self, key):
        if key in self.__slots__:
            return self[key]
        else:
            return dict.__getattribute__(self, key)
        
    def __setattr__(self, key, value):
        if key in self.__slots__:
            self[key] = value
        else:
            raise AttributeError("dict attributes are not modifiable.")
        
    def __lt__(self, other):
        assert type(other) is CalendarEvent, "Both objects must be CalendarEvents to compare."
        return self["start_time"] < other["start_time"]
    
    def __le__(self, other):
        assert type(other) is CalendarEvent, "Both objects must be CalendarEvents to compare."
        return self["start_time"] <= other["start_time"]

    def __gt__(self, other):
        assert type(other) is CalendarEvent, "Both objects must be CalendarEvents to compare."
        return self["start_time"] > other["start_time"]

    def __ge__(self, other):
        assert type(other) is CalendarEvent, "Both objects must be CalendarEvents to compare."
        return self["start_time"] >= other["start_time"]

possible_days = {
    "MO":0,
    "TU":1,
    "WE":2,
    "TH":3,
    "FR":4,
    "SA":5,
    "SU":6
}

def copia_evento(event_dict: CalendarEvent, delta: int):
    novo = CalendarEvent()
    novo["name"]=event_dict["name"]
    novo["start_time"]=event_dict["start_time"]+timedelta(days=delta)
    novo["end_time"]=event_dict["end_time"]+timedelta(days=delta)
    return novo
    

class CalendarParser(object):
    def __init__(self, ics_url=None):
        self.ics_url = ics_url
        self.time_zone = None
        self.calendar = None
        self.title = ""
        self.subtitle = ""
        self.author = ""
        self.email = ""
        self.last_updated = None
        self.date_published = None
        self.events = []

    def __len__(self):
        return len(self.events)

    def __iter__(self):
        return self.events.__iter__()

    def __reversed__(self):
        return reversed(self.events)

    def __contains__(self, item):
        if type(item) is not str:
            return item in self.events
        
        for event in self.events:
            if event["name"].lower() == item.lower():
                return True
            
        return False

    def __getitem__(self, item):
        if type(item) is str:
            event_list = []
            for event in self.events:
                if event["name"].lower() == item.lower():
                    event_list.append(event)
                
            if len(event_list) == 0:
                raise LookupError("'%s' is not an event in this calendar." % (item))
            if len(event_list) == 1:
                return event_list[0]
            else:
                return event_list
        else:
            return self.events[item]


    def keys(self):
        "Returns the names of all the parsed events, which may be used as lookup-keys on the parser object."
        return [event["name"] for event in self.events]


    def sort_by_latest(self, sort_in_place=False):
        "Returns a list of the parsed events, where the newest events are listed first."
        sorted_events = sorted(self.events, reverse=True)
        if sort_in_place:
            self.events = sorted_events
        return sorted_events

    def sort_by_oldest(self, sort_in_place=False):
        "Returns a list of the parsed events, where the oldest events are listed first."
        sorted_events = sorted(self.events)
        if sort_in_place:
            self.events = sorted_events
        return sorted_events


    def fetch_calendar(self, force_xml=False, force_ics=False):
        "Fetches the calendar data from an XML/.ics resource in preperation for parsing."
        cal_data = None
        if self.ics_url:
            cal_data = urlopen(self.ics_url)
        else:
            raise UnboundLocalError("No calendar url or file path has been set.")

        cal_str = cal_data.read()
        cal_data.close()

        self.calendar = Calendar.from_ical(cal_str)

        return self.calendar

                
    def parse_ics(self, overwrite_events=True):
        "Returns a generator of Event dictionaries from an iCal (.ics) file."
        assert self.ics_url, "No ics resource has been set."

        # Returns an icalendar.Calendar object.
        self.fetch_calendar(force_ics=True)

        self.time_zone = timezone(str(self.calendar["x-wr-timezone"]))
        self.title = str(self.calendar["x-wr-calname"])

        if overwrite_events:
            self.events = []

        today = datetime.now()

        for event in self.calendar.walk():
            if isinstance(event, Event):
                event_dict = CalendarEvent()
                if "SUMMARY" in event:
                    event_dict["name"] = _normalize(event["summary"])
                if "DESCRIPTION" in event:
                    event_dict["description"] = _normalize(event["description"])
                if "LOCATION" in event and event["location"]:
                    event_dict["location"] = _normalize(event["location"])
                if "DTSTART" in event:
                    event_dict["start_time"] = _fix_timezone(event["dtstart"].dt, self.time_zone)
                if "DTEND" in event:
                    event_dict["end_time"] = _fix_timezone(event["dtend"].dt, self.time_zone)
                else:
                    continue
                if event_dict["start_time"].hour == 0 \
                and event_dict["start_time"].minute == 0 \
                and (event_dict["end_time"] - event_dict["start_time"]) == timedelta(days=1):
                    event_dict["all_day"] = True
                else:
                    event_dict["all_day"] = False
                
                daily = False

                event_dict["repeats"] = False
                if "RRULE" in event:
                    rep_dict = event["RRULE"]

                    event_dict["repeats"] = True
                    event_dict["repeat_freq"] = rep_dict["FREQ"][0]

                    if event_dict["repeat_freq"] == "YEARLY":
                        event_dict["repeat_day"] = event_dict["start_time"].day
                        event_dict["repeat_month"] = event_dict["start_time"].month

                    if "BYDAY" in rep_dict:
                        daily = True
                        event_dict["repeat_day"] = rep_dict["BYDAY"][0]
                    elif "BYMONTHDAY" in rep_dict:
                        event_dict["repeat_day"] = rep_dict["BYMONTHDAY"][0]

                    if "BYMONTH" in rep_dict:
                        event_dict["repeat_month"] = rep_dict["BYMONTH"][0]

                    if "UNTIL" in rep_dict:
                        event_dict["repeat_until"] = _fix_timezone(rep_dict["UNTIL"][0], self.time_zone)
                        if(event_dict["repeat_until"]<today):
                            continue

                #Ver se interessa
                ev_date = event_dict["start_time"]
                repete = event_dict["repeats"]

                if debugOn:
                    print(event_dict["name"],ev_date,event_dict["end_time"],"Repete->",repete)
                

                if(repete):
                    if debugOn:
                        print("Vamos pôr no dia certo")
                    
                    while(today.isocalendar()[1] != event_dict["start_time"].isocalendar()[1]):
                        event_dict["start_time"] += timedelta(weeks=1)
                        event_dict["end_time"] += timedelta(weeks=1)

                    if debugOn:
                        print(event_dict["name"],event_dict["start_time"],event_dict["end_time"],"Repete->",repete)

                    if(daily):
                        for day in range(1,len(rep_dict["BYDAY"])):
                            delta = possible_days[rep_dict["BYDAY"][day]]-possible_days[rep_dict["BYDAY"][0]]
                            copia = copia_evento(event_dict, delta)
                            if debugOn:
                                print(event_dict["name"],event_dict["start_time"],event_dict["end_time"],"Repete->",repete)
                            #self.events.append(copia)
                            yield copia
                else:
                    #Ver se já passou e nao se repete
                    if(ev_date < today):
                        print("passou")
                        continue
                    #Mesmo ano
                    same_year = ev_date.isocalendar()[0] == today.isocalendar()[0]
                    if(not same_year):
                        continue

                    #Quantas semanas de diferença
                    in_weeks = ev_date - today
                    print(in_weeks)
                    if(in_weeks > timedelta(weeks=1)):
                        print("too far")
                        continue

                #if overwrite_events:
                    #self.events.append(event_dict)

                yield event_dict


    def parse_calendar(self, force_list=False, overwrite_events=True):
        "Parses the calendar at the specified resource path.  Returns a generator of CalendarEvents."
        
        generator = self.parse_ics(overwrite_events)
            
        if force_list:
            return [event for event in generator]
        else:
            return generator

@ntask.loop(minutes=10)
async def clear_users():
    if((len(IncludedUsers)!=0) and (not running)):
        IncludedUsers.clear()
        print("Clearing")

bot.run(os.getenv("BOT_TOKEN"))