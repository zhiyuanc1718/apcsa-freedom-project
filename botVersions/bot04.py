import hlt

# This library contains constant values.
from hlt import constants

# This library contains direction metadata to better interface with the game.
from hlt.positionals import Direction
from hlt.positionals import Position
from hlt.game_map import GameMap

# This library allows you to generate random numbers.
import random
import math
# Logging allows you to save messages for yourself. This is required because the regular STDOUT
#   (print statements) are reserved for the engine-bot communication.
import logging

""" <<<Game Begin>>> """

# This game object contains the initial game state.
game = hlt.Game()
# At this point "game" variable is populated with initial map data.
# This is a good place to do computationally expensive start-up pre-processing.
# As soon as you call "ready" function below, the 2 second per turn timer will start.
game.ready("TrialBot04")

# Now that your bot is initialized, save a message to yourself in the log file with some important information.
# Here, you log here your id, which you can always fetch from the game object by using my_id.
logging.info("Successfully created bot! My Player ID is {}.".format(game.my_id))

# You extract player metadata and the updated map metadata here for convenience.
me = game.me
game_map = game.game_map

# Variables related to player/game state
maxTurnDict = {64:500, 56:475, 48:450, 40:425, 32:400}
maxTurns = maxTurnDict[game_map.width]
maxHalite = 0
direction_order = [Direction.North, Direction.South, Direction.East, Direction.West, Direction.Still]

# related to ships
zones = {}                  # maps zone highest density position to total halite in zone of size 8
ship_states = {}            # ship.id map to game mode
ship_coords = {}            # ship.id map to coordinate
ship_deposits = {}          # ship.id map to theoretical deposit
destinations = {}           # ship.id map to destination
destinationList = []
avoidCoords = []            # No ships are allowed to step upon these coordinates
shipCount = 0

# sets no-go-zone to be within a radius of 2 of any enemy shipyards
for player in game.players:
    if player != me.id:
        for i in range(game.players[player].shipyard.position.x-2, game.players[player].shipyard.position.x+3):
            for j in range(game.players[player].shipyard.position.y-2, game.players[player].shipyard.position.y+3):
                avoidCoords.append(Position(i,j))

# update no-go-zone for any enemy dropoffs
def updateAvoid():
    for player in game.players:
        if player != me.id:
            for dropoff in game.players[player].get_dropoffs():
                if dropoff.position not in avoidCoords:
                    avoidCoords.append(dropoff.position)

# returns the amount of halite available on this map
def haliteInMap():
    halite = 0;
    for y in range(0, game_map.height, 8):
        for x in range(0, game_map.width, 8):
            gridSum = 0
            highest = Position(x,y)
            for j in range(y, y+8):
                for i in range(x, x+8):
                    gridSum += game_map[Position(i,j)].halite_amount
                    if game_map[Position(i,j)].halite_amount > game_map[highest].halite_amount:
                        highest = Position(i,j)
            halite += gridSum
            zones.update({highest: gridSum})
    return halite

# returns the closest dropoff including shipyard for a ship
# param : pos = current position of object
def nearestBase(pos):
    drops = []
    for dropoff in me.get_dropoffs():
        drops.append(dropoff.position)
    minDis = game_map.calculate_distance(pos, me.shipyard.position)
    droplocation = me.shipyard.position
    for drop in drops:
        distance = game_map.calculate_distance(pos, drop)
        if distance < minDis:
            minDis = distance
            droplocation = drop
    return droplocation

# returns boolean as to if ship would move prior to making all moves for the turn
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

# Each enemy ship "can" move in 4 directions or stay still. For the sake of ultimate safety, we want to make sure there's a 0% chance of collision with the enemy unless otherwise (later planning for attack). Make sure we know all the possible positions of enemy's ships.
# returns a super long list of positions of all enemy ships
def enemyPossiblePaths():
    positions = []
    for player in game.players:
        if player != me.id:
            for ship in game.players[player].get_ships():
                surroundings = ship.position.get_surrounding_cardinals() + [ship.position]
                for p in surroundings:
                    positions.append(p)
    return positions

