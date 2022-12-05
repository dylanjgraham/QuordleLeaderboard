from __future__ import print_function

import os.path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import logging
import emoji
import sqlite3 as sl

# If modifying these scopes, delete the file token.json.
import QuordleEmailSender

SCOPES = ['https://www.googleapis.com/auth/gmail.readonly', 'https://www.googleapis.com/auth/gmail.send']
CON = sl.connect('QUORDLE_LEADERBOARD.db')
logging.basicConfig(filename='Quordle.log', encoding='utf-8', level = logging.DEBUG)

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
            for message in messages:
                msg = service.users().messages().get(userId='me', id=message['id']).execute()
                logging.debug("Found Message ID: " + message['id'])
                if isNewMessage(msg):
                    print(msg['snippet'] + '\n\n')
                    parsedMessage = parseSnippet(msg['snippet'])
                    if parsedMessage != -1:
                        todaysScore = parsedMessage[0]
                        quordleDay = parsedMessage[1]
                        emojiScore = parsedMessage[2]
                        logging.debug("todaysScore: %s quordleDay: %s" % (todaysScore, quordleDay))
                        if msg['payload']['headers'][15]['name'] == 'Return-Path':
                            fromEmail = msg['payload']['headers'][15]['value']
                        else:
                            fromEmail = msg['payload']['headers'][6]['value']
                        storeScore(todaysScore, fromEmail, quordleDay, emojiScore)
                        storeEmailID(msg)
                else:
                    print("Read an old message so we are stopping")
                    logging.debug("Read an old message so we are stopping")
                    break

    except HttpError as error:
        # TODO(developer) - Handle errors from gmail API.
        print(f'An error occurred: {error}')
        logging.error('Likely bad credentials ' + error)


# Parse the email for the 4 emojis that contain the score.
def parseSnippet(msg):
    totalScore = 0
    splitMsg = msg.split()
    if splitMsg[0] == 'Daily' and splitMsg[1] == 'Quordle':
        topEmojiScore = splitMsg[3]
        bottomEmojiScore = splitMsg[4]
        fourEmojiScore = topEmojiScore + bottomEmojiScore
        for ii in fourEmojiScore:
            num = ii
            if num.isnumeric():
                print(num)
                totalScore += int(num)
            elif emoji.demojize(num) == ':red_square:':
                totalScore += 13
        return totalScore, splitMsg[2], topEmojiScore + '<br>' + bottomEmojiScore
    else:
        print('Email didn\'t start with Quordle and is not being read further ')
        return -1

def storeScore(todaysScore, email, quordleDay, emojiScore, override = False):
    dbRow = getCurrentScoreRecord(email)
    if dbRow:
        currentScore = dbRow[2]
        ID = dbRow[0]
        newScore = currentScore + todaysScore
        sql = 'UPDATE LEADERBOARD SET TOTAL_SCORE = ' + str(newScore) + ', YESTERDAY_SCORE =' + str('\"' + emojiScore + '\"') + ', ProtocolTypeID = ' + str(quordleDay) + ' WHERE ID = ' + str(ID)
        with CON:
            CON.execute(sql)
    else:
        if QuordleEmailSender.getDaysRemaining() == 6 or override == True:
            sql = 'INSERT INTO LEADERBOARD (EMAIL, TOTAL_SCORE, ProtocolTypeID, YESTERDAY_SCORE) values(?, ?, ?, ?)'
            data = [
                (email, todaysScore, quordleDay, str(emojiScore))
            ]
            with CON:
                CON.executemany(sql, data)
        else:
            print(str(email) + " cannot be added mid week")
            logging.warning("user cannot be added mid week")
            


def getCurrentScoreRecord(email):
    with CON:
        data = CON.execute("SELECT * FROM LEADERBOARD WHERE EMAIL = '" + email + "'")
        for row in data:
            print(row)
            return row
        return None


def isNewMessage(msg):
    with CON:
        data = CON.execute("SELECT * FROM READ_EMAILS WHERE GMAIL_ID = '" + msg['id'] + "'")
        for row in data:
            return False
        return True


# store the emailID so that we know that one was read and we don't accidentally add its score again later
def storeEmailID(msg):
    sql = 'INSERT INTO READ_EMAILS (GMAIL_ID) values(?)'
    data = [
        (msg['id'],)
    ]
    with CON:
        CON.executemany(sql, data)


# if a player doesnt submit their score for the day they are given the maximum score as though they got 4 red squares
def penalizeNonPlayers():
    if QuordleEmailSender.getDaysRemaining() < 6:
        quordleDay = -1
        with CON:
            data = CON.execute("SELECT MAX(ProtocolTypeID) AS today FROM LEADERBOARD")
            for val in data:
                quordleDay = val
                logging.debug('Penalizing non-Players with QuordleDays less than %s' % (quordleDay))
        if quordleDay != -1 and isinstance(quordleDay[0], str):
            fourRedSquares = emoji.emojize(":red_square:") + emoji.emojize(":red_square:") + "<br>" + emoji.emojize(":red_square:") + emoji.emojize(":red_square:")
            with CON:
                CON.execute("UPDATE LEADERBOARD SET TOTAL_SCORE = TOTAL_SCORE + 52, YESTERDAY_SCORE = " + str('\"' + fourRedSquares + '\"') + ", ProtocolTypeID = " + str('\"' + quordleDay[0] + '\"') + " WHERE ProtocolTypeID < " + str(quordleDay[0]))


def setupDB():
    with CON:
        # CON.execute("""
        #     CREATE TABLE READ_EMAILS (
        #         ID INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
        #         GMAIL_ID TEXT
        #     );
        # """)
        # CON.execute("""
        #     CREATE TABLE LEADERBOARD (
        #         ID INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
        #         EMAIL TEXT,
        #         TOTAL_SCORE INTEGER,
        #         ProtocolTypeID TEXT,
        #         YESTERDAY_SCORE TEXT
        #     );
        # """)

        CON.execute("""
            CREATE TABLE HISTORIC_WINS (
                ID INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
                EMAIL TEXT,
                NUM_WINS INTEGER
            );
        """)
#         CON.execute("""
#                     ALTER TABLE LEADERBOARD
# RENAME COLUMN ProtocolTypeID TO QUORDLE_DAY;
#         """)

        # CON.execute("UPDATE LEADERBOARD SET EMAIL='<kengraham717@gmail.com>' where ID=3")

#         CON.execute("""INSERT INTO LEADERBOARD (EMAIL, TOTAL_SCORE, ProtocolTypeID, YESTERDAY_SCORE)
# VALUES ('<maddielum19@gmail.com>', '26', '111', '26');""")

        # CON.execute("""
        #             ALTER TABLE LEADERBOARD
        # ADD COLUMN YESTERDAY_SCORE INTEGER;
        #         """)

        # CON.execute("DELETE from LEADERBOARD where ID = 8")
        # CON.execute("UPDATE LEADERBOARD SET TOTAL_SCORE = 106 where ID = 3")



# TODO send emails individually



if __name__ == '__main__':
    # Uncomment if this is the first time running the project and you dont have a QuoprdleLeaderBoard.db in the project directory
    # setupDB()
    main()
    penalizeNonPlayers()
    QuordleEmailSender.sendEmail()
