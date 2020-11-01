import os
from datetime import datetime
from urllib.request import urlopen
from numpy import cumsum
from bs4 import BeautifulSoup
import pandas as pd


def summary_scrape(season,gameId,subSeason='02',*raw_html):
    """
    Script that scrapes goals scored data from NHL Game Summary pages. Requires
    4 digit season (eg 2018 for the 2018-19 season), 4 digit gameId and 2 digit
    sub season (01 preseason, 02 regular, 03 playoffs).

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
        """

    if len(str(season)) == 4:
        season = str(season) + str(int(season)+1)

    if ~('raw_html' in locals()):
        url = 'http://www.nhl.com/scores/htmlreports/' + season + '/GS' +\
            str(subSeason).zfill(2) + str(gameId).zfill(4) + '.HTM'
        # url='http://www.nhl.com/scores/htmlreports/20132014/GS020001.HTM'
        try:
            raw_html = urlopen(url)
        except:
            return pd.DataFrame(['Game not found.'], columns=['Err']),
        pd.DataFrame([])
        bs_obj = BeautifulSoup(raw_html.read().decode('utf-8'), 'html.parser')
        tds = bs_obj.find_all('td')

    for fin in range(len(tds)):
        if tds[fin].text == 'Final':
            break
        if fin == len(tds)-1:
            return pd.DataFrame(['Game in progress.'], columns=['Err']),

    pd.DataFrame([])
    date = pd.to_datetime(tds[fin-4].text).strftime('%Y-%m-%d')
    start_time = pd.to_datetime(tds[fin-2].text.split('\xa0')[1])\
        .strftime('%H:%M')
    goals = tds[fin+11]
    # list of team abbrevs, visitor first
    teams = {'Visitor': str(tds[fin+20].text)[:3],
             'Home': str(tds[fin+21].text)[:3]}

    tmp = [[], []]
    goalie_start = bs_obj.find('td', {'valign': 'middle'}).find_parent('tr')\
        .find_next_siblings('tr')
    j = 0
    for i in range(1, len(goalie_start)):
        res = goalie_start[i].find('td').text
        try:
            tmp[j].append(int(res))
        except:
            if res[:4] == 'TEAM':
                i += 3
                j = 1
                goalies = {'Visitor': tmp[0], 'Home': tmp[1]}
                # create empty list of lists for each row in Goal summary
                res = [[] for _ in range(1, len(goals.find_all('tr')))]

    for i in range(len(res)):
        for j in range(len(goals.find_all('tr')[i+1].find_all('td'))):
            val = goals.find_all('tr')[i+1].find_all('td')[j].text.strip()\
                .split(', ')
            if len(val) > 1:
                res[i].append(val)
            else:
                res[i].append(val[0])
                if val[0] == 'Penalty Shot':
                    res[i].append('')

    cols = ['G', 'Per', 'Time', 'Str', 'Team', 'Scorer', 'Assist.1',
            'Assist.2', 'Visitor_On_Ice', 'Home_On_Ice']
    df = pd.DataFrame(res, columns=cols)
    '''
    strip out numbers that are included with players names to denote season
    total of Goals / Assists
    '''
    for col in cols[5:8]:
        df[col] = df[col].str.replace(r'\(\d+\)|\d+', '').str.strip()

    df['Season'], df['gameId'] = [season[:4],
                                  str(str(subSeason) +
                                      str(gameId).zfill(4)).zfill(6)]
    if any(df['Assist.1'].str.contains('Unsuccessful Penalty Shot')):
        try:
            p_df = pd.read_csv('csv/failed_ps_' + str(int(season)) +
                               '.csv', dtype={'gameId': 'str'})
            p_df = pd.concat([p_df, df[df[
                'Assist.1'] == 'Unsuccessful Penalty Shot'].drop([
                    'Visitor_On_Ice', 'Home_On_Ice'], axis=1)], sort=False)\
                .drop_duplicates()
        except:
            os.mkdir('csv')
            p_df = df[df['Assist.1'] == 'Unsuccessful Penalty Shot']\
                .drop(['Visitor_On_Ice', 'Home_On_Ice'], axis=1)
        p_df.set_index(['Season', 'gameId']).to_csv('csv/failed_ps_' +
                                                    str(int(season)) +
                                                    '.csv', index=True)
    # drop rows that contain unsuccessful penalty shots
    df = df[df['Assist.1'] != 'Unsuccessful Penalty Shot']

    for team in ['Visitor', 'Home']:
        df[team + '_Goalie_On_Ice'] = df[team + '_On_Ice']\
            .apply(lambda x: any(str(g) in x for g in goalies[team])
                   if x is not None else True)
        df[team+'_Score'] = cumsum([1 if df.loc[ei, 'Team'] == teams[team]
                                    else 0 for ei in df.index])

    df['Difference'] = [df.Home_Score[ei] - df.Visitor_Score[ei]
                        if df.Team[ei] == teams['Home']
                        else df.Visitor_Score[ei] - df.Home_Score[ei]
                        for ei in df.index]

    # coerce errors since SO goals don't occur at a time
    df['Time'] = pd.to_datetime(df.Time, format='%M:%S',
                                errors='coerce').dt.time


    df_meta = pd.DataFrame([[season[:4], str(subSeason) +
                             str(gameId).zfill(4), date, start_time,
                             teams['Visitor'], teams['Home']]],
                           columns=['Season', 'gameId', 'Date', 'Start',
                                    'Visitor', 'Home'])

    return df.set_index(['Season', 'gameId']), df_meta.set_index(['Season',
                                                                  'gameId'])

