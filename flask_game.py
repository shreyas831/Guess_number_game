from flask import Flask, render_template, request, session, redirect, url_for, flash
import random
import time
import json
import os
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'your-secret-key-change-this-in-production'

# Register strftime filter for templates
@app.template_filter('strftime')
def strftime_filter(timestamp, format_string='%H:%M:%S'):
    if timestamp:
        return datetime.fromtimestamp(timestamp).strftime(format_string)
    return 'N/A'

# Multiplayer rooms storage
ROOMS_FILE = 'multiplayer_rooms.json'
multiplayer_rooms = {}

def load_rooms():
    global multiplayer_rooms
    if os.path.exists(ROOMS_FILE):
        try:
            with open(ROOMS_FILE, 'r') as f:
                data = json.load(f)
                # Clean up old rooms (older than 1 hour)
                current_time = time.time()
                cleaned_data = {}
                for room_name, room_data in data.items():
                    if current_time - room_data.get('created_at', 0) < 3600:  # 1 hour
                        cleaned_data[room_name] = room_data
                multiplayer_rooms = cleaned_data
        except:
            multiplayer_rooms = {}

def save_rooms():
    try:
        with open(ROOMS_FILE, 'w') as f:
            json.dump(multiplayer_rooms, f)
    except:
        pass

class NumberGuessingGame:
    def __init__(self):
        self.games_played = 0
        self.games_won = 0
        self.total_attempts = 0
        self.current_streak = 0
        self.best_streak = 0
        self.best_game = None
        self.worst_game = None
        self.last_number = None
        self.achievements = []
        self.game_history = []
        self.total_score = 0
        self.difficulties = {
            '1': {'name': 'Easy', 'range': (1, 20), 'attempts': 8, 'hints': 3},
            '2': {'name': 'Medium', 'range': (1, 50), 'attempts': 6, 'hints': 2},
            '3': {'name': 'Hard', 'range': (1, 100), 'attempts': 4, 'hints': 1}
        }
        self.load_high_scores()

    def load_high_scores(self):
        if os.path.exists('highscores.json'):
            try:
                with open('highscores.json', 'r') as f:
                    data = json.load(f)
                    self.best_game = data.get('best_game')
                    self.worst_game = data.get('worst_game')
                    self.last_number = data.get('last_number')
            except:
                pass

    def save_high_scores(self):
        data = {'best_game': self.best_game, 'worst_game': self.worst_game, 'last_number': self.last_number}
        try:
            with open('highscores.json', 'w') as f:
                json.dump(data, f)
        except:
            pass

    def calculate_points(self, difficulty, attempts, max_attempts, hints_used, max_hints):
        difficulty_multiplier = {'Easy': 1, 'Medium': 2, 'Hard': 3, 'Custom': 2}[difficulty]
        base_points = 100 * difficulty_multiplier

        attempt_deduction = (attempts / max_attempts) * 20 * difficulty_multiplier
        hint_bonus = (max_hints - hints_used) * 5

        points = int(base_points - attempt_deduction + hint_bonus)
        return max(points, 10)

    def check_achievements(self, points, attempts, max_attempts, difficulty):
        new_achievement = None

        if attempts == 1 and difficulty == 'Hard':
            new_achievement = "🎯 Perfect Shot! First try on Hard mode!"
        elif self.current_streak == 3:
            new_achievement = "🔥 Hot Streak! 3 wins in a row!"
        elif self.current_streak == 5:
            new_achievement = "🌟 Legendary! 5 consecutive wins!"
        elif points >= 250:
            new_achievement = "💎 Point Master! Earned 250+ points!"
        elif self.games_won == 10:
            new_achievement = "🏆 Dedicated Player! Won 10 games!"
        elif self.games_won == 50:
            new_achievement = "👑 Champion! Won 50 games!"

        if new_achievement and new_achievement not in self.achievements:
            self.achievements.append(new_achievement)
            return new_achievement
        return None

    def get_hint(self, number, low, high):
        if number <= (low + high) // 2:
            return f"💡 Hint: The number is in the lower half ({low}-{(low + high) // 2})"
        else:
            return f"💡 Hint: The number is in the upper half ({(low + high) // 2 + 1}-{high})"

    def create_custom_difficulty(self):
        try:
            max_num = int(request.form.get('max_num', 50))
            max_attempts = int(request.form.get('max_attempts', 5))
            max_hints = int(request.form.get('max_hints', 2))

            if max_num < 2 or max_attempts < 1 or max_hints < 0:
                return self.difficulties['2']

            return {
                'name': 'Custom',
                'range': (1, max_num),
                'attempts': max_attempts,
                'hints': max_hints
            }
        except ValueError:
            return self.difficulties['2']

