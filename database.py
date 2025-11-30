import sqlite3
from typing import List, Optional, Tuple
from config import DATABASE_PATH, logger


class Database:
    def __init__(self, db_path: str = DATABASE_PATH):
        self.db_path = db_path
        self.init_db()
        logger.info(f"База данных инициализирована: {db_path}")
    
    def get_connection(self):
        return sqlite3.connect(self.db_path)
    
    def init_db(self):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS resources (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,
                    description TEXT,
                    total_quantity INTEGER DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS bookings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    resource_id INTEGER NOT NULL,
                    client_name TEXT NOT NULL,
                    client_phone TEXT NOT NULL,
                    start_date DATE NOT NULL,
                    end_date DATE NOT NULL,
                    quantity INTEGER DEFAULT 1,
                    delivery_type TEXT NOT NULL,
                    delivery_comment TEXT,
                    cost TEXT,
                    status TEXT DEFAULT 'active',
                    created_by INTEGER NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    completed_at TIMESTAMP,
                    FOREIGN KEY (resource_id) REFERENCES resources(id)
                )
            """)
            
            # Проверка и добавление недостающих колонок
            cursor.execute("PRAGMA table_info(resources)")
            resource_columns = [column[1] for column in cursor.fetchall()]
            
            if 'total_quantity' not in resource_columns:
                cursor.execute("ALTER TABLE resources ADD COLUMN total_quantity INTEGER DEFAULT 1")
            
            cursor.execute("PRAGMA table_info(bookings)")
            booking_columns = [column[1] for column in cursor.fetchall()]
            
            if 'quantity' not in booking_columns:
                cursor.execute("ALTER TABLE bookings ADD COLUMN quantity INTEGER DEFAULT 1")
            if 'delivery_type' not in booking_columns:
                cursor.execute("ALTER TABLE bookings ADD COLUMN delivery_type TEXT DEFAULT 'pickup'")
            if 'delivery_comment' not in booking_columns:
                cursor.execute("ALTER TABLE bookings ADD COLUMN delivery_comment TEXT")
            if 'cost' not in booking_columns:
                cursor.execute("ALTER TABLE bookings ADD COLUMN cost TEXT")
            if 'status' not in booking_columns:
                cursor.execute("ALTER TABLE bookings ADD COLUMN status TEXT DEFAULT 'active'")
            if 'completed_at' not in booking_columns:
                cursor.execute("ALTER TABLE bookings ADD COLUMN completed_at TIMESTAMP")
            
            conn.commit()
    
    def add_resource(self, name: str, description: str = "", quantity: int = 1) -> bool:
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO resources (name, description, total_quantity) VALUES (?, ?, ?)",
                    (name, description, quantity)
                )
                conn.commit()
                logger.info(f"Ресурс добавлен: {name} ({quantity} шт.)")
                return True
        except sqlite3.IntegrityError:
            logger.warning(f"Ресурс уже существует: {name}")
            return False
    
    def get_resources(self) -> List[Tuple]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, name, description, total_quantity FROM resources ORDER BY name")
            return cursor.fetchall()
    
    def get_resource_info(self, resource_id: int) -> Optional[Tuple]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, name, total_quantity FROM resources WHERE id = ?", (resource_id,))
            return cursor.fetchone()
    
    def delete_resource(self, resource_id: int) -> bool:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM resources WHERE id = ?", (resource_id,))
            conn.commit()
            if cursor.rowcount > 0:
                logger.info(f"Ресурс удалён: ID {resource_id}")
                return True
            return False
    
    def get_available_quantity(self, resource_id: int, start_date: str, end_date: str, 
                               exclude_booking_id: int = None) -> int:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("SELECT total_quantity FROM resources WHERE id = ?", (resource_id,))
            result = cursor.fetchone()
            if not result:
                return 0
            total = result[0]
            
            query = """
                SELECT SUM(quantity) FROM bookings
                WHERE resource_id = ?
                AND status = 'active'
                AND NOT (end_date < ? OR start_date > ?)
            """
            params = [resource_id, start_date, end_date]
            
            if exclude_booking_id:
                query += " AND id != ?"
                params.append(exclude_booking_id)
            
            cursor.execute(query, params)
            booked = cursor.fetchone()[0] or 0
            
            return total - booked
    
    def check_availability(self, resource_id: int, start_date: str, end_date: str, 
                          quantity: int = 1, exclude_booking_id: int = None) -> bool:
        available = self.get_available_quantity(resource_id, start_date, end_date, exclude_booking_id)
        return available >= quantity
    
    def create_booking(self, resource_id: int, client_name: str, client_phone: str,
                      start_date: str, end_date: str, quantity: int, delivery_type: str,
                      delivery_comment: str, cost: str, created_by: int) -> Optional[int]:
        if not self.check_availability(resource_id, start_date, end_date, quantity):
            logger.warning(f"Недостаточно ресурсов {resource_id} в период {start_date} - {end_date}")
            return None
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO bookings 
                (resource_id, client_name, client_phone, start_date, end_date,
                 quantity, delivery_type, delivery_comment, cost, created_by)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (resource_id, client_name, client_phone, start_date, end_date,
                  quantity, delivery_type, delivery_comment, cost, created_by))
            conn.commit()
            booking_id = cursor.lastrowid
            logger.info(f"Бронь создана: #{booking_id} для клиента {client_name}")
            return booking_id
    
    def get_bookings_for_date(self, date: str, filter_type: str = 'all') -> List[Tuple]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            if filter_type == 'start':
                query = """
                    SELECT b.id, r.name, b.client_name, b.client_phone, 
                           b.start_date, b.end_date, b.quantity, b.delivery_type, 
                           b.delivery_comment, b.cost, b.status
                    FROM bookings b
                    JOIN resources r ON b.resource_id = r.id
                    WHERE b.start_date = ? AND b.status = 'active'
                    ORDER BY r.name
                """
            elif filter_type == 'end':
                query = """
                    SELECT b.id, r.name, b.client_name, b.client_phone, 
                           b.start_date, b.end_date, b.quantity, b.delivery_type, 
                           b.delivery_comment, b.cost, b.status
                    FROM bookings b
                    JOIN resources r ON b.resource_id = r.id
                    WHERE b.end_date = ? AND b.status = 'active'
                    ORDER BY r.name
                """
            else:
                query = """
                    SELECT b.id, r.name, b.client_name, b.client_phone, 
                           b.start_date, b.end_date, b.quantity, b.delivery_type, 
                           b.delivery_comment, b.cost, b.status
                    FROM bookings b
                    JOIN resources r ON b.resource_id = r.id
                    WHERE ? BETWEEN b.start_date AND b.end_date 
                    AND b.status = 'active'
                    ORDER BY r.name
                """
            
            cursor.execute(query, (date,))
            return cursor.fetchall()
    
    def get_bookings_for_period(self, start_date: str, end_date: str) -> List[Tuple]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT b.id, r.name, b.client_name, b.client_phone, 
                       b.start_date, b.end_date, b.quantity, b.delivery_type,
                       b.delivery_comment, b.cost, b.status
                FROM bookings b
                JOIN resources r ON b.resource_id = r.id
                WHERE NOT (b.end_date < ? OR b.start_date > ?)
                AND b.status = 'active'
                ORDER BY b.start_date, r.name
            """, (start_date, end_date))
            return cursor.fetchall()
    
    def mark_booking_completed(self, booking_id: int) -> bool:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE bookings SET status = 'completed', completed_at = CURRENT_TIMESTAMP WHERE id = ?",
                (booking_id,)
            )
            conn.commit()
            if cursor.rowcount > 0:
                logger.info(f"Бронь #{booking_id} отмечена как завершённая")
                return True
            return False
    
    def delete_booking(self, booking_id: int) -> bool:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM bookings WHERE id = ?", (booking_id,))
            conn.commit()
            if cursor.rowcount > 0:
                logger.info(f"Бронь удалена: #{booking_id}")
                return True
            return False
    
    def get_booking_details(self, booking_id: int) -> Optional[Tuple]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT b.id, r.name, b.client_name, b.client_phone, 
                       b.start_date, b.end_date, b.quantity, b.delivery_type,
                       b.delivery_comment, b.cost, b.status
                FROM bookings b
                JOIN resources r ON b.resource_id = r.id
                WHERE b.id = ?
            """, (booking_id,))
            return cursor.fetchone()
    
    def get_all_active_bookings(self) -> List[Tuple]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT b.id, r.name, b.client_name, b.client_phone, 
                       b.start_date, b.end_date, b.quantity, b.delivery_type,
                       b.delivery_comment, b.cost, b.status
                FROM bookings b
                JOIN resources r ON b.resource_id = r.id
                WHERE b.status = 'active'
                ORDER BY b.start_date DESC, b.id DESC
            """)
            return cursor.fetchall()
    
    def get_clients_report(self, start_date: str = None, end_date: str = None) -> List[Tuple]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            query = """
                SELECT DISTINCT b.client_name, b.client_phone, 
                       MIN(b.created_at) as first_order,
                       MAX(b.created_at) as last_order,
                       COUNT(*) as total_orders,
                       SUM(CASE WHEN b.cost != '' THEN CAST(b.cost AS REAL) ELSE 0 END) as total_spent
                FROM bookings b
                WHERE 1=1
            """
            params = []
            
            if start_date:
                query += " AND DATE(b.created_at) >= ?"
                params.append(start_date)
            if end_date:
                query += " AND DATE(b.created_at) <= ?"
                params.append(end_date)
            
            query += " GROUP BY b.client_name, b.client_phone ORDER BY last_order DESC"
            
            cursor.execute(query, params)
            return cursor.fetchall()
    
    def get_financial_report(self, start_date: str = None, end_date: str = None) -> Tuple:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            query = """
                SELECT 
                    COUNT(*) as total_bookings,
                    SUM(CASE WHEN cost != '' THEN CAST(cost AS REAL) ELSE 0 END) as total_revenue,
                    AVG(CASE WHEN cost != '' THEN CAST(cost AS REAL) ELSE 0 END) as avg_order
                FROM bookings
                WHERE 1=1
            """
            params = []
            
            if start_date:
                query += " AND DATE(created_at) >= ?"
                params.append(start_date)
            if end_date:
                query += " AND DATE(created_at) <= ?"
                params.append(end_date)
            
            cursor.execute(query, params)
            return cursor.fetchone()
    
    def get_operations_report(self, start_date: str = None, end_date: str = None) -> List[Tuple]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            query = """
                SELECT b.id, r.name, b.client_name, b.client_phone,
                       b.start_date, b.end_date, b.quantity, b.cost,
                       b.status, b.created_at, b.completed_at
                FROM bookings b
                JOIN resources r ON b.resource_id = r.id
                WHERE 1=1
            """
            params = []
            
            if start_date:
                query += " AND DATE(b.created_at) >= ?"
                params.append(start_date)
            if end_date:
                query += " AND DATE(b.created_at) <= ?"
                params.append(end_date)
            
            query += " ORDER BY b.created_at DESC"
            
            cursor.execute(query, params)
            return cursor.fetchall()