def season_summary_scrape(season,start=1,subSeason='02',autosave=False):
    """
    Update, 2020-11-01: 2018-19 post season game numbering changed to groupings
    by series so series 1 was CBJ vs TB and it was number 0111. All games in
    that series start 011X. 2019-2020 playoffs went back to the normal 0001 for
    the first game of the playoffs. Will work to update this to handle the
    2018-2019 playoffs, but for no it's not functional for that post-season.

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

    failed = 0
    skipped = []
    season_gs_df, season_gs_meta_df = pd.DataFrame(), pd.DataFrame()
    i = int(start)
    while True:
        gameId = '%04d' % i
        try:
            raw_html = urlopen('http://www.nhl.com/scores/htmlreports/' +
                                str(season) + '/GS' +
                                str(subSeason).zfill(2) + gameId + '.HTM')
        except:
            skipped.append([season, str(subSeason) + str(gameId), 'DNE',
                            datetime.fromtimestamp(
                                datetime.timestamp(
                                    datetime.now())).strftime(
                                        '%Y-%m-%d %H:%M:%S')])
            print('Unable to find: ' + str(season[:4]) + str(subSeason) +
                  str(gameId))
            if i == failed + 1:
                break
            else:
                failed = i
                i += 1
                continue
        print('Scraping game ' + str(season[:4]) + str(subSeason) +
              str(gameId))

        with open('last_game', 'w') as f:
            f.write(str(season[:4]) + str(subSeason) + str(gameId))
            f.close()
        df_tmp, df_meta = summary_scrape(str(season), gameId, subSeason,
                                         raw_html)
        if df_tmp.columns[0] == 'Err':
            print(df_tmp.Err.iloc[0])
            skipped.append([season, str(subSeason) + str(gameId),
                            'In Progress / Missing',
                            datetime.fromtimestamp(datetime.timestamp(
                                datetime.now())).strftime(
                                    '%Y-%m-%d %H:%M:%S')])
            i += 1
            continue
        else:
            season_gs_df = season_gs_df.append(df_tmp, ignore_index=False)
            season_gs_meta_df = season_gs_meta_df.append(df_meta,
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
        with open('last_game', 'w') as f:
            f.write(str(gId[:4]) + str(gId[8:]))
            f.close()

        df_tmp, df_meta = summary_scrape(gId[:4], gId[-4:], gId[8:10],
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
                       gs_meta_df.append(df_meta, ignore_index=False), skipped,
                       failed)

    season_gs_df, season_gs_meta_df = gss(gId, pd.DataFrame(), pd.DataFrame(),
                                          pd.DataFrame(), 0)

    if autosave:
        season_gs_df.to_csv('ss_' + str(gId)[:8] + '.csv', index=True)
        season_gs_meta_df.to_csv('ss_' + str(gId)[:8] + '_meta.csv',
                                 index=True)

    return season_gs_df, season_gs_meta_df
