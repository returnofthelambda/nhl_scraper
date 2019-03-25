def summary_scrape(season,gameId,subSeason='02'):
    """
    Script that scrapes goals scored data from NHL Game Summary pages. Requires 4 digit season (eg 2018 for the 2018-19 season), 4 digit gameId and 2 digit sub season (01 preseason, 02 regular, 03 playoffs). 

    This script returns a dataframe that contains all information in the Goal Summary section and augments it with a few extra bits of info:
        #1: Whether or not the home or away goalies were on the ice. Instead of cross checking a separate database, the test is done from the data provided on the Game Summary Page. Test can handle any amount of goalies (typically 2 per team).
        #2: Which team the goal was scored against.
        #3: How that goal impacted the score, from the pesrpective of the scoring team. This is to make it easier suss out what 3rd period goals without a goalie on the ice are the result of gambling for an extra attacker vs how many of those goals are from delayed penalties.
    """
    from bs4 import BeautifulSoup
    from urllib.request import urlopen
    import pandas as pd
    from numpy import cumsum
    import os

    if len(str(season))==4:
        season=str(season)+str(int(season)+1)

    url='http://www.nhl.com/scores/htmlreports/'+season+'/GS'+str(subSeason).zfill(2)+str(gameId).zfill(4)+'.HTM'
    #url='http://www.nhl.com/scores/htmlreports/20132014/GS020001.HTM'
    raw_html = urlopen(url).read()
    bsObj=BeautifulSoup(raw_html,'html.parser')
    tds=bsObj.find_all('td')

    for fin in range(len(tds)):
        if tds[fin].text=='Final':
            break
        if fin==len(tds)-1:
            return pd.DataFrame(['Game in progress.'],columns=['Err']),pd.DataFrame([])

    date=pd.to_datetime(tds[fin-4].text).strftime('%Y-%m-%d')
    startTime=pd.to_datetime(tds[fin-2].text.split('\xa0')[1]).strftime('%H:%M')
    goals=tds[fin+11]

    #list of team abbrevs, visitor first
    teams={'Visitor':str(tds[fin+20].text)[:3],'Home':str(tds[fin+21].text)[:3]}

    tmp=[[],[]]
    goalieStart=bsObj.find('td',{'valign':'middle'}).find_parent('tr').find_next_siblings('tr')
    j=0
    for i in range(1,len(goalieStart)):
        res=goalieStart[i].find('td').text
        try:
            tmp[j].append(int(res))
        except:
            if res[:4]=='TEAM':
                i+=3
                j=1
    goalies={'Visitor':tmp[0],'Home':tmp[1]}
    #create empty list of lists for each row in Goal summary
    res=[[] for _ in range(1,len(goals.find_all('tr')))]

    for i in range(len(res)):
        for j in range(len(goals.find_all('tr')[i+1].find_all('td'))):
            val=goals.find_all('tr')[i+1].find_all('td')[j].text.strip().split(', ')
            if len(val)>1:
                res[i].append(val)
            else:
                res[i].append(val[0])
                if val[0]=='Penalty Shot':
                    res[i].append('')


    cols=['G','Per','Time','Str','Team','Scorer','Assist.1','Assist.2','Visitor_On_Ice','Home_On_Ice']
    df=pd.DataFrame(res,columns=cols)
    #strip out numbers that are included with players names to denote season total of Goals / Assists
    for col in cols[5:8]:
        df[col]=df[col].str.replace('\(\d+\)|\d+', '').str.strip()
    df['Season'],df['gameId']=[season[:4],str(str(subSeason)+str(gameId).zfill(4)).zfill(6)]
    if any(df['Assist.1'].str.contains('Unsuccessful Penalty Shot')):
        try:
            p_df=pd.read_csv('csv/failed_ps_'+str(int(season))+'.csv',dtype={'gameId':'str'})
            p_df=pd.concat([p_df,df[df['Assist.1']=='Unsuccessful Penalty Shot'].drop(['Visitor_On_Ice','Home_On_Ice'],axis=1)],sort=False).drop_duplicates()
        except:
            p_df=df[df['Assist.1']=='Unsuccessful Penalty Shot'].drop(['Visitor_On_Ice','Home_On_Ice'],axis=1)

        p_df.set_index(['Season','gameId']).to_csv('csv/failed_ps_'+str(int(season))+'.csv',index=True)

    #drop rows that contain unsuccessful penalty shots
    df=df[df['Assist.1']!='Unsuccessful Penalty Shot']

    for team in ['Visitor','Home']:
        df[team+'_Goalie_On_Ice']=df[team+'_On_Ice'].apply(lambda x: any(str(g) in x for g in goalies[team]) if x is not None else True)
        df[team+'_Score']=cumsum([ 1 if df.loc[ei,'Team']==teams[team] else 0 for ei in df.index])

    df['Difference']=[ df.Home_Score[ei]-df.Visitor_Score[ei] if df.Team[ei]==teams['Home'] else df.Visitor_Score[ei]-df.Home_Score[ei] for ei in df.index ]

    #coerce errors since SO goals don't occur at a time
    df['Time']=pd.to_datetime(df.Time,format='%M:%S',errors='coerce').dt.time


    df_meta=pd.DataFrame([[season[:4],str(subSeason)+str(gameId).zfill(4),date,startTime,teams['Visitor'],teams['Home']]],columns=['Season','gameId','Date','Start','Visitor','Home'])

    return df.set_index(['Season','gameId']),df_meta.set_index(['Season','gameId'])

