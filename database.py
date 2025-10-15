import os
import logging

class Database:
    def __init__(self):
        self.connection = None
        self.connect()
        self.init_db()
    
    def connect(self):
        """Подключение к базе данных"""
        try:
            # Проверяем, есть ли PostgreSQL URL (на Render)
            database_url = os.environ.get('DATABASE_URL')
            
            if database_url:
                # Используем PostgreSQL на Render
                import psycopg2
                self.connection = psycopg2.connect(database_url, sslmode='require')
                print("✅ Подключено к PostgreSQL")
            else:
                # Используем SQLite локально
                import sqlite3
                self.connection = sqlite3.connect('bot_database.db')
                print("✅ Подключено к SQLite (локально)")
                
        except Exception as e:
            logging.error(f"Database connection error: {e}")
            print(f"❌ Ошибка подключения: {e}")
    
    def init_db(self):
        """Инициализация базы данных"""
        try:
            cursor = self.connection.cursor()
            
            if os.environ.get('DATABASE_URL'):
                # PostgreSQL
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS users (
                        user_id BIGINT PRIMARY KEY,
                        username TEXT,
                        first_name TEXT,
                        last_name TEXT,
                        subscribed BOOLEAN DEFAULT FALSE,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
            else:
                # SQLite
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS users (
                        user_id INTEGER PRIMARY KEY,
                        username TEXT,
                        first_name TEXT,
                        last_name TEXT,
                        subscribed BOOLEAN DEFAULT FALSE,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
            
            self.connection.commit()
            print("✅ База данных инициализирована")
        except Exception as e:
            logging.error(f"Database init error: {e}")
            print(f"❌ Ошибка инициализации: {e}")
    
    def add_user(self, user_id, username, first_name, last_name):
        """Добавление пользователя в базу"""
        try:
            cursor = self.connection.cursor()
            
            if os.environ.get('DATABASE_URL'):
                # PostgreSQL
                cursor.execute('''
                    INSERT INTO users (user_id, username, first_name, last_name) 
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (user_id) DO UPDATE SET
                    username = EXCLUDED.username,
                    first_name = EXCLUDED.first_name,
                    last_name = EXCLUDED.last_name
                ''', (user_id, username, first_name, last_name))
            else:
                # SQLite
                cursor.execute('''
                    INSERT OR REPLACE INTO users 
                    (user_id, username, first_name, last_name) 
                    VALUES (?, ?, ?, ?)
                ''', (user_id, username, first_name, last_name))
            
            self.connection.commit()
            return True
        except Exception as e:
            logging.error(f"Add user error: {e}")
            self.connect()  # Переподключаемся при ошибке
            return False
    
    def update_subscription(self, user_id, subscribed):
        """Обновление статуса подписки"""
        try:
            cursor = self.connection.cursor()
            
            if os.environ.get('DATABASE_URL'):
                cursor.execute('UPDATE users SET subscribed = %s WHERE user_id = %s', (subscribed, user_id))
            else:
                cursor.execute('UPDATE users SET subscribed = ? WHERE user_id = ?', (subscribed, user_id))
            
            self.connection.commit()
            return True
        except Exception as e:
            logging.error(f"Update subscription error: {e}")
            self.connect()
            return False
    
    def get_user(self, user_id):
        """Получение информации о пользователе"""
        try:
            cursor = self.connection.cursor()
            
            if os.environ.get('DATABASE_URL'):
                cursor.execute('SELECT * FROM users WHERE user_id = %s', (user_id,))
            else:
                cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
            
            return cursor.fetchone()
        except Exception as e:
            logging.error(f"Get user error: {e}")
            self.connect()
            return None
    
    def get_all_users(self):
        """Получение ВСЕХ пользователей из базы"""
        try:
            cursor = self.connection.cursor()
            cursor.execute('SELECT user_id FROM users')
            return cursor.fetchall()
        except Exception as e:
            logging.error(f"Get all users error: {e}")
            self.connect()
            return []
    
    def get_user_count(self):
        """Получение количества пользователей"""
        try:
            cursor = self.connection.cursor()
            cursor.execute('SELECT COUNT(*) FROM users')
            result = cursor.fetchone()
            return result[0] if result else 0
        except Exception as e:
            logging.error(f"Get user count error: {e}")
            self.connect()
            return 0