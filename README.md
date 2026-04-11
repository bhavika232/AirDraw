Air Drawing Pictionary 🎨

This is a simple air-drawing based Pictionary game where you draw in the air using your hand and the system tries to recognize what you’re drawing. It’s basically a mix of gesture tracking and a guessing game.

I built this to experiment with computer vision and make something interactive instead of just another static project.

---

How it works 🧠

- The camera tracks your hand movements  
- You draw letters or shapes in the air  
- The system captures the motion  
- It then tries to interpret what you drew  

---

Rules / How to play 🎮

1. Make sure your camera is on and clearly visible  
2. Start the program and wait for it to detect your hand  
3. Use one finger (preferably index) to draw in the air  
4. Draw slowly and clearly — messy drawings confuse the model  
5. Keep your hand within the camera frame  
6. Each round, draw the given word (or choose one yourself)  
7. The system will try to guess what you drew  

Optional:
- One person draws, others guess  
- You can add a timer for each round ⏱️  

---

Tech Stack 🛠️

- Python  
- OpenCV  
- Mediapipe for real time hand tracking 

---

## How to run ▶️

1. Clone the repo  
   ```bash
   git clone https://github.com/your-username/your-repo-name.git
2. Go to the project folder
    cd your-repo-name
3. install all dependencies
     pip install -r requirements.txt
4. run the program
     python app.py

Notes ⚠️
Works best in good lighting
Plain background helps with detection
Performance depends on camera quality
