import cv2
import mediapipe as mp,base64
import numpy as np
from flask import Flask, Response #creates web server for react to talk to and response lets you stream data continuously 
from flask_cors import CORS #security issues solved
from flask import request, jsonify
from threading import Thread
import time
import random

app = Flask(__name__) #creates the web server
CORS(app) #applies the cors fix to the server so react can communicate w it 

def draw_rounded_rect(img, x1, y1, x2, y2, color, radius=15, thickness=-1):
    # Top-left, top-right, bottom-right, bottom-left circles rounded rectangles
    cv2.circle(img, (x1 + radius, y1 + radius), radius, color, thickness)
    cv2.circle(img, (x2 - radius, y1 + radius), radius, color, thickness)
    cv2.circle(img, (x1 + radius, y2 - radius), radius, color, thickness)
    cv2.circle(img, (x2 - radius, y2 - radius), radius, color, thickness)
    
    # Rectangles to fill the gaps
    cv2.rectangle(img, (x1 + radius, y1), (x2 - radius, y2), color, thickness)
    cv2.rectangle(img, (x1, y1 + radius), (x2, y2 - radius), color, thickness)

cap = cv2.VideoCapture(0) #opens camera

mp_hands = mp.solutions.hands # gives access to hand-ttracking model
mp_draw = mp.solutions.drawing_utils #gives utilities to draw landmakrs on screen

#min_detection_confidence is the confidence that mediapipe as that the motion in the camera is from a hand (0.8 is the threshold)
hands = mp_hands.Hands(max_num_hands = 1, min_detection_confidence = 0.7)

prev_x, prev_y = 0, 0
overlay = None
drawing = False #checking for drawing mode

# ── Simplified game state (single room, no Room class needed) ──────────────
# Everything lives in one dictionary — easy to read and debug
game = {
    "players": {},          # username -> { "score": int }
    "drawer": None,         # who is currently drawing
    "word": None,           # secret word for this round
    "round": 1,
    "max_rounds": 3,
    "time_left": 60,
    "game_started": False,
    "game_over": False,
    "chat": [],             # list of message strings shown in the UI
    "guessed_correctly": [], # players who got it right this round
    "countdown": 0,         # 3-2-1 before each round
    "round_start_time": None,
    "drawer_index": 0,      # cycles through players so everyone draws
}

WORDS = [
    "apple", "car", "house", "tree", "dog", "cat",
    "sun", "moon", "fish", "bird", "boat", "star",
    "flower", "clock", "chair", "ball", "hat", "book",
    "rain", "snow", "pizza", "cake", "key", "heart",
    "cloud", "door", "plane", "train", "bus", "cup"
]

ROUND_TIME = 60       # seconds each round lasts
COUNTDOWN_SECS = 3    # seconds of countdown before each round

#checks if camera is open
if not cap.isOpened(): 
    print("camera failed to open!")
    exit()

colors = [(0,0,255),(0,255,0),(255,0,0),(0,255,255)]
color_index = 0 #to track the current color
draw_color = colors[color_index]

#boxes on the left side (vertically alligned), 60x60 each
boxes = [(10,80,70,140), (10,150,70,210),(10,220,70,280), (10,290,70,350)]
#tuple = (x1,y1,x2,y2)

#clear screen box
clear_box = (10,370,70,430)
clear_hover_counter = 0
CLEAR_THRESHOLD = 15

hover_index = -1 # the box currently beign hovered over
hover_counter = 0 #how many frames the finger hovers
HOVER_THRESHOLD = 15 # ~1.5s to selects color

