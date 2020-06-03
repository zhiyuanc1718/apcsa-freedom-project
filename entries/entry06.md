# Entry 06
##### 6/2/20

## Recap from previous entry...

We have finally finished our MVP, which consisted of an algorithmic bot and a machine learning bot [see Feliz's blog](https://github.com/felixz2535/apcsa-freedom-project/blob/master/entries/entry06.md) and attempted to improve our product by adding interesting features.

Our current Engineering Design Process is communicating the results and improving the MVP with any additional features that could make our AI bot perform better.

We attempted to make a bot that could play against players who were pronounced rankings of "silver" and "gold". Most games resulted in our algorithmic bot losing, but our bot performed great in its consistency.

## The MVP

By looking for lines of code that I may have accidentally forgotten or deleted, I successfully fixed the errors from the previous blog. The MVP bot plays most games without "bad collisions" : when multiple ships collide but they had no intention to do so. This usually results in a negative net performance because it takes halite (the energy source) to build ships, and without ever bringing back the halite used to build the ships and have the ships crash into one another, this can make us lose the match.

Another feature of the MVP is its ability to dodge enemies by looking at the positions taken over by enemies and make sure that our ships do not go near them when we can avoid collisions. I found a basic description of this behavior from the [halite game strategy forum](https://forums.halite.io/t/avoid-collisions-with-other-players/1017.html) to verify that this strategy is effective. However, when a ship is surrounded and has a low number of halite, it's worth a try to set it on attack mode, and let it approach the enemies (the enemy has a 50% chance of moving away)

## Beyond MVP

A common feature of all top bots as I looked at their behavior on halite.io is the mass collision near the end of the game.

Notice that :
- it takes one turn to move
- each ship wants to deliver halite before the game is over
- There are 4 directions to reach one cell

Therefore...
The strategy is to crash ships at the end of the game in a group of 4 (one from each direction NSEW) thus saving 3 turns per ship and providing enough time to make sure every halite from every ship gets deposited. Whoever has more halite wins.

I also attempted to program a new bot hevaior : [the herd behavior (read more on halite forums)](https://forums.halite.io/t/herd-behaviour-of-top-bots/1267.html). This behavior is very powerful because when ships travel together as a group in one direction, they can easily clear out the map and destroy any enemies along the way. My attempt wasn't successful but I will continue to consider this strategy as opposed to my main strategy which relies on calculating best locations and sending small amounts of ships there to avoid crashing.

## AP CSA Java

Near the end of this project and the end of our AP CSA course, we focused on Free Response Questions (FRQs) to help prepare us for the AP exam. The FRQs focused on writing methods that requires at least one `for` loop. These practices were helpful to my project as I began to separate code into methods and utilize methods throughout the entire project. I figured that long chunks of code should most likely exist within a method and not the main body of the project that performs the task of giving the ships their instructions.

## What are my takeaways ?

I learned that success in a project with limited resources is very challenging, and we definitely need to embrace failures, a skill that I developed just by watching my bot time out or ships crash into one another. These failures tells me that somewhere in my thinking process could have gone wrong, so I would need to invest more time into planning. It is not easy to go through hours of debugging because revising long chunks of code takes time. You have to reread and check the code that you wrote down (comments are very important for this reason). The main skill I developed was debugging. From seeing errors probably more than at least a hundred times, whenever an error (displayed in red on my running terminal) pops up, I can easily understand what exactly went from and fix it within 1 minute or less.

## Games

- Battle 1 (Lost) Our bot vs Gold player
- Battle 2 (Won) Gold Player bot's algorithms failed?
- Battle 3 (2nd, 3rd) Two copies of our bot playing against the Gold-ranked player and a Silver-ranked player with herd strategy

If you want to see these recorded games, click [here](../videos.html)

[Previous](entry05.md) | [Next](entry07.md)

[Home](../README.md)