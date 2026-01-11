from flask import Flask, render_template, request, redirect, url_for, session, flash
import database
from datetime import datetime
from authlib.integrations.flask_client import OAuth
import os

from werkzeug.middleware.proxy_fix import ProxyFix

app = Flask(__name__)
# Fix for HTTPS on Render/Heroku (Cloud Deployment)
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

app.secret_key = 'your_secret_key_here_change_this_in_prod'

# Enable insecure transport for local development (HTTP)
# os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'  <-- Commented out for Production

# Google OAuth Configuration
# Using credentials found in context/logs
app.config['GOOGLE_CLIENT_ID'] = '5546206720-7aifk56mfqrk5pogp5p1nrge87uteg51.apps.googleusercontent.com'
app.config['GOOGLE_CLIENT_SECRET'] = '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'

oauth = OAuth(app)
google = oauth.register(
    name='google',
    client_id=app.config['GOOGLE_CLIENT_ID'],
    client_secret=app.config['GOOGLE_CLIENT_SECRET'],
    access_token_url='https://oauth2.googleapis.com/token',
    authorize_url='https://accounts.google.com/o/oauth2/auth',
    api_base_url='https://www.googleapis.com/oauth2/v1/',
    client_kwargs={'scope': 'openid email profile'},
    jwks_uri='https://www.googleapis.com/oauth2/v3/certs'
)

# Initialize DB
database.init_db()
database.create_admin_if_not_exists()

@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        mobile = request.form['mobile']
        username = request.form['username']
        password = request.form['password']
        
        # New users are always 'agent'
        if database.create_user(name, mobile, username, password, role='agent'):
            flash('Registration successful! Please sign in.', 'success')
            return redirect(url_for('login'))
        else:
            flash('Username already exists!', 'error')
            
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        user = database.verify_user(username, password)
        if user:
            session['user_id'] = user['id']
            session['name'] = user['name']
            session['role'] = user['role']
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password!', 'error')
            
    return render_template('login.html')

@app.route('/login/google')
def google_login():
    redirect_uri = url_for('google_auth', _external=True)
    return google.authorize_redirect(redirect_uri)

@app.route('/auth/google')
def google_auth():
    try:
        token = google.authorize_access_token()
        # Manually fetch userinfo using the token to avoid dependency on metadata
        resp = google.get('https://www.googleapis.com/oauth2/v1/userinfo')
        user_info = resp.json()
        
        google_id = user_info['id']
        email = user_info['email']
        name = user_info.get('name', email.split('@')[0])
        
        user = database.get_user_by_google_id(google_id)
        
        if not user:
            # Create new agent user with Google ID
            # Using email as username for google users
            database.create_user(name, "0000000000", email, None, role='agent', google_id=google_id)
            user = database.get_user_by_google_id(google_id)
            
        session['user_id'] = user['id']
        session['name'] = user['name']
        session['role'] = user['role']
        return redirect(url_for('dashboard'))
    except Exception as e:
        flash(f'Google Sign-In failed: {str(e)}', 'error')
        return redirect(url_for('login'))

@app.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        username = request.form['username']
        mobile = request.form['mobile']
        new_password = request.form['new_password']
        
        if database.reset_password(username, mobile, new_password):
            flash('Password reset successful! Please login.', 'success')
            return redirect(url_for('login'))
        else:
            flash('Invalid username or mobile number.', 'error')
            
    return render_template('forgot_password.html')

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    role = session.get('role', 'agent')
    
    if role == 'admin':
        collections = database.get_all_collections()
        total_amount = database.get_total_amount_all()
    else:
        collections = database.get_user_collections(session['user_id'])
        total_amount = database.get_total_amount(session['user_id'])
        
    return render_template('dashboard.html', 
                           name=session['name'], 
                           collections=collections, 
                           total_amount=total_amount,
                           role=role)

@app.route('/manage_users')
def manage_users():
    if 'user_id' not in session or session.get('role') != 'admin':
        return redirect(url_for('dashboard'))
    
    users = database.get_all_users()
    return render_template('manage_users.html', users=users, name=session['name'], role='admin')

@app.route('/delete_user/<int:user_id>')
def delete_user(user_id):
    if 'user_id' not in session or session.get('role') != 'admin':
        return redirect(url_for('login'))
        
    database.delete_user(user_id)
    flash('User deleted successfully.', 'success')
    return redirect(url_for('manage_users'))

@app.route('/add_collection', methods=['POST'])
def add_collection():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    amount = request.form['amount']
    purpose = request.form['purpose']
    date = request.form['date']
    
    if not date:
        date = datetime.now().strftime('%Y-%m-%d')
        
    database.add_collection(session['user_id'], amount, purpose, date)
    flash('Collection added successfully!', 'success')
    return redirect(url_for('dashboard'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True, port=5000)
