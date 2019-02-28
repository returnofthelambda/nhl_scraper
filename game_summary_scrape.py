def summary_scrape(gameId,season):
    '''
    Script that scrapes goals scored data from NHL Game Summary pages. Requires full 6 digit gameId and 4 digit season (eg 2018 for the 2018-19 season). Eventually 6 digit code will be broken into a 2 digit code (01 preseason, 02 regular, 03 playoffs) and a 4 digit gameId. 

    This script returns a dataframe that contains all information in the Goal Summary section and augments it with a few extra bits of info:
        #1: Whether or not the home or away goalies were on the ice. Instead of cross checkinga separate database, the test is done from the data provided on the Game Summary Page. Test can handle any amount of goalies, though I believe there has never been an instance where a team had more than 2 goalies dressed in a game.
        #2: Who the goal was scored against.
        #3: How that goal impacted the score, from the pesrpective of the scoring team. This tidbit will allow me to easier suss out what 3rd period goals without a goalie on the ice are the result of gambling for an extra attacker and how many of those goals are from delayed penalties. Given the limitation of the data, this likely will not be 100% accurate as it's almost certain that at some point a team that was trailing has scored a late goal while on a delayed penalty.

    2019-02-10 Unresolved Issues:
        #1: Prior to 2014, Montreal Game Summary pages were written in English and in French, this throws an error as currently constructed.
    '''
    from bs4 import BeautifulSoup
    from urllib.request import urlopen
    import pandas as pd
    from numpy import cumsum

    season=str(season)+str(int(season)+1)

    url='http://www.nhl.com/scores/htmlreports/'+season+'/GS'+str(gameId)+'.HTM'
    raw_html = urlopen(url).read()
    bsObj=BeautifulSoup(raw_html,"html.parser")
    goals=bsObj.find_all("td")[28]

    #I don't think the visitor/home full names are necessary, but keep for now.
    #visitor=[str(bsObj.find_all("td")[37].text)[:3],bsObj.find_all("img")[0].get('alt','')]
    #home=[str(bsObj.find_all("td")[38].text)[:3],bsObj.find_all("img")[1].get('alt','')]

    #list of team abbrevs, visitor first
    teams=[str(bsObj.find_all("td")[37].text)[:3],str(bsObj.find_all("td")[38].text)[:3]]
    #test to make sure there are only 4 goalies on the game summary sheet:
    goalies=[[],[]]
    goalie_start=bsObj.find("td",{"valign":"middle"}).find_parent("tr").find_next_siblings("tr")
    j=0
    for i in range(1,len(goalie_start)):
        res=goalie_start[i].find('td').text
        try:
            goalies[j].append(int(res))
        except:
            if res[:4]=='TEAM':
                i+=3
                j=1
    res=[[] for _ in range(len(goals.find_all("tr")))]
    
    for i in range(len(res)):
        for j in range(len(goals.find_all('tr')[i].find_all('td'))):
            val=goals.find_all('tr')[i].find_all('td')[j].text.strip().split(', ')
            if len(val)>1:
                res[i].append(val)
            else:
                res[i].append(val[0])
                if val[0]=='Penalty Shot':
                    res[i].append('')

    if len(res)==1:
        return pd.DataFrame('No goals scored, game in progress.',columns='Err')
    res[0][-2:]=['Visitor_On_Ice','Home_On_Ice']
    df=pd.DataFrame(res[1:],columns=res[0])
    df['Season'],df['gameId']=[season[:4],gameId]

    df['Visitor_Goalie_On_Ice']=df['Visitor_On_Ice'].apply(lambda x: any(str(g) in x for g in goalies[0]) if x is not None else True)
    df['Home_Goalie_On_Ice']=df['Home_On_Ice'].apply(lambda x: any(str(g) in x for g in goalies[1]) if x is not None else True)

    df['Visitor']=teams[0]
    df['Home']=teams[1]

    df['Visitor_Score']=list(cumsum([ 1 if df.loc[ei,'Team']==teams[0] else 0 for ei in df.index]))
    df['Home_Score']=list(cumsum([ 1 if df.loc[ei,'Team']==teams[1] else 0 for ei in df.index]))

    df['Difference']=[ df.Home_Score[ei]-df.Visitor_Score[ei] if df.Team[ei]==teams[1] else df.Visitor_Score[ei]-df.Home_Score[ei] for ei in df.index ]

    return df

def season_summary_scrape(season):
    '''Cycle through all games in a season and add cleaned data to a dataframe.

    '''
    from urllib.request import urlopen
    import pandas as pd


    '''include test for whether season exists in database. must be prior to 2017 (though there's  probably a better way to test for current season) and 1917 or after.

    '''


    max_games = 1271 if int(season) > 2016 else 1230
    failed=0
    for i in range(max_games):
        gameId = "02" + "%04d" % int(i+1)
        try:
            urlopen('http://www.nhl.com/scores/htmlreports/'+str(season)+str(season+1)+'/GS'+gameId+'.HTM')
        except:
            print("unable to find: " + str(season) + "" + str(gameId))
            if int(gameId)==int(failed)+1:
                break
            else:
                failed=int(gameId)
                continue
        print("scraping game " + str(season) + "" + str(gameId))
        df_tmp=summary_scrape(gameId,season)
        if df_tmp.columns[0]=='Err':
            print(df_tmp.Err.iloc[0])
            continue
        else:
            if 'game_summary_df' in locals():
                game_summary_df=game_summary_df.append(df_tmp,ignore_index=True)
            else:
                game_summary_df=df_tmp

    return game_summary_df


def for_against(df):
    '''
    Takes in a df created above and formats it to show goals for vs against.
    '''
    import pandas as pd

    joined=pd.concat([df[['Team','G']].groupby(['Team']).agg('count'),df[['Against','G']].groupby(['Against']).agg('count')],ignore_index=False,sort=True,axis=1)
    joined.columns=['For','Against']
    joined['Difference']=joined.For-joined.Against

    return joined.sort_values('Difference',ascending=False)

def players(df):
    '''
    Takes in a df created above and formats it to show goals and assists for all players included in the database.
    '''

    import pandas as pd

    joined=pd.concat([df[['Goal Scorer','G']].groupby(['Goal Scorer']).agg('count'),df[['Assist','G']].groupby(['Assist']).agg('count'),df[['Assist.1','G']].groupby(['Assist.1']).agg('count')],ignore_index=False,sort=True,axis=1)
    joined.columns=['Goals','Assist.1','Assist.2']
    joined.fillna(0,inplace=True)
    joined=joined.astype(int)
    joined['Points']=joined.sum(axis=1)
    joined['Primary_Points']=joined[['Goals','Assist.1']].sum(axis=1)

    return joined.sort_values('Points',ascending=False)
