import hlt

from collections import Counter

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
game.ready("TrialBot05")

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
coords = []
avoidCoords = []
ship_deposits = {}          # ship.id map to theoretical deposit
destinations = {}           # ship.id map to destination
shipCount = 0
moveBoolean = {}
droplocations = [me.shipyard.position]
baseCoords = []

# sets no-go-zone to be within a radius of 2 of any enemy shipyards
for player in game.players:
    if player != me.id:
        for i in range(game.players[player].shipyard.position.x-2, game.players[player].shipyard.position.x+3):
            for j in range(game.players[player].shipyard.position.y-2, game.players[player].shipyard.position.y+3):
                avoidCoords.append(Position(i,j))

for i in range(me.shipyard.position.x-2, me.shipyard.position.x+3):
    for j in range(me.shipyard.position.y-2,me.shipyard.position.y+3):
        baseCoords.append(Position(i,j))

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
    for y in range(0, game_map.height, 2):
        for x in range(0, game_map.width, 2):
            gridSum = 0
            highest = Position(x,y)
            for j in range(y, y+2):
                for i in range(x, x+2):
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
    droplocations = drops + [me.shipyard.position]
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
    End of game, destroy as needed
    '''
    if ship_states[ship.id] == "destroy":
        return False

    '''
    we will obviously not move if we do not have the resources to.
    '''

    if (ship.halite_amount < int(game_map[ship.position].halite_amount / constants.MOVE_COST_RATIO)):
        return False

    '''
    when cell has no energy, pointless to stay (will check to avoid collisions in directionToMove method)
    '''

    if game_map[ship.position].halite_amount == 0:
        return True

    '''
    moving will reduce our ship's halite by 1/10 of x halite on the cell we're about to leave
    staying will increase our halite by 1/4 of x halite on cell we're on.
    We want to maximize halite. Stay if staying is better/necessary. Otherwise, move.
    '''

    '''
    Assuming we will keep moving, the net lost is 1/10 of all cells prior to destination
    any pause (mining) will reduce net lost by 1/4 of X cell's halite
    '''

    if ship_states[ship.id] == "navigating" or ship_states[ship.id] == "collecting":
        stayMoveProfit =  game_map[ship.position].halite_amount/constants.EXTRACT_RATIO - 0.75 * game_map[ship.position].halite_amount / constants.MOVE_COST_RATIO
        for pos in ship.position.get_surrounding_cardinals():
            moveStayProfit =  game_map[pos].halite_amount/constants.EXTRACT_RATIO - game_map[ship.position].halite_amount/constants.MOVE_COST_RATIO
            if stayMoveProfit < moveStayProfit:
                #move-stay benefit
                return True
        #stay-move beneft
        return False

    else:
        if ship_states[ship.id] == "depositing":
            deposit = ship_deposits[ship.id]
            if not ship.halite_amount == 1000 and ship.halite_amount -  game_map[ship.position].halite_amount/constants.MOVE_COST_RATIO <= 0.9 * deposit:
                #stay to save energy
                return False
            #full or energy can be conserved
            return True
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
                    if p not in baseCoords:
                        positions.append(p)
    return positions

# game_map._get_target_direction is unreliable and needs a little wrap upgrade
def preferredDirections(ship, target):

    d = []
    if target.y > ship.position.y:
        if abs(target.y - ship.position.y) <= abs(ship.position.y + game_map.height - target.y):
            d.append(Direction.South)
        else:
            d.append(Direction.North)
    elif target.y < ship.position.y:
        if abs(target.y - ship.position.y) <= abs(target.y + game_map.height - ship.position.y):
            d.append(Direction.North)
        else:
            d.append(Direction.South)

    if target.x > ship.position.x:
        if abs(target.x - ship.position.x) <= abs(ship.position.x + game_map.width - target.x):
            d.append(Direction.East)
        else:
            d.append(Direction.West)
    if target.x < ship.position.x:
        if abs(target.x - ship.position.x) <= abs(target.x + game_map.width - ship.position.x):
            d.append(Direction.West)
        else:
            d.append(Direction.East)
    return d

# apply method when wantToMove() returns True
# return the optimal direction to move, which includes staying still.
def directionToMove(ship, epos, ecount):
    '''
    Move only into "will-not-be-occipied cells"
    If both directions are not opened for navigation, consider moving somewhere else.

    Avoid a potential path of an enemy if our ship has X halite. Attack or proceed in the direction chosen if we have little halite.
    '''

    willSuicide = suicide(ship, ecount)
    if ship.position in coords and ship.halite_amount < 400:
        willSuicide = True
    directional_choice = direction_order[4]

    if ship_states[ship.id] == "collecting":
        options = ship.position.get_surrounding_cardinals() + [ship.position]
        # pos = {(0, -1): Position(8, 15), (-1,0) : Position(7, 16) ...}
        pos = {}
        # energy dictionary : maps the direction choice with halite {(0, -1): 708, (0, 1): 492 ...}
        energy = {}
        for n, direction in enumerate(direction_order):
            pos[direction] = options[n]

        for direction in pos:
            # position will be a coordinate
            position = pos[direction]
            halite_amount = game_map[position].halite_amount
            flag = True
            threat = None
            if game_map[position].is_occupied:
                if game_map[position].ship in me.get_ships():
                    flag = moveBoolean[game_map[position].ship.id]
                    threat = "o"
                else:
                    threat = "e"
            if threat == "e" and not willSuicide:
                continue
            bool = position not in coords and flag and position not in epos and position not in avoidCoords
            if willSuicide:
                bool = position not in coords and flag
            if bool:
                if direction == Direction.Still:
                    halite_amount *= len(me.get_ships())
                    energy[direction] = halite_amount
                else:
                    energy[direction] = halite_amount
        if len(energy) > 0:
            directional_choice = max(energy, key=energy.get)
        return directional_choice

    else:
        preferred = preferredDirections(ship, destinations[ship.id])
        for d in preferred:
            p = ship.position + Position(*d)
            bool = p not in coords and p not in epos and p not in avoidCoords
            if willSuicide:
                bool = p not in coords
            if maxTurns - game.turn_number <= 35:
                bool = p not in coords or p in droplocations
            if bool:
                if game_map[p].is_occupied:
                    if p in droplocations and maxTurns - game.turn_number <= 35:
                        return d
                    if game_map[p].ship in me.get_ships():
                        if moveBoolean[game_map[p].ship.id]:
                            directional_choice = d
                    else:
                        if willSuicide:
                            directional_choice = d
                else :
                    directional_choice = d
                return directional_choice

        if not maxTurns - game.turn_number <= 35:
            directions = [d for d in direction_order if d not in preferred and d is not Direction.Still]

            for d in directions:
                p = ship.position + Position(*d)
                if not game_map[p].is_occupied and p not in epos and p not in coords and p not in avoidCoords:
                    directional_choice = d
                    break
                else:
                    if game_map[p].is_occupied:
                        if game_map[p].ship in me.get_ships():
                            if moveBoolean[game_map[p].ship.id]:
                                directional_choice = d
                        else:
                            if willSuicide:
                                directional_choice = d
        return directional_choice

def setNewDestination(ship):
    haliteInMap()
    # if we want to deposit, all we need is a dropoff or the shipyard. we find the closest one
    if ship_states[ship.id] == "depositing":
        destination = nearestBase(ship.position)
        return destination

    # if we want to collect halite, then we must find the highest score areas
    else:
        scores = {}
        shipDestinations = []
        destinationCounts = Counter(destinations.values())
        for p,h in zones.items():
            condition = p in destinations.values()
            if condition:
                if destinationCounts[p] > int(h/constants.MAX_HALITE) * 4:
                    continue
            score = h / (game_map.calculate_distance(ship.position, p) * game.turn_number/maxTurns + 1)
            # + game_map.calculate_distance(p, nearestBase(p))
            scores.update({p : score})
        maxScore = max(scores.values())
        for k,v in scores.items():
            if v == maxScore:
                shipDestinations.append(k)
        return shipDestinations[0]

def suicide(ship, enemyCount):
    if enemyCount >= 6:
        return True
    if enemyCount > 3 and ship.halite_amount <= 300:
        return True
    return False

maxHalite = haliteInMap()

'''
Neighbor grid consist of any cells [x] or [X] that another ship can possibly occupy (before making move for this turn) and crash into current ship marked by [o]
[ ][ ][x][ ][ ]
[ ][x][X][x][ ]
[x][X][o][X][x]
[ ][x][X][x][ ]
[ ][ ][x][ ][ ]

