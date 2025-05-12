from flask import Flask, render_template, request, jsonify, session, redirect, url_for, flash, send_file # type: ignore
import pandas as pd # type: ignore
from datetime import datetime
import re
import requests # type: ignore
import os
import sqlite3
import uuid
import hashlib
import json
from werkzeug.security import generate_password_hash, check_password_hash # type: ignore

app = Flask(__name__)
app.secret_key = 'fertilizer_recommendation_key'

# Define the states of the conversation
WELCOME = 0
ASK_SOIL = 1
ASK_CROP = 2
ASK_LOCATION = 3  # New state for asking location
ASK_NITROGEN = 4
ASK_PHOSPHORUS = 5
ASK_POTASSIUM = 6
RECOMMENDATION = 7

# Weather API configuration
WEATHER_API_KEY = 'e15394b4e13546e1822110812252203'
WEATHER_API_URL = 'http://api.weatherapi.com/v1/current.json'
WEATHER_API_SEARCH_URL = 'http://api.weatherapi.com/v1/search.json'

# Load fertilizer recommendations
fertilizer_df = pd.read_csv('f2.csv')

# Get valid crop types from the CSV file
VALID_CROPS = sorted(list(set(fertilizer_df['Crop_Type'].str.lower())))

# Define soil types
SOIL_TYPES = {
    'black': 'Black',
    'clayey': 'Clayey',
    'loamy': 'Loamy',
    'red': 'Red',
    'sandy': 'Sandy'
}

# Define crop types
CROP_TYPES = {
    'rice': 'Rice',
    'wheat': 'Wheat',
    'maize': 'Maize',
    'cotton': 'Cotton',
    'sugarcane': 'Sugarcane'
}

