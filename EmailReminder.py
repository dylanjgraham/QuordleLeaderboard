import os.path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import logging
import emoji
import sqlite3 as sl

SCOPES = ['https://www.googleapis.com/auth/gmail.readonly', 'https://www.googleapis.com/auth/gmail.send']
CON = sl.connect('QUORDLE_LEADERBOARD.db')

def main():
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

        if not messages:
            print("No messages found.")
        else:
            print("Message snippets:")
            currentPlayers = getCurrentPlayers()
            for message in messages:
                msg = service.users().messages().get(userId='me', id=message['id']).execute()
                logging.debug("Found Message ID: " + message['id'])
                if isNewMessage(msg):
                    for player in currentPlayers:
                        if msg['payload']['headers'][15]['name'] == 'Return-Path':
                            fromEmail = msg['payload']['headers'][15]['value']
                        else:
                            fromEmail = msg['payload']['headers'][6]['value']
                        if player == fromEmail:
                            currentPlayers.remove(player)
                            break;
                else:
                    print("Read an old message")
                    logging.debug("Read an old message; Anyone left in currentPlayers list has not sent in a quordle yet today")
                    
                    if len(currentPlayers) > 0:
                      body = 'It looks like you may have forgotten to send in your Quordle Email today! \n \n Be sure to send it in before 11:55 pm tonight!'
                      msg = EmailMessage()
                      msg.set_content(body, subtype='html')

                      msg['Subject'] = 'Quordle Reminder'
                      msg['From'] = "Quordle Leaderboard <quordleleaderboard@gmail.com>"
                      msg['To'] = currentPlayers
                      logging.debug("Email Recipients of reminder email: " + str(currentPlayers))

                      # Create a secure SSL context
                      context = ssl.create_default_context()
                      context.check_hostname = False
                      context.verify_mode = ssl.CERT_NONE

                      with smtplib.SMTP_SSL("smtp.gmail.com", PORT, context=context) as server:
                          server.login("QuordleLeaderboard@gmail.com", unrevisioned.getPassword())
                          server.send_message(msg)
                          print("Reminder Email Sent")
                          server.quit()
                  else:
                      print("Everyone already sent in their quordle score today")
                        
                       
    except HttpError as error:
        # TODO(developer) - Handle errors from gmail API.
        print(f'An error occurred: {error}')
        logging.error('Likely bad credentials ' + error)

        
        
def isNewMessage(msg):
    with CON:
        data = CON.execute("SELECT * FROM READ_EMAILS WHERE GMAIL_ID = '" + msg['id'] + "'")
        for row in data:
            return False
        return True

def getCurrentPlayers():
    players = []
    with CON:
        data = CON.execute("SELECT DISTINCT EMAIL FROM LEADERBOARD")
        for row in data:
            players.append(str(row))
        return players
                
        
