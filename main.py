from machine import Pin, I2C
import ssd1306
import time

# --- MUX select pins ---
S0 = Pin(12, Pin.OUT)
S1 = Pin(14, Pin.OUT)
S2 = Pin(27, Pin.OUT)
S3 = Pin(26, Pin.OUT)

# --- MUX signal pin (GPIO35: input only, NO pull-up) ---
SIG = Pin(35, Pin.IN)

# --- OLED setup ---
i2c = I2C(0, scl=Pin(22), sda=Pin(21))
oled = ssd1306.SSD1306_I2C(128, 64, i2c)

def select_channel(ch):
    S0.value(ch & 1)
    S1.value((ch >> 1) & 1)
    S2.value((ch >> 2) & 1)
    S3.value((ch >> 3) & 1)
    time.sleep_us(3)  # settle time

def show_button(ch):
    oled.fill(0)
    oled.text("Pressed:", 0, 0)
    oled.text("Button {}".format(ch), 0, 20)
    oled.show()

oled.fill(0)
oled.text("Ready", 0, 0)
oled.text("Scanning...", 0, 16)
oled.show()

print("MUX scan started")

last_pressed = -1

while True:
    for ch in range(16):
        select_channel(ch)

        if SIG.value() == 0:  # active LOW
            if ch != last_pressed:
                print("Detected button:", ch)
                show_button(ch)
                last_pressed = ch
                time.sleep(0.25)  # debounce
    time.sleep_ms(5)
