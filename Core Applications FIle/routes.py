from flask import render_template, redirect, url_for, request, flash, jsonify, session
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from app import app, db
from models import User, Candidate, Election, Vote, Block
from blockchain import Blockchain
from retina_authentication import RetinalAuthentication
import json
import base64
import io
import logging
from datetime import datetime

# Initialize blockchain and retinal authentication
blockchain = Blockchain()
retina_auth = RetinalAuthentication()

# Initialize blockchain after app context is created
@app.before_request
def initialize_blockchain():
    """Initialize blockchain before each request if not already initialized"""
    if not blockchain.initialized:
        blockchain.initialize()

@app.route('/')
def index():
    """Home page"""
    # Get active elections
    active_elections = Election.query.filter_by(is_active=True).all()
    return render_template('index.html', active_elections=active_elections)

@app.route('/register', methods=['GET', 'POST'])
def register():
    """User registration page"""
    if current_user.is_authenticated:
        return redirect(url_for('index'))
        
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        # Basic validation
        if not username or not email or not password:
            flash('All fields are required', 'danger')
            return render_template('register.html')
            
        if password != confirm_password:
            flash('Passwords do not match', 'danger')
            return render_template('register.html')
            
        # Check if user already exists
        existing_user = User.query.filter((User.username == username) | (User.email == email)).first()
        if existing_user:
            flash('Username or email already exists', 'danger')
            return render_template('register.html')
            
        # Create new user
        new_user = User(username=username, email=email)
        new_user.set_password(password)
        
        db.session.add(new_user)
        db.session.commit()
        
        flash('Registration successful! Please login.', 'success')
        return redirect(url_for('login'))
        
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    """User login page"""
    if current_user.is_authenticated:
        return redirect(url_for('index'))
        
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        # Basic validation
        if not username or not password:
            flash('Username and password are required', 'danger')
            return render_template('login.html')
            
        # Find user
        user = User.query.filter_by(username=username).first()
        
        # Check password
        if user and user.check_password(password):
            login_user(user)
            
            # If user has not registered their retina scan, redirect to scan page
            if not user.is_registered and not user.is_admin:
                flash('Please register your retina scan to complete registration', 'info')
                return redirect(url_for('scan_retina'))
                
            next_page = request.args.get('next')
            return redirect(next_page or url_for('index'))
        else:
            flash('Invalid username or password', 'danger')
            
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    """User logout"""
    logout_user()
    flash('You have been logged out', 'info')
    return redirect(url_for('index'))

@app.route('/scan_retina', methods=['GET', 'POST'])
@login_required
def scan_retina():
    """Retina scan registration page"""
    if request.method == 'POST':
        # Get base64 image data
        image_data = request.form.get('image_data')
        
        if not image_data:
            flash('No retina scan data received', 'danger')
            return render_template('scan.html', mode='register')
            
        # Process base64 data
        try:
            # Strip out the base64 prefix
            image_data = image_data.split(',')[1]
            # Decode base64 to binary
            binary_data = base64.b64decode(image_data)
            
            # Extract features from the scan
            features = retina_auth.extract_features(binary_data)
            
            if features is None:
                flash('Failed to process retina scan. Please try again.', 'danger')
                return render_template('scan.html', mode='register')
                
            # Serialize features for storage
            serialized_features = retina_auth.serialize_features(features)
            
            # Save scan and features to user
            current_user.retina_scan = binary_data
            current_user.retina_features = serialized_features
            current_user.is_registered = True
            
            db.session.commit()
            
            flash('Retina scan registered successfully!', 'success')
            return redirect(url_for('index'))
            
        except Exception as e:
            logging.error(f"Error processing retina scan: {str(e)}")
            flash('Error processing retina scan. Please try again.', 'danger')
            
    return render_template('scan.html', mode='register')

