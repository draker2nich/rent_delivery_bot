from aiogram.fsm.state import State, StatesGroup


class BookingStates(StatesGroup):
    choosing_resource = State()
    entering_quantity = State()
    entering_dates = State()
    confirming_dates = State()
    entering_client_name = State()
    entering_client_phone = State()
    choosing_delivery_type = State()
    entering_delivery_comment = State()
    entering_cost = State()


class ResourceStates(StatesGroup):
    entering_name = State()
    entering_description = State()
    entering_quantity = State()


class MessageStates(StatesGroup):
    entering_user_id = State()
    entering_message = State()


class ReportStates(StatesGroup):
    choosing_report_type = State()
    entering_date_range = State()