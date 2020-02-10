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
game.ready("TrialBot03")

# Now that your bot is initialized, save a message to yourself in the log file with some important information.
# Here, you log here your id, which you can always fetch from the game object by using my_id.
logging.info("Successfully created bot! My Player ID is {}.".format(game.my_id))

# You extract player metadata and the updated map metadata here for convenience.
me = game.me
game_map = game.game_map

# Variables related to player/game state
maxTurnsDict = {60:500, 56:475, 48:450, 40:425, 32:400}
maxTurns = maxTurnsDict[game_map.width]
maxHalite = 0
zoneHalite = {}         # maps zone number to halite amount
zonePosition = {}       # maps zone number to top left corner position
coordsToZone = {}       # Position(x,y) maps to zone value : used to check whether a ship is in destinated zone, len() is squared of width [very large]

# related to ships
ship_states = {}        # ship.id map to game mode
ship_returning = {}     # ship.id map to return boolean, immediately sets to false after base defined
shipArrived = {}
ship_toBase = {}        # ship.id map to closest base Position(x,y)
destinations = {}
destinationZones = {}
avoidCoords = [] # No ships are allowed to step upon these coordinates

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

# returns the amount of halite in an area block of size 4 x 4
# param : x,y should be the coordinate of the very left corner in zone.
# To call haliteInZone() : x,y can be retrieved from zonePosition[zone number].x and .y respectively once running haliteInMap(True)
def haliteInZone(x,y,fill = None):
    areaHalite = 0
    zoneNum = int(y/4 * game_map.width/4 + x/4)
    if fill is not None:
        zonePosition.update({zoneNum : Position(x,y)})
    for i in range (x, x+4):
        for j in range(y, y+4):
            if fill is not None:
                coordsToZone.update({Position(i,j) : zoneNum})
            areaHalite += game_map[Position(i,j)].halite_amount
        zoneHalite.update({zoneNum : areaHalite})
    return areaHalite

# returns the amount of halite in the entire map
# param : fill = boolean (True only for initial), reduce run time with None.
def haliteInMap(fill = None):
    haliteRemaining = 0
    for y in range(0, game_map.height, 4):
        for x in range(0, game_map.width, 4):
            if fill is None:
                haliteRemaining += haliteInZone(x,y)
            else:
                haliteRemaining += haliteInZone(x,y,fill)
    return haliteRemaining

# returns the closest dropoff including shipyard for a ship
# param : pos = current position of object
def nearestBase(pos):
    drops = []
    for dropoff in me.get_dropoffs():
        drops.append(dropoff.position)
    drops.append(me.shipyard.position)
    min = game_map.calculate_distance(pos, me.shipyard.position)
    droplocation = me.shipyard.position
    for drop in drops:
        if game_map.calculate_distance(pos, drop) < min:
            min = game_map.calculate_distance(pos, drop)
            droplocation = drop
    return droplocation

# returns a list of average distances to each particular zone
# param : ship = current ship [access position]
def averageDistance(ship):
    distanceToZones = []
    # p is a Position(i,j) class object
    for p in zonePosition.values():
        distance = 0
        # iterate over the 4 x 4 grid starting from the corner
        for px in range (p.x, p.x + 4):
            for py in range (p.y, p.y + 4):
                distance += game_map.calculate_distance(ship.position, Position(px,py))
        distance = int(distance/16)
        distanceToZones.append(distance)
    return distanceToZones

# returns a list of values taken from halite in zone divided by average distance to zone
# params : ship = current ship [access position]
def areaWorth(ship):
    distanceArray = averageDistance(ship)
    worth = []
    # Next > consider the distance it takes to the zone and back to base from zone for dropoff
    for areaCode, halite in zoneHalite.items():
        worth.append(round(3*halite/(distanceArray[areaCode]),2))
    return worth

