#!/usr/bin/env python
# coding: utf-8

# # Importing Libraries

# In[22]:


from bs4 import BeautifulSoup
import urllib
from urllib.request import urlopen
from fake_useragent import UserAgent
from selenium import webdriver
import requests
import pandas as pd
from textblob import TextBlob
import re
from PIL import Image
from io import BytesIO
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
import matplotlib.pyplot as plt
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import ast
import pyrebase
analyser = SentimentIntensityAnalyzer()


# # Creating Recommendation

# In[23]:


def create_recommendation():

    df=pd.read_csv('movie_metadata.csv')
    df['plot_keywords'].fillna('Unknown',inplace=True)
    df['director_name'].fillna('Unknown',inplace=True)
    df['actor_1_name'].fillna('Unknown',inplace=True)
    df['actor_2_name'].fillna('Unknown',inplace=True)
    df['actor_3_name'].fillna('Unknown',inplace=True)

    df=df[df['plot_keywords']!='Unknown']
    df=df[df['director_name']!='Unknown']
    df=df[df['actor_1_name']!='Unknown']
    df=df[df['actor_2_name']!='Unknown']
    df=df[df['actor_3_name']!='Unknown']

    df['plot_keywords']=df['plot_keywords'].apply(lambda x:x.replace('|',' '))
    df['plot_keywords']=df.apply(lambda x:x['plot_keywords']+' '+x['director_name']+' '+x['actor_1_name']+' '+
                                 x['actor_2_name']+' '+x['actor_3_name'],axis=1)
    df=df.loc[:,['movie_title','plot_keywords']]
    df=df.reset_index().drop('index',axis=1)
    df['_id']=df.index
    df.columns=['title','plot','_id']
    cols=['_id','title','plot']
    df=df[cols]
    df['title']=df['title'].apply(lambda x:x.strip().lower())

    tfidf = TfidfVectorizer(stop_words='english')
    df['plot'] = df['plot'].fillna('')
    tfidf_matrix = tfidf.fit_transform(df['plot'])
    similarity_distance = cosine_similarity(tfidf_matrix,tfidf_matrix)

    def get_recommendations(title, cosine_sim=similarity_distance):
        # Get the index of the movie that matches the title
        idx  = df['_id'][df['title']==title].index[0]

        # Get all movies with same similarity score
        sim_scores = list(enumerate(cosine_sim[idx]))

        # Sort the movies based on the similarity scores
        sim_scores = sorted(sim_scores, key=lambda x: x[1], reverse=True)

        # Get the movie indices
        movie_indices = [i[0] for i in sim_scores]

        # Return the top 10 most similar movies
        return df.iloc[movie_indices][:10]

    final=pd.DataFrame(columns=['Title','Recommendations'])

    for i in range(len(df)):
        val=df['title'][i]
        val=val.strip().lower()

        rec=list(get_recommendations(val)['title'])

        if(len(rec)>5):
            rec=rec[1:6]
        else:
            rec=rec[1:]

        final.loc[len(final)]=[val,rec]

    return final


# In[ ]:


def recommendations(title):

    title=title.strip().lower()

    recom=rec[rec['Title']==title]
    if(recom.shape[0]!=0):
        recom=recom['Recommedations'].tolist()[0]
        recom=ast.literal_eval(recom)
    else:
        recom=[]

    return recom


# # Connecting To Firebase

# In[24]:


firebaseConfig = {'apiKey': "AIzaSyBXO5doO7OaUCBl89OAD_GOve1_W--Zxbw",
                  'authDomain': "mediascrapper-13ce5.firebaseapp.com",
                  'projectId': "mediascrapper-13ce5",
                  'storageBucket': "mediascrapper-13ce5.appspot.com",
                  'messagingSenderId': "10842217782",
                  'appId': "1:10842217782:web:a00ef6a519df7654c1a797",
                  'measurementId': "G-WF1WV22SNR",
                  'databaseURL': "https://mediascrapper-13ce5-default-rtdb.firebaseio.com/"}

firebase = pyrebase.initialize_app(firebaseConfig)
db=firebase.database()


# In[25]:


def fetch_firebase(name,cols):

    data=db.child(name).get()
    df=pd.DataFrame(columns=cols)
    for per in data.each():
        df.loc[len(df)]=list(per.val().values())

    return df