def season_summary_scrape(season,start=0,subSeason='02',autosave=True):
    """
    User provides season number and optionally the starting game, and returns a dataframe of summary data for all games from start to final game of the season. Start defaults to 0 if no input is provided by the user.
    The reason I set the loop to not break until two consecutive games are empty is because if a game is postponed for any reason (weather, etc) the NHL keeps that gameId number for the postponed game, and often those games are made up at the end of the season. If two consecutive games are ever postponed (and I'm sure at some point that will happen) I will have to revisit how to handle this.

    """
    from urllib.request import urlopen
    import pandas as pd
    from datetime import datetime


    """include test for whether season exists in database. must be prior to 2017 (though there's  probably a better way to test for current season) and 1917 or after.

    """


    max_games = 1291 #if int(season) > 2016 else 1230
    failed=0
    skipped=[]
    for i in range(start,max_games):
        gameId = '%04d' % int(i+1)
        try:
            urlopen('http://www.nhl.com/scores/htmlreports/'+str(season)+str(int(season)+1)+'/GS'+str(subSeason).zfill(2)+gameId+'.HTM')
        except:
            skipped.append([season,str(subSeason)+str(gameId),'DNE',datetime.fromtimestamp(datetime.timestamp(datetime.now())).strftime('%Y-%m-%d %H:%M:%S')])
            print('unable to find: ' + str(season) + str(subSeason) + str(gameId))
            if int(gameId)==int(failed)+1:
                break
            else:
                failed=int(gameId)
                continue
        print('scraping game ' + str(season) + str(subSeason) + str(gameId))
        df_tmp,df_meta=summary_scrape(str(season),gameId,subSeason)
        if df_tmp.columns[0]=='Err':
            print(df_tmp.Err.iloc[0])
            skipped.append([season,str(subSeason)+str(gameId),'In Progress / Missing',datetime.fromtimestamp(datetime.timestamp(datetime.now())).strftime('%Y-%m-%d %H:%M:%S')])
            continue
        else:
            if 'game_summary_df' in locals():
                game_summary_df=game_summary_df.append(df_tmp,ignore_index=False)
                gs_meta_df=gs_meta_df.append(df_meta,ignore_index=False)
            else:
                game_summary_df=df_tmp
                gs_meta_df=df_meta
    if len(skipped)>2:
        pd.DataFrame(skipped[:-2],columns=['Season','gameId','Reason','Time Failed']).to_csv('skipped_'+str(season)+'.csv',index=False)

    while type(autosave)!=bool:
        text=input('Would you like to save to csv (Y/n)? ')
        if text[0].upper()=='Y':
            autosave=True
        elif text[0].upper()=='N':
            autosave=False
        else:
            print('Please enter Y/n.')
    if autosave:
        game_summary_df.to_csv('ss_'+str(season)+str(int(season+1))+'.csv',index=True)
        gs_meta_df.to_csv('ss_'+str(season)+str(int(season+1))+'_meta.csv',index=True)

    return game_summary_df,gs_meta_df

