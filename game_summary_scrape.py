def summary_scrape(gameId,season):
    from bs4 import BeautifulSoup
    #import re
    from urllib.request import urlopen
    import pandas as pd

    season=str(season)+str(int(season)+1)

    url='http://www.nhl.com/scores/htmlreports/'+season+'/GS'+str(gameId)+'.HTM'
    raw_html = urlopen(url).read()
    bsObj=BeautifulSoup(raw_html,"html.parser")
    goals=bsObj.find_all("td")[28]

    #I don't think the visitor/home full names are necessary, but keep for now.
    visitor=[str(bsObj.find_all("td")[37].text)[:3],bsObj.find_all("img")[0].get('alt','')]
    home=[str(bsObj.find_all("td")[38].text)[:3],bsObj.find_all("img")[1].get('alt','')]

    #test to make sure there are only 4 goalies on the game summary sheet:
    if len(bsObj.find_all("td","lborder + bborder + rborder"))==4:
        visitor_goalies=[bsObj.find_all("td","lborder + bborder + rborder")[0].text,bsObj.find_all("td","lborder + bborder + rborder")[1].text]
        home_goalies=[bsObj.find_all("td","lborder + bborder + rborder")[2].text,bsObj.find_all("td","lborder + bborder + rborder")[3].text]
    else:
        print('dumb')
        #throw error


    #df=pd.DataFrame(columns=["G","Per","Time","Str","Team","Scorer","1st Assist","2nd Assist","Visitor On Ice","Home On Ice","Visitor","Home"])
    res=[[] for _ in range(len(goals.find_all("tr")))]
    for i in range(len(goals.find_all("tr"))):
        for tag in goals.find_all('tr')[i].find_all('td'):
            val=tag.text.strip().split(', ')
            if len(val)>1:
                res[i].append(val)
            else:
                res[i].append(val[0])


    res[0][-2]='Visitor on Ice'
    res[0][-1]='Home on Ice'
    df=pd.DataFrame(res[1:],columns=res[0])
    df['Season']=season[:4]
    df['gameId']=gameId

    df['Visitor Goalie On Ice']=df['Visitor on Ice'].apply(lambda x: any(g in x for g in visitor_goalies) if x is not None else True)
    df['Home Goalie On Ice']=df['Home on Ice'].apply(lambda x: any(g in x for g in home_goalies) if x is not None else True)
    df['Visitor']=visitor[0]
    df['Home']=home[0]


    '''
    FIXED: Find goalies and use their number and team to cross check that they were on the ice during goal scored. Create column, binary to denote yay/nay if one of the goalies was pulled. This, combined with the period column will allow me to parse data on whether or not the team scored with a regular empty net situation or if it was a delayed penalty. May not capture all situations, i.e. late game situations that would also look like a standard empty net situation... actually, the coding for empty net should filter that out.
    When I filtered the pbp data for empty net goals and searched for unique values in the     period column, only the 3rd period had any empty net values. Hopefully that will allow me to find the information I'm looking for.
    FIXED: Within the individual game scrape, I need to include variables for Visitor/Home team name.
    '''

    return df

def season_summary_scrape(season):
    '''Cycle through all games in a season and add cleaned data to a dataframe.

    '''
    import urllib.request, json
    import pandas as pd


    '''include test for whether season exists in database. must be prior to 2017 (though there's  probably a better way to test for current season) and 1917 or after.

    '''


    max_games = 1271 if int(season) > 2016 else 30
    failed=0
    for i in range(max_games):
        gameId = "02" + "%04d" % int(i+1)
        try:
            urllib.request.urlopen('http://www.nhl.com/scores/htmlreports/'+str(season)+str(season+1)+'/GS'+gameId+'.HTM')
        except:
            print("unable to find: " + str(season) + "" + str(gameId))
            if int(gameId)==int(failed)+1:
                break
            else:
                failed=int(gameId)
                continue
        print("scraping game " + str(season) + "" + str(gameId))
        df_tmp=summary_scrape(gameId,season)
        if 'game_summary_df' in locals():
            game_summary_df=game_summary_df.append(df_tmp,ignore_index=True)
        else:
            game_summary_df=df_tmp

    return game_summary_df