# In[26]:


def upload_firebase(df,name,ctr):

    for i in range(len(df)):
        try:
            val=dict(df.iloc[i])
            db.child(name).child(ctr).set(val)
            ctr=ctr+1
        except:
            continue


# In[27]:


#Recommendation Data
try:
    rec=fetch_firebase("Movie_Recommendations",['Recommedations','Title'])
except:
    rec=create_recommendation()

#Search Data

try:
    search_old=fetch_firebase("Search_Data",['ID','IMDB Link','Input','Type'])
except:
    search_old=pd.DataFrame(columns=['ID',"Input",'Type','IMDB Link'])

search=pd.DataFrame(columns=['ID',"Input",'Type','IMDB Link'])

#User Data

try:
    user_old=fetch_firebase("User",['ID','Inputs'])
except:
    user_old=pd.DataFrame(columns=['ID',"Inputs"])

user=pd.DataFrame(columns=['ID',"Inputs"])


#Searched Input Content

try:
    search_data_old=fetch_firebase("Scrapped_Data",['Directors, Writers, Main Lead','Genres','Length','Name',
                                                    'Ratings','Release','Reviews Count','Sentiment','Storyline','Type'])
except:
    search_data_old=pd.DataFrame(columns=['Directors, Writers, Main Lead','Genres','Length','Name',
                                      'Ratings','Release','Reviews Count','Sentiment','Storyline','Type'])

search_data=pd.DataFrame(columns=['Directors, Writers, Main Lead','Genres','Length','Name',
                           'Ratings','Release','Reviews Count','Sentiment','Storyline','Type'])


# # Scrapping

# In[32]:


def link_extract(name):
    query = name

    query = urllib.parse.quote_plus(query) # Format into URL encoding
    number_result = 1
    ua = UserAgent()
    google_url = "https://www.google.com/search?q=" + query +"imdb"+"&num=" + str(number_result)
    response = requests.get(google_url, {"User-Agent": ua.random})
    soup = BeautifulSoup(response.text, "html.parser")
    result_div = soup.find_all('div', attrs = {'class': 'ZINbbc'})
    for r in result_div:
        try:
            link = r.find('a', href = True)
            title = r.find('div', attrs={'class':'vvjwJb'}).get_text()
            if link != '':
                imdb_links=link['href'][7:44]
                break
        except:
            continue

    return imdb_links


# In[33]:


#Function to extract information
def scrapper_media(imdb_link):

    values=[]
    dirs_cast_="Unknown"
    genres_d="Unknown"
    length_d="Unknown"
    name="Unknown"
    rating_d="Unknown"
    release_d="Unknown"
    review_count_d="Unknown"
    sentiment_d="Unknown"
    storyline_d="Unknown"
    type_d="Unknown"

    ua = UserAgent()
    response=requests.get(imdb_link, {"User-Agent": ua.random})
    soup=BeautifulSoup(response.text,'lxml')

    if(re.search('https://www.imdb.com',imdb_link)):

        #Type
        try:
            content=soup.find('div',class_='titleReviewBar')
            for i in content.find_all('div',class_='titleReviewBarItem')[:1]:
                k=i.find('div',class_='metacriticScore score_favorable titleReviewBarSubItem')
                if(k):
                    type_='Movie'
                else:
                    type_='Series'
            type_d=type_
        except:
            type_d='Unknown'

        #Name
        print('-----------------------------------\n\n')
        try:
            name=soup.find('div',class_='title_wrapper')
            name_db=name.find('h1').text.strip().split('\xa0')[0]
            print('Name: ',name_db,'\n\n')
            name_d=name_db
        except:
            name_d='Unknown'
            print('Name: Unknown','\n\n')
        print('-----------------------------------\n\n')

        #Recommendation
        recom=recommendations(name_db)

        #Length
        print('-----------------------------------\n\n')
        try:
            if(type_=='Series'):
                if(soup.select('#titleDetails > div:nth-child(15)')):
                    for i in soup.select('#titleDetails > div:nth-child(15)'):
                        x=i.text.strip().replace('\n','')
                        x=x.split('|')[0].split(':')[1]
                        print('Episode Length: ',x,'\n\n')
                        length_d=x
                else:
                    print('Episode Length: Unknown','\n\n')
                    length_d='Unknown'
            else:
                if(soup.select('#titleDetails > div:nth-child(23)')):
                    for i in soup.select('#titleDetails > div:nth-child(23)'):
                        x=i.text.strip().replace('\n','')
                        x=x.split('|')[0].split(':')[1]
                        print('Movie Length: ',x,'\n\n')
                        length_d=x
                else:
                    print('Movie Length: Unknown','\n\n')
                    length_d='Unknown'
        except:
            length_d='Unknown'
            print('Movie/Episode Length : Unknown')
        print('-----------------------------------\n\n')

        #Genres
        print('-----------------------------------\n\n')
        try:
            x=[]
            content=soup.find('div',id='titleStoryLine')
            print("Genres: ")
            for i in content.find_all('div',class_='see-more inline canwrap'):
                try:
                    k=i.find_all('a')
                    for j in k:
                        if('genres' in j['href']):
                            x.append(j.text.strip())
                            print(j.text.strip())
                except:
                    print("Genres: Unknown")

            if(len(x)>0):
                genres_d=x
            else:
                genres_d='Unknown'

        except:
            genres_d='Unknown'
            print('Genres: Unknown\n\n')
        print('-----------------------------------\n\n')

        #Release
        print('-----------------------------------\n\n')
        try:
            content=soup.find('div',id='titleDetails')
            val_='Unknown'
            for i in content.find_all('div',class_='txt-block'):
                if(i.text.strip().split(':')[0]=='Release Date'):
                    x=i.text.strip().replace('\n','')
                    x=i.text.strip().replace('\n','').split('   ')[0]
                    val_=x.split(':')[1].strip()
            if(val_!='Unknown'):
                print("Release Date: ",val_)
                release_d=val_
            else:
                print('Release Date: Unknown')
                release_d='Unknown'
        except:
            release_d='Unknown'
            print('Release Date: Unknown')
        print('-----------------------------------\n\n')

        #Storyline
        print('-----------------------------------\n\n')
        try:
            l=soup.find('div',id="titleStoryLine")
            l=l.find('p')

            if(l):
                print('Storyline: ',l.text.strip())
                storyline_d=l.text.strip()
            else:
                print('Storyline: Unknown')
                storyline_d='Unknown'

        except:
            storyline_d='Unknown'
            print('\n')
        print('-----------------------------------\n\n')

        #Directors, Writers, Main Lead
        print('-----------------------------------\n\n')
        try:
            v=[]
            content=soup.find('div',class_='plot_summary')
            for i in content.find_all('div',class_='credit_summary_item'):
                a=i.find('h4')
                b=i.find('a')
                print(a.text.strip(),': ',b.text.strip())
                v.append(b.text.strip())

            if(len(v)!=0):
                dirs_cast_d=v
            else:
                dirs_cast_d='Unknown'
        except:
            dirs_cast_d='Unknown'
            print('Directors, Writers, Main Lead: Unknown')
        print('-----------------------------------\n\n')

        #Rating
        print('-----------------------------------\n\n')
        try:
            l=soup.find('div',class_='ratingValue')
            if(l):
                print('Rating: ',l.find('strong')['title'])
                rating_d=l.find('strong')['title']
            else:
                print('Rating: Unknown')
                rating_d='Unknown'
        except:
            rating_d='Unknown'
            print('Rating: Unknown\n')
        print('-----------------------------------\n\n')

        #Reviews Count
        print('-----------------------------------\n\n')
        try:
            content=soup.find('div',class_='titleReviewBarItem titleReviewbarItemBorder')
            x=content.text.strip().replace('\n','').split(' ')
            x=[y for y in x if y!='']

            print("Total Users Reviews: ",x[1],'\nTotal Critic Reviews: ',x[2].split('|')[1])


            if(x[1]):
                review_count_d=x[1]
            else:
                review_count_d='Unknown'
        except:
            review_count_d='Unknown'
        print('-----------------------------------\n\n')

        #Pictures
        try:
            pics=soup.find('div',class_="mediastrip")
            print('-----------------------------------\n\n')
            for i in pics.find_all('a'):
                print(imdb_link[:20]+i['href'])
            print('-----------------------------------\n\n')
        except:
            print('\n')

        #Number of Seasons
        print('-----------------------------------\n\n')
        try:
            if(type_=='Series'):
                for i in soup.select('#title-episode-widget > div > div:nth-child(4)'):
                    k=i.find_all('a')
                    if(k):
                        for j in k[:1]:
                            print("Number of Seasons: "+j.text.strip()+'\n')
        except:
            print('\n')
        print('-----------------------------------\n\n')

        #Number of Episodes
        print('-----------------------------------\n\n')
        try:
            for k in soup.select('#title-overview-widget > div.vital > div.button_panel.navigation_panel > a > div > div > span'):
                if(k):
                    print("Number of episodes:"+k.text.strip().split(' ')[0]+"\n")
        except:
            print('\n')
        print('-----------------------------------\n\n')

        #Poster
        try:
            content=soup.find('div',class_='poster')
            if(content):
                co=content.find('a')
                co2=co.find('img')
                response = requests.get(co2['src'])
                img = Image.open(BytesIO(response.content))
                plt.imshow(img)
        except:
            print('\n')

        #Creators and Star Cast
        try:
            content=soup.find('div',class_='plot_summary')
            if(content):
                for i in content.find_all('div',class_='credit_summary_item'):
                    j=i.find('h4')
                    if(j):
                        if((j.text.strip()=='Creator:')|(j.text.strip()=='Creators:')):
                            w=i.find_all('a')
                            print('-----------------------------------\n\n')
                            print('Creator:')
                            for s in w:
                                if(s.text.strip()=='See full cast & crew'):
                                    break
                                else:
                                    print(s.text.strip())
                            print('-----------------------------------\n\n')
                        elif(j.text.strip()=='Stars:'):
                            w=i.find_all('a')
                            print('-----------------------------------\n\n')
                            print('Stars:')
                            for s in w:
                                if(s.text.strip()=='See full cast & crew'):
                                    break
                                else:
                                    print(s.text.strip())
                            print('-----------------------------------\n\n')
                    else:
                        print('-----------------------------------\n\n')
                        print('Not Available')
                        print('-----------------------------------\n\n')
        except:
            print('\n')

        #Trivia And Goofs
        try:
            content=soup.find('div',id='titleDidYouKnow')
            if(content):
                trivia=content.find('div',id='trivia')
                if(trivia):
                    print('-----------------------------------\n\n')
                    print("Trivia: "+trivia.text[7:-24].strip()+"\n")
                    print('-----------------------------------\n\n')

                goof=content.find('div',id="goofs")
                if(goof):
                    print('-----------------------------------\n\n')
                    print('Goofs: '+goof.text[6:-24].strip()+"\n")
                    print('-----------------------------------\n\n')

                quotes=content.find('div',id="quotes")
                if(quotes):
                    print('-----------------------------------\n\n')
                    quotes=quotes.text.strip().replace('See more »','').split('\n')[1:-1]
                    quotes=" ".join(quotes)
                    print('Quotes:\n '+quotes+"\n")
                    print('-----------------------------------\n\n')
        except:
            print('\n')

        #Other Details
        try:
            content=soup.find('div',id='titleDetails')
            tags=['Language:','Also Known As:','Filming Locations:','Budget:','Opening Weekend USA:','Opening Weekend USA:',
                  'Gross USA:','Cumulative Worldwide Gross:']
            l=[]
            for i in content.find_all('div',class_='txt-block'):
                k=i.find('h4')
                if(k):
                    if(k.text.strip() in tags):
                        val=i.text.strip().replace('See more\xa0»','')
                        print(val)
        except:
            print('\n')

        #Reviews
        try:
            reviews=[]
            link2=imdb_link+'reviews?ref_=tt_urv'
            response2=requests.get(link2, {"User-Agent": ua.random})
            soup2=BeautifulSoup(response2.text,'lxml')
            content=soup2.find('div',class_='lister-list')
            ctr=0

            print('-----------------------------------\n\n')
            print('Reviews:\n')

            for i in content.find_all('div',class_='lister-item-content'):

                if(ctr!=5):

                    review=i.find('div',class_='content')
                    rev=review.text.strip().replace('Permalink','').replace('Was this review helpful?  Sign in to vote.','').split('\n')[:-7]
                    rev=" ".join(rev)
                    reviews.append(rev)
                    print(rev)
                    print('\n\n')
                    ctr=ctr+1

            print('-----------------------------------\n\n')
            reviews_=" ".join(reviews)
            print('-----------------------------------\n\n')
            if(reviews_):
                score = analyser.polarity_scores(reviews_)['compound']
                if(score>=0.5):
                    print('Sentiment: Positive')
                    sentiment_d='Positive'
                else:
                    print('Sentiment: Negative')
                    sentiment_d='Negative'
            else:
                sentiment_d='Unknown'
            print('-----------------------------------\n\n')
        except:
            sentiment_d='Unknown'
            print('\n')

        #Recommendations
        try:
            if(len(recom)>0):

                print('-----------------------------------\n\n')
                print('Recommendations: \n')
                for i in recom:
                    print(i)
                print('-----------------------------------\n\n')
        except:
            print('\n')

    else:
        print('Not Available')

    values=[dirs_cast_d,genres_d,length_d,name_d,rating_d,release_d,review_count_d,sentiment_d,storyline_d,type_d]

    return name_db,values



