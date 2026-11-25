## One run at the game: the board and the dragon on it, from the first tick until the
## run ends. Rules that involve more than the dragon (food, score, what the dragon can
## run into) belong here, so Dragon stays about movement and app/ only draws.
class_name Session
extends RefCounted

const NO_PASSENGER := Vector2i(-1, -1)

var board: Board
var dragon: Dragon
var passenger_cell := NO_PASSENGER
var score := 0
var _rng := RandomNumberGenerator.new()


func _init(grid_size: Vector2i, passenger_seed := 1) -> void:
	board = Board.bordered(grid_size)
	dragon = Dragon.new(grid_size)
	_rng.seed = passenger_seed
	_place_passenger()


func tick() -> void:
	var old_tail: Vector2i = dragon.body.back()
	dragon.tick()
	if dragon.body[0] == passenger_cell:
		dragon.body.append(old_tail)
		score += 1
		_place_passenger()


func _place_passenger() -> void:
	var free_cells: Array[Vector2i] = []
	for x in board.size.x:
		for y in board.size.y:
			var cell := Vector2i(x, y)
			if not board.is_solid(cell) and not dragon.body.has(cell):
				free_cells.append(cell)

	passenger_cell = NO_PASSENGER
	if not free_cells.is_empty():
		passenger_cell = free_cells[_rng.randi_range(0, free_cells.size() - 1)]
