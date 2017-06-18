__author__ = 'divyansh'
__author__ = 'DIVYANSH'
import urllib2
import json
import os
from pymongo import MongoClient
#get current working directory
path=os.getcwd()
apikey=open(path+'//api.txt','r')
#read your YOUTUBE API key from a file
API_KEY=apikey.read()
apikey.close()
#logs file
#here are some encoding schemes ,metainformation that may be required for getting youtube data in JSON format 
hdr = {'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.11 (KHTML, like Gecko) Chrome/23.0.1271.64 Safari/537.11',
	   'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
	   'Accept-Charset': 'ISO-8859-1,utf-8;q=0.7,*;q=0.3',
	   'Accept-Encoding': 'none',
	   'Accept-Language': 'en-US,en;q=0.8',
	   'Connection': 'keep-alive'}
"""
This function checks if the video is availaible in your country or region
returns true if available else returns false
"""
def is_video_available(vid):
	reqstr='https://www.googleapis.com/youtube/v3/videos?part=id&id='+vid+'&key='+API_KEY
	#print reqstr
	stats_json=urllib2.urlopen(reqstr).read()
	stats=json.loads(stats_json)
	totalResults=stats["pageInfo"]["totalResults"]
	if totalResults==0 :
		return False
	else:
		return True
"""
This function returns the commentcount,viewcount,like and dislike count ,video publishing date and its title.
"""
def get_stats(vid):
	reqstr='https://www.googleapis.com/youtube/v3/videos?part=statistics%2Csnippet&id='+vid+'&key='+API_KEY
	#print reqstr
	stats_json=urllib2.urlopen(reqstr).read()
	stats=json.loads(stats_json)
	try:
		video_publishedAt=stats["items"][0]["snippet"]["publishedAt"].split('T')[0] # only want date not time so split.format : 2016-09-12T04:43:14.000Z
	except:
		video_publishedAt="empty"
	try:
		video_title=stats["items"][0]["snippet"]["title"]
	except:
		video_title="empty"
	try:
		viewCount=stats["items"][0]["statistics"]["viewCount"]		
	except:
		viewCount=0
	try:
		likeCount=stats["items"][0]["statistics"]["likeCount"]		
	except:
		likeCount=0
	try:
		dislikeCount=stats["items"][0]["statistics"]["likeCount"]		
	except:
		dislikeCount=0
	try:
		commentCount=stats["items"][0]["statistics"]["commentCount"]
	except:
		commentCount=0
	return viewCount,likeCount,dislikeCount,commentCount,video_publishedAt,video_title""
"""
New Youtube API v3 does not sends a single json containing all the comments and replies.
At max only 100 results per page can be requested.If more results are required a pageToken is generated 
which can be used further to get another page of results.This function initiates the connection
by fetching 100 results or maximum results(if comments are less than 100).
"""
def init(maxres,vid,nextPageToken):
	if not nextPageToken:
		request_str='https://www.googleapis.com/youtube/v3/commentThreads?part=id%2Csnippet%2Creplies&maxResults='+str(maxres)+'&videoId='+vid+'&key='+API_KEY
	else:
	   request_str='https://www.googleapis.com/youtube/v3/commentThreads?part=id%2Csnippet%2Creplies&maxResults='+str(maxres)+'&pageToken='+nextPageToken+'&videoId='+vid+'&key='+API_KEY
	print request_str
	json_string=urllib2.Request(request_str,headers=hdr)
	json_string=urllib2.urlopen(json_string,timeout=5).read()
	data=json.loads(json_string)
	totalResults=data["pageInfo"]["totalResults"]
	resultsPerPage=data["pageInfo"]["resultsPerPage"]
	try :
	   #print 'i m here'
	   nextPageToken=data["nextPageToken"]
	except:
		#print 'no i m here'
		nextPageToken=''
	comment,publishedAt=[],[]
	for i in range(totalResults):
		#use extend instead of append to extend the list elements instead of appending the whole objects
		comment.append(data["items"][i]["snippet"]["topLevelComment"]["snippet"]["textDisplay"])
		publishedAt.append(data["items"][i]["snippet"]["topLevelComment"]["snippet"]["publishedAt"].split('T')[0])
		totalReplyCount=data["items"][i]["snippet"]["totalReplyCount"]
		#print totalReplyCount
		if totalReplyCount>0:
			try:
				repl=data["items"][i]["replies"]
				var=0
				while var<len(repl):
					comment.append(data["items"][i]["replies"]["comments"][var]["snippet"]["textDisplay"])
				#split the published at,we only want date! format:2016-09-12T04:43:14.000Z
					publishedAt.append(data["items"][i]["replies"]["comments"][var]["snippet"]["publishedAt"].split('T')[0])
					var=var+1
			except:
				#print 'in except of replies'
				continue

	return nextPageToken,comment,publishedAt
