extends "res://tests/test_case.gd"


func test_movement_waits_for_first_direction() -> void:
	var session := Session.new(Vector2i(10, 10))
	session.tick()
	assert_true(not session.started)
	assert_eq(session.dragon.body[0], Vector2i(5, 5))
	session.turn(Vector2i.RIGHT)
	session.tick()
	assert_true(session.started)
	assert_eq(session.dragon.body[0], Vector2i(6, 5))


func test_the_dragon_starts_on_open_floor_inside_a_wall() -> void:
	var session := Session.new(Vector2i(10, 10))
	assert_true(session.board.is_solid(Vector2i(0, 0)))
	assert_true(not session.board.is_solid(session.dragon.body[0]))


func test_collecting_a_passenger_adds_a_carriage_and_a_point() -> void:
	var session := Session.new(Vector2i(10, 10))
	var length := session.dragon.body.size()
	var old_tail: Vector2i = session.dragon.body.back()
	session.passenger_cell = Vector2i(6, 5)
	session.turn(Vector2i.RIGHT)
	session.tick()
	assert_eq(session.dragon.body.size(), length + 1)
	assert_eq(session.dragon.body.back(), old_tail)
	assert_eq(session.score, 1)
	assert_true(not session.dragon.body.has(session.passenger_cell))
	assert_true(not session.board.is_solid(session.passenger_cell))


func test_no_passenger_spawns_when_all_floor_cells_are_taken() -> void:
	var session := Session.new(Vector2i(10, 10))
	session.passenger_cell = Vector2i(6, 5)
	for cell in session.board.tiles:
		if cell != session.passenger_cell and not session.dragon.body.has(cell):
			session.board.tiles[cell] = "wall"
	session.turn(Vector2i.RIGHT)
	session.tick()
	assert_eq(session.passenger_cell, Session.NO_PASSENGER)


func test_hitting_a_wall_stops_the_run() -> void:
	var session := Session.new(Vector2i(10, 10))
	session.passenger_cell = Session.NO_PASSENGER
	session.turn(Vector2i.UP)
	for i in 5:
		session.tick()
	assert_true(session.crashed)
	assert_eq(session.dragon.body[0], Vector2i(5, 1))
	session.turn(Vector2i.RIGHT)
	session.tick()
	assert_eq(session.dragon.body[0], Vector2i(5, 1))


func test_hitting_the_body_stops_the_run() -> void:
	var session := Session.new(Vector2i(10, 10))
	session.passenger_cell = Vector2i(6, 5)
	session.turn(Vector2i.RIGHT)
	session.tick()
	session.passenger_cell = Session.NO_PASSENGER
	for direction in [Vector2i.UP, Vector2i.RIGHT, Vector2i.DOWN, Vector2i.LEFT]:
		session.turn(direction)
		session.tick()
	assert_true(session.crashed)
	assert_eq(session.dragon.body[0], Vector2i(7, 5))
	assert_eq(session.score, 1)


func test_moving_into_the_departing_tail_is_safe() -> void:
	var session := Session.new(Vector2i(10, 10))
	session.passenger_cell = Session.NO_PASSENGER
	for direction in [Vector2i.UP, Vector2i.RIGHT, Vector2i.DOWN, Vector2i.LEFT]:
		session.turn(direction)
		session.tick()
	assert_true(not session.crashed)
	assert_eq(session.dragon.body[0], Vector2i(5, 5))
