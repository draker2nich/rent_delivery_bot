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
            
            # Новая таблица для клиентов
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS clients (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    phone TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(name, phone)
                )
            """)
            
            # Обновленная таблица заказов (orders) - теперь без resource_id
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS orders (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    client_id INTEGER NOT NULL,
                    start_date DATE NOT NULL,
                    end_date DATE NOT NULL,
                    delivery_type TEXT NOT NULL,
                    delivery_comment TEXT,
                    cost TEXT,
                    status TEXT DEFAULT 'active',
                    created_by INTEGER NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    completed_at TIMESTAMP,
                    FOREIGN KEY (client_id) REFERENCES clients(id)
                )
            """)
            
            # Таблица позиций заказа (order_items) - связь заказов с ресурсами
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS order_items (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    order_id INTEGER NOT NULL,
                    resource_id INTEGER NOT NULL,
                    quantity INTEGER NOT NULL,
                    FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE,
                    FOREIGN KEY (resource_id) REFERENCES resources(id)
                )
            """)
            
            # Миграция старых данных из bookings в новую структуру
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='bookings'")
            if cursor.fetchone():
                logger.info("Обнаружена старая таблица bookings, начинаю миграцию...")
                
                # Копируем клиентов
                cursor.execute("""
                    INSERT OR IGNORE INTO clients (name, phone)
                    SELECT DISTINCT client_name, client_phone FROM bookings
                """)
                
                # Копируем заказы
                cursor.execute("""
                    INSERT INTO orders (client_id, start_date, end_date, delivery_type, 
                                       delivery_comment, cost, status, created_by, created_at, completed_at)
                    SELECT 
                        c.id,
                        b.start_date,
                        b.end_date,
                        b.delivery_type,
                        b.delivery_comment,
                        b.cost,
                        b.status,
                        b.created_by,
                        b.created_at,
                        b.completed_at
                    FROM bookings b
                    JOIN clients c ON c.name = b.client_name AND c.phone = b.client_phone
                """)
                
                # Копируем позиции заказов
                cursor.execute("""
                    INSERT INTO order_items (order_id, resource_id, quantity)
                    SELECT 
                        o.id,
                        b.resource_id,
                        b.quantity
                    FROM bookings b
                    JOIN clients c ON c.name = b.client_name AND c.phone = b.client_phone
                    JOIN orders o ON o.client_id = c.id 
                        AND o.start_date = b.start_date 
                        AND o.end_date = b.end_date
                        AND o.created_at = b.created_at
                """)
                
                logger.info("Миграция завершена успешно")
            
            conn.commit()
    
    # === КЛИЕНТЫ ===
    
    def add_client(self, name: str, phone: str) -> Optional[int]:
        """Добавить клиента или получить существующего"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT OR IGNORE INTO clients (name, phone) VALUES (?, ?)",
                    (name, phone)
                )
                cursor.execute(
                    "SELECT id FROM clients WHERE name = ? AND phone = ?",
                    (name, phone)
                )
                client_id = cursor.fetchone()[0]
                conn.commit()
                logger.info(f"Клиент добавлен/получен: {name} (ID: {client_id})")
                return client_id
        except Exception as e:
            logger.error(f"Ошибка добавления клиента: {e}")
            return None
    
    def get_all_clients(self) -> List[Tuple]:
        """Получить всех клиентов"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT c.id, c.name, c.phone, 
                       COUNT(o.id) as order_count,
                       MAX(o.created_at) as last_order
                FROM clients c
                LEFT JOIN orders o ON c.id = o.client_id
                GROUP BY c.id, c.name, c.phone
                ORDER BY last_order DESC NULLS LAST
            """)
            return cursor.fetchall()
    
    def get_client_by_id(self, client_id: int) -> Optional[Tuple]:
        """Получить клиента по ID"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, name, phone FROM clients WHERE id = ?", (client_id,))
            return cursor.fetchone()
    
    # === РЕСУРСЫ ===
    
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
    
    def update_resource(self, resource_id: int, name: str = None, description: str = None, 
                       total_quantity: int = None) -> bool:
        """Обновить ресурс"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                updates = []
                params = []
                
                if name is not None:
                    updates.append("name = ?")
                    params.append(name)
                if description is not None:
                    updates.append("description = ?")
                    params.append(description)
                if total_quantity is not None:
                    updates.append("total_quantity = ?")
                    params.append(total_quantity)
                
                if not updates:
                    return False
                
                params.append(resource_id)
                query = f"UPDATE resources SET {', '.join(updates)} WHERE id = ?"
                cursor.execute(query, params)
                conn.commit()
                
                if cursor.rowcount > 0:
                    logger.info(f"Ресурс обновлён: ID {resource_id}")
                    return True
                return False
        except Exception as e:
            logger.error(f"Ошибка обновления ресурса: {e}")
            return False
    
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
                               exclude_order_id: int = None) -> int:
        """Получить доступное количество ресурса на период"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("SELECT total_quantity FROM resources WHERE id = ?", (resource_id,))
            result = cursor.fetchone()
            if not result:
                return 0
            total = result[0]
            
            query = """
                SELECT SUM(oi.quantity) 
                FROM order_items oi
                JOIN orders o ON oi.order_id = o.id
                WHERE oi.resource_id = ?
                AND o.status = 'active'
                AND NOT (o.end_date < ? OR o.start_date > ?)
            """
            params = [resource_id, start_date, end_date]
            
            if exclude_order_id:
                query += " AND o.id != ?"
                params.append(exclude_order_id)
            
            cursor.execute(query, params)
            booked = cursor.fetchone()[0] or 0
            
            return total - booked
    
    def check_availability(self, resource_id: int, start_date: str, end_date: str, 
                          quantity: int = 1, exclude_order_id: int = None) -> bool:
        """Проверить доступность ресурса"""
        available = self.get_available_quantity(resource_id, start_date, end_date, exclude_order_id)
        return available >= quantity
    
    # === ЗАКАЗЫ ===
    
    def create_order(self, client_id: int, start_date: str, end_date: str,
                    delivery_type: str, delivery_comment: str, cost: str,
                    created_by: int) -> Optional[int]:
        """Создать новый заказ (без позиций)"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO orders 
                    (client_id, start_date, end_date, delivery_type, 
                     delivery_comment, cost, created_by)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (client_id, start_date, end_date, delivery_type, 
                      delivery_comment, cost, created_by))
                conn.commit()
                order_id = cursor.lastrowid
                logger.info(f"Заказ создан: #{order_id}")
                return order_id
        except Exception as e:
            logger.error(f"Ошибка создания заказа: {e}")
            return None
    
    def add_order_item(self, order_id: int, resource_id: int, quantity: int) -> bool:
        """Добавить позицию в заказ"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO order_items (order_id, resource_id, quantity)
                    VALUES (?, ?, ?)
                """, (order_id, resource_id, quantity))
                conn.commit()
                logger.info(f"Позиция добавлена в заказ #{order_id}: ресурс {resource_id}, кол-во {quantity}")
                return True
        except Exception as e:
            logger.error(f"Ошибка добавления позиции: {e}")
            return False
    
    def get_order_items(self, order_id: int) -> List[Tuple]:
        """Получить все позиции заказа"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT oi.id, r.name, oi.quantity, r.id
                    FROM order_items oi
                    JOIN resources r ON oi.resource_id = r.id
                    WHERE oi.order_id = ?
                """, (order_id,))
                result = cursor.fetchall()
                return result if result else []
        except Exception as e:
            logger.error(f"Ошибка получения позиций заказа {order_id}: {e}")
            return []
        
    def get_orders_for_date(self, date: str, filter_type: str = 'all') -> List[Tuple]:
        """Получить заказы на определенную дату
        
        Args:
            date: Дата в формате YYYY-MM-DD
            filter_type: 'start' - заказы начинающиеся в эту дату,
                        'end' - заказы заканчивающиеся в эту дату,
                        'all' - все заказы активные в эту дату
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            if filter_type == 'start':
                date_condition = "o.start_date = ?"
            elif filter_type == 'end':
                date_condition = "o.end_date = ?"
            else:
                date_condition = "? BETWEEN o.start_date AND o.end_date"
            
            query = f"""
                SELECT o.id, c.name, c.phone, o.start_date, o.end_date,
                    o.delivery_type, o.delivery_comment, o.cost, o.status
                FROM orders o
                JOIN clients c ON o.client_id = c.id
                WHERE {date_condition} AND o.status = 'active'
                ORDER BY o.start_date
            """
            
            cursor.execute(query, (date,))
            return cursor.fetchall()

    def get_order_details(self, order_id: int) -> Optional[Tuple]:
        """Получить детали заказа"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT o.id, c.name, c.phone, o.start_date, o.end_date,
                        o.delivery_type, o.delivery_comment, o.cost, o.status
                    FROM orders o
                    JOIN clients c ON o.client_id = c.id
                    WHERE o.id = ?
                """, (order_id,))
                return cursor.fetchone()
        except Exception as e:
            logger.error(f"Ошибка получения деталей заказа {order_id}: {e}")
            return None
    
    def get_orders_for_period(self, start_date: str, end_date: str) -> List[Tuple]:
        """Получить заказы за период"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT o.id, c.name, c.phone, o.start_date, o.end_date,
                       o.delivery_type, o.delivery_comment, o.cost, o.status
                FROM orders o
                JOIN clients c ON o.client_id = c.id
                WHERE NOT (o.end_date < ? OR o.start_date > ?)
                AND o.status = 'active'
                ORDER BY o.start_date
            """, (start_date, end_date))
            return cursor.fetchall()
    
    def get_all_active_orders(self) -> List[Tuple]:
        """Получить все активные заказы"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT o.id, c.name, c.phone, o.start_date, o.end_date,
                       o.delivery_type, o.delivery_comment, o.cost, o.status
                FROM orders o
                JOIN clients c ON o.client_id = c.id
                WHERE o.status = 'active'
                ORDER BY o.start_date DESC, o.id DESC
            """)
            return cursor.fetchall()
    
    def get_order_details(self, order_id: int) -> Optional[Tuple]:
        """Получить детали заказа"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT o.id, c.name, c.phone, o.start_date, o.end_date,
                       o.delivery_type, o.delivery_comment, o.cost, o.status
                FROM orders o
                JOIN clients c ON o.client_id = c.id
                WHERE o.id = ?
            """, (order_id,))
            return cursor.fetchone()
    
    def mark_order_completed(self, order_id: int) -> bool:
        """Отметить заказ как завершённый"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE orders SET status = 'completed', completed_at = CURRENT_TIMESTAMP WHERE id = ?",
                (order_id,)
            )
            conn.commit()
            if cursor.rowcount > 0:
                logger.info(f"Заказ #{order_id} отмечен как завершённый")
                return True
            return False
    
    def delete_order(self, order_id: int) -> bool:
        """Удалить заказ"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM orders WHERE id = ?", (order_id,))
            conn.commit()
            if cursor.rowcount > 0:
                logger.info(f"Заказ удалён: #{order_id}")
                return True
            return False
    
    # === ОТЧЁТЫ ===
    
    def get_clients_report(self, start_date: str = None, end_date: str = None) -> List[Tuple]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            query = """
                SELECT c.name, c.phone, 
                       MIN(o.created_at) as first_order,
                       MAX(o.created_at) as last_order,
                       COUNT(o.id) as total_orders,
                       SUM(CASE WHEN o.cost != '' THEN CAST(o.cost AS REAL) ELSE 0 END) as total_spent
                FROM clients c
                LEFT JOIN orders o ON c.id = o.client_id
                WHERE 1=1
            """
            params = []
            
            if start_date:
                query += " AND DATE(o.created_at) >= ?"
                params.append(start_date)
            if end_date:
                query += " AND DATE(o.created_at) <= ?"
                params.append(end_date)
            
            query += " GROUP BY c.id, c.name, c.phone HAVING COUNT(o.id) > 0 ORDER BY last_order DESC"
            
            cursor.execute(query, params)
            return cursor.fetchall()
    
    def get_financial_report(self, start_date: str = None, end_date: str = None) -> Tuple:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            query = """
                SELECT 
                    COUNT(*) as total_orders,
                    SUM(CASE WHEN cost != '' THEN CAST(cost AS REAL) ELSE 0 END) as total_revenue,
                    AVG(CASE WHEN cost != '' THEN CAST(cost AS REAL) ELSE 0 END) as avg_order
                FROM orders
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
                SELECT o.id, c.name, c.phone, o.start_date, o.end_date,
                       o.cost, o.status, o.created_at, o.completed_at
                FROM orders o
                JOIN clients c ON o.client_id = c.id
                WHERE 1=1
            """
            params = []
            
            if start_date:
                query += " AND DATE(o.created_at) >= ?"
                params.append(start_date)
            if end_date:
                query += " AND DATE(o.created_at) <= ?"
                params.append(end_date)
            
            query += " ORDER BY o.created_at DESC"
            
            cursor.execute(query, params)
            return cursor.fetchall()
    
    # Совместимость со старым API (для постепенной миграции)
    def create_booking(self, resource_id: int, client_name: str, client_phone: str,
                      start_date: str, end_date: str, quantity: int, delivery_type: str,
                      delivery_comment: str, cost: str, created_by: int) -> Optional[int]:
        """Создать бронь (legacy API)"""
        client_id = self.add_client(client_name, client_phone)
        if not client_id:
            return None
        
        order_id = self.create_order(client_id, start_date, end_date, delivery_type,
                                     delivery_comment, cost, created_by)
        if not order_id:
            return None
        
        if not self.add_order_item(order_id, resource_id, quantity):
            self.delete_order(order_id)
            return None
        
        return order_id
    
    def get_bookings_for_date(self, date: str, filter_type: str = 'all') -> List[Tuple]:
        """Legacy: получить брони на дату"""
        orders = self.get_orders_for_date(date, filter_type)
        result = []
        
        for order in orders:
            order_id = order[0]
            items = self.get_order_items(order_id)
            
            for item in items:
                _, resource_name, quantity, resource_id = item
                result.append((
                    order_id,
                    resource_name,
                    order[1],  # client_name
                    order[2],  # client_phone
                    order[3],  # start_date
                    order[4],  # end_date
                    quantity,
                    order[5],  # delivery_type
                    order[6],  # delivery_comment
                    order[7],  # cost
                    order[8]   # status
                ))
        
        return result
    
    def get_bookings_for_period(self, start_date: str, end_date: str) -> List[Tuple]:
        """Legacy: получить брони за период"""
        orders = self.get_orders_for_period(start_date, end_date)
        result = []
        
        for order in orders:
            order_id = order[0]
            items = self.get_order_items(order_id)
            
            for item in items:
                _, resource_name, quantity, resource_id = item
                result.append((
                    order_id,
                    resource_name,
                    order[1],  # client_name
                    order[2],  # client_phone
                    order[3],  # start_date
                    order[4],  # end_date
                    quantity,
                    order[5],  # delivery_type
                    order[6],  # delivery_comment
                    order[7],  # cost
                    order[8]   # status
                ))
        
        return result
    
    def get_all_active_bookings(self) -> List[Tuple]:
        """Legacy: получить все активные брони"""
        orders = self.get_all_active_orders()
        result = []
        
        for order in orders:
            order_id = order[0]
            items = self.get_order_items(order_id)
            
            for item in items:
                _, resource_name, quantity, resource_id = item
                result.append((
                    order_id,
                    resource_name,
                    order[1],  # client_name
                    order[2],  # client_phone
                    order[3],  # start_date
                    order[4],  # end_date
                    quantity,
                    order[5],  # delivery_type
                    order[6],  # delivery_comment
                    order[7],  # cost
                    order[8]   # status
                ))
        
        return result
    
    def get_booking_details(self, booking_id: int) -> Optional[Tuple]:
        """Legacy: получить детали брони"""
        order = self.get_order_details(booking_id)
        if not order:
            return None
        
        items = self.get_order_items(booking_id)
        if not items:
            return None
        
        # Возвращаем первую позицию (для совместимости)
        item = items[0]
        _, resource_name, quantity, _ = item
        
        return (
            order[0],  # id
            resource_name,
            order[1],  # client_name
            order[2],  # client_phone
            order[3],  # start_date
            order[4],  # end_date
            quantity,
            order[5],  # delivery_type
            order[6],  # delivery_comment
            order[7],  # cost
            order[8]   # status
        )
    
    def mark_booking_completed(self, booking_id: int) -> bool:
        """Legacy: отметить бронь завершённой"""
        return self.mark_order_completed(booking_id)
    
    def delete_booking(self, booking_id: int) -> bool:
        """Legacy: удалить бронь"""
        return self.delete_order(booking_id)
    
_db_instance = None

def get_database() -> Database:
    """Получить единственный экземпляр базы данных"""
    global _db_instance
    if _db_instance is None:
        _db_instance = Database()
    return _db_instance