@app.route('/video_feed') #tells the flask that whenever someone visits the url, the function below this line runs
def video_feed(): #flask calls this
    def generate(): #keeps generating data continuously instead of stopping after returning once
        global overlay, prev_x, prev_y, drawing, hover_index, hover_counter, color_index, draw_color, clear_hover_counter
        #infinite loop cuz video is a stream of multiple images
        while True: 
        #cap.read() gives two values, boolean and the actual image which is the numpy array
            yes, frame = cap.read() 
    
            if not yes:
                print("frame not captured!!")
                break
    
        #mirror view
            frame = cv2.flip(frame,1)
            h, w, c = frame.shape

            if overlay is None:
                #creates a transparent layer for the user to draw on 
                overlay = frame.copy() * 0

            #bgr to rgb
            rgb_frame = cv2.cvtColor(frame,cv2.COLOR_BGR2RGB)

            #processing the frame to detect hands
            results = hands.process(rgb_frame)

            if results.multi_hand_landmarks:
                for hand_landmarks in results.multi_hand_landmarks:

                    lm_list = []

                    for id, lm in enumerate(hand_landmarks.landmark):
                        #normalized to pixel
                        cx, cy = int(lm.x*w), int(lm.y*h)
                        lm_list.append((cx,cy))

                    #fingertip is always above the joint when finger is up
                    #index fingertip = landmark 8, index middle joint = lamdmark 6
                    #y increases downward in coordinates
                    index_up = lm_list[8][1] < lm_list[6][1] #if true, finger is pointing upwards

                    #middle fingertip = landmark 12, imiddle middle joint = lamdmark 10
                    #y increases downward in coordinates
                    middle_up = lm_list[12][1] < lm_list[10][1] #if true, finger is pointing upwards

                    #thumb tip = landmark 4, thumb joint = landmark 3
                    #lm_list[4][0]  = x coordinate of thumb tip
                    #for a mirrored right hand thumb, thumb tip > thumb joint x means thumb is sticking out 
                    #x coordinate cuz thumb tip moves sideways unlike y which moves downwards
                    thumb_up = lm_list[4][0] > lm_list[3][0]

                    #same as above (y coordinate)
                    ring_up = lm_list[16][1] < lm_list[14][1]
                    pinky_up = lm_list[20][1] < lm_list[18][1]

                    #for thumbs up, all the other fingers should be curled
                    index_down = not index_up
                    middle_down = not middle_up
                    ring_down = not ring_up
                    pinky_down = not pinky_up

                    #drawing mode
                    if index_up and middle_down:
                        #getting the current fingertip position
                        curr_x, curr_y = lm_list[8]

                        #check if finger is hovering over any box
                        hovered = -1
                        for i, (x1,y1,x2,y2) in enumerate(boxes):
                            # looping all 4 boxes and chekcing if the finger is hovering over any one of them
                            # if x is bw left and right & y is bw top and bottom -> box is being hovered on 
                            # then hovered = box index (0,1,2,3)
                            if x1 < curr_x < x2 and y1 < curr_y < y2:
                                hovered = i
                                break
                
                        #checking clr box
                        cx1, cy1, cx2, cy2 = clear_box
                        over_clear = cx1 < curr_x < cx2 and cy1 < curr_y < cy2

                        #finger is over a box
                        if hovered != -1:
                            #finger is over the same box, counter increases indefinitely till finger moves
                            if hovered == hover_index:
                                hover_counter += 1

                            # finger moved to different box
                            else:
                                #hover_index = index of new box
                                hover_index = hovered
                                hover_counter = 0 # new box resets the counter to 0 cuz you have to start from scratch

                            #if counter hits 40, color selected
                            if hover_counter >= HOVER_THRESHOLD:
                                color_index = hover_index
                                draw_color = colors[color_index]
                                #counter reset so ther's no re-triggering
                                hover_counter = 0
                
                            prev_x, prev_y = 0,0

                        #clear screen
                        elif over_clear:
                            clear_hover_counter += 1
                            if clear_hover_counter >= CLEAR_THRESHOLD:
                                overlay = np.zeros((h,w,c), dtype = np.uint8) #wipes canvas
                                clear_hover_counter = 0
                            prev_x,prev_y = 0,0

                        #no box hovered over
                        else:
                            #if no box hovered, draw normally
                            hover_index = -1
                            hover_counter = 0
                            clear_hover_counter = 0
                            drawing = True
                            if prev_x == 0 and prev_y == 0:
                                #on first frame, set prev = curr so that theres no line from (0,0) to finger's position
                                prev_x, prev_y = curr_x, curr_y

                            #draws a line in red from prev to current position with thickness = 5
                            cv2.line(overlay, (prev_x, prev_y), (curr_x,curr_y),draw_color,5)

                            prev_x, prev_y = curr_x, curr_y

                    #pause drawing mode 
                    elif index_up and middle_up and ring_down:
                        drawing = False 
                        prev_x, prev_y = 0,0
                        #resetting to (0,0) shows that next draw starts fresh

                    #eraser
                    elif index_up and middle_up and ring_up:
                        #draws black over the overlay
                        #middle finger tip = center of eraser
                        curr_x, curr_y = lm_list[12]
                        #(0,0,0) = black, 20 = eraser radius, -1 = filled circle
                        cv2.circle(overlay, (curr_x, curr_y), 20, (0,0,0), -1)
                        prev_x, prev_y = 0,0

            else:
                #if no hand -> reset prev position 
                prev_x,prev_y = 0,0

            #blends live camera frame and drawing overlay together 
            #frame weight = 1 (full opacity), overlay weight = 1 (full opacity), o -> no brightness offset
            combined = cv2.addWeighted(frame, 1, overlay, 1, 0)

                        #boxes frame
            def draw_rounded_rect(img, x1, y1, x2, y2, color, radius=20):
            # fill the middle rectangle
                cv2.rectangle(img, (x1 + radius, y1), (x2 - radius, y2), color, -1)
                cv2.rectangle(img, (x1, y1 + radius), (x2, y2 - radius), color, -1)
                # fill the 4 rounded corners with circles
                cv2.circle(img, (x1 + radius, y1 + radius), radius, color, -1)
                cv2.circle(img, (x2 - radius, y1 + radius), radius, color, -1)
                cv2.circle(img, (x1 + radius, y2 - radius), radius, color, -1)
                cv2.circle(img, (x2 - radius, y2 - radius), radius, color, -1)

            # Render Color Boxes
            for i, (x1, y1, x2, y2) in enumerate(boxes):
                # Draw the actual color box (Solid)
                draw_rounded_rect(combined, x1, y1, x2, y2, colors[i], radius=15)

                # Draw a white dot in the center if selected
                if i == color_index:
                    center_x = (x1 + x2) // 2
                    center_y = (y1 + y2) // 2
                    cv2.circle(combined, (center_x, center_y), 5, (255, 255, 255), -1)

                # Draw Progress Bar inside the box if hovering
                if i == hover_index:
                    bar_width = int((hover_counter / HOVER_THRESHOLD) * (x2 - x1 - 20))
                    cv2.rectangle(combined, (x1 + 10, y2 - 10), (x1 + 10 + bar_width, y2 - 6), (255, 255, 255), -1)

            # Render Clear Box
            cx1, cy1, cx2, cy2 = clear_box
            draw_rounded_rect(combined, cx1, cy1, cx2, cy2, (240, 240, 240), radius=15)
            cv2.putText(combined, "CLR", (cx1+15, cy1+38), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 2)

            # Progress bar for Clear Box
            if clear_hover_counter > 0:
                bar_width = int((clear_hover_counter / CLEAR_THRESHOLD) * (cx2 - cx1 - 20))
                cv2.rectangle(combined, (cx1 + 10, cy2 - 10), (cx1 + 10 + bar_width, cy2 - 6), (100, 100, 255), -1)

            #displays video
            cv2.imshow("Air Drawing", combined) 

            #checks if the key pressed is esc
            if cv2.waitKey(1) == 27: 
                break

            _,buffer = cv2.imencode('.jpg', combined) #converts cv froame to jpeg
            #converts jpeg into text string to be sent over the internet
            # base64 turns raw bites into safe text characters 
            # .decode('utf-8') makes it into regular python string 
            encoded = base64.b64encode(buffer).decode('utf-8')

            #makes generate() a generator, yield sends one frame then pauses and waits for the other frame
            yield f"data: {encoded}\n\n"
        #wraps generator in response object and tells the browser that this isnt a one time response
    return Response(generate(), mimetype = 'text/event-stream')