def newDestintation(ship):
    myDestination = None
    worth = areaWorth(ship)
    targetZones = {}
    for i in range(0, len(worth)):
        if i not in destinationZones.values():
            targetZones.update({i : worth[i]})
    targetZone = []
    maxWorth = max(targetZones.values())
    for k,v in targetZones.items():
        if v == maxWorth:
            targetZone.append(k)
    targetZone = targetZone[0]
    destinationZones.update({ship.id : targetZone})
    myDestinationZone = zonePosition[targetZone]
    haliteLevel = 0;
    for i in range(myDestinationZone.x, myDestinationZone.x+4):
        for j in range(myDestinationZone.y, myDestinationZone.y+4):
            if game_map[Position(i,j)].halite_amount > haliteLevel:
                haliteLevel = game_map[Position(i,j)].halite_amount
                myDestination = Position(i,j)
    destinations[ship.id] = myDestination

maxHalite = haliteInMap(True)

# returns a tuple of zone code(s) and it's halite (this is the highest halite zone on the map)
def highestDensityZone():
    highest = max(zoneHalite.values())
    zoneCode = []
    for k,v in zoneHalite.items():
        if v == highest:
            zoneCode.append(k)
    return (highest, zoneCode)

# writing files
f = open("gameinfo" + str(game.my_id) + ".txt","w+")

for areaCode in zoneHalite:
    f.write("Area Code: " + str(areaCode) +", Halite :" + str(zoneHalite[areaCode]) + "\n")

f.write("Total Halite in game map = " + str(maxHalite) + "\n")
highHaliteZone = highestDensityZone()
f.write("Highest Halite within one Area : " + str(highHaliteZone[0]) + "\n")
for z in highHaliteZone[1]:
    f.write("Highest Halite Value Area Code: " + str(z) + "\n")

f.write("My ships will avoid the following coordinates \n")
for coords in avoidCoords:
    f.write(str(coords) + "\n")

shipyards = []
for player in game.players:
    shipyards.append(game.players[player].shipyard.position)

for base in shipyards:
    f.write("shipyard location: (" + str(base.x) + ", " + str(base.y) + ")\n")
f.close()


