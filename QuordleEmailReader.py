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

        # Call the Gmail API to fetch INBOX
        results = service.users().messages().list(userId='me', labelIds=['INBOX']).execute()
        messages = results.get('messages', [])

        if not messages:
            print("No messages found.")
        else:
            print("Message snippets:")
            daysRemaining = QuordleEmailSender.getDaysRemaining()
            LatestQuordleDayInDB = -1
            if daysRemaining < 6:
                LatestQuordleDayInDB = getLatestQuordleDayInDB()
            for message in messages:
                msg = service.users().messages().get(userId='me', id=message['id']).execute()
                logging.debug("Found Message ID: " + message['id'])
                if isNewMessage(msg):
                    print(msg['snippet'] + '\n\n')
                    parsedMessage = parseSnippet(msg['snippet'])
                    if parsedMessage != -1:
                        todaysScore = parsedMessage[0]
                        quordleDay = parsedMessage[1]
                        if (LatestQuordleDayInDB != -1) and (int(quordleDay) - LatestQuordleDayInDB > 1):
                            QuordleEmailSender.sendMailToMe("Someone tried to submit early. I am ignoring this email with quordle day " + quordleDay)
                        else:
                            emojiScore = str(parsedMessage[2]) + '<br>' + str(todaysScore)
                            logging.debug("todaysScore: %s quordleDay: %s" % (todaysScore, quordleDay))
                            fromEmail = findFromEmail(msg['payload']['headers'])
                            if fromEmail == "":
                                QuordleEmailSender.sendMailToMe("Could not find the email address for this message \n " + msg['snippet'])
                                break
                            storeScore(todaysScore, fromEmail, quordleDay, emojiScore)
                            storeEmailID(msg)
                    else:
                        QuordleEmailSender.sendMailToMe("The following email was ignored \n " + msg['snippet'])
                else:
                    print("Read an old message so we are stopping")
                    logging.debug("Read an old message so we are stopping")
                    break

    except HttpError as error:
        # TODO(developer) - Handle errors from gmail API.
        print(f'An error occurred: {error}')

        # Send myself the error message
        QuordleEmailSender.sendMailToMe(str(error))


# Parse the email for the 4 emojis that contain the score.
def parseSnippet(msg):
    totalScore = 0
    splitMsg = msg.split()
    # check to see if there was any email content to parse
    if splitMsg:
        if (splitMsg[0] == 'Daily' and splitMsg[1] == 'Quordle'):
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
        elif splitMsg[1] == 'Daily' and splitMsg[2] == 'Quordle':
            topEmojiScore = splitMsg[4]
            bottomEmojiScore = splitMsg[5]
            fourEmojiScore = topEmojiScore + bottomEmojiScore
            for ii in fourEmojiScore:
                num = ii
                if num.isnumeric():
                    print(num)
                    totalScore += int(num)
                elif emoji.demojize(num) == ':red_square:':
                    totalScore += 13
            return totalScore, splitMsg[3], topEmojiScore + '<br>' + bottomEmojiScore
            
        else:
            print('Email didn\'t start with Quordle and is not being read further ')
            return -1
    else:
        print('Email had no parseable content?')
        return -1

def storeScore(todaysScore, email, quordleDay, emojiScore):
    dbRow = getCurrentScoreRecord(email)
    if dbRow:
        currentScore = dbRow[2]
        existingQuordleDay = dbRow[3]
        if existingQuordleDay == quordleDay:
            # Looks like they tried to upload the same days score twice. we dont want to accidentally double their score so we will not store this score
            QuordleEmailSender.sendMailToMe('We have encountered a duplicate email for quordleDay ' + quordleDay + '. This email was ignored')
        else:
            ID = dbRow[0]
            newScore = currentScore + todaysScore
            sql = 'UPDATE LEADERBOARD SET TOTAL_SCORE = ' + str(newScore) + ', YESTERDAY_SCORE =' + str('\"' + emojiScore + '\"') + ', ProtocolTypeID = ' + str(quordleDay) + ' WHERE ID = ' + str(ID)
            with CON:
                CON.execute(sql)
    else:
        daysRemaining = QuordleEmailSender.getDaysRemaining()
        penalty = calculateMidWeekAdditionPointPenalty(daysRemaining)
        penaltyMarker = ""
        if penalty > 0:
            penaltyMarker = "**"
        sql = 'INSERT INTO LEADERBOARD (EMAIL, TOTAL_SCORE, ProtocolTypeID, YESTERDAY_SCORE) values(?, ?, ?, ?)'
        data = [
            (email, todaysScore + penalty, quordleDay, str(emojiScore + penaltyMarker))
        ]
        with CON:
            CON.executemany(sql, data)
            
# Penalty is set as if they got 4 red squares for each day they missed
def calculateMidWeekAdditionPointPenalty(daysRemaining):
    penalty = 52 * (6 - daysRemaining)
    return penalty

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

# The Return-Path comes in at different indexes seemingly dependent on which email
# client is used to send it as well as android vs iphone so we must search the headers for the field
def findFromEmail(headersList):
    for dict in headersList:
        if dict['name'] == 'Return-Path':
            return dict['value']
    return ""


def getLatestQuordleDayInDB():
    with CON:
        data = CON.execute("SELECT MAX(ProtocolTypeID) AS today FROM LEADERBOARD")
        for val in data:
            return int(val[0])


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

        # CON.execute("""
        #     CREATE TABLE HISTORIC_WINS (
        #         ID INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
        #         EMAIL TEXT,
        #         NUM_WINS INTEGER
        #     );
        # """)


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

        #CON.execute("DELETE from LEADERBOARD where ID = 7")
        CON.execute("UPDATE LEADERBOARD SET EMAIL = '<dylangraham97@gmail.com>' where ID = 9")



# TODO send emails individually



if __name__ == '__main__':
    # Uncomment if this is the first time running the project and you dont have a QuoprdleLeaderBoard.db in the project directory
    # setupDB()
    main()
    penalizeNonPlayers()
    QuordleEmailSender.sendEmail()
