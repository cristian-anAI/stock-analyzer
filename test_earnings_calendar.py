import unittest
from earnings_calendar import EarningsChecker
import datetime

class TestEarningsChecker(unittest.TestCase):
    def setUp(self):
        self.checker = EarningsChecker()

    def test_known_earnings(self):
        # Ejemplo: AAPL suele tener earnings en julio/octubre/enero/abril
        # Ajusta la fecha si es necesario para la semana actual
        symbol = "AAPL"
        result = self.checker.has_upcoming_earnings(symbol, days=7)
        # No se puede garantizar True/False, pero debe ejecutarse sin error
        self.assertIsInstance(result, bool)

    def test_no_calendar(self):
        # Un símbolo inventado no debe tener earnings
        symbol = "ZZZZZZ"
        result = self.checker.has_upcoming_earnings(symbol, days=7)
        self.assertFalse(result)

if __name__ == "__main__":
    unittest.main()
