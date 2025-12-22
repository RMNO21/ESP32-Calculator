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

# ---------- STATE ----------
expr = ""
ANS = 0
shift=0
selected=1
Mode="calc"
# Added new modes here
modes_list= ["selecting", "calc", "integral", "equation", "matrix", "slope", "graph"]

# ------------selecting modes-------------
def modes(selected):
    oled.fill(0)
    # Update local list to match global
    modes_list_local = ["selecting", "calc", "integral", "equation", "matrix", "slope", "graph"]
    
    if selected < 1:
        selected = 1
    if selected >= len(modes_list_local):
        selected = len(modes_list_local) - 1    
    a=selected//6
    b=min((a+1)*6,len(modes_list_local))

    for i in range(a*6, b):
        y = (i - a*6) * 10
        if i == selected:
            oled.text(">" + modes_list_local[i], 0, y)
        else:
            oled.text(" " + modes_list_local[i], 0, y)

    oled.show()
    return(selected)

# ---------built-in functions:
def print_(*args):
    oled.fill(0)
    for i, arg in enumerate(args):
        arg=str(arg)
        arg = arg.replace("**", "^")
        arg = arg.replace("math.", "")
        arg = arg.replace("math.log(", "ln(")
        # truncate long lines
        if len(arg) > 16: arg = arg[:16]
        oled.text(arg, 0, i*10)
    oled.show()

def input_(text=None):
    if text is not None:
        print_(text)
        inp=""
        while True:
            key = read_key()
            if key=="=":
                break
            if key:
                if key == "c": inp = ""
                elif key == "←": inp = inp[:-1]
                else: inp=inp+process_key_simple(key)
            time.sleep_ms(10)
            print_(text,inp)
        return inp
    return ""

# Helper to process keys without executing math (for inputs)
def process_key_simple(k):
    if k in ["shift","mode","up","down","left","right","none"]: return ""
    if k == "x": return "x"
    if k == "^": return "**"
    if k == "log": return "math.log10("
    if k == "ln": return "math.log("
    if k == "sin": return "math.sin("
    if k == "cos": return "math.cos("
    if k == "tan": return "math.tan("
    if k == "√": return "math.sqrt("
    return k

# ----------Modes--------------

def integral():
    func = input_("enter f(x): ")
    a = float(input_("start point: "))
    b = float(input_("end point: "))
    n=1000 # fixed steps for speed

    step = (b - a) / n
    x = a + step / 2
    ans = 0
    i=0
    print_("calculating...")
    while x < b:
        try:
            value = eval(func, {"x": x, "math": math, "e": math.e, "pi": math.pi})
            ans += value
        except:
            pass # ignore domain errors
        x += step
        i+=1
    print_("Result:", ans * step)

def solve_eq():
    degree = float(input_("deg (2 or 3)? "))
    
    if degree == 2:
        a = float(input_("a: "))
        b = float(input_("b: "))
        c = float(input_("c: "))
        delta = b**2 - 4*a*c
        if delta < 0:
            print_("Complex Roots")
        else:
            x1 = (-b + math.sqrt(delta)) / (2*a)
            x2 = (-b - math.sqrt(delta)) / (2*a)
            print_("x1="+format_result(x1), "x2="+format_result(x2))
            
    elif degree == 3:
        # Solving ax^3 + bx^2 + cx + d = 0
        a = float(input_("a: "))
        b = float(input_("b: "))
        c = float(input_("c: "))
        d = float(input_("d: "))
        
        # simple numerical solver (Newton Raphson) to find one real root
        x = 0.0 # guess
        for i in range(20):
            fx = a*x**3 + b*x**2 + c*x + d
            dfx = 3*a*x**2 + 2*b*x + c
            if dfx == 0: break
            x = x - fx/dfx
        
        print_("Real root approx:", format_result(x))
    else:
        print_("Not supprted")

def matrix_ops():
    mode_m = float(input_("1:Det 2:Inv 3:Sys"))
    n = int(input_("Size n? "))
    
    # Input Matrix A
    mat = []
    print_("Enter Matrix A")
    time.sleep(1)
    for r in range(n):
        row = []
        for c in range(n):
            val = float(input_(f"A[{r+1}][{c+1}]: "))
            row.append(val)
        mat.append(row)
        
    if mode_m == 1: # Determinant
        det = get_det(mat, n)
        print_("Det =", det)
        
    elif mode_m == 2: # Inverse
        det = get_det(mat, n) # check singularity
        if abs(det) < 1e-9:
            print_("Singular Matrix")
        else:
            inv = get_inverse(mat, n)
            print_("Inv calculated")
            time.sleep(1)
            # Show row by row
            for r in range(n):
                s = ""
                for val in inv[r]:
                    s += "{:.1f},".format(val)
                print_(f"R{r+1}:", s)
                while read_key() != "=": time.sleep_ms(10)
                
    elif mode_m == 3: # System Ax=B
        b_vec = []
        print_("Enter Vector B")
        time.sleep(1)
        for i in range(n):
            val = float(input_(f"B[{i+1}]: "))
            b_vec.append(val)
            
        res = solve_system(mat, b_vec, n)
        if res is None:
            print_("No unique sol")
        else:
            for i in range(n):
                print_(f"X{i+1} =", format_result(res[i]))
                while read_key() != "=": time.sleep_ms(10)