def ss_df_import(season=2009):
    import pandas as pd

    df=pd.read_csv('csv\ss_'+str(season)+str(season+1)+'.csv',dtype={'gameId':'str'}).set_index(['Season','gameId'])

    for szn in range(season+1,2019):
        df=pd.concat([df,pd.read_csv('csv\ss_'+str(szn)+str(szn+1)+'.csv',dtype={'gameId':'str'}).set_index(['Season','gameId'])],sort=False)

    return df


def for_against(df):
    """
    Takes in a df created above and formats it to show goals for vs against.
    """
    import pandas as pd

    against=[df.Home.loc[ei] if df.Team.loc[ei] == df.Visitor.loc[ei] else df.Visitor.loc[ei] for ei in df.index]  

    df['Against']=against

    joined=pd.concat([df[['Team','G']].groupby(['Team']).agg('count'),df[['Against','G']].groupby(['Against']).agg('count')],ignore_index=False,sort=True,axis=1)
    joined.columns=['For','Against']
    joined['Difference']=joined.For-joined.Against

    return joined.sort_values('Difference',ascending=True)

def players(df):
    """
    ***ISSUE: DUE TO WAY NHL LISTS PLAYERS ON GAME SUMMARY SHEET, THIS IS USELESS IN IT'S CURRENT FORM. ANY PLAYERS WITH SAME FIRST INITIAL AND LAST NAME WILL GET GROUPED TOGETHER - eg JAMIE AND JORDY BENN. CAN'T LEAVE JERSEY # IN PLACE, BECAUSE PLAYERS CHANGE #'s FROM TIME TO TIME. NEED TO LOOK INTO MAKING DATABASE FROM PBP DATA AND MERGE ON PER/TIME/GAMEID/SEASON TO UPDATE SCORER/ASSIST.1/ASSIST.2 NAMES TO PLAYERS FULL NAMES.***

    Takes in a df created above and formats it to show goals and assists for all players included in the database.
    """

    import pandas as pd

    joined=pd.concat([df[['Scorer','G']].groupby(['Scorer']).agg('count'),df[['Assist.1','G']].groupby(['Assist.1']).agg('count'),df[['Assist.2','G']].groupby(['Assist.2']).agg('count')],ignore_index=False,sort=True,axis=1)
    joined.columns=['Goals','Assist.1','Assist.2']
    joined.fillna(0,inplace=True)
    joined=joined.astype(int)
    joined['Points']=joined.sum(axis=1)
    joined['Primary_Points']=joined[['Goals','Assist.1']].sum(axis=1)

    return joined.sort_values('Points',ascending=False)

def extra_attacker(df):


    df=df[(df.Visitor_Goalie_On_Ice == False) | (df.Home_Goalie_On_Ice == False)]
    df=df[(df.Per.isin(['1', '2', '3', 'OT']))]

    return df[(~df.Str.isin(['SH-EN','EV-EN','PP-EN','EV-PS','PP-PS','SH-PS']))]

def delayed_penalty(df):
    #Calls extra attacker. If this has already been called on df, it won't change anything
    import extra_attacker
    df=extra_attacker(df)

    return pd.concat([df[df.Per!='3'],(df[(df.Per=='3') & (df.Difference>0)]),df[(df.Time < datetime.time(minute=10,second=00)) & (df.Per=='3') & (df.Difference<1)]])