# ── Game helper functions ──────────────────────────────────────────────────

def pick_next_drawer():
    """Rotate through the player list so everyone gets a turn to draw."""
    players = list(game["players"].keys())
    game["drawer"] = players[game["drawer_index"] % len(players)]
    game["drawer_index"] += 1

def end_round():
    """Announce the word and reset per-round state."""
    game["chat"].append(f"--- Round {game['round']} over! The word was: {game['word']} ---")
    game["guessed_correctly"] = []
    game["word"] = None
    game["drawer"] = None

def game_loop():
    for round_num in range(1, game["max_rounds"] + 1):
        game["round"] = round_num

        #countdown shown to all players
        for i in range(COUNTDOWN_SECS, 0, -1):
            game["countdown"] = i
            time.sleep(1)
        game["countdown"] = 0

        # Pick who draws and what word
        pick_next_drawer()
        game["word"] = random.choice(WORDS)
        game["round_start_time"] = time.time()
        game["time_left"] = ROUND_TIME
        game["chat"].append(f"--- Round {round_num} starts! {game['drawer']} is drawing ---")

        # Tick the timer down every second
        while game["time_left"] > 0 and game["game_started"]:
            time.sleep(1)
            game["time_left"] = max(0, ROUND_TIME - int(time.time() - game["round_start_time"]))

            # End early if everyone has already guessed correctly
            non_drawers = [p for p in game["players"] if p != game["drawer"]]
            if non_drawers and all(p in game["guessed_correctly"] for p in non_drawers):
                break

        end_round()

    # All rounds finished
    game["game_started"] = False
    game["game_over"] = True
    game["chat"].append("🌟 Game over! Check the final scores.")


