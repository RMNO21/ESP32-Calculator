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
    ['x','[+]','log','left','right'],
    ['^','√','sin','cos','tan'],
    ['1','2','3','←','c'],
    ['4','5','6','*','/'],
    ['7','8','9','+','-'],
    ['.','0','(',')','=']
]
# ------------selecting modes-------------

def modes(selected):

    oled.fill(0)

    modes_list= ["selecting", "calc", "integral","mode 4", "mode 5", "mode 6","mode 7", "mode 8", "mode 9"]
    if selected < 1:
        selected = 1
    if selected >= len(modes_list):
        selected = len(modes_list) - 1    
    a=selected//6
    b=min((a+1)*6,len(modes_list))


    for i in range(a*6, b):
        y = (i - a*6) * 10
        if i == selected:
            oled.text(">" + modes_list[i], 0, y)
        else:
            oled.text(" " + modes_list[i], 0, y)

    oled.show()
    return(selected)

# ---------built-in functions:
def print_(*args):
    oled.fill(0)
    for i in range (len(args)) :
            args[i]=args[i].replace("**", "^")
            args[i]=args[i].replace("math.", "")
            args[i]=args[i].replace("math.log(", "ln(")
        oled.text(args[i],0,i*10)
    oled.show()

def input_():
    inp=""
    while True:
        key = read_key()
        if key=="=":
            break
        if key:
            inp=inp+process_key(key)
        time.sleep_ms(10)
    return inp



# ---------- STATE ----------


expr = ""
ANS = 0
shift=0
selected=1
Mode="calc"
modes_list= ["selecting", "calc", "integral","mode 4", "mode 5", "mode 6","mode 7", "mode 8", "mode 9"]
# ----------Modes--------------
def integral():
    oled.fill(0)
    key=""
    func=""
    while key!="=":
        key = read_key()
        if key=="=":
            break
        elif key:
            func+=str(process_key(key))

        oled.fill(0)
        oled.text("enter f(x): ",0,0)
        oled.text("S "+func+" dx",0,10)
        oled.show()

    #a = float(input("start point: "))
    start=""
    expr=""
    while True:
        key = read_key()
        if key=="=":
            break
        if key:
            start=str(process_key(key))

        oled.fill(0)
        oled.text("enter start: ",0,0)
        oled.text("a: "+start,0,10)
        oled.show()    

    #b = float(input("end point: "))
    end=""
    expr=""
    while True:
        key = read_key()
        if key=="=":
            break
        if key:
            end=str(process_key(key))

        oled.fill(0)
        oled.text("enter end: ",0,0)
        oled.text("b: "+end,0,10)
        oled.show()
    #print(start)
    a=int(start)
    b=int(end)
    n=1000*10**math.log10(b-a)

    step = (b - a) / n
    x = a + step / 2
    ans = 0
    i=0
    while x < b:
        if i%(n/10)==0:
            print(int((i/n)*100),"%",sep='',end="\r")
            
        value = eval(func, {"x": x, "math": math})
        ans += value
        x += step
        i+=1
    print (ans * step)
    return ans * step



# ---------- DISPLAY ----------
def show(text,Mode):
    if Mode== "selecting":
        return
    text=text.replace("**", "^")
    text=text.replace("math.", "")
    text=text.replace("math.log(", "ln(")
    if text[-5:]=="shift":
        Mode +=" shift"
        text=text[:-5]
    oled.fill(0)
    oled.text(Mode, 0, 0)
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
    global expr, ANS ,shift,keys,selected,Mode

    shifted = [
        ['shift','none','settings','down','up'],
        ['y','[-]','ln','left','right'],
        ['10^','||','asin','acos','atan'],
        ['1','2','3','←','ca'],
        ['4','5','6','!','%'],
        ['7','8','9','M+','M-'],
        ['inf','0+','e','pi','ans']
    ]

    normal = [
        ['shift','none','mode','down','up'],
        ['x','[+]','log','left','right'],
        ['^','√','sin','cos','tan'],
        ['1','2','3','←','c'],
        ['4','5','6','*','/'],
        ['7','8','9','+','-'],
        ['.','0','(',')','=']
    ]

    keys = shifted if shift else normal
    if Mode!="calc":
        expr=""
    #if k == "shift":
    #    shift = 1 - shift  # Toggle shift state (0 to 1 or 1 to 0)

    if k == "=":
        try:
            result = eval(expr, {"math": math})
            ANS = result
            expr = format_result(result)
            show(expr,Mode)
        except:
            expr = ""
            show("ERROR",Mode)
        return
    #elif k == "settings":

    elif k=="mode":
        modes(selected)
        Mode = "selecting"
        return
    
    elif k=="down":
        selected=selected-1
        selected=modes(selected)
        

    elif k=="up":
        selected=selected+1
        selected=modes(selected)
        return
    #elif k=="left":
    elif k=="right" and Mode =="selecting":
        Mode =modes_list[selected]
        
        

    elif k=="left":
        Mode="calc"
        

    
    #elif k=="right":
    
    elif k=="[+]":
        expr=expr+"math.ceil("
    elif k=="[-]":
        expr=expr+"math.floor("
    elif k=="ln":
        expr=expr+"math.log"

    elif k=="10^":
        expr=expr+"*10**("
    elif k=="||":
        expr=expr+"math.abs("
    elif k=="asin":
        expr=expr+"math.asin("
    elif k=="acos":
        expr=expr+"math.acos("
    elif k=="atan":
        expr=expr+"math.atan("
    elif k=="ca":
        expr=""
    #elif k=="M+":

    #elif k=="M-":

    elif k=="e":
        expr=expr+math.e
    elif k=="pi":
        expr=expr+math.pi
    elif k == "inf":
        expr += "1e308" 
    elif k == "0+":
        expr += "1e-308"
    elif k== "ans":
        expr += f"{ANS}"



    elif k == "←":
        expr = expr[:-1]
    elif k == "c":
        expr = ""
    elif k == "^":
        expr += "**"
    elif k == "√":
        expr += "math.sqrt("
    elif k == "sin":
        expr += "math.sin("
    elif k == "cos":
        expr += "math.cos("
    elif k == "tan":
        expr += "math.tan("
    elif k == "log":
        expr += "math.log10("
    elif k == "shift":

        if shift == 0:
           
            shift = 1
            keys = shifted
            expr += k
            show(expr,Mode)
            expr = expr[:-5]
        else:

            shift = 0
            keys = normal
            show(expr,Mode)

        time.sleep_ms(150)
        return

    else:
        expr += k
    if shift == 1 and k != "shift":
        shift = 0  
        keys = normal
    if Mode =="calc":
        show(expr,Mode)
    return(expr)

def format_result(r):
    if isinstance(r, float):
        if abs(r) > 1e6 or abs(r) < 1e-6:
            return "{:.6e}".format(r)
        return "{:.6f}".format(r).rstrip("0").rstrip(".")
    return str(r)

# ---------- INIT ----------
show("Ready",Mode)

# ---------- MAIN LOOP ----------
while True:
    if Mode =="integral":
        integral()
    key = read_key()
    if key:
        process_key(key)
    time.sleep_ms(10)