@app.route('/authenticate_retina', methods=['GET', 'POST'])
@login_required
def authenticate_retina():
    """Retina scan authentication page"""
    # Get active election
    election_id = request.args.get('election_id')
    election = Election.query.get_or_404(election_id)
    
    if request.method == 'POST':
        # Get base64 image data
        image_data = request.form.get('image_data')
        
        if not image_data:
            flash('No retina scan data received', 'danger')
            return render_template('scan.html', mode='authenticate', election=election)
            
        # Process base64 data
        try:
            # Strip out the base64 prefix
            image_data = image_data.split(',')[1]
            # Decode base64 to binary
            binary_data = base64.b64decode(image_data)
            
            # Extract features from the scan
            features = retina_auth.extract_features(binary_data)
            
            if features is None:
                flash('Failed to process retina scan. Please try again.', 'danger')
                return render_template('scan.html', mode='authenticate', election=election)
                
            # Compare with stored features
            if not current_user.retina_features:
                flash('You have not registered a retina scan', 'danger')
                return redirect(url_for('scan_retina'))
                
            # Check if the scans match
            is_match = retina_auth.compare_features(features, current_user.retina_features)
            
            if is_match:
                flash('Authentication successful!', 'success')
                # Set session variable to indicate authenticated for voting
                session['retina_authenticated'] = True
                session['election_id'] = election_id
                return redirect(url_for('vote', election_id=election_id))
            else:
                flash('Authentication failed. Retina scan does not match.', 'danger')
                return render_template('scan.html', mode='authenticate', election=election)
                
        except Exception as e:
            logging.error(f"Error processing retina scan: {str(e)}")
            flash('Error processing retina scan. Please try again.', 'danger')
            
    return render_template('scan.html', mode='authenticate', election=election)

