def game_scrape(game_id, season):
    '''take game# and season and use that to pull json from web
    likely will split this off into it's own function and then move the parsing into a
    separate function.'''

    from pandas.io.json import json_normalize
    import urllib.request, json

    game_url = 'http://statsapi.web.nhl.com/api/v1/game/'+season+game_id+'/feed/live'
    with urllib.request.urlopen(game_url) as url:
        data = json.loads(url.read().decode())

    all_plays=data['liveData']['plays']['allPlays']
    play_data=json_normalize(all_plays) # need to flatten out the json string
    play_data['gameId']=game_id
    play_data['season']=season
    
    skaters, goalies=players_scrape(data['liveData']['boxscore']['teams'])
    skaters['game_id']=game_id
    goalies['game_id']=game_id
    return play_data, skaters, goalies

def players_scrape(players_json):
    '''take the data['liveData']['boxscore']['teams'] json string and parse game data for each
    player.'''

    import pandas as pd
    
    tmp_dict={}
    tmp_dict['goalieStats']={}
    tmp_dict['skaterStats']={}
    for team in ['home','away']:
        players=list(players_json[team]['players'].keys())
        tmp_stats=players_json[team]['players']
        for p in players:
            for playerType in ['skaterStats','goalieStats']:
                if playerType in tmp_stats[p]['stats']:
                    tmp_dict[playerType].update({p[2:] : tmp_stats[p]['stats'][playerType]})
    
    skaters_df=pd.DataFrame(tmp_dict['skaterStats']).T
    goalies_df=pd.DataFrame(tmp_dict['goalieStats']).T

    return skaters_df, goalies_df
