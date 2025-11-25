import os
import json
import logging
import time
import requests
import base64
from io import BytesIO
from datetime import datetime
from flask import Flask, render_template, request, jsonify, send_file, session, redirect, url_for, flash
from flask_cors import CORS
import google.generativeai as genai
from dotenv import load_dotenv
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from authlib.integrations.flask_client import OAuth
import secrets
import tempfile
from moviepy.editor import ImageClip, AudioFileClip, CompositeVideoClip, TextClip, ColorClip
import requests
import os
from PIL import Image, ImageDraw, ImageFont
import numpy as np
import textwrap

# Load environment variables
load_dotenv()

# Allow OAuth over HTTP for local testing
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

# Configure Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

app = Flask(__name__)
CORS(app)

# Configuration
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'your-secret-key-change-this')
app.config['GOOGLE_CLIENT_ID'] = os.getenv('GOOGLE_CLIENT_ID', '').strip()
app.config['GOOGLE_CLIENT_SECRET'] = os.getenv('GOOGLE_CLIENT_SECRET', '').strip()

if not app.config['GOOGLE_CLIENT_ID'] or "your_google_client_id" in app.config['GOOGLE_CLIENT_ID']:
    logging.error("❌ GOOGLE_CLIENT_ID is not set or is still the default placeholder!")
    logging.error("👉 Please update your .env file with your actual Google Cloud credentials.")

# OAuth Setup
# OAuth Setup
# HARDCODED CREDENTIALS FOR DEBUGGING
GOOGLE_CLIENT_ID = '1045996945878-mod025k39cevdbiucbrfr2b2fdapgfdd.apps.googleusercontent.com'
GOOGLE_CLIENT_SECRET = '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'

oauth = OAuth(app)
google = oauth.register(
    name='google',
    client_id=GOOGLE_CLIENT_ID,
    client_secret=GOOGLE_CLIENT_SECRET,
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={'scope': 'openid email profile'},
)

# Database Configuration
database_url = os.getenv('DATABASE_URL', 'sqlite:///vibecheck.db')
# Fix for Render's Postgres URL (SQLAlchemy requires postgresql://)
if database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)

app.config['SQLALCHEMY_DATABASE_URI'] = database_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize Extensions
db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# --- DATABASE MODELS ---
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(150), unique=True, nullable=False)
    name = db.Column(db.String(150), nullable=False)
    password = db.Column(db.String(150), nullable=True) # Nullable for Google users
    google_id = db.Column(db.String(100), unique=True, nullable=True)
    profile_pic = db.Column(db.String(500), nullable=True)
    invitations = db.relationship('Invitation', backref='author', lazy=True)

class Invitation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    body = db.Column(db.Text, nullable=True)
    image_url = db.Column(db.String(500), nullable=False)
    event_type = db.Column(db.String(50), nullable=False)
    vibe = db.Column(db.String(50), nullable=False)
    date_created = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    # New enhanced features
    family_name = db.Column(db.String(200), nullable=True)  # Family name
    celebrant_name = db.Column(db.String(200), nullable=True)  # Name of person being celebrated
    event_date = db.Column(db.String(100), nullable=True)  # Event date
    event_time = db.Column(db.String(100), nullable=True)  # Event time
    event_venue = db.Column(db.String(300), nullable=True)  # Event venue
    event_message = db.Column(db.Text, nullable=True)  # Custom message
    gallery_photos = db.Column(db.Text, nullable=True)  # JSON array of photo URLs
    location_name = db.Column(db.String(200), nullable=True)
    location_address = db.Column(db.String(500), nullable=True)
    location_lat = db.Column(db.Float, nullable=True)
    location_lng = db.Column(db.Float, nullable=True)
    voice_message_url = db.Column(db.String(500), nullable=True)
    share_link = db.Column(db.String(100), unique=True, nullable=True)  # Unique shareable link
    view_count = db.Column(db.Integer, default=0)  # Track views
    rsvps = db.relationship('RSVP', backref='invitation', lazy=True)