# API routes

@app.route('/join', methods=['POST'])
def join():
    #player enteres room
    username = request.json.get("username", "").strip()
    if not username:
        return jsonify({"error": "Username is required"}), 400
    if username in game["players"]:
        return jsonify({"error": "Username already taken"}), 400

    game["players"][username] = {"score": 0}
    return jsonify({"message": "joined"})


@app.route('/start', methods=['POST'])
def start():
    #any player can start
    if game["game_started"] or game["game_over"]:
        return jsonify({"error": "Game already started or finished"}), 400
    if len(game["players"]) < 2:
        return jsonify({"error": "Need at least 2 players"}), 400

    # Reset scores and state before starting
    for p in game["players"]:
        game["players"][p]["score"] = 0
    game.update({
        "chat": [],
        "round": 1,
        "drawer_index": 0,
        "guessed_correctly": [],
        "game_started": True,
        "game_over": False,
    })

    # Run the game loop in a background thread so Flask stays responsive
    Thread(target=game_loop, daemon=True).start()
    return jsonify({"message": "game started"})


@app.route('/state')
def state():
    """
    React polls this every 600ms to sync everyone's screen.
    The drawer sees the real word; guessers see blanks like '_ _ _ _'.
    """
    username = request.args.get("username", "")

    # Show blanks to guessers so they can count letters
    if game["word"]:
        masked = "_ " * len(game["word"])
    else:
        masked = ""

    return jsonify({
        "players":           game["players"],
        "drawer":            game["drawer"],
        "round":             game["round"],
        "max_rounds":        game["max_rounds"],
        "time_left":         game["time_left"],
        "word":              game["word"] if username == game["drawer"] else masked,
        "chat":              game["chat"],
        "game_started":      game["game_started"],
        "game_over":         game["game_over"],
        "guessed_correctly": game["guessed_correctly"],
        "countdown":         game["countdown"],
    })


@app.route('/guess', methods=['POST'])
def guess():
    #A guesser submits a word. Points awarded based on how much time is left.
    data = request.json
    username = data.get("username", "")
    text = data.get("guess", "").strip()

    # Reject guesses from the drawer or repeat correct guessers
    if username == game["drawer"] or username in game["guessed_correctly"]:
        return jsonify({"correct": False})

    if game["word"] and text.lower() == game["word"].lower():
        # More time left = more points (min 10, max 120)
        points = max(10, game["time_left"] * 2)
        game["players"][username]["score"] += points
        game["guessed_correctly"].append(username)
        game["chat"].append(f"🌟 {username} guessed correctly! (+{points} pts)")
        return jsonify({"correct": True})
    else:
        game["chat"].append(f"{username}: {text}")
        return jsonify({"correct": False})


@app.route('/reset', methods=['POST'])
def reset():
    #Reset everything so players can play again without restarting the server.
    game.update({
        "players":           {},
        "drawer":            None,
        "word":              None,
        "round":             1,
        "time_left":         ROUND_TIME,
        "game_started":      False,
        "game_over":         False,
        "chat":              [],
        "guessed_correctly": [],
        "countdown":         0,
        "round_start_time":  None,
        "drawer_index":      0,
    })
    return jsonify({"message": "reset"})


if __name__ == '__main__':
    app.run(port=5000)

#☝️ Index finger — draws in selected color
#✌️ Two fingers — pauses drawing
#✌️☝️ Three fingers — eraser
#🎨 Color boxes — hover to switch between red, green, blue, yellow
#🗑️ CLR box — hover to clear the canvas