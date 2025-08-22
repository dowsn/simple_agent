"""
SQLite Database Handler for Streamlit Web Scraper App
Handles user authentication, session management, and workflow logs
"""

import sqlite3
import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any
import json
from pathlib import Path


class Database:
    """Database handler for the Streamlit application."""
    
    def __init__(self, db_path: str = "./app_data.db"):
        """Initialize database connection and create tables if needed."""
        self.db_path = db_path
        self.init_database()
    
    def get_connection(self):
        """Get a database connection."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def init_database(self):
        """Initialize database tables."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Users table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    role TEXT DEFAULT 'user',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_login TIMESTAMP
                )
            """)
            
            # Sessions table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    token TEXT UNIQUE NOT NULL,
                    expires_at TIMESTAMP NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (id)
                )
            """)
            
            # Workflow runs table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS workflow_runs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    completed_at TIMESTAMP,
                    status TEXT NOT NULL,
                    config JSON,
                    results JSON,
                    social_posts JSON,
                    FOREIGN KEY (user_id) REFERENCES users (id)
                )
            """)
            
            # Logs table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    workflow_run_id INTEGER,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    level TEXT NOT NULL,
                    message TEXT NOT NULL,
                    data JSON,
                    FOREIGN KEY (workflow_run_id) REFERENCES workflow_runs (id)
                )
            """)
            
            # API configurations table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS api_configs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    service TEXT NOT NULL,
                    config JSON,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (id),
                    UNIQUE(user_id, service)
                )
            """)
            
            conn.commit()
    
    # ============= User Management =============
    
    def hash_password(self, password: str) -> str:
        """Hash a password using SHA256."""
        return hashlib.sha256(password.encode()).hexdigest()
    
    def create_user(self, username: str, password: str, role: str = "user") -> bool:
        """Create a new user."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO users (username, password_hash, role)
                    VALUES (?, ?, ?)
                """, (username, self.hash_password(password), role))
                conn.commit()
                return True
        except sqlite3.IntegrityError:
            return False
    
    def authenticate_user(self, username: str, password: str) -> Optional[Dict]:
        """Authenticate a user and return user info if successful."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, username, role, created_at
                FROM users
                WHERE username = ? AND password_hash = ?
            """, (username, self.hash_password(password)))
            
            user = cursor.fetchone()
            if user:
                # Update last login
                cursor.execute("""
                    UPDATE users SET last_login = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (user['id'],))
                conn.commit()
                
                return dict(user)
        return None
    
    # ============= Session Management =============
    
    def create_session(self, user_id: int, duration_hours: int = 24) -> str:
        """Create a new session token for a user."""
        token = secrets.token_urlsafe(32)
        expires_at = datetime.now() + timedelta(hours=duration_hours)
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO sessions (user_id, token, expires_at)
                VALUES (?, ?, ?)
            """, (user_id, token, expires_at))
            conn.commit()
        
        return token
    
    def validate_session(self, token: str) -> Optional[Dict]:
        """Validate a session token and return user info if valid."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT u.id, u.username, u.role, s.expires_at
                FROM sessions s
                JOIN users u ON s.user_id = u.id
                WHERE s.token = ? AND s.expires_at > CURRENT_TIMESTAMP
            """, (token,))
            
            session = cursor.fetchone()
            if session:
                return dict(session)
        return None
    
    def delete_session(self, token: str):
        """Delete a session (logout)."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM sessions WHERE token = ?", (token,))
            conn.commit()
    
    # ============= Workflow Management =============
    
    def create_workflow_run(self, user_id: int, config: Dict) -> int:
        """Create a new workflow run record."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO workflow_runs (user_id, status, config)
                VALUES (?, 'running', ?)
            """, (user_id, json.dumps(config)))
            conn.commit()
            return cursor.lastrowid
    
    def update_workflow_run(self, run_id: int, status: str, results: Dict = None, 
                           social_posts: Dict = None):
        """Update a workflow run with results."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE workflow_runs
                SET status = ?, completed_at = CURRENT_TIMESTAMP,
                    results = ?, social_posts = ?
                WHERE id = ?
            """, (status, json.dumps(results) if results else None,
                 json.dumps(social_posts) if social_posts else None, run_id))
            conn.commit()
    
    def get_workflow_runs(self, user_id: int, limit: int = 10) -> List[Dict]:
        """Get recent workflow runs for a user."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, started_at, completed_at, status, config, results, social_posts
                FROM workflow_runs
                WHERE user_id = ?
                ORDER BY started_at DESC
                LIMIT ?
            """, (user_id, limit))
            
            runs = []
            for row in cursor.fetchall():
                run = dict(row)
                if run['config']:
                    run['config'] = json.loads(run['config'])
                if run['results']:
                    run['results'] = json.loads(run['results'])
                if run['social_posts']:
                    run['social_posts'] = json.loads(run['social_posts'])
                runs.append(run)
            
            return runs
    
    def add_log(self, workflow_run_id: int, level: str, message: str, data: Dict = None):
        """Add a log entry for a workflow run."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO logs (workflow_run_id, level, message, data)
                VALUES (?, ?, ?, ?)
            """, (workflow_run_id, level, message, json.dumps(data) if data else None))
            conn.commit()
    
    def get_logs(self, workflow_run_id: int) -> List[Dict]:
        """Get logs for a workflow run."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT timestamp, level, message, data
                FROM logs
                WHERE workflow_run_id = ?
                ORDER BY timestamp ASC
            """, (workflow_run_id,))
            
            logs = []
            for row in cursor.fetchall():
                log = dict(row)
                if log['data']:
                    log['data'] = json.loads(log['data'])
                logs.append(log)
            
            return logs
    
    # ============= API Configuration =============
    
    def save_api_config(self, user_id: int, service: str, config: Dict):
        """Save API configuration for a user and service."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO api_configs (user_id, service, config, updated_at)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP)
            """, (user_id, service, json.dumps(config)))
            conn.commit()
    
    def get_api_config(self, user_id: int, service: str) -> Optional[Dict]:
        """Get API configuration for a user and service."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT config FROM api_configs
                WHERE user_id = ? AND service = ?
            """, (user_id, service))
            
            row = cursor.fetchone()
            if row and row['config']:
                return json.loads(row['config'])
        return None
    
    # ============= Cleanup =============
    
    def cleanup_expired_sessions(self):
        """Remove expired sessions from the database."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                DELETE FROM sessions
                WHERE expires_at < CURRENT_TIMESTAMP
            """)
            conn.commit()


# Initialize default admin user if database is new
def init_default_admin(db: Database, username: str, password: str):
    """Create default admin user if it doesn't exist."""
    db.create_user(username, password, role="admin")


if __name__ == "__main__":
    # Test database initialization
    db = Database()
    print("Database initialized successfully!")
    
    # Create test admin user
    if db.create_user("admin", "admin123", "admin"):
        print("Created admin user")
    else:
        print("Admin user already exists")