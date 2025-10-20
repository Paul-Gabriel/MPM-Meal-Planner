"""Plan domain entity: captures weekly meal schedule (week, year, meals mapping)."""

class Plan:
    def __init__(self, week_number, meals, year=None):
        self.week_number = week_number
        self.meals = meals
        self.year = year
        self.week = week_number  # stored also as 'week' for template compatibility