# Define Maharashtra tahsil data
MAHARASHTRA_TAHSILS = {
    "Ahmednagar": ["Akole", "Jamkhed", "Karjat", "Kopargaon", "Nagar", "Nevasa", "Parner", "Pathardi", "Rahta", "Rahuri", "Sangamner", "Shevgaon", "Shrigonda", "Shrirampur"],
    "Akola": ["Akola", "Akot", "Balapur", "Barshitakli", "Murtijapur", "Patur", "Telhara"],
    "Amravati": ["Achalpur", "Amravati", "Anjangaon Surji", "Bhatkuli", "Chandur Bazar", "Chandur Railway", "Chikhaldara", "Daryapur", "Dharni", "Morshi", "Nandgaon Khandeshwar", "Teosa", "Warud"],
    "Aurangabad": ["Aurangabad", "Gangapur", "Kannad", "Khuldabad", "Paithan", "Phulambri", "Sillod", "Soegaon", "Vaijapur"],
    "Beed": ["Ambejogai", "Ashti", "Beed", "Dharur", "Georai", "Kaij", "Manjlegaon", "Parli", "Patoda", "Shirur Kasar", "Wadwani"],
    "Bhandara": ["Bhandara", "Lakhandur", "Mohadi", "Pauni", "Sakoli", "Tumsar"],
    "Buldhana": ["Buldana", "Chikhli", "Deulgaon Raja", "Jalgaon Jamod", "Khamgaon", "Lonar", "Malkapur", "Mehkar", "Motala", "Nandura", "Sangrampur", "Shegaon", "Sindkhed Raja"],
    "Chandrapur": ["Ballarpur", "Bhadravati", "Brahmapuri", "Chandrapur", "Chimur", "Gondpipri", "Jiwati", "Korpana", "Mul", "Nagbhir", "Pombhurna", "Rajura", "Sawali", "Sindewahi", "Warora"],
    "Dhule": ["Dhule", "Sakri", "Shirpur", "Sindkheda"],
    "Gadchiroli": ["Aheri", "Armori", "Bhamragad", "Chamorshi", "Desaiganj", "Dhanora", "Etapalli", "Gadchiroli", "Korchi", "Kurkheda", "Mulchera", "Sironcha"],
    "Gondia": ["Amgaon", "Arjuni Morgaon", "Deori", "Gondia", "Goregaon", "Sadak Arjuni", "Salekasa", "Tirora"],
    "Hingoli": ["Aundha Nagnath", "Basmath", "Hingoli", "Kalamnuri", "Sengaon"],
    "Jalgaon": ["Amalner", "Bhusawal", "Bodvad", "Chalisgaon", "Chopda", "Dharangaon", "Erandol", "Jalgaon", "Jamner", "Muktainagar", "Pachora", "Parola", "Raver", "Yawal"],
    "Jalna": ["Ambad", "Badnapur", "Bhokardan", "Ghansawangi", "Jafferabad", "Jalna", "Mantha", "Partur"],
    "Kolhapur": ["Ajra", "Bavda", "Bhudargad", "Chandgad", "Gadhinglaj", "Hatkanangle", "Kagal", "Karvir", "Panhala", "Radhanagari", "Shahuwadi", "Shirol"],
    "Latur": ["Ahmadpur", "Ausa", "Chakur", "Deoni", "Jalkot", "Latur", "Nilanga", "Renapur", "Shirur Anantpal", "Udgir"],
    "Mumbai City": ["Mumbai"],
    "Mumbai Suburban": ["Andheri", "Borivali", "Kurla"],
    "Nagpur": ["Bhiwapur", "Hingna", "Kamptee", "Katol", "Kuhi", "Mauda", "Nagpur (Rural)", "Nagpur (Urban)", "Narkhed", "Parseoni", "Ramtek", "Savner", "Umred"],
    "Nanded": ["Ardhapur", "Bhokar", "Biloli", "Deglur", "Dharmabad", "Hadgaon", "Himayatnagar", "Kandhar", "Kinwat", "Loha", "Mahoor", "Mudkhed", "Mukhed", "Naigaon", "Nanded", "Umri"],
    "Nandurbar": ["Akkalkuwa", "Akrani", "Nandurbar", "Nawapur", "Shahada", "Taloda"],
    "Nashik": ["Baglan", "Chandvad", "Deola", "Dindori", "Igatpuri", "Kalwan", "Malegaon", "Nandgaon", "Nashik", "Niphad", "Peint", "Sinnar", "Surgana", "Trimbakeshwar", "Yevla"],
    "Osmanabad": ["Bhum", "Kalamb", "Lohara", "Osmanabad", "Paranda", "Tuljapur", "Umarga", "Washi"],
    "Palghar": ["Dahanu", "Jawhar", "Mokhada", "Palghar", "Talasari", "Vada", "Vasai", "Vikramgad"],
    "Parbhani": ["Gangakhed", "Jintur", "Manwath", "Palam", "Parbhani", "Pathri", "Purna", "Sailu", "Sonpeth"],
    "Pune": ["Ambegaon", "Baramati", "Bhor", "Daund", "Haveli", "Indapur", "Junnar", "Khed", "Maval", "Mulshi", "Pune City", "Purandhar", "Shirur", "Velhe"],
    "Raigad": ["Alibag", "Karjat", "Khalapur", "Mahad", "Mangaon", "Mhasala", "Murud", "Panvel", "Pen", "Poladpur", "Roha", "Shrivardhan", "Sudhagad", "Tala", "Uran"],
    "Ratnagiri": ["Chiplun", "Dapoli", "Guhagar", "Khed", "Lanja", "Mandangad", "Rajapur", "Ratnagiri", "Sangameshwar"],
    "Sangli": ["Atpadi", "Jat", "Kadegaon", "Kavathemahankal", "Khanapur", "Miraj", "Palus", "Shirala", "Tasgaon", "Walwa"],
    "Satara": ["Jaoli", "Karad", "Khandala", "Khatav", "Koregaon", "Mahabaleshwar", "Man", "Patan", "Phaltan", "Satara", "Wai"],
    "Sindhudurg": ["Devgad", "Dodamarg", "Kankavli", "Kudal", "Malwan", "Sawantwadi", "Vaibhavvadi", "Vengurla"],
    "Solapur": ["Akkalkot", "Barshi", "Karmala", "Madha", "Malshiras", "Mangalvedhe", "Mohol", "Pandharpur", "Sangola", "Solapur North", "Solapur South"],
    "Thane": ["Ambarnath", "Bhiwandi", "Kalyan", "Murbad", "Shahapur", "Thane", "Ulhasnagar"],
    "Wardha": ["Arvi", "Ashti", "Deoli", "Hinganghat", "Karanja", "Samudrapur", "Seloo", "Wardha"],
    "Washim": ["Karanja", "Malegaon", "Mangrulpir", "Manora", "Risod", "Washim"],
    "Yavatmal": ["Arni", "Babulgaon", "Darwha", "Digras", "Ghatanji", "Kalamb", "Kelapur", "Mahagaon", "Maregaon", "Ner", "Pusad", "Ralegaon", "Umarkhed", "Wani", "Yavatmal", "Zari Jamani"]
}