while True:
    # This loop handles each turn of the game. The game object changes every turn, and you refresh that state by
    # running update_frame().
    game.update_frame()

    # A command queue holds all the commands you will run this turn. You build this list up and submit it at the end of the turn.
    command_queue = []

    # store the coordinates of all ships considering where they will move to avoid crashing.
    coordinates = []

    direction_order = [Direction.North, Direction.South, Direction.East, Direction.West, Direction.Still]

    for ship in me.get_ships():
        # all new ships will be collecting halite

        if ship.id not in ship_states:
            ship_states[ship.id] = "collecting"

        if ship.id not in ship_returning:
            ship_returning[ship.id] = False

        if ship.id not in destinationZones:
            destinationZones[ship.id] = -1

        if ship.id not in shipArrived:
            shipArrived[ship.id] = False

        if destinationZones[ship.id] == -1:
            newDestintation(ship)

        if ship_states[ship.id] == "collecting":
            myDestination = destinations[ship.id]
            upcoming_position = None
            directional_choice = None;
            if ship.position != myDestination and not shipArrived[ship.id]:
                toTargetChoices = GameMap._get_target_direction(ship.position, myDestination)
                directionalChoices = []
                for t in toTargetChoices:
                    if t is not None:
                        directionalChoices.append(t)
                oppositeDirectionalChoices = [Direction.invert(d) for d in directionalChoices]
                for directional in directionalChoices:
                    upcoming_position = ship.position.directional_offset(directional)
                    if upcoming_position not in coordinates:
                        if game_map[ship.position].halite_amount == 0 or ship.halite_amount > int(game_map[ship.position].halite_amount/constants.EXTRACT_RATIO):
                            coordinates.append(upcoming_position)
                            directional_choice = directional
                            break;
                if directional_choice is not None:
                    command_queue.append(ship.move(directional_choice))
                else:
                    # if moving towards destination is not allowed, check to either move in oppsite direction when staying still is not allowed
                    # Case 1 : ship's current position will be occupied : MUST MOVE
                    # NEXT STEPS : what if we must move but we can't move due to lack of halite, tell whichever ship that will occupy our cell to not move here.
                    if ship.position in coordinates:
                        for directional in oppositeDirectionalChoices:
                            upcoming_position = ship.position.directional_offset(directional)
                            if upcoming_position not in coordinates:
                                if game_map[ship.position].halite_amount == 0 or ship.halite_amount > int(game_map[ship.position].halite_amount/constants.EXTRACT_RATIO):
                                    coordinates.append(upcoming_position)
                                    directional_choice = directional
                                    break;
                        if directional_choice is not None:
                            command_queue.append(ship.move(directional_choice))
                        else:
                            coordinates.append(ship.position)
                            command_queue.append(ship.move(Direction.Still))
                    # Case 2 : ship's location will currently not be occupied, so we can stay still.
                    else:
                        coordinates.append(ship.position)
                        command_queue.append(ship.move(Direction.Still))
            else:
                shipArrived[ship.id] = True

                # get_surrounding_cardinals() returns the surrounding coordinates in the following direction order
                options = ship.position.get_surrounding_cardinals() + [ship.position]

                # pos = {(0, -1): Position(8, 15), (-1,0) : Position(7, 16) ...}
                # pos dictionary : maps direction (NSEW) to a Position(x,y)
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
                    if pos[direction] not in coordinates:
                        # we prefer to stay still to collect remaining halite
                        if direction == Direction.Still:
                            halite_amount *= len(me.get_ships())
                        energy[direction] = halite_amount
                if len(energy) > 0 and (game_map[ship.position].halite_amount == 0 or ship.halite_amount > int(game_map[ship.position].halite_amount/constants.EXTRACT_RATIO)):
                    directional_choice = max(energy, key=energy.get)
                else:
                    directional_choice = (0,0)
                coordinates.append(pos[directional_choice])
                command_queue.append(ship.move(game_map.naive_navigate(ship, ship.position + Position(*directional_choice))))

            if ship.halite_amount >= constants.MAX_HALITE - int((game.turn_number/maxTurns) * 600):
                ship_states[ship.id] = "depositing"
                destinationZones.update({ship.id : -1})
                ship_returning.update({ship.id : True})
                shipArrived[ship.id] = False

        else :
            if ship_returning[ship.id] == True:
                ship_toBase.update({ship.id : nearestBase(ship.position)})
                ship_returning[ship.id] = False
            move = game_map.naive_navigate(ship, ship_toBase[ship.id])
            upcoming_position = ship.position + Position(*move)
            if upcoming_position not in coordinates:
                coordinates.append(upcoming_position)
                command_queue.append(ship.move(move))
                if upcoming_position == ship_toBase[ship.id]:
                    ship_states[ship.id] = "collecting"
            else:
                myDestination = destinations[ship.id]
                move = game_map.naive_navigate(ship, myDestination)
                upcoming_position = ship.position + Position(*move)
                if upcoming_position not in coordinates:
                    coordinates.append(upcoming_position)
                    command_queue.append(ship.move(move))
                else:
                    coordinates.append(ship.position)
                    command_queue.append(ship.move(game_map.naive_navigate(ship, ship.position+Position(*Direction.Still))))

    # ship costs 1000, dont make a ship on a ship or they both sink
    if len(me.get_ships()) < math.ceil(game.turn_number / 25):
        if me.halite_amount >= 1000 and not game_map[me.shipyard].is_occupied:
            command_queue.append(me.shipyard.spawn())

    # Send your moves back to the game environment, ending this turn.
    logging.info(command_queue)
    game.end_turn(command_queue)

    if game.turn_number % 20 == 0:
        haliteInMap()