# Initialize game instance
game = NumberGuessingGame()

# Load multiplayer rooms on startup
load_rooms()

@app.route('/')
def index():
    return redirect(url_for('menu'))

@app.route('/menu')
def menu():
    return render_template('menu.html')

@app.route('/select_difficulty/<mode>')
def select_difficulty(mode):
    return render_template('difficulty.html', mode=mode)

@app.route('/custom_difficulty/<mode>')
def custom_difficulty(mode):
    return render_template('custom_difficulty.html', mode=mode)

@app.route('/start_game/<mode>', methods=['POST'])
def start_game(mode):
    difficulty_choice = request.form.get('difficulty')

    if difficulty_choice == '4':
        difficulty = game.create_custom_difficulty()
    else:
        difficulty = game.difficulties.get(difficulty_choice, game.difficulties['2'])

    # Initialize game session
    session['mode'] = mode
    session['difficulty'] = difficulty
    session['number'] = random.randint(*difficulty['range'])
    session['attempts'] = 0
    session['max_attempts'] = difficulty['attempts']
    session['hints_used'] = 0
    session['max_hints'] = difficulty['hints']
    session['guesses'] = []
    session['last_guess'] = None
    session['start_time'] = time.time()
    session['game_active'] = True

    return redirect(url_for('play_game'))

@app.route('/play', methods=['GET', 'POST'])
def play_game():
    if not session.get('game_active', False):
        return redirect(url_for('menu'))

    if request.method == 'POST':
        user_input = request.form.get('guess', '').strip().lower()

        if user_input == 'hint':
            if session['hints_used'] < session['max_hints']:
                session['hints_used'] += 1
                hint = game.get_hint(session['number'], *session['difficulty']['range'])
                flash(hint, 'info')
            else:
                flash("❌ No hints left! You used all hints.", 'error')
            return redirect(url_for('play_game'))

        try:
            guess = int(user_input)

            if not (session['difficulty']['range'][0] <= guess <= session['difficulty']['range'][1]):
                flash(f"❌ Please enter a number between {session['difficulty']['range'][0]} and {session['difficulty']['range'][1]}!", 'error')
                return redirect(url_for('play_game'))

            session['attempts'] += 1
            session['guesses'].append(guess)

            if guess == session['number']:
                # Game won
                elapsed_time = time.time() - session['start_time']
                points = game.calculate_points(
                    session['difficulty']['name'],
                    session['attempts'],
                    session['max_attempts'],
                    session['hints_used'],
                    session['max_hints']
                )

                game.total_score += points
                game.current_streak += 1
                if game.current_streak > game.best_streak:
                    game.best_streak = game.current_streak

                game_record = {
                    'difficulty': session['difficulty']['name'],
                    'attempts': session['attempts'],
                    'points': points,
                    'time': elapsed_time
                }

                if not game.best_game or points > game.best_game['points']:
                    game.best_game = game_record
                if not game.worst_game or points < game.worst_game['points']:
                    game.worst_game = game_record

                if session.get('mode') == 'multiplayer':
                    achievement = None
                    # Update room status for multiplayer
                    if session.get('room') in multiplayer_rooms:
                        room_data = multiplayer_rooms[session['room']]
                        room_data['game_finished'] = True
                        room_data['end_time'] = time.time()
                        room_data['winner'] = session.get('username', 'Guesser')
                        room_data['final_attempts'] = session['attempts']
                        room_data['final_time'] = elapsed_time
                        room_data['guesses'] = session['guesses']
                        save_rooms()
                else:
                    achievement = game.check_achievements(points, session['attempts'], session['max_attempts'], session['difficulty']['name'])

                game.games_won += 1
                game.total_attempts += session['attempts']
                game.games_played += 1
                game.last_number = session['number']
                game.save_high_scores()
                game.game_history.append(game_record)

                session['game_active'] = False

                return render_template('game_won.html',
                                     attempts=session['attempts'],
                                     guesses=session['guesses'],
                                     points=points,
                                     time=elapsed_time,
                                     achievement=achievement)

            else:
                # Game continues
                feedback = ""
                if guess < session['number']:
                    feedback = "📉 Too low! Try a higher number."
                else:
                    feedback = "📈 Too high! Try a lower number."

                flash(feedback, 'info')

                if session['attempts'] >= session['max_attempts']:
                    # Game lost
                    elapsed_time = time.time() - session['start_time']
                    game.current_streak = 0
                    game.games_played += 1
                    game.last_number = session['number']
                    game.save_high_scores()

                    game.game_history.append({
                        'difficulty': session['difficulty']['name'],
                        'attempts': session['attempts'],
                        'points': 0,
                        'time': elapsed_time,
                        'won': False
                    })

                    # Update room status for multiplayer
                    if session.get('mode') == 'multiplayer' and session.get('room') in multiplayer_rooms:
                        room_data = multiplayer_rooms[session['room']]
                        room_data['game_finished'] = True
                        room_data['end_time'] = time.time()
                        room_data['winner'] = None  # No winner
                        room_data['final_attempts'] = session['attempts']
                        room_data['final_time'] = elapsed_time
                        room_data['guesses'] = session['guesses']
                        save_rooms()

                    session['game_active'] = False

                    return render_template('game_lost.html',
                                         number=session['number'],
                                         guesses=session['guesses'],
                                         time=elapsed_time)

                return redirect(url_for('play_game'))

        except ValueError:
            flash("❌ Please enter a valid number!", 'error')
            return redirect(url_for('play_game'))

    # GET request - show game interface
    progress = "█" * session['attempts'] + "░" * (session['max_attempts'] - session['attempts'])
    return render_template('play.html',
                         difficulty=session['difficulty'],
                         attempts=session['attempts'],
                         max_attempts=session['max_attempts'],
                         hints_used=session['hints_used'],
                         max_hints=session['max_hints'],
                         progress=progress,
                         mode=session['mode'],
                         guesses=session['guesses'])