# apply method when wantToMove() returns True
# return the optimal direction to move, which includes staying still.
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

        for direction in pos:
            # position will be a coordinate
            position = pos[direction]
            halite_amount = game_map[position].halite_amount
            # the position of the direction we are planning to move will not be taken over by another ship
            # we will consider each of the available directions for movement
            if pos[direction] not in ship_coords.values() and pos[direction] not in epos:
                # we prefer to stay still to collect remaining halite
                if direction == Direction.Still:
                    halite_amount *= len(me.get_ships())
                    energy[direction] = halite_amount
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
            for d in options:
                pos = ship.position + Position(*d)
                if pos not in ship_coords.values() and pos not in epos:
                    directionalChoice = d
                    break
        return directionalChoice

def setNewDestination(ship):
    # if we want to deposit, all we need is a dropoff or the shipyard. we find the closest one
    if ship_states[ship.id] == "depositing":
        destination = nearestBase(ship.position)
        return destination

    # if we want to collect halite, then we must find the highest score areas
    else:
        scores = {}
        shipDestinations = []
        for p,h in zones.items():
            if p not in destinations.values():
                score = h / (game_map.calculate_distance(ship.position, p) + game_map.calculate_distance(p, nearestBase(p)))
                scores.update({p : score})
        maxScore = max(scores.values())
        for k,v in scores.items():
            if v == maxScore:
                shipDestinations.append(k)
        return shipDestinations[0]

maxHalite = haliteInMap()

# writing files
f = open("gameinfo" + str(game.my_id) + ".txt","w+")
f.write("Total Halite in game map = " + str(maxHalite) + "\n")
f.write("My ships will avoid the following coordinates \n")
for coords in avoidCoords:
    f.write(str(coords) + "\n")
shipyards = []
for player in game.players:
    shipyards.append(game.players[player].shipyard.position)

for base in shipyards:
    f.write("shipyard location: (" + str(base.x) + ", " + str(base.y) + ")\n")
f.close()

# store the coordinates of all ships considering where they will move to avoid crashing.

while True:
    # This loop handles each turn of the game. The game object changes every turn, and you refresh that state by
    # running update_frame().
    game.update_frame()

    # A command queue holds all the commands you will run this turn. You build this list up and submit it at the
    # end of the turn.
    command_queue = []
    ship_coords = {}
    destinationList = []
    epos = enemyPossiblePaths()

    for ship in me.get_ships():
        # all new ships will be navigating and collecting halite

        if ship.id not in ship_states:
            ship_states[ship.id] = "navigating"
            shipCount += 1
            destinations.update({ship.id : setNewDestination(ship)})
            logging.info(ship.id)
            logging.info(destinations[ship.id])

        if ship_states[ship.id] == "navigating" and ship.position == destinations[ship.id]:
            ship_states[ship.id] = "collecting"

        destinationList.append(destinations[ship.id])
        upcoming_position = None
        directional_choice = None;

        if wantToMove(ship):
            directional_choice = directionToMove(ship,epos)
        else:
            directional_choice = direction_order[4]

        upcoming_position = ship.position + Position(*directional_choice)
        ship_coords.update({ship.id : upcoming_position})
        command_queue.append(ship.move(directional_choice))

        if ship_states[ship.id] == "collecting" or ship_states[ship.id] == "navigating":

            if ship.halite_amount >= constants.MAX_HALITE - int((game.turn_number/maxTurns) * 600):
                logging.info("I am full")
                ship_states[ship.id] = "depositing"
                ship_deposits[ship.id] = ship.halite_amount
                destinations.update({ship.id : setNewDestination(ship)})
        else :
            if upcoming_position == destinations[ship.id]:
                ship_states[ship.id] = "navigating"
                setNewDestination(ship)

    # ship costs 1000, dont make a ship on a ship or they both sink
    if game.turn_number < maxTurns * 0.5:
        if me.halite_amount >= 1000 and not game_map[me.shipyard].is_occupied and not me.shipyard.position in ship_coords.values():
            command_queue.append(me.shipyard.spawn())
    elif game.turn_number < maxTurns * 0.75:
        if me.halite_amount >= 1000 and not game_map[me.shipyard].is_occupied and not me.shipyard.position in ship_coords.values() and random.randint(1,9) > 6 :
            command_queue.append(me.shipyard.spawn())

    # Send your moves back to the game environment, ending this turn.
    logging.info(command_queue)
    game.end_turn(command_queue)


    if game.turn_number % 5 == 0:
        haliteInMap()
