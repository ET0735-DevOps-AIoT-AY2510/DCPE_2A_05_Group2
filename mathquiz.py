# game_math.py
# Math quiz game that does NOT initialize hardware or spawn threads.
# Usage:
#   from game_math import run_math_game
#   run_math_game(lcd, get_key_input)  # returns True (finished) or False (cancelled/wrong)

import random
import time
from database.db_utils import load_products_from_db, update_stock_in_db
from dcmotor import motor_spin

def run_math_game(lcd, read_key, rounds=5):
    
    def show(line1="", line2=""):
        lcd.lcd_clear()
        if line1:
            lcd.lcd_display_string(str(line1)[:16].ljust(16), 1)
        if line2:
            lcd.lcd_display_string(str(line2)[:16].ljust(16), 2)

    def gen_question():
        ops = ['+', '-', '*']
        a = random.randint(1, 10)
        b = random.randint(1, 10)
        op = random.choice(ops)
        if op == '-' and b > a:
            a, b = b, a
        expr = f"{a} {op} {b}"
        ans = eval(expr)  # safe here (controlled ops/operands)
        return f"{expr} = ?", ans

    # Ask up to `rounds` questions; any wrong answer ends the game
    for i in range(rounds):
        q_text, answer = gen_question()
        user = ""

        while True:
            show(f"Q{i+1}/{rounds}: {q_text}", user)
            k = read_key()  # int (0-9) or '*', '#', etc.; None if interrupted

            if k is None:
                show("Game cancelled", "")
                time.sleep(1)
                return False

            # backspace
            if k == '*':
                user = user[:-1]
                continue

            # submit
            if k == '#':
                if not user:
                    continue
                try:
                    if int(user) == int(answer):
                        show("Correct!", f"{user} \N{CHECK MARK}")
                        time.sleep(0.8)
                        break  # go to the next question
                    else:
                        show("Wrong!", f"Ans: {answer}")
                        time.sleep(1.5)
                        show("TRY AGAIN", "NEXT TIME!")
                        time.sleep(1.6)
                        return False
                except ValueError:
                    show("Digits only", "")
                    time.sleep(0.8)
                    user = ""
                    continue

            # digits
            if isinstance(k, int) or (isinstance(k, str) and k.isdigit()):
                user += str(k)
                if len(user) > 5:
                    user = user[:5]
                continue

            # ignore anything else and keep waiting

    # All correct → free drink
    show("CONGRATS!", "FREE DRINK!")
    time.sleep(1.1)

    drinks = load_products_from_db()
    in_stock = [pid for pid, p in drinks.items() if p.get("stock", 0) > 0]
    if not in_stock:
        show("No stock", "Sorry!")
        time.sleep(1.2)
        return True

    pid = random.choice(in_stock)
    name = drinks[pid]["name"]

    show("YOU WIN:", f"1 {name}")
    motor_spin()
    update_stock_in_db(pid)
    time.sleep(2.0)

    show("End of Game", "")
    time.sleep(1.0)
    lcd.lcd_clear()
    return True
