from celery import Celery 
import requests
import shutil
import os
import subprocess as subp

import tweepy;
from tweepy import OAuthHandler
from tweepy import Stream
import json
import random

celeryapp = Celery ('gpucelery', broker='amqp://guest@localhost')

def deep_search(needles, haystack):
    found = {}
    if type(needles) != type([]):
        needles = [needles]

    if type(haystack) == type(dict()):
        for needle in needles:
            if needle in haystack.keys():
                found[needle] = haystack[needle]
            elif len(haystack.keys()) > 0:
                for key in haystack.keys():
                    result = deep_search(needle, haystack[key])
                    if result:
                        for k, v in result.items():
                            found[k] = v
    elif type(haystack) == type([]):
        for node in haystack:
            result = deep_search(needles, node)
            if result:
                for k, v in result.items():
                    found[k] = v
    return found

# only support for jpg and png for now
def validPictureFormat (filename):
    filename = filename.lower ()
    if filename[-4:] == ".jpg" or filename[-5:] == ".jpeg" or filename[-4:] == ".png":
        return True
    return False

def getFileType (filename):
    filename = filename.lower ()
    if filename[-4:] == ".jpg" or filename[-5:] == ".jpeg":
        return 'jpg'
    elif filename[-4:] == ".png":
        return 'png'
    else:
        return 'invalidformat'


@celeryapp.task
def Twitter_ToGPU_paint (tweepyapi, payload):
        paintingdir="/home/kbhit/git/neural-style/me-myself-ai/paintings/forslackbot/"
        neuralstylistscript = "/home/kbhit/git/neural-style/NeuroStylist_forSlack.sh"
        finalpainting="/home/kbhit/git/neural-style/me-myself-ai/paintings/forslackbot/montage_finaloutput.jpg"

        json_data= json.loads(payload)
        print(payload)

        findme = deep_search(["media_url"], json_data)
        if 'media_url' in findme:
           painturl = findme['media_url']
           if (validPictureFormat (painturl) == True):
              print ("going to paint URL %s: " % (findme['media_url']))
              filetype = getFileType (painturl);

              # start with a fresh input/output directory
              if (os.path.isdir (paintingdir)):
                  shutil.rmtree (paintingdir) # remove directory
                  print ("removing directory, it already exists");
              os.makedirs (paintingdir) # make the same directory
              
              # download original slack image
              inputimage = "%s/slackinput.%s" % (paintingdir, filetype);
              response = requests.get(painturl, stream=True)
              with open (inputimage, 'wb') as out_file:
                  shutil.copyfileobj (response.raw, out_file)
              # lets paint
              subp.call (["/bin/bash", neuralstylistscript, inputimage, '/home/kbhit/git/neural-style/me-myself-ai/styles/Picasso.jpg'])
   
              tweeter_name = json_data['user']['screen_name']
              status = "(@%s thanks for the mention and random number %f" % (tweeter_name, random.random())
              tweepyapi.update_with_media(finalpainting, status=status)
   

@celeryapp.task
def ToGPU_paint (token, channelid, userid, commandtext, downloadurl, filetype):
    # config
    paintingdir="/home/kbhit/git/neural-style/me-myself-ai/paintings/forslackbot/"
    finalpainting="/home/kbhit/git/neural-style/me-myself-ai/paintings/forslackbot/montage_finaloutput.jpg"
    neuralstylistscript = "/home/kbhit/git/neural-style/NeuroStylist_forSlack.sh"
    stylemapperdict = { 'paint monet': '/home/kbhit/git/neural-style/me-myself-ai/styles/Monet.jpg',
                        'paint picasso': '/home/kbhit/git/neural-style/me-myself-ai/styles/Picasso.jpg',
                        'paint afremov': '/home/kbhit/git/neural-style/me-myself-ai/styles/LeonidAfremov.jpg',
                        'paint van gogh': '/home/kbhit/git/neural-style/me-myself-ai/styles/VincentvanGogh.jpg' };

    # start with a fresh input/output directory
    if (os.path.isdir (paintingdir)):
        shutil.rmtree (paintingdir) # remove directory
        print ("removing directory, it already exists");
    os.makedirs (paintingdir) # make the same directory

    # download original slack image
    inputimage = "%s/slackinput.%s" % (paintingdir, filetype);
    response = requests.get(downloadurl, headers={'Authorization': "Bearer %s" % (token)}, stream=True)
    with open (inputimage, 'wb') as out_file:
        shutil.copyfileobj (response.raw, out_file)

    # lets paint
    subp.call (["/bin/bash", neuralstylistscript, inputimage, stylemapperdict[commandtext]])

    # give results
    message = "I just finished my painting <@%s|cal>, how do you like my painting?  I used my Neural Network from the VGG19 ConvNet and NeuralStyle algorithm to paint this.  All neuron computations occurred on our teams GPU server - please consider donating!" % (userid);
    f = {'file': (finalpainting, open(finalpainting, 'rb'), 'image/png', {'Expires':'0'})}
    response = requests.post (url='https://slack.com/api/files.upload', data = {'token': token, 'channels': channelid, 'initial_comment': message, 'media': f}, headers={'Accept': 'application/json'}, files=f)
    return commandtext;

