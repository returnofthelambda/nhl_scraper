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

    '''
    Find goalies and use their number and team to cross check that they were on the ice
    during goal scored. Create column, binary to denote yay/nay if one of the goalies was 
    pulled. This, combined with the period column will allow me to parse data on whether
    or not the team scored with a regular empty net situation or if it was a delayed penalty.
    May not capture all situations, ie late game situations that would also look like 
    a standard empty net situation... actually, the coding for empty net should filter that out.
    When I filtered the pbp data for empty net goals and searched for unique values in the 
    period column, only the 3rd period had any empty net values. Hopefully that will allow me to 
    find the information I'm looking for.
    '''

    return cleand