By default, if we include [o], then there is a minimum of 1 ship in the entire neighbor grid.
The most dangerous cells are marked [X] if they all contain our ships, our ship either will be stuck or might risk crashing if we do not make the move first.
enemy ships are far more dangerous and priority must be given to current ship.

Ship-Cap : 13 in neighbor range (12 others)
Suggest : enemy ships be worth 12 times more if within radius of 1 (very close by)
Suggest : enemy ships be worth 6 times if within radius of 2 (full navigation grid)
'''
neighbor_1rad = [Position(x,y) for y in range(-1,2) for x in range(-1,2)]
neighbor_2rad = [Position(-2,0), Position(0,-2), Position(2,0), Position(0,2)]

while True:
    # This loop handles each turn of the game. The game object changes every turn, and you refresh that state by
    # running update_frame().
    game.update_frame()

    # A command queue holds all the commands you will run this turn. You build this list up and submit it at the
    # end of the turn.
    command_queue = []
    epos = enemyPossiblePaths()
    neighborShipDensity = []
    sortedShips = []
    enemyCounts = {}
    moveBoolean = {}

    # sort ships based on danger priority and distance.
    for ship in me.get_ships():
        # all new ships will be navigating and collecting halite
        if ship.id not in ship_states:
            ship_states[ship.id] = "navigating"
            shipCount += 1
            destinations.update({ship.id : setNewDestination(ship)})
        # prioritize (#2) all ships with less distance to destination
        invDistance = 1/(game_map.calculate_distance(ship.position, destinations[ship.id]) + 1)
        #neighborShipDensity : highest density gets priority to decide first.
        nsd = invDistance
        enemies = 0
        for p in neighbor_1rad:
            if game_map[ship.position + p].is_occupied:
                nsd += 2
                # if occupied but not by our ships (our ship : +2, enemy ship : +12)
                if ship.position + p not in coords:
                    nsd += 10
                    enemies += 1
        for p in neighbor_2rad:
            if game_map[ship.position + p].is_occupied:
                nsd += 1
                if ship.position + p not in coords:
                    nsd += 5
                    enemies += 1
        index = 0
        for s in range(len(sortedShips)):
            if nsd < neighborShipDensity[s]:
                index += 1
            else:
                break
        sortedShips.insert(index, ship)
        neighborShipDensity.insert(index, nsd)
        moveBoolean[ship.id] = wantToMove(ship)
        enemyCounts[ship.id] = enemies;

        disToDrop = game_map.calculate_distance(ship.position, nearestBase(ship.position))
        if ship_states[ship.id] != "destroy":
            if ship.halite_amount > 100 and disToDrop <= maxTurns - game.turn_number + 15 and maxTurns - game.turn_number <= 35:
                ship_states[ship.id] = "depositing"
                ship_deposits[ship.id] = ship.halite_amount
                destinations.update({ship.id : setNewDestination(ship)})

    coords = []

    for ship in sortedShips:

        if ship_states[ship.id] == "navigating" and ship.position == destinations[ship.id]:
            ship_states[ship.id] = "collecting"

        upcoming_position = None
        directional_choice = None

        if moveBoolean[ship.id]:
            directional_choice = directionToMove(ship,epos, enemyCounts[ship.id])
        else:
            directional_choice = direction_order[4]

        upcoming_position = ship.position + Position(*directional_choice)

        if (not (maxTurns - game.turn_number <= 35 and upcoming_position in droplocations)):
            coords.append(upcoming_position)
        command_queue.append(ship.move(directional_choice))

        if ship_states[ship.id] == "collecting" or ship_states[ship.id] == "navigating":
            if ship.halite_amount >= constants.MAX_HALITE - int((game.turn_number/maxTurns) * 300):
                ship_states[ship.id] = "depositing"
                ship_deposits[ship.id] = ship.halite_amount
                destinations.update({ship.id : setNewDestination(ship)})
        else :
            if upcoming_position == destinations[ship.id]:
                ship_states[ship.id] = "navigating"
                destinations.update({ship.id : setNewDestination(ship)})
            if upcoming_position in droplocations:
                if maxTurns - game.turn_number <= 35:
                    ship_states[ship.id] = "destroy"

    # ship costs 1000, dont make a ship on a ship or they both sink
    if game.turn_number < maxTurns * 0.5:
        if me.halite_amount >= 1000 and not game_map[me.shipyard].is_occupied and not me.shipyard.position in coords:
            command_queue.append(me.shipyard.spawn())
    elif game.turn_number < maxTurns * 0.65:
        if me.halite_amount >= 1000 and not game_map[me.shipyard].is_occupied and not me.shipyard.position in coords and random.randint(1,9) > 6 :
            command_queue.append(me.shipyard.spawn())

    # Send your moves back to the game environment, ending this turn.
    game.end_turn(command_queue)

