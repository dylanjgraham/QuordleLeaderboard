# QuordleLeaderboard

This is a leaderboard for the game Quordle which can be found at https://www.quordle.com/#/

The code takes user input through an email share of the users results after they play the game (similar to how you would share your score with friends)

At 11:55 pm nightly the code checks for new emails, parses the email content to find the scores and adds the scores to the users running total.
If it is a new user it simply adds them to the list of players

After updating all the scores we then send an email with the current standings to all participants in the database

Lowest score wins at the end of the Week and all the scores are reset

Example email output:

<img width="396" alt="Example Email" src="https://user-images.githubusercontent.com/25232870/173972381-b323da94-05ce-444d-9e97-4e81792d4689.png">


