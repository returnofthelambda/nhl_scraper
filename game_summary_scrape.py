import os
from datetime import datetime
from urllib.request import urlopen, HTTPError
import numpy as np
from bs4 import BeautifulSoup
import pandas as pd


def summary_scrape(season, gameId, subSeason='02', *raw_html):
    """
    Script that scrapes goals scored data from NHL Game Summary pages. Requires
    4 digit season (eg 2018 for the 2018-19 season), 4 digit gameId and 2 digit
    sub season (01 preseason, 02 regular, 03 playoffs).

    """

    meta = {}
    if len(str(season)) == 4:
        meta['Season'] = str(season) + str(int(season) + 1)
    else:
        meta['Season'] = str(season)

    if ~('raw_html' in locals()):
        meta['gameId'] = str(subSeason).zfill(2) + str(gameId).zfill(4)
        url = 'http://www.nhl.com/scores/htmlreports/' + meta['Season'] +\
            '/GS' + meta['gameId'] + '.HTM'
        # url='http://www.nhl.com/scores/htmlreports/20132014/GS020001.HTM'

    try:
        raw_html = urlopen(url)
    except HTTPError:
        return pd.DataFrame(['Game not found.'], columns=['Err']),\
            pd.DataFrame(), None

    bs_obj = BeautifulSoup(raw_html.read().decode('utf-8'), 'html.parser')
    tds = bs_obj.find_all('td')
    meta = meta_clean(meta, tds)

    return bs_obj, meta, tds


def meta_clean(meta, tds):
    '''
    returns the meta data from the game being scraped.
    '''
    times = tds[15].text.split('\xa0')

    try:
        meta['End'] = pd.to_datetime(times[3]).strftime('%H:%M')
    except IndexError:
        return pd.DataFrame(['Game in progress.'], columns=['Err'])

    meta['Date'] = pd.to_datetime(tds[13].text).strftime('%Y-%m-%d'),
    meta['Start'] = pd.to_datetime(times[1]).strftime('%H:%M')
    # list of team abbrevs, visitor first
    meta['Visitor'] = str(tds[37].text)[:3]
    meta['Home'] = str(tds[38].text)[:3]

    return meta


def goalie_info(bs_obj):
    # find goalie info and use it to extract goalie numbers
    goalie_info = bs_obj.find('td', {'valign': 'middle'}).find_parent('tr')\
        .find_next_siblings('tr')
    team = 'Visitor'
    goalies = {'Visitor': [], 'Home': []}
    for line in goalie_info:
        for val in line.find('td'):
            if val.isnumeric():
                goalies[team].append(val)
            if val[:2] == 'TE':
                team = 'Home'
    return goalies


def penalty_shot(goals_df, meta):
    if 'csv' not in os.listdir():
        os.mkdir('csv')
    ps_file = 'failed_ps_' + meta['Season'] + '.csv'
    if ps_file in os.listdir('csv/'):
        p_df = pd.read_csv('csv/' + ps_file, dtype={'gameId': 'str'})
        p_df = pd.concat([p_df, goals_df[goals_df[
            'Assist.1'] == 'Unsuccessful Penalty Shot'].drop([
                'Visitor_On_Ice', 'Home_On_Ice'], axis=1)], sort=False)\
            .drop_duplicates()
    else:
        p_df = goals_df[goals_df['Assist.1'] == 'Unsuccessful Penalty Shot']\
            .drop(['Visitor_On_Ice', 'Home_On_Ice'], axis=1)
    p_df.set_index(['Season', 'gameId']).to_csv('csv/' + ps_file, index=True)
    return None


