import QuordleEmailSender
import smtplib
import ssl
from email.message import EmailMessage
import unrevisioned
import emoji

PORT = 465  # For SSL

def truncateLeaderBoard():
    QuordleEmailSender.truncateLeaderboard()

def sendMailToMe():
    body = QuordleEmailSender.buildEmailContent()
    msg = EmailMessage()
    msg.set_content(body, subtype='html')

    msg['Subject'] = 'Score Update'
    msg['From'] = "Quordle Leaderboard <quordleleaderboard@gmail.com>"
    msg['Bcc'] = 'dylangraham97@gmail.com'

    # Create a secure SSL context
    context = ssl.create_default_context()
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE

    with smtplib.SMTP_SSL("smtp.gmail.com", PORT, context=context) as server:
        server.login("QuordleLeaderboard@gmail.com", unrevisioned.getPassword())
        server.send_message(msg)

if __name__ == '__main__':
    # getCredentials()
     sendMailToMe()
    # truncateLeaderBoard()