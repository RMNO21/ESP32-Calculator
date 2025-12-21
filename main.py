import machine, ssd1306, time, math

# ---------- OLED ----------
i2c = machine.I2C(0, scl=machine.Pin(22), sda=machine.Pin(21))
oled = ssd1306.SSD1306_I2C(128, 64, i2c)

# ---------- KEYPAD ----------
row_pins = [33, 25, 26, 27, 14, 12, 13]
col_pins = [18, 19, 32, 5, 23]

rows = [machine.Pin(p, machine.Pin.OUT, value=1) for p in row_pins]
cols = [machine.Pin(p, machine.Pin.IN, machine.Pin.PULL_UP) for p in col_pins]

keys = [
    ['shift','none','mode','down','up'],
    ['x','[]','log','left','right'],
    ['^','√','sin','cos','tan'],
    ['1','2','3','←','c'],
    ['4','5','6','*','/'],
    ['7','8','9','+','-'],
    ['.','0','(',')','=']
]

# ---------- STATE ----------
expr = ""
ANS = 0

# ---------- SAFE ENV ----------
SAFE_ENV = {
    "__builtins__": None,
    "sin": math.sin,
    "cos": math.cos,
    "tan": math.tan,
    "sqrt": math.sqrt,
    "log": math.log,
    "log10": math.log10,
    "pi": math.pi,
    "e": math.e,
    "ANS": lambda: ANS
}

# ---------- DISPLAY ----------
def show(text):
    oled.fill(0)
    oled.text("Calc:", 0, 0)
    lines = [text[i:i+16] for i in range(0, len(text), 16)]
    for i, l in enumerate(lines[-3:]):
        oled.text(l, 0, 16 + i*16)
    oled.show()

# ---------- KEYPAD SCAN ----------
def read_key():
    for r_i, r in enumerate(rows):
        r.value(0)
        time.sleep_ms(3)
        for c_i, c in enumerate(cols):
            if c.value() == 0:
                time.sleep_ms(20)
                if c.value() == 0:
                    k = keys[r_i][c_i]
                    while c.value() == 0:
                        time.sleep_ms(10)
                    r.value(1)
                    return k
        r.value(1)
    return None

# ---------- KEY PROCESS ----------
def process_key(k):
    global expr, ANS

    if k == "=":
        try:
            result = eval(expr, SAFE_ENV)
            ANS = result
            expr = format_result(result)
            show(expr)
        except:
            expr = ""
            show("ERROR")
        return

    if k == "←":
        expr = expr[:-1]
    elif k.lower() == "c":
        expr = ""
    elif k == "x":
        expr += "*"
    elif k == "^":
        expr += "**"
    elif k == "√":
        expr += "sqrt("
    elif k == "sin":
        expr += "sin("
    elif k == "cos":
        expr += "cos("
    elif k == "tan":
        expr += "tan("
    elif k == "log":
        expr += "log10("
    else:
        expr += k

    show(expr)

def format_result(r):
    if isinstance(r, float):
        if abs(r) > 1e6 or abs(r) < 1e-6:
            return "{:.6e}".format(r)
        return "{:.6f}".format(r).rstrip("0").rstrip(".")
    return str(r)

# ---------- INIT ----------
show("Ready")

# ---------- MAIN LOOP ----------
while True:
    key = read_key()
    if key:
        process_key(key)
    time.sleep_ms(10)
