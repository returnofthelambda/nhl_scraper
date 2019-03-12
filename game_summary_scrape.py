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
    if bsObj.find_all("td")[17].text != 'Final':
        return pd.DataFrame('Game in progress.',columns='Err')

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



    res[0][5:]=['Scorer','Assist.1','Assist.2','Visitor_On_Ice','Home_On_Ice']
    df=pd.DataFrame(res[1:],columns=res[0])
    df['Scorer']=df['Scorer'].str.replace('\(\d+\)|\d+', '')
    df['Assist.1']=df['Assist.1'].str.replace('\(\d+\)|\d+', '')
    df['Assist.2']=df['Assist.2'].str.replace('\(\d+\)|\d+', '')
    df['Season'],df['gameId']=[season[:4],gameId]

    df['Visitor_Goalie_On_Ice']=df['Visitor_On_Ice'].apply(lambda x: any(str(g) in x for g in goalies[0]) if x is not None else True)
    df['Home_Goalie_On_Ice']=df['Home_On_Ice'].apply(lambda x: any(str(g) in x for g in goalies[1]) if x is not None else True)

    df['Visitor']=teams[0]
    df['Home']=teams[1]

    df['Visitor_Score']=list(cumsum([ 1 if df.loc[ei,'Team']==teams[0] else 0 for ei in df.index]))
    df['Home_Score']=list(cumsum([ 1 if df.loc[ei,'Team']==teams[1] else 0 for ei in df.index]))

    df['Difference']=[ df.Home_Score[ei]-df.Visitor_Score[ei] if df.Team[ei]==teams[1] else df.Visitor_Score[ei]-df.Home_Score[ei] for ei in df.index ]

    df['Time']=pd.to_datetime(df.Time,format='%M:%S').dt.time

    return df

def season_summary_scrape(season,start=0):
    '''
    User provides season number and optionally the starting game, and returns a dataframe of summary data for all games from start to final game of the season. Start defaults to 0 if no input is provided by the user.
    The reason I set the loop to not break until two consecutive games are empty is because if a game is postponed for any reason (weather, etc) the NHL keeps that gameId number for the postponed game, and often those games are made up at the end of the season. If two consecutive games are ever postponed (and I'm sure at some point that will happen) I will have to revisit how to handle this.

    '''
    from urllib.request import urlopen
    import pandas as pd


    '''include test for whether season exists in database. must be prior to 2017 (though there's  probably a better way to test for current season) and 1917 or after.

    '''


    max_games = 1271 if int(season) > 2016 else 1230
    failed=0
    for i in range(start,max_games):
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

    against=[df.Home.loc[ei] if df.Team.loc[ei] == df.Visitor.loc[ei] else df.Visitor.loc[ei] for ei in df.index]  

    df['Against']=against

    joined=pd.concat([df[['Team','G']].groupby(['Team']).agg('count'),df[['Against','G']].groupby(['Against']).agg('count')],ignore_index=False,sort=True,axis=1)
    joined.columns=['For','Against']
    joined['Difference']=joined.For-joined.Against

    return joined.sort_values('Difference',ascending=True)

def players(df):
    '''
    ***ISSUE: DUE TO WAY NHL LISTS PLAYERS ON GAME SUMMARY SHEET, THIS IS USELESS IN IT'S CURRENT FORM. ANY PLAYERS WITH SAME FIRST INITIAL AND LAST NAME WILL GET GROUPED TOGETHER - eg JAMIE AND JORDY BENN. CAN'T LEAVE JERSEY # IN PLACE, BECAUSE PLAYERS CHANGE #'s FROM TIME TO TIME. NEED TO LOOK INTO MAKING DATABASE FROM PBP DATA AND MERGE ON PER/TIME/GAMEID/SEASON TO UPDATE SCORER/ASSIST.1/ASSIST.2 NAMES TO PLAYERS FULL NAMES.***

    Takes in a df created above and formats it to show goals and assists for all players included in the database.
    '''

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
    import pandas as pd

    tc_df=color_scrape()


    df_merged=df.merge(tc_df,left_index=True,right_index=True)

    fig=plt.figure()
    ax1=fig.add_subplot(121)
    max=df_merged.For.max() or df_merged.Against.max()
    ax1.set_xlim([df_merged.Against.min()-2,df_merged.Against.max()+2]) #max+2])
    ax1.set_ylim([df_merged.For.min()-2,df_merged.For.max()+2]) #max+2])
    ax1.set_aspect(1)
    ax1.scatter(df_merged.Against,df_merged.For,color='blue',s=10,edgecolor='none')
    ax1.plot(range(max+5),color='black',linewidth=0.2)

    ax1.plot(df_merged.For.mean(),df_merged.For.mean(),'--')

    for ei in df_merged.index:
        ax1.annotate(ei, 
                     xy=(df_merged.Against.loc[ei], df_merged.For.loc[ei]),
                     xytext=(-20,20),
                     textcoords='offset points',
                     bbox=dict(boxstyle='round,pad=0.5',fc=df_merged.Main.loc[ei].strip(' '),ec=df_merged.Accent.loc[ei]),
                     arrowprops=dict(arrowstyle = '->', connectionstyle='arc3,rad=0'),
                     color=df_merged.Text.loc[ei])

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
    tc=color_scrape()
    df_merged=df.merge(tc,left_index=True,right_index=True)
    fig,ax=plt.subplots(figsize=(175,76))
    ax.set_xlim(auto=True)
    ax.set_ylim([df_merged.Difference.min()-2,df_merged.Difference.max()+2])
    ax.bar(height=df_merged.Difference,x=list(range(1,32)),color=df_merged.Main,width=0.7)

    for rect, label in zip(ax.patches,df_merged.index):
        if rect.get_height() < 0:
            ax.text(rect.get_x()+rect.get_width() / 2, rect.get_height()-0.5, label, ha='center',va='top')
        else:
            ax.text(rect.get_x()+rect.get_width() / 2, rect.get_height()+0.5, label, ha='center',va='bottom')

    return plt.show()
