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
  
    
      HOW TO DEPLOY?
      
      - Create a Discord Bot
      - In ".env" file, add the bot token string to the value corresponding to BOT_TOKEN key
      - Run the Python file with:
        python main.py
      - Add the bot to your Discord server with permission to read messages and slash commands.
      - Use the slash commands