def goals_clean(bs_obj, meta, tds):
    '''
    This script returns a dataframe that contains all information in the Goal
    Summary section and augments it with a few extra bits of info:
        #1: Whether or not the home or away goalies were on the ice. Instead of
        cross checking a separate database, the test is done from the data
        provided on the Game Summary Page. Test can handle any amount of
        goalies (typically 2 per team).
        #2: Which team the goal was scored against.
        #3: How that goal impacted the score, from the pesrpective of the
        scoring team. This is to make it easier suss out what 3rd period goals
            without a goalie on the ice are the result of gambling for an extra
        attacker vs how many of those goals are from delayed penalties.
    '''

    goalies = goalie_info(bs_obj)

    goals = [val.text.strip() for val in tds[28].find_all('td')[10:]]

    '''
    Penalty shots are formatted differently than any other goal, this
    function adds an extra blank to make the goal information lines
    consistent throughout
    '''
    PS = ['Penalty Shot', 'Unsuccessful Penalty Shot']
    if any(i in PS for i in goals) > 0:
        for pos in [i for i in range(len(goals)) if goals[i] in PS]:
            goals.insert(pos+1, '')

    if '-PS' in goals:
        goals.append('')
    # return goals

    cols = ['G', 'Per', 'Time', 'Str', 'Team', 'Scorer', 'Assist.1',
            'Assist.2', 'Visitor_On_Ice', 'Home_On_Ice']
    goals_df = pd.DataFrame(np.array(goals).reshape(len(goals)//10, 10),
                            columns=cols)
    '''
    strip out numbers that are included with players names to denote season
    total of Goals / Assists
    '''
    for col in cols[5:8]:
        goals_df[col] = goals_df[col].str.replace(r'\(\d+\)|\d+',
                                                  '').str.strip()

    goals_df['Season'], goals_df['gameId'] = [meta['Season'], meta['gameId']]
    if any(goals_df['Assist.1'].str.contains('Unsuccessful Penalty Shot')):
        penalty_shot(goals_df, meta)
    # drop rows that contain unsuccessful penalty shots because we only
    # want actual goals
    goals_df = goals_df[goals_df['Assist.1'] != 'Unsuccessful Penalty Shot']

    for team in ['Visitor', 'Home']:
        goals_df[team + '_Goalie_On_Ice'] = goals_df[team + '_On_Ice']\
            .apply(lambda x: any(str(g) in x for g in goalies[team])
                   if x is not None else True)
        goals_df[team + '_Score'] = np.cumsum([1 if val == meta[team] else
                                               0 for val in goals_df['Team']])

    goals_df['Difference'] = [val - goals_df.iloc[_]['Visitor_Score']
                              if goals_df.iloc[_]['Team'] == meta['Home']
                              else goals_df.iloc[_]['Visitor_Score'] - val
                              for _, val in enumerate(goals_df.Home_Score)]

    # coerce errors since SO goals don't occur at a time
    goals_df['Time'] = pd.to_datetime(goals_df.Time, format='%M:%S',
                                      errors='coerce').dt.time

    return goals_df.set_index(['Season', 'gameId'])


def missing_game(game_id, failed):
    '''
    Function for handling increment after reaching a missing game
    game_id is a string
    '''
    print('Unable to find:', game_id)
    if int(game_id[-4:]) == failed + 1:
        if (game_id[6] == '3') & (int(game_id[8]) < 5):
            # 2018-2019 playoffs count handling
            # increment to next hundreds place
            count = (int(game_id[-4:]/100)+1) * 100 + 11
            return count, count - 1
        else:
            return None,
    else:
        if game_id[:2] == '03':
            if game_id[-4:] < 111:
                count = 110
            else:
                # increment to next tens place
                count = (int(game_id[-4:]/10) + 1) * 10
            return count + 1, count


def season_summary_scrape(season, start=1, subSeason='02', *autosave):
    """
    User provides season number and optionally the starting game, and returns a
    dataframe of summary data for all games from start to final game of the
    season. Start defaults to 0 if no input is provided by the user.
    The reason I set the loop to not break until two consecutive games are
    empty is because if a game is postponed for any reason (weather, etc) the
    NHL keeps that gameId number for the postponed game, and often those games
    are made up at the end of the season. If two consecutive games are ever
    postponed (and I'm sure at some point that will happen) I will have to
    revisit how to handle this.
    """

    while not isinstance(autosave, bool):
        text = input('Would you like to save to csv (Y/n)? ')
        if text[0].upper() == 'Y':
            autosave = True
        elif text[0].upper() == 'N':
            autosave = False
        else:
            print('Please enter Y/n.')

    if len(str(season)) == 4:
        season = str(season) + str(int(season) + 1)

    failed = -1
    skipped = []
    season_gs_df, season_gs_meta_df = pd.DataFrame(), pd.DataFrame()
    i = int(start)
    while True:
        # gameId = '%04d' % i
        game_id = str(subSeason).zfill(2) + '%04d' % i
        bs_obj, meta, tds = summary_scrape(str(season), game_id[2:], subSeason)
        if tds is None:
            i, failed = missing_game(season[:4]+str(subSeason)+str(game_id),
                                     failed)
            if i is None:
                break
            else:
                continue
        else:
            print('Scraping game ' + str(season[:4]) + game_id)
            meta_df = pd.DataFrame(meta)

            if meta_df.columns[0] == 'Err':
                print(meta_df.Err.iloc[0])
                skipped.append([season, game_id, 'In Progress / Missing',
                                datetime.fromtimestamp(datetime.timestamp(
                                    datetime.now())).strftime(
                                        '%Y-%m-%d %H:%M:%S')])
                i += 1
                continue
            else:
                meta_df.set_index(['Season', 'gameId'], inplace=True)
                goals_df = goals_clean(bs_obj, meta, tds)


            season_gs_df = season_gs_df.append(goals_df, ignore_index=False)
            season_gs_meta_df = season_gs_meta_df.append(meta_df,
                                                         ignore_index=False)
            i += 1
    if (len(skipped) > 2) & autosave:
        pd.DataFrame(skipped[:-2], columns=['Season', 'gameId', 'Reason',
                                            'Time Failed']).to_csv(
                                                'skipped_' + str(season) +
                                                '.csv', index=False)
    if autosave:
        season_gs_df.to_csv('ss_' + str(season) + '.csv', index=True)
        season_gs_meta_df.to_csv('ss_' + str(season) + '_meta.csv',
                                 index=True)

    return season_gs_df, season_gs_meta_df

def ss_df_import(season=2008):
    df, dfm = pd.DataFrame(), pd.DataFrame()

    for szn in range(season, 2019):
        df = df.append(pd.read_csv('csv\ss_' + str(szn) + str(szn + 1) +
                                   '.csv', dtype={'gameId': 'str'
                                                  }).set_index(['Season',
                                                                'gameId']),
                       sort=False)
        dfm = dfm.append(pd.read_csv('csv\ss_' + str(szn) + str(szn + 1) +
                                     '_meta.csv', dtype={'gameId': 'str'})
                         .set_index(['Season', 'gameId']), sort=False)

    return df, dfm

def sss1(season,start=1,subSeason='02',*autosave):
    """
    Update, 2020-11-01: not currently working for a full season. Use
    season_summary_scrape listed above.

    Function that is similar to the season_summary_scrape function above, but
    replaces loops with recursive functions.
    """

    def autosave_check():
        text = input('Would you like to save to csv (Y/n)? ')[0]
        if (text.upper()=='Y') | (text.upper()=='N'):
            return text.upper() == 'Y'
        else:
            print('Please enter Y/n.')
            return autosave_check()

    autosave = autosave_check()

    gId = str(season) + str(int(season) + 1) + str(subSeason).zfill(2) +\
        str(start).zfill(4) if len(str(season)) == 4 else str(season) +\
        str(subSeason).zfill(2) + str(start).zfill(4)

    print(gId)
    def gss(gId,gs_df,gs_meta_df,skipped,failed):
        try:
            raw_html = urlopen('http://www.nhl.com/scores/htmlreports/' +
                               gId[:8] + '/GS' + gId[-6:] + '.HTM')
        except:
            print('Unable to find: ' + str(gId)[:4] + str(gId)[-6:])
            if gId == str(int(failed) + 1):
                if (skipped.shape[0] > 2) & (autosave):
                    skipped.columns = ['Season', 'gameId', 'Reason',
                                       'Time Failed']
                    skipped.to_csv('skipped_' + gId[:8] + '.csv', index=False)
                return gs_df, gs_meta_df
            else:
                return gss(str(int(gId) + 1), gs_df, gs_meta_df,
                           skipped.append(pd.DataFrame(
                               [gId[:8], gId[-6:],'DNE',
                                datetime.fromtimestamp(datetime.timestamp(
                                    datetime.now())).strftime(
                                        '%Y-%m-%d %H:%M:%S')]).T), gId)
        print('Scraping game ' + gId[:4] + gId[8:])

        df_tmp, game_meta = summary_scrape(gId[:4], gId[-4:], gId[8:10],
                                         raw_html)
        if df_tmp.columns[0] == 'Err':
            print(df_tmp.Err.iloc[0])
            if gId == str(int(failed) + 1):
                return gs_df, gs_meta_df
            else:
                return gss(str(int(gId) + 1), gs_df, gs_meta_df,
                           skipped.append(pd.DataFrame(
                               [gId[:8], gId[8:], 'In Progress',
                                datetime.fromtimestamp(datetime.timestamp(
                                    datetime.now())).strftime(
                                        '%Y-%m-%d %H:%M:%S')]).T), gId)
        else:
            return gss(str(int(gId) + 1), gs_df.append(df_tmp,
                                                       ignore_index=False),
                       gs_meta_df.append(game_meta, ignore_index=False), skipped,
                       failed)

    season_gs_df, season_gs_meta_df = gss(gId, pd.DataFrame(), pd.DataFrame(),
                                          pd.DataFrame(), 0)

    if autosave:
        season_gs_df.to_csv('ss_' + str(gId)[:8] + '.csv', index=True)
        season_gs_meta_df.to_csv('ss_' + str(gId)[:8] + '_meta.csv',
                                 index=True)

    return season_gs_df, season_gs_meta_df
