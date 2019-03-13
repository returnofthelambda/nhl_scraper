# nhl_scraper
Scrape nhl shift, pbp, and boxscore data from nhl api.

After searching for information on goals scored with an extra attacker (whether because of a delayed penalty or late game situation) what I found was the data didn't easily exist. From what I saw, the NHL API doesn't handle this either, but there is Goal On-Ice data on the Game Summary sheet that the NHL produces during and after every game. The Game Summary Scraper script pulls that data, and checks to see if each team had a goalie on the ice during the goal (by cross-referencing the goalie detail on the GS sheet). The function returns a dataframe with all goal related data, the goalie on/off boolean for each team, and the effect of the score. A subsequent function in the GSS.py file runs a few pandas dataframe filters to parse out 1) all extra attacker goals and 2) a majority of the delayed penalty goals. For DP goals, I used the assumptions that any goal scored with an extra attacker in the first 2 Periods or Overtime + goals scored in the first 10 minutes of the 3rd Period + goals scored in the final 10 minutes of the 3rd Period that put the team up by at least 1 goal. These delayed penalty assumptions will have false positives if a team is down by enough goals that they pulled their goalie in the first 10 of the 3rd  OR if it is a late season situation and a team needs a regulation / overtime win to get into the playoffs and chooses to pull their goalie in the final 10 minutes / overtime of a tied game. The conditions will yield false negatives if a team that is trailing scores a goal in the final 10 minutes of the 3rd while on a delayed penalty. 

Future considerations to improving false negatives / positives: scan game recaps from sports sites to check for the phrase (which could lead to false positives if a team scores a delayed penalty goal early in the game and pulls their goalie again in the last 10 of the third). In developing this, I did check ~20 game recaps from multiple sports sites, but none consistently noted whether an extra attacker goal was scored via Delayed Penalty or due to desperation.
