import random
from config.settings import settings

class MathService:
    @staticmethod
    def generate_problem() -> tuple[str, int]:
        """Генерация математической задачи"""
        a = random.randint(settings.MATH_MIN_NUMBER, settings.MATH_MAX_NUMBER)
        b = random.randint(settings.MATH_MIN_NUMBER, settings.MATH_MAX_NUMBER)
        problem = f"{a} + {b}"
        answer = a + b
        return problem, answer
    
    @staticmethod
    def validate_answer(user_answer: str, correct_answer: int) -> bool:
        """Проверка ответа"""
        try:
            return int(user_answer.strip()) == correct_answer
        except (ValueError, TypeError):
            return False