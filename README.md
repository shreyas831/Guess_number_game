# r Number Guessing Game

A lightweight Flask web application for a multiplayer number guessing game.

Players can create rooms with custom difficulty settings, share room names, and join existing games. The app tracks active rooms, game status, and player guesses in real time.

## Features

- Create and join multiplayer rooms
- Custom secret number range, max attempts, and max hints
- Room details and live game state
- Active room list with status badges
- Simple session-based multiplayer flow

## Requirements

- Python 3.11+ (recommended)
- Flask 2.3.3
- Werkzeug 2.3.7

Install dependencies:

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

## Run Locally

```bash
python flask_game.py
```

Then open:

```
http://127.0.0.1:5000
```

## Project Structure

- `flask_game.py` - main Flask application
- `requirements.txt` - Python dependencies
- `templates/` - HTML templates for the game UI

## Notes

- The app uses a simple JSON file to store multiplayer rooms and high score data.
- In production, use a proper secret key and a WSGI server such as Gunicorn or uWSGI.
- 
- <img width="667" height="575" alt="image" src="https://github.com/user-attachments/assets/4148fad4-9768-4308-b5e8-4b526dc7cea4" />


## License

This project is suitable for the Apache-2.0 License.
