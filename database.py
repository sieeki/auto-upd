import sqlite3
import logging
import os

class Database:
    def __init__(self, db_name='bot_database.db'):
        self.db_name = db_name
        self.init_db()
    
    def init_db(self):
        """Инициализация базы данных"""
        try:
            conn = sqlite3.connect(self.db_name)
            cursor = conn.cursor()
            
            # Таблица пользователей
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
            
            # Таблица рефералов
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS referrals (
                    user_id INTEGER PRIMARY KEY,
                    referrer_id INTEGER,
                    invited_count INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (user_id)
                )
            ''')
            
            conn.commit()
            conn.close()
            print("✅ База данных инициализирована")
        except Exception as e:
            logging.error(f"Database init error: {e}")
            print(f"❌ Ошибка инициализации: {e}")
    
    def add_user(self, user_id, username, first_name, last_name, referrer_id=None):
        """Добавление пользователя в базу"""
        try:
            conn = sqlite3.connect(self.db_name)
            cursor = conn.cursor()
            
            # Добавляем пользователя
            cursor.execute('''
                INSERT OR REPLACE INTO users 
                (user_id, username, first_name, last_name) 
                VALUES (?, ?, ?, ?)
            ''', (user_id, username, first_name, last_name))
            
            # Добавляем реферала если есть реферер
            if referrer_id:
                cursor.execute('''
                    INSERT OR REPLACE INTO referrals 
                    (user_id, referrer_id, invited_count) 
                    VALUES (?, ?, COALESCE((SELECT invited_count FROM referrals WHERE user_id = ?), 0))
                ''', (user_id, referrer_id, referrer_id))
                
                # Увеличиваем счетчик приглашенных у реферера
                cursor.execute('''
                    UPDATE referrals SET invited_count = invited_count + 1 
                    WHERE user_id = ?
                ''', (referrer_id,))
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logging.error(f"Add user error: {e}")
            return False
    
    def update_subscription(self, user_id, subscribed):
        """Обновление статуса подписки"""
        try:
            conn = sqlite3.connect(self.db_name)
            cursor = conn.cursor()
            
            cursor.execute('UPDATE users SET subscribed = ? WHERE user_id = ?', (subscribed, user_id))
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logging.error(f"Update subscription error: {e}")
            return False
    
    def get_user(self, user_id):
        """Получение информации о пользователе"""
        try:
            conn = sqlite3.connect(self.db_name)
            cursor = conn.cursor()
            
            cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
            user = cursor.fetchone()
            
            conn.close()
            return user
        except Exception as e:
            logging.error(f"Get user error: {e}")
            return None
    
    def get_all_users(self):
        """Получение ВСЕХ пользователей из базы"""
        try:
            conn = sqlite3.connect(self.db_name)
            cursor = conn.cursor()
            
            cursor.execute('SELECT user_id FROM users')
            users = cursor.fetchall()
            
            conn.close()
            return users
        except Exception as e:
            logging.error(f"Get all users error: {e}")
            return []
    
    def get_user_count(self):
        """Получение количества пользователей"""
        try:
            conn = sqlite3.connect(self.db_name)
            cursor = conn.cursor()
            
            cursor.execute('SELECT COUNT(*) FROM users')
            count = cursor.fetchone()[0]
            
            conn.close()
            return count
        except Exception as e:
            logging.error(f"Get user count error: {e}")
            return 0
    
    def get_referral_info(self, user_id):
        """Получение информации о рефералах пользователя"""
        try:
            conn = sqlite3.connect(self.db_name)
            cursor = conn.cursor()
            
            # Получаем количество приглашенных
            cursor.execute('SELECT invited_count FROM referrals WHERE user_id = ?', (user_id,))
            result = cursor.fetchone()
            invited_count = result[0] if result else 0
            
            # Получаем кто пригласил этого пользователя
            cursor.execute('SELECT referrer_id FROM referrals WHERE user_id = ?', (user_id,))
            referrer_result = cursor.fetchone()
            referrer_id = referrer_result[0] if referrer_result else None
            
            conn.close()
            
            return {
                'invited_count': invited_count,
                'referrer_id': referrer_id,
                'needed_count': max(0, 30 - invited_count)  # Сколько осталось до награды
            }
        except Exception as e:
            logging.error(f"Get referral info error: {e}")
            return {'invited_count': 0, 'referrer_id': None, 'needed_count': 30}
    
    def get_referral_stats(self):
        """Получение общей статистики по рефералам"""
        try:
            conn = sqlite3.connect(self.db_name)
            cursor = conn.cursor()
            
            # Топ рефереров
            cursor.execute('''
                SELECT u.user_id, u.first_name, u.username, r.invited_count 
                FROM referrals r 
                JOIN users u ON r.user_id = u.user_id 
                WHERE r.invited_count > 0 
                ORDER BY r.invited_count DESC 
                LIMIT 10
            ''')
            top_referrers = cursor.fetchall()
            
            conn.close()
            return top_referrers
        except Exception as e:
            logging.error(f"Get referral stats error: {e}")
            return []