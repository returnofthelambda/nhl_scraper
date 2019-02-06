def game_scrape(season, game_id):
    '''take game# and season and use that to pull json from web
    likely will split this off into it's own function and then move the parsing into a
    separate function.
    
    returns 3 dataframes.'''

    from pandas.io.json import json_normalize
    import urllib.request, json

    game_url = 'http://statsapi.web.nhl.com/api/v1/game/'+season+game_id+'/feed/live'
    with urllib.request.urlopen(game_url) as url:
        data = json.loads(url.read().decode())

    all_plays=data['liveData']['plays']['allPlays']

    for play_num in range(len(all_plays)):
        for key in list(all_plays[play_num].keys()):
            if (type(all_plays[play_num][key])==list):
                for i in range(len(all_plays[play_num][key])):
                    all_plays[play_num][key+'.'+str(i)]=all_plays[play_num][key][i]
                del all_plays[play_num][key]

    play_data=json_normalize(all_plays)
    play_data['game_id']=game_id
    play_data['season']=season

    skaters_df, goalies_df=players_scrape(data['liveData']['boxscore']['teams'])
    skaters_df['game_id']=game_id
    goalies_df['game_id']=game_id
    return play_data, skaters_df, goalies_df

def players_scrape(players_json):
    '''take the data['liveData']['boxscore']['teams'] json string and parse game data for each
    player.'''

    import pandas as pd

    tmp_dict={}
    '''have to leave the next two variables in its casing'''
    tmp_dict['goalieStats']={}
    tmp_dict['skaterStats']={}
    for team in ['home','away']:
        players=list(players_json[team]['players'].keys())
        tmp_stats=players_json[team]['players']
        for p in players:
            for player_type in ['skaterStats','goalieStats']:
                if player_type in tmp_stats[p]['stats']:
                    tmp_dict[player_type].update({p[2:] : tmp_stats[p]['stats'][player_type]})

    skaters_df=pd.DataFrame(tmp_dict['skaterStats'])
    skaters_df.index.name='skater_id'
    goalies_df=pd.DataFrame(tmp_dict['goalieStats'])
    goalies_df.index.name='goalie_id'

    return skaters_df.T, goalies_df.T


def season_scrape(season):
    '''import all games for a season. if a season is completed, include playoff games.
    at end of import, create new column that takes gameId and use to create a column to note
    regular / playoffs.

    add ability to test if current season and what the next game number is, and ability to
    run thru regular season and playoffs'''


    import urllib.request, json
    import pandas as pd


    '''include test for whether season exists in database. must be prior to 2017 (though there's
    probably a better way to test for current season) and 1917 or after. 

    '''


    max_games = 1271 if int(season) > 2016 else 30
    for i in range(max_games):
        game_id = "02" + "%04d" % int(i+1)
        try:
            urllib.request.urlopen('http://statsapi.web.nhl.com/api/v1/game/'+str(season)+game_id+'/feed/live')
        except:
            print("unable to find: " + str(season) + "" + str(game_id))
            continue
        print("scraping game " + str(season) + "" + str(game_id))
        play_df_tmp, skaters_tmp, goalies_tmp = game_scrape(str(season),game_id)
        if 'play_df' in locals():
            play_df = play_df.append(play_df_tmp,ignore_index=True)
            skaters_df = skaters_df.append(skaters_tmp,ignore_index=True)
            goalies_df = goalies_df.append(goalies_tmp,ignore_index=True)
        else:
            play_df = play_df_tmp
            skaters_df = skaters_tmp
            goalies_df = goalies_tmp

    removal = ['Game Scheduled', 'Period Ready', 'Shootout Complete', 'Period Official', 'Game Official']
    play_df=play_df.loc[~play_df['result.event'].isin(removal)]
    play_df.drop(['about.periodTimeRemaining','about.ordinalNum','team.link','team.name','team.triCode'],axis=1,inplace=True)


    return play_df, skaters_df, goalies_df
