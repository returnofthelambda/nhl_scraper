def game_scrape(game_id, season):
    '''take game# and season and use that to pull json from web
    likely will split this off into it's own function and then move the parsing into a
    separate function.'''

    from pandas.io.json import json_normalize
    import urllib.request, json

    game_url = 'http://statsapi.web.nhl.com/api/v1/game/'+season+gameId+'/feed/live'
    with urllib.request.urlopen(gameUrl) as url:
        data = json.loads(url.read().decode())

    all_plays=data['liveData']['plays']['allPlays']
    play_data=json_normalize(all_plays) # need to flatten out the json string
    play_data['gameId']=game_id
    play_data['season']=season
    
    skaters, goalies=players_scrape(data['liveData']['boxscore']['teams'])
    skaters['game_id']=game_id
    goalies['game_id']=game_id
    return playData, skaters, goalies

def players_scrape(players):
    '''take the data['liveData']['boxscore']['teams'] json string and parse game data for each
    player.'''

    for team in ['home','away']:

        skaters=players[team]['skaters']
        goalies=players[team]['goalies']
        goalies_stats=[players[team]['players']['ID'+str(g)]['stats']['goalieStats'] for g in goalies]
        skaters_stats=[players[team]['players']['ID'+str(g)]['stats']['skaterStats'] for g in skaters]
        for i in range(len(skaters)):
            skaters_stats[i]['player_id']=s 
        for i in range(len(goalies):    
            goalies_stats[i]['player_id']=g
        

    return skaters_stats, goalies_stats
