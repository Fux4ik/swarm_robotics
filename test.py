from AlphaBot2 import AlphaBot2
import time

bot = AlphaBot2()

print("Forward")
bot.setMotor(20, 20)
time.sleep(2)
bot.setMotor(0, 0)

time.sleep(1)

print("Turn right")
bot.setMotor(20, -20)
time.sleep(1)
bot.setMotor(0, 0)

time.sleep(1)

print("Turn left")
bot.setMotor(-20, 20)
time.sleep(1)
bot.setMotor(0, 0)
