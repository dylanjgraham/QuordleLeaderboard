# QuordleLeaderboard

This is a leaderboard for the game Quordle which can be found at https://www.quordle.com/#/

The code takes user input through an email share of the users results after they play the game (similar to how you would share your score with friends)

At 11:55 pm nightly the code checks for new emails, parses the email content to find the scores and adds the scores to the users running total
  If it is a new user it simply adds them to the list of players

After updating all the scores we then send an email with the current standings to all participants in the database