# Database setup
def init_db():
    # Create database if it doesn't exist
    conn = sqlite3.connect('fertilizer_system.db')
    cursor = conn.cursor()
    
    # Create users table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    # Create chat history table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS chat_history (
        id TEXT PRIMARY KEY,
        user_id INTEGER NOT NULL,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        soil_type TEXT,
        crop TEXT,
        location TEXT,
        temperature REAL,
        humidity REAL,
        moisture REAL,
        nitrogen REAL,
        phosphorus REAL,
        potassium REAL,
        recommendation TEXT,
        messages TEXT,
        FOREIGN KEY (user_id) REFERENCES users (id)
    )
    ''')
    
    conn.commit()
    conn.close()

# Initialize database
init_db()

@app.route('/')
def home():
    if 'user_id' in session:
        return render_template('plantindex.html')
    return redirect(url_for('login'))

@app.route('/welcome')
def welcome():
    # This route is accessible without login and serves as an entry point
    return render_template('welcome.html')

@app.route('/detail')
def detail():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('Detail.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        conn = sqlite3.connect('fertilizer_system.db')
        cursor = conn.cursor()
        cursor.execute('SELECT id, password FROM users WHERE username = ?', (username,))
        user = cursor.fetchone()
        conn.close()
        
        if user and check_password_hash(user[1], password):
            session['user_id'] = user[0]
            session['username'] = username
            return redirect(url_for('home'))
        else:
            return render_template('login.html', error='Invalid username or password')
    
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        
        if password != confirm_password:
            return render_template('register.html', error='Passwords do not match')
        
        # Hash the password
        hashed_password = generate_password_hash(password)
        
        conn = sqlite3.connect('fertilizer_system.db')
        cursor = conn.cursor()
        
        try:
            cursor.execute(
                'INSERT INTO users (username, email, password) VALUES (?, ?, ?)',
                (username, email, hashed_password)
            )
            conn.commit()
            conn.close()
            
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            conn.close()
            return render_template('register.html', error='Username or email already exists')
    
    return render_template('register.html')

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    session.pop('username', None)
    session.pop('chat_data', None)
    session.pop('state', None)
    return redirect(url_for('welcome'))

@app.route('/model1')
def model1():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    # Clear any existing chat session when loading the page
    session.pop('chat_data', None)
    session.pop('state', None)
    return render_template('Model1.html')

@app.route('/history')
def history():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    page = request.args.get('page', 1, type=int)
    per_page = 5  # Number of history items per page
    
    conn = sqlite3.connect('fertilizer_system.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Get total count of history items for this user
    cursor.execute('SELECT COUNT(*) FROM chat_history WHERE user_id = ?', (session['user_id'],))
    total_items = cursor.fetchone()[0]
    
    # Calculate total pages
    total_pages = (total_items + per_page - 1) // per_page
    
    # Get paginated history items
    offset = (page - 1) * per_page
    cursor.execute(
        'SELECT * FROM chat_history WHERE user_id = ? ORDER BY timestamp DESC LIMIT ? OFFSET ?',
        (session['user_id'], per_page, offset)
    )
    history_rows = cursor.fetchall()
    
    history_items = []
    for row in history_rows:
        item = dict(row)
        # Parse messages from JSON string
        item['messages'] = json.loads(item['messages']) if item['messages'] else []
        history_items.append(item)
    
    conn.close()
    
    return render_template(
        'history.html', 
        history_items=history_items, 
        current_page=page, 
        total_pages=total_pages
    )

@app.route('/export_excel', defaults={'history_id': None})
@app.route('/export_excel/<history_id>')
def export_excel(history_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    conn = sqlite3.connect('fertilizer_system.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    if history_id:
        # Export a single history item
        cursor.execute(
            'SELECT * FROM chat_history WHERE id = ? AND user_id = ?',
            (history_id, session['user_id'])
        )
        rows = cursor.fetchall()
        filename = f'fertilizer_recommendation_{history_id}.xlsx'
    else:
        # Export all history items for this user
        cursor.execute(
            'SELECT * FROM chat_history WHERE user_id = ? ORDER BY timestamp DESC',
            (session['user_id'],)
        )
        rows = cursor.fetchall()
        filename = f'fertilizer_recommendations_{session["user_id"]}.xlsx'
    
    # Create appropriate directories for file storage
    os.makedirs('exports', exist_ok=True)
    filepath = os.path.join('exports', filename)
    
    # Convert rows to list of dictionaries for pandas
    data = [dict(row) for row in rows]
    
    # Create a writer to save the Excel file with formatting
    try:
        # Format data for Excel report
        excel_data = []
        for item in data:
            # Parse messages from JSON if needed
            if isinstance(item['messages'], str):
                try:
                    messages = json.loads(item['messages'])
                except:
                    messages = []
            else:
                messages = item['messages'] if item['messages'] else []
            
            # Prepare row for export
            row_data = {
                'Date': item['timestamp'],
                'Soil Type': item['soil_type'],
                'Crop': item['crop'],
                'Location': item['location'],
                'Temperature (°C)': item['temperature'],
                'Humidity (%)': item['humidity'],
                'Moisture (mm)': item['moisture'],
                'Nitrogen (kg/ha)': item['nitrogen'],
                'Phosphorus (kg/ha)': item['phosphorus'],
                'Potassium (kg/ha)': item['potassium'],
                'Recommended Fertilizer': item['recommendation']
            }
            excel_data.append(row_data)
        
        # Create DataFrame and save to Excel
        df = pd.DataFrame(excel_data)
        
        # Create Excel writer with formatted columns
        with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Recommendations', index=False)
            
            # Get the workbook and worksheet objects
            workbook = writer.book
            worksheet = writer.sheets['Recommendations']
            
            # Auto-adjust columns width to fit content
            for idx, col in enumerate(df.columns):
                column_len = max(df[col].astype(str).map(len).max(), len(col) + 2)
                worksheet.column_dimensions[chr(65 + idx)].width = column_len
        
        # Return the file as a download attachment
        return send_file(filepath, as_attachment=True, download_name=filename)
    
    except Exception as e:
        print(f"Error creating Excel export: {e}")
        return redirect(url_for('history'))

@app.route('/test-jalgaon-locations')
def test_jalgaon_locations():
    """Test route to show all Jalgaon locations from the API"""
    search_term = "jalgaon"
    try:
        params = {
            'key': WEATHER_API_KEY,
            'q': search_term
        }
        response = requests.get(WEATHER_API_SEARCH_URL, params=params)
        if response.status_code == 200:
            locations = response.json()
            result = "<h2>Locations in and around Jalgaon</h2><ul>"
            
            if locations:
                for loc in locations:
                    name = loc.get('name', '')
                    region = loc.get('region', '')
                    country = loc.get('country', '')
                    formatted_name = f"{name}, {region}, {country}"
                    result += f"<li>{formatted_name}</li>"
            else:
                result += "<li>No locations found for 'Jalgaon'</li>"
                
            result += "</ul>"
            return result
        else:
            return f"Error: {response.status_code}"
    except Exception as e:
        return f"Error: {str(e)}"

@app.route('/maharashtra-locations')
def maharashtra_locations():
    """Display Maharashtra locations organized by district and tahsil"""
    result = "<html><head><title>Maharashtra Locations by Tahsil</title>"
    result += "<style>body{font-family:Arial;margin:20px;} h1{color:#006400;} h2{color:#228B22;margin-top:30px;} "
    result += "h3{color:#2E8B57;} ul{list-style-type:none;} li{margin:5px 0;} "
    result += ".district{background:#f0f8ff;padding:15px;margin-bottom:20px;border-radius:5px;} "
    result += ".tahsil{background:#f5fffa;padding:10px;margin:10px 0;border-radius:5px;}</style></head>"
    result += "<body><h1>Maharashtra Locations by District and Tahsil</h1>"
    
    # Add a short description
    result += "<p>This page lists all districts and tahsils in Maharashtra state that can be used with our fertilizer recommendation system.</p>"
    
    # Sort districts alphabetically
    sorted_districts = sorted(MAHARASHTRA_TAHSILS.keys())
    
    for district in sorted_districts:
        result += f"<div class='district'><h2>District: {district}</h2>"
        result += "<ul>"
        
        # Sort tahsils alphabetically within each district
        sorted_tahsils = sorted(MAHARASHTRA_TAHSILS[district])
        for tahsil in sorted_tahsils:
            full_name = f"{tahsil}, {district}, Maharashtra"
            result += f"<li class='tahsil'><h3>{tahsil}</h3>"
            result += f"Location name to use in chatbot: <strong>{full_name}</strong></li>"
        
        result += "</ul></div>"
    
    result += "</body></html>"
    return result

@app.route('/search-maharashtra-locations')
def search_maharashtra_locations():
    """Display a page to search Maharashtra locations"""
    search_term = request.args.get('term', '').lower()
    
    result = "<html><head><title>Search Maharashtra Locations</title>"
    result += "<style>body{font-family:Arial;margin:20px;} h1{color:#006400;} form{margin:20px 0;} "
    result += "input[type=text]{padding:8px;width:300px;} input[type=submit]{padding:8px 15px;background:#4CAF50;color:white;border:none;cursor:pointer;} "
    result += ".results{margin-top:20px;} .location{background:#f5fffa;padding:10px;margin:10px 0;border-radius:5px;}</style></head>"
    result += "<body><h1>Search Maharashtra Locations</h1>"
    
    # Search form
    result += "<form method='get' action='/search-maharashtra-locations'>"
    result += f"<input type='text' name='term' value='{search_term}' placeholder='Enter tahsil or district name...'>"
    result += "<input type='submit' value='Search'>"
    result += "</form>"
    
    if search_term:
        result += "<div class='results'><h2>Search Results:</h2>"
        found = False
        
        for district, tahsils in MAHARASHTRA_TAHSILS.items():
            district_lower = district.lower()
            
            # Check if the search term matches the district
            if search_term in district_lower:
                found = True
                result += f"<div class='location'><h3>District: {district}</h3><ul>"
                for tahsil in sorted(tahsils):
                    full_name = f"{tahsil}, {district}, Maharashtra"
                    result += f"<li>{tahsil} - Use: <strong>{full_name}</strong></li>"
                result += "</ul></div>"
            else:
                # Check if the search term matches any tahsil in this district
                matching_tahsils = [t for t in tahsils if search_term in t.lower()]
                if matching_tahsils:
                    found = True
                    result += f"<div class='location'><h3>District: {district}</h3><ul>"
                    for tahsil in sorted(matching_tahsils):
                        full_name = f"{tahsil}, {district}, Maharashtra"
                        result += f"<li>{tahsil} - Use: <strong>{full_name}</strong></li>"
                    result += "</ul></div>"
        
        if not found:
            result += "<p>No locations found matching your search term.</p>"
        
        result += "</div>"
    
    result += "<p><a href='/maharashtra-locations'>View all Maharashtra locations</a></p>"
    result += "</body></html>"
    return result

@app.route('/chat', methods=['POST'])
def chat():
    try:
        # Get user message - handle both JSON and form data
        data = request.json or {}
        user_message = data.get('message', '')
        if not user_message and request.form:
            user_message = request.form.get('user_message', '')
        
        # Check for restart commands
        if user_message.strip() in ['\\', '/']:
            # Reset conversation
            session['state'] = WELCOME
            session['chat_data'] = {}
            return jsonify({'response': "Welcome to the Fertilizer Recommendation System! What type of soil do you have? (e.g., Red, Black, Sandy, Clayey, Loamy)"})
        
        # Get current state
        current_state = session.get('state', WELCOME)
        
        # Get current chat data
        chat_data = session.get('chat_data', {})
        
        # Handle initialization request - empty message or init_chat is treated as initialization
        if not user_message or user_message == 'init_chat' or current_state == WELCOME:
            # Clear any existing session data for a fresh start
            session.pop('chat_data', None)
            session.pop('state', None)
            session['chat_data'] = {}
            session['state'] = ASK_SOIL
            return jsonify({'response': "Welcome to the Fertilizer Chatbot! I'll help you find the best fertilizer for your crops. Let's start with a few questions:\n\nWhat type of soil do you have? (e.g., Sandy, Clayey, Loamy, Black, Red)"})        
        
        # Initialize chat_data if not already in session
        if 'chat_data' not in session:
            session['chat_data'] = {}
        
        # Initialize state if not already in session
        if 'state' not in session:
            session['state'] = ASK_SOIL
            return jsonify({'response': "What type of soil do you have? (e.g., Sandy, Clayey, Loamy, Black, Red)"})    
        
        # Process user message based on current state
        if current_state == ASK_SOIL:
            soil_type = user_message.lower().strip()
            valid_soil_types = ["black", "clayey", "loamy", "red", "sandy"]
            
            # Check if user's input is a valid soil type
            if any(soil in soil_type for soil in valid_soil_types):
                chat_data['soil_type'] = next((s for s in valid_soil_types if s in soil_type), soil_type)
                session['state'] = ASK_CROP
                session['chat_data'] = chat_data
                return jsonify({'response': "What crop are you planning to grow?"})
            else:
                # Invalid soil type, ask again
                return jsonify({'response': "Please enter a valid soil type: Black, Clayey, Loamy, Red, or Sandy."})
                
        elif current_state == ASK_CROP:
            # Store crop information
            if user_message.strip():
                crop = user_message.strip().lower()
                if crop in VALID_CROPS:
                    chat_data['crop'] = crop
                    session['state'] = ASK_LOCATION
                    session['chat_data'] = chat_data
                    return jsonify({'response': "What is your location?"})
                else:
                    return jsonify({'response': f"Please enter a valid crop type. Some examples include: {', '.join(VALID_CROPS)}"})
            else:
                return jsonify({'response': "Please enter the name of the crop you're planning to grow."})
        
        elif current_state == ASK_LOCATION:
            location = user_message.strip()
            if location:
                weather_data = get_weather_data(location)
                if weather_data and weather_data['success']:
                    chat_data['temperature'] = weather_data['temp_c']
                    chat_data['humidity'] = weather_data['humidity']
                    chat_data['moisture'] = weather_data['moisture']
                    chat_data['location'] = location  # Store location in chat_data
                    
                    # Create a weather info message to show the user
                    weather_info = f"Weather data for {location}:\n"
                    weather_info += f"Temperature: {weather_data['temp_c']}°C\n"
                    weather_info += f"Humidity: {weather_data['humidity']}%\n"
                    weather_info += f"Precipitation: {weather_data['moisture']} mm"
                    
                    session['state'] = ASK_NITROGEN
                    session['chat_data'] = chat_data
                    return jsonify({'response': f"{weather_info}\n\nThank you! Now, what is the nitrogen content in your soil?"})
                else:
                    error_msg = weather_data.get('error', 'Failed to retrieve weather data') if weather_data else 'Failed to connect to weather service'
                    return jsonify({'response': f"Sorry! {error_msg}. Please try again with a valid location name (like 'London', 'New York', etc)."})
            else:
                return jsonify({'response': "Please enter a valid location name (city, town, etc)."})
        
        elif current_state == ASK_NITROGEN:
            try:
                # Extract numbers from the user message
                numbers = re.findall(r'\d+(?:\.\d+)?', user_message)
                if numbers:
                    nitrogen = float(numbers[0])
                    if 0 <= nitrogen <= 150:  # Reasonable nitrogen range
                        chat_data['nitrogen'] = nitrogen
                        session['state'] = ASK_PHOSPHORUS
                        session['chat_data'] = chat_data
                        return jsonify({'response': "What is the phosphorus content in your soil?"})
                    else:
                        return jsonify({'response': "The nitrogen content seems outside a reasonable range. Please enter a value between 0 and 150."})
                else:
                    return jsonify({'response': "Please enter a valid number for nitrogen content."})
            except ValueError:
                return jsonify({'response': "Please enter a valid number for nitrogen content."})
                
        elif current_state == ASK_PHOSPHORUS:
            try:
                # Extract numbers from the user message
                numbers = re.findall(r'\d+(?:\.\d+)?', user_message)
                if numbers:
                    phosphorus = float(numbers[0])
                    if 0 <= phosphorus <= 150:  # Reasonable phosphorus range
                        chat_data['phosphorus'] = phosphorus
                        session['state'] = ASK_POTASSIUM
                        session['chat_data'] = chat_data
                        return jsonify({'response': "What is the potassium content in your soil?"})
                    else:
                        return jsonify({'response': "The phosphorus content seems outside a reasonable range. Please enter a value between 0 and 150."})
                else:
                    return jsonify({'response': "Please enter a valid number for phosphorus content."})
            except ValueError:
                return jsonify({'response': "Please enter a valid number for phosphorus content."})
        
        elif current_state == ASK_POTASSIUM:
            try:
                # Extract numbers from the user message
                numbers = re.findall(r'\d+(?:\.\d+)?', user_message)
                if numbers:
                    potassium = float(numbers[0])
                    if 0 <= potassium <= 150:  # Reasonable potassium range
                        chat_data['potassium'] = potassium
                        session['state'] = RECOMMENDATION
                        session['chat_data'] = chat_data
                        
                        # Get fertilizer recommendation
                        recommendation = get_fertilizer_recommendation(chat_data)
                        
                        if recommendation:
                            response = f"Based on your inputs, here's my recommendation:\n\n"
                            response += f"Recommended Fertilizer: **{recommendation['fertilizer']}**\n\n"
                            response += f"Recommended application rates: {recommendation['application_rate']}\n\n"
                            
                            if recommendation.get('is_estimate', False):
                                response += f"Note: This is an estimated recommendation based on {recommendation.get('estimate_basis', 'available data')}. No exact match was found for your specific combination.\n\n"
                            
                            if recommendation.get('details'):
                                response += f"Additional information: {recommendation['details']}"
                        else:
                            response = "I couldn't find a specific recommendation based on your inputs. This could be because:\n\n"
                            response += "1. The combination of soil type, crop, and soil conditions is uncommon\n"
                            response += "2. We don't have data for this specific combination\n\n"
                            response += "Please consider consulting with a local agriculture expert for personalized advice."
                        
                        # Save chat history
                        chat_id = str(uuid.uuid4())
                        
                        # Create messages array for storing in JSON format
                        message_history = session.get('message_history', [])
                        message_history.append({'type': 'user', 'content': user_message})
                        message_history.append({'type': 'bot', 'content': response})
                        
                        # Store the conversation data in the database
                        try:
                            # Get location from chat_data instead of local variable
                            user_location = chat_data.get('location', '')
                            
                            conn = sqlite3.connect('fertilizer_system.db')
                            cursor = conn.cursor()
                            cursor.execute(
                                'INSERT INTO chat_history (id, user_id, soil_type, crop, location, temperature, humidity, moisture, nitrogen, phosphorus, potassium, recommendation, messages) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
                                (chat_id, session['user_id'], chat_data['soil_type'], chat_data['crop'], user_location, 
                                 chat_data.get('temperature'), chat_data.get('humidity'), chat_data.get('moisture'),
                                 chat_data.get('nitrogen'), chat_data.get('phosphorus'), chat_data.get('potassium'), 
                                 recommendation['fertilizer'], json.dumps(message_history))
                            )
                            conn.commit()
                            conn.close()
                        except Exception as e:
                            print(f"Error saving chat history: {e}")
                        
                        # Reset the state for a new conversation
                        session['state'] = ASK_SOIL
                        session['message_history'] = []
                        return jsonify({'response': response})
                    else:
                        return jsonify({'response': "The potassium content seems outside a reasonable range. Please enter a value between 0 and 150."})
                else:
                    return jsonify({'response': "Please enter a valid number for potassium content."})
            except ValueError:
                return jsonify({'response': "Please enter a valid number for potassium content."})
        
        # Default response if state is not recognized
        return jsonify({'response': "I'm not sure how to respond. Let's start over. What type of soil do you have?"})
    
    except Exception as e:
        print(f"Error in chat: {e}")
        return jsonify({'response': "An error occurred. Let's start over. What type of soil do you have?"})

@app.route('/search-location', methods=['POST'])
def search_location():
    """Search for locations based on user input"""
    search_term = request.json.get('term', '')
    if not search_term or len(search_term) < 3:
        return jsonify([])
    
    try:
        params = {
            'key': WEATHER_API_KEY,
            'q': search_term
        }
        response = requests.get(WEATHER_API_SEARCH_URL, params=params)
        if response.status_code == 200:
            locations = response.json()
            # Format results with region and country
            formatted_locations = []
            for loc in locations:
                name = loc.get('name', '')
                region = loc.get('region', '')
                country = loc.get('country', '')
                formatted_name = f"{name}, {region}, {country}"
                formatted_locations.append({
                    'value': formatted_name,
                    'label': formatted_name
                })
            return jsonify(formatted_locations)
        else:
            return jsonify([])
    except Exception as e:
        print(f"Error searching locations: {str(e)}")
        return jsonify([])

@app.route('/delete_history/<history_id>')
def delete_history(history_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    try:
        conn = sqlite3.connect('fertilizer_system.db')
        cursor = conn.cursor()
        
        # Verify the history item belongs to the current user
        cursor.execute(
            'SELECT id FROM chat_history WHERE id = ? AND user_id = ?',
            (history_id, session['user_id'])
        )
        item = cursor.fetchone()
        
        if item:
            # Delete the history item
            cursor.execute('DELETE FROM chat_history WHERE id = ?', (history_id,))
            conn.commit()
            flash('History item deleted successfully.', 'success')
        else:
            flash('History item not found or you do not have permission to delete it.', 'error')
        
        conn.close()
    except Exception as e:
        print(f"Error deleting history: {e}")
        flash('An error occurred while deleting the history item.', 'error')
    
    return redirect(url_for('history'))

def get_weather_data(location):
    try:
        params = {
            'key': WEATHER_API_KEY,
            'q': location,
            'aqi': 'yes'  # Include air quality data
        }
        response = requests.get(WEATHER_API_URL, params=params)
        if response.status_code == 200:
            data = response.json()
            return {
                'success': True,
                'data': data,
                'temp_c': data['current']['temp_c'],
                'humidity': data['current']['humidity'],
                'moisture': data['current']['precip_mm']  # Precipitation as moisture indicator
            }
        else:
            return {
                'success': False,
                'error': f'Error retrieving weather data: {response.status_code}'
            }
    except Exception as e:
        return {
            'success': False,
            'error': f'Error: {str(e)}'
        }

def get_fertilizer_recommendation(data):
    """Get fertilizer recommendation based on user inputs."""
    try:
        # Extract user inputs
        soil_type = data.get('soil_type')
        crop = data.get('crop')
        temperature = data.get('temperature')
        humidity = data.get('humidity')  # New parameter from weather API
        moisture = data.get('moisture')  # New parameter from weather API
        nitrogen = data.get('nitrogen')
        phosphorus = data.get('phosphorus')
        potassium = data.get('potassium')
        
        # Original filtering approach
        filtered_df = fertilizer_df.copy()
        
        if soil_type:
            filtered_df = filtered_df[filtered_df['Soil_Type'].str.contains(soil_type, case=False, na=False)]
        
        if crop:
            filtered_df = filtered_df[filtered_df['Crop_Type'].str.contains(crop, case=False, na=False)]
        
        if temperature:
            temp_value = float(temperature)
            filtered_df = filtered_df[
                (filtered_df['Temparature'] >= temp_value - 10) & 
                (filtered_df['Temparature'] <= temp_value + 10)
            ]
        
        # Create a copy before further filtering for fallback
        npk_filtered_df = filtered_df.copy()
        
        # Further filter based on NPK values if available
        if nitrogen and phosphorus and potassium:
            n_value = float(nitrogen)
            p_value = float(phosphorus)
            k_value = float(potassium)
            
            # Filter by nitrogen level
            filtered_df = filtered_df[
                (filtered_df['Nitrogen'] >= n_value - 15) & 
                (filtered_df['Nitrogen'] <= n_value + 15)
            ]
            
            # Filter by phosphorus level
            filtered_df = filtered_df[
                (filtered_df['Phosphorous'] >= p_value - 15) & 
                (filtered_df['Phosphorous'] <= p_value + 15)
            ]
            
            # Filter by potassium level
            filtered_df = filtered_df[
                (filtered_df['Potassium'] >= k_value - 15) & 
                (filtered_df['Potassium'] <= k_value + 15)
            ]
        
        # Get recommendations
        if not filtered_df.empty:
            # Get diverse recommendations - choose one of the top 3 options if available
            if len(filtered_df) >= 3:
                import random
                # Select a random fertilizer type from available options
                selected_fertilizer = random.choice(filtered_df['Fertilizer'].unique())
                # Get a recommendation with that fertilizer
                recommendation = filtered_df[filtered_df['Fertilizer'] == selected_fertilizer].iloc[0]
            else:
                recommendation = filtered_df.iloc[0]
            
            # Prepare detailed recommendation with weather information
            application_rate = "Apply according to product instructions, typically 45-50kg per acre depending on soil Condition"
            
            # Adjust recommendation based on humidity and moisture
            details = "For best results, apply in the "
            
            if humidity is not None and moisture is not None:
                # Adjust timing based on humidity
                if float(humidity) > 70:
                    details += "early morning when humidity decreases. "
                else:
                    details += "early morning or late evening. "
                
                # Adjust watering advice based on moisture
                if float(moisture) < 2.0:  # Low precipitation/moisture
                    details += "Water thoroughly after application as current moisture levels are low. "
                elif float(moisture) > 10.0:  # High precipitation/moisture
                    details += "Be cautious with watering as current moisture levels are high. "
                else:
                    details += "Water moderately after application. "
            else:
                details += "early morning or late evening. Water thoroughly after application. "
                
            result = {
                'fertilizer': recommendation['Fertilizer'],
                'application_rate': application_rate,
                'details': details,
                'weather_info': {
                    'temperature': temperature,
                    'humidity': humidity,
                    'moisture': moisture
                },
                'is_estimate': False
            }
            return result
        else:
            # Try a broader matching approach with relaxed constraints
            
            # First check if we had any matches before NPK filtering
            if not npk_filtered_df.empty:
                # Get diverse recommendations - choose one of the top 3 options if available
                if len(npk_filtered_df) >= 3:
                    import random
                    # Select a random fertilizer type from available options
                    selected_fertilizer = random.choice(npk_filtered_df['Fertilizer'].unique())
                    # Get a recommendation with that fertilizer
                    recommendation = npk_filtered_df[npk_filtered_df['Fertilizer'] == selected_fertilizer].iloc[0]
                else:
                    recommendation = npk_filtered_df.iloc[0]
                
                result = {
                    'fertilizer': recommendation['Fertilizer'],
                    'application_rate': "Apply according to product instructions, typically 45-50 kg per acre depending on soil conditions.",
                    'details': "This is an estimated recommendation based on soil, crop, and temperature, without exact NPK matching. For best results, apply in the early morning or late evening.",
                    'is_estimate': True,
                    'estimate_basis': "soil type, crop, and temperature"
                }
                return result
            
            # Try to match just by crop type
            broader_df = fertilizer_df.copy()
            if crop:
                crop_df = broader_df[broader_df['Crop_Type'].str.contains(crop, case=False, na=False)]
                if not crop_df.empty:
                    # Get more diverse recommendations
                    fertilizers = crop_df['Fertilizer'].unique()
                    if len(fertilizers) > 1:
                        import random
                        # Select a random fertilizer type from available options
                        selected_fertilizer = random.choice(fertilizers)
                        # Get a recommendation with that fertilizer
                        recommendation = crop_df[crop_df['Fertilizer'] == selected_fertilizer].iloc[0]
                    else:
                        recommendation = crop_df.iloc[0]
                        
                    result = {
                        'fertilizer': recommendation['Fertilizer'],
                        'application_rate': "Apply according to product instructions, typically 45-50 kg per acre depending on soil conditions.",
                        'details': "This is an estimated recommendation based on crop type only. For best results, apply in the early morning or late evening.",
                        'is_estimate': True,
                        'estimate_basis': "crop type"
                    }
                    return result
            
            # If that fails, try to match by soil type
            if soil_type:
                soil_df = broader_df[broader_df['Soil_Type'].str.contains(soil_type, case=False, na=False)]
                if not soil_df.empty:
                    # Get more diverse recommendations
                    fertilizers = soil_df['Fertilizer'].unique()
                    if len(fertilizers) > 1:
                        import random
                        # Select a random fertilizer type from available options
                        selected_fertilizer = random.choice(fertilizers)
                        # Get a recommendation with that fertilizer
                        recommendation = soil_df[soil_df['Fertilizer'] == selected_fertilizer].iloc[0]
                    else:
                        recommendation = soil_df.iloc[0]
                        
                    result = {
                        'fertilizer': recommendation['Fertilizer'],
                        'application_rate': "Apply according to product instructions, typically 45-50 kg per acre depending on soil conditions.",
                        'details': "This is an estimated recommendation based on soil type only. For best results, apply in the early morning or late evening.",
                        'is_estimate': True,
                        'estimate_basis': "soil type"
                    }
                    return result
            
            # If all else fails, return a general recommendation based on nutrient levels
            if nitrogen and phosphorus and potassium:
                n_value = float(nitrogen)
                p_value = float(phosphorus)
                k_value = float(potassium)
                
                # Logic for general fertilizer selection based on NPK values
                if n_value > p_value and n_value > k_value:
                    # High nitrogen needs - select from nitrogen-rich fertilizers
                    nitrogen_fertilizers = ['Urea', 'DAP', '20-20', '15-15-15']
                    import random
                    result = {
                        'fertilizer': random.choice(nitrogen_fertilizers),
                        'application_rate': "Apply according to product instructions, typically 45-50 kg per acre depending on soil conditions.",
                        'details': "This is an estimated recommendation based on your soil having higher nitrogen needs. For best results, apply in the early morning or late evening.",
                        'is_estimate': True,
                        'estimate_basis': "nutrient levels"
                    }
                elif p_value > n_value and p_value > k_value:
                    # High phosphorus needs - select from phosphorus-rich fertilizers
                    phosphorus_fertilizers = ['DAP', 'TSP', 'Superphosphate', '14-35-14']
                    import random
                    result = {
                        'fertilizer': random.choice(phosphorus_fertilizers),
                        'application_rate': "Apply according to product instructions, typically 45-50 kg per acre depending on soil conditions.",
                        'details': "This is an estimated recommendation based on your soil having higher phosphorus needs. For best results, apply in the early morning or late evening.",
                        'is_estimate': True,
                        'estimate_basis': "nutrient levels"
                    }
                else:
                    # High potassium or balanced needs - select from potassium-rich or balanced fertilizers
                    potassium_fertilizers = ['Potassium sulfate.', 'Potassium chloride', '10-26-26', '17-17-17']
                    import random
                    result = {
                        'fertilizer': random.choice(potassium_fertilizers),
                        'application_rate': "Apply according to product instructions, typically 45-50 kg per acre depending on soil conditions.",
                        'details': "This is an estimated recommendation based on your soil having higher potassium or balanced nutrient needs. For best results, apply in the early morning or late evening.",
                        'is_estimate': True,
                        'estimate_basis': "nutrient levels"
                    }
                return result
            
            # If we still can't make a recommendation, use a completely random approach
            # Select a random fertilizer from the full list of available fertilizers
            import random
            all_fertilizers = sorted(list(fertilizer_df['Fertilizer'].unique()))
            result = {
                'fertilizer': random.choice(all_fertilizers),
                'application_rate': "Apply according to product instructions, typically 45-50 kg per acre depending on soil conditions.",
                'details': "This is a general recommendation as no specific match was found for your inputs. For best results, apply in the early morning or late evening.",
                'is_estimate': True,
                'estimate_basis': "general recommendation"
            }
            return result
            
    except Exception as e:
        print(f"Error in get_fertilizer_recommendation: {e}")
        return None

if __name__ == '__main__':
    app.run(debug=True)