# Matrix Helpers
def get_det(mat, n):
    temp = [row[:] for row in mat] # copy
    det = 1
    for i in range(n):
        pivot = i
        while pivot < n and temp[pivot][i] == 0: pivot += 1
        if pivot == n: return 0 # singular
        if pivot != i:
            temp[i], temp[pivot] = temp[pivot], temp[i]
            det *= -1
        det *= temp[i][i]
        for j in range(i + 1, n):
            factor = temp[j][i] / temp[i][i]
            for k in range(i + 1, n):
                temp[j][k] -= factor * temp[i][k]
    return det

def get_inverse(mat, n):
    # Augmented matrix [A | I]
    aug = [row[:] + [1 if i == j else 0 for j in range(n)] for i, row in enumerate(mat)]
    
    # Gaussian Elimination
    for i in range(n):
        pivot = aug[i][i]
        for j in range(i+1, 2*n): aug[i][j] /= pivot
        for k in range(n):
            if k != i:
                factor = aug[k][i]
                for j in range(i+1, 2*n): aug[k][j] -= factor * aug[i][j]
                
    return [row[n:] for row in aug]

def solve_system(A, B, n):
    # Cramer's rule is slow, use Gauss-Jordan logic simply
    # Create Augmented A|B
    aug = [A[i][:] + [B[i]] for i in range(n)]
    
    for i in range(n):
        pivot = aug[i][i]
        if pivot == 0: return None
        for j in range(i, n+1): aug[i][j] /= pivot
        for k in range(n):
            if k != i:
                factor = aug[k][i]
                for j in range(i, n+1): aug[k][j] -= factor * aug[i][j]
    return [row[n] for row in aug]

def calc_slope():
    func = input_("enter f(x): ")
    pt = float(input_("at point: "))
    h = 0.0001
    
    # f(x+h)
    x = pt + h
    y2 = eval(func, {"x": x, "math": math})
    # f(x-h)
    x = pt - h
    y1 = eval(func, {"x": x, "math": math})
    
    slope = (y2 - y1) / (2*h)
    print_("Slope m =", slope)

def graph_func():
    func = input_("f(x): ")
    # Simple auto scale or fixed
    xmin = -10
    xmax = 10
    ymin = -10
    ymax = 10
    
    oled.fill(0)
    # Draw axes
    oled.vline(64, 0, 64, 1) # Y axis
    oled.hline(0, 32, 128, 1) # X axis
    
    prev_px = None
    prev_py = None
    
    for col in range(128):
        # map screen x (0-128) to graph x
        x_val = xmin + (col / 128) * (xmax - xmin)
        try:
            y_val = eval(func, {"x": x_val, "math": math})
            
            # map graph y to screen y (64-0)
            # 64 pixels height. 
            py = 64 - int((y_val - ymin) / (ymax - ymin) * 64)
            
            if 0 <= py < 64:
                oled.pixel(col, py, 1)
                # simple line connect
                if prev_py is not None and abs(prev_py - py) < 10:
                    oled.line(col-1, prev_py, col, py, 1)
                prev_py = py
            else:
                prev_py = None
        except:
            prev_py = None
            
    oled.show()
    print_("Done. Press =")

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

    if k == "=":
        try:
            result = eval(expr, {"math": math, "e": math.e, "pi": math.pi})
            ANS = result
            expr = format_result(result)
            show(expr,Mode)
        except:
            expr = ""
            show("ERROR",Mode)
        return

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
    
    elif k=="right" and Mode =="selecting":
        Mode =modes_list[selected]
        
        

    elif k=="left":
        Mode="calc"
        

    
    elif k=="[+]":
        expr=expr+"math.ceil("
    elif k=="[-]":
        expr=expr+"math.floor("
    elif k=="ln":
        expr=expr+"math.log("

    elif k=="10^":
        expr=expr+"*10**("
    elif k=="||":
        expr=expr+"abs("
    elif k=="asin":
        expr=expr+"math.asin("
    elif k=="acos":
        expr=expr+"math.acos("
    elif k=="atan":
        expr=expr+"math.atan("
    elif k=="ca":
        expr=""

    elif k=="e":
        expr=expr+"math.e"
    elif k=="pi":
        expr=expr+"math.pi"
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
        while True:
            key = read_key()
            if key: break 
            time.sleep_ms(10)
    
    elif Mode == "equation":
        solve_eq()
        while True:
            key = read_key()
            if key: break
            time.sleep_ms(10)

    elif Mode == "matrix":
        matrix_ops()
        while True:
            key = read_key()
            if key: break
            time.sleep_ms(10)

    elif Mode == "slope":
        calc_slope()
        while True:
            key = read_key()
            if key: break
            time.sleep_ms(10)

    elif Mode == "graph":
        graph_func()
        while True:
            key = read_key()
            if key: break
            time.sleep_ms(10)

    key = read_key()
    if key:
        process_key(key)
    time.sleep_ms(10)