# In[34]:


def scrapper_star(imdb_link):

    ua = UserAgent()
    imdb_links=imdb_link[:-1]
    imdb_links2=imdb_links+'bio?ref_=nm_ov_bio_sm'

    response=requests.get(imdb_links2, {"User-Agent": ua.random})
    soup=BeautifulSoup(response.text,'lxml')

    if(re.search('https://www.imdb.com',imdb_links2)):

        content=soup.find('div',class_='article listo')

        #Name
        try:
            name=content.find('div',class_='subpage_title_block name-subpage-header-block')
            name=name.find('h3').text.strip()
            print('-----------------------------------\n\n')
            if(name):
                inp_name=name
                print('Name:',name)
            else:
                print('Name: Unknown')
                inp_name='Unknown'
            print('-----------------------------------\n\n')
        except:
            print('\n')

        #Overview
        try:
            bio=content.find('table',id='overviewTable')
            print('-----------------------------------\n\n')
            if(bio):
                print('Overview:\n')
                for i in bio.find_all('tr'):
                    k=i.find_all('td')
                    a=k[0].text.strip()
                    b=k[1].text.strip()
                    b=b.replace('\xa0','')
                    b=' '.join(b.split())
                    print(a,':',b)
            else:
                print('Overview: Unknown')
            print('-----------------------------------\n\n')
        except:
            print('\n')

        #Bio
        try:
            bio_mini=content.find('div',class_='soda odd')
            bio_mini=bio_mini.text.strip().replace('\n','').split('- IMDb Mini Biography By:')[0]
            print('-----------------------------------\n\n')
            if(bio_mini):
                print('Bio:\n')
                print(bio_mini)
            else:
                prin('Bio: Unknown')
            print('-----------------------------------\n\n')
        except:
            print('\n')

        #Spouse
        try:
            spouse=content.find('table',id='tableSpouses')
            print('-----------------------------------\n\n')
            if(spouse):

                print('Spouse:\n')
                for i in spouse.find_all('tr'):
                    k=i.find_all('td')
                    a=k[0].text.strip()
                    b=k[1].text.strip()
                    b=b.replace('\xa0','')
                    b=' '.join(b.split())
                    print(a,':',b)
            else:
                print('Spouse: Unknown')
            print('-----------------------------------\n\n')
        except:
            print('\n')

        #Salary
        try:
            sal=content.find('table',id='salariesTable')
            sum_=0
            print('-----------------------------------\n\n')
            if(sal):
                for i in sal.find_all('tr'):
                    k=i.find_all('td')
                    b=k[1].text.strip()
                    b=b.replace('\xa0','').replace('$','').replace(',','')
                    b=' '.join(b.split())
                    b=b.split(' ')[0]
                    try:
                        b=int(b)
                        sum_+=b
                    except:
                        sum_+=0

                print('Earnings: ',"$",sum_)
            else:
                print('Earnings: Unknown')
            print('-----------------------------------\n\n')
        except:
            print('\n')

    response=requests.get(imdb_links, {"User-Agent": ua.random})
    soup=BeautifulSoup(response.text,'lxml')

    if(re.search('https://www.imdb.com',imdb_links)):

        #Role
        try:
            content=soup.find('div',class_='infobar')
            print('-----------------------------------\n\n')
            if(content):
                print("Roles: ",content.text.strip().replace('\n',''))
            print('-----------------------------------\n\n')

            #Movies Famous For
            content=soup.find_all('div',class_='knownfor-title')
            print('-----------------------------------\n\n')
            print('Movies Famous For:\n')
            if(content):
                for i in content:
                    k=i.find('div',class_='knownfor-title-role')
                    print(k.text.strip())
            print('-----------------------------------\n\n')
        except:
            print('\n')

        #Career
        try:
            content=soup.find('div',id='filmography')
            l=[]
            for i in content.find_all('div',class_='head'):
                val=i.text.strip().replace('\xa0',' ').replace('\n',' ').replace('Hide','').replace('Show','').strip()
                l.append(val)

            data={}
            ctr=0
            l_val=[]
            for i in content.find_all('div',class_='filmo-category-section'):
                for j in i.find_all('div',class_='filmo-row odd'):
                    k=j.find('a')
                    k=k.text.replace('\xa0',' ').replace('\n',' ').strip()
                    l_val.append(k)

                for j in i.find_all('div',class_='filmo-row even'):
                    k=j.find('a')
                    k=k.text.replace('\xa0',' ').replace('\n',' ').strip()
                    l_val.append(k)

                data[l[ctr]]=l_val
                ctr=ctr+1
                l_val=[]

            for key, value in data.items():
                print(key, ' :\n ', value)
        except:
            print('\n')

        #Other Info
        try:
            classes=['details-other-works','details-publicity-listings','dyk-personal-quote','dyk-trivia','dyk-trademark']
            print('-----------------------------------\n\n')

            for c in classes:
                content=soup.find('div',id=c)
                b=content.text.strip().replace('\n','')
                b=' '.join(b.split())
                b=b.replace('See more »','')
                print(b)
            print('-----------------------------------\n\n')
        except:
            print('\n')

    return inp_name



