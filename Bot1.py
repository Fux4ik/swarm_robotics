import sys
import tty
import termios
from AlphaBot2 import AlphaBot2
import time

def get_key():
    """Получить нажатую клавишу"""
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    try:
        tty.setraw(sys.stdin.fileno())
        key = sys.stdin.read(1)
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
    return key

def main():
    # Инициализация робота
    bot = AlphaBot2()
    speed = 50  # Начальная скорость
    
    print("=== AlphaBot2 Keyboard Control ===")
    print("W - Вперёд")
    print("S - Назад")
    print("A - Влево")
    print("D - Вправо")
    print("+ - Увеличить скорость")
    print("- - Уменьшить скорость")
    print("Space - Стоп")
    print("Q - Выход")
    print(f"\nТекущая скорость: {speed}%")
    print("================================\n")
    
    try:
        while True:
            key = get_key().lower()
            
            if key == 'w':
                print(f"Вперёд (скорость: {speed}%)")
                bot.setPWMA(speed)
                bot.setPWMB(speed)
                bot.forward()
                
            elif key == 's':
                print(f"Назад (скорость: {speed}%)")
                bot.setPWMA(speed)
                bot.setPWMB(speed)
                bot.backward()
                
            elif key == 'a':
                print(f"Влево (скорость: {speed}%)")
                bot.left()
                
            elif key == 'd':
                print(f"Вправо (скорость: {speed}%)")
                bot.right()
                
            elif key == ' ':
                print("Стоп")
                bot.stop()
                
            elif key == '+' or key == '=':
                speed = min(100, speed + 10)
                print(f"Скорость увеличена: {speed}%")
                
            elif key == '-' or key == '_':
                speed = max(20, speed - 10)
                print(f"Скорость уменьшена: {speed}%")
                
            elif key == 'q':
                print("Выход...")
                bot.stop()
                break
                
            elif key == '\x03':  # Ctrl+C
                break
                
    except KeyboardInterrupt:
        print("\nПрограмма остановлена")
    finally:
        bot.stop()
        print("Робот остановлен")

if __name__ == '__main__':
    main()