@celeryapp.task
def ToGPU_daydream (token, channelid, userid, commandtext, downloadurl, filetype):
    # config
    paintingdir="/home/kbhit/git/deepdream/paintings_forslackbot/"
    finalpainting="/home/kbhit/git/deepdream/paintings_forslackbot/montage_finaloutput.jpg"
    thescript = "/home/kbhit/git/PainterBot/Features/DeepDream/DeepDream_forSlack.sh"

    # start with a fresh input/output directory
    if (os.path.isdir (paintingdir)):
        shutil.rmtree (paintingdir) # remove directory
        print ("removing directory, it already exists");
    os.makedirs (paintingdir) # make the same directory

    # download original slack image
    inputimage = "%s/slackinput.%s" % (paintingdir, filetype);
    response = requests.get(downloadurl, headers={'Authorization': "Bearer %s" % (token)}, stream=True)
    with open (inputimage, 'wb') as out_file:
        shutil.copyfileobj (response.raw, out_file)

    # lets paint
    subp.call (["/bin/bash", thescript, inputimage])

    # give results
    message = "I just finished daydreaming <@%s|cal>, was I having a nightmare?  I used google's deepdream algorithm for this.  All neuron computations occurred on our teams GPU server - please consider donating!" % (userid);
    f = {'file': (finalpainting, open(finalpainting, 'rb'), 'image/png', {'Expires':'0'})}
    response = requests.post (url='https://slack.com/api/files.upload', data = {'token': token, 'channels': channelid, 'initial_comment': message, 'media': f}, headers={'Accept': 'application/json'}, files=f)
    return commandtext;

@celeryapp.task
def ToGPU_guesspicture (token, channelid, userid, downloadurl, filetype):
    # config
    scriptrundir="/home/kbhit/git/dml-chatbot/vgg16-guesspicture/outfiles/"
    scriptresults="/home/kbhit/git/dml-chatbot/vgg16-guesspicture/outfiles/guesses.txt"
    scriptfile = "/home/kbhit/git/dml-chatbot/vgg16-guesspicture/guesspicture_vgg16.py"

    # start with a fresh input/output directory
    if (os.path.isdir (scriptrundir)):
        shutil.rmtree (scriptrundir) # remove directory
        print ("removing directory, it already exists");
    os.makedirs (scriptrundir) # make the same directory

    # download original slack image
    inputimage = "%s/slackinput.%s" % (scriptrundir, filetype);
    response = requests.get(downloadurl, headers={'Authorization': "Bearer %s" % (token)}, stream=True)
    with open (inputimage, 'wb') as out_file:
        shutil.copyfileobj (response.raw, out_file)

    # lets paint
    subp.call (["python", scriptfile, inputimage])

    # give results
    guessresults = [line.rstrip('\n').split ("\t") for line in open(scriptresults)]
    print (guessresults);
    message = "Here are my 3 guesses (with confidence levels) on what the picture is <@%s|cal>.\nGuess 1: %s (%.02f%%)\nGuess 2: %s (%.02f%%)\nGuess 3: %s (%.02f%%)\nHow did I do?  Remember I'm only as good as the training data used during my questionable upbringing (ImageNet VGG16 ConvNet brain).  All neuron computations occurred on our teams GPU server - please consider donating!" % (userid, guessresults[0][0], float (guessresults[0][1])*100, guessresults[1][0], float (guessresults[1][1])*100, guessresults[2][0], float (guessresults[2][1])*100);

    payload = {'token': token, 'channel': channelid, 'text': message};
    response = requests.post(url='https://slack.com/api/chat.postMessage', data=payload);

    return True;