@app.route('/stats')
def stats():
    win_rate = (game.games_won / game.games_played * 100) if game.games_played > 0 else 0
    avg_attempts = game.total_attempts / game.games_won if game.games_won > 0 else 0

    return render_template('stats.html',
                         games_played=game.games_played,
                         games_won=game.games_won,
                         win_rate=win_rate,
                         avg_attempts=avg_attempts,
                         total_score=game.total_score,
                         current_streak=game.current_streak,
                         best_streak=game.best_streak,
                         best_game=game.best_game,
                         worst_game=game.worst_game,
                         last_number=game.last_number,
                         achievements_count=len(game.achievements))

@app.route('/achievements')
def achievements():
    return render_template('achievements.html', achievements=game.achievements)

@app.route('/reset')
def reset_game():
    session.clear()
    return redirect(url_for('menu'))

@app.route('/multiplayer')
def multiplayer():
    # Clean up old rooms
    current_time = time.time()
    rooms_to_delete = []
    for room_name, room_data in multiplayer_rooms.items():
        if current_time - room_data.get('created_at', 0) > 3600:  # 1 hour
            rooms_to_delete.append(room_name)
    
    for room_name in rooms_to_delete:
        del multiplayer_rooms[room_name]
    
    if rooms_to_delete:
        save_rooms()
    
    # Get active rooms for display
    active_rooms = []
    for room_name, room_data in multiplayer_rooms.items():
        status = 'waiting'
        if room_data.get('game_started', False):
            if room_data.get('game_finished', False):
                status = 'finished'
            else:
                status = 'in_progress'
        
        active_rooms.append({
            'name': room_name,
            'status': status,
            'difficulty': room_data['difficulty']['name'],
            'range': room_data['difficulty']['range'],
            'created_at': room_data.get('created_at', 0),
            'players': len(room_data.get('players', []))
        })
    
    # Sort by creation time (newest first)
    active_rooms.sort(key=lambda x: x['created_at'], reverse=True)
    
    return render_template('multiplayer.html', active_rooms=active_rooms)

