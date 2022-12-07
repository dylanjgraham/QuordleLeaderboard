import QuordleEmailReader

import os.path
import emoji

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import sqlite3 as sl

SCOPES = ['https://www.googleapis.com/auth/gmail.readonly', 'https://www.googleapis.com/auth/gmail.send']
CON = sl.connect('QUORDLE_LEADERBOARD.db')



def testStoreScore():
    #QuordleEmailReader.storeScore(52, '<dylangraham97@gmail.com>', 201, 'manual', True)
    QuordleEmailReader.storeScore(157, '<maddielum19@gmail.com>', 171, 'manual')
    QuordleEmailReader.storeScore(187, '<dylangraham97@gmail.com>', 171, 'manual')
    QuordleEmailReader.storeScore(170, '<kengraham717@gmail.com>', 171, 'manual')

def setPlayerScore():
    with CON:
        CON.execute("UPDATE LEADERBOARD SET TOTAL_SCORE = 119 where ID = 8")

def testEmojize():
    with CON:
        CON.execute("UPDATE LEADERBOARD SET TOTAL_SCORE = 106 where ID = 3")
    
def removeEmailIds():
    with CON:
        CON.execute("DELETE from READ_EMAILS where ID = 132")

def getCredentials():
    creds = None
    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open('token.json', 'w') as token:
            token.write(creds.to_json())

    try:
        # Call the Gmail API
        service = build('gmail', 'v1', credentials=creds)
        results = service.users().labels().list(userId='me').execute()
        labels = results.get('labels', [])

        # Call the Gmail API to fetch INBOX
        results = service.users().messages().list(userId='me', labelIds=['INBOX']).execute()
        messages = results.get('messages', [])

        if not  messages:
            print("No messages found.")
        else:
            print("Good connection")

    except HttpError as error:
        # TODO(developer) - Handle errors from gmail API.
        print(f'An error occurred: {error}')


if __name__ == '__main__':
    #getCredentials()
    #removeEmailIds()
    #testEmojize()
    setPlayerScore()
    #testStoreScore()