class RSVP(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    invitation_id = db.Column(db.Integer, db.ForeignKey('invitation.id'), nullable=False)
    guest_name = db.Column(db.String(150), nullable=False)
    guest_email = db.Column(db.String(150), nullable=True)
    guest_message = db.Column(db.Text, nullable=True)  # Personal message from guest
    selfie_url = db.Column(db.String(500), nullable=True)
    vibe_pass_url = db.Column(db.String(500), nullable=True)
    status = db.Column(db.String(50), default='attending')  # attending, declined
    date_responded = db.Column(db.DateTime, default=datetime.utcnow)

# Create DB
with app.app_context():
    db.create_all()

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# --- AI CONFIGURATION ---
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not GEMINI_API_KEY or GEMINI_API_KEY == "your_gemini_api_key_here":
    logging.error("⚠️ GEMINI_API_KEY not found or not configured in .env file!")
    logging.error("Please get your API key from: https://makersuite.google.com/app/apikey")
else:
    logging.info(f"✅ Gemini API key loaded (starts with: {GEMINI_API_KEY[:10]}...)")

# Image generation uses Pollinations.AI - NO API KEY NEEDED!
logging.info("✅ Image generation: Using Pollinations.AI (FREE, no auth required)")

genai.configure(api_key=GEMINI_API_KEY)

# --- ROUTES ---

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/terms')
def terms():
    return render_template('terms.html')

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/privacy')
def privacy():
    return render_template('privacy.html')

@app.route('/help')
def help_center():
    return render_template('help.html')

@app.route('/contact')
def contact():
    return render_template('contact.html')

# Auth Routes
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid email or password', 'error')
    return render_template('auth/login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        email = request.form.get('email')
        name = request.form.get('name')
        password = request.form.get('password')
        
        user = User.query.filter_by(email=email).first()
        if user:
            flash('Email already exists', 'error')
        else:
            new_user = User(email=email, name=name, password=generate_password_hash(password, method='pbkdf2:sha256'))
            db.session.add(new_user)
            db.session.commit()
            login_user(new_user)
            return redirect(url_for('dashboard'))
    return render_template('auth/signup.html')


@app.route('/login/google')
def google_login():
    if not app.config['GOOGLE_CLIENT_ID'] or "your_google_client_id" in app.config['GOOGLE_CLIENT_ID']:
        flash('Google Login is not configured. Please set GOOGLE_CLIENT_ID in .env', 'error')
        return redirect(url_for('login'))
        
    google = oauth.create_client('google')
    redirect_uri = url_for('google_authorize', _external=True)
    logging.info(f"Initiating Google Login. Redirect URI: {redirect_uri}")
    return google.authorize_redirect(redirect_uri)

@app.route('/login/google/callback')
def google_authorize():
    try:
        # Manual Token Exchange to Debug/Fix invalid_client
        code = request.args.get('code')
        if not code:
            flash('No code received from Google', 'error')
            return redirect(url_for('login'))

        token_url = "https://oauth2.googleapis.com/token"
        # Determine the redirect URI used in the request
        # We must match exactly what was used to generate the authorize URL
        # Since we are on localhost, let's try to be smart or just use the request.base_url
        redirect_uri = url_for('google_authorize', _external=True)
        
        # Force http if running locally and behind a proxy that might report https
        if 'localhost' in redirect_uri or '127.0.0.1' in redirect_uri:
            redirect_uri = redirect_uri.replace('https://', 'http://')

        payload = {
            'code': code,
            'client_id': GOOGLE_CLIENT_ID,
            'client_secret': GOOGLE_CLIENT_SECRET,
            'redirect_uri': redirect_uri,
            'grant_type': 'authorization_code'
        }

        logging.info("--- MANUAL TOKEN EXCHANGE ---")
        logging.info(f"Sending token request to: {token_url}")
        logging.info(f"Payload Client ID: {payload['client_id']}")
        logging.info(f"Payload Redirect URI: {payload['redirect_uri']}")
        # Don't log the full secret, just the length/start
        logging.info(f"Payload Secret: {payload['client_secret'][:5]}...")

        resp = requests.post(token_url, data=payload)
        
        logging.info(f"Token Response Status: {resp.status_code}")
        logging.info(f"Token Response Body: {resp.text}")

        if resp.status_code != 200:
            error_data = resp.json()
            error_msg = error_data.get('error_description') or error_data.get('error') or 'Unknown error'
            flash(f'Google Login Failed (Token Exchange): {error_msg}', 'error')
            return redirect(url_for('login'))

        token_data = resp.json()
        access_token = token_data.get('access_token')
        
        # Get User Info
        user_info_resp = requests.get(
            'https://www.googleapis.com/oauth2/v3/userinfo',
            headers={'Authorization': f'Bearer {access_token}'}
        )
        
        if user_info_resp.status_code != 200:
            flash('Failed to fetch user info from Google', 'error')
            return redirect(url_for('login'))
            
        user_info = user_info_resp.json()
        
        if not user_info.get('email'):
            flash('Failed to get email from Google.', 'error')
            return redirect(url_for('login'))

        # Check if user exists
        user = User.query.filter_by(email=user_info['email']).first()
        
        if not user:
            # Create new user
            random_password = secrets.token_urlsafe(16)
            user = User(
                email=user_info['email'],
                name=user_info['name'],
                google_id=user_info['sub'], # 'sub' is the unique ID in OIDC
                profile_pic=user_info.get('picture'),
                password=generate_password_hash(random_password)
            )
            db.session.add(user)
            db.session.commit()
        else:
            # Update existing user info
            if not user.google_id:
                user.google_id = user_info['sub']
            if not user.profile_pic:
                user.profile_pic = user_info.get('picture')
            db.session.commit()
            
        login_user(user)
        return redirect(url_for('dashboard'))

    except Exception as e:
        logging.error(f"Google Login Error: {str(e)}")
        flash(f'Google Login Failed: {str(e)}', 'error')
        return redirect(url_for('login'))

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/dashboard')
@login_required
def dashboard():
    user_invites = Invitation.query.filter_by(user_id=current_user.id).order_by(Invitation.date_created.desc()).all()
    return render_template('dashboard.html', invites=user_invites, user=current_user)

@app.route('/api/delete-invitation/<int:invite_id>', methods=['DELETE'])
@login_required
def delete_invitation(invite_id):
    """Delete an invitation"""
    try:
        invitation = Invitation.query.get(invite_id)
        
        if not invitation:
            return jsonify({"success": False, "error": "Invitation not found"}), 404
        
        if invitation.user_id != current_user.id:
            return jsonify({"success": False, "error": "Unauthorized"}), 403
        
        # Delete associated RSVPs first
        RSVP.query.filter_by(invitation_id=invite_id).delete()
        
        # Delete the invitation
        db.session.delete(invitation)
        db.session.commit()
        
        logging.info(f"Deleted invitation {invite_id} by user {current_user.id}")
        return jsonify({"success": True, "message": "Invitation deleted successfully"})
    
    except Exception as e:
        logging.error(f"Error deleting invitation: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/edit/<int:invite_id>')
@login_required
def edit_invitation(invite_id):
    """Edit invitation page"""
    invitation = Invitation.query.get(invite_id)
    
    if not invitation:
        flash('Invitation not found', 'error')
        return redirect(url_for('dashboard'))
    
    if invitation.user_id != current_user.id:
        flash('Unauthorized access', 'error')
        return redirect(url_for('dashboard'))
    
    return render_template('edit_invitation.html', invitation=invitation)

@app.route('/api/update-invitation/<int:invite_id>', methods=['PUT'])
@login_required
def update_invitation(invite_id):
    """Update invitation details"""
    try:
        invitation = Invitation.query.get(invite_id)
        
        if not invitation:
            return jsonify({"success": False, "error": "Invitation not found"}), 404
        
        if invitation.user_id != current_user.id:
            return jsonify({"success": False, "error": "Unauthorized"}), 403
        
        data = request.json
        
        # Update fields
        if 'title' in data:
            invitation.title = data['title']
        if 'body' in data:
            invitation.body = data['body']
        if 'event_type' in data:
            invitation.event_type = data['event_type']
        if 'vibe' in data:
            invitation.vibe = data['vibe']
        if 'location_name' in data:
            invitation.location_name = data['location_name']
        if 'location_address' in data:
            invitation.location_address = data['location_address']
        
        db.session.commit()
        
        logging.info(f"Updated invitation {invite_id} by user {current_user.id}")
        return jsonify({"success": True, "message": "Invitation updated successfully"})
    
    except Exception as e:
        logging.error(f"Error updating invitation: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/create')
@login_required
def create():
    return render_template('create.html')

# API Routes
@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({"status": "ok", "timestamp": datetime.now().isoformat()})

@app.route('/api/refine-prompt', methods=['POST'])
@login_required
def refine_prompt():
    try:
        data = request.json
        event_type = data.get('eventType')
        vibe = data.get('vibe')
        details = data.get('details')
        family_name = data.get('familyName', '')
        celebrant_name = data.get('celebrantName', '')

        logging.info(f"Refining prompt for user {current_user.id}: {event_type}, {vibe}, {family_name}")

        system_prompt = """
        You are an expert creative director and event planner. 
        Your goal is to take user input about an event and generate:
        1. A HIGHLY DETAILED, artistic image generation prompt for an AI model (Flux/Midjourney style).
        2. A catchy, short title for the invitation card.
        3. A warm, inviting body text for the card (max 2 sentences).

        Return ONLY a JSON object with keys: "image_prompt", "card_title", "card_body".
        
        CRITICAL: The image_prompt must be EXTREMELY detailed and visually rich. Include:
        - Specific visual elements (objects, scenery, architecture)
        - Lighting details (golden hour, neon glow, soft ambient, dramatic spotlights)
        - Color palette (specific colors, gradients, contrasts)
        - Texture and materials (velvet, marble, glass, metal, flowers)
        - Atmosphere and mood (elegant, energetic, serene, luxurious)
        - Composition (foreground, background, depth, perspective)
        """

        user_prompt = f"""
        Event Type: {event_type}
        Theme/Style: {vibe}
        Family Name: {family_name}
        Celebrant Name: {celebrant_name}
        Details: {details}

        Create an EXTREMELY DETAILED, HIGHLY ARTISTIC visual description for the background image.
        This should be a MASTERPIECE-QUALITY prompt that produces stunning, professional results.
        
        Include these elements in your description:
        - Specific lighting (golden hour, neon glow, soft ambient, dramatic backlighting, cinematic lighting)
        - Exact color palette with hex codes or specific color names
        - Textures and materials (velvet, silk, marble, crystal, gold leaf, etc.)
        - Atmospheric elements (fog, sparkles, confetti, floating elements)
        - Depth and perspective (foreground, midground, background layers)
        - Photographic style (bokeh, depth of field, wide angle, macro details)
        - Mood and emotion (joyful, elegant, energetic, intimate, luxurious)
        
        Based on the specific theme '{vibe}' for a {event_type}:
        
        BIRTHDAY THEMES:
        - Neon Party: Vibrant cyberpunk cityscape, glowing neon signs in electric pink/purple/blue, reflective wet streets, holographic party decorations, futuristic nightclub atmosphere, laser lights, energetic vibe
        - Balloon Fest: Colorful balloons floating in sky, confetti rain, bright daylight, cheerful atmosphere, rainbow colors, party streamers, festive celebration mood
        - Confetti Pop: Explosion of golden and colorful confetti, sparkles, celebration moment frozen in time, warm lighting, joyful energy, party poppers
        - Cake Dreams: Whimsical candy land, pastel pink and cream colors, floating cake layers, sweet treats, dreamy soft lighting, magical bakery atmosphere
        
        WEDDING THEMES:
        - Royal Elegance: Opulent ballroom, crystal chandeliers, gold ornate details, marble columns, velvet drapes in burgundy, warm golden lighting, baroque architecture
        - Floral Romance: Lush garden with blooming roses and peonies, soft romantic lighting, golden hour glow, watercolor florals, dreamy pastel colors
        - Classic White: Elegant white chapel, soft natural light, minimalist beauty, white roses, pristine marble, serene atmosphere
        - Garden Dream: Enchanted garden, hanging lights, green foliage, fairy tale setting, twilight ambiance, romantic outdoor venue
        
        PARTY THEMES:
        - Disco Lights: Retro disco ball, colorful spotlights, dance floor, 70s vibes, mirror ball reflections, energetic party atmosphere
        - Beach Vibes: Tropical beach sunset, palm trees, ocean waves, tiki torches, warm sand, relaxed summer party mood
        - Retro Funk: 80s neon aesthetic, geometric patterns, vibrant colors, vintage party decorations, nostalgic atmosphere
        - Glow Party: UV lights, neon paint splashes, blacklight effects, glowing elements, electric energy, modern club scene
        
        CORPORATE THEMES:
        - Professional: Modern office space, clean lines, corporate blue/gray tones, professional lighting, sleek design, business atmosphere
        - Modern Tech: Futuristic tech environment, holographic displays, blue digital elements, innovation theme, cutting-edge design
        - Luxury Gold: Premium corporate setting, gold accents, marble surfaces, sophisticated lighting, high-end business venue
        - Minimal Clean: Minimalist white space, geometric shapes, soft shadows, contemporary design, elegant simplicity
        
        ANNIVERSARY THEMES:
        - Romantic Rose: Red roses in full bloom, candlelight, intimate setting, warm romantic glow, elegant table setting
        - Golden Years: Golden anniversary theme, warm amber lighting, vintage elegance, nostalgic atmosphere, timeless beauty
        - Champagne: Luxury celebration, champagne bubbles, golden sparkles, elegant glassware, sophisticated party setting
        - Starry Night: Night sky filled with stars, romantic evening, twinkling lights, dreamy atmosphere, celestial beauty
        
        BABY SHOWER THEMES:
        - Baby Blue: Soft blue clouds, baby boy theme, gentle lighting, cute teddy bears, nursery atmosphere, peaceful mood
        - Soft Pink: Delicate pink flowers, baby girl theme, soft pastel tones, sweet decorations, warm gentle lighting
        - Pastel Rainbow: Soft rainbow colors, whimsical clouds, dreamy atmosphere, gender-neutral celebration, joyful mood
        - Teddy Bear: Cozy nursery with teddy bears, warm brown tones, soft toys, comfortable setting, loving atmosphere
        
        Make the description VERY SPECIFIC with 40-50 words.
        Include exact colors, lighting details, specific objects, textures, and atmosphere.
        CRITICAL: Do NOT include any text, words, letters, or typography in the image description.
        Focus ONLY on creating a stunning visual background scene perfect for an invitation.
        """

        # Use actual available models from your API key
        model_names = ['gemini-2.5-flash', 'gemini-2.5-pro-preview-03-25']
        response = None
        last_error = None
        
        for model_name in model_names:
            try:
                logging.info(f"Trying Gemini model: {model_name}")
                model = genai.GenerativeModel(model_name)
                response = model.generate_content(system_prompt + "\n\n" + user_prompt)
                if response:
                    logging.info(f"Successfully used model: {model_name}")
                    break
            except Exception as e:
                last_error = str(e)
                logging.warning(f"Model {model_name} failed: {last_error}")
                continue
        
        if not response:
            error_msg = "Unable to generate invitation content. "
            
            # Provide specific guidance based on the error
            if not GEMINI_API_KEY or GEMINI_API_KEY == "your_gemini_api_key_here":
                error_msg += "Please configure your GEMINI_API_KEY in the .env file. Get your free API key from https://makersuite.google.com/app/apikey"
            elif last_error and ("API_KEY_INVALID" in last_error or "invalid" in last_error.lower()):
                error_msg += "Your API key appears to be invalid. Please check your GEMINI_API_KEY in the .env file."
            elif last_error and ("quota" in last_error.lower() or "limit" in last_error.lower()):
                error_msg += "API quota exceeded. Please check your usage at https://aistudio.google.com/app/apikey or try again later."
            else:
                error_msg += f"Technical details: {last_error}"
            
            logging.error(error_msg)
            raise Exception(error_msg)

        text_response = response.text.strip()
        # Clean up markdown if present
        if text_response.startswith("```json"):
            text_response = text_response[7:-3]
        
        result_json = json.loads(text_response)
        return jsonify({"success": True, "data": result_json})

    except Exception as e:
        logging.error(f"Error in refine-prompt: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/generate-image', methods=['POST'])
@login_required
def generate_image():
    try:
        data = request.json
        image_prompt = data.get('image_prompt')
        user_photo_url = data.get('user_photo_url')
        family_name = data.get('familyName', '')
        celebrant_name = data.get('celebrantName', '')
        event_date = data.get('eventDate', '')
        event_time = data.get('eventTime', '')
        event_venue = data.get('eventVenue', '')
        event_message = data.get('eventMessage', '')
        
        logging.info(f"Generating image for user {current_user.id}. Family: {family_name}, Celebrant: {celebrant_name}")

        output_url = ""

        # Use Pollinations.AI (100% FREE, NO API KEY NEEDED!)
        logging.info("Generating image with Pollinations.AI (FREE, no auth required)...")
        
        # Enhance the prompt for better quality
        enhanced_prompt = f"{image_prompt}, highly detailed, professional quality, vibrant colors, masterpiece, 8k"
        
        try:
            # Pollinations.AI - Simple URL-based API
            # Just encode the prompt in the URL - no authentication needed!
            import urllib.parse
            encoded_prompt = urllib.parse.quote(enhanced_prompt)
            
            # Pollinations.AI endpoint with parameters
            pollinations_url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=1024&height=576&nologo=true&enhance=true"
            
            logging.info(f"Generating image with prompt: {enhanced_prompt[:100]}...")
            logging.info(f"Pollinations URL: {pollinations_url[:150]}...")
            
            # Download the image
            response = requests.get(pollinations_url, timeout=60)
            
            if response.status_code == 200:
                # Convert to base64 for display
                image_bytes = response.content
                
                # COMPOSITE FAMILY NAME AND USER PHOTO IF AVAILABLE
                try:
                    # Open background image
                    bg_img = Image.open(BytesIO(image_bytes)).convert("RGBA")
                    draw = ImageDraw.Draw(bg_img)
                    
                    # Add Family Name at Top
                    if family_name:
                        try:
                            # Load font for family name (elegant, large)
                            try:
                                font_family = ImageFont.truetype("arial.ttf", 60)
                            except:
                                font_family = ImageFont.load_default()
                            
                            # Get text size
                            bbox = draw.textbbox((0, 0), family_name, font=font_family)
                            text_width = bbox[2] - bbox[0]
                            text_height = bbox[3] - bbox[1]
                            
                            # Position at top center
                            x = (bg_img.width - text_width) // 2
                            y = 30
                            
                            # Draw text with outline for visibility
                            # Outline
                            for adj_x in range(-3, 4):
                                for adj_y in range(-3, 4):
                                    draw.text((x + adj_x, y + adj_y), family_name, font=font_family, fill='black')
                            # Main text
                            draw.text((x, y), family_name, font=font_family, fill='#c084fc')  # Purple color
                            
                            logging.info(f"✅ Family name '{family_name}' added to image!")
                        except Exception as font_e:
                            logging.error(f"Failed to add family name: {font_e}")
                    
                    # Add user photo below family name
                    if user_photo_url:
                        try:
                            # Download user photo
                            photo_response = requests.get(user_photo_url, timeout=30)
                            if photo_response.status_code == 200:
                                user_img = Image.open(BytesIO(photo_response.content)).convert("RGBA")
                                
                                # Resize and crop user photo to circle
                                size = (200, 200) # Size of the photo bubble
                                user_img = user_img.resize(size, Image.Resampling.LANCZOS)
                                
                                # Create circular mask
                                mask = Image.new('L', size, 0)
                                mask_draw = ImageDraw.Draw(mask)
                                mask_draw.ellipse((0, 0) + size, fill=255)
                                
                                # Create circular image
                                output = Image.new('RGBA', size, (0, 0, 0, 0))
                                output.paste(user_img, (0, 0), mask)
                                
                                # Add purple border
                                border_size = 5
                                border_draw = ImageDraw.Draw(output)
                                border_draw.ellipse((0, 0, size[0]-1, size[1]-1), outline="#c084fc", width=border_size)
                                
                                # Paste onto background (Below family name, centered)
                                x = (bg_img.width - size[0]) // 2
                                y = 120 if family_name else 50  # Lower if family name exists
                                
                                bg_img.paste(output, (x, y), output)
                                
                                logging.info("✅ User photo composited successfully!")
                            else:
                                logging.warning("Could not download user photo for compositing")
                        except Exception as photo_e:
                            logging.error(f"User photo compositing failed: {photo_e}")
                    
                    # Save back to bytes
                    buffer = BytesIO()
                    bg_img = bg_img.convert("RGB") # Convert back to RGB for JPEG
                    bg_img.save(buffer, format="JPEG", quality=95)
                    image_bytes = buffer.getvalue()
                    
                except Exception as comp_e:
                    logging.error(f"Image compositing failed: {comp_e}")
                    # Continue with original image if compositing fails

                image_base64 = base64.b64encode(image_bytes).decode('utf-8')
                output_url = f"data:image/jpeg;base64,{image_base64}"
                
                logging.info("✅ Image generated successfully with Pollinations.AI!")
            else:
                raise Exception(f"Pollinations.AI error: {response.status_code}")
                
        except Exception as e:
            logging.error(f"Pollinations.AI generation failed: {e}")
            # Fallback to a simpler model
            try:
                logging.info("Trying fallback: Pollinations.AI with simpler prompt...")
                simple_prompt = urllib.parse.quote(image_prompt)
                fallback_url = f"https://image.pollinations.ai/prompt/{simple_prompt}?width=1024&height=576&nologo=true"
                response = requests.get(fallback_url, timeout=60)
                if response.status_code == 200:
                    image_bytes = response.content
                    image_base64 = base64.b64encode(image_bytes).decode('utf-8')
                    output_url = f"data:image/jpeg;base64,{image_base64}"
                    logging.info("✅ Image generated with fallback!")
                else:
                    raise Exception(f"Fallback also failed: {response.status_code}")
            except Exception as fallback_error:
                logging.error(f"All image generation attempts failed: {fallback_error}")
                raise Exception(f"Image generation failed. Please try again later.")
        
        # SAVE TO DB IF LOGGED IN
        if current_user.is_authenticated:
            try:
                import secrets
                import string
                
                title = f"{celebrant_name}'s {data.get('eventType', 'Event')}" if celebrant_name else data.get('title', 'Untitled Invitation')
                body = event_message if event_message else data.get('body', '')
                event_type = data.get('eventType', 'General')
                vibe = data.get('vibe', 'General')
                location_name = event_venue if event_venue else data.get('location_name', '')
                
                # Generate unique share link
                def generate_share_link():
                    chars = string.ascii_lowercase + string.digits
                    while True:
                        link = ''.join(secrets.choice(chars) for _ in range(8))
                        if not Invitation.query.filter_by(share_link=link).first():
                            return link

                new_invite = Invitation(
                    title=title,
                    body=body,
                    image_url=output_url,
                    event_type=event_type,
                    vibe=vibe,
                    user_id=current_user.id,
                    share_link=generate_share_link(),
                    family_name=family_name,
                    celebrant_name=celebrant_name,
                    event_date=event_date,
                    event_time=event_time,
                    event_venue=event_venue,
                    event_message=event_message,
                    location_name=location_name
                )
                db.session.add(new_invite)
                db.session.commit()
                logging.info(f"Saved invitation {new_invite.id} with share link: {new_invite.share_link}")
                
                return jsonify({
                    "success": True, 
                    "image_url": output_url,
                    "invitation_id": new_invite.id,
                    "share_link": new_invite.share_link
                })
            except Exception as db_e:
                logging.error(f"Failed to save to DB: {str(db_e)}")

        return jsonify({"success": True, "image_url": output_url})

    except Exception as e:
        logging.error(f"Error in generate-image: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500

# --- ENHANCED INVITATION ROUTES ---

@app.route('/invite/<share_link>')
def public_invitation(share_link):
    """Public invitation view - accessible to anyone - Clean view without header/footer"""
    invitation = Invitation.query.filter_by(share_link=share_link).first()
    
    if not invitation:
        return render_template('404.html'), 404
    
    # Increment view count
    invitation.view_count += 1
    db.session.commit()
    
    # Use the clean share template (no header/footer)
    return render_template('share_invitation.html', invitation=invitation)

@app.route('/api/enhance-invitation', methods=['POST'])
@login_required
def enhance_invitation():
    """Add gallery, location, and voice to invitation"""
    try:
        data = request.json
        invitation_id = data.get('invitation_id')
        
        invitation = Invitation.query.get(invitation_id)
        if not invitation or invitation.user_id != current_user.id:
            return jsonify({"success": False, "error": "Unauthorized"}), 403
        
        # Update gallery photos
        if 'gallery_photos' in data:
            invitation.gallery_photos = json.dumps(data['gallery_photos'])
        
        # Update location
        if 'location_name' in data:
            invitation.location_name = data['location_name']
            invitation.location_address = data.get('location_address')
            invitation.location_lat = data.get('location_lat')
            invitation.location_lng = data.get('location_lng')
        
        # Update voice message
        if 'voice_message_url' in data:
            invitation.voice_message_url = data['voice_message_url']
        
        db.session.commit()
        
        return jsonify({
            "success": True,
            "share_link": invitation.share_link,
            "share_url": f"{request.host_url}invite/{invitation.share_link}"
        })
    
    except Exception as e:
        logging.error(f"Error enhancing invitation: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/upload-voice', methods=['POST'])
@login_required
def upload_voice():
    """Upload voice message (15 seconds max)"""
    try:
        if 'voice' not in request.files:
            return jsonify({"success": False, "error": "No voice file"}), 400
        
        voice_file = request.files['voice']
        
        # Here you would upload to cloud storage (Uploadcare, S3, etc.)
        # For now, we'll return a placeholder
        # In production, integrate with Uploadcare or similar
        
        voice_url = "placeholder_voice_url"  # Replace with actual upload
        
        return jsonify({"success": True, "voice_url": voice_url})
    
    except Exception as e:
        logging.error(f"Error uploading voice: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/generate-video', methods=['POST'])
@login_required
def generate_video():
    """Generate a 5-10s hype video from invitation with optional music"""
    try:
        logging.info("🎬 Video generation started")
        
        data = request.json
        invitation_id = data.get('invitation_id')
        music_choice = data.get('music')  # Can be None or a music type
        duration = data.get('duration', 10)  # Default 10 seconds
        
        logging.info(f"Video request - ID: {invitation_id}, Music: {music_choice}, Duration: {duration}s")
        
        # Ensure duration is between 5-10 seconds
        duration = max(5, min(10, duration))
        
        invitation = Invitation.query.get(invitation_id)
        if not invitation:
            logging.error(f"Invitation {invitation_id} not found")
            return jsonify({"success": False, "error": "Invitation not found"}), 404
            
        if invitation.user_id != current_user.id:
            logging.error(f"Unauthorized access attempt for invitation {invitation_id}")
            return jsonify({"success": False, "error": "Unauthorized"}), 403
        
        logging.info(f"Processing invitation: {invitation.title}")
            
        # 1. Download/Process Image
        logging.info("Step 1: Processing image...")
        if invitation.image_url.startswith('data:'):
            # Handle Base64 Image
            header, encoded = invitation.image_url.split(",", 1)
            img_data = base64.b64decode(encoded)
            with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as tmp_img:
                tmp_img.write(img_data)
                img_path = tmp_img.name
            logging.info("Base64 image saved to temp file")
        else:
            # Handle Regular URL
            img_resp = requests.get(invitation.image_url)
            with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as tmp_img:
                tmp_img.write(img_resp.content)
                img_path = tmp_img.name
            logging.info("URL image downloaded to temp file")
            
        # 2. Create Video Clip with specified duration
        logging.info(f"Step 2: Creating {duration}s video clip...")
        clip = ImageClip(img_path).set_duration(duration)
        logging.info("Image clip created successfully")
        
        # Add simple pan/zoom effect (Ken Burns)
        # Resize to be slightly larger to allow for movement
        w, h = clip.size
        clip = clip.resize(height=1920) # Vertical video target
        clip = clip.crop(x1=0, y1=0, width=1080, height=1920, x_center=clip.w/2, y_center=clip.h/2)
        
        # Create Text Clips (Reveal Effect)
        # We use a simple fade-in for the "reveal" effect
        
        # Create Text Clips (Reveal Effect) using PIL (Robust fallback)
        
        # Create Text Clips (Reveal Effect) using PIL (Robust fallback)
        
        def create_text_clip_pil(text, fontsize, color, max_width, duration, start_time, y_pos):
            clips = []
            try:
                # 1. Create PIL Image
                try:
                    # Try to use a font that matches the "Display" or "Serif" style of the invitation
                    # Times New Roman is a safe bet for a "classy" look matching the invitation style
                    # If you have specific font files (e.g. Playfair Display), you should load them here
                    font = ImageFont.truetype("times.ttf", fontsize) 
                except:
                    try:
                        font = ImageFont.truetype("arial.ttf", fontsize)
                    except:
                        font = ImageFont.load_default()
                
                # Wrap text
                avg_char_width = fontsize * 0.6
                chars_per_line = int(max_width / avg_char_width)
                lines = textwrap.wrap(text, width=chars_per_line)
                
                line_height = int(fontsize * 1.2)
                current_y = y_pos
                
                # Create a clip for EACH line to animate them separately
                for i, line in enumerate(lines):
                    # Create image for just this line
                    # Make it wide enough for the text
                    try:
                        bbox = ImageDraw.Draw(Image.new('RGB', (1, 1))).textbbox((0, 0), line, font=font)
                        text_width = bbox[2] - bbox[0]
                        text_height = bbox[3] - bbox[1] + 20 # Add padding
                    except:
                        text_width = len(line) * avg_char_width
                        text_height = fontsize + 20

                    # Create image for this line
                    img = Image.new('RGBA', (max_width, int(text_height + 20)), (0, 0, 0, 0))
                    draw = ImageDraw.Draw(img)
                    
                    x = (max_width - text_width) // 2
                    
                    # Draw outline/stroke
                    for adj in range(-3, 4):
                        for adj2 in range(-3, 4):
                            draw.text((x+adj, 10+adj2), line, font=font, fill='black')
                    draw.text((x, 10), line, font=font, fill=color)
                    
                    np_img = np.array(img)
                    
                    # Stagger start times: 0.5s delay per line
                    line_start = start_time + (i * 0.8) 
                    
                    txt_clip = ImageClip(np_img).set_duration(duration - (line_start - start_time)).set_start(line_start)
                    txt_clip = txt_clip.set_position(('center', current_y)).crossfadein(1.0)
                    clips.append(txt_clip)
                    
                    current_y += line_height
                
                return clips, current_y
                
            except Exception as e:
                logging.error(f"PIL Text generation failed: {e}")
                return [], y_pos

        clips_to_composite = [clip]

        # Title Text - MATCH INVITATION STYLE (Larger, Serif)
        # Invitation uses ~text-8xl which is very large
        title_clips, next_y = create_text_clip_pil(invitation.title, 120, 'white', 1000, 10, 0.5, 300)
        clips_to_composite.extend(title_clips)
        
        # Body Text - MATCH INVITATION STYLE
        # Invitation uses ~text-3xl
        body_start_time = 0.5 + (len(title_clips) * 0.5) + 0.5
        body_clips, next_y = create_text_clip_pil(invitation.body, 60, 'white', 900, 10, body_start_time, next_y + 60)
        clips_to_composite.extend(body_clips)

        # Location Text
        if invitation.location_name:
            location_start_time = body_start_time + (len(body_clips) * 0.5) + 0.5
            location_clips, _ = create_text_clip_pil(f"📍 {invitation.location_name}", 50, 'yellow', 900, 10, location_start_time, next_y + 40)
            clips_to_composite.extend(location_clips)
        
        logging.info("Step 3: Compositing clips...")
        final_clip = CompositeVideoClip(clips_to_composite)
        logging.info("Composite video created")

        # 4. Write to file
        # Save to static/videos so it can be served
        logging.info("Step 4: Writing video file...")
        video_dir = os.path.join(app.root_path, 'static', 'videos')
        os.makedirs(video_dir, exist_ok=True)
        
        filename = f"hype_{invitation.id}_{int(time.time())}.mp4"
        output_path = os.path.join(video_dir, filename)
        
        logging.info(f"Writing video to: {output_path}")
        final_clip.write_videofile(output_path, fps=24, codec='libx264', audio=False, logger=None)
        logging.info("✅ Video file written successfully!")
        
        # 5. Return URL
        video_url = url_for('static', filename=f'videos/{filename}', _external=True)
        logging.info(f"Video URL: {video_url}")
        
        # Clean up input image
        try:
            os.remove(img_path)
            logging.info("Temp image file cleaned up")
        except:
            pass
        
        return jsonify({"success": True, "video_url": video_url})

    except Exception as e:
        logging.error(f"❌ Error generating video: {str(e)}")
        logging.error(f"Full error: {repr(e)}")
        import traceback
        logging.error(traceback.format_exc())
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/rsvp-submit', methods=['POST'])
def rsvp_submit():
    """Submit RSVP with guest data"""
    try:
        data = request.json
        invitation_id = data.get('invitation_id')
        guest_name = data.get('guest_name')
        guest_email = data.get('guest_email')
        guest_message = data.get('guest_message')
        
        if not invitation_id or not guest_name:
            return jsonify({"success": False, "error": "Missing required fields"}), 400
            
        invitation = Invitation.query.get(invitation_id)
        if not invitation:
            return jsonify({"success": False, "error": "Invitation not found"}), 404
        
        # Create RSVP entry
        new_rsvp = RSVP(
            invitation_id=invitation_id,
            guest_name=guest_name,
            guest_email=guest_email,
            guest_message=guest_message,
            status='attending'
        )
        
        db.session.add(new_rsvp)
        db.session.commit()
        
        logging.info(f"✅ RSVP received from {guest_name} for invitation {invitation_id}")
        
        # SEND EMAIL TO OWNER (Simulated for now)
        owner_email = User.query.get(invitation.user_id).email
        logging.info(f"📧 SENDING EMAIL TO OWNER: {owner_email}")
        logging.info(f"Subject: New RSVP from {guest_name}!")
        logging.info(f"Body: {guest_name} has RSVP'd to your event '{invitation.title}'.")
        
        # TODO: Integrate SendGrid/Mailgun here for actual emails
        
        return jsonify({
            "success": True, 
            "message": "RSVP received!",
            "rsvp_id": new_rsvp.id
        })
        
    except Exception as e:
        logging.error(f"RSVP error: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/get-rsvps/<int:invitation_id>', methods=['GET'])
def get_rsvps(invitation_id):
    """Get all RSVPs for an invitation"""
    try:
        invitation = Invitation.query.get(invitation_id)
        if not invitation:
            return jsonify({"success": False, "error": "Invitation not found"}), 404
        
        rsvps = RSVP.query.filter_by(invitation_id=invitation_id).order_by(RSVP.date_responded.desc()).all()
        
        rsvps_data = [{
            'id': rsvp.id,
            'guest_name': rsvp.guest_name,
            'guest_email': rsvp.guest_email,
            'guest_message': rsvp.guest_message,
            'status': rsvp.status,
            'date_responded': rsvp.date_responded.strftime('%Y-%m-%d %H:%M:%S')
        } for rsvp in rsvps]
        
        return jsonify({
            "success": True,
            "rsvps": rsvps_data
        })
        
    except Exception as e:
        logging.error(f"Error fetching RSVPs: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/get-invitation-id-by-link/<share_link>', methods=['GET'])
@login_required
def get_invitation_id_by_link(share_link):
    """Get invitation ID from share link - for existing invitations"""
    try:
        invitation = Invitation.query.filter_by(share_link=share_link).first()
        
        if not invitation:
            return jsonify({"success": False, "error": "Invitation not found"}), 404
        
        if invitation.user_id != current_user.id:
            return jsonify({"success": False, "error": "Unauthorized"}), 403
        
        return jsonify({
            "success": True,
            "invitation_id": invitation.id
        })
        
    except Exception as e:
        logging.error(f"Error fetching invitation ID: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)
