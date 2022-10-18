# taskmaster


      _________   _____ __ __ __  ______   _____________________ 
     /_  __/   | / ___// //_//  |/  /   | / ___/_  __/ ____/ __ \
      / / / /| | \__ \/ ,<  / /|_/ / /| | \__ \ / / / __/ / /_/ /
     / / / ___ |___/ / /| |/ /  / / ___ |___/ // / / /___/ _, _/ 
    /_/ /_/  |_/____/_/ |_/_/  /_/_/  |_/____//_/ /_____/_/ |_|  
                                                             
- What is it?
  
  A Discord Bot to find a common timeslot between pairs.
  
- Why I made it?
 
  As a student working with multiple people on projects and with a internship on top, scheduling a meeting beacme very difficult because everyone had a different agenda.
  On top of that, others had their internship as well so we couldn't just have a common Google Calendar or something, because we had multiple calendars.
  So I needed to find a way to get a common timeslot that everyone could attend.
  
- How does it work?

  People add their calendars (more on that later). Then choose the people who will attend the meeting and the time it will take, for example: Pedro, Nuno and José are in for a 30 min meeting.
  Then choose calculate and Taskmaster will get the calendars and find a timeslot in the current week.
  
Ready to start using it?
    
      HOW TO DEPLOY?
      
      - Create a Discord Bot
      - In ".env" file, add the bot token string to the value corresponding to BOT_TOKEN key
      - Run the Python file with:
        python main.py
      - Add the bot to your Discord server with permission to read messages and slash commands.
      - Use the slash commands
      
So now you have the bot running
      

      HOW TO USE?
      
      - First add as many calendars as you want with the command:
      /new_calendar
      * Note that the calendar has to be in the .ical format and be public. As matter the fact, the calendar doesn't need to be publicly available, but public for people with a link. In the case of Google Calendar you have a secret ical address you can use.
      
      - Then, when everyone has added their calendar you need to include them in a calculation with the command:
      /find_timeslot users add
      
      - Now you just have to tell Taskmaster to begin the calculation with the command:
      /find_timeslot users calculate
      
      AND DONE!