"""
This function gets all the comments and replies.stores comment text and time of its publishing as a python tuple.
"""
def get_all_comments(vid):
	maxres=100
	nextPageToken=''
	nextPageToken,comment,publishedAt=init(maxres,vid,nextPageToken)
	all_comments,all_timestamps=[],[]
	all_comments.extend(comment),all_timestamps.extend(publishedAt)
	#print nextPageToken
	"""
	#comment_str='\n'.join(comment)
	#time_str='\n'.join(publishedAt) used for debugging purposes to print to the the text file
	"""

	while nextPageToken:
		nextPageToken,comment,publishedAt=init(maxres,vid,nextPageToken)
		all_comments.extend(comment),all_timestamps.extend(publishedAt)
		#comment_str=comment_str+'\n'.join(comment)
		#time_str=time_str+'\n'.join(publishedAt)
	#These two strings are encoding the utf-8 to ASCII in case we want to see the output as text
	#comment_str=comment_str.encode('ascii','ignore')
	#time_str=time_str.encode('ascii','ignore')
   # f=open('neww.txt','w')
   # f.write(comment_str+'\n'+time_str)
   #f.write(viewCount+likeCount+dislikeCount+commentCount)
   # f.close()
	comment_time_tuple=zip(all_comments,all_timestamps)
	return comment_time_tuple
"""
This function inserts the stats and comments into mongo db.
Takes two parameters 
1.movie_name : string containing the name of movie or episode or song or any youtube url
2.full_youtube_id : full youtube link/URL
"""
def insert_in_db(movie_name,full_youtube_id):
	log=open(path+'//comment_log.txt','a')
	#supports shortened youtu.be URL
	client = MongoClient()
	try :
		if "youtu.be" in full_youtube_id :
			vid=full_youtube_id.split('/')[3]
		else :
			vid=full_youtube_id.split('=')[1]
		if is_video_available(vid):
			viewCount,likeCount,dislikeCount,commentCount,video_publishedAt,video_title=get_stats(vid)
			if commentCount == 0:
				log.write(movie_name+' Comments are disabled for this video')
			else:
				comment_time_tuple=get_all_comments(vid)
        #this is name of your mongo db and fullcomments is the name of collection in the db
				db = client.movies
				post = {"name":movie_name, "comments":comment_time_tuple, "commentCount" : str(commentCount),"viewCount":str(viewCount),"likeCount":str(likeCount),"dislikeCount":str(dislikeCount),"video_publishedAt":video_publishedAt,"video_title":video_title}
				try:
				 	testid = db.fullcomments.insert_one(post)
				 	print movie_name+' done'
				 	log.write( movie_name+" Insert Done!!!\n")
				except :
				 	print movie_name+' not done'
				 	log.write(movie_name+" An error inserting into mongoDb has been occurred")
	except :
		log.write(movie_name+" This movie does not contain youtube trailer link\n")
	client.close()
	log.close()

	