@app.route('/create_room', methods=['POST'])
def create_room():
    room_name = request.form['room_name'].strip()
    secret_number = int(request.form['secret_number'])
    min_num = int(request.form['min_num'])
    max_num = int(request.form['max_num'])
    max_attempts = int(request.form['max_attempts'])
    max_hints = int(request.form['max_hints'])

    if not room_name:
        flash('Room name cannot be empty', 'error')
        return redirect(url_for('multiplayer'))

    if room_name in multiplayer_rooms:
        flash('Room already exists', 'error')
        return redirect(url_for('multiplayer'))

    if not (min_num < secret_number <= max_num):
        flash('Secret number must be between min and max (inclusive)', 'error')
        return redirect(url_for('multiplayer'))

    # Validate inputs
    if max_num - min_num < 1 or max_attempts < 1 or max_hints < 0:
        flash('Invalid game parameters', 'error')
        return redirect(url_for('multiplayer'))

    multiplayer_rooms[room_name] = {
        'number': secret_number,
        'difficulty': {
            'name': 'Custom',
            'range': (min_num, max_num),
            'attempts': max_attempts,
            'hints': max_hints
        },
        'created_at': time.time(),
        'creator': session.get('username', 'Anonymous'),
        'players': [],
        'game_started': False,
        'game_finished': False,
        'winner': None,
        'guesses': [],
        'start_time': None,
        'end_time': None
    }

    save_rooms()

    session['room'] = room_name
    session['role'] = 'setter'
    flash(f'Room "{room_name}" created! Share this room name with your friend.', 'success')
    return redirect(url_for('menu'))

@app.route('/join_room', methods=['POST'])
def join_room():
    room_name = request.form.get('room_name', '').strip()

    if not room_name or room_name not in multiplayer_rooms:
        flash('Room not found', 'error')
        return redirect(url_for('multiplayer'))

    room_data = multiplayer_rooms[room_name]

    if room_data.get('game_finished'):
        flash('This room is already finished.', 'warning')
        return redirect(url_for('room_details', room_name=room_name))

    if room_data.get('game_started'):
        flash('Game already in progress. You cannot join now.', 'warning')
        return redirect(url_for('room_details', room_name=room_name))

    username = session.get('username', 'Anonymous')
    if username not in room_data.get('players', []):
        room_data.setdefault('players', []).append(username)

    session['mode'] = 'multiplayer'
    session['room'] = room_name
    session['role'] = 'guesser'
    session['difficulty'] = room_data['difficulty']
    session['number'] = room_data['number']
    session['attempts'] = 0
    session['max_attempts'] = room_data['difficulty']['attempts']
    session['hints_used'] = 0
    session['max_hints'] = room_data['difficulty']['hints']
    session['guesses'] = []
    session['last_guess'] = None
    session['start_time'] = time.time()
    session['game_active'] = True

    room_data['game_started'] = True
    room_data['start_time'] = session['start_time']
    save_rooms()

    flash(f'Joined room "{room_name}"! Good luck.', 'success')
    return redirect(url_for('play_game'))

@app.route('/room/<room_name>')
def room_details(room_name):
    if room_name not in multiplayer_rooms:
        flash('Room not found', 'error')
        return redirect(url_for('multiplayer'))
    
    room_data = multiplayer_rooms[room_name]
    return render_template('room_details.html', room_name=room_name, room_data=room_data)

@app.route('/delete_room/<room_name>', methods=['POST'])
def delete_room(room_name):
    if room_name in multiplayer_rooms:
        # Only allow creator or admin to delete
        room_data = multiplayer_rooms[room_name]
        if room_data.get('creator') == session.get('username', 'Anonymous') or session.get('admin', False):
            del multiplayer_rooms[room_name]
            save_rooms()
            flash(f'Room "{room_name}" deleted successfully', 'success')
        else:
            flash('You can only delete rooms you created', 'error')
    else:
        flash('Room not found', 'error')
    
    return redirect(url_for('multiplayer'))

@app.route('/set_username', methods=['POST'])
def set_username():
    username = request.form.get('username', '').strip()
    if username and len(username) <= 20:
        session['username'] = username
        flash(f'Username set to: {username}', 'success')
    else:
        flash('Invalid username (1-20 characters)', 'error')
    
    return redirect(request.referrer or url_for('menu'))

@app.route('/signout')
def signout():
    if 'username' in session:
        username = session['username']
        session.pop('username', None)
        flash(f'Signed out successfully. Goodbye {username}!', 'info')
    else:
        flash('You are not signed in.', 'warning')
    
    return redirect(url_for('menu'))

if __name__ == '__main__':
    app.run(debug=True)