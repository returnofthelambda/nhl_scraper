def summary_scrape(gameId,season, *cleand):
    from bs4 import BeautifulSoup
    #import re
    from urllib.request import urlopen
    #import pandas as pd

    season=str(season)+str(int(season)+1)

    url='http://www.nhl.com/scores/htmlreports/'+season+'/GS'+gameId+'.HTM'
    raw_html = urlopen(url).read()
    bsObj=BeautifulSoup(raw_html,"html.parser")
    goals=bsObj.find_all("td")[28]

    #I don't think the visitor/home full names are necessary, but keep for now.
    visitor=[str(bsObj2.find_all("td")[37].text)[:3],bsObj2.find_all("img")[0].get('alt','')]
    home=[str(bsObj2.find_all("td")[38].text)[:3],bsObj2.find_all("img")[1].get('alt','')]
d
    #test to make sure there are only 4 goalies on the game summary sheet:
    if len(bsObj2.find_all("td","lborder + bborder + rborder"))==4:
        visitor_goalie=[bsObj2.find_all("td","lborder + bborder + rborder")[0].text,bsObj2.find_all("td","lborder + bborder + rborder")[1].text]
        home_goalie=[bsObj2.find_all("td","lborder + bborder + rborder")[2].text,bsObj2.find_all("td","lborder + bborder + rborder")[3].text]
    else:
        #throw error


    df=pd.DataFrame(columns=["G","Per","Time","Str","Team","Scorer","1st Assist","2nd Assist","Visitor On Ice","Home On Ice","Visitor","Home"])

    for i in range(len(goals.find_all("tr"))):
        for tag in goals.find_all('tr')[i].find_all('td'):
            #this if statement doesn't do anything. fixt that.
            if tag.text != "\n":
                print(tag.text)

    '''
    Find goalies and use their number and team to cross check that they were on the ice during goal scored. Create column, binary to denote yay/nay if one of the goalies was pulled. This, combined with the period column will allow me to parse data on whether or not the team scored with a regular empty net situation or if it was a delayed penalty. May not capture all situations, i.e. late game situations that would also look like a standard empty net situation... actually, the coding for empty net should filter that out.
    When I filtered the pbp data for empty net goals and searched for unique values in the     period column, only the 3rd period had any empty net values. Hopefully that will allow me to find the information I'm looking for.
    FIXED: Within the individual game scrape, I need to include variables for Visitor/Home team name.
    '''

    return cleand
