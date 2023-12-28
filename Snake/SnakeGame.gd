extends Node

var snake_body: Array[Node2D]
var snake_init_pos = [Vector2(256,240), Vector2(240, 240), Vector2(224, 240)]
var lastApple: Node2D
var lastAction: int = 0
var lastUpdateTime = 0
var isGameBegin = false
var isGameStart = false
var isGameEnd = false
var httpNodeInit: HTTPRequest
var httpNodeAct: HTTPRequest
var httpNodeState: HTTPRequest

var isTrainingMode = true

func _ready():
	httpNodeInit = HTTPRequest.new()
	httpNodeInit.set_name("HTTPNode")
	add_child(httpNodeInit)
	httpNodeInit.request_completed.connect(self._http_request_completed_init)
	
	httpNodeAct = HTTPRequest.new()
	httpNodeAct.set_name("HTTPNode")
	add_child(httpNodeAct)
	httpNodeAct.request_completed.connect(self._http_request_completed_act)
	
	httpNodeState = HTTPRequest.new()
	httpNodeState.set_name("HTTPNode")
	add_child(httpNodeState)
	httpNodeState.request_completed.connect(self._http_request_completed_state)
	
	if !isTrainingMode:
		isGameBegin = true
		start_game()
	
func _process(delta):
	if !isTrainingMode:
		return
	
	if !isGameBegin or isGameEnd:
		get_init_info()
		
	if isGameBegin and isGameStart and !isGameEnd:
		post_game_state(false)
		get_cur_action()
		
func is_http_usable(httpNode:HTTPRequest):
	if httpNode.get_http_client_status() == HTTPClient.STATUS_DISCONNECTED:
		return true
	
	return false
	
func reset_http(httpNode:HTTPRequest):
	httpNode.cancel_request()

func get_init_info():
	if !is_http_usable(httpNodeInit):
		return
	var error = httpNodeInit.request("http://127.0.0.1:5000/initinfo")
	if error != OK:
		push_error("An error occurred in the HTTP request.")
		reset_http(httpNodeInit)

func get_cur_action():
	if !is_http_usable(httpNodeAct):
		return
	var error = httpNodeAct.request("http://127.0.0.1:5000/curAction")
	if error != OK:
		push_error("An error occurred in the HTTP request.")
		reset_http(httpNodeAct)
		
func post_game_state(isFinalDeadState:bool):
	if isFinalDeadState:
		isGameEnd = true
		reset_http(httpNodeState)
	else:
		if snake_body.size() < 3 or lastApple == null:
			return
		if !is_http_usable(httpNodeState):
			return
		
	var headPos = snake_body[0].global_position
	var applePos = lastApple.global_position
	
	var body = JSON.stringify({"gameEnd": isGameEnd, "head_x": headPos.x,"head_y":headPos.y, 
	"apple_delta_x": applePos.x - headPos.x, "apple_delta_y": applePos.y - headPos.y, "snake_length":snake_body.size()})
	var error = httpNodeState.request("http://127.0.0.1:5000/setState", [], HTTPClient.METHOD_POST, body)
	if error != OK:
		push_error("An error occurred in the HTTP request.")
		reset_http(httpNodeState)

func _http_request_completed_init(result, response_code, headers, body):
	var json = JSON.new()
	json.parse(body.get_string_from_utf8())
	var response = json.get_data()
	print(response["begin"])
	if !isGameBegin and response["begin"]:
		isGameBegin = true
		isGameEnd = false
		start_game()
	elif isGameBegin and !response["begin"]:
		isGameBegin = false
	reset_http(httpNodeInit)

func _http_request_completed_act(result, response_code, headers, body):
	var json = JSON.new()
	json.parse(body.get_string_from_utf8())
	var response = json.get_data()
	
	var curAction = lastAction
	if response["curAction"] == 0 && lastAction != 1:
		curAction = 0
	elif response["curAction"] == 1 && lastAction != 0:
		curAction = 1
	elif response["curAction"] == 2 && lastAction != 3:
		curAction = 2
	elif response["curAction"] == 3 && lastAction != 2:
		curAction = 3
	lastAction = curAction
	print(lastAction)
	
