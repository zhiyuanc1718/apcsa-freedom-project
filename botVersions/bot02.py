import hlt

# This library contains constant values.
from hlt import constants

# This library contains direction metadata to better interface with the game.
from hlt.positionals import Direction
from hlt.positionals import Position

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
game.ready("Version02")

# Now that your bot is initialized, save a message to yourself in the log file with some important information.
# Here, you log here your id, which you can always fetch from the game object by using my_id.
logging.info("Successfully created bot! My Player ID is {}.".format(game.my_id))

ship_states = {}

while True:
    # This loop handles each turn of the game. The game object changes every turn, and you refresh that state by
    # running update_frame().
    game.update_frame()
    # You extract player metadata and the updated map metadata here for convenience.
    me = game.me
    game_map = game.game_map

    # A command queue holds all the commands you will run this turn. You build this list up and submit it at the
    # end of the turn.
    command_queue = []

    # get_surrounding_cardinals() returns the surrounding coordinates in the following direction order
    direction_order = [Direction.North, Direction.South, Direction.East, Direction.West, Direction.Still]

    # store the coordinates of all ships considering where they will move to avoid crashing.
    coordinates = []
    for ship in me.get_ships():

        # all new ships will be collecting halite
        if ship.id not in ship_states:
            ship_states[ship.id] = "collecting"

        if ship_states[ship.id] == "collecting":
            # from positionals.py.

            # provides the coordinates of all options/moves (NSEW) excluding staying still
            options = ship.position.get_surrounding_cardinals() + [ship.position]

            # pos = {(0, -1): Position(8, 15), (-1,0) : Position(7, 16) ...}
            # pos dictionary : maps direction (NSEW) to a Position(coordinate)
            pos = {}

            # energy dictionary : maps the direction choice with halite
            # energy = {(0, -1): halite, (0, 1): halite ...}
            energy = {}

            for n, direction in enumerate(direction_order):
                pos[direction] = options[n]

            for direction in pos:
                position = pos[direction]
                halite_amount = game_map[position].halite_amount

                # the position of the direction we are planning to move will not be taken over by another ship
                # we will consider each of the available directions for movement
                if pos[direction] not in coordinates:
                    # we prefer to stay still to collect remaining halite
                    if direction == Direction.Still:
                        halite_amount *= len(me.get_ships())
                    energy[direction] = halite_amount

            directional_choice = max(energy, key=energy.get)
            coordinates.append(pos[directional_choice])

            command_queue.append(ship.move(game_map.naive_navigate(ship, ship.position + Position(*directional_choice))))

            if ship.halite_amount >= constants.MAX_HALITE * 0.75:
                ship_states[ship.id] = "depositing"

        else:
            move = game_map.naive_navigate(ship, me.shipyard.position)
            upcoming_position = ship.position + Position(*move)
            if upcoming_position not in coordinates:
                coordinates.append(upcoming_position)
                command_queue.append(ship.move(move))
                if move == Direction.Still:
                    ship_states[ship.id] = "collecting"
            else:
                coordinates.append(ship.position)
                command_queue.append(ship.move(game_map.naive_navigate(ship, ship.position+Position(*Direction.Still))))

    # ship costs 1000, dont make a ship on a ship or they both sink
    if len(me.get_ships()) < math.ceil(game.turn_number / 25):
        if me.halite_amount >= 1000 and not game_map[me.shipyard].is_occupied:
            command_queue.append(me.shipyard.spawn())

    # Send your moves back to the game environment, ending this turn.
    game.end_turn(command_queue)