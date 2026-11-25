extends "res://tests/test_case.gd"


func test_a_tick_moves_the_dragon_head() -> void:
	var session := Session.new(Vector2i(10, 10))
	session.tick()
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
	session.tick()
	assert_eq(session.passenger_cell, Session.NO_PASSENGER)