func _http_request_completed_state(result, response_code, headers, body):
	var json = JSON.new()
	json.parse(body.get_string_from_utf8())
	var response = json.get_data()
	reset_http(httpNodeState)
	
func reset_game():
	for b in snake_body:
		b.queue_free()
	snake_body.clear()
	if lastApple != null:
		lastApple.queue_free()
		lastApple = null
	
	isGameBegin = false
	isGameStart = false
	isGameEnd = true
	lastAction = 0
	lastUpdateTime = 0
	
func start_game():
	spawn_init_snake()
	spawn_apple()
	isGameStart = true
	isGameEnd = false
	
func spawn_init_snake():
	var scene = preload("res://snake_body.tscn")
	for p in snake_init_pos:
		var sb = scene.instantiate()
		sb.global_position = p
		get_node('/root/Node2D').add_child(sb)
		snake_body.append(sb)
	
func spawn_apple():
	var posX = randi_range(3, 28)
	var posY = randi_range(3, 28)
	
	var newPos = Vector2(posX*16, posY*16)
	var scene = preload("res://apple.tscn")
	var apple = scene.instantiate()
	apple.global_position = newPos
	get_node('/root/Node2D').add_child(apple)
	lastApple = apple

func _physics_process(delta):
	if Time.get_ticks_msec() - lastUpdateTime > 100 && isGameStart:
		lastUpdateTime = Time.get_ticks_msec()
		do_update()

func do_update():
	var nextHeadPos = snake_body[0].global_position
	if lastAction == 0:
		nextHeadPos.x = nextHeadPos.x + 16
	elif lastAction == 1:
		nextHeadPos.x = nextHeadPos.x - 16
	elif lastAction == 2:
		nextHeadPos.y = nextHeadPos.y - 16
	elif lastAction == 3:
		nextHeadPos.y = nextHeadPos.y + 16
		
	if lastApple and lastApple.global_position == nextHeadPos:
		snake_grow(nextHeadPos)
		lastApple.queue_free()
		lastApple = null
		spawn_apple()
	elif nextHeadPos.x < 0 or nextHeadPos.x > 480 or nextHeadPos.y < 0 or nextHeadPos.y > 480:
		snake_dead()
	elif is_pos_collide_body(nextHeadPos):
		snake_dead()
	else:
		snake_move(nextHeadPos)


func _input(event):
	if !isGameBegin:
		return
	
	var curAction = lastAction
	
	if event.is_action_pressed("right") && lastAction != 1:
		curAction = 0
	elif event.is_action_pressed("left") && lastAction != 0:
		curAction = 1
	elif event.is_action_pressed("up") && lastAction != 3:
		curAction = 2
	elif event.is_action_pressed("down") && lastAction != 2:
		curAction = 3
		
	lastAction = curAction
	
func snake_grow(pos):
	var scene = preload("res://snake_body.tscn")
	var sb = scene.instantiate()
	sb.global_position = pos
	get_node('/root/Node2D').add_child(sb)
	snake_body.push_front(sb)
	
func snake_move(pos):
	var scene = preload("res://snake_body.tscn")
	var sb = scene.instantiate()
	sb.global_position = pos
	get_node('/root/Node2D').add_child(sb)
	var lastBody = snake_body.pop_back()
	(lastBody as Node).queue_free()
	snake_body.push_front(sb)

func is_pos_collide_body(pos):
	for i in snake_body:
		if i.global_position == pos:
			return true
	return false
	
func snake_dead():
	if !isTrainingMode:
		reset_game()
		isGameBegin = true
		start_game()
	else:
		post_game_state(true)
		reset_game()