def for_against_plot(df):
    import matplotlib.pyplot as plt
    from matplotlib.offsetbox import OffsetImage, AnnotationBbox
    import os

    def getImage(path,zoom=.5):
        return OffsetImage(plt.imread(path),zoom=zoom)
    #tc_df=color_scrape()
    #tc_df=pd.read_csv('nhl_team_colors.csv',index_col='Abbrev')


    #df_merged=df.merge(tc_df,left_index=True,right_index=True)

    fig,ax1=plt.subplots()#figsize=(125,36))
    ax1.set_xlim(auto=True)

    max=df.For.max() or df.Against.max()
    ax1.set_xlim([df.Against.min()-2,max+2])
    ax1.set_ylim([df.For.min()-2,max+2])
    ax1.set_aspect(1)
    ax1.scatter(df.Against,df.For,color=df.Main,s=50,edgecolor=df.Accent)
    ax1.plot(range(max+5),color='black',linewidth=0.2)

    ax1.set_xlabel('Goals Allowed')
    ax1.set_ylabel('Gaols Scored')
    plt.title('Extra Attacker Goals Scored / Allowed in the NHL Since 2014-2015 Season')

    artists=[]
    
    paths=[os.path.join(os.getcwd(),'logos',df.Logos[i]) for i in range(len(df.Logos))]
    for diff,x0,y0,path in zip(df.Difference,df.Against,df.For,paths):
        ab=AnnotationBbox(getImage(path),(x0,y0), frameon=False)
        artists.append(ax1.add_artist(ab))

    return plt.show()

def color_scrape():
    import pandas as pd
    from bs4 import BeautifulSoup as BS
    from urllib.request import urlopen
    url = 'https://teamcolorcodes.com/nhl-team-color-codes/'
    raw_html=urlopen(url).read()
    bsObj=BS(raw_html,'html.parser')
    colors=bsObj.find_all('p')[2].find_all('a')

    tc=[[colors[i].text,colors[i]['style'].split('; ')[0].split(': ')[1].strip(' '),colors[i]['style'].split('; ')[1].split(': ')[1].strip(' '),colors[i]['style'].split('; ')[2].split(': ')[1].split(' ')[2].strip(';').strip(' ')] for i in range(len(colors))]

    tc_df=pd.DataFrame(tc,columns=['Team','Main','Text','Accent'])
    tc_df.Accent=['#'+tc_df.Accent[ei][1:]*2 if len(tc_df.Accent[ei])==4 else tc_df.Accent[ei] for ei in tc_df.index]
    tc_df.Main=['#'+tc_df.Main[ei][1:]*2 if len(tc_df.Main[ei])==4 else tc_df.Main[ei] for ei in tc_df.index]
    tc_df['Abbrev']=['ANA','ARI','BOS','BUF','CGY','CAR','CHI','COL','CBJ','DAL','DET','EDM','FLA','L.A','MIN','MTL','NSH','N.J','NYI','NYR','OTT','PHI','PIT','STL','S.J','T.B','TOR','VAN','VGK','WSH','WPG'] 
    return tc_df.set_index('Abbrev')


def bar_plot(df):
    import matplotlib.pyplot as plt
    import pandas as pd

    #tc=pd.read_csv('nhl_team_colors.csv',index_col='Abbrev')# or color_scrape()
    #df_merged=df.merge(tc,left_index=True,right_index=True)
    fig,ax=plt.subplots()#figsize=(125,36))
    plt.title('Net Extra Attacker Goals Scored in the NHL Since 2014-2015 Season')
    ax.set_xlim([df.Difference.min()-2,df.Difference.max()+2])
    ax.set_yticklabels([])
    ax.set_yticks([])
    ax.barh(width=df.Difference,y=list(range(1,32)),color=df.Main,height=0.7)

    ax.set_xlim(auto=True)
    ax.set_ylim(auto=True)

    for rect, label in zip(ax.patches,df.index):
        color=df.Accent.loc[label]
        if rect.get_width() < 0:
            ax.text(rect.get_width()-0.2, rect.get_y(), label, ha='right',va='bottom',color=color)
        else:
            ax.text(rect.get_width()+0.2, rect.get_y(), label, ha='left',va='bottom',color=color)

    return plt.show()