@app.route('/vote/<int:election_id>', methods=['GET', 'POST'])
@login_required
def vote(election_id):
    """Voting page for a specific election"""
    # Check if user is retina authenticated for this election
    if not session.get('retina_authenticated') or session.get('election_id') != str(election_id):
        flash('You need to authenticate with your retina scan first', 'warning')
        return redirect(url_for('authenticate_retina', election_id=election_id))
        
    # Get election details
    election = Election.query.get_or_404(election_id)
    
    # Check if election is active
    if not election.is_active:
        flash('This election is not active', 'warning')
        return redirect(url_for('index'))
        
    # Check if user already voted in this election
    existing_vote = Vote.query.filter_by(
        user_id=current_user.id,
        election_id=election_id
    ).first()
    
    if existing_vote:
        flash('You have already voted in this election', 'info')
        return redirect(url_for('index'))
        
    # Get candidates for this election
    candidates = Candidate.query.all()
    
    if request.method == 'POST':
        candidate_id = request.form.get('candidate_id')
        
        if not candidate_id:
            flash('Please select a candidate', 'danger')
            return render_template('vote.html', election=election, candidates=candidates)
            
        # Create vote data for blockchain
        vote_data = {
            'user_id': current_user.id,
            'candidate_id': int(candidate_id),
            'election_id': election_id,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        # Add vote to blockchain
        block_index = blockchain.new_vote(vote_data)
        
        # Create vote record in database
        vote = Vote(
            user_id=current_user.id,
            candidate_id=int(candidate_id),
            election_id=election_id,
            blockchain_hash=blockchain.hash(blockchain.chain[block_index-1]) if block_index > 0 else None
        )
        
        db.session.add(vote)
        db.session.commit()
        
        # Clear authentication session
        session.pop('retina_authenticated', None)
        session.pop('election_id', None)
        
        flash('Your vote has been recorded securely!', 'success')
        return redirect(url_for('index'))
        
    return render_template('vote.html', election=election, candidates=candidates)

@app.route('/results/<int:election_id>')
def results(election_id):
    """Election results page"""
    election = Election.query.get_or_404(election_id)
    
    # Only show results if election is over or user is admin
    if election.end_date > datetime.utcnow() and not (current_user.is_authenticated and current_user.is_admin):
        flash('Results will be available after the election ends', 'info')
        return redirect(url_for('index'))
        
    # Get vote counts for each candidate
    candidates = Candidate.query.all()
    results = []
    
    for candidate in candidates:
        vote_count = Vote.query.filter_by(
            candidate_id=candidate.id,
            election_id=election_id
        ).count()
        
        results.append({
            'candidate': candidate,
            'votes': vote_count
        })
        
    # Sort by vote count (descending)
    results.sort(key=lambda x: x['votes'], reverse=True)
    
    # Get total votes
    total_votes = Vote.query.filter_by(election_id=election_id).count()
    
    return render_template('results.html', 
                          election=election,
                          results=results,
                          total_votes=total_votes)

# Admin routes
@app.route('/admin/dashboard')
@login_required
def admin_dashboard():
    """Admin dashboard"""
    if not current_user.is_admin:
        flash('Access denied. Admin privileges required.', 'danger')
        return redirect(url_for('index'))
        
    # Get statistics for dashboard cards
    stats = {
        'elections': Election.query.count(),
        'candidates': Candidate.query.count(),
        'voters': User.query.filter(User.is_registered == True, User.is_admin == False).count()
    }
    
    # Get active elections
    active_elections = Election.query.filter_by(is_active=True).all()
    
    # Get recent votes
    recent_votes = Vote.query.order_by(Vote.timestamp.desc()).limit(5).all()
    
    return render_template('admin/dashboard.html',
                          stats=stats,
                          active_elections=active_elections,
                          recent_votes=recent_votes)

@app.route('/admin/elections', methods=['GET', 'POST'])
@login_required
def admin_elections():
    """Manage elections"""
    if not current_user.is_admin:
        flash('Access denied. Admin privileges required.', 'danger')
        return redirect(url_for('index'))
        
    if request.method == 'POST':
        action = request.form.get('action')
        
        if action == 'create':
            title = request.form.get('title')
            description = request.form.get('description')
            start_date = request.form.get('start_date')
            end_date = request.form.get('end_date')
            is_active = request.form.get('is_active') == 'on'
            
            if not title or not start_date or not end_date:
                flash('All required fields must be filled', 'danger')
            else:
                try:
                    # Parse the datetime correctly
                    new_election = Election(
                        title=title,
                        description=description,
                        start_date=datetime.strptime(start_date, '%Y-%m-%dT%H:%M'),
                        end_date=datetime.strptime(end_date, '%Y-%m-%dT%H:%M'),
                        is_active=is_active
                    )
                    
                    db.session.add(new_election)
                    db.session.commit()
                    flash('Election created successfully', 'success')
                except Exception as e:
                    logging.error(f"Error creating election: {str(e)}")
                    flash('Error creating election', 'danger')
        
        elif action == 'update':
            election_id = request.form.get('election_id')
            title = request.form.get('title')
            description = request.form.get('description')
            start_date = request.form.get('start_date')
            end_date = request.form.get('end_date')
            is_active = request.form.get('is_active') == 'on'
            
            election = Election.query.get(election_id)
            if election:
                try:
                    election.title = title
                    election.description = description
                    election.start_date = datetime.strptime(start_date, '%Y-%m-%dT%H:%M')
                    election.end_date = datetime.strptime(end_date, '%Y-%m-%dT%H:%M')
                    election.is_active = is_active
                    
                    db.session.commit()
                    flash('Election updated successfully', 'success')
                except Exception as e:
                    logging.error(f"Error updating election: {str(e)}")
                    flash('Error updating election', 'danger')
            else:
                flash('Election not found', 'danger')
                
        elif action == 'delete':
            election_id = request.form.get('election_id')
            election = Election.query.get(election_id)
            
            if election:
                try:
                    db.session.delete(election)
                    db.session.commit()
                    flash('Election deleted successfully', 'success')
                except Exception as e:
                    logging.error(f"Error deleting election: {str(e)}")
                    flash('Error deleting election', 'danger')
            else:
                flash('Election not found', 'danger')
                
    # Get all elections
    elections = Election.query.all()
    
    return render_template('admin/elections.html', elections=elections)

@app.route('/admin/candidates', methods=['GET', 'POST'])
@login_required
def admin_candidates():
    """Manage candidates"""
    if not current_user.is_admin:
        flash('Access denied. Admin privileges required.', 'danger')
        return redirect(url_for('index'))
        
    if request.method == 'POST':
        action = request.form.get('action')
        
        if action == 'create':
            name = request.form.get('name')
            description = request.form.get('description')
            position = request.form.get('position')
            
            if not name or not position:
                flash('Name and position are required', 'danger')
            else:
                try:
                    new_candidate = Candidate(
                        name=name,
                        description=description,
                        position=position
                    )
                    
                    db.session.add(new_candidate)
                    db.session.commit()
                    flash('Candidate added successfully', 'success')
                except Exception as e:
                    logging.error(f"Error adding candidate: {str(e)}")
                    flash('Error adding candidate', 'danger')
        
        elif action == 'update':
            candidate_id = request.form.get('candidate_id')
            name = request.form.get('name')
            description = request.form.get('description')
            position = request.form.get('position')
            
            candidate = Candidate.query.get(candidate_id)
            if candidate:
                try:
                    candidate.name = name
                    candidate.description = description
                    candidate.position = position
                    
                    db.session.commit()
                    flash('Candidate updated successfully', 'success')
                except Exception as e:
                    logging.error(f"Error updating candidate: {str(e)}")
                    flash('Error updating candidate', 'danger')
            else:
                flash('Candidate not found', 'danger')
                
        elif action == 'delete':
            candidate_id = request.form.get('candidate_id')
            candidate = Candidate.query.get(candidate_id)
            
            if candidate:
                try:
                    db.session.delete(candidate)
                    db.session.commit()
                    flash('Candidate deleted successfully', 'success')
                except Exception as e:
                    logging.error(f"Error deleting candidate: {str(e)}")
                    flash('Error deleting candidate', 'danger')
            else:
                flash('Candidate not found', 'danger')
                
    # Get all candidates
    candidates = Candidate.query.all()
    
    return render_template('admin/candidates.html', candidates=candidates)

@app.route('/admin/voters', methods=['GET', 'POST'])
@login_required
def admin_voters():
    """Manage voters"""
    if not current_user.is_admin:
        flash('Access denied. Admin privileges required.', 'danger')
        return redirect(url_for('index'))
        
    if request.method == 'POST':
        action = request.form.get('action')
        
        if action == 'delete':
            user_id = request.form.get('user_id')
            user = User.query.get(user_id)
            
            if user and not user.is_admin:  # Prevent admin deletion
                try:
                    # Delete associated votes first
                    Vote.query.filter_by(user_id=user.id).delete()
                    db.session.delete(user)
                    db.session.commit()
                    flash('Voter deleted successfully', 'success')
                except Exception as e:
                    logging.error(f"Error deleting voter: {str(e)}")
                    flash('Error deleting voter', 'danger')
            else:
                flash('Voter not found or is an admin', 'danger')
                
    # Get all registered users
    users = User.query.all()
    
    return render_template('admin/voters.html', users=users)

@app.route('/api/blockchain')
def get_blockchain():
    """API endpoint to get blockchain data for visualization"""
    chain = blockchain.chain
    return jsonify(chain)

# Flag to track if admin creation has run
admin_created = False

# Initialize admin user if none exists
@app.before_request
def create_admin():
    global admin_created
    # Only run once by checking the global flag
    if not admin_created:
        admin = User.query.filter_by(is_admin=True).first()
        if not admin:
            admin = User(
                username='admin',
                email='admin@example.com',
                is_admin=True,
                is_registered=True
            )
            admin.set_password('adminpassword')
            db.session.add(admin)
            db.session.commit()
            logging.info("Admin user created")
        # Set flag to prevent re-running on every request
        admin_created = True