# In[35]:


def run():
    inps=[]
    print('Enter Quit to stop')
    while True:
        c = int(input('1. Movie\n2. Star\n3. Quit\n'))

        if(c==1):
            inp = str(input('Enter movie/series/anime name:'))
        elif(c==2):
            inp = str(input('Enter actor/director name:'))
        elif(c==3):
            break
        else:
            print('Invalid Input')
            break

        if(inp.lower().strip()!='quit'):
            record=search[search['Input']==inp.lower().strip()]

            if(record.shape[0]==0):
                link=link_extract(inp)
                if(c==1):
                    inp_name,values=scrapper_media(link)
                    search.loc[len(search)]=[len(search),inp_name.lower().strip(),'Movie',link]
                    search_data.loc[len(search_data)]=values
                elif(c==2):
                    inp_name=scrapper_star(link)
                    search.loc[len(search)]=[len(search),inp_name.lower().strip(),'Star',link]

            else:
                link=record['IMDB Link'].tolist()[0]
                if(c==1):
                    try:
                        inp_name=scrapper_media(link)
                        search.loc[len(search)]=[len(search),inp_name.lower().strip(),'Movie',link]
                    except:
                        print('Invalid input')
                elif(c==2):
                    try:
                        inp_name=scrapper_star(link)
                        search.loc[len(search)]=[len(search),inp_name.lower().strip(),'Star',link]
                    except:
                        print('Invalid input')



            print('-----------------------------------------------------------------------------------------------')
            print('xx-----------xx-----------xx--------------xx-----------------xx-----------------xx-----------xx')
            print('xx-----------xx-----------xx--------------xx-----------------xx-----------------xx-----------xx')
            print('-----------------------------------------------------------------------------------------------')

            inps.append(inp_name)

        else:
            break

    user.loc[len(user)]=[len(user),inps]


# In[36]:


run()


# In[41]:


upload_firebase(search,'Search_Data',len(search_old))
upload_firebase(user,'User',len(user_old))
upload_firebase(search_data,'Scrapped_Data',len(search_data_old))
