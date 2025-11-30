from aiogram.fsm.state import State, StatesGroup


class BookingStates(StatesGroup):
    choosing_client = State()
    entering_client_name = State()
    entering_client_phone = State()
    entering_dates = State()
    confirming_dates = State()
    choosing_resource = State()
    entering_quantity = State()
    adding_resources = State()
    choosing_delivery_type = State()
    entering_delivery_comment = State()
    entering_cost = State()


class ResourceStates(StatesGroup):
    entering_name = State()
    entering_description = State()
    entering_quantity = State()
    # Новые состояния для редактирования
    choosing_resource_to_edit = State()
    editing_field = State()
    entering_new_value = State()


class MessageStates(StatesGroup):
    entering_user_id = State()
    entering_message = State()
    # Новое состояние для рассылки
    entering_broadcast_message = State()


class ReportStates(StatesGroup):
    choosing_report_type = State()
    entering_date_range = State()


class OrderEditStates(StatesGroup):
    """Состояния для редактирования заказов"""
    choosing_order = State()
    choosing_field = State()
    entering_new_dates = State()
    entering_new_cost = State()
    entering_new_comment = State()