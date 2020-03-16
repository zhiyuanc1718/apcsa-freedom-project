# Entry 05
##### 3/15/20

## Recap from previous entry...

Some new ideas that I considered :
- Due to redundancy in code, I wanted to make a method that determines whether a ship would move or not based on a variety of situations
- We also wanted to consider the enemy's ships and avoid collisions with them unless it is ideal to do so (such as a 100 halite ship from our side crashing into an enemy's ship with 1000 halite). In that case, we will need to adapt our destination methods to something more like "head to direction" rather than destinations...

## Engineering Design Process

Our progress with the Freedom Project is between **creating a prototype** with Machine Learning and **testing and evaluate the prototype** (same as previous entry which is running a model against previous models, other player's bots, and fighting itself) and lastly **improve as needed** (better algorithms which I will address partially in this entry with some new methods).

Here, I will discuss about a new prototype and a new way of navigation that would work ideally but not in code (some debugging needed).

## Knowledge

While learning about `private` and `public` variables in java, I could see how python classes and objects are different than java objects. `private` does not exist in python and instead of making accessor methods in python, we can simply use the `.` symbol to access variables of an object such as Position.x where Position is an instance of the class with some values stored as x and y.

With java, we apply the `new` keyword to make a new instance of the class, but in python we don't use the `new` keyword.

Instead of
```java
class Position {
    private int x;
    private int y;
    public Position(int px, int py){
        x = px;
        y = py;
    }

    public int getX(){
        return x;
    }

    //etc
}

Position p = new Position(3,4)
p.getX()    //returns 3

```

here's python
```python
class Position:
    def __init__(self, x, y):
        self.x = x
        self.y = y

p = Position(3,4)
p.x     # returns 3
```

These similarities allows me to understand python while I code (compiler will point out errors, and I'll fix them)
However due to the syntax simplicity, sometimes I will forget the data type of the variable which creates place for errors.

## Skills

Some skills that I further developed were my ability to research and google for new ideas. I approached [Halite forum](https://forums.halite.io/t/herd-behaviour-of-top-bots/1267.html) for new ideas to implement into my AI Bot. I looked through the forums and found a [game strategy page](https://forums.halite.io/c/game-strategy.html) made from many different contributors. The biggest skill I further developed while coding for this entry is logical reasoning. Despite my code essentially breaking my bot (more debugging for the next blog entry), my intention behind the new methods is to allow a ship to consider the larger picture and make moves accordingly.

## Bot Development

Version 04 : Not-Working-yet Bot (merge new ideas with previous bot)

So what happened ?
- Well, meanwhile Felix learns Machine Learning and begins the ML bot, I decided to scrap my previous model and make an entire new one, hoping that it will work. Unfortunately, I need to spend more time to figure out the issue to the weird behavior of my ships for the new model.

#### Step 1 : To move or not to move?

We can move all the time if we have enough halite. We need to know whether it is worth moving to a particular cell and take turns to mine some halite on that cell.

If you stay at a cell for n turns, for every turn you mine 1/4 of the available halite.

So in 2 turns, you will mine 1/4 of the original 100% and then 1/4 of the remaining 75%. Thus 0.25 + 0.1875 = 0.4375
You will realize the pattern. Percent gained for n turns = Sum of (1/4)(3/4)^(n-1) for n turns

```python
# param : ship = ship object from me.get_ships()
def wantToMove(ship):
    '''
    we will obviously not move if we do not have the resources to.
    '''
    if (ship.halite_amount < int(game_map[ship.position].halite_amount/constants.MOVE_COST_RATIO)):
        return False

    '''
    moving will reduce our ship's halite by 1/10 of x halite on the cell we're about to leave
    staying will increase our halite by 1/4 of x halite on cell we're on.
    We want to maximize halite. Stay if staying is better/necessary. Otherwise, move.
    '''

    '''
    Assuming we will keep moving, the net lost is 1/10 of all cells prior to destination
    any pause (mining) will reduce net lost by 1/4 of X cell's halite
    '''

    if ship_states[ship.id] == "navigating":
        totalLost = 0
        targetX = destinations[ship.id].x
        targetY = destinations[ship.id].y
        direction = [1,1]
        if targetX - ship.position.x < 0:
            direction[0] = -1
        if targetY - ship.position.y < 0:
            direction[1] = -1
        for i in range(abs(targetX - ship.position.x)):
            totalLost += constants.MOVE_COST_RATIO * game_map[ship.position + Position(direction[0] * i, 0)].halite_amount
        for j in range(abs(targetY - ship.position.y)):
            totalLost += constants.MOVE_COST_RATIO * game_map[ship.position + Position(0, direction[1] * j)].halite_amount

        # assume that we will mine for about 5 turns
        gainRatio = [0.25, 0.4375, 0.578125, 0.68359375, 0.7626953125]
        averageHalite = 0
        averageLost = 0
        surroundings = destinations[ship.id].get_surrounding_cardinals() + [destinations[ship.id]]
        for p in surroundings:
            averageHalite += game_map[p].halite_amount
            averageLost += game_map[p].halite_amount * constants.MOVE_COST_RATIO
        averageHalite = int(averageHalite/len(surroundings))
        for r in gainRatio:
            if r * averageHalite - averageLost > totalLost:
                return True
        # if the gain after 5 mining turns is less than the net lost during constant movement, consider pausing.
        profit = constants.EXTRACT_RATIO * game_map[ship.position].halite_amount
        moveCost = constants.MOVE_COST_RATIO * game_map[ship.position + Position(direction[0],0)].halite_amount + constants.MOVE_COST_RATIO * game_map[ship.position + Position(direction[0] * 2,0)].halite_amount + constants.MOVE_COST_RATIO * game_map[ship.position + Position(0,direction[1])].halite_amount + constants.MOVE_COST_RATIO * game_map[ship.position + Position(0,direction[1] * 2)].halite_amount
        if  profit > int(moveCost/4):
            return False
        return True
    else:
        if ship_states[ship.id] == "depositing":
            deposit = ship_deposits[ship.id]
            if not ship.halite_amount == 1000 and ship.halite_amount - constants.MOVE_COST_RATIO * game_map[ship.position].halite_amount <= 0.9 * deposit:
                return False
            return True
        else:
            return True
```

Let me explain what's going on above.
We calculate the net lost during the path taken to the destination (a very bad idea... as I realize the amount of code needed to predict the path taken and consider the amount of halite used up on the path). If a ship can gain more than the amount lost by the time it reach the destination cell (mining for 5 turns), then we would allow the ship to proceed without stopping to mine halite.

`return True` for if a ship has enough energy to move off the current cell and is actually worth moving
`return False` when out of energy and we need to collect more before heading towards destination


#### Step 2 : what about the enemies ?
Because we cannot predict where exactly the opponent's ships will be, let's just assume that every surrounding coordinate about an opponent's ship will be an "unsafe cell". That means we should always be at least one cell from the enemy's ships. (Unless we decided to attack, more on this in later blogs).

```python
def enemyPossiblePaths():
    positions = []
    for player in game.players:
        if player != me.id:
            for ship in game.players[player].get_ships():
                surroundings = ship.position.get_surrounding_cardinals() + [ship.position]
                for p in surroundings:
                    positions.append(p)
    return positions
```

#### Step 3 : Where to move ?

In collecting mode, we will just look around us and check the best cell to move, so we can `collect` more halite.

In navigation mode, a ship will just keep moving or staying still temporarily to collect enough halite to continue the trip.
Same applies to depositing mode.

```python
def directionToMove(ship, epos):
    '''
    Move only into "will-not-be-occipied cells"
    If both directions are not opened for navigation, consider moving somewhere else.

    Avoid a potential path of an enemy if our ship has X halite. Attack or proceed in the direction chosen if we have little halite compared to enemy.
    '''
    if ship_states[ship.id] == "collecting":
        directional_choice = direction_order[4]
        options = ship.position.get_surrounding_cardinals() + [ship.position]
        # pos = {(0, -1): Position(8, 15), (-1,0) : Position(7, 16) ...}
        # pos dictionary : maps direction (NSEW) to a Position(coordinate)
        pos = {}
        # energy dictionary : maps the direction choice with halite
        # energy = {(0, -1): 708, (0, 1): 492 ...}
        energy = {}
        for n, direction in enumerate(direction_order):
            pos[direction] = options[n]

        ### code not shown, essentially from the previous model
        if len(energy) > 0:
            directional_choice = max(energy, key=energy.get)
        return directional_choice
    else:
        directions = GameMap._get_target_direction(ship.position, destinations[ship.id])
        pos = ship.position
        directionalChoice = direction_order[4]
        for d in directions:
            if d is not None:
                pos = ship.position + Position(*d)
                if pos not in ship_coords.values() and pos not in epos:
                    directionalChoice = d
                    break
        if directionalChoice == Direction.Still:
            options = ship.position.get_surrounding_cardinals() + [ship.position]
            for n in len(options):
                pos = options[n]
                if pos not in ship_coords.values() and pos not in epos:
                    directionalChoice = d
                    break
        return directionalChoice
```
See full code in botVersions folder.
However, we need to look back at previous code and merge the new ideas with previous models. The most important thing is to have a working bot. More debugging for us ! Rubber duck debugging time!

Stay Tuned for the next bot version that WORKS!

[Previous](entry04.md) | [Next](entry06.md)

[Home](../